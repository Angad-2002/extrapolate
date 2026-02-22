"""Forecast and trends interactive workflows."""

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from xpol.core import DashboardRunner
from xpol.services.forecast import ForecastService
from xpol.utils.visualizations import print_progress, print_error, DashboardVisualizer
from xpol.utils.helpers import get_project_id
from xpol.cli.interactive.utils.context import prompt_common_context, apply_logging_from_context

console = Console()

def run_forecast_interactive_mode() -> None:
    """Run forecast section menu."""
    while True:
        choice = inquirer.select(
            message="Forecast & Trends:",
            choices=[
                Choice(value="forecast", name="Generate Cost Forecast"),
                Choice(value="trend", name="View Cost Trends"),
                Choice(value="back", name="Back to Main Menu")
            ]
        ).execute()
        
        if choice == "back":
            break
        elif choice == "forecast":
            _run_forecast_interactive()
        elif choice == "trend":
            _run_trend_interactive()

def _run_forecast_interactive() -> None:
    """Run forecast generation interactively."""
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
    
    # Prompt for forecast-specific parameters
    forecast_days_str = inquirer.text(
        message="Number of days to forecast (default: 90):",
        default="90"
    ).execute()
    
    historical_days_str = inquirer.text(
        message="Number of days of historical data to use (default: 180):",
        default="180"
    ).execute()
    
    # Convert to integers with validation
    try:
        forecast_days = int(forecast_days_str) if forecast_days_str.strip() else 90
        historical_days = int(historical_days_str) if historical_days_str.strip() else 180
    except ValueError:
        print_error("Invalid number format. Using defaults (90 forecast days, 180 historical days).")
        forecast_days = 90
        historical_days = 180
    
    try:
        # Initialize runner to get GCP client
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Initialize forecast service (matching original CLI pattern)
        forecast_service = ForecastService(
            client=runner.gcp_client.bigquery,
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1"
        )
        
        # Generate forecast
        print_progress("Training Prophet model and generating forecast...")
        forecast_data = forecast_service.forecast_costs(
            forecast_days=forecast_days,
            historical_days=historical_days,
            project_id=ctx["project_id"]
        )
        print_progress("Forecast generated", done=True)
        
        # Display forecast
        visualizer = DashboardVisualizer()
        visualizer.display_forecast(forecast_data)
        
        # Add pause before returning to menu
        console.print("\n[dim]Press Enter to continue...[/dim]")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
            
    except Exception as e:
        print_error(f"Forecast failed: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def _run_trend_interactive() -> None:
    """Run trend analysis interactively - shows historical monthly costs."""
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
    
    # Prompt for number of months to show
    months_str = inquirer.text(
        message="Number of months to analyze (default: 6):",
        default="6"
    ).execute()
    
    try:
        months = int(months_str) if months_str.strip() else 6
    except ValueError:
        print_error("Invalid number format. Using default (6 months).")
        months = 6
    
    try:
        # Initialize runner to get cost processor
        runner = DashboardRunner(
            project_id=ctx["project_id"],
            billing_dataset=ctx["billing_dataset"],
            billing_table_prefix="gcp_billing_export_v1",
            regions=ctx["regions"],
            location=ctx["location"],
            hide_project_id=ctx["hide_project_id"]
        )
        
        # Get monthly cost trend data
        print_progress("Fetching historical cost data...")
        monthly_costs = runner.cost_processor.get_monthly_cost_trend(
            months=months,
            project_id=ctx["project_id"]
        )
        print_progress("Trend data retrieved", done=True)
        
        # Display trend results
        _display_cost_trend(monthly_costs)
        
        # Add pause before returning to menu
        console.print("\n[dim]Press Enter to continue...[/dim]")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
            
    except Exception as e:
        print_error(f"Trend analysis failed: {str(e)}")
        console.print("[yellow]Please check your configuration and try again.[/]")

def _display_cost_trend(monthly_costs: list) -> None:
    """Display monthly cost trend in a formatted table.
    
    Args:
        monthly_costs: List of (month, cost) tuples
    """
    if not monthly_costs:
        console.print("\n[yellow]No trend data available. This might be due to insufficient billing data.[/]")
        return
    
    # Create table
    table = Table(
        title="[bold cyan]GCP Cost Trend Analysis[/]",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Month", style="cyan", width=15)
    table.add_column("Cost", justify="right", style="green", width=15)
    table.add_column("Change", justify="right", width=15)
    table.add_column("Trend", width=30)
    
    prev_cost = None
    max_cost = max(cost for _, cost in monthly_costs) if monthly_costs else 0
    
    for month, cost in monthly_costs:
        # Calculate change percentage
        if prev_cost is not None and prev_cost > 0:
            change_pct = ((cost - prev_cost) / prev_cost) * 100
            if abs(change_pct) < 0.01:
                change_str = "[yellow]0.0%[/]"
            else:
                sign = "+" if change_pct > 0 else ""
                color = "red" if change_pct > 0 else "green"
                change_str = f"[{color}]{sign}{change_pct:.1f}%[/]"
        else:
            change_str = "[dim]—[/]"
        
        # Create trend bar (similar to AWS version)
        bar_length = int((cost / max_cost) * 25) if max_cost > 0 else 0
        bar = "█" * bar_length
        
        # Determine bar color based on trend
        if prev_cost is not None:
            if cost > prev_cost * 1.1:  # 10% increase
                bar_color = "bright_red"
            elif cost < prev_cost * 0.9:  # 10% decrease
                bar_color = "bright_green"
            else:
                bar_color = "blue"
        else:
            bar_color = "blue"
        
        table.add_row(
            month,
            f"${cost:,.2f}",
            change_str,
            f"[{bar_color}]{bar}[/]"
        )
        
        prev_cost = cost
    
    console.print("\n")
    console.print(Panel(table, border_style="cyan", padding=(0, 1)))
    console.print("\n")

