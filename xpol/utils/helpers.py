"""Helper utilities for GCP FinOps Dashboard."""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from dateutil.relativedelta import relativedelta

# Conditional import for tomllib
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def get_project_id() -> Optional[str]:
    """Get GCP project ID from environment or gcloud config."""
    # Try environment variable first
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    
    if project_id:
        return project_id
    
    # Try gcloud config
    try:
        import subprocess
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return None


def get_date_range(months_back: int = 2) -> Tuple[str, str]:
    """Get date range for billing queries in YYYYMMDD format.
    
    Args:
        months_back: Number of months to look back (default: 2 for current + last month)
    
    Returns:
        Tuple of (start_date, end_date) in YYYYMMDD format
    """
    today = datetime.now()
    start_date = (today - relativedelta(months=months_back)).replace(day=1)
    end_date = today
    
    return (
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d")
    )


def get_current_month_range() -> Tuple[str, str]:
    """Get current month date range in YYYYMMDD format."""
    today = datetime.now()
    start_date = today.replace(day=1)
    return (
        start_date.strftime("%Y%m%d"),
        today.strftime("%Y%m%d")
    )


def get_last_month_range() -> Tuple[str, str]:
    """Get last month date range in YYYYMMDD format."""
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    
    return (
        first_day_last_month.strftime("%Y%m%d"),
        last_day_last_month.strftime("%Y%m%d")
    )


def format_currency(amount: float) -> str:
    """Format amount as USD currency."""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value:.1f}%"


def parse_memory_string(memory_str: str) -> int:
    """Parse memory string (e.g., '2Gi', '512Mi') to MB.
    
    Args:
        memory_str: Memory string with unit (Ki, Mi, Gi)
    
    Returns:
        Memory in MB
    """
    memory_str = memory_str.strip().upper()
    
    if memory_str.endswith("GI"):
        return int(float(memory_str[:-2]) * 1024)
    elif memory_str.endswith("MI"):
        return int(float(memory_str[:-2]))
    elif memory_str.endswith("KI"):
        return int(float(memory_str[:-2]) / 1024)
    elif memory_str.endswith("G"):
        return int(float(memory_str[:-1]) * 1024)
    elif memory_str.endswith("M"):
        return int(float(memory_str[:-1]))
    else:
        # Assume MB if no unit
        return int(memory_str)


def format_memory_mb(memory_mb: int) -> str:
    """Format memory in MB to human-readable string."""
    if memory_mb >= 1024:
        return f"{memory_mb / 1024:.1f}Gi"
    else:
        return f"{memory_mb}Mi"


def get_resource_name_from_uri(uri: str) -> str:
    """Extract resource name from GCP resource URI.
    
    Args:
        uri: GCP resource URI (e.g., 'projects/my-project/locations/us-central1/services/my-service')
    
    Returns:
        Resource name (e.g., 'my-service')
    """
    parts = uri.split("/")
    return parts[-1] if parts else uri


def calculate_percentage_change(current: float, previous: float) -> float:
    """Calculate percentage change between two values.
    
    Args:
        current: Current value
        previous: Previous value
    
    Returns:
        Percentage change
    """
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    
    return ((current - previous) / previous) * 100


def days_ago_to_datetime(days: int) -> datetime:
    """Convert days ago to datetime."""
    return datetime.now() - timedelta(days=days)


def estimate_monthly_cost_from_daily(daily_cost: float) -> float:
    """Estimate monthly cost from daily cost."""
    return daily_cost * 30


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is 0."""
    return numerator / denominator if denominator != 0 else default


def load_config_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Load configuration from TOML, YAML, or JSON file.
    
    Args:
        file_path: Path to config file (.toml, .yaml, .yml, or .json)
    
    Returns:
        Configuration dictionary or None if loading fails
    """
    from rich.console import Console
    console = Console()
    
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    try:
        with open(file_path, "rb" if file_extension == ".toml" else "r") as f:
            if file_extension == ".toml":
                if tomllib is None:
                    console.print(
                        "[bold red]Error: TOML library (tomli) not installed for Python < 3.11. "
                        "Please install it: pip install tomli[/]"
                    )
                    return None
                loaded_data = tomllib.load(f)
                if isinstance(loaded_data, dict):
                    return loaded_data
                console.print(
                    f"[bold red]Error: TOML file {file_path} did not load as a dictionary.[/]"
                )
                return None
            elif file_extension in [".yaml", ".yml"]:
                if yaml is None:
                    console.print(
                        "[bold red]Error: PyYAML library not installed. "
                        "Please install it: pip install pyyaml[/]"
                    )
                    return None
                loaded_data = yaml.safe_load(f)
                if isinstance(loaded_data, dict):
                    return loaded_data
                console.print(
                    f"[bold red]Error: YAML file {file_path} did not load as a dictionary.[/]"
                )
                return None
            elif file_extension == ".json":
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict):
                    return loaded_data
                console.print(
                    f"[bold red]Error: JSON file {file_path} did not load as a dictionary.[/]"
                )
                return None
            else:
                console.print(
                    f"[bold red]Error: Unsupported configuration file format: {file_extension}[/]"
                )
                return None
    except FileNotFoundError:
        console.print(f"[bold red]Error: Configuration file not found: {file_path}[/]")
        return None
    except Exception as e:
        console.print(f"[bold red]Error loading configuration file {file_path}: {e}[/]")
        return None
