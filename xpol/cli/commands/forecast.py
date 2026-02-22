"""Forecast command module."""

from typing import Optional
import click
import logging
from xpol.cli.utils.display import show_enhanced_progress
from xpol.cli.commands.base import BaseCommand
from xpol.cli.constants import EX_OK, EX_GENERAL, EX_USAGE
from xpol.cli.exceptions import CLIException

logger = logging.getLogger(__name__)

class ForecastCommand(BaseCommand):
    """Forecast command implementation."""
    
    def __init__(
        self,
        project_id: Optional[str],
        billing_table_prefix: str,
        location: str,
        forecast_days: int = 90,
        history_days: int = 180,
    ):
        super().__init__(project_id, billing_table_prefix, location)
        self.forecast_days = forecast_days
        self.history_days = history_days
    
    def run(self) -> int:
        """Run the forecast command.
        
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        try:
            if not self.project_id:
                logger.error("Project ID is required")
                return EX_USAGE
            
            show_enhanced_progress("Initializing BigQuery client...")
            self.init_bigquery()
            
            show_enhanced_progress("Fetching historical cost data...")
            # Add your historical data fetching logic here
            
            show_enhanced_progress("Training forecast model...")
            # Add your forecast model training logic here
            
            show_enhanced_progress("Generating cost forecast...")
            # Add your forecast generation logic here
            
            show_enhanced_progress("Creating visualization...", done=True)
            # Add your visualization logic here
            
            return EX_OK
        except Exception as e:
            logger.error(f"Forecast command failed: {str(e)}", exc_info=True)
            return EX_GENERAL

@click.command()
@BaseCommand.common_options
@click.option(
    "--forecast-days",
    type=int,
    default=90,
    help="Number of days to forecast (default: 90)",
)
@click.option(
    "--history-days",
    type=int,
    default=180,
    help="Number of days of historical data to use (default: 180)",
)
@click.pass_context
def forecast(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    forecast_days: int,
    history_days: int,
) -> None:
    """Generate cost forecasts using machine learning."""
    cmd = ForecastCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        forecast_days=forecast_days,
        history_days=history_days,
    )
    exit_code = cmd.run()
    if exit_code != EX_OK:
        raise CLIException(f"Forecast command failed with exit code {exit_code}", exit_code)
