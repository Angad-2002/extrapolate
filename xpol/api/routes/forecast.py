"""Forecast API routes."""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import traceback

from xpol.api.config import (
    get_cached_dashboard_data,
    get_forecast_service,
    get_cached_forecast,
    set_cached_forecast
)
from xpol.api.serializers import forecast_to_response_dict

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("")
async def get_cost_forecast(
    days: int = Query(90, description="Number of days to forecast (default: 90)"),
    historical_days: int = Query(180, description="Days of historical data to use (default: 180)"),
    refresh: bool = Query(False, description="Force refresh forecast")
):
    """
    Get cost forecast using Prophet.
    
    Predicts future costs based on historical billing data.
    Returns daily predictions with confidence intervals.
    """
    try:
        now = datetime.now()
        
        # Check if we need to refresh cache
        cached_forecast = get_cached_forecast(force_refresh=refresh)
        
        if cached_forecast is None or refresh:
            forecast_service = get_forecast_service()
            forecast = forecast_service.forecast_costs(
                forecast_days=days,
                historical_days=historical_days,
                project_id=None  # Use None to query all projects in dataset
            )
            set_cached_forecast(forecast)
            cached_forecast = forecast
        
        return forecast_to_response_dict(cached_forecast)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast: {str(e)}")


@router.get("/summary")
async def get_forecast_summary(
    days: int = Query(30, description="Number of days to forecast (default: 30)")
):
    """
    Get summarized forecast information.
    
    Returns key metrics like predicted monthly cost and trend.
    """
    try:
        forecast_service = get_forecast_service()
        forecast = forecast_service.forecast_costs(
            forecast_days=days,
            historical_days=180,
            project_id=None  # Use None to query all projects
        )
        
        # Get current month cost for comparison
        data = get_cached_dashboard_data()
        
        return {
            "predicted_cost_next_30d": forecast.total_predicted_cost,
            "current_month_cost": data.current_month_cost,
            "trend": forecast.trend,
            "confidence": forecast.model_confidence,
            "forecast_days": days,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast summary: {str(e)}")


@router.get("/service/{service_name}")
async def get_service_forecast(
    service_name: str,
    days: int = Query(90, description="Number of days to forecast"),
    historical_days: int = Query(180, description="Days of historical data to use")
):
    """
    Get cost forecast for a specific GCP service.
    
    Examples:
    - /api/forecast/service/Cloud%20Run
    - /api/forecast/service/Compute%20Engine
    """
    try:
        forecast_service = get_forecast_service()
        forecast = forecast_service.forecast_service_cost(
            service_name=service_name,
            forecast_days=days,
            historical_days=historical_days,
            project_id=None  # Use None to query all projects
        )
        
        return forecast_to_response_dict(forecast, service_name=service_name)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate forecast for service '{service_name}': {str(e)}"
        )


@router.get("/trends")
async def get_forecast_trends():
    """
    Get forecast trends for all major services.
    
    Returns predicted costs and trends for top services.
    """
    try:
        # Get top services from current data
        data = get_cached_dashboard_data()
        top_services = sorted(
            data.service_costs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 services
        
        forecast_service = get_forecast_service()
        
        trends = []
        for service_name, current_cost in top_services:
            try:
                forecast = forecast_service.forecast_service_cost(
                    service_name=service_name,
                    forecast_days=30,
                    historical_days=90,
                    project_id=None  # Use None to query all projects
                )
                
                trends.append({
                    "service_name": service_name,
                    "current_cost": current_cost,
                    "predicted_cost_30d": forecast.total_predicted_cost,
                    "trend": forecast.trend,
                    "confidence": forecast.model_confidence,
                })
            except Exception:
                # Skip services that fail to forecast
                continue
        
        return {
            "trends": trends,
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast trends: {str(e)}")


@router.get("/debug")
async def debug_forecast():
    """Debug endpoint to check forecast data retrieval."""
    try:
        from xpol.api.config import get_config
        forecast_service = get_forecast_service()
        config = get_config()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        debug_info = {
            "config": {
                "project_id": config["project_id"],
                "billing_dataset": config["billing_dataset"],
                "table_prefix": config["billing_table_prefix"],
            },
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "start_suffix": start_date.strftime("%Y%m%d"),
                "end_suffix": end_date.strftime("%Y%m%d"),
            }
        }
        
        # Try to get data (use None for project_id to get all data in test dataset)
        df = forecast_service.get_historical_daily_costs(180, None)
        
        debug_info.update({
            "result": {
                "rows": len(df),
                "columns": list(df.columns) if not df.empty else [],
                "date_range": {
                    "min": str(df['ds'].min()) if not df.empty else None,
                    "max": str(df['ds'].max()) if not df.empty else None
                },
                "total_cost": float(df['y'].sum()) if not df.empty else 0,
                "sample": df.head(3).to_dict('records') if not df.empty else []
            }
        })
        
        return debug_info
    except Exception as e:
        return {
            "error": str(e), 
            "type": str(type(e).__name__),
            "traceback": traceback.format_exc()
        }


@router.get("/alert-thresholds")
async def get_forecast_alert_thresholds():
    """
    Get recommended alert thresholds based on forecast.
    
    Suggests budget limits and alert thresholds based on predicted spending.
    """
    try:
        forecast_service = get_forecast_service()
        
        # Get 30-day forecast
        forecast = forecast_service.forecast_costs(
            forecast_days=30,
            historical_days=180,
            project_id=None  # Use None to query all projects
        )
        
        # Calculate recommended thresholds
        predicted_30d = forecast.total_predicted_cost
        
        # Conservative threshold (10% above prediction)
        conservative_threshold = predicted_30d * 1.10
        
        # Warning threshold (20% above prediction)
        warning_threshold = predicted_30d * 1.20
        
        # Critical threshold (30% above prediction)
        critical_threshold = predicted_30d * 1.30
        
        return {
            "predicted_monthly_cost": predicted_30d,
            "recommended_thresholds": {
                "conservative": round(conservative_threshold, 2),
                "warning": round(warning_threshold, 2),
                "critical": round(critical_threshold, 2),
            },
            "confidence": forecast.model_confidence,
            "trend": forecast.trend,
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate alert thresholds: {str(e)}")

