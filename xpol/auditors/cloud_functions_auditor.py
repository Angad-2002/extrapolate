"""Cloud Functions auditor."""

import logging
from typing import List, Optional
from google.cloud import functions_v2, monitoring_v3
from google.api_core import exceptions

from xpol.types import CloudFunction, CloudFunctionMetrics, OptimizationRecommendation, AuditResult
from xpol.utils.helpers import get_resource_name_from_uri
from xpol.auditors.base import BaseAuditor
from xpol.auditors.constants import (
    COST_ESTIMATES,
    THRESHOLDS,
    MEMORY_OPTIMIZATION,
    CLOUD_FUNCTIONS_DEFAULT_REGIONS
)

logger = logging.getLogger(__name__)


class CloudFunctionsAuditor(BaseAuditor):
    """Audit Cloud Functions for cost optimization.
    
    This auditor analyzes Cloud Functions resources to identify cost optimization
    opportunities, including:
    - Idle functions (zero invocations)
    - Over-provisioned memory allocation
    - High error rates causing wasted invocations
    
    The auditor uses Cloud Monitoring metrics to analyze function usage patterns
    and provides actionable recommendations with estimated savings.
    
    Example:
        ```python
        from google.cloud import functions_v2, monitoring_v3
        
        functions_client = functions_v2.FunctionServiceClient()
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        auditor = CloudFunctionsAuditor(
            functions_client=functions_client,
            monitoring_client=monitoring_client,
            project_id="my-project"
        )
        
        result = auditor.audit_all_functions(regions=["us-central1"])
        print(f"Found {result.total_count} functions")
        print(f"Potential savings: ${result.potential_monthly_savings:.2f}/month")
        ```
    """
    
    def __init__(
        self,
        functions_client: functions_v2.FunctionServiceClient,
        monitoring_client: monitoring_v3.MetricServiceClient,
        project_id: str
    ):
        """Initialize Cloud Functions auditor.
        
        Args:
            functions_client: Cloud Functions API client for listing functions
            monitoring_client: Cloud Monitoring API client for querying metrics.
                Required for detailed analysis.
            project_id: GCP project ID to audit
        
        Raises:
            ValueError: If project_id is invalid (inherited from BaseAuditor)
        """
        super().__init__(project_id, monitoring_client)
        self.functions_client = functions_client
    
    def audit_all_functions(self, regions: Optional[List[str]] = None) -> AuditResult:
        """Audit all Cloud Functions across regions.
        
        Analyzes all Cloud Functions in the specified regions and identifies:
        - Idle functions (no invocations in 30 days)
        - Functions with low memory utilization (< 30% of allocated)
        - Functions with high error rates (> 5%)
        - Untagged functions (missing labels)
        
        Args:
            regions: List of GCP regions to audit (e.g., ["us-central1", "us-east1"]).
                If None, uses default regions from constants.
        
        Returns:
            AuditResult containing:
            - total_count: Total number of functions found
            - untagged_count: Functions without labels
            - idle_count: Functions with zero invocations
            - over_provisioned_count: Functions with low memory utilization
            - recommendations: List of OptimizationRecommendation objects
            - potential_monthly_savings: Total estimated monthly savings (USD)
            - issues: List of any errors encountered during audit
        
        Example:
            ```python
            result = auditor.audit_all_functions(regions=["us-central1"])
            for rec in result.recommendations:
                print(f"{rec.resource_name}: {rec.issue}")
                print(f"  Savings: ${rec.potential_monthly_savings}/month")
            ```
        """
        if regions is None:
            regions = CLOUD_FUNCTIONS_DEFAULT_REGIONS
        
        # Validate regions
        for region in regions:
            self._validate_region(region)
        
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0
        over_provisioned_count = 0
        issues = []
        
        for region in regions:
            try:
                functions = self.list_functions(region)
                total_count += len(functions)
                
                for function in functions:
                    # Check for untagged functions
                    if not function.labels:
                        untagged_count += 1
                    
                    # Get metrics
                    metrics = self.get_function_metrics(function.name, function.region)
                    
                    # Check for idle functions
                    if metrics and metrics.invocations_30d == THRESHOLDS["invocations_idle"]:
                        idle_count += 1
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_function",
                                resource_name=function.name,
                                region=function.region,
                                issue="Unused function (zero invocations in 30 days)",
                                recommendation="Consider deleting this function",
                                potential_monthly_savings=COST_ESTIMATES["cloud_function_idle"],
                                priority="medium",
                                details={"invocations_30d": 0}
                            )
                        )
                    
                    # Check for over-provisioned memory
                    memory_threshold = function.memory_mb * THRESHOLDS["memory_utilization_low"]
                    if metrics and metrics.avg_memory_usage_mb < memory_threshold:
                        over_provisioned_count += 1
                        recommended_mb = max(
                            MEMORY_OPTIMIZATION["minimum_memory_mb"],
                            int(function.memory_mb * MEMORY_OPTIMIZATION["recommended_reduction_factor"])
                        )
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_function",
                                resource_name=function.name,
                                region=function.region,
                                issue=f"Low memory utilization ({metrics.avg_memory_usage_mb:.0f}MB / {function.memory_mb}MB)",
                                recommendation=f"Reduce memory allocation to {recommended_mb}MB",
                                potential_monthly_savings=COST_ESTIMATES["cloud_function_memory_optimization"],
                                priority="low",
                                details={
                                    "current_memory_mb": function.memory_mb,
                                    "recommended_memory_mb": recommended_mb,
                                    "avg_memory_usage_mb": metrics.avg_memory_usage_mb
                                }
                            )
                        )
                    
                    # Check for high error rates
                    if metrics and metrics.invocations_30d > 0:
                        error_rate = (metrics.error_count / metrics.invocations_30d) * 100
                        if error_rate > THRESHOLDS["error_rate_high"]:
                            all_recommendations.append(
                                OptimizationRecommendation(
                                    resource_type="cloud_function",
                                    resource_name=function.name,
                                    region=function.region,
                                    issue=f"High error rate ({error_rate:.1f}%)",
                                    recommendation="Investigate and fix errors to avoid wasted invocations",
                                    potential_monthly_savings=COST_ESTIMATES["cloud_function_error_reduction"],
                                    priority="high",
                                    details={
                                        "error_rate": error_rate,
                                        "error_count": metrics.error_count,
                                        "total_invocations": metrics.invocations_30d
                                    }
                                )
                            )
            
            except exceptions.PermissionDenied as e:
                error_msg = f"Permission denied for region {region}"
                issues.append(error_msg)
                logger.warning(error_msg, extra={"region": region, "project_id": self.project_id})
            except Exception as e:
                error_msg = f"Error auditing region {region}: {str(e)}"
                issues.append(error_msg)
                logger.error(error_msg, exc_info=True, extra={"region": region, "project_id": self.project_id})
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="cloud_functions",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_functions(self, region: str) -> List[CloudFunction]:
        """List all Cloud Functions in a region.
        
        Retrieves all Cloud Functions (Gen 2) from the specified region and
        parses their configuration including memory, timeout, runtime, and labels.
        
        Args:
            region: GCP region identifier (e.g., "us-central1", "europe-west1")
        
        Returns:
            List of CloudFunction objects with parsed configuration.
            Returns empty list if no functions found or region doesn't exist.
        
        Raises:
            ValueError: If region is invalid (from BaseAuditor._validate_region)
            exceptions.PermissionDenied: If insufficient permissions for the region
        
        Example:
            ```python
            functions = auditor.list_functions("us-central1")
            for func in functions:
                print(f"{func.name}: {func.memory_mb}MB, {func.runtime}")
            ```
        """
        self._validate_region(region)
        parent = f"projects/{self.project_id}/locations/{region}"
        functions = []
        
        try:
            for function in self.functions_client.list_functions(parent=parent):
                # Parse function details
                build_config = function.build_config
                service_config = function.service_config
                
                runtime = build_config.runtime if build_config else "unknown"
                memory_mb = 256  # Default
                timeout_seconds = 60  # Default
                
                if service_config:
                    # Parse memory (e.g., "256M", "1G")
                    if service_config.available_memory:
                        memory_str = service_config.available_memory.upper()
                        if memory_str.endswith("G"):
                            memory_mb = int(float(memory_str[:-1]) * 1024)
                        elif memory_str.endswith("M"):
                            memory_mb = int(memory_str[:-1])
                    
                    if service_config.timeout_seconds:
                        timeout_seconds = service_config.timeout_seconds
                
                # Determine trigger type
                trigger_type = "unknown"
                if function.event_trigger:
                    trigger_type = "event"
                elif service_config and service_config.uri:
                    trigger_type = "http"
                
                functions.append(CloudFunction(
                    name=get_resource_name_from_uri(function.name),
                    region=region,
                    runtime=runtime,
                    memory_mb=memory_mb,
                    timeout_seconds=timeout_seconds,
                    labels=dict(function.labels) if function.labels else {},
                    trigger_type=trigger_type,
                    created_time=function.create_time,
                    updated_time=function.update_time
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return functions
    
    def get_function_metrics(
        self,
        function_name: str,
        region: str,
        days: int = 30
    ) -> Optional[CloudFunctionMetrics]:
        """Get metrics for a Cloud Function.
        
        Queries Cloud Monitoring for function metrics over the specified time period.
        Retrieves:
        - Invocation count (total executions)
        - Average execution time
        - Error count
        - Average memory usage
        
        Args:
            function_name: Name of the Cloud Function (without full path)
            region: GCP region where the function is deployed
            days: Number of days of historical data to analyze (default: 30)
        
        Returns:
            CloudFunctionMetrics object containing aggregated metrics, or None if
            metrics cannot be retrieved. Metrics default to 0 if unavailable.
        
        Raises:
            ValueError: If function_name or region is invalid
        
        Note:
            - Requires monitoring_client to be set during initialization
            - Returns metrics with default values (0) if monitoring fails
            - Errors are logged but not raised
        
        Example:
            ```python
            metrics = auditor.get_function_metrics("my-function", "us-central1", days=30)
            if metrics:
                print(f"Invocations: {metrics.invocations_30d}")
                print(f"Error rate: {metrics.error_count / metrics.invocations_30d * 100:.1f}%")
            ```
        """
        if not function_name or not isinstance(function_name, str):
            raise ValueError("function_name must be a non-empty string")
        self._validate_region(region)
        
        interval = self._create_time_interval(days)
        
        metrics_data = {
            "invocations_30d": 0,
            "avg_execution_time_ms": 0.0,
            "error_count": 0,
            "avg_memory_usage_mb": 0.0
        }
        
        resource_labels = {
            "function_name": function_name,
            "region": region
        }
        
        # Get invocation count
        invocations = self._query_metric(
            "cloudfunctions.googleapis.com/function/execution_count",
            "cloud_function",
            resource_labels,
            interval,
            aggregation="sum"
        )
        metrics_data["invocations_30d"] = int(invocations)
        
        # Get execution time
        exec_time = self._query_metric(
            "cloudfunctions.googleapis.com/function/execution_times",
            "cloud_function",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_execution_time_ms"] = exec_time
        
        # Get error count
        errors = self._query_metric(
            "cloudfunctions.googleapis.com/function/execution_count",
            "cloud_function",
            resource_labels,
            interval,
            aggregation="sum",
            filter_str='metric.label.status!="ok"'
        )
        metrics_data["error_count"] = int(errors)
        
        # Get memory usage (if available)
        memory = self._query_metric(
            "cloudfunctions.googleapis.com/function/user_memory_bytes",
            "cloud_function",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_memory_usage_mb"] = memory / (1024 * 1024)  # Convert to MB
        
        return CloudFunctionMetrics(
            function_name=function_name,
            region=region,
            **metrics_data
        )
    

