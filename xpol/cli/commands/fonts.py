"""Fonts and ASCII art command module."""

from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel

console = Console()

class FontsCommand:
    """Fonts command implementation."""
    
    def __init__(self, font: Optional[str] = None, list_fonts: bool = False):
        self.font = font
        self.list_fonts = list_fonts
    
    def run(self):
        """Run the fonts command."""
        try:
            if self.list_fonts:
                self._list_fonts()
            elif self.font:
                self._preview_font()
            else:
                self._show_default_preview()
        except Exception as e:
            console.print("[red]Error:[/] Make sure pyfiglet is installed: pip install pyfiglet")
            raise click.Abort()
    
    def _list_fonts(self):
        """List all available fonts."""
        # Lazy import pyfiglet to avoid loading it at module import time
        import pyfiglet
        fonts = sorted(pyfiglet.FigletFont.getFonts())
        console.print("[bold]Available Fonts:[/]")
        for font in fonts:
            console.print(f"• {font}")
    
    def _preview_font(self):
        """Preview a specific font."""
        # Lazy import pyfiglet to avoid loading it at module import time
        import pyfiglet
        text = "GCP FinOps"
        try:
            fig = pyfiglet.Figlet(font=self.font)
            art = fig.renderText(text)
            panel = Panel(
                art,
                title=f"Font Preview: {self.font}",
                border_style="blue",
            )
            console.print(panel)
        except Exception as e:
            console.print(f"[red]Error:[/] Font '{self.font}' not found or invalid")
    
    def _show_default_preview(self):
        """Show default font preview."""
        # Lazy import pyfiglet to avoid loading it at module import time
        import pyfiglet
        text = "GCP FinOps"
        default_fonts = ["slant", "big", "standard", "block"]
        
        for font in default_fonts:
            try:
                fig = pyfiglet.Figlet(font=font)
                art = fig.renderText(text)
                panel = Panel(
                    art,
                    title=f"Font Preview: {font}",
                    border_style="blue",
                )
                console.print(panel)
                console.print()
            except Exception:
                continue

@click.command()
@click.option(
    "--font",
    type=str,
    help="Show preview of specific font",
)
@click.option(
    "--list",
    "list_fonts",
    is_flag=True,
    help="List all available fonts",
)
def fonts(font: Optional[str], list_fonts: bool) -> None:
    """Show ASCII art fonts and previews."""
    cmd = FontsCommand(font=font, list_fonts=list_fonts)
    cmd.run()
