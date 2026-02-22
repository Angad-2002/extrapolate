"""API route modules."""

from .config_routes import router as config_router
from .dashboard import router as dashboard_router
from .costs import router as costs_router
from .audits import router as audits_router
from .recommendations import router as recommendations_router
from .reports import router as reports_router
from .ai import router as ai_router
from .forecast import router as forecast_router

__all__ = [
    "config_router",
    "dashboard_router",
    "costs_router",
    "audits_router",
    "recommendations_router",
    "reports_router",
    "ai_router",
    "forecast_router",
]

