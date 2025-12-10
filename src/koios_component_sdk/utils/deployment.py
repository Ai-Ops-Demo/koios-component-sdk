"""
Component deployment utilities for the Koios Component SDK.

This module provides functionality for deploying components to Koios servers,
including authentication, upload, and installation management.
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
import base64
import time

from ..exceptions import DeploymentError, ConnectionError
from .packaging import ComponentPackager


class ComponentDeployer:
    """
    Handles deployment of Koios components to servers.
    
    This class provides functionality to upload and install component packages
    on Koios servers via REST API.
    """
    
    def __init__(self, host: str, port: int = 443, use_ssl: bool = True):
        """
        Initialize the deployer.
        
        Args:
            host: Koios server hostname
            port: Server port
            use_ssl: Whether to use HTTPS
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.base_url = f"{'https' if use_ssl else 'http'}://{host}:{port}"
        self.session = requests.Session()
        self.auth_token: Optional[str] = None
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with the Koios server.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if authentication successful
            
        Raises:
            DeploymentError: If authentication fails
        """
        try:
            auth_url = f"{self.base_url}/api/auth/login"
            
            response = self.session.post(
                auth_url,
                json={
                    'username': username,
                    'password': password
                },
                timeout=30
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get('token')
                
                # Set authorization header for future requests
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                
                return True
            else:
                raise DeploymentError(
                    f"Authentication failed: {response.status_code} - {response.text}",
                    target_host=self.host
                )
                
        except requests.exceptions.RequestException as e:
            raise DeploymentError(f"Connection error during authentication: {str(e)}", target_host=self.host)
        except Exception as e:
            raise DeploymentError(f"Authentication error: {str(e)}", target_host=self.host)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the Koios server.
        
        Returns:
            Dictionary with connection test results
        """
        try:
            health_url = f"{self.base_url}/api/health"
            
            response = self.session.get(health_url, timeout=10)
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'server_info': response.json() if response.status_code == 200 else None
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_component(self, package_path: str, 
                        overwrite: bool = False) -> Dict[str, Any]:
        """
        Upload component package to server.
        
        Args:
            package_path: Path to component package file
            overwrite: Whether to overwrite existing component
            
        Returns:
            Upload result dictionary
            
        Raises:
            DeploymentError: If upload fails
        """
        if not self.auth_token:
            raise DeploymentError("Not authenticated. Call authenticate() first.", target_host=self.host)
        
        package_file = Path(package_path)
        if not package_file.exists():
            raise DeploymentError(f"Package file not found: {package_path}")
        
        try:
            # Get package info
            package_info = ComponentPackager.get_package_info(package_path)
            component_name = package_info['component_manifest']['name']
            component_version = package_info['component_manifest']['version']
            
            # Check if component already exists
            if not overwrite:
                existing = self._check_component_exists(component_name, component_version)
                if existing:
                    raise DeploymentError(
                        f"Component {component_name} v{component_version} already exists. "
                        f"Use overwrite=True to replace it."
                    )
            
            # Upload package
            upload_url = f"{self.base_url}/api/components/upload"
            
            with open(package_file, 'rb') as f:
                files = {
                    'package': (package_file.name, f, 'application/octet-stream')
                }
                data = {
                    'overwrite': str(overwrite).lower()
                }
                
                response = self.session.post(
                    upload_url,
                    files=files,
                    data=data,
                    timeout=300  # 5 minutes for large packages
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise DeploymentError(
                    f"Upload failed: {response.status_code} - {response.text}",
                    target_host=self.host
                )
                
        except DeploymentError:
            raise
        except Exception as e:
            raise DeploymentError(f"Upload error: {str(e)}", target_host=self.host)
    
    def install_component(self, component_name: str, component_version: str,
                         configuration: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Install uploaded component on server.
        
        Args:
            component_name: Name of component to install
            component_version: Version of component to install
            configuration: Optional component configuration
            
        Returns:
            Installation result dictionary
        """
        if not self.auth_token:
            raise DeploymentError("Not authenticated. Call authenticate() first.", target_host=self.host)
        
        try:
            install_url = f"{self.base_url}/api/components/install"
            
            install_data = {
                'name': component_name,
                'version': component_version,
                'configuration': configuration or {}
            }
            
            response = self.session.post(
                install_url,
                json=install_data,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise DeploymentError(
                    f"Installation failed: {response.status_code} - {response.text}",
                    target_host=self.host
                )
                
        except DeploymentError:
            raise
        except Exception as e:
            raise DeploymentError(f"Installation error: {str(e)}", target_host=self.host)
    
    def deploy_component(self, package_path: str, 
                        configuration: Optional[Dict[str, Any]] = None,
                        overwrite: bool = False) -> Dict[str, Any]:
        """
        Complete deployment: upload and install component.
        
        Args:
            package_path: Path to component package file
            configuration: Optional component configuration
            overwrite: Whether to overwrite existing component
            
        Returns:
            Deployment result dictionary
        """
        try:
            # Upload component
            upload_result = self.upload_component(package_path, overwrite)
            
            if not upload_result.get('success', False):
                raise DeploymentError(f"Upload failed: {upload_result.get('error', 'Unknown error')}")
            
            # Get component info from upload result
            component_info = upload_result.get('component_info', {})
            component_name = component_info.get('name')
            component_version = component_info.get('version')
            
            if not component_name or not component_version:
                raise DeploymentError("Could not determine component name/version from upload result")
            
            # Install component
            install_result = self.install_component(component_name, component_version, configuration)
            
            return {
                'success': True,
                'upload_result': upload_result,
                'install_result': install_result,
                'component_name': component_name,
                'component_version': component_version
            }
            
        except DeploymentError:
            raise
        except Exception as e:
            raise DeploymentError(f"Deployment error: {str(e)}", target_host=self.host)
    
    def list_components(self) -> List[Dict[str, Any]]:
        """
        List installed components on server.
        
        Returns:
            List of component information dictionaries
        """
        if not self.auth_token:
            raise DeploymentError("Not authenticated. Call authenticate() first.", target_host=self.host)
        
        try:
            list_url = f"{self.base_url}/api/components"
            
            response = self.session.get(list_url, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('components', [])
            else:
                raise DeploymentError(
                    f"Failed to list components: {response.status_code} - {response.text}",
                    target_host=self.host
                )
                
        except DeploymentError:
            raise
        except Exception as e:
            raise DeploymentError(f"List components error: {str(e)}", target_host=self.host)
    
    def uninstall_component(self, component_name: str, 
                           component_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Uninstall component from server.
        
        Args:
            component_name: Name of component to uninstall
            component_version: Optional specific version to uninstall
            
        Returns:
            Uninstall result dictionary
        """
        if not self.auth_token:
            raise DeploymentError("Not authenticated. Call authenticate() first.", target_host=self.host)
        
        try:
            uninstall_url = f"{self.base_url}/api/components/uninstall"
            
            uninstall_data = {
                'name': component_name
            }
            
            if component_version:
                uninstall_data['version'] = component_version
            
            response = self.session.post(
                uninstall_url,
                json=uninstall_data,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise DeploymentError(
                    f"Uninstall failed: {response.status_code} - {response.text}",
                    target_host=self.host
                )
                
        except DeploymentError:
            raise
        except Exception as e:
            raise DeploymentError(f"Uninstall error: {str(e)}", target_host=self.host)
    
    def get_component_status(self, component_name: str) -> Dict[str, Any]:
        """
        Get status of installed component.
        
        Args:
            component_name: Name of component
            
        Returns:
            Component status dictionary
        """
        if not self.auth_token:
            raise DeploymentError("Not authenticated. Call authenticate() first.", target_host=self.host)
        
        try:
            status_url = f"{self.base_url}/api/components/{component_name}/status"
            
            response = self.session.get(status_url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {'exists': False, 'error': 'Component not found'}
            else:
                raise DeploymentError(
                    f"Failed to get component status: {response.status_code} - {response.text}",
                    target_host=self.host
                )
                
        except DeploymentError:
            raise
        except Exception as e:
            raise DeploymentError(f"Status check error: {str(e)}", target_host=self.host)
    
    def _check_component_exists(self, component_name: str, 
                               component_version: str) -> bool:
        """Check if component version already exists on server."""
        try:
            components = self.list_components()
            
            for component in components:
                if (component.get('name') == component_name and 
                    component.get('version') == component_version):
                    return True
            
            return False
            
        except Exception:
            # If we can't check, assume it doesn't exist
            return False
    
    def logout(self):
        """Logout and clear authentication."""
        if self.auth_token:
            try:
                logout_url = f"{self.base_url}/api/auth/logout"
                self.session.post(logout_url, timeout=10)
            except Exception:
                pass  # Ignore logout errors
            
            self.auth_token = None
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
