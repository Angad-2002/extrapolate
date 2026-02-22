"""Cloud Run resource auditor."""

import logging
from typing import List, Dict, Optional
from google.cloud import run_v2, monitoring_v3
from google.api_core import exceptions

from xpol.types import (
    CloudRunService,
    CloudRunMetrics,
    OptimizationRecommendation,
    AuditResult
)
from xpol.utils.helpers import parse_memory_string, format_memory_mb, get_resource_name_from_uri
from xpol.auditors.base import BaseAuditor
from xpol.auditors.constants import (
    COST_ESTIMATES,
    THRESHOLDS,
    MEMORY_OPTIMIZATION,
    DEFAULT_REGIONS
)

logger = logging.getLogger(__name__)


class CloudRunAuditor(BaseAuditor):
    """Audit Cloud Run services for cost optimization.
    
    This auditor analyzes Cloud Run services to identify cost optimization
    opportunities, including:
    - Idle services (zero requests)
    - Services with CPU always allocated but low utilization
    - Services with low memory utilization
    - Services with unnecessary minimum instances
    
    The auditor uses Cloud Monitoring metrics to analyze service usage patterns
    and provides actionable recommendations with estimated savings.
    
    Example:
        ```python
        from google.cloud import run_v2, monitoring_v3
        
        run_client = run_v2.ServicesClient()
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        auditor = CloudRunAuditor(
            cloud_run_client=run_client,
            monitoring_client=monitoring_client,
            project_id="my-project"
        )
        
        result = auditor.audit_all_services(regions=["us-central1"])
        ```
    """
    
    def __init__(
        self,
        cloud_run_client: run_v2.ServicesClient,
        monitoring_client: monitoring_v3.MetricServiceClient,
        project_id: str
    ):
        """Initialize Cloud Run auditor.
        
        Args:
            cloud_run_client: Cloud Run API client for listing services
            monitoring_client: Cloud Monitoring API client for querying metrics.
                Required for detailed analysis.
            project_id: GCP project ID to audit
        
        Raises:
            ValueError: If project_id is invalid (inherited from BaseAuditor)
        """
        super().__init__(project_id, monitoring_client)
        self.cloud_run_client = cloud_run_client
    
    def audit_all_services(self, regions: Optional[List[str]] = None) -> AuditResult:
        """Audit all Cloud Run services across regions.
        
        Args:
            regions: List of regions to audit (default: all common regions)
        
        Returns:
            AuditResult with findings and recommendations
        """
        if regions is None:
            regions = DEFAULT_REGIONS
        
        # Validate regions
        for region in regions:
            self._validate_region(region)
        
        all_services = []
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0
        over_provisioned_count = 0
        issues = []
        
        for region in regions:
            try:
                services = self.list_services(region)
                total_count += len(services)
                
                for service in services:
                    # Check for untagged services
                    if not service.labels:
                        untagged_count += 1
                    
                    # Get metrics
                    metrics = self.get_service_metrics(service.name, service.region)
                    
                    # Check for idle services
                    if metrics and metrics.request_count_30d == THRESHOLDS["requests_idle"]:
                        idle_count += 1
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_run",
                                resource_name=service.name,
                                region=service.region,
                                issue="Idle service (zero requests in 30 days)",
                                recommendation="Consider deleting or archiving this service",
                                potential_monthly_savings=COST_ESTIMATES["cloud_run_idle"],
                                priority="medium",
                                details={"request_count_30d": 0}
                            )
                        )
                    
                    # Check for over-provisioned resources
                    if metrics:
                        # Check CPU allocation
                        if (service.cpu_allocated == "1" and  # "always" allocated
                            metrics.avg_cpu_utilization < THRESHOLDS["cpu_utilization_low"]):
                            over_provisioned_count += 1
                            all_recommendations.append(
                                OptimizationRecommendation(
                                    resource_type="cloud_run",
                                    resource_name=service.name,
                                    region=service.region,
                                    issue=f"CPU allocated 'always' but usage only {metrics.avg_cpu_utilization:.1f}%",
                                    recommendation="Change CPU allocation to 'request-only' (CPU throttling)",
                                    potential_monthly_savings=COST_ESTIMATES["cloud_run_cpu_optimization"],
                                    priority="high",
                                    details={
                                        "current_allocation": "always",
                                        "avg_cpu_utilization": metrics.avg_cpu_utilization
                                    }
                                )
                            )
                        
                        # Check memory allocation
                        if metrics.avg_memory_utilization < (THRESHOLDS["memory_utilization_very_low"] * 100):
                            memory_mb = parse_memory_string(service.memory_limit)
                            recommended_mb = max(
                                MEMORY_OPTIMIZATION["minimum_memory_mb"],
                                int(memory_mb * MEMORY_OPTIMIZATION["recommended_reduction_factor"])
                            )
                            all_recommendations.append(
                                OptimizationRecommendation(
                                    resource_type="cloud_run",
                                    resource_name=service.name,
                                    region=service.region,
                                    issue=f"Low memory utilization ({metrics.avg_memory_utilization:.1f}%)",
                                    recommendation=f"Reduce memory from {service.memory_limit} to {format_memory_mb(recommended_mb)}",
                                    potential_monthly_savings=COST_ESTIMATES["cloud_run_memory_optimization"],
                                    priority="medium",
                                    details={
                                        "current_memory": service.memory_limit,
                                        "recommended_memory": format_memory_mb(recommended_mb),
                                        "avg_memory_utilization": metrics.avg_memory_utilization
                                    }
                                )
                            )
                    
                    # Check for unnecessary min instances
                    if service.min_instances > 0:
                        savings = service.min_instances * COST_ESTIMATES["cloud_run_min_instances_per_instance"]
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="cloud_run",
                                resource_name=service.name,
                                region=service.region,
                                issue=f"Min instances set to {service.min_instances} (always-on cost)",
                                recommendation="Set min instances to 0 unless cold starts are critical",
                                potential_monthly_savings=savings,
                                priority="high",
                                details={
                                    "current_min_instances": service.min_instances,
                                    "cold_start_count": metrics.cold_start_count if metrics else 0
                                }
                            )
                        )
                    
                    all_services.append(service)
            
            except exceptions.PermissionDenied as e:
                error_msg = f"Permission denied for region {region}"
                issues.append(error_msg)
                logger.warning(error_msg, extra={"region": region, "project_id": self.project_id})
            except Exception as e:
                error_msg = f"Error auditing region {region}: {str(e)}"
                issues.append(error_msg)
                logger.error(error_msg, exc_info=True, extra={"region": region, "project_id": self.project_id})
        
        # Calculate total potential savings
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="cloud_run",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_services(self, region: str) -> List[CloudRunService]:
        """List all Cloud Run services in a region.
        
        Args:
            region: GCP region (e.g., 'us-central1')
        
        Returns:
            List of CloudRunService objects
        """
        self._validate_region(region)
        parent = f"projects/{self.project_id}/locations/{region}"
        services = []
        
        try:
            for service in self.cloud_run_client.list_services(parent=parent):
                # Parse service details
                template = service.template
                container = template.containers[0] if template.containers else None
                
                # Get resource limits
                memory_limit = "256Mi"  # Default
                if container and container.resources and container.resources.limits:
                    memory_limit = container.resources.limits.get("memory", "256Mi")
                
                # Get scaling settings
                min_instances = 0
                max_instances = 100
                if template.scaling:
                    min_instances = template.scaling.min_instance_count
                    max_instances = template.scaling.max_instance_count
                
                # Get CPU allocation - check for CPU throttling annotation
                # Default to throttled (CPU allocated = "0") unless explicitly set to always
                cpu_allocated = "0"  # Default to throttled
                
                # Check if CPU throttling is disabled (CPU always allocated)
                if hasattr(template, 'metadata') and template.metadata and hasattr(template.metadata, 'annotations'):
                    annotations = template.metadata.annotations
                    if annotations and "run.googleapis.com/cpu-throttling" in annotations:
                        cpu_throttling = annotations["run.googleapis.com/cpu-throttling"]
                        if cpu_throttling.lower() == "false":
                            cpu_allocated = "1"  # Always allocated
                
                services.append(CloudRunService(
                    name=get_resource_name_from_uri(service.name),
                    region=region,
                    labels=dict(service.labels) if service.labels else {},
                    cpu_allocated=cpu_allocated,
                    memory_limit=memory_limit,
                    min_instances=min_instances,
                    max_instances=max_instances,
                    ingress=str(service.ingress),
                    created_time=service.create_time,
                    updated_time=service.update_time
                ))
        
        except exceptions.NotFound:
            # Region doesn't have Cloud Run services
            pass
        except exceptions.PermissionDenied:
            # No permission for this region
            raise
        
        return services
    
    def get_service_metrics(
        self,
        service_name: str,
        region: str,
        days: int = 30
    ) -> Optional[CloudRunMetrics]:
        """Get metrics for a Cloud Run service.
        
        Args:
            service_name: Service name
            region: GCP region
            days: Number of days to look back (default: 30)
        
        Returns:
            CloudRunMetrics object or None if no data
        """
        if not service_name or not isinstance(service_name, str):
            raise ValueError("service_name must be a non-empty string")
        self._validate_region(region)
        
        interval = self._create_time_interval(days)
        
        metrics_data = {
            "request_count_30d": 0,
            "avg_cpu_utilization": 0.0,
            "avg_memory_utilization": 0.0,
            "cold_start_count": 0,
            "avg_request_latency_ms": 0.0
        }
        
        resource_labels = {
            "service_name": service_name,
            "location": region
        }
        
        # Get request count
        request_count = self._query_metric(
            "run.googleapis.com/request_count",
            "cloud_run_revision",
            resource_labels,
            interval,
            aggregation="sum"
        )
        metrics_data["request_count_30d"] = int(request_count)
        
        # Get CPU utilization
        cpu_util = self._query_metric(
            "run.googleapis.com/container/cpu/utilizations",
            "cloud_run_revision",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_cpu_utilization"] = cpu_util * 100  # Convert to percentage
        
        # Get memory utilization
        memory_util = self._query_metric(
            "run.googleapis.com/container/memory/utilizations",
            "cloud_run_revision",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_memory_utilization"] = memory_util * 100  # Convert to percentage
        
        # Get cold start count
        cold_starts = self._query_metric(
            "run.googleapis.com/request_count",
            "cloud_run_revision",
            resource_labels,
            interval,
            aggregation="sum",
            filter_str='metric.label.response_code_class="startup"'
        )
        metrics_data["cold_start_count"] = int(cold_starts)
        
        # Get request latency
        latency = self._query_metric(
            "run.googleapis.com/request_latencies",
            "cloud_run_revision",
            resource_labels,
            interval,
            aggregation="mean"
        )
        metrics_data["avg_request_latency_ms"] = latency
        
        return CloudRunMetrics(
            service_name=service_name,
            region=region,
            **metrics_data
        )
    

