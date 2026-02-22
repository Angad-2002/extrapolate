"""BigQuery spend service for actual and forecasted spend evaluation."""

from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from google.cloud import bigquery
import pandas as pd

from xpol.utils.helpers import get_current_month_range
from xpol.utils.visualizations import print_error
from xpol.services.billing.base import BaseBillingService


class BQSpendService(BaseBillingService):
    """Service for querying actual and forecasted spend from BigQuery billing export."""
    
    def get_actual_month_spend(self, project_id: str) -> float:
        """Get actual spend for current month from billing export.
        
        Args:
            project_id: GCP project ID
            
        Returns:
            Actual spend for current month
        """
        start_date, end_date = get_current_month_range()
        
        query = f"""
            SELECT 
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            AND project.id = @project_id
        """
        
        job_config = self._build_query_job_config(
            start_date,
            end_date,
            project_id=project_id,
            use_parameterized_project=True
        )
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            for row in results:
                return float(row.total_cost) if row.total_cost else 0.0
        except Exception as e:
            print_error(f"Failed to get actual spend for {project_id}: {str(e)}")
            return 0.0
        
        return 0.0
    
    def get_forecast_spend(
        self,
        project_id: str,
        days_ahead: int = 30
    ) -> float:
        """Get forecasted spend for the rest of the month.
        
        This uses a simple linear projection based on current month's daily average.
        
        Args:
            project_id: GCP project ID
            days_ahead: Number of days to forecast (default: 30 for end of month)
            
        Returns:
            Forecasted spend for the period
        """
        start_date, end_date = get_current_month_range()
        
        # Get current spend and days elapsed
        today = datetime.now()
        month_start = datetime.strptime(start_date, "%Y%m%d")
        days_elapsed = (today - month_start).days + 1
        total_days_in_month = (datetime.strptime(end_date, "%Y%m%d") - month_start).days + 1
        
        # Get current spend
        current_spend = self.get_actual_month_spend(project_id)
        
        if days_elapsed <= 0:
            return 0.0
        
        # Calculate daily average
        daily_average = current_spend / days_elapsed
        
        # Forecast for remaining days
        days_remaining = min(days_ahead, total_days_in_month - days_elapsed)
        if days_remaining <= 0:
            return current_spend
        
        forecasted_spend = current_spend + (daily_average * days_remaining)
        
        return forecasted_spend
    
    def get_servicewise_breakdown(
        self,
        project_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, float]:
        """Get cost breakdown by service for a project.
        
        Args:
            project_id: GCP project ID
            start_date: Start date in YYYYMMDD format (defaults to current month start)
            end_date: End date in YYYYMMDD format (defaults to current month end)
            
        Returns:
            Dictionary mapping service name to cost
        """
        if start_date is None or end_date is None:
            start_date, end_date = get_current_month_range()
        
        query = f"""
            SELECT 
                service.description as service_name,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            AND project.id = @project_id
            GROUP BY service_name
            ORDER BY total_cost DESC
        """
        
        job_config = self._build_query_job_config(
            start_date,
            end_date,
            project_id=project_id,
            use_parameterized_project=True
        )
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            return {row.service_name: float(row.total_cost) for row in results}
        except Exception as e:
            print_error(f"Failed to get service breakdown for {project_id}: {str(e)}")
            return {}
    
    def get_daily_spend_trend(
        self,
        project_id: str,
        days: int = 30
    ) -> List[Tuple[str, float]]:
        """Get daily spend trend for a project.
        
        Args:
            project_id: GCP project ID
            days: Number of days to look back
            
        Returns:
            List of (date, cost) tuples
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        
        query = f"""
            SELECT 
                DATE(usage_start_time) as usage_date,
                SUM(cost) as daily_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            AND project.id = @project_id
            GROUP BY usage_date
            ORDER BY usage_date
        """
        
        job_config = self._build_query_job_config(
            start_date_str,
            end_date_str,
            project_id=project_id,
            use_parameterized_project=True
        )
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            return [
                (row.usage_date.strftime("%Y-%m-%d"), float(row.daily_cost))
                for row in results
            ]
        except Exception as e:
            print_error(f"Failed to get daily spend trend for {project_id}: {str(e)}")
            return []
    
    def get_multi_project_spend(
        self,
        project_ids: List[str]
    ) -> Dict[str, float]:
        """Get actual spend for multiple projects.
        
        Args:
            project_ids: List of project IDs
            
        Returns:
            Dictionary mapping project ID to actual spend
        """
        start_date, end_date = get_current_month_range()
        
        # Build project filter
        project_filter, _ = self._build_project_filter(project_ids=project_ids)
        
        query = f"""
            SELECT 
                project.id as project_id,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            {project_filter}
            GROUP BY project_id
        """
        
        job_config = self._build_query_job_config(start_date, end_date, project_ids=project_ids)
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            return {row.project_id: float(row.total_cost) for row in results}
        except Exception as e:
            print_error(f"Failed to get multi-project spend: {str(e)}")
            return {pid: 0.0 for pid in project_ids}
