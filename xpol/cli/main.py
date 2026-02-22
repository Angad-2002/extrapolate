"""Core CLI module for GCP FinOps Dashboard."""

from __future__ import annotations

import sys
import warnings
import logging
from pathlib import Path
from typing import Optional

import click


def _get_version() -> str:
    """Return package version from metadata, or fallback for dev installs."""
    try:
        from importlib.metadata import version
        return version("xpol")
    except Exception:
        return "1.0.0"
from rich.console import Console

# Suppress pandas bottleneck version warning
warnings.filterwarnings("ignore", message=".*bottleneck.*", category=UserWarning)

# Lazy imports - only import command modules when they're actually invoked
# This dramatically speeds up CLI startup time
# ConfigManager, welcome_banner, and InteractiveMenu are imported lazily when needed
from xpol.cli.constants import EX_OK, EX_GENERAL, EX_USAGE, EX_CONFIG
from xpol.cli.exceptions import CLIException

# Initialize console for rich output
console = Console()

def init_cli():
    """Initialize CLI environment and dependencies."""
    # Add parent directory to sys.path for imports
    parent_dir = str(Path(__file__).resolve().parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

def configure_logging(verbose: int, debug: bool, trace: bool) -> None:
    """Configure logging based on verbosity flags.
    
    Args:
        verbose: Verbosity level (0-3)
        debug: Enable debug logging
        trace: Enable trace logging (most verbose)
    """
    # Determine log level
    if trace:
        log_level = logging.DEBUG  # Most verbose - shows everything
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    elif debug:
        log_level = logging.DEBUG
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    elif verbose == 1:
        log_level = logging.INFO
        format_str = '%(levelname)s - %(message)s'
    elif verbose >= 2:
        log_level = logging.DEBUG
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    else:
        log_level = logging.WARNING
        format_str = '%(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=format_str,
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True  # Override any existing configuration
    )
    
    # Set specific logger levels for verbose output
    if trace or debug or verbose >= 2:
        # Enable debug for our modules
        logging.getLogger('xpol').setLevel(logging.DEBUG)
        # Reduce noise from third-party libraries unless trace is enabled
        if not trace:
            logging.getLogger('google').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('requests').setLevel(logging.WARNING)
    else:
        # Reduce noise from third-party libraries
        logging.getLogger('google').setLevel(logging.ERROR)
        logging.getLogger('urllib3').setLevel(logging.ERROR)
        logging.getLogger('requests').setLevel(logging.ERROR)

@click.group(invoke_without_command=True)
@click.version_option(version=_get_version(), prog_name="xpol")
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to configuration file",
)
@click.option(
    "--verbose", "-v",
    count=True,
    help="Increase verbosity. Use -v for INFO, -vv for DEBUG, -vvv for more detail",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging (equivalent to -vv)",
)
@click.option(
    "--trace",
    is_flag=True,
    help="Enable trace logging (most verbose, includes third-party library logs)",
)
@click.pass_context
def cli(ctx: click.Context, config_file: Optional[str], verbose: int, debug: bool, trace: bool) -> None:
    """GCP FinOps Dashboard - Cost optimization and analysis tools for Google Cloud Platform.

    Run 'xpol --help' to see all available commands.
    """
    # Configure logging first
    configure_logging(verbose, debug, trace)
    
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    ctx.obj["trace"] = trace
    ctx.obj["exit_code"] = EX_OK  # Default to success
    
    # Load config if provided (lazy import ConfigManager)
    if config_file:
        try:
            from xpol.cli.config.manager import ConfigManager
            config_manager = ConfigManager(config_file)
            config_data = config_manager.load_config()
            ctx.obj["config_data"] = config_data
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to load config file: {str(e)}", exc_info=debug or trace)
            console.print(f"[red]Error loading config file:[/red] {str(e)}")
            ctx.obj["exit_code"] = EX_CONFIG
            raise click.Abort()
    
    # Initialize CLI environment
    init_cli()
    
    # Display banner only if not just showing help (skip for --help to speed up startup)
    # This avoids loading pyfiglet and reading files unnecessarily
    show_banner = ctx.invoked_subcommand is None and not any([
        '--help' in sys.argv,
        '-h' in sys.argv,
        'help' in sys.argv
    ])
    
    if show_banner:
        try:
            # Lazy import welcome_banner to avoid loading pyfiglet at startup
            from xpol.cli.utils.display import welcome_banner
            config_data = ctx.obj.get("config_data") if isinstance(ctx.obj, dict) else None
            welcome_banner(config_data)
        except Exception:
            # Banner is non-critical; ignore failures to avoid blocking CLI usage
            pass
    
    # If no subcommand was invoked, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# -------------------------
# Lazy command registrations
# -------------------------
# Commands are imported only when invoked, dramatically improving startup time

