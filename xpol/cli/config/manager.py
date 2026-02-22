"""Configuration management module."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import toml
import yaml
import json
from rich.console import Console

console = Console()

class ConfigManager:
    """Configuration management for the CLI."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
        
        if config_file:
            self.load_config()
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration from file."""
        if not self.config_file:
            return None
        
        try:
            file_path = Path(self.config_file)
            if not file_path.exists():
                console.print(f"[red]Config file not found: {self.config_file}[/]")
                return None
            
            content = file_path.read_text()
            ext = file_path.suffix.lower()
            
            if ext == '.toml':
                self.config_data = toml.loads(content)
            elif ext in ('.yml', '.yaml'):
                self.config_data = yaml.safe_load(content)
            elif ext == '.json':
                self.config_data = json.loads(content)
            else:
                console.print(f"[red]Unsupported config file format: {ext}[/]")
                return None
            
            return self.config_data
            
        except Exception as e:
            console.print(f"[red]Error loading config file: {str(e)}[/]")
            return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config_data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config_data[key] = value
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """Save configuration to file."""
        try:
            target_path = file_path or self.config_file
            if not target_path:
                console.print("[red]No config file specified[/]")
                return False
            
            path = Path(target_path)
            ext = path.suffix.lower()
            
            if ext == '.toml':
                content = toml.dumps(self.config_data)
            elif ext in ('.yml', '.yaml'):
                content = yaml.safe_dump(self.config_data)
            elif ext == '.json':
                content = json.dumps(self.config_data, indent=2)
            else:
                console.print(f"[red]Unsupported config file format: {ext}[/]")
                return False
            
            path.write_text(content)
            return True
            
        except Exception as e:
            console.print(f"[red]Error saving config file: {str(e)}[/]")
            return False
