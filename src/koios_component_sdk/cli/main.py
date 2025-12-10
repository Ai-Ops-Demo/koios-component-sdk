"""
Main CLI entry point for the Koios Component SDK.

This module provides the main command-line interface for the SDK,
including commands for creating, testing, building, and deploying components.
"""

import click
import sys
from pathlib import Path

from .create import create_component
from .build import build_package
from .test import test_component
from .deploy import deploy_component
from .validate import validate_component


@click.group()
@click.version_option(version="1.0.0", prog_name="koios-component")
def cli():
    """
    Koios Component SDK - Tools for developing custom Koios components.
    
    This CLI provides tools to create, test, build, and deploy custom components
    for the Koios industrial automation platform.
    
    Examples:
        koios-component create --name "My PID Controller" --category control
        koios-component test ./my_component
        koios-component build ./my_component
        koios-component deploy my_component-1.0.0.kcp --host https://koios.example.com
    """
    pass


# Add subcommands
cli.add_command(create_component, name='create')
cli.add_command(build_package, name='build')
cli.add_command(test_component, name='test')
cli.add_command(deploy_component, name='deploy')
cli.add_command(validate_component, name='validate')


@cli.command()
@click.option('--list-templates', is_flag=True, help='List available component templates')
def templates(list_templates):
    """Manage component templates."""
    if list_templates:
        from ..utils.templates import get_available_templates
        
        templates = get_available_templates()
        if templates:
            click.echo("Available component templates:")
            for template in templates:
                click.echo(f"  - {template['name']}: {template['description']}")
        else:
            click.echo("No templates available.")
    else:
        click.echo("Use --list-templates to see available templates.")


@cli.command()
@click.argument('component_dir', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file for documentation')
@click.option('--format', type=click.Choice(['markdown', 'html', 'json']), 
              default='markdown', help='Documentation format')
def docs(component_dir, output, format):
    """Generate documentation for a component."""
    from ..utils.documentation import generate_docs
    
    try:
        component_path = Path(component_dir)
        docs_content = generate_docs(component_path, format)
        
        if output:
            output_path = Path(output)
            output_path.write_text(docs_content)
            click.echo(f"Documentation written to {output_path}")
        else:
            click.echo(docs_content)
            
    except Exception as e:
        click.echo(f"Error generating documentation: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='localhost', help='Koios server host')
@click.option('--port', default=443, help='Koios server port')
@click.option('--username', prompt=True, help='Username for authentication')
@click.option('--password', prompt=True, hide_input=True, help='Password for authentication')
def login(host, port, username, password):
    """Login to a Koios server for deployment."""
    from ..utils.auth import save_credentials, test_connection
    
    try:
        # Test connection
        if test_connection(host, port, username, password):
            # Save credentials
            save_credentials(host, port, username, password)
            click.echo(f"Successfully logged in to {host}:{port}")
        else:
            click.echo("Login failed. Please check your credentials.", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Login error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def logout():
    """Logout from Koios server."""
    from ..utils.auth import clear_credentials
    
    try:
        clear_credentials()
        click.echo("Successfully logged out.")
    except Exception as e:
        click.echo(f"Logout error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('component_dir', type=click.Path(exists=True))
@click.option('--watch', '-w', is_flag=True, help='Watch for changes and auto-rebuild')
@click.option('--output-dir', '-o', help='Output directory for built packages')
def dev(component_dir, watch, output_dir):
    """Development mode with auto-rebuild and testing."""
    from ..utils.dev_server import start_dev_server
    
    try:
        component_path = Path(component_dir)
        output_path = Path(output_dir) if output_dir else component_path.parent
        
        if watch:
            click.echo(f"Starting development server for {component_path}")
            click.echo("Watching for changes... Press Ctrl+C to stop.")
            start_dev_server(component_path, output_path)
        else:
            # Single build and test
            from .build import build_package_impl
            from .test import test_component_impl
            
            click.echo("Running tests...")
            test_result = test_component_impl(component_path)
            
            if test_result.success:
                click.echo("✅ Tests passed!")
                
                click.echo("Building package...")
                package_path = build_package_impl(component_path, output_path)
                click.echo(f"✅ Package built: {package_path}")
            else:
                click.echo("❌ Tests failed:")
                for error in test_result.errors:
                    click.echo(f"  - {error}")
                sys.exit(1)
                
    except KeyboardInterrupt:
        click.echo("\nDevelopment server stopped.")
    except Exception as e:
        click.echo(f"Development server error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--category', type=click.Choice(['control', 'logic', 'communication', 'processing']),
              help='Filter examples by category')
def examples(category):
    """List and describe example components."""
    from ..utils.examples import get_examples, describe_example
    
    try:
        examples_list = get_examples(category)
        
        if examples_list:
            click.echo("Available example components:")
            for example in examples_list:
                click.echo(f"\n{example['name']} ({example['category']})")
                click.echo(f"  Description: {example['description']}")
                click.echo(f"  Location: {example['path']}")
                
                if click.confirm(f"Show detailed description for {example['name']}?", default=False):
                    details = describe_example(example['path'])
                    click.echo(f"\n{details}")
        else:
            filter_msg = f" in category '{category}'" if category else ""
            click.echo(f"No example components found{filter_msg}.")
            
    except Exception as e:
        click.echo(f"Error listing examples: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