@cli.command()
@click.pass_context
def dashboard(ctx, **kwargs):
    """Generate an interactive cost analysis dashboard."""
    from xpol.cli.commands.dashboard import dashboard as real_cmd
    ctx.invoke(real_cmd, **kwargs)

@cli.command()
@click.pass_context
def report(ctx, **kwargs):
    """Generate cost analysis reports in various formats."""
    from xpol.cli.commands.report import report as real_cmd
    ctx.invoke(real_cmd, **kwargs)

@cli.command()
@click.pass_context
def audit(ctx, **kwargs):
    """Run cost optimization audits and generate recommendations."""
    from xpol.cli.commands.audit import audit as real_cmd
    ctx.invoke(real_cmd, **kwargs)

@cli.command()
@click.pass_context
def forecast(ctx, **kwargs):
    """Generate cost forecasts using machine learning."""
    from xpol.cli.commands.forecast import forecast as real_cmd
    ctx.invoke(real_cmd, **kwargs)

@cli.command()
@click.pass_context
def trend(ctx, **kwargs):
    """Analyze and visualize cost trends."""
    from xpol.cli.commands.trend import trend as real_cmd
    ctx.invoke(real_cmd, **kwargs)

@cli.command()
@click.pass_context
def api(ctx, **kwargs):
    """Start the API server for programmatic access."""
    from xpol.cli.commands.api import api as real_cmd
    ctx.invoke(real_cmd, **kwargs)

@cli.command()
@click.pass_context
def run(ctx, **kwargs):
    """Run the complete FinOps analysis with config file support."""
    from xpol.cli.commands.run import run as real_cmd
    ctx.invoke(real_cmd, **kwargs)

# AI is a Click group - use lazy loading with dynamic command resolution
class LazyAIGroup(click.Group):
    """Lazy-loading wrapper for AI command group."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._real_group = None
    
    def _get_real_group(self):
        """Lazy import the real AI group."""
        if self._real_group is None:
            from xpol.cli.ai.commands import ai
            self._real_group = ai
        return self._real_group
    
    def list_commands(self, ctx):
        """List commands from the real AI group."""
        return self._get_real_group().list_commands(ctx)
    
    def get_command(self, ctx, name):
        """Get command from the real AI group."""
        return self._get_real_group().get_command(ctx, name)
    
    def invoke(self, ctx):
        """Invoke the real AI group."""
        return self._get_real_group().invoke(ctx)

@cli.group(name='ai', cls=LazyAIGroup, invoke_without_command=True)
@click.pass_context
def ai_group(ctx):
    """AI-powered cost analysis commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@cli.command()
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start interactive mode with menu navigation",
)
@click.pass_context
def setup(ctx: click.Context, interactive: bool) -> None:
    """Show setup instructions or start interactive mode."""
    try:
        if interactive:
            # Lazy import InteractiveMenu - only load when needed
            # This avoids importing heavy dependencies like DashboardRunner, ForecastService, etc.
            from xpol.cli.interactive.menu import InteractiveMenu
            InteractiveMenu.run_main_menu()
        else:
            from xpol.cli.config.setup import show_setup_instructions
            show_setup_instructions()
        ctx.obj["exit_code"] = EX_OK
    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted by user[/yellow]")
        ctx.obj["exit_code"] = 130
        raise click.Abort()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Setup command failed: {str(e)}", exc_info=True)
        console.print(f"[red]Setup failed:[/red] {str(e)}")
        ctx.obj["exit_code"] = EX_GENERAL
        raise CLIException(f"Setup command failed: {str(e)}", EX_GENERAL)

def main() -> int:
    """Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Use standalone_mode=True to let Click handle most things
        cli(prog_name="xpol")
        # Default to success if no exception was raised
        return EX_OK
    except CLIException as e:
        # Custom CLI exception with exit code
        console.print(f"[red]Error:[/red] {e.message}")
        logger = logging.getLogger(__name__)
        logger.error(e.message, exc_info=True)
        return e.exit_code
    except click.ClickException as e:
        # Click exceptions have their own exit codes
        console.print(f"[red]Error:[/red] {str(e)}")
        return e.exit_code if hasattr(e, 'exit_code') and e.exit_code is not None else EX_USAGE
    except click.Abort:
        # User pressed Ctrl+C or we raised Abort
        # Exit code may be set in context, but we can't access it here easily
        # Default to general error
        return EX_GENERAL
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        console.print("\n[yellow]Aborted by user[/yellow]")
        return 130  # Standard exit code for SIGINT
    except SystemExit as e:
        # Click or other code called sys.exit()
        return e.code if isinstance(e.code, int) else EX_GENERAL
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        return EX_GENERAL

if __name__ == "__main__":
    sys.exit(main())