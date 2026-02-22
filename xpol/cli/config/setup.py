"""Setup and initialization module."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
import click
from xpol.cli.utils.display import show_enhanced_progress

console = Console()

def show_setup_instructions() -> None:
    """Show setup instructions."""
    instructions = """
    [bold cyan]GCP FinOps Dashboard Setup Instructions[/]
    
    1. Install the package:
       pip install xpol
    
    2. Set up Google Cloud credentials:
       gcloud auth application-default login
    
    3. Configure your billing export:
       - Enable BigQuery billing export in GCP Console
       - Note your billing dataset name
    
    4. Basic usage:
       xpol dashboard --billing-dataset YOUR_PROJECT.billing_export
    
    5. Advanced usage with all options:
       xpol dashboard \\
           --project-id YOUR_PROJECT_ID \\
           --billing-dataset YOUR_PROJECT.billing_export \\
           --regions us-central1,us-east1
    
    For more information: https://github.com/your-repo/xpol
    """
    console.print(instructions)

def quick_setup() -> None:
    """Run quick setup wizard."""
    console.print("[bold cyan]Quick Setup Wizard[/]")
    
    # Project ID
    project_id = click.prompt(
        "Enter your GCP project ID",
        type=str,
        default=os.getenv("GOOGLE_CLOUD_PROJECT"),
    )
    
    # Billing dataset
    billing_dataset = click.prompt(
        "Enter your BigQuery billing dataset (e.g., project.billing_export)",
        type=str,
    )
    
    # Regions
    regions = click.prompt(
        "Enter regions to monitor (comma-separated, e.g., us-central1,us-east1)",
        type=str,
        default="",
    )
    
    # Create config
    config = {
        "project_id": project_id,
        "billing_dataset": billing_dataset,
    }
    if regions:
        config["regions"] = [r.strip() for r in regions.split(",")]
    
    # Save config
    config_dir = Path.home() / ".xpol"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.toml"
    
    try:
        import toml
        config_file.write_text(toml.dumps(config))
        console.print(f"\n[green]Configuration saved to {config_file}[/]")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {str(e)}[/]")
        return
    
    console.print("\n[bold green]Setup completed successfully![/]")
    console.print("\nTry running: xpol dashboard")
