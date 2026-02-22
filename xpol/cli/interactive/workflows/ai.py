"""AI-powered interactive workflows."""

from typing import Optional
from InquirerPy import inquirer
from rich.console import Console
from xpol.cli.ai.service import LLMService
from xpol.core import DashboardRunner
from xpol.utils.visualizations import print_progress, print_error, DashboardVisualizer
from xpol.cli.interactive.utils.context import prompt_common_context, apply_logging_from_context
from xpol.cli.interactive.utils.export import prompt_save_and_export
from xpol.cli.utils.formatting import format_ai_output
from xpol.cli.tui.chat_app import run_chat_app

console = Console()

def run_ai_chat_interactive_mode(llm_service: LLMService) -> None:
    """Run AI chat interactive mode with TUI interface."""
    console.print("[bold cyan]Starting AI Chat TUI...[/]")
    console.print("[dim]Loading dashboard data...[/]")
    console.print()
    
    # Ask user if they want to load dashboard data
    load_data = inquirer.confirm(
        message="Load GCP dashboard data for AI analysis?",
        default=True
    ).execute()
    
    dashboard_data = None
    if load_data:
        try:
            # Collect billing dataset and context (including logging options)
            ctx = prompt_common_context(include_logging=True)
            
            # Apply logging configuration if requested
            apply_logging_from_context(ctx)
            
            # Initialize runner with the collected parameters
            runner = DashboardRunner(
                project_id=ctx["project_id"],
                billing_dataset=ctx["billing_dataset"],
                billing_table_prefix="gcp_billing_export_v1",
                regions=ctx["regions"],
                location=ctx["location"],
                hide_project_id=ctx["hide_project_id"]
            )
            
            # Run analysis to collect data
            print_progress("Analyzing GCP resources and costs...")
            dashboard_data = runner.run()
            print_progress("Analysis complete", done=True)
            
            console.print(f"[green]✓[/] Dashboard data loaded successfully!")
            console.print(f"[dim]Provider: {llm_service.provider} | Model: {llm_service.model}[/]")
            console.print()
            
        except Exception as e:
            print_error(f"Failed to load dashboard data: {str(e)}")
            console.print("[yellow]Continuing without dashboard data...[/]")
            dashboard_data = None
    
    try:
        # Launch TUI chat interface
        console.print("[bold green]Launching chat interface...[/]")
        console.print("[dim]Press Ctrl+C in the chat to return to menu[/]")
        console.print()
        
        run_chat_app(
            llm_service=llm_service,
            rag_service=None,
            mode="ai",
            dashboard_data=dashboard_data
        )
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Returning to menu...[/]")
    except Exception as e:
        print_error(f"TUI error: {str(e)}")
        console.print("[yellow]Returning to menu...[/]")

def run_ai_analyze_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI analyze workflow (collects billing dataset, etc.)."""
    ctx = prompt_common_context(include_logging=True)
    apply_logging_from_context(ctx)
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate AI analysis
        print_progress("Generating AI insights...")
        analysis_result = llm_service.analyze_dashboard_data(data)
        print_progress("AI analysis ready", done=True)
        
        # Display AI analysis
        format_ai_output("🔍 AI Analysis", analysis_result['analysis'], llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, analysis_result['analysis'], default_base="xpol-analysis")
        
    except Exception as e:
        print_error(f"Failed to run analysis: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def run_ai_summary_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI executive summary workflow."""
    ctx = prompt_common_context(include_logging=True)
    apply_logging_from_context(ctx)
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate executive summary
        print_progress("Generating executive summary...")
        summary = llm_service.generate_executive_summary(data)
        print_progress("Executive summary ready", done=True)
        
        # Display AI summary
        format_ai_output("📋 Executive Summary", summary, llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, summary, default_base="xpol-summary")
        
    except Exception as e:
        print_error(f"Failed to generate summary: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def run_ai_explain_spike_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI explain-spike workflow."""
    ctx = prompt_common_context(include_logging=True)
    apply_logging_from_context(ctx)
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Explain cost spike
        print_progress("Analyzing cost changes...")
        explanation = llm_service.explain_cost_spike(data)
        print_progress("Cost analysis complete", done=True)
        
        # Display AI explanation
        format_ai_output("📈 Cost Spike Analysis", explanation, llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, explanation, default_base="xpol-explain-spike")
        
    except Exception as e:
        print_error(f"Failed to explain cost spike: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def run_ai_budget_suggestions_interactive_mode(llm_service: LLMService) -> None:
    """Run interactive AI budget suggestions workflow."""
    ctx = prompt_common_context(include_logging=True)
    apply_logging_from_context(ctx)
    try:
        # Initialize runner with the collected parameters
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Run analysis to collect data
        print_progress("Running dashboard analysis...")
        data = runner.run()
        print_progress("Analysis complete", done=True)
        
        # Generate budget suggestions
        print_progress("Analyzing spending patterns...")
        suggestions = llm_service.suggest_budget_alerts(data)
        print_progress("Budget analysis complete", done=True)
        
        # Display AI suggestions
        format_ai_output("💰 Budget Suggestions", suggestions, llm_service.provider, llm_service.model)
        
        # Prompt to save
        prompt_save_and_export(data, suggestions, default_base="xpol-budget")
        
    except Exception as e:
        print_error(f"Failed to generate budget suggestions: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

