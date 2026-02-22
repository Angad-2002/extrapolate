"""Storage and networking auditor."""

import logging
from typing import List, Optional
from google.cloud import compute_v1
from google.api_core import exceptions

from xpol.types import PersistentDisk, StaticIPAddress, OptimizationRecommendation, AuditResult
from xpol.auditors.base import BaseAuditor
from xpol.auditors.constants import (
    COST_ESTIMATES,
    DEFAULT_ZONES,
    DEFAULT_REGIONS
)

logger = logging.getLogger(__name__)


class StorageAuditor(BaseAuditor):
    """Audit storage and networking resources for cost optimization.
    
    This auditor analyzes storage and networking resources to identify cost
    optimization opportunities, including:
    - Unattached persistent disks incurring storage costs
    - Unused static IP addresses
    
    Example:
        ```python
        from google.cloud import compute_v1
        
        disks_client = compute_v1.DisksClient()
        addresses_client = compute_v1.AddressesClient()
        
        auditor = StorageAuditor(
            disks_client=disks_client,
            addresses_client=addresses_client,
            project_id="my-project"
        )
        
        disk_result = auditor.audit_disks(zones=["us-central1-a"])
        ip_result = auditor.audit_static_ips(regions=["us-central1"])
        ```
    """
    
    def __init__(
        self,
        disks_client: compute_v1.DisksClient,
        addresses_client: compute_v1.AddressesClient,
        project_id: str
    ):
        """Initialize storage auditor.
        
        Args:
            disks_client: Compute Engine disks client for listing persistent disks
            addresses_client: Compute Engine addresses client for listing static IPs
            project_id: GCP project ID to audit
        
        Raises:
            ValueError: If project_id is invalid (inherited from BaseAuditor)
        """
        super().__init__(project_id)
        self.disks_client = disks_client
        self.addresses_client = addresses_client
    
    def audit_disks(self, zones: Optional[List[str]] = None) -> AuditResult:
        """Audit persistent disks for unattached volumes.
        
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
        idle_count = 0  # Unattached disks
        issues = []
        
        for zone in zones:
            try:
                disks = self.list_disks(zone)
                total_count += len(disks)
                
                for disk in disks:
                    # Check for untagged disks
                    if not disk.labels:
                        untagged_count += 1
                    
                    # Check for unattached disks
                    if not disk.in_use:
                        idle_count += 1
                        # Calculate cost based on disk size
                        monthly_cost = disk.size_gb * COST_ESTIMATES["disk_storage_per_gb_monthly"]
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="persistent_disk",
                                resource_name=disk.name,
                                region=zone,
                                issue="Unattached disk incurring storage costs",
                                recommendation="Delete if no longer needed, or create snapshot and delete",
                                potential_monthly_savings=monthly_cost,
                                priority="high",
                                details={
                                    "size_gb": disk.size_gb,
                                    "disk_type": disk.disk_type,
                                    "in_use": False
                                }
                            )
                        )
            
            except exceptions.PermissionDenied as e:
                error_msg = f"Permission denied for zone {zone}"
                issues.append(error_msg)
                logger.warning(error_msg, extra={"zone": zone, "project_id": self.project_id})
            except Exception as e:
                error_msg = f"Error auditing disks in zone {zone}: {str(e)}"
                issues.append(error_msg)
                logger.error(error_msg, exc_info=True, extra={"zone": zone, "project_id": self.project_id})
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="persistent_disks",
            total_count=total_count,
            untagged_count=untagged_count,
            idle_count=idle_count,
            over_provisioned_count=0,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def audit_static_ips(self, regions: Optional[List[str]] = None) -> AuditResult:
        """Audit static IP addresses for unused IPs.
        
        Args:
            regions: List of regions to audit
        
        Returns:
            AuditResult with findings and recommendations
        """
        if regions is None:
            regions = DEFAULT_REGIONS
        
        # Validate regions
        for region in regions:
            self._validate_region(region)
        
        all_recommendations = []
        total_count = 0
        idle_count = 0  # Unused IPs
        issues = []
        
        for region in regions:
            try:
                addresses = self.list_static_ips(region)
                total_count += len(addresses)
                
                for address in addresses:
                    # Check for unused IPs
                    if not address.in_use:
                        idle_count += 1
                        # Unused external IPs have monthly cost
                        monthly_cost = COST_ESTIMATES["static_ip_external_monthly"] if address.address_type == "EXTERNAL" else 0.0
                        all_recommendations.append(
                            OptimizationRecommendation(
                                resource_type="static_ip",
                                resource_name=address.name,
                                region=region,
                                issue="Unused static IP incurring charges",
                                recommendation="Release if no longer needed",
                                potential_monthly_savings=monthly_cost,
                                priority="medium",
                                details={
                                    "address": address.address,
                                    "address_type": address.address_type,
                                    "in_use": False
                                }
                            )
                        )
            
            except exceptions.PermissionDenied as e:
                error_msg = f"Permission denied for region {region}"
                issues.append(error_msg)
                logger.warning(error_msg, extra={"region": region, "project_id": self.project_id})
            except Exception as e:
                error_msg = f"Error auditing IPs in region {region}: {str(e)}"
                issues.append(error_msg)
                logger.error(error_msg, exc_info=True, extra={"region": region, "project_id": self.project_id})
        
        total_savings = sum(r.potential_monthly_savings for r in all_recommendations)
        
        return AuditResult(
            resource_type="static_ips",
            total_count=total_count,
            untagged_count=0,
            idle_count=idle_count,
            over_provisioned_count=0,
            issues=issues,
            recommendations=all_recommendations,
            potential_monthly_savings=total_savings
        )
    
    def list_disks(self, zone: str) -> List[PersistentDisk]:
        """List all persistent disks in a zone.
        
        Args:
            zone: GCP zone
        
        Returns:
            List of PersistentDisk objects
        """
        self._validate_zone(zone)
        disks = []
        
        try:
            for disk in self.disks_client.list(project=self.project_id, zone=zone):
                # Disk type (last part of URL)
                disk_type = disk.type.split("/")[-1] if disk.type else "unknown"
                
                # Check if disk is attached to any instance
                in_use = bool(disk.users)
                
                disks.append(PersistentDisk(
                    name=disk.name,
                    zone=zone,
                    size_gb=disk.size_gb if disk.size_gb else 0,
                    disk_type=disk_type,
                    status=disk.status,
                    in_use=in_use,
                    labels=dict(disk.labels) if disk.labels else {},
                    created_time=None
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return disks
    
    def list_static_ips(self, region: str) -> List[StaticIPAddress]:
        """List all static IP addresses in a region.
        
        Args:
            region: GCP region
        
        Returns:
            List of StaticIPAddress objects
        """
        self._validate_region(region)
        addresses = []
        
        try:
            for address in self.addresses_client.list(project=self.project_id, region=region):
                # Check if IP is in use (attached to an instance/service)
                in_use = bool(address.users)
                
                addresses.append(StaticIPAddress(
                    name=address.name,
                    region=region,
                    address=address.address if address.address else "unknown",
                    address_type=address.address_type,
                    status=address.status,
                    in_use=in_use,
                    created_time=None
                ))
        
        except exceptions.NotFound:
            pass
        except exceptions.PermissionDenied:
            raise
        
        return addresses

