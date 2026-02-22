"""Main dashboard runner that coordinates all auditors and processors."""

from typing import Optional, List, Dict
from datetime import datetime

from xpol.clients.gcp import GCPClient
from xpol.services.billing import CostProcessor
from xpol.auditors import (
    CloudRunAuditor,
    CloudFunctionsAuditor,
    ComputeAuditor,
    CloudSQLAuditor,
    StorageAuditor,
)
from xpol.services.forecast import ForecastService
from xpol.services.budget import BudgetService
from xpol.services.billing import BQSpendService
from xpol.services.project import ProjectManager
from xpol.types import (
    DashboardData,
    AuditResult,
    OptimizationRecommendation,
    ForecastData,
    MultiProjectDashboardData,
    ProjectData,
    BudgetAlert
)
from xpol.utils.visualizations import print_progress, print_error, print_warning
from xpol.utils.helpers import get_current_month_range


class DashboardRunner:
    """Main dashboard runner."""
    
    def __init__(
        self,
        project_id: str,
        billing_dataset: str,
        billing_table_prefix: str = "gcp_billing_export_v1",
        regions: Optional[List[str]] = None,
        location: Optional[str] = None,
        hide_project_id: bool = False
    ):
        """Initialize dashboard runner.
        
        Args:
            project_id: GCP project ID
            billing_dataset: BigQuery billing dataset (e.g., 'project.dataset_name')
            billing_table_prefix: Billing table prefix
            regions: List of regions to audit
            location: BigQuery location/region (e.g., 'US', 'asia-southeast1')
            hide_project_id: Whether to hide project ID in output for security
        """
        self.project_id = project_id
        self.billing_dataset = billing_dataset
        self.billing_table_prefix = billing_table_prefix
        self.regions = regions or ["us-central1", "us-east1", "europe-west1"]
        self.hide_project_id = hide_project_id
        
        # Initialize GCP client
        print_progress("Initializing GCP clients...")
        self.gcp_client = GCPClient(project_id=project_id, location=location)
        print_progress("GCP clients initialized", done=True)
        
        # Initialize processors and auditors
        self.cost_processor = CostProcessor(
            self.gcp_client.bigquery,
            billing_dataset,
            billing_table_prefix
        )
        
        self.cloud_run_auditor = CloudRunAuditor(
            self.gcp_client.cloud_run,
            self.gcp_client.monitoring,
            project_id
        )
        
        self.cloud_functions_auditor = CloudFunctionsAuditor(
            self.gcp_client.cloud_functions,
            self.gcp_client.monitoring,
            project_id
        )
        
        self.compute_auditor = ComputeAuditor(
            self.gcp_client.compute_instances,
            project_id
        )
        
        self.cloud_sql_auditor = CloudSQLAuditor(
            self.gcp_client.cloud_sql,
            self.gcp_client.monitoring,
            project_id
        )
        
        self.storage_auditor = StorageAuditor(
            self.gcp_client.compute_disks,
            self.gcp_client.compute_addresses,
            project_id
        )
        
        # Initialize forecast service
        self.forecast_service = ForecastService(
            self.gcp_client.bigquery,
            billing_dataset,
            billing_table_prefix
        )
        
        # Initialize budget and spend services
        self.budget_service = BudgetService(credentials=self.gcp_client.credentials)
        self.bq_spend_service = BQSpendService(
            self.gcp_client.bigquery,
            billing_dataset,
            billing_table_prefix
        )
        self.project_manager = ProjectManager(credentials=self.gcp_client.credentials)
    
    def run(self) -> DashboardData:
        """Run complete dashboard analysis.
        
        Returns:
            DashboardData with all results
        """
        print_progress("Starting FinOps dashboard analysis...")
        print()
        
        # Get cost data
        print_progress("Fetching cost data from BigQuery...")
        try:
            current_month_cost = self.cost_processor.get_current_month_cost(self.project_id)
            last_month_cost = self.cost_processor.get_last_month_cost(self.project_id)
            ytd_cost = self.cost_processor.get_ytd_cost(self.project_id)
            
            start_date, end_date = get_current_month_range()
            service_costs = self.cost_processor.get_service_costs(
                start_date,
                end_date,
                self.project_id
            )
            print_progress("Cost data retrieved", done=True)
        except Exception as e:
            print_error(f"Failed to fetch cost data: {str(e)}")
            current_month_cost = 0.0
            last_month_cost = 0.0
            ytd_cost = 0.0
            service_costs = {}
        
        print()
        
        # Run audits
        audit_results = {}
        all_recommendations = []
        
        # Cloud Run audit
        print_progress("Auditing Cloud Run services...")
        try:
            cloud_run_result = self.cloud_run_auditor.audit_all_services(self.regions)
            audit_results["cloud_run"] = cloud_run_result
            all_recommendations.extend(cloud_run_result.recommendations)
            print_progress(f"Cloud Run audit complete: {cloud_run_result.total_count} services found", done=True)
        except Exception as e:
            print_warning(f"Cloud Run audit failed: {str(e)}")
        
        # Cloud Functions audit
        print_progress("Auditing Cloud Functions...")
        try:
            functions_result = self.cloud_functions_auditor.audit_all_functions(self.regions)
            audit_results["cloud_functions"] = functions_result
            all_recommendations.extend(functions_result.recommendations)
            print_progress(f"Cloud Functions audit complete: {functions_result.total_count} functions found", done=True)
        except Exception as e:
            print_warning(f"Cloud Functions audit failed: {str(e)}")
        
        # Compute Engine audit
        print_progress("Auditing Compute Engine instances...")
        try:
            zones = []
            for region in self.regions:
                zones.extend([f"{region}-a", f"{region}-b", f"{region}-c"])
            
            compute_result = self.compute_auditor.audit_all_instances(zones)
            audit_results["compute_engine"] = compute_result
            all_recommendations.extend(compute_result.recommendations)
            print_progress(f"Compute Engine audit complete: {compute_result.total_count} instances found", done=True)
        except Exception as e:
            print_warning(f"Compute Engine audit failed: {str(e)}")
        
        # Cloud SQL audit
        print_progress("Auditing Cloud SQL instances...")
        try:
            sql_result = self.cloud_sql_auditor.audit_all_instances()
            audit_results["cloud_sql"] = sql_result
            all_recommendations.extend(sql_result.recommendations)
            print_progress(f"Cloud SQL audit complete: {sql_result.total_count} instances found", done=True)
        except Exception as e:
            print_warning(f"Cloud SQL audit failed: {str(e)}")
        
        # Storage audit (disks)
        print_progress("Auditing persistent disks...")
        try:
            zones = []
            for region in self.regions:
                zones.extend([f"{region}-a", f"{region}-b", f"{region}-c"])
            
            disks_result = self.storage_auditor.audit_disks(zones)
            audit_results["persistent_disks"] = disks_result
            all_recommendations.extend(disks_result.recommendations)
            print_progress(f"Disk audit complete: {disks_result.total_count} disks found", done=True)
        except Exception as e:
            print_warning(f"Disk audit failed: {str(e)}")
        
        # Storage audit (static IPs)
        print_progress("Auditing static IP addresses...")
        try:
            ips_result = self.storage_auditor.audit_static_ips(self.regions)
            audit_results["static_ips"] = ips_result
            all_recommendations.extend(ips_result.recommendations)
            print_progress(f"IP audit complete: {ips_result.total_count} IPs found", done=True)
        except Exception as e:
            print_warning(f"IP audit failed: {str(e)}")
        
        print()
        print_progress("Dashboard analysis complete!", done=True)
        print()
        
        # Calculate total savings
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return DashboardData(
            project_id=self.project_id,
            billing_month=datetime.now().strftime("%B %Y"),
            current_month_cost=current_month_cost,
            last_month_cost=last_month_cost,
            ytd_cost=ytd_cost,
            service_costs=service_costs,
            audit_results=audit_results,
            recommendations=all_recommendations,
            total_potential_savings=total_savings,
            hide_project_id=self.hide_project_id,
            budget_alerts=[]  # Will be populated if budget service is used
        )
    
    def add_budget_alerts(self, data: DashboardData) -> DashboardData:
        """Add budget alerts to dashboard data.
        
        Args:
            data: Dashboard data to enhance
            
        Returns:
            Dashboard data with budget alerts
        """
        try:
            billing_account_id = self.budget_service.get_billing_account_id(data.project_id)
            if billing_account_id:
                current_spend = self.bq_spend_service.get_actual_month_spend(data.project_id)
                alerts = self.budget_service.check_budget_breaches(
                    data.project_id,
                    current_spend,
                    billing_account_id
                )
                data.budget_alerts = alerts
        except Exception as e:
            print_warning(f"Failed to fetch budget alerts: {str(e)}")
        
        return data
    
    def run_specific_audit(self, audit_type: str) -> Optional[AuditResult]:
        """Run a specific audit type.
        
        Args:
            audit_type: Type of audit ('cloud_run', 'cloud_functions', 'compute', 'cloud_sql', 'storage')
        
        Returns:
            AuditResult or None if audit type not found
        """
        if audit_type == "cloud_run":
            return self.cloud_run_auditor.audit_all_services(self.regions)
        elif audit_type == "cloud_functions":
            return self.cloud_functions_auditor.audit_all_functions(self.regions)
        elif audit_type == "compute":
            zones = []
            for region in self.regions:
                zones.extend([f"{region}-a", f"{region}-b", f"{region}-c"])
            return self.compute_auditor.audit_all_instances(zones)
        elif audit_type == "cloud_sql":
            return self.cloud_sql_auditor.audit_all_instances()
        elif audit_type == "disks":
            zones = []
            for region in self.regions:
                zones.extend([f"{region}-a", f"{region}-b", f"{region}-c"])
            return self.storage_auditor.audit_disks(zones)
        elif audit_type == "ips":
            return self.storage_auditor.audit_static_ips(self.regions)
        else:
            return None
    
    def run_forecast(self, forecast_days: int = 90, historical_days: int = 180) -> ForecastData:
        """Run cost forecasting analysis.
        
        Args:
            forecast_days: Number of days to forecast into the future
            historical_days: Number of days of historical data to use
        
        Returns:
            ForecastData with cost predictions
        """
        print_progress("Generating cost forecast...")
        
        try:
            forecast_data = self.forecast_service.forecast_costs(
                forecast_days=forecast_days,
                historical_days=historical_days,
                project_id=self.project_id
            )
            
            print_progress("Forecast complete", done=True)
            return forecast_data
            
        except Exception as e:
            print_error(f"Failed to generate forecast: {str(e)}")
            # Return empty forecast data on error
            return ForecastData(
                forecast_points=[],
                total_predicted_cost=0.0,
                forecast_days=forecast_days,
                model_confidence=0.0,
                trend="unknown",
                generated_at=datetime.now().isoformat()
            )
    
    def run_multi_project(
        self,
        projects: Optional[List[str]] = None,
        all_projects: bool = False,
        combine: bool = False
    ) -> MultiProjectDashboardData:
        """Run dashboard analysis for multiple projects.
        
        Args:
            projects: Optional list of project IDs
            all_projects: If True, use all available projects
            combine: If True, group projects by billing account
            
        Returns:
            MultiProjectDashboardData with aggregated results
        """
        print_progress("Initializing multi-project analysis...")
        
        # Initialize projects
        project_groups = self.project_manager.initialize_projects(
            projects=projects,
            all_projects=all_projects,
            combine=combine
        )
        
        if not project_groups:
            raise ValueError("No valid projects found")
        
        # Create project data list
        project_data_list = self.project_manager.create_project_data_list(project_groups)
        
        print_progress(f"Analyzing {len(project_data_list)} project(s)...")
        
        # Process each project
        all_budget_alerts: List[BudgetAlert] = []
        all_audit_results: Dict[str, AuditResult] = {}
        all_recommendations: List[OptimizationRecommendation] = []
        
        # Aggregate costs
        combined_current_month = 0.0
        combined_last_month = 0.0
        combined_ytd = 0.0
        combined_service_costs: Dict[str, float] = {}
        
        for project_data in project_data_list:
            project_id = project_data.project_id
            print_progress(f"Processing project: {project_id}...")
            
            try:
                # Get costs for this project
                project_data.current_month_cost = self.cost_processor.get_current_month_cost(project_id)
                project_data.last_month_cost = self.cost_processor.get_last_month_cost(project_id)
                project_data.ytd_cost = self.cost_processor.get_ytd_cost(project_id)
                
                start_date, end_date = get_current_month_range()
                project_data.service_costs = self.cost_processor.get_service_costs(
                    start_date, end_date, project_id
                )
                
                # Get actual and forecasted spend
                project_data.actual_spend = self.bq_spend_service.get_actual_month_spend(project_id)
                project_data.forecasted_spend = self.bq_spend_service.get_forecast_spend(project_id)
                
                # Get budget alerts
                if project_data.billing_account_id:
                    alerts = self.budget_service.check_budget_breaches(
                        project_id,
                        project_data.actual_spend,
                        project_data.billing_account_id
                    )
                    project_data.budget_alerts = alerts
                    all_budget_alerts.extend(alerts)
                
                # Aggregate costs
                combined_current_month += project_data.current_month_cost
                combined_last_month += project_data.last_month_cost
                combined_ytd += project_data.ytd_cost
                
                for service, cost in project_data.service_costs.items():
                    combined_service_costs[service] = combined_service_costs.get(service, 0.0) + cost
                
                # Run audits for this project (optional - can be expensive)
                # For now, we'll skip individual project audits in multi-project mode
                # to keep it fast. Users can run single-project audits separately.
                
            except Exception as e:
                print_warning(f"Failed to process project {project_id}: {str(e)}")
                continue
        
        print_progress("Multi-project analysis complete!", done=True)
        
        # Sort combined service costs by value
        combined_service_costs = dict(
            sorted(combined_service_costs.items(), key=lambda x: x[1], reverse=True)
        )
        
        return MultiProjectDashboardData(
            projects=project_data_list,
            billing_month=datetime.now().strftime("%B %Y"),
            combined_current_month_cost=combined_current_month,
            combined_last_month_cost=combined_last_month,
            combined_ytd_cost=combined_ytd,
            combined_service_costs=combined_service_costs,
            combined_audit_results=all_audit_results,
            combined_recommendations=all_recommendations,
            total_potential_savings=0.0,  # Will be calculated if audits are run
            all_budget_alerts=all_budget_alerts,
            hide_project_id=self.hide_project_id,
            is_combined=combine
        )
