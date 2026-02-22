"""Custom exceptions for CLI with exit codes."""

from xpol.cli.constants import EX_GENERAL


class CLIException(Exception):
    """Base exception for CLI errors with exit codes."""
    
    def __init__(self, message: str, exit_code: int = EX_GENERAL):
        super().__init__(message)
        self.exit_code = exit_code
        self.message = message

