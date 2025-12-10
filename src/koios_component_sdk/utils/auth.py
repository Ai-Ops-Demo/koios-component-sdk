"""
Authentication utilities for the Koios Component SDK.

This module provides functionality for managing authentication
credentials for Koios server connections.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import base64
import requests

from ..exceptions import DeploymentError


def get_credentials_file() -> Path:
    """Get path to credentials file."""
    home_dir = Path.home()
    return home_dir / ".koios_credentials"


def save_credentials(host: str, port: int, username: str, password: str) -> bool:
    """
    Save authentication credentials.
    
    Args:
        host: Server hostname
        port: Server port
        username: Username
        password: Password
        
    Returns:
        True if credentials were saved successfully
    """
    try:
        credentials = {
            'host': host,
            'port': port,
            'username': username,
            'password': base64.b64encode(password.encode()).decode()  # Basic encoding
        }
        
        creds_file = get_credentials_file()
        with open(creds_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        # Set file permissions (read/write for owner only)
        if hasattr(os, 'chmod'):
            os.chmod(creds_file, 0o600)
        
        return True
    
    except Exception:
        return False


def load_credentials() -> Optional[Dict[str, Any]]:
    """
    Load saved authentication credentials.
    
    Returns:
        Dictionary with credentials or None if not found
    """
    try:
        creds_file = get_credentials_file()
        
        if not creds_file.exists():
            return None
        
        with open(creds_file, 'r') as f:
            credentials = json.load(f)
        
        # Decode password
        if 'password' in credentials:
            credentials['password'] = base64.b64decode(credentials['password'].encode()).decode()
        
        return credentials
    
    except Exception:
        return None


def clear_credentials() -> bool:
    """
    Clear saved authentication credentials.
    
    Returns:
        True if credentials were cleared successfully
    """
    try:
        creds_file = get_credentials_file()
        
        if creds_file.exists():
            creds_file.unlink()
        
        return True
    
    except Exception:
        return False


def test_connection(host: str, port: int, username: str, password: str) -> bool:
    """
    Test connection to Koios server.
    
    Args:
        host: Server hostname
        port: Server port
        username: Username
        password: Password
        
    Returns:
        True if connection test succeeded
    """
    try:
        # Test basic connectivity
        base_url = f"https://{host}:{port}"
        
        # Try health check endpoint
        response = requests.get(f"{base_url}/api/health", timeout=10, verify=False)
        
        if response.status_code != 200:
            return False
        
        # Try authentication
        auth_response = requests.post(
            f"{base_url}/api/auth/login",
            json={'username': username, 'password': password},
            timeout=10,
            verify=False
        )
        
        return auth_response.status_code == 200
    
    except Exception:
        return False


def get_saved_credentials_info() -> Optional[Dict[str, str]]:
    """
    Get information about saved credentials without exposing password.
    
    Returns:
        Dictionary with credential info (without password)
    """
    credentials = load_credentials()
    
    if not credentials:
        return None
    
    return {
        'host': credentials.get('host', 'unknown'),
        'port': str(credentials.get('port', 'unknown')),
        'username': credentials.get('username', 'unknown')
    }
