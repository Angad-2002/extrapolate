"""Compute Engine auditor."""

import logging
from typing import List, Optional
from google.cloud import compute_v1
from google.api_core import exceptions

from xpol.types import ComputeInstance, OptimizationRecommendation, AuditResult
from xpol.auditors.base import BaseAuditor
from xpol.auditors.constants import (
    COST_ESTIMATES,
    DEFAULT_ZONES
)

logger = logging.getLogger(__name__)


class ComputeAuditor(BaseAuditor):
    """Audit Compute Engine resources for cost optimization.
    
    This auditor analyzes Compute Engine VM instances to identify cost optimization
    opportunities, including:
    - Stopped instances still incurring disk storage costs
    - Non-preemptible instances that could use preemptible VMs
    - Untagged instances
    
    Example:
        ```python
        from google.cloud import compute_v1
        
        instances_client = compute_v1.InstancesClient()
        
        auditor = ComputeAuditor(
            instances_client=instances_client,
            project_id="my-project"
        )
        
        result = auditor.audit_all_instances(zones=["us-central1-a"])
        ```
    """
    
    def __init__(
        self,
        instances_client: compute_v1.InstancesClient,
        project_id: str
    ):
        """Initialize Compute Engine auditor.
        
        Args:
            instances_client: Compute Engine instances client for listing VMs
            project_id: GCP project ID to audit
        
        Raises:
            ValueError: If project_id is invalid (inherited from BaseAuditor)
        """
        super().__init__(project_id)
        self.instances_client = instances_client
    
    def audit_all_instances(self, zones: Optional[List[str]] = None) -> AuditResult:
        """Audit all Compute Engine instances across zones.
        
        Args:
            zones: List of zones to audit
        
        Returns:
            AuditResult with findings and recommendations
        """
        if zones is None:
            zones = DEFAULT_ZONES
        
        # Validate zones
        for zone in zones:
            self._validate_zone(zone)
        
        all_recommendations = []
        total_count = 0
        untagged_count = 0
        idle_count = 0  # Stopped instances
        over_provisioned_count = 0
        issues = []
        
        for zone in zones:
            try:
                instances = self.list_instances(zone)
                total_count += len(instances)
                
                for instance in instances:
                    # Check for untagged instances
                    if not instance.labels:
                        untagged_count += 1
                    
                    # Check for stopped instances (still costing for attached disks)
                    if instance.status in ["STOPPED", "SUSPENDED", "TERMINATED"]:
                        idle_count += 1
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="compute_instance",
                                resource_name=instance.name,
                                region=zone,
                                issue=f"Instance is {instance.status} but still incurring storage costs",
                                recommendation="Delete instance if no longer needed, or start it if needed",
                                potential_monthly_savings=COST_ESTIMATES["compute_stopped_disk_cost"],
                                priority="medium",
                                details={"status": instance.status}
                            )
                        )
                    
                    # Check for preemptible recommendation
                    if not instance.preemptible and instance.status == "RUNNING":
                        # For fault-tolerant workloads, recommend preemptible
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="compute_instance",
                                resource_name=instance.name,
                                region=zone,
                                issue="Non-preemptible instance running",
                                recommendation="Consider using preemptible VM for up to 80% savings (if workload allows)",
                                potential_monthly_savings=COST_ESTIMATES["compute_preemptible_savings"],
                                priority="low",
                                details={
                                    "machine_type": instance.machine_type,
                                    "preemptible": False
                                }
                            )
                        )
            
            except exceptions.PermissionDenied as e:
                error_msg = f"Permission denied for zone {zone}"
                issues.append(error_msg)
                logger.warning(error_msg, extra={"zone": zone, "project_id": self.project_id})
            except Exception as e:
                error_msg = f"Error auditing zone {zone}: {str(e)}"
                issues.append(error_msg)
                logger.error(error_msg, exc_info=True, extra={"zone": zone, "project_id": self.project_id})
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="compute_engine",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=over_provisioned_count,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_instances(self, zone: str) -> List[ComputeInstance]:
        """List all Compute Engine instances in a zone.
        
        Args:
            zone: GCP zone
        
        Returns:
            List of ComputeInstance objects
        """
        self._validate_zone(zone)
        instances = []
        
        try:
            for instance in self.instances_client.list(project=self.project_id, zone=zone):
                # Get machine type (last part of URL)
                machine_type = instance.machine_type.split("/")[-1] if instance.machine_type else "unknown"
                
                instances.append(ComputeInstance(
                    name=instance.name,
                    zone=zone,
                    machine_type=machine_type,
                    status=instance.status,
                    labels=dict(instance.labels) if instance.labels else {},
                    preemptible=instance.scheduling.preemptible if instance.scheduling else False,
                    created_time=None  # Parse instance.creation_timestamp if needed
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return instances

