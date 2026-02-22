"""Interactive menu system for CLI."""

from typing import Optional, Dict, Any
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from xpol.cli.utils.display import show_enhanced_progress, welcome_banner
from xpol.cli.ai.service import get_llm_service
from xpol.cli.interactive.workflows import (
    run_forecast_interactive_mode,
    run_config_interactive_mode,
    run_quick_setup,
    show_setup_instructions,
    run_ai_chat_interactive_mode,
    run_ai_analyze_interactive_mode,
    run_ai_summary_interactive_mode,
    run_ai_explain_spike_interactive_mode,
    run_ai_budget_suggestions_interactive_mode,
    run_audit_interactive_mode,
    run_ai_config_interactive,
    run_logging_config_interactive,
)
from xpol.cli.interactive.workflows.rag import (
    run_rag_chat_interactive,
    run_upload_document_interactive,
    run_list_documents_interactive,
    run_delete_document_interactive,
    run_vector_db_config_interactive,
    run_rag_settings_interactive,
    run_document_search_interactive,
    run_document_details_interactive,
    run_statistics_interactive,
)
from xpol.cli.interactive.utils.context import prompt_common_context, apply_logging_from_context
# Heavy imports moved to lazy loading - only import when needed
# from ...dashboard_runner import DashboardRunner
# from ...utils.visualizations import print_progress, print_error, DashboardVisualizer
# from ...helpers import get_project_id
# from ...utils.reports import ReportGenerator
# from ...api.config import REPORTS_DIR
from xpol.cli.ai.service import LLMService

console = Console()

