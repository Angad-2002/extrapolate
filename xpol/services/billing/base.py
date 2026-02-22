"""Base class for BigQuery billing services.

Google Cloud billing export to BigQuery supports two table layouts:
- Daily-sharded: one table per day, e.g. gcp_billing_export_v1_20260201; filter by _TABLE_SUFFIX.
- Single partitioned table: one table per billing account, e.g. gcp_billing_export_v1_0148A9_A6130F_E0294F;
  filter by usage_start_time. This module supports both; detection is by table name format.
"""

from typing import Optional, List
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from xpol.utils.visualizations import print_error


class BaseBillingService:
    """Base class for BigQuery billing export services."""
    
    def __init__(
        self,
        client: bigquery.Client,
        billing_dataset: str,
        billing_table_prefix: str = "gcp_billing_export_v1"
    ):
        """Initialize base billing service.
        
        Args:
            client: BigQuery client
            billing_dataset: Full dataset ID (e.g., 'project.dataset_name')
            billing_table_prefix: For daily-sharded export use 'gcp_billing_export_v1'.
                For a single partitioned table use the full table name, e.g.
                'gcp_billing_export_v1_0148A9_A6130F_E0294F' (billing account ID suffix).
        """
        self.client = client
        self.billing_dataset = billing_dataset
        self.billing_table_prefix = billing_table_prefix

    def _is_single_partitioned_table(self) -> bool:
        """Return True if billing_table_prefix is a full table name (single partitioned table).
        Single partitioned tables have a suffix like billing account ID (e.g. 0148A9_A6130F_E0294F),
        not daily date shards (YYYYMMDD). When True, queries must filter by usage_start_time instead of _TABLE_SUFFIX.
        """
        if not self.billing_table_prefix or not self.billing_table_prefix.startswith("gcp_billing_export_v1_"):
            return False
        suffix = self.billing_table_prefix[len("gcp_billing_export_v1_"):]
        # Daily sharded tables have suffix = 8-digit date (YYYYMMDD)
        if len(suffix) == 8 and suffix.isdigit():
            return False
        return True

    def _get_date_filter_sql(self) -> str:
        """Return the SQL predicate for filtering by date range.
        For daily-sharded tables: _TABLE_SUFFIX BETWEEN @start_date AND @end_date
        For single partitioned table: filter on usage_start_time using same YYYYMMDD params.
        """
        if self._is_single_partitioned_table():
            return "FORMAT_DATE('%Y%m%d', DATE(usage_start_time)) BETWEEN @start_date AND @end_date"
        return "_TABLE_SUFFIX BETWEEN @start_date AND @end_date"
    
    def _build_project_filter(
        self,
        project_id: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
        use_parameter: bool = False
    ) -> tuple:
        """Build project filter clause for BigQuery queries.
        
        Args:
            project_id: Single project ID (optional)
            project_ids: List of project IDs (optional)
            use_parameter: If True, use parameterized query (@project_id), else use string formatting
        
        Returns:
            Tuple of (filter_clause, parameters_list)
            - filter_clause: SQL filter string (e.g., "AND project.id = @project_id" or "AND project.id = 'project-id'")
            - parameters: List of ScalarQueryParameter objects (empty if use_parameter=False)
        """
        parameters = []
        
        if project_ids:
            # Multiple projects - use IN clause
            project_list = "', '".join(project_ids)
            if use_parameter:
                # For parameterized queries, we'd need to use ARRAY, but BigQuery doesn't support
                # array parameters easily, so we'll use string formatting for IN clauses
                return f"""AND project.id IN ('{project_list}')""", []
            else:
                return f"""AND project.id IN ('{project_list}')""", []
        elif project_id:
            # Single project
            if use_parameter:
                parameters.append(
                    bigquery.ScalarQueryParameter("project_id", "STRING", project_id)
                )
                return """AND project.id = @project_id""", parameters
            else:
                return f"""AND project.id = '{project_id}'""", []
        else:
            # No project filter
            return "", []
    
    def _build_date_parameters(
        self,
        start_date: str,
        end_date: str
    ) -> list:
        """Build date parameters for BigQuery queries.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
        
        Returns:
            List of ScalarQueryParameter objects
        """
        return [
            bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
            bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
        ]
    
    def _build_query_job_config(
        self,
        start_date: str,
        end_date: str,
        project_id: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
        additional_parameters: Optional[list] = None,
        use_parameterized_project: bool = False
    ) -> bigquery.QueryJobConfig:
        """Build QueryJobConfig with common parameters.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            project_id: Single project ID (optional)
            project_ids: List of project IDs (optional)
            additional_parameters: Additional query parameters
            use_parameterized_project: Whether to use parameterized project filter
        
        Returns:
            QueryJobConfig object
        """
        parameters = []
        
        # Add date parameters
        parameters.extend(self._build_date_parameters(start_date, end_date))
        
        # Add project filter parameters
        project_filter, project_params = self._build_project_filter(
            project_id=project_id,
            project_ids=project_ids,
            use_parameter=use_parameterized_project
        )
        parameters.extend(project_params)
        
        # Add additional parameters if provided
        if additional_parameters:
            parameters.extend(additional_parameters)
        
        return bigquery.QueryJobConfig(query_parameters=parameters)
    
    def _execute_query(
        self,
        query: str,
        job_config: bigquery.QueryJobConfig,
        error_message: Optional[str] = None
    ):
        """Execute BigQuery query with error handling.
        
        Args:
            query: SQL query string
            job_config: QueryJobConfig object
            error_message: Custom error message (optional)
        
        Returns:
            Query results iterator
        
        Raises:
            Exception: If query execution fails
        """
        try:
            return self.client.query(query, job_config=job_config).result()
        except Exception as e:
            if error_message:
                print_error(error_message.format(str(e)))
            raise
    
    def _get_table_reference(self) -> str:
        """Get BigQuery table reference string.
        
        For daily-sharded export: project.dataset.gcp_billing_export_v1_*
        For single partitioned table: project.dataset.gcp_billing_export_v1_0148A9_A6130F_E0294F (no wildcard)
        
        Returns:
            Table reference string
        """
        if self._is_single_partitioned_table():
            return f"`{self.billing_dataset}.{self.billing_table_prefix}`"
        return f"`{self.billing_dataset}.{self.billing_table_prefix}_*`"
