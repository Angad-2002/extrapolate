"""Cloud SQL auditor."""

import logging
from typing import List, Optional, Any
from google.cloud import monitoring_v3
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from xpol.types import CloudSQLInstance, CloudSQLMetrics, OptimizationRecommendation, AuditResult
from xpol.auditors.base import BaseAuditor
from xpol.auditors.constants import (
    COST_ESTIMATES,
    THRESHOLDS
)

logger = logging.getLogger(__name__)


class CloudSQLAuditor(BaseAuditor):
    """Audit Cloud SQL instances for cost optimization.
    
    This auditor analyzes Cloud SQL database instances to identify cost optimization
    opportunities, including:
    - Stopped instances still incurring costs
    - Idle instances with very low connection counts
    - Over-provisioned instances with low CPU utilization
    
    The auditor uses Cloud Monitoring metrics to analyze database usage patterns
    and provides actionable recommendations with estimated savings.
    
    Example:
        ```python
        from googleapiclient.discovery import build
        from google.cloud import monitoring_v3
        
        sql_client = build('sqladmin', 'v1')
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        auditor = CloudSQLAuditor(
            cloud_sql_client=sql_client,
            monitoring_client=monitoring_client,
            project_id="my-project"
        )
        
        result = auditor.audit_all_instances()
        ```
    """
    
    def __init__(
        self,
        cloud_sql_client: Resource,
        monitoring_client: monitoring_v3.MetricServiceClient,
        project_id: str
    ):
        """Initialize Cloud SQL auditor.
        
        Args:
            cloud_sql_client: Cloud SQL Admin API client (Discovery API) for listing instances
            monitoring_client: Cloud Monitoring API client for querying metrics.
                Required for detailed analysis.
            project_id: GCP project ID to audit
        
        Raises:
            ValueError: If project_id is invalid (inherited from BaseAuditor)
        """
        super().__init__(project_id, monitoring_client)
        self.cloud_sql_client = cloud_sql_client
    
    def audit_all_instances(self) -> AuditResult:
        """Audit all Cloud SQL instances.
        
        Returns:
            AuditResult with findings and recommendations
        """
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0
        over_provisioned_count = 0
        issues = []
        
        try:
            instances = self.list_instances()
            total_count = len(instances)
            
            for instance in instances:
                # Check for untagged instances
                if not instance.labels:
                    untagged_count += 1
                
                # Check for stopped instances
                if instance.state != "RUNNABLE":
                    idle_count += 1
                    all_recommendations.append(
                        OptimizationRecommendation(
                            resource_type="cloud_sql",
                            resource_name=instance.name,
                            region=instance.region,
                            issue=f"Instance is in {instance.state} state",
                            recommendation="Delete if no longer needed",
                            potential_monthly_savings=COST_ESTIMATES["cloud_sql_stopped"],
                            priority="medium",
                            details={"state": instance.state}
                        )
                    )
                
                # Get metrics
                metrics = self.get_instance_metrics(instance.name)
                
                # Check for low connection count
                if metrics and metrics.avg_connections_30d < THRESHOLDS["connection_count_idle"]:
                    idle_count += 1
                    all_recommendations.append(
                        OptimizationRecommendation(
                            resource_type="cloud_sql",
                            resource_name=instance.name,
                            region=instance.region,
                            issue="Very low connection count (avg < 1)",
                            recommendation="Consider deleting or stopping this instance",
                            potential_monthly_savings=COST_ESTIMATES["cloud_sql_idle"],
                            priority="high",
                            details={"avg_connections_30d": metrics.avg_connections_30d}
                        )
                    )
                
                # Check for low CPU utilization
                if metrics and metrics.avg_cpu_utilization < THRESHOLDS["cpu_utilization_low"]:
                    over_provisioned_count += 1
                    all_recommendations.append(
                        OptimizationRecommendation(
                            resource_type="cloud_sql",
                            resource_name=instance.name,
                            region=instance.region,
                            issue=f"Low CPU utilization ({metrics.avg_cpu_utilization:.1f}%)",
                            recommendation="Consider downsizing to a smaller machine type",
                            potential_monthly_savings=COST_ESTIMATES["cloud_sql_downsizing"],
                            priority="medium",
                            details={
                                "current_tier": instance.tier,
                                "avg_cpu_utilization": metrics.avg_cpu_utilization
                            }
                        )
                    )
        
        except HttpError as e:
            if e.resp.status == 403:
                error_msg = "Permission denied to list Cloud SQL instances"
                issues.append(error_msg)
                logger.warning(error_msg, extra={"project_id": self.project_id})
            else:
                error_msg = f"HTTP Error auditing Cloud SQL: {str(e)}"
                issues.append(error_msg)
                logger.error(error_msg, exc_info=True, extra={"project_id": self.project_id, "status": e.resp.status})
        except Exception as e:
            error_msg = f"Error auditing Cloud SQL: {str(e)}"
            issues.append(error_msg)
            logger.error(error_msg, exc_info=True, extra={"project_id": self.project_id})
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="cloud_sql",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_instances(self) -> List[CloudSQLInstance]:
        """List all Cloud SQL instances in the project.
        
        Returns:
            List of CloudSQLInstance objects
        """
        instances = []
        
        try:
            # Use Discovery API to list instances
            request = self.cloud_sql_client.instances().list(project=self.project_id)
            response = request.execute()
            
            if 'items' in response:
                for instance in response['items']:
                    # Get storage size
                    storage_gb = 10  # Default
                    if 'settings' in instance and 'dataDiskSizeGb' in instance['settings']:
                        storage_gb = int(instance['settings']['dataDiskSizeGb'])
                    
                    # Get tier/machine type
                    tier = "unknown"
                    if 'settings' in instance and 'tier' in instance['settings']:
                        tier = instance['settings']['tier']
                    
                    # Get labels
                    labels = {}
                    if 'settings' in instance and 'userLabels' in instance['settings']:
                        labels = instance['settings']['userLabels']
                    
                    instances.append(CloudSQLInstance(
                        name=instance.get('name', 'unknown'),
                        region=instance.get('region', 'unknown'),
                        database_version=instance.get('databaseVersion', 'unknown'),
                        tier=tier,
                        state=instance.get('state', 'UNKNOWN'),
                        labels=labels,
                        storage_gb=storage_gb,
                        created_time=None
                    ))
        
        except HttpError as e:
            if e.resp.status == 403:
                raise
        
        return instances
    
    def get_instance_metrics(
        self,
        instance_name: str,
        days: int = 30
    ) -> Optional[CloudSQLMetrics]:
        """Get metrics for a Cloud SQL instance.
        
        Args:
            instance_name: Instance name
            days: Number of days to look back
        
        Returns:
            CloudSQLMetrics object or None
        """
        if not instance_name or not isinstance(instance_name, str):
            raise ValueError("instance_name must be a non-empty string")
        
        interval = self._create_time_interval(days)
        
        metrics_data = {
            "avg_connections_30d": 0.0,
            "avg_cpu_utilization": 0.0,
            "avg_memory_utilization": 0.0,
            "query_count_30d": 0
        }
        
        resource_labels = {
            "database_id": f"{self.project_id}:{instance_name}"
        }
        
        # Get connection count
        connections = self._query_metric(
            "cloudsql.googleapis.com/database/network/connections",
            "cloudsql_database",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_connections_30d"] = connections
        
        # Get CPU utilization
        cpu = self._query_metric(
            "cloudsql.googleapis.com/database/cpu/utilization",
            "cloudsql_database",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_cpu_utilization"] = cpu * 100  # Convert to percentage
        
        # Get memory utilization
        memory = self._query_metric(
            "cloudsql.googleapis.com/database/memory/utilization",
            "cloudsql_database",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_memory_utilization"] = memory * 100  # Convert to percentage
        
        return CloudSQLMetrics(
            instance_name=instance_name,
            region="unknown",
            **metrics_data
        )
