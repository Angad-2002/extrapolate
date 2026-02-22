"""Progress indicators and spinners."""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

console = Console()

def create_progress(transient: bool = True) -> Progress:
    """Create a progress bar with consistent styling."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
        transient=transient,
    )

def create_spinner(message: str, spinner: str = "dots") -> Progress:
    """Create a spinner with message."""
    progress = Progress(
        SpinnerColumn(spinner_name=spinner),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )
    progress.add_task(message, total=None)
    return progress
