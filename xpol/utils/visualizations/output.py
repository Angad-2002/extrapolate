"""Output utility functions for console printing."""

from rich.console import Console

console = Console()


def print_progress(message: str, done: bool = False) -> None:
    """Print progress message.
    
    Args:
        message: Progress message
        done: Whether the task is complete
    """
    if done:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[cyan]⋯[/cyan] {message}")


def print_error(message: str) -> None:
    """Print error message.
    
    Args:
        message: Error message
    """
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print warning message.
    
    Args:
        message: Warning message
    """
    console.print(f"[yellow]Warning:[/yellow] {message}")