class InteractiveMenu:
    """Interactive menu system."""
    
    @staticmethod
    def run_main_menu():
        """Run the main interactive menu."""
        # Display ASCII art banner
        welcome_banner()
        console.print()
        console.print("[bold cyan]Interactive Mode[/]")
        console.print("[dim]Navigate through different sections and commands[/]")
        console.print()
        
        while True:
            main_choice = inquirer.select(
                message="Select a section:",
                choices=[
                    Choice(value="dashboard", name="Dashboard & Reports"),
                    Choice(value="audit", name="Audits & Analysis"),
                    Choice(value="forecast", name="Forecasting & Trends"),
                    Choice(value="ai", name="AI-Powered Insights"),
                    Choice(value="config", name="Configuration & Setup"),
                    Choice(value="logging", name="Logging Configuration"),
                    Choice(value="quick-setup", name="Quick Setup (First Time)"),
                    Choice(value="help", name="Help & Documentation"),
                    Choice(value="exit", name="Exit")
                ]
            ).execute()
            
            if main_choice == "exit":
                console.print("[yellow]Goodbye![/]")
                break
            elif main_choice == "dashboard":
                InteractiveMenu.run_dashboard_menu()
            elif main_choice == "audit":
                InteractiveMenu.run_audit_menu()
            elif main_choice == "forecast":
                InteractiveMenu.run_forecast_menu()
            elif main_choice == "ai":
                InteractiveMenu.run_ai_menu()
            elif main_choice == "config":
                InteractiveMenu.run_config_menu()
            elif main_choice == "logging":
                run_logging_config_interactive()
            elif main_choice == "quick-setup":
                InteractiveMenu.run_quick_setup()
            elif main_choice == "help":
                InteractiveMenu.show_help_menu()
    
    @staticmethod
    def run_dashboard_menu():
        """Run dashboard section menu."""
        while True:
            choice = inquirer.select(
                message="Dashboard & Reports:",
                choices=[
                    Choice(value="dashboard", name="Generate Interactive Dashboard"),
                    Choice(value="report", name="Create PDF Report"),
                    Choice(value="back", name="Back to Main Menu")
                ]
            ).execute()
            
            if choice == "back":
                break
            elif choice == "dashboard":
                InteractiveMenu._run_dashboard_interactive()
            elif choice == "report":
                InteractiveMenu._run_report_interactive()
    
    @staticmethod
    def _run_dashboard_interactive():
        """Run interactive dashboard generation."""
        # Lazy import heavy dependencies
        from xpol.core import DashboardRunner
        from xpol.utils.visualizations import print_progress, print_error, DashboardVisualizer
        from xpol.utils.helpers import get_project_id
        
        # Collect common parameters (including logging options)
        ctx = prompt_common_context(include_logging=True)
        
        # Apply logging configuration if requested
        apply_logging_from_context(ctx)
        
        # Get project ID if not provided
        if not ctx["project_id"]:
            ctx["project_id"] = get_project_id()
            if not ctx["project_id"]:
                print_error("Project ID is required. Please specify it.")
                return
        
        try:
            # Initialize runner
            runner = DashboardRunner(
                project_id=ctx["project_id"],
                billing_dataset=ctx["billing_dataset"],
                billing_table_prefix="gcp_billing_export_v1",
                regions=ctx["regions"],
                location=ctx["location"],
                hide_project_id=ctx["hide_project_id"]
            )
            
            # Run dashboard
            print_progress("Running dashboard analysis...")
            data = runner.run()
            # Add budget alerts
            data = runner.add_budget_alerts(data)
            print_progress("Dashboard complete", done=True)
            
            # Display dashboard
            visualizer = DashboardVisualizer()
            visualizer.display_dashboard(data)
            
            # Add pause before returning to menu
            console.print("\n[dim]Press Enter to continue...[/dim]")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
                
        except Exception as e:
            print_error(f"Dashboard generation failed: {str(e)}")
            console.print("[yellow]Please check your configuration and try again.[/]")
    
    @staticmethod
    def _run_report_interactive():
        """Run interactive PDF report generation."""
        # Lazy import heavy dependencies
        from xpol.core import DashboardRunner
        from xpol.utils.visualizations import print_progress, print_error
        from xpol.utils.helpers import get_project_id
        from xpol.utils.reports import ReportGenerator
        from xpol.api.config import REPORTS_DIR
        
        # Collect common parameters (including logging options)
        ctx = prompt_common_context(include_logging=True)
        
        # Apply logging configuration if requested
        apply_logging_from_context(ctx)
        
        # Get project ID if not provided
        if not ctx["project_id"]:
            ctx["project_id"] = get_project_id()
            if not ctx["project_id"]:
                print_error("Project ID is required. Please specify it.")
                return
        
        try:
            # Initialize runner
            runner = DashboardRunner(
                project_id=ctx["project_id"],
                billing_dataset=ctx["billing_dataset"],
                billing_table_prefix="gcp_billing_export_v1",
                regions=ctx["regions"],
                location=ctx["location"],
                hide_project_id=ctx["hide_project_id"]
            )
            
            # Run dashboard to get data
            print_progress("Generating report data...")
            data = runner.run()
            print_progress("Report data ready", done=True)
            
            # Generate PDF report
            print_progress("Creating PDF report...")
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"xpol-report-{timestamp}.pdf"
            output_path = REPORTS_DIR / filename
            
            report_gen = ReportGenerator(output_dir=str(REPORTS_DIR))
            report_gen.generate_report(data, str(output_path))
            print_progress("PDF report created", done=True)
            
            console.print(f"\n[green]✓[/] Report saved to [cyan]{output_path.resolve()}[/]")
            
            # Add pause before returning to menu
            console.print("\n[dim]Press Enter to continue...[/dim]")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
                
        except Exception as e:
            print_error(f"Report generation failed: {str(e)}")
            console.print("[yellow]Please check your configuration and try again.[/]")
    
    @staticmethod
    def run_ai_menu():
        """Run AI section menu."""
        # Get LLM service with proper error handling
        llm_service = get_llm_service()
        ai_available = llm_service is not None
        
        if not ai_available:
            console.print("[red]AI features not available. API key not configured.[/]")
            console.print("[yellow]You can configure AI settings from this menu.[/]")
            console.print()
        
        while True:
            choice = inquirer.select(
                message="AI-Powered Insights:",
                choices=[
                    Choice(value="analyze", name="Generate Cost Analysis"),
                    Choice(value="ask", name="Ask Questions"),
                    Choice(value="summary", name="Generate Executive Summary"),
                    Choice(value="explain-spike", name="Explain Cost Spikes"),
                    Choice(value="budget", name="Get Budget Suggestions"),
                    Choice(value="rag", name="Document Chat (RAG)"),
                    Choice(value="config", name="Configure AI Settings"),
                    Choice(value="back", name="Back to Main Menu")
                ]
            ).execute()
            
            if choice == "back":
                break
            elif choice == "config":
                run_ai_config_interactive()
                # Refresh LLM service after configuration
                llm_service = get_llm_service()
                ai_available = llm_service is not None
            elif choice == "ask":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_chat_interactive_mode(llm_service)
            elif choice == "analyze":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_analyze_interactive_mode(llm_service)
            elif choice == "summary":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_summary_interactive_mode(llm_service)
            elif choice == "explain-spike":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_explain_spike_interactive_mode(llm_service)
            elif choice == "budget":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                run_ai_budget_suggestions_interactive_mode(llm_service)
            elif choice == "rag":
                if not ai_available:
                    console.print("[red]AI features not available. Please configure AI settings first.[/]")
                    continue
                InteractiveMenu._run_rag_menu()
    
    @staticmethod
    def _run_rag_menu():
        """Run RAG (Document Chat) menu."""
        from xpol.cli.interactive.workflows.rag import get_rag_service
        
        while True:
            # Get current vector DB info for display
            rag_service = get_rag_service()
            db_type = "Unknown"
            if rag_service:
                db_info = rag_service.get_vector_db_info()
                db_type = db_info.get("type", "Unknown").upper()
            
            choice = inquirer.select(
                message=f"Document Chat (RAG) [Current DB: {db_type}]:",
                choices=[
                    Choice(value="chat", name="Chat with Documents"),
                    Choice(value="search", name="Search Documents"),
                    Choice(value="upload", name="Upload PDF Document"),
                    Choice(value="list", name="List Uploaded Documents"),
                    Choice(value="details", name="View Document Details"),
                    Choice(value="delete", name="Delete Document"),
                    Choice(value="config", name="Configure Vector Database"),
                    Choice(value="rag_settings", name="Configure RAG settings"),
                    Choice(value="stats", name="System Statistics"),
                    Choice(value="back", name="Back to AI Menu")
                ]
            ).execute()
            
            if choice == "back":
                break
            elif choice == "chat":
                run_rag_chat_interactive()
            elif choice == "search":
                run_document_search_interactive()
            elif choice == "upload":
                run_upload_document_interactive()
            elif choice == "list":
                run_list_documents_interactive()
            elif choice == "details":
                run_document_details_interactive()
            elif choice == "delete":
                run_delete_document_interactive()
            elif choice == "config":
                run_vector_db_config_interactive()
            elif choice == "rag_settings":
                run_rag_settings_interactive()
            elif choice == "stats":
                run_statistics_interactive()
    
    @staticmethod
    def run_audit_menu():
        """Run audit section menu."""
        while True:
            choice = inquirer.select(
                message="Audits & Analysis:",
                choices=[
                    Choice(value="cloudrun", name="Cloud Run Audit"),
                    Choice(value="functions", name="Cloud Functions Audit"),
                    Choice(value="compute", name="Compute Engine Audit"),
                    Choice(value="sql", name="Cloud SQL Audit"),
                    Choice(value="disk", name="Disk Audit"),
                    Choice(value="ip", name="IP Address Audit"),
                    Choice(value="all", name="Run All Audits"),
                    Choice(value="multi-project", name="Multi-Project Analysis"),
                    Choice(value="back", name="Back to Main Menu"),
                ],
            ).execute()
            
            if choice == "back":
                break
            else:
                # Execute the selected audit
                run_audit_interactive_mode(choice)
    
    @staticmethod
    def run_forecast_menu():
        """Run forecast & trends section menu (delegates to prompts)."""
        run_forecast_interactive_mode()
    
    @staticmethod
    def run_config_menu():
        """Run configuration & setup menu (delegates to prompts)."""
        run_config_interactive_mode()
    
    @staticmethod
    def run_quick_setup():
        """Run quick setup wizard (delegates to prompts)."""
        run_quick_setup()
    
    @staticmethod
    def show_help_menu():
        """Show help & documentation."""
        show_setup_instructions()
