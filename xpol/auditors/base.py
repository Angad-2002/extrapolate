"""Base auditor class with common patterns.

This module provides a base class for all GCP resource auditors, containing
common functionality such as:
- Input validation for regions, zones, and project IDs
- Time interval creation for metrics queries
- Metric querying with retry logic and error handling
- Structured logging for audit operations

All auditor classes should inherit from BaseAuditor to ensure consistent
behavior and reduce code duplication.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from google.cloud import monitoring_v3
from google.api_core import exceptions, retry
from google.api_core.retry import Retry

logger = logging.getLogger(__name__)


class BaseAuditor:
    """Base class for GCP resource auditors.
    
    This class provides common functionality for auditing GCP resources,
    including:
    - Input validation (regions, zones, project IDs)
    - Time interval creation for metrics queries
    - Metric querying with automatic retry logic
    - Structured error logging
    
    Subclasses should implement resource-specific audit logic while
    leveraging these common utilities.
    
    Example:
        ```python
        class MyAuditor(BaseAuditor):
            def __init__(self, client, monitoring_client, project_id):
                super().__init__(project_id, monitoring_client)
                self.client = client
            
            def audit_resources(self, regions=None):
                # Use self._validate_region(), self._query_metric(), etc.
                pass
        ```
    """
    
    def __init__(self, project_id: str, monitoring_client: Optional[monitoring_v3.MetricServiceClient] = None):
        """Initialize base auditor.
        
        Args:
            project_id: GCP project ID (must be non-empty string)
            monitoring_client: Cloud Monitoring API client (optional).
                If None, metric queries will return 0.0
        
        Raises:
            ValueError: If project_id is empty or not a string
        
        Example:
            ```python
            auditor = BaseAuditor(
                project_id="my-project-id",
                monitoring_client=monitoring_client
            )
            ```
        """
        if not project_id or not isinstance(project_id, str):
            raise ValueError("project_id must be a non-empty string")
        
        self.project_id = project_id
        self.monitoring_client = monitoring_client
    
    def _validate_region(self, region: str) -> None:
        """Validate region parameter.
        
        Ensures the region is a non-empty string. This validation helps
        prevent invalid API calls that would fail at runtime.
        
        Args:
            region: GCP region string (e.g., "us-central1", "europe-west1")
        
        Raises:
            ValueError: If region is empty, None, or not a string
        
        Example:
            ```python
            self._validate_region("us-central1")  # OK
            self._validate_region("")  # Raises ValueError
            ```
        """
        if not region or not isinstance(region, str):
            raise ValueError("region must be a non-empty string")
    
    def _validate_zone(self, zone: str) -> None:
        """Validate zone parameter.
        
        Ensures the zone is a non-empty string. Zones are more specific
        than regions (e.g., "us-central1-a" vs "us-central1").
        
        Args:
            zone: GCP zone string (e.g., "us-central1-a", "europe-west1-b")
        
        Raises:
            ValueError: If zone is empty, None, or not a string
        
        Example:
            ```python
            self._validate_zone("us-central1-a")  # OK
            self._validate_zone(None)  # Raises ValueError
            ```
        """
        if not zone or not isinstance(zone, str):
            raise ValueError("zone must be a non-empty string")
    
    def _create_time_interval(self, days: int = 30) -> monitoring_v3.TimeInterval:
        """Create time interval for metrics queries.
        
        Creates a TimeInterval object suitable for Cloud Monitoring API queries.
        The interval spans from (now - days) to now, using UTC timezone.
        
        Args:
            days: Number of days to look back (must be positive)
        
        Returns:
            TimeInterval object with start_time and end_time in seconds since epoch
        
        Raises:
            ValueError: If days is not positive
        
        Example:
            ```python
            interval = self._create_time_interval(days=30)
            # Returns interval covering last 30 days
            ```
        """
        if days <= 0:
            raise ValueError("days must be positive")
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        return monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())},
            }
        )
    
    @retry.Retry(
        predicate=retry.if_exception_type(
            exceptions.ServiceUnavailable,
            exceptions.InternalServerError,
            exceptions.DeadlineExceeded
        ),
        initial=1.0,
        maximum=10.0,
        multiplier=2.0,
        deadline=60.0
    )
    def _query_metric(
        self,
        metric_type: str,
        resource_type: str,
        resource_labels: dict,
        interval: monitoring_v3.TimeInterval,
        aggregation: str = "mean",
        filter_str: str = ""
    ) -> float:
        """Query a metric from Cloud Monitoring with retry logic.
        
        This method queries Cloud Monitoring for a specific metric with automatic
        retry on transient failures. It handles:
        - Building filter queries from resource labels
        - Creating aggregation objects
        - Executing queries with retry logic
        - Aggregating results across all data points
        - Error handling and logging
        
        The method uses exponential backoff retry for transient errors:
        - Initial delay: 1 second
        - Maximum delay: 10 seconds
        - Multiplier: 2.0 (doubles each retry)
        - Deadline: 60 seconds total
        
        Args:
            metric_type: Full metric type path (e.g., 'run.googleapis.com/request_count',
                'cloudfunctions.googleapis.com/function/execution_count')
            resource_type: Resource type identifier (e.g., 'cloud_run_revision',
                'cloud_function', 'cloudsql_database')
            resource_labels: Dictionary mapping label keys to values.
                Example: {"service_name": "my-service", "location": "us-central1"}
            interval: TimeInterval object defining the time range for the query
            aggregation: Aggregation method - 'mean', 'sum', 'max', 'min', etc.
                Defaults to 'mean'. Case-insensitive.
            filter_str: Optional additional filter string to append to the query.
                Example: 'metric.label.status!="ok"'
        
        Returns:
            Aggregated metric value as float. Returns 0.0 if:
            - No monitoring client is available
            - No data points are found
            - An error occurs (logged but not raised)
        
        Raises:
            No exceptions are raised - all errors are logged and return 0.0
        
        Example:
            ```python
            interval = self._create_time_interval(days=30)
            resource_labels = {
                "service_name": "my-service",
                "location": "us-central1"
            }
            request_count = self._query_metric(
                metric_type="run.googleapis.com/request_count",
                resource_type="cloud_run_revision",
                resource_labels=resource_labels,
                interval=interval,
                aggregation="sum"
            )
            ```
        
        Note:
            - Permission errors are logged as warnings and return 0.0
            - Not found errors are logged as debug and return 0.0
            - Other errors are logged as errors with full traceback
        """
        if not self.monitoring_client:
            logger.warning("Monitoring client not available, returning 0.0")
            return 0.0
        
        try:
            # Build filter query
            filter_parts = [
                f'resource.type="{resource_type}"',
                f'metric.type="{metric_type}"'
            ]
            
            # Add resource labels
            for key, value in resource_labels.items():
                filter_parts.append(f'resource.labels.{key}="{value}"')
            
            if filter_str:
                filter_parts.append(filter_str)
            
            filter_query = " AND ".join(filter_parts)
            
            # Create aggregation object
            # Some metrics (DELTA + DISTRIBUTION type) cannot use ALIGN_MEAN
            # Cloud Run metrics like cpu/utilizations, memory/utilizations, and request_latencies
            # are DELTA + DISTRIBUTION and require ALIGN_DELTA instead
            distribution_metrics = [
                "run.googleapis.com/container/cpu/utilizations",
                "run.googleapis.com/container/memory/utilizations",
                "run.googleapis.com/request_latencies",
            ]
            
            if metric_type in distribution_metrics:
                # Force ALIGN_DELTA for DELTA + DISTRIBUTION metrics
                aligner = monitoring_v3.Aggregation.Aligner.ALIGN_DELTA
            else:
                try:
                    aligner = getattr(
                        monitoring_v3.Aggregation.Aligner,
                        f"ALIGN_{aggregation.upper()}"
                    )
                except AttributeError:
                    logger.warning(f"Unknown aggregation '{aggregation}', using ALIGN_MEAN")
                    aligner = monitoring_v3.Aggregation.Aligner.ALIGN_MEAN
            
            aggregation_obj = monitoring_v3.Aggregation(
                {
                    "alignment_period": {"seconds": 3600},  # 1 hour
                    "per_series_aligner": aligner,
                }
            )
            
            # Create request
            request = monitoring_v3.ListTimeSeriesRequest(
                {
                    "name": f"projects/{self.project_id}",
                    "filter": filter_query,
                    "interval": interval,
                    "aggregation": aggregation_obj,
                }
            )
            
            # Execute query
            results = self.monitoring_client.list_time_series(request=request)
            
            # Aggregate results
            total = 0.0
            count = 0
            
            for result in results:
                for point in result.points:
                    if hasattr(point.value, 'double_value'):
                        total += point.value.double_value
                        count += 1
                    elif hasattr(point.value, 'int64_value'):
                        total += point.value.int64_value
                        count += 1
                    elif hasattr(point.value, 'distribution_value'):
                        # For distribution metrics, extract the mean
                        dist = point.value.distribution_value
                        if dist.count > 0:
                            total += dist.mean
                            count += 1
            
            if count > 0:
                return total / count
            else:
                logger.debug(f"No data points found for metric {metric_type}")
                return 0.0
                
        except exceptions.PermissionDenied as e:
            logger.warning(f"Permission denied querying metric {metric_type}: {str(e)}")
            return 0.0
        except exceptions.NotFound as e:
            logger.debug(f"Metric {metric_type} not found: {str(e)}")
            return 0.0
        except Exception as e:
            logger.error(
                f"Error querying metric {metric_type}: {str(e)}",
                exc_info=True,
                extra={
                    "metric_type": metric_type,
                    "resource_type": resource_type,
                    "project_id": self.project_id
                }
            )
            return 0.0
