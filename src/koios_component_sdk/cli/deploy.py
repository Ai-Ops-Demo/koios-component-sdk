"""
Component deployment CLI command.

This module provides the 'deploy' command for deploying components
to Koios servers.
"""

import click
import sys
from pathlib import Path
from typing import Optional

from ..utils.deployment import ComponentDeployer
from ..exceptions import DeploymentError


@click.command()
@click.argument('package_path', type=click.Path(exists=True))
@click.option('--host', required=True, help='Koios server hostname')
@click.option('--port', default=443, help='Server port (default: 443)')
@click.option('--no-ssl', is_flag=True, help='Disable SSL/HTTPS')
@click.option('--username', help='Username for authentication')
@click.option('--password', help='Password for authentication')
@click.option('--overwrite', is_flag=True, help='Overwrite existing component')
@click.option('--config-file', help='Component configuration file (JSON)')
def deploy_component(package_path: str, host: str, port: int, no_ssl: bool,
                    username: Optional[str], password: Optional[str],
                    overwrite: bool, config_file: Optional[str]):
    """
    Deploy a component package to Koios server.
    
    This command uploads and installs a component package on a Koios server.
    Authentication credentials can be provided via options or will be prompted.
    
    Examples:
        koios-component deploy my_component-1.0.0.kcp --host koios.example.com
        koios-component deploy my_component-1.0.0.kcp --host koios.example.com --overwrite
        koios-component deploy my_component-1.0.0.kcp --host koios.example.com --config-file config.json
    """
    try:
        # Load configuration if provided
        configuration = None
        if config_file:
            config_path = Path(config_file)
            if not config_path.exists():
                click.echo(f"❌ Configuration file not found: {config_file}", err=True)
                sys.exit(1)
            
            import json
            try:
                with open(config_path, 'r') as f:
                    configuration = json.load(f)
                click.echo(f"📋 Loaded configuration from {config_file}")
            except Exception as e:
                click.echo(f"❌ Error loading configuration: {str(e)}", err=True)
                sys.exit(1)
        
        # Create deployer
        use_ssl = not no_ssl
        deployer = ComponentDeployer(host, port, use_ssl)
        
        # Test connection first
        click.echo("🔌 Testing connection...")
        connection_test = deployer.test_connection()
        
        if not connection_test['success']:
            click.echo(f"❌ Connection failed: {connection_test.get('error', 'Unknown error')}", err=True)
            sys.exit(1)
        
        click.echo(f"✅ Connected to {host}:{port} (response time: {connection_test['response_time']:.2f}s)")
        
        # Get authentication credentials
        if not username:
            username = click.prompt("Username")
        
        if not password:
            password = click.prompt("Password", hide_input=True)
        
        # Authenticate
        click.echo("🔐 Authenticating...")
        if not deployer.authenticate(username, password):
            click.echo("❌ Authentication failed", err=True)
            sys.exit(1)
        
        click.echo("✅ Authentication successful")
        
        # Deploy component
        click.echo("🚀 Deploying component...")
        
        result = deployer.deploy_component(
            package_path=package_path,
            configuration=configuration,
            overwrite=overwrite
        )
        
        if result['success']:
            component_name = result['component_name']
            component_version = result['component_version']
            
            click.echo(f"✅ Component deployed successfully!")
            click.echo(f"   Name: {component_name}")
            click.echo(f"   Version: {component_version}")
            click.echo(f"   Server: {host}:{port}")
            
            # Show component status
            try:
                status = deployer.get_component_status(component_name)
                if status.get('exists', False):
                    click.echo(f"   Status: {status.get('status', 'Unknown')}")
            except Exception:
                pass  # Ignore status check errors
        else:
            click.echo("❌ Deployment failed", err=True)
            sys.exit(1)
        
        # Logout
        deployer.logout()
        
    except DeploymentError as e:
        click.echo(f"❌ Deployment error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@click.command()
@click.option('--host', required=True, help='Koios server hostname')
@click.option('--port', default=443, help='Server port (default: 443)')
@click.option('--no-ssl', is_flag=True, help='Disable SSL/HTTPS')
@click.option('--username', help='Username for authentication')
@click.option('--password', help='Password for authentication')
def list_components(host: str, port: int, no_ssl: bool,
                   username: Optional[str], password: Optional[str]):
    """
    List components installed on Koios server.
    
    Examples:
        koios-component list --host koios.example.com
    """
    try:
        # Create deployer
        use_ssl = not no_ssl
        deployer = ComponentDeployer(host, port, use_ssl)
        
        # Get authentication credentials
        if not username:
            username = click.prompt("Username")
        
        if not password:
            password = click.prompt("Password", hide_input=True)
        
        # Authenticate
        if not deployer.authenticate(username, password):
            click.echo("❌ Authentication failed", err=True)
            sys.exit(1)
        
        # List components
        components = deployer.list_components()
        
        if components:
            click.echo(f"📦 Components on {host}:")
            for component in components:
                name = component.get('name', 'Unknown')
                version = component.get('version', 'Unknown')
                status = component.get('status', 'Unknown')
                click.echo(f"  - {name} v{version} ({status})")
        else:
            click.echo("No components found on server")
        
        # Logout
        deployer.logout()
        
    except DeploymentError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@click.command()
@click.argument('component_name')
@click.option('--version', help='Specific version to uninstall')
@click.option('--host', required=True, help='Koios server hostname')
@click.option('--port', default=443, help='Server port (default: 443)')
@click.option('--no-ssl', is_flag=True, help='Disable SSL/HTTPS')
@click.option('--username', help='Username for authentication')
@click.option('--password', help='Password for authentication')
@click.option('--force', is_flag=True, help='Force uninstall without confirmation')
def uninstall_component(component_name: str, version: Optional[str],
                       host: str, port: int, no_ssl: bool,
                       username: Optional[str], password: Optional[str],
                       force: bool):
    """
    Uninstall a component from Koios server.
    
    Examples:
        koios-component uninstall "My Component" --host koios.example.com
        koios-component uninstall "My Component" --version 1.0.0 --host koios.example.com
    """
    try:
        # Confirm uninstall
        if not force:
            version_str = f" v{version}" if version else ""
            if not click.confirm(f"Uninstall component '{component_name}{version_str}'?"):
                click.echo("Uninstall cancelled")
                return
        
        # Create deployer
        use_ssl = not no_ssl
        deployer = ComponentDeployer(host, port, use_ssl)
        
        # Get authentication credentials
        if not username:
            username = click.prompt("Username")
        
        if not password:
            password = click.prompt("Password", hide_input=True)
        
        # Authenticate
        if not deployer.authenticate(username, password):
            click.echo("❌ Authentication failed", err=True)
            sys.exit(1)
        
        # Uninstall component
        result = deployer.uninstall_component(component_name, version)
        
        if result.get('success', False):
            click.echo(f"✅ Component '{component_name}' uninstalled successfully")
        else:
            error_msg = result.get('error', 'Unknown error')
            click.echo(f"❌ Uninstall failed: {error_msg}", err=True)
            sys.exit(1)
        
        # Logout
        deployer.logout()
        
    except DeploymentError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


# Export for use in main CLI
__all__ = ['deploy_component', 'list_components', 'uninstall_component']
