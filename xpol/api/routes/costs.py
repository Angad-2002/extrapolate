"""Cost-related API routes."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict

from xpol.api.config import get_cached_dashboard_data
from xpol.utils.helpers import calculate_percentage_change

router = APIRouter(prefix="/api/costs", tags=["costs"])


@router.get("/services")
async def get_service_costs():
    """Get costs by service."""
    try:
        data = get_cached_dashboard_data()
        
        # Convert to array format for frontend
        services = [
            {"name": service, "value": cost}
            for service, cost in data.service_costs.items()
        ]
        
        # Sort by cost descending
        services.sort(key=lambda x: x["value"], reverse=True)
        
        return services
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch service costs: {str(e)}")


@router.get("/trend")
async def get_cost_trend():
    """Get cost trend data (6 months)."""
    try:
        # This would need to be implemented in cost_processor to fetch historical data
        # For now, return a simple trend based on current data
        data = get_cached_dashboard_data()
        
        # Generate simple trend (would be replaced with actual historical data)
        current = data.current_month_cost
        last = data.last_month_cost
        
        months = ["May", "Jun", "Jul", "Aug", "Sep", "Oct"]
        trend = []
        
        for i, month in enumerate(months):
            if i == len(months) - 1:
                cost = current
            elif i == len(months) - 2:
                cost = last
            else:
                # Estimate previous months
                cost = last * (0.85 + i * 0.05)
            
            # Calculate change percentage, avoiding division by zero
            if i == 0:
                change = 0
            elif trend[i-1]["cost"] == 0:
                # If previous cost was 0, calculate as 100% increase if current > 0, else 0
                change = 100.0 if cost > 0 else 0
            else:
                change = ((cost - trend[i-1]["cost"]) / trend[i-1]["cost"]) * 100
            
            trend.append({
                "month": month,
                "cost": round(cost, 2),
                "change": round(change, 1)
            })
        
        return trend
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost trend: {str(e)}")

