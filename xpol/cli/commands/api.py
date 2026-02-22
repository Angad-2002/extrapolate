"""API server command module."""

import click
from rich.console import Console
from xpol.cli.utils.display import show_enhanced_progress

console = Console()

# CLI Command
@click.command()
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port for API server (default: 8000)",
)
def api(port: int) -> None:
    """Start the API server for programmatic access."""
    # Lazy import - only load when command is invoked to speed up CLI startup
    import uvicorn
    from xpol.api.main import start_api_server
    
    show_enhanced_progress("Starting API server...")
    try:
        start_api_server(host="0.0.0.0", port=port)
    except Exception as e:
        console.print(f"[red]Error starting API server: {str(e)}[/]")
        raise click.Abort()
