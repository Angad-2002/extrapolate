"""Base service utilities for common patterns."""

from typing import Optional
from google.auth import default
from google.auth.credentials import Credentials


def get_default_credentials(credentials: Optional[Credentials] = None) -> Credentials:
    """Get default GCP credentials if not provided.
    
    Args:
        credentials: Optional credentials object
    
    Returns:
        GCP credentials object
    """
    if credentials is None:
        credentials, _ = default()
    return credentials
