"""Audit API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict

from xpol.api.config import get_cached_dashboard_data, get_dashboard_runner
from xpol.api.serializers import audit_result_to_dict

router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.get("")
async def get_all_audits():
    """Get all audit results."""
    try:
        data = get_cached_dashboard_data()
        
        results = {
            key: audit_result_to_dict(result)
            for key, result in data.audit_results.items()
        }
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audits: {str(e)}")


@router.get("/{audit_type}")
async def get_specific_audit(audit_type: str, refresh: bool = Query(False)):
    """Get specific audit result."""
    try:
        if refresh:
            runner = get_dashboard_runner()
            result = runner.run_specific_audit(audit_type)
            if not result:
                raise HTTPException(status_code=404, detail=f"Audit type '{audit_type}' not found")
        else:
            data = get_cached_dashboard_data()
            result = data.audit_results.get(audit_type)
            if not result:
                raise HTTPException(status_code=404, detail=f"Audit type '{audit_type}' not found")
        
        return audit_result_to_dict(result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit: {str(e)}")

