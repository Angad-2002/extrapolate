"""AI service integration module - delegates to real LLM service."""

from typing import Optional
from xpol.services.llm import LLMService as RealLLMService, get_llm_service as get_real_llm_service, refresh_llm_service as refresh_real_llm_service

# Re-export the real LLMService class for type compatibility
LLMService = RealLLMService


# Delegate to real LLM service functions
def get_llm_service() -> Optional[LLMService]:
    """Get or create LLM service singleton - delegates to real service."""
    return get_real_llm_service()


def refresh_llm_service() -> Optional[LLMService]:
    """Refresh the LLM service singleton - delegates to real service."""
    return refresh_real_llm_service()
