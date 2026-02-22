"""BigQuery cost processor for billing data analysis."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from google.cloud import bigquery
import pandas as pd

from xpol.types import CostData
from xpol.utils.helpers import (
    get_current_month_range,
    get_last_month_range,
    get_date_range
)
from xpol.services.billing.base import BaseBillingService


class CostProcessor(BaseBillingService):
    """Process cost data from BigQuery billing export."""
    
    def get_current_month_cost(self, project_id: Optional[str] = None) -> float:
        """Get total cost for current month.
        
        Args:
            project_id: Filter by project ID (optional)
        
        Returns:
            Total cost for current month
        """
        start_date, end_date = get_current_month_range()
        return self._get_total_cost(start_date, end_date, project_id)
    
    def get_last_month_cost(self, project_id: Optional[str] = None) -> float:
        """Get total cost for last month.
        
        Args:
            project_id: Filter by project ID (optional)
        
        Returns:
            Total cost for last month
        """
        start_date, end_date = get_last_month_range()
        return self._get_total_cost(start_date, end_date, project_id)
    
    def get_ytd_cost(self, project_id: Optional[str] = None) -> float:
        """Get year-to-date total cost.
        
        Args:
            project_id: Filter by project ID (optional)
        
        Returns:
            YTD total cost
        """
        year_start = datetime.now().replace(month=1, day=1).strftime("%Y%m%d")
        today = datetime.now().strftime("%Y%m%d")
        return self._get_total_cost(year_start, today, project_id)
    
    def get_service_costs(
        self,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None,
        top_n: int = 10
    ) -> Dict[str, float]:
        """Get cost breakdown by service.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
            top_n: Return top N services by cost
        
        Returns:
            Dictionary of service name to cost
        """
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                service.description as service_name,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            {project_filter}
            GROUP BY service_name
            ORDER BY total_cost DESC
            LIMIT {top_n}
        """
        
        job_config = self._build_query_job_config(start_date, end_date, project_id=project_id)
        
        results = self.client.query(query, job_config=job_config).result()
        
        return {row.service_name: float(row.total_cost) for row in results}
    
    def get_service_cost_trend(
        self,
        service_name: str,
        months: int = 6,
        project_id: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Get monthly cost trend for a service.
        
        Args:
            service_name: Service name (e.g., 'Cloud Run')
            months: Number of months to look back
            project_id: Filter by project ID (optional)
        
        Returns:
            List of (month, cost) tuples
        """
        start_date, end_date = get_date_range(months)
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                FORMAT_DATE('%Y-%m', DATE(usage_start_time)) as month,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            AND service.description = @service_name
            {project_filter}
            GROUP BY month
            ORDER BY month
        """
        
        job_config = self._build_query_job_config(
            start_date,
            end_date,
            project_id=project_id,
            additional_parameters=[
                bigquery.ScalarQueryParameter("service_name", "STRING", service_name)
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        
        return [(row.month, float(row.total_cost)) for row in results]
    
    def get_monthly_cost_trend(
        self,
        months: int = 6,
        project_id: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Get monthly cost trend for all services.
        
        Args:
            months: Number of months to look back (default: 6)
            project_id: Filter by project ID (optional)
        
        Returns:
            List of (month, cost) tuples where month is in 'YYYY-MM' format
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        # Calculate date range
        today = datetime.now()
        start_date = (today - relativedelta(months=months)).replace(day=1)
        end_date = today
        
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                FORMAT_DATE('%Y-%m', DATE(usage_start_time)) as month,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            {project_filter}
            GROUP BY month
            ORDER BY month
        """
        
        job_config = self._build_query_job_config(start_date_str, end_date_str, project_id=project_id)
        
        results = self.client.query(query, job_config=job_config).result()
        
        # Convert to list of tuples and format month nicely
        monthly_costs = []
        for row in results:
            # Convert 'YYYY-MM' to 'MMM YYYY' format (e.g., '2024-01' -> 'Jan 2024')
            month_str = datetime.strptime(row.month, "%Y-%m").strftime("%b %Y")
            monthly_costs.append((month_str, float(row.total_cost)))
        
        return monthly_costs
    
    def get_cloud_run_costs(
        self,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None
    ) -> Dict[str, float]:
        """Get Cloud Run cost breakdown by service.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
        
        Returns:
            Dictionary of service name to cost
        """
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                labels.value as service_name,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()},
            UNNEST(CAST(labels AS ARRAY<STRUCT<key STRING, value STRING>>)) as labels
            WHERE {self._get_date_filter_sql()}
            AND (
                JSON_EXTRACT_SCALAR(service, '$.description') = 'Cloud Run' OR
                CAST(service AS STRING) LIKE '%Cloud Run%'
            )
            AND labels.key = 'service_name'
            {project_filter}
            GROUP BY service_name
            ORDER BY total_cost DESC
        """
        
        job_config = self._build_query_job_config(start_date, end_date, project_id=project_id)
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            return {row.service_name: float(row.total_cost) for row in results}
        except Exception:
            # If service_name label doesn't exist, return empty dict
            return {}
    
    def get_sku_costs(
        self,
        service_name: str,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None,
        top_n: int = 10
    ) -> List[CostData]:
        """Get SKU-level cost breakdown for a service.
        
        Args:
            service_name: Service name (e.g., 'Cloud Run')
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
            top_n: Return top N SKUs by cost
        
        Returns:
            List of CostData objects
        """
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                service.description as service_name,
                sku.description as sku_name,
                SUM(cost) as total_cost,
                SUM(usage.amount) as usage_amount,
                usage.unit as usage_unit,
                project.id as project_id,
                location.region as region
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            AND service.description = @service_name
            {project_filter}
            GROUP BY service_name, sku_name, usage_unit, project_id, region
            ORDER BY total_cost DESC
            LIMIT {top_n}
        """
        
        job_config = self._build_query_job_config(
            start_date,
            end_date,
            project_id=project_id,
            additional_parameters=[
                bigquery.ScalarQueryParameter("service_name", "STRING", service_name)
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        
        cost_data = []
        for row in results:
            cost_data.append(CostData(
                service=row.service_name,
                sku=row.sku_name,
                cost=float(row.total_cost),
                usage_amount=float(row.usage_amount),
                usage_unit=row.usage_unit,
                project_id=row.project_id,
                region=row.region,
            ))
        
        return cost_data
    
    def _get_total_cost(
        self,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None
    ) -> float:
        """Get total cost for a date range.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Filter by project ID (optional)
        
        Returns:
            Total cost
        """
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            {project_filter}
        """
        
        job_config = self._build_query_job_config(start_date, end_date, project_id=project_id)
        
        results = self.client.query(query, job_config=job_config).result()
        
        for row in results:
            return float(row.total_cost) if row.total_cost else 0.0
        
        return 0.0
    
    def get_multi_project_current_month_cost(self, project_ids: List[str]) -> float:
        """Get aggregated current month cost for multiple projects.
        
        Args:
            project_ids: List of project IDs
            
        Returns:
            Total current month cost across all projects
        """
        start_date, end_date = get_current_month_range()
        return self._get_multi_project_total_cost(start_date, end_date, project_ids)
    
    def get_multi_project_last_month_cost(self, project_ids: List[str]) -> float:
        """Get aggregated last month cost for multiple projects.
        
        Args:
            project_ids: List of project IDs
            
        Returns:
            Total last month cost across all projects
        """
        start_date, end_date = get_last_month_range()
        return self._get_multi_project_total_cost(start_date, end_date, project_ids)
    
    def get_multi_project_ytd_cost(self, project_ids: List[str]) -> float:
        """Get aggregated year-to-date cost for multiple projects.
        
        Args:
            project_ids: List of project IDs
            
        Returns:
            Total YTD cost across all projects
        """
        year_start = datetime.now().replace(month=1, day=1).strftime("%Y%m%d")
        today = datetime.now().strftime("%Y%m%d")
        return self._get_multi_project_total_cost(year_start, today, project_ids)
    
    def get_multi_project_service_costs(
        self,
        project_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        top_n: int = 10
    ) -> Dict[str, float]:
        """Get aggregated service costs for multiple projects.
        
        Args:
            project_ids: List of project IDs
            start_date: Start date in YYYYMMDD format (defaults to current month start)
            end_date: End date in YYYYMMDD format (defaults to current month end)
            top_n: Return top N services by cost
            
        Returns:
            Dictionary of service name to aggregated cost
        """
        if start_date is None or end_date is None:
            start_date, end_date = get_current_month_range()
        
        # Build project filter
        project_filter, _ = self._build_project_filter(project_ids=project_ids)
        
        query = f"""
            SELECT 
                service.description as service_name,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            {project_filter}
            GROUP BY service_name
            ORDER BY total_cost DESC
            LIMIT {top_n}
        """
        
        job_config = self._build_query_job_config(start_date, end_date, project_ids=project_ids)
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            return {row.service_name: float(row.total_cost) for row in results}
        except Exception as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Failed to get multi-project service costs: {str(e)}")
            return {}
    
    def _get_multi_project_total_cost(
        self,
        start_date: str,
        end_date: str,
        project_ids: List[str]
    ) -> float:
        """Get total cost for multiple projects in a date range.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_ids: List of project IDs
            
        Returns:
            Total cost across all projects
        """
        if not project_ids:
            return 0.0
        
        # Build project filter
        project_filter, _ = self._build_project_filter(project_ids=project_ids)
        
        query = f"""
            SELECT 
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            {project_filter}
        """
        
        job_config = self._build_query_job_config(start_date, end_date, project_ids=project_ids)
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            for row in results:
                return float(row.total_cost) if row.total_cost else 0.0
        except Exception as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Failed to get multi-project total cost: {str(e)}")
        
        return 0.0
