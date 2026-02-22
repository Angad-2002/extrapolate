"""Formatting utilities for CLI output."""

from typing import Dict, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()

def format_ai_output(title: str, content: str, provider: str = "", model: str = "") -> None:
    """Format AI output in a box similar to chat responses with enhanced visual separation."""
    # Create timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Add visual separator before output
    console.print()
    console.print(Rule(style="dim"))
    
    # Create content panel with markdown support
    try:
        # Try to render as markdown first
        markdown_content = Markdown(content)
        content_panel = Panel(
            markdown_content,
            title=f"[bold {get_color('success')}]{title}[/]",
            title_align="left",
            border_style=get_color('success'),
            padding=(1, 2)
        )
    except Exception:
        # Fallback to plain text if markdown fails
        content_panel = Panel(
            Text(content, style="white"),
            title=f"[bold {get_color('success')}]{title}[/]",
            title_align="left",
            border_style=get_color('success'),
            padding=(1, 2)
        )
    
    # Create metadata panel with enhanced styling
    metadata_text = f"[dim]⏰ Time: {timestamp}[/dim]"
    if provider:
        metadata_text += f" [dim]| 🤖 Provider: {provider}[/dim]"
    if model:
        metadata_text += f" [dim]| 🧠 Model: {model}[/dim]"
    
    metadata_panel = Panel(
        Text(metadata_text, style="dim"),
        border_style="dim",
        padding=(0, 1)
    )
    
    # Display panels with enhanced spacing
    console.print(content_panel)
    console.print()
    console.print(metadata_panel)
    console.print()
    console.print(Rule(style="dim"))
    console.print()

def get_color(color_name: str) -> str:
    """Get color code for consistent styling."""
    colors = {
        "primary": "blue",
        "secondary": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "white",
        "dim": "grey70",
        "muted": "grey70",  # Alias for muted/dim text
    }
    return colors.get(color_name, color_name)

def get_ascii_art_config(config_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Get ASCII art configuration with defaults."""
    defaults = {
        "enabled": True,
        "font": "slant",
        "color": "blue",
    }
    
    if not config_data or "ascii_art" not in config_data:
        return defaults
    
    ascii_config = config_data["ascii_art"]
    return {
        "enabled": ascii_config.get("enabled", defaults["enabled"]),
        "font": ascii_config.get("font", defaults["font"]),
        "color": ascii_config.get("color", defaults["color"]),
    }
