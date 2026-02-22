"""Report generation command module."""

from typing import Optional, Tuple
import click
import logging
from xpol.cli.utils.display import show_enhanced_progress
from xpol.cli.commands.base import BaseCommand
from xpol.cli.constants import EX_OK, EX_GENERAL, EX_USAGE
from xpol.cli.exceptions import CLIException

logger = logging.getLogger(__name__)

class ReportCommand(BaseCommand):
    """Report command implementation."""
    
    def __init__(
        self,
        project_id: Optional[str],
        billing_table_prefix: str,
        location: str,
        report_name: str,
        report_type: Tuple[str, ...],
        output_dir: Optional[str] = None,
        hide_project_id: bool = False,
    ):
        super().__init__(project_id, billing_table_prefix, location)
        self.report_name = report_name
        self.report_type = report_type
        self.output_dir = output_dir
        self.hide_project_id = hide_project_id
    
    def run(self) -> int:
        """Run the report generation command.
        
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            if not self.project_id:
                logger.error("Project ID is required")
                return EX_USAGE
            
            show_enhanced_progress("Initializing BigQuery client...")
            self.init_bigquery()
            
            show_enhanced_progress("Fetching cost data...")
            # Add your report data fetching logic here
            
            show_enhanced_progress("Generating reports...")
            # Add your report generation logic here
            
            for report_type in self.report_type:
                show_enhanced_progress(f"Generating {report_type} report...", done=True)
                # Add specific report type generation logic here
            
            return EX_OK
        except Exception as e:
            logger.error(f"Report command failed: {str(e)}", exc_info=True)
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
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)",
)
@click.pass_context
def report(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    report_name: str,
    report_type: Tuple[str, ...],
    dir: Optional[str],
    hide_project_id: bool,
) -> None:
    """Generate cost analysis reports in various formats."""
    cmd = ReportCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        report_name=report_name,
        report_type=report_type,
        output_dir=dir,
        hide_project_id=hide_project_id,
    )
    exit_code = cmd.run()
    if exit_code != EX_OK:
        raise CLIException(f"Report command failed with exit code {exit_code}", exit_code)
