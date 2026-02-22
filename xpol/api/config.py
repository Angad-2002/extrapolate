"""API configuration and caching logic."""

from typing import Optional, List
from datetime import datetime
from pathlib import Path
import os

from xpol.core import DashboardRunner
from xpol.types import DashboardData, ForecastData
from xpol.utils.helpers import get_project_id
from xpol.services.forecast import ForecastService
from xpol.clients import get_bigquery_client

# Global configuration
_project_id: Optional[str] = None
_billing_dataset: Optional[str] = None
_billing_table_prefix: str = "gcp_billing_export_v1"
_regions: Optional[List[str]] = None
_bigquery_location: Optional[str] = None

# Cache for dashboard data
_cached_dashboard_data: Optional[DashboardData] = None
_cache_timestamp: Optional[datetime] = None
_cache_ttl_seconds = 300  # 5 minutes

# Cache for forecast data
_cached_forecast: Optional[ForecastData] = None
_forecast_cache_timestamp: Optional[datetime] = None
_forecast_cache_ttl_seconds = 900  # 15 minutes (forecasts can be cached longer)

# Reports directory configuration
# Use project root reports directory (consistent across API and CLI)
# Path calculation: config.py -> api/ -> xpol/ -> project_root/
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def get_config() -> dict:
    """Get current configuration."""
    return {
        "project_id": _project_id,
        "billing_dataset": _billing_dataset,
        "billing_table_prefix": _billing_table_prefix,
        "regions": _regions,
        "bigquery_location": _bigquery_location
    }


def set_config(
    project_id: Optional[str] = None,
    billing_dataset: Optional[str] = None,
    billing_table_prefix: Optional[str] = None,
    regions: Optional[List[str]] = None,
    bigquery_location: Optional[str] = None
) -> dict:
    """Set configuration."""
    global _project_id, _billing_dataset, _billing_table_prefix, _regions, _bigquery_location, _cached_dashboard_data
    
    if project_id:
        _project_id = project_id
    if billing_dataset:
        _billing_dataset = billing_dataset
    if billing_table_prefix:
        _billing_table_prefix = billing_table_prefix
    if regions:
        _regions = regions
    if bigquery_location:
        _bigquery_location = bigquery_location
    
    # Clear cache when configuration changes
    _cached_dashboard_data = None
    
    return get_config()


def get_dashboard_runner() -> DashboardRunner:
    """Get configured dashboard runner."""
    global _project_id, _billing_dataset, _bigquery_location, _regions
    
    if not _project_id:
        _project_id = os.getenv("GCP_PROJECT_ID") or get_project_id()
    
    if not _billing_dataset:
        _billing_dataset = os.getenv("GCP_BILLING_DATASET")
    
    if not _bigquery_location:
        _bigquery_location = os.getenv("BIGQUERY_LOCATION") or os.getenv("GCP_BIGQUERY_LOCATION") or "US"
    
    if not _regions:
        regions_env = os.getenv("GCP_REGIONS")
        if regions_env:
            _regions = [r.strip() for r in regions_env.split(",")]
        else:
            _regions = ["us-central1", "us-east1", "europe-west1"]
    
    if not _project_id:
        raise ValueError(
            "Project ID not configured. Set GCP_PROJECT_ID environment variable or configure via /api/config endpoint."
        )
    
    if not _billing_dataset:
        raise ValueError(
            "Billing dataset not configured. Set GCP_BILLING_DATASET environment variable or configure via /api/config endpoint."
        )
    
    return DashboardRunner(
        project_id=_project_id,
        billing_dataset=_billing_dataset,
        billing_table_prefix=_billing_table_prefix,
        regions=_regions,
        location=_bigquery_location
    )


def get_forecast_service() -> ForecastService:
    """Get configured forecast service."""
    global _project_id, _billing_dataset, _bigquery_location
    
    if not _project_id:
        _project_id = os.getenv("GCP_PROJECT_ID") or get_project_id()
    
    if not _billing_dataset:
        _billing_dataset = os.getenv("GCP_BILLING_DATASET")
    
    if not _bigquery_location:
        _bigquery_location = os.getenv("BIGQUERY_LOCATION") or os.getenv("GCP_BIGQUERY_LOCATION") or "US"
    
    if not _project_id:
        raise ValueError(
            "Project ID not configured. Set GCP_PROJECT_ID environment variable or configure via /api/config endpoint."
        )
    
    if not _billing_dataset:
        raise ValueError(
            "Billing dataset not configured. Set GCP_BILLING_DATASET environment variable or configure via /api/config endpoint."
        )
    
    client = get_bigquery_client(location=_bigquery_location)
    
    return ForecastService(
        client=client,
        billing_dataset=_billing_dataset,
        billing_table_prefix=_billing_table_prefix
    )


def get_cached_dashboard_data(force_refresh: bool = False) -> DashboardData:
    """Get dashboard data with caching."""
    global _cached_dashboard_data, _cache_timestamp
    
    now = datetime.now()
    
    # Check if we need to refresh cache
    if (
        force_refresh
        or _cached_dashboard_data is None
        or _cache_timestamp is None
        or (now - _cache_timestamp).total_seconds() > _cache_ttl_seconds
    ):
        runner = get_dashboard_runner()
        _cached_dashboard_data = runner.run()
        _cache_timestamp = now
    
    return _cached_dashboard_data


def get_cached_forecast(force_refresh: bool = False) -> Optional[ForecastData]:
    """Get forecast data with caching."""
    global _cached_forecast, _forecast_cache_timestamp
    
    now = datetime.now()
    
    # Check if cache is valid
    if (
        force_refresh
        or _cached_forecast is None
        or _forecast_cache_timestamp is None
        or (now - _forecast_cache_timestamp).total_seconds() > _forecast_cache_ttl_seconds
    ):
        return None
    
    return _cached_forecast


def set_cached_forecast(forecast: ForecastData) -> None:
    """Set cached forecast data."""
    global _cached_forecast, _forecast_cache_timestamp
    _cached_forecast = forecast
    _forecast_cache_timestamp = datetime.now()


def clear_cache() -> None:
    """Clear all caches."""
    global _cached_dashboard_data, _cache_timestamp, _cached_forecast, _forecast_cache_timestamp
    _cached_dashboard_data = None
    _cache_timestamp = None
    _cached_forecast = None
    _forecast_cache_timestamp = None


def is_configured() -> bool:
    """Check if API is configured."""
    return _project_id is not None and _billing_dataset is not None

