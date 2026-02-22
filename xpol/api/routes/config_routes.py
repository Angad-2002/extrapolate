"""Configuration API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from xpol.api.config import get_config, set_config, is_configured

router = APIRouter(prefix="/api/config", tags=["configuration"])


@router.post("")
async def configure(
    project_id: Optional[str] = None,
    billing_dataset: Optional[str] = None,
    billing_table_prefix: Optional[str] = None,
    regions: Optional[List[str]] = None,
    bigquery_location: Optional[str] = None
):
    """Configure API settings."""
    try:
        return {
            "status": "configured",
            **set_config(
                project_id=project_id,
                billing_dataset=billing_dataset,
                billing_table_prefix=billing_table_prefix,
                regions=regions,
                bigquery_location=bigquery_location
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure: {str(e)}")


@router.get("")
async def get_config_endpoint():
    """Get current configuration."""
    return get_config()

