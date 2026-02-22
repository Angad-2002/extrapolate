"""GCP client for authentication and API access."""

from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud import bigquery
    from google.cloud.bigquery import Client as BigQueryClient

from google.cloud import run_v2
from google.cloud import compute_v1
from google.cloud import monitoring_v3
from google.cloud import functions_v2
from google.auth import default
from google.auth.credentials import Credentials
from googleapiclient import discovery
from googleapiclient.discovery import Resource


class GCPClient:
    """GCP API client manager."""
    
    def __init__(self, project_id: Optional[str] = None, credentials: Optional[Credentials] = None, location: Optional[str] = None):
        """Initialize GCP client.
        
        Args:
            project_id: GCP project ID (defaults to application default)
            credentials: GCP credentials (defaults to application default)
            location: BigQuery location/region (e.g., 'US', 'asia-southeast1')
        """
        if credentials is None:
            credentials, default_project = default()
            if project_id is None:
                project_id = default_project
        
        if project_id is None:
            raise ValueError(
                "Project ID is required. Set GCP_PROJECT_ID environment variable "
                "or use 'gcloud config set project PROJECT_ID'"
            )
        
        self.project_id = project_id
        self.credentials = credentials
        self.location = location or "US"
        
        # Initialize clients lazily
        self._bigquery_client: Optional["BigQueryClient"] = None
        self._cloud_run_client: Optional[run_v2.ServicesClient] = None
        self._cloud_functions_client: Optional[functions_v2.FunctionServiceClient] = None
        self._compute_client: Optional[compute_v1.InstancesClient] = None
        self._compute_disks_client: Optional[compute_v1.DisksClient] = None
        self._compute_addresses_client: Optional[compute_v1.AddressesClient] = None
        self._cloud_sql_client: Optional[Resource] = None
        self._monitoring_client: Optional[monitoring_v3.MetricServiceClient] = None
    
    @property
    def bigquery(self) -> "BigQueryClient":
        """Get BigQuery client."""
        if self._bigquery_client is None:
            # Lazy import to avoid loading IPython/tqdm at module import time
            from google.cloud import bigquery
            self._bigquery_client = bigquery.Client(
                project=self.project_id,
                credentials=self.credentials,
                location=self.location
            )
        return self._bigquery_client
    
    @property
    def cloud_run(self) -> run_v2.ServicesClient:
        """Get Cloud Run client."""
        if self._cloud_run_client is None:
            self._cloud_run_client = run_v2.ServicesClient(credentials=self.credentials)
        return self._cloud_run_client
    
    @property
    def cloud_functions(self) -> functions_v2.FunctionServiceClient:
        """Get Cloud Functions client."""
        if self._cloud_functions_client is None:
            self._cloud_functions_client = functions_v2.FunctionServiceClient(
                credentials=self.credentials
            )
        return self._cloud_functions_client
    
    @property
    def compute_instances(self) -> compute_v1.InstancesClient:
        """Get Compute Engine instances client."""
        if self._compute_client is None:
            self._compute_client = compute_v1.InstancesClient(credentials=self.credentials)
        return self._compute_client
    
    @property
    def compute_disks(self) -> compute_v1.DisksClient:
        """Get Compute Engine disks client."""
        if self._compute_disks_client is None:
            self._compute_disks_client = compute_v1.DisksClient(credentials=self.credentials)
        return self._compute_disks_client
    
    @property
    def compute_addresses(self) -> compute_v1.AddressesClient:
        """Get Compute Engine addresses client."""
        if self._compute_addresses_client is None:
            self._compute_addresses_client = compute_v1.AddressesClient(
                credentials=self.credentials
            )
        return self._compute_addresses_client
    
    @property
    def cloud_sql(self) -> Resource:
        """Get Cloud SQL Admin API client."""
        if self._cloud_sql_client is None:
            self._cloud_sql_client = discovery.build(
                'sqladmin', 'v1', credentials=self.credentials
            )
        return self._cloud_sql_client
    
    @property
    def monitoring(self) -> monitoring_v3.MetricServiceClient:
        """Get Cloud Monitoring client."""
        if self._monitoring_client is None:
            self._monitoring_client = monitoring_v3.MetricServiceClient(
                credentials=self.credentials
            )
        return self._monitoring_client
    
    def list_regions(self) -> list[str]:
        """Get list of commonly used GCP regions.
        
        Returns:
            List of region names
        """
        # Common GCP regions
        return [
            "us-central1",
            "us-east1",
            "us-east4",
            "us-west1",
            "us-west2",
            "us-west3",
            "us-west4",
            "europe-west1",
            "europe-west2",
            "europe-west3",
            "europe-west4",
            "asia-east1",
            "asia-northeast1",
            "asia-southeast1",
        ]
    
    def list_zones(self, region: Optional[str] = None) -> list[str]:
        """Get list of zones for a region.
        
        Args:
            region: Region name (e.g., 'us-central1'). If None, returns all zones.
        
        Returns:
            List of zone names
        """
        if region:
            # Generate common zones for the region
            return [f"{region}-a", f"{region}-b", f"{region}-c", f"{region}-f"]
        else:
            # Return zones for all common regions
            zones = []
            for reg in self.list_regions():
                zones.extend(self.list_zones(reg))
            return zones


def get_bigquery_client(project_id: Optional[str] = None, location: Optional[str] = None) -> "BigQueryClient":
    """Get a BigQuery client.
    
    Args:
        project_id: GCP project ID (defaults to application default)
        location: BigQuery location/region (e.g., 'US', 'asia-southeast1')
    
    Returns:
        BigQuery client instance
    """
    gcp_client = GCPClient(project_id=project_id, location=location)
    return gcp_client.bigquery
