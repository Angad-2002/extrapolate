"""Audit interactive workflows."""

from typing import Any
from rich.console import Console
from rich.table import Table
from xpol.core import DashboardRunner
from xpol.utils.visualizations import print_progress, print_error, DashboardVisualizer
from xpol.utils.helpers import get_project_id
from xpol.cli.interactive.utils.context import prompt_common_context, apply_logging_from_context

console = Console()

def run_audit_interactive_mode(audit_type: str) -> None:
    """Run a specific audit interactively.
    
    Args:
        audit_type: Type of audit from menu ('cloudrun', 'functions', 'compute', 'sql', 'disk', 'ip', 'all', 'multi-project')
    """
    # Map menu audit types to actual audit types
    audit_type_map = {
        "cloudrun": "cloud_run",
        "functions": "cloud_functions",
        "compute": "compute",
        "sql": "cloud_sql",
        "disk": "disks",
        "ip": "ips",
        "all": "all",
        "multi-project": "multi-project"
    }
    
    # Check if multi-project mode
    if audit_type == "multi-project":
        run_multi_project_audit_interactive()
        return
    
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
            billing_table_prefix=ctx.get("billing_table_prefix", "gcp_billing_export_v1"),
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        if audit_type == "all":
            # Run complete dashboard
            print_progress("Running all audits...")
            data = runner.run()
            # Add budget alerts
            data = runner.add_budget_alerts(data)
            print_progress("All audits complete", done=True)
            
            # Display dashboard
            visualizer = DashboardVisualizer()
            visualizer.display_dashboard(data)
            
            # Add pause before returning to menu to prevent auto-selection
            console.print("\n[dim]Press Enter to continue...[/dim]")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
        else:
            # Run specific audit
            actual_audit_type = audit_type_map.get(audit_type, audit_type)
            # Map to proper display names
            display_name_map = {
                "cloudrun": "Cloud Run",
                "functions": "Cloud Functions",
                "compute": "Compute Engine",
                "sql": "Cloud SQL",
                "disk": "Disk",
                "ip": "IP Address"
            }
            audit_display_name = display_name_map.get(audit_type, audit_type.replace("-", " ").title())
            
            print_progress(f"Running {audit_display_name} audit...")
            result = runner.run_specific_audit(actual_audit_type)
            print_progress(f"{audit_display_name} audit complete", done=True)
            
            if result:
                # Display results in a formatted table
                display_audit_results_table(audit_display_name, result)
                
                # Display recommendations if available
                if result.recommendations:
                    console.print("\n[bold cyan]Optimization Recommendations[/]")
                    console.print()
                    visualizer = DashboardVisualizer()
                    visualizer.display_detailed_recommendations(result.recommendations)
                
                # Add pause before returning to menu to prevent auto-selection
                console.print("\n[dim]Press Enter to continue...[/dim]")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
            else:
                print_error(f"Audit type '{audit_type}' not found or returned no results.")
                
    except Exception as e:
        print_error(f"Audit failed: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def display_audit_results_table(audit_name: str, result: Any) -> None:
    """Display audit results in a formatted table.
    
    Args:
        audit_name: Name of the audit (e.g., 'Cloud Run', 'Compute Engine')
        result: AuditResult object with audit findings
    """
    # Create summary table
    table = Table(
        title=f"[bold cyan]{audit_name} Audit Summary[/]", 
        show_header=True, 
        header_style="bold magenta"
    )
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Count", justify="right", style="green", width=15)
    
    # Add rows
    table.add_row("Total Resources", str(result.total_count))
    table.add_row("Untagged Resources", str(result.untagged_count))
    table.add_row("Idle Resources", str(result.idle_count))
    table.add_row("Over-provisioned", str(result.over_provisioned_count))
    table.add_section()
    table.add_row(
        "[bold]Potential Monthly Savings[/]", 
        f"[bold green]${result.potential_monthly_savings:,.2f}[/]"
    )
    
    console.print("\n")
    console.print(table)
    console.print("\n")

def run_multi_project_audit_interactive() -> None:
    """Run multi-project audit in interactive mode."""
    from InquirerPy import inquirer
    from xpol.services.project import ProjectManager
    from xpol.core import DashboardRunner
    from xpol.utils.visualizations import DashboardVisualizer
    from xpol.utils.helpers import get_project_id
    
    # Collect common parameters (including logging options)
    ctx = prompt_common_context(include_logging=True)
    
    # Apply logging configuration if requested
    apply_logging_from_context(ctx)
    
    # Ask for multi-project mode
    from InquirerPy.base.control import Choice
    multi_mode = inquirer.select(
        message="Select multi-project mode:",
        choices=[
            Choice(value="projects", name="Specific projects (comma-separated)"),
            Choice(value="all", name="All accessible projects"),
            Choice(value="cancel", name="Cancel")
        ]
    ).execute()
    
    if multi_mode == "cancel":
        return
    
    projects = None
    all_projects = False
    
    if multi_mode == "projects":
        projects_input = inquirer.text(
            message="Enter project IDs (comma-separated):",
        ).execute()
        if projects_input.strip():
            projects = [p.strip() for p in projects_input.split(",")]
        else:
            print_error("No projects specified")
            return
    elif multi_mode == "all":
        all_projects = True
    
    # Ask if combine by billing account
    combine = inquirer.confirm(
        message="Group projects by billing account?",
        default=False,
    ).execute()
    
    # Get default project for billing dataset (use first project or default)
    default_project = projects[0] if projects else None
    if not default_project:
        default_project = get_project_id()
    
    if not ctx["billing_dataset"] and default_project:
        ctx["billing_dataset"] = f"{default_project}.billing_export"
    
    try:
        # Initialize runner with default project
        runner = DashboardRunner(
            project_id=default_project or "default",
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix=ctx.get("billing_table_prefix", "gcp_billing_export_v1"),
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        print_progress("Running multi-project analysis...")
        multi_data = runner.run_multi_project(
            projects=projects,
            all_projects=all_projects,
            combine=combine
        )
        print_progress("Multi-project analysis complete", done=True)
        
        # Display multi-project dashboard
        visualizer = DashboardVisualizer()
        visualizer.display_multi_project_dashboard(multi_data)
        
        # Add pause before returning to menu
        console.print("\n[dim]Press Enter to continue...[/dim]")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
            
    except Exception as e:
        print_error(f"Multi-project audit failed: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")
        import traceback
        traceback.print_exc()

