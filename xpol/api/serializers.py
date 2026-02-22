"""Shared API serializers for converting domain objects to response dicts."""

from typing import Optional, List, Dict, Any

from xpol.types import (
    AuditResult,
    ForecastData,
    ForecastPoint,
    OptimizationRecommendation,
)


def audit_result_to_dict(result: AuditResult) -> Dict[str, Any]:
    """Convert AuditResult to API response dict."""
    return {
        "resource_type": result.resource_type,
        "total_count": result.total_count,
        "untagged_count": result.untagged_count,
        "idle_count": result.idle_count,
        "over_provisioned_count": result.over_provisioned_count,
        "issues": result.issues,
        "potential_monthly_savings": result.potential_monthly_savings,
    }


def recommendation_to_dict(rec: OptimizationRecommendation) -> Dict[str, Any]:
    """Convert OptimizationRecommendation to API response dict."""
    return {
        "resource_type": rec.resource_type,
        "resource_name": rec.resource_name,
        "region": rec.region,
        "issue": rec.issue,
        "recommendation": rec.recommendation,
        "potential_monthly_savings": rec.potential_monthly_savings,
        "priority": rec.priority,
        "details": rec.details,
    }


def forecast_point_to_dict(point: ForecastPoint) -> Dict[str, Any]:
    """Convert ForecastPoint to API response dict."""
    return {
        "date": point.date,
        "predicted_cost": point.predicted_cost,
        "lower_bound": point.lower_bound,
        "upper_bound": point.upper_bound,
    }


def forecast_to_response_dict(
    forecast: ForecastData,
    *,
    service_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert ForecastData to full API response dict."""
    result: Dict[str, Any] = {
        "forecast_points": [
            forecast_point_to_dict(point) for point in forecast.forecast_points
        ],
        "total_predicted_cost": forecast.total_predicted_cost,
        "forecast_days": forecast.forecast_days,
        "model_confidence": forecast.model_confidence,
        "trend": forecast.trend,
        "generated_at": forecast.generated_at,
    }
    if service_name is not None:
        result["service_name"] = service_name
    return result
