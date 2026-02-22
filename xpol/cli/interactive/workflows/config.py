"""Configuration and setup interactive workflows."""

import os
import logging
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.table import Table
from xpol.cli.ai.service import refresh_llm_service
from xpol.cli.utils.display import show_enhanced_progress

console = Console()

def run_config_interactive_mode() -> None:
    """Run configuration interactive mode."""
    while True:
        choice = inquirer.select(
            message="Configuration & Setup:",
            choices=[
                Choice(value="ai-config", name="Configure AI Settings"),
                Choice(value="logging", name="Configure Logging"),
                Choice(value="quick-setup", name="Quick Setup"),
                Choice(value="setup-instructions", name="Show Setup Instructions"),
                Choice(value="back", name="Back to Main Menu")
            ]
        ).execute()
        
        if choice == "back":
            break
        elif choice == "ai-config":
            run_ai_config_interactive()
        elif choice == "logging":
            run_logging_config_interactive()
        elif choice == "quick-setup":
            run_quick_setup()
        elif choice == "setup-instructions":
            show_setup_instructions()

def run_ai_config_interactive() -> None:
    """Run AI configuration interactive mode."""
    console.print("\n[bold cyan]AI Configuration[/]")
    
    # Select provider
    provider = inquirer.select(
        message="Select AI provider:",
        choices=[
            Choice(value="openai", name="OpenAI"),
            Choice(value="groq", name="Groq"),
            Choice(value="anthropic", name="Anthropic (Claude)"),
            Choice(value="cancel", name="Cancel")
        ]
    ).execute()
    
    if provider == "cancel":
        return
    
    # Enter API key
    api_key = inquirer.secret(
        message=f"Enter {provider} API key:"
    ).execute()
    
    # Select model
    models = {
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "groq": [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
        ],
    }
    model_choices = [
        Choice(value=m, name=m) for m in models.get(provider, [])
    ]
    if not model_choices:
        console.print("[yellow]No models available for the selected provider.[/]")
        return
    model = inquirer.select(
        message="Select model:",
        choices=model_choices
    ).execute()
    
    # Save configuration
    show_enhanced_progress("Saving configuration...")
    try:
        os.environ["AI_PROVIDER"] = provider
        if provider == "groq":
            os.environ["GROQ_API_KEY"] = api_key
        elif provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        os.environ["AI_MODEL"] = model
        # Refresh LLM singleton so changes take effect immediately
        refreshed = refresh_llm_service()
        if refreshed is None:
            console.print("[yellow]Configuration saved, but AI service could not be initialized. Check API key.[/]")
        else:
            console.print("[green]✓ AI configuration saved and loaded.[/]")
    except Exception as e:
        console.print(f"[red]Failed to save AI configuration:[/] {e}")

def run_quick_setup() -> None:
    """Run quick setup wizard (saves to session environment variables only)."""
    console.print("\n[bold cyan]Quick Setup Wizard[/]")
    console.print("[dim]This configuration will persist for this interactive session only.[/]")
    console.print()
    
    # Get current values as defaults
    current_project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    current_billing = os.getenv("GCP_BILLING_DATASET") or ""
    current_regions = os.getenv("GCP_REGIONS") or ""
    
    # Project ID
    project_id = inquirer.text(
        message="Enter GCP project ID:",
        default=current_project
    ).execute()
    
    if not project_id.strip():
        console.print("[yellow]Project ID cannot be empty. Setup cancelled.[/]")
        return
    
    # Billing dataset
    billing_dataset = inquirer.text(
        message="Enter billing dataset (e.g., project.billing_export):",
        default=current_billing
    ).execute()
    
    if not billing_dataset.strip():
        console.print("[yellow]Billing dataset cannot be empty. Setup cancelled.[/]")
        return
    
    # Regions
    regions_input = inquirer.text(
        message="Enter regions (comma-separated, e.g., us-central1,us-east1, or blank for all):",
        default=current_regions
    ).execute()
    
    # Save configuration to environment variables (session-only)
    show_enhanced_progress("Saving configuration to session...")
    try:
        os.environ["GCP_PROJECT_ID"] = project_id.strip()
        os.environ["GCP_BILLING_DATASET"] = billing_dataset.strip()
        
        if regions_input.strip():
            os.environ["GCP_REGIONS"] = regions_input.strip()
        else:
            # Clear regions if blank
            os.environ.pop("GCP_REGIONS", None)
        
        console.print("[green]✓ Configuration saved for this interactive session.[/]")
        console.print(f"[dim]Project ID: {project_id}[/]")
        console.print(f"[dim]Billing Dataset: {billing_dataset}[/]")
        if regions_input.strip():
            console.print(f"[dim]Regions: {regions_input}[/]")
        else:
            console.print("[dim]Regions: (all regions)[/]")
        console.print("\n[yellow]Note: This configuration is only valid for this session. To persist, set environment variables or use config file.[/]")
    except Exception as e:
        console.print(f"[red]Failed to save configuration:[/] {e}")

