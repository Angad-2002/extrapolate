"""AI insights API routes."""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import os

from xpol.api.config import get_cached_dashboard_data
from xpol.services.llm import get_llm_service, LLMService
from xpol.utils.helpers import calculate_percentage_change

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _check_ai_available():
    """Check if AI service is available, raise HTTPException if not."""
    llm_service = get_llm_service()
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="AI features not available. Set GROQ_API_KEY environment variable."
        )
    return llm_service


@router.get("/status")
async def ai_status():
    """
    Check if AI features are enabled and available.
    
    Returns status of Groq API integration.
    """
    llm_service = get_llm_service()
    
    provider_name = llm_service.provider if llm_service else None
    
    return {
        "enabled": llm_service is not None,
        "model": llm_service.model if llm_service else None,
        "provider": provider_name or "not configured",
        "message": "AI features are enabled" if llm_service else "Set AI_PROVIDER and corresponding API key environment variable to enable AI features"
    }


@router.get("/models")
async def get_available_models():
    """
    Get list of available Groq AI models.
    
    Returns available models with descriptions and recommendations.
    """
    models = LLMService.get_available_models()
    
    # Convert to list format for frontend
    model_list = [
        {
            "id": model_id,
            "name": info["name"],
            "description": info["description"],
            "context_window": info["context_window"],
            "recommended": info.get("recommended", False)
        }
        for model_id, info in models.items()
    ]
    
    # Get current model
    current_model = os.getenv("AI_MODEL") or LLMService.DEFAULT_MODEL
    
    return {
        "models": model_list,
        "current_model": current_model,
        "default_model": LLMService.DEFAULT_MODEL
    }


@router.post("/models/set")
async def set_ai_model(model_id: str = Query(..., description="Model ID to use")):
    """
    Set the AI model to use for analysis.
    
    Note: This sets it for the current session only. To persist, set GROQ_MODEL environment variable.
    """
    # Validate model exists by checking all providers
    all_models = LLMService.get_available_models()
    model_found = any(model_id == m or m.endswith(f":{model_id}") for m in all_models.keys())
    
    if not model_found:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model ID. Use /api/ai/models to see available models."
        )
    
    # Update environment variable for current process
    os.environ["AI_MODEL"] = model_id
    
    return {
        "success": True,
        "model": model_id,
        "message": f"AI model set to {model_id} (session only - set GROQ_MODEL env var to persist)"
    }


@router.post("/analyze")
async def ai_analyze_dashboard(refresh: bool = Query(False)):
    """
    Generate comprehensive AI analysis of dashboard data.
    
    Uses Groq's LLM to provide insights, recommendations, and anomaly detection.
    """
    llm_service = _check_ai_available()
    
    try:
        data = get_cached_dashboard_data(force_refresh=refresh)
        analysis = llm_service.analyze_dashboard_data(data)
        
        return {
            "success": True,
            "analysis": analysis["analysis"],
            "model": analysis["model_used"],
            "project_id": analysis["project_id"],
            "billing_month": analysis["billing_month"],
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI analysis: {str(e)}")


@router.post("/explain-spike")
async def ai_explain_cost_spike():
    """
    Get AI explanation for cost increases or decreases.
    
    Analyzes why costs changed compared to last month.
    """
    llm_service = _check_ai_available()
    
    try:
        data = get_cached_dashboard_data()
        explanation = llm_service.explain_cost_spike(data)
        
        return {
            "success": True,
            "explanation": explanation,
            "current_month": data.current_month_cost,
            "last_month": data.last_month_cost,
            "change_pct": calculate_percentage_change(data.current_month_cost, data.last_month_cost),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to explain cost spike: {str(e)}")


@router.post("/executive-summary")
async def ai_executive_summary():
    """
    Generate executive summary of FinOps data.
    
    Creates a concise summary suitable for stakeholders.
    """
    llm_service = _check_ai_available()
    
    try:
        data = get_cached_dashboard_data()
        summary = llm_service.generate_executive_summary(data)
        
        return {
            "success": True,
            "summary": summary,
            "project_id": data.project_id,
            "billing_month": data.billing_month,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/ask")
async def ai_ask_question(question: str = Query(..., description="Your question about the FinOps data")):
    """
    Ask a natural language question about your GCP costs.
    
    Examples:
    - "Why are my Cloud Run costs so high?"
    - "What are my biggest cost drivers?"
    - "How many idle resources do I have?"
    """
    llm_service = _check_ai_available()
    
    try:
        data = get_cached_dashboard_data()
        answer = llm_service.answer_question(question, data)
        
        return {
            "success": True,
            "question": question,
            "answer": answer,
            "generated_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")


@router.post("/prioritize-recommendations")
async def ai_prioritize_recommendations():
    """
    Get AI help prioritizing optimization recommendations.
    
    Suggests which recommendations to implement first based on impact and complexity.
    """
    llm_service = _check_ai_available()
    
    try:
        data = get_cached_dashboard_data()
        prioritization = llm_service.prioritize_recommendations(data.recommendations)
        
        return {
            "success": True,
            "prioritization": prioritization,
            "total_recommendations": len(data.recommendations),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prioritize recommendations: {str(e)}")


@router.post("/suggest-budgets")
async def ai_suggest_budget_alerts():
    """
    Get AI suggestions for budget alert thresholds.
    
    Analyzes spending patterns to recommend appropriate budget limits.
    """
    llm_service = _check_ai_available()
    
    try:
        data = get_cached_dashboard_data()
        suggestions = llm_service.suggest_budget_alerts(data)
        
        return {
            "success": True,
            "suggestions": suggestions,
            "current_month_cost": data.current_month_cost,
            "ytd_cost": data.ytd_cost,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest budgets: {str(e)}")


@router.post("/analyze-utilization")
async def ai_analyze_utilization():
    """
    Analyze resource utilization patterns with AI.
    
    Provides insights on how efficiently resources are being used.
    """
    llm_service = _check_ai_available()
    
    try:
        data = get_cached_dashboard_data()
        analysis = llm_service.analyze_resource_utilization(data.audit_results)
        
        return {
            "success": True,
            "analysis": analysis,
            "total_resources": sum(r.total_count for r in data.audit_results.values()),
            "idle_resources": sum(r.idle_count for r in data.audit_results.values()),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze utilization: {str(e)}")

