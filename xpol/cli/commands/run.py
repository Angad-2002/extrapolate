"""Run command with configuration file support."""

from typing import Optional, Tuple, Dict, Any
import click
import logging
from xpol.cli.utils.display import show_enhanced_progress
from xpol.cli.config.manager import ConfigManager
from xpol.cli.commands.base import BaseCommand
from xpol.cli.constants import EX_OK, EX_GENERAL, EX_USAGE
from xpol.cli.exceptions import CLIException

logger = logging.getLogger(__name__)

class RunCommand(BaseCommand):
    """Run command implementation."""
    
    def __init__(
        self,
        project_id: Optional[str],
        billing_table_prefix: str,
        location: str,
        report_name: str,
        report_type: Tuple[str, ...],
        output_dir: Optional[str] = None,
        time_range: Optional[int] = None,
        months_back: int = 2,
        labels: Tuple[str, ...] = (),
        services: Tuple[str, ...] = (),
        hide_project_id: bool = False,
        config_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(project_id, billing_table_prefix, location)
        self.report_name = report_name
        self.report_type = report_type
        self.output_dir = output_dir
        self.time_range = time_range
        self.months_back = months_back
        self.labels = labels
        self.services = services
        self.hide_project_id = hide_project_id
        self.config_data = config_data or {}
    
    def run(self) -> int:
        """Run the complete FinOps analysis.
        
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            if not self.project_id:
                logger.error("Project ID is required")
                return EX_USAGE
            
            show_enhanced_progress("Initializing services...")
            self.init_bigquery()
            
            show_enhanced_progress("Fetching cost data...")
            # Add your data fetching logic here
            
            show_enhanced_progress("Running analysis...")
            # Add your analysis logic here
            
            show_enhanced_progress("Generating reports...")
            for report_type in self.report_type:
                show_enhanced_progress(f"Creating {report_type} report...")
                # Add report generation logic here
            
            show_enhanced_progress("Done!", done=True)
            return EX_OK
        except Exception as e:
            logger.error(f"Run command failed: {str(e)}", exc_info=True)
            return EX_GENERAL

@click.command()
@BaseCommand.common_options
@click.option(
    "--report-name",
    default="xpol-report",
    help="Specify the base name for the report file (without extension)",
)
@click.option(
    "--report-type",
    multiple=True,
    type=click.Choice(["csv", "json", "pdf", "dashboard"]),
    default=["dashboard"],
    help="Report types: csv, json, pdf, or dashboard (can be specified multiple times)",
)
@click.option(
    "--dir",
    type=str,
    help="Directory to save the report files (default: reports directory)",
)
@click.option(
    "--time-range",
    type=int,
    help="Time range for cost data in days (default: current month). Examples: 7, 30, 90",
)
@click.option(
    "--months-back",
    type=int,
    default=2,
    help="Number of months to look back for billing data (default: 2)",
)
@click.option(
    "--label",
    multiple=True,
    help="Filter by labels/tags, e.g., --label env=prod --label team=devops",
)
@click.option(
    "--service",
    multiple=True,
    help="Filter by specific GCP services (e.g., --service cloud-run --service compute)",
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)",
)
@click.pass_context
def run(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    report_name: str,
    report_type: Tuple[str, ...],
    dir: Optional[str],
    time_range: Optional[int],
    months_back: int,
    label: Tuple[str, ...],
    service: Tuple[str, ...],
    hide_project_id: bool,
) -> None:
    """Run the complete FinOps analysis with config file support."""
    # Get config data from context
    config_data = ctx.obj.get('config_data', {})
    
    # Override CLI args with config data if not provided via CLI
    if config_data:
        if not project_id and "project_id" in config_data:
            project_id = config_data["project_id"]
        if not dir and "dir" in config_data:
            dir = config_data["dir"]
        if not time_range and "time_range" in config_data:
            time_range = config_data["time_range"]
        if months_back == 2 and "months_back" in config_data:
            months_back = config_data["months_back"]
        if not hide_project_id and "hide_project_id" in config_data:
            hide_project_id = config_data["hide_project_id"]
    
    cmd = RunCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        report_name=report_name,
        report_type=report_type,
        output_dir=dir,
        time_range=time_range,
        months_back=months_back,
        labels=label,
        services=service,
        hide_project_id=hide_project_id,
        config_data=config_data,
    )
    exit_code = cmd.run()
    if exit_code != EX_OK:
        raise CLIException(f"Run command failed with exit code {exit_code}", exit_code)
