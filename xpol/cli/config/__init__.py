"""Configuration management package."""

from .manager import ConfigManager
from .setup import show_setup_instructions, quick_setup

__all__ = ["ConfigManager", "show_setup_instructions", "quick_setup"]
