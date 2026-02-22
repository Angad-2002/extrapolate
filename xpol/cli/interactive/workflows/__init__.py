"""Interactive workflows for different CLI sections."""

from .ai import (
    run_ai_chat_interactive_mode,
    run_ai_analyze_interactive_mode,
    run_ai_summary_interactive_mode,
    run_ai_explain_spike_interactive_mode,
    run_ai_budget_suggestions_interactive_mode,
)
from .audit import run_audit_interactive_mode
from .forecast import run_forecast_interactive_mode
from .config import (
    run_config_interactive_mode,
    run_ai_config_interactive,
    run_logging_config_interactive,
    run_quick_setup,
    show_setup_instructions,
)
from .rag import (
    run_rag_chat_interactive,
    run_upload_document_interactive,
    run_list_documents_interactive,
    run_delete_document_interactive,
    run_vector_db_config_interactive,
    run_document_search_interactive,
    run_document_details_interactive,
    run_statistics_interactive,
)

__all__ = [
    # AI workflows
    "run_ai_chat_interactive_mode",
    "run_ai_analyze_interactive_mode",
    "run_ai_summary_interactive_mode",
    "run_ai_explain_spike_interactive_mode",
    "run_ai_budget_suggestions_interactive_mode",
    # Audit workflows
    "run_audit_interactive_mode",
    # Forecast workflows
    "run_forecast_interactive_mode",
    # Config workflows
    "run_config_interactive_mode",
    "run_ai_config_interactive",
    "run_logging_config_interactive",
    "run_quick_setup",
    "show_setup_instructions",
    # RAG workflows
    "run_rag_chat_interactive",
    "run_upload_document_interactive",
    "run_list_documents_interactive",
    "run_delete_document_interactive",
    "run_vector_db_config_interactive",
    "run_document_search_interactive",
    "run_document_details_interactive",
    "run_statistics_interactive",
]

