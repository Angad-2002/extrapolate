"""Dashboard API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from xpol.api.config import get_cached_dashboard_data, get_dashboard_runner, clear_cache
from xpol.api.serializers import audit_result_to_dict, recommendation_to_dict
from xpol.utils.helpers import calculate_percentage_change

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard(refresh: bool = Query(False, description="Force refresh data")):
    """Get complete dashboard data."""
    try:
        data = get_cached_dashboard_data(force_refresh=refresh)
        
        # Convert dataclass to dict
        result = {
            "project_id": data.project_id,
            "billing_month": data.billing_month,
            "current_month_cost": data.current_month_cost,
            "last_month_cost": data.last_month_cost,
            "ytd_cost": data.ytd_cost,
            "service_costs": data.service_costs,
            "total_potential_savings": data.total_potential_savings,
            "audit_results": {
                key: audit_result_to_dict(audit_result)
                for key, audit_result in data.audit_results.items()
            },
            "recommendations": [
                recommendation_to_dict(rec) for rec in data.recommendations
            ],
        }
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")


@router.get("/summary")
async def get_summary():
    """Get cost summary."""
    try:
        data = get_cached_dashboard_data()
        
        # Use helper function to avoid division by zero
        change_pct = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        # Count total resources
        total_resources = sum(
            result.total_count
            for result in data.audit_results.values()
        )
        
        return {
            "current_month": data.current_month_cost,
            "last_month": data.last_month_cost,
            "ytd": data.ytd_cost,
            "change_pct": change_pct,
            "resources_active": total_resources,
            "potential_savings": data.total_potential_savings,
            "project_id": data.project_id,
            "billing_month": data.billing_month,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {str(e)}")


@router.post("/refresh")
async def refresh_data():
    """Force refresh all dashboard data."""
    try:
        clear_cache()
        data = get_cached_dashboard_data(force_refresh=True)
        
        from datetime import datetime
        return {
            "status": "refreshed",
            "timestamp": datetime.now().isoformat(),
            "project_id": data.project_id,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh data: {str(e)}")


@router.get("/resources/summary")
async def get_resources_summary():
    """Get resources summary."""
    try:
        data = get_cached_dashboard_data()
        
        total = 0
        idle = 0
        untagged = 0
        
        for result in data.audit_results.values():
            total += result.total_count
            idle += result.idle_count
            untagged += result.untagged_count
        
        running = total - idle
        
        return {
            "total": total,
            "running": running,
            "idle": idle,
            "untagged": untagged,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch resources summary: {str(e)}")

