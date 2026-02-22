"""Main FastAPI application with modular routes."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import routers
from xpol.api.routes import (
    config_router,
    dashboard_router,
    costs_router,
    audits_router,
    recommendations_router,
    reports_router,
    ai_router,
    forecast_router,
)
from xpol.api.config import is_configured

# Create FastAPI app
app = FastAPI(
    title="GCP FinOps Dashboard API",
    description="API for GCP FinOps cost optimization and resource auditing",
    version="1.0.0"
)

# CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config_router)
app.include_router(dashboard_router)
app.include_router(costs_router)
app.include_router(audits_router)
app.include_router(recommendations_router)
app.include_router(reports_router)
app.include_router(ai_router)
app.include_router(forecast_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "GCP FinOps Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "configured": is_configured()
    }


def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the FastAPI server.
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 8000)
    """
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api_server()