def run_logging_config_interactive() -> None:
    """Run logging configuration interactive mode."""
    from xpol.cli.main import configure_logging
    
    console.print("\n[bold cyan]Logging Configuration[/]")
    console.print()
    
    # Show current logging status
    current_level = logging.getLogger().level
    level_name = logging.getLevelName(current_level)
    
    console.print("[bold]Current Logging Status:[/]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=25)
    table.add_column("Value", style="green")
    
    table.add_row("Log Level", level_name)
    table.add_row("Root Logger Level", str(current_level))
    
    # Check if third-party loggers are suppressed
    google_level = logging.getLogger('google').level
    urllib3_level = logging.getLogger('urllib3').level
    requests_level = logging.getLogger('requests').level
    
    third_party_status = "Enabled" if google_level <= logging.INFO else "Suppressed"
    table.add_row("Third-Party Logs", third_party_status)
    
    console.print(table)
    console.print()
    
    # Ask what to do
    choice = inquirer.select(
        message="Select action:",
        choices=[
            Choice(value="configure", name="Configure Logging Level"),
            Choice(value="disable", name="Disable Logging (WARNING only)"),
            Choice(value="status", name="Show Current Status"),
            Choice(value="back", name="Back to Config Menu")
        ]
    ).execute()
    
    if choice == "back":
        return
    elif choice == "status":
        # Already shown above, just return
        return
    elif choice == "disable":
        # Disable logging - set to WARNING level
        configure_logging(verbose=0, debug=False, trace=False)
        console.print("[green]✓[/] Logging disabled (WARNING level only).")
        console.print("[dim]Only warnings and errors will be shown.[/]")
    elif choice == "configure":
        # Configure logging level
        log_level = inquirer.select(
            message="Select logging level:",
            choices=[
                Choice(value="warning", name="WARNING - Only warnings and errors"),
                Choice(value="info", name="INFO - Basic information"),
                Choice(value="debug", name="DEBUG - Detailed debugging"),
                Choice(value="trace", name="TRACE - Most verbose (includes third-party logs)"),
            ],
            default="info"
        ).execute()
        
        if log_level == "trace":
            configure_logging(verbose=0, debug=False, trace=True)
            console.print("[green]✓[/] Logging configured to TRACE level.")
            console.print("[dim]All logs including third-party libraries will be shown.[/]")
        elif log_level == "debug":
            configure_logging(verbose=0, debug=True, trace=False)
            console.print("[green]✓[/] Logging configured to DEBUG level.")
            console.print("[dim]Detailed debugging information will be shown.[/]")
        elif log_level == "info":
            configure_logging(verbose=1, debug=False, trace=False)
            console.print("[green]✓[/] Logging configured to INFO level.")
            console.print("[dim]Basic information will be shown.[/]")
        else:  # warning
            configure_logging(verbose=0, debug=False, trace=False)
            console.print("[green]✓[/] Logging configured to WARNING level.")
            console.print("[dim]Only warnings and errors will be shown.[/]")
    
    console.print()

def show_setup_instructions() -> None:
    """Show setup instructions."""
    console.print("\n[bold cyan]Setup Instructions[/]")
    console.print("""
    1. Install the package:
       pip install xpol
    
    2. Set up Google Cloud credentials:
       gcloud auth application-default login
    
    3. Configure your billing export:
       - Enable BigQuery billing export in GCP Console
       - Note your billing dataset name
    
    4. Basic usage:
       xpol dashboard --billing-dataset YOUR_PROJECT.billing_export
    
    For more information: https://github.com/your-repo/xpol
    """)

