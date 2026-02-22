"""Common context collection utilities."""

import os
import logging
from typing import Optional, Dict, Any
from InquirerPy import inquirer
from InquirerPy.base.control import Choice


def apply_logging_from_context(ctx: Dict[str, Any]) -> None:
    """Apply logging configuration from context dictionary.
    
    Args:
        ctx: Context dictionary that may contain verbose, debug, trace keys
    """
    verbose = ctx.get("verbose", 0)
    debug = ctx.get("debug", False)
    trace = ctx.get("trace", False)
    
    # Only configure if logging options are present
    if verbose or debug or trace:
        # Import here to avoid circular imports
        from xpol.cli.main import configure_logging
        configure_logging(verbose, debug, trace)

def prompt_logging_options() -> Dict[str, Any]:
    """Prompt user for logging verbosity options.
    
    Returns:
        Dictionary with keys: verbose, debug, trace
    """
    # Ask if user wants to enable logging
    enable_logging = inquirer.confirm(
        message="Enable verbose logging for this operation?",
        default=False,
    ).execute()
    
    if not enable_logging:
        return {"verbose": 0, "debug": False, "trace": False}
    
    # If yes, ask for level
    log_level = inquirer.select(
        message="Select logging level:",
        choices=[
            Choice(value="info", name="INFO - Basic information"),
            Choice(value="debug", name="DEBUG - Detailed debugging"),
            Choice(value="trace", name="TRACE - Most verbose (includes third-party logs)"),
        ],
        default="info"
    ).execute()
    
    if log_level == "trace":
        return {"verbose": 0, "debug": False, "trace": True}
    elif log_level == "debug":
        return {"verbose": 0, "debug": True, "trace": False}
    else:  # info
        return {"verbose": 1, "debug": False, "trace": False}


def prompt_common_context(include_logging: bool = False) -> Dict[str, Any]:
    """Collect common context like project, billing dataset, regions, location, hide flag.
    
    Uses session environment variables as defaults if set (from Quick Setup).
    
    Args:
        include_logging: If True, also prompt for logging options
    
    Returns:
        Dictionary with keys: project_id, billing_dataset, regions, location, hide_project_id,
        and optionally verbose, debug, trace if include_logging is True
    """
    # Get defaults from session environment variables
    default_project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    default_billing = os.getenv("GCP_BILLING_DATASET") or ""
    default_regions = os.getenv("GCP_REGIONS") or ""
    
    project_id = inquirer.text(
        message="Enter GCP project ID (blank = default config):",
        default=default_project,
    ).execute()
    if project_id.strip() == "":
        project_id = None
    
    billing_dataset = inquirer.text(
        message="Enter BigQuery billing dataset (e.g., project.billing_export):",
        default=default_billing,
    ).execute()
    
    default_table = os.getenv("GCP_BILLING_TABLE_PREFIX") or "gcp_billing_export_v1"
    billing_table_prefix = inquirer.text(
        message="Billing table name (e.g. gcp_billing_export_v1):",
        default=default_table,
    ).execute()
    if not billing_table_prefix.strip():
        billing_table_prefix = "gcp_billing_export_v1"
    
    regions_input = inquirer.text(
        message="Enter regions (comma-separated, or press Enter for all):",
        default=default_regions,
    ).execute()
    region_list: Optional[list] = None
    if regions_input.strip():
        region_list = [r.strip() for r in regions_input.split(",")]
    
    location = inquirer.text(
        message="BigQuery location (default: US):",
        default="US",
    ).execute()
    hide_project_id = inquirer.confirm(
        message="Hide project ID in output?",
        default=False,
    ).execute()
    
    result = {
        "project_id": project_id,
        "billing_dataset": billing_dataset,
        "billing_table_prefix": billing_table_prefix.strip() or "gcp_billing_export_v1",
        "regions": region_list,
        "location": location,
        "hide_project_id": hide_project_id,
    }
    
    # Add logging options if requested
    if include_logging:
        logging_opts = prompt_logging_options()
        result.update(logging_opts)
    
    return result

