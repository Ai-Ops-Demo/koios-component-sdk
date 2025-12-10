"""
Component creation CLI command.

This module provides the 'create' command for generating new Koios components
from templates with interactive prompts and validation.
"""

import click
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
import re

from ..utils.templates import TemplateManager, get_available_templates
from ..exceptions import KoiosComponentError


@click.command()
@click.option('--name', prompt='Component name', help='Name of the component')
@click.option('--category', 
              type=click.Choice(['control', 'logic', 'communication', 'processing']), 
              prompt='Component category', 
              help='Component category')
@click.option('--author', prompt='Author name', help='Component author')
@click.option('--description', prompt='Description', help='Component description')
@click.option('--version', default='1.0.0', help='Initial version (default: 1.0.0)')
@click.option('--template', help='Specific template to use (optional)')
@click.option('--output-dir', '-o', help='Output directory (default: current directory)')
@click.option('--interactive/--no-interactive', default=True, 
              help='Interactive mode for additional configuration')
@click.option('--force', is_flag=True, help='Overwrite existing component directory')
def create_component(name: str, category: str, author: str, description: str, 
                    version: str, template: Optional[str], output_dir: Optional[str],
                    interactive: bool, force: bool):
    """
    Create a new Koios component from template.
    
    This command creates a new component directory with all necessary files
    based on the selected category and template. It provides interactive
    prompts for configuration and validates the input.
    
    Examples:
        koios-component create --name "Advanced PID" --category control
        koios-component create --template pid_controller --output-dir ./components
    """
    try:
        # Validate component name
        if not _validate_component_name(name):
            click.echo("Error: Component name must contain only letters, numbers, spaces, and hyphens.", err=True)
            sys.exit(1)
        
        # Set up paths
        output_path = Path(output_dir) if output_dir else Path.cwd()
        component_dir_name = _sanitize_name(name)
        component_path = output_path / component_dir_name
        
        # Check if directory already exists
        if component_path.exists() and not force:
            if not click.confirm(f"Directory '{component_path}' already exists. Overwrite?"):
                click.echo("Component creation cancelled.")
                sys.exit(0)
        
        # Get available templates
        available_templates = get_available_templates()
        category_templates = [t for t in available_templates if t['category'] == category]
        
        if not category_templates:
            click.echo(f"Error: No templates available for category '{category}'.", err=True)
            sys.exit(1)
        
        # Select template
        selected_template = None
        if template:
            # Use specified template
            selected_template = next((t for t in category_templates if t['name'] == template), None)
            if not selected_template:
                click.echo(f"Error: Template '{template}' not found for category '{category}'.", err=True)
                click.echo(f"Available templates: {', '.join(t['name'] for t in category_templates)}")
                sys.exit(1)
        else:
            # Interactive template selection
            if len(category_templates) == 1:
                selected_template = category_templates[0]
                click.echo(f"Using template: {selected_template['name']}")
            else:
                click.echo(f"Available templates for {category}:")
                for i, tmpl in enumerate(category_templates, 1):
                    click.echo(f"  {i}. {tmpl['name']}: {tmpl['description']}")
                
                while True:
                    try:
                        choice = click.prompt("Select template", type=int)
                        if 1 <= choice <= len(category_templates):
                            selected_template = category_templates[choice - 1]
                            break
                        else:
                            click.echo("Invalid choice. Please try again.")
                    except (ValueError, click.Abort):
                        click.echo("Invalid input. Please enter a number.")
        
        # Gather template context
        context = {
            'component_name': name,
            'component_class': _to_class_name(name),
            'category': category,
            'author': author,
            'description': description,
            'version': version,
            'package_name': component_dir_name,
            'creation_date': _get_current_date(),
        }
        
        # Interactive configuration
        if interactive:
            context.update(_gather_interactive_config(selected_template, category))
        
        # Create component from template
        template_manager = TemplateManager()
        
        click.echo(f"Creating component '{name}' in {component_path}...")
        
        created_files = template_manager.create_component(
            template_name=selected_template['name'],
            output_path=component_path,
            context=context,
            force=force
        )
        
        click.echo(f"✅ Component '{name}' created successfully!")
        click.echo(f"📁 Location: {component_path}")
        click.echo(f"📄 Files created: {len(created_files)}")
        
        # Show next steps
        _show_next_steps(component_path, component_dir_name)
        
    except KoiosComponentError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


def _validate_component_name(name: str) -> bool:
    """Validate component name format."""
    # Allow letters, numbers, spaces, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9\s\-_]+$'
    return bool(re.match(pattern, name.strip()))


def _sanitize_name(name: str) -> str:
    """Convert component name to valid directory name."""
    # Replace spaces with underscores, remove special characters
    sanitized = re.sub(r'[^\w\-_]', '_', name.strip())
    sanitized = re.sub(r'_+', '_', sanitized)  # Remove multiple underscores
    return sanitized.lower()


def _to_class_name(name: str) -> str:
    """Convert component name to valid Python class name."""
    # Split on spaces and special characters, capitalize each word
    words = re.findall(r'\w+', name)
    return ''.join(word.capitalize() for word in words)


def _get_current_date() -> str:
    """Get current date in ISO format."""
    from datetime import datetime
    return datetime.now().isoformat()


def _gather_interactive_config(template: Dict[str, Any], category: str) -> Dict[str, Any]:
    """Gather additional configuration through interactive prompts."""
    config = {}
    
    # Category-specific configuration
    if category == 'control':
        config.update(_gather_control_config())
    elif category == 'communication':
        config.update(_gather_communication_config())
    elif category == 'processing':
        config.update(_gather_processing_config())
    elif category == 'logic':
        config.update(_gather_logic_config())
    
    # Template-specific configuration
    template_config = template.get('config_prompts', {})
    for key, prompt_info in template_config.items():
        if isinstance(prompt_info, str):
            # Simple string prompt
            value = click.prompt(prompt_info, default='')
        elif isinstance(prompt_info, dict):
            # Complex prompt with validation
            prompt_text = prompt_info.get('prompt', key)
            default_value = prompt_info.get('default')
            value_type = prompt_info.get('type', str)
            
            if value_type == bool:
                value = click.confirm(prompt_text, default=default_value)
            elif value_type == int:
                value = click.prompt(prompt_text, type=int, default=default_value)
            elif value_type == float:
                value = click.prompt(prompt_text, type=float, default=default_value)
            else:
                value = click.prompt(prompt_text, default=default_value or '')
        
        config[key] = value
    
    return config


def _gather_control_config() -> Dict[str, Any]:
    """Gather configuration for control components."""
    config = {}
    
    if click.confirm("Configure default control parameters?", default=True):
        config['default_scan_rate'] = click.prompt("Default scan rate (seconds)", type=float, default=1.0)
        config['output_min'] = click.prompt("Output minimum", type=float, default=0.0)
        config['output_max'] = click.prompt("Output maximum", type=float, default=100.0)
        config['has_manual_mode'] = click.confirm("Include manual mode support?", default=True)
    
    return config


def _gather_communication_config() -> Dict[str, Any]:
    """Gather configuration for communication components."""
    config = {}
    
    if click.confirm("Configure default connection parameters?", default=True):
        config['default_host'] = click.prompt("Default host", default='localhost')
        config['default_port'] = click.prompt("Default port", type=int, default=502)
        config['default_timeout'] = click.prompt("Default timeout (seconds)", type=float, default=5.0)
        config['supports_async'] = click.confirm("Support async operations?", default=True)
    
    return config


def _gather_processing_config() -> Dict[str, Any]:
    """Gather configuration for processing components."""
    config = {}
    
    if click.confirm("Configure default processing parameters?", default=True):
        config['default_buffer_size'] = click.prompt("Default buffer size", type=int, default=1000)
        config['default_batch_size'] = click.prompt("Default batch size", type=int, default=1)
        config['supports_streaming'] = click.confirm("Support streaming processing?", default=False)
    
    return config


def _gather_logic_config() -> Dict[str, Any]:
    """Gather configuration for logic components."""
    config = {}
    
    if click.confirm("Configure default logic parameters?", default=True):
        config['default_evaluation_interval'] = click.prompt("Default evaluation interval (seconds)", type=float, default=1.0)
        config['supports_state_machine'] = click.confirm("Include state machine support?", default=True)
        config['auto_reset'] = click.confirm("Support auto-reset?", default=False)
    
    return config


def _show_next_steps(component_path: Path, component_name: str):
    """Show next steps after component creation."""
    click.echo("\n📋 Next steps:")
    click.echo(f"  1. cd {component_path}")
    click.echo("  2. Edit component.py to implement your logic")
    click.echo("  3. Update koios_component.json with your parameters")
    click.echo("  4. Test your component:")
    click.echo(f"     koios-component test {component_path}")
    click.echo("  5. Build your component:")
    click.echo(f"     koios-component build {component_path}")
    
    click.echo("\n📚 Documentation:")
    click.echo("  - See README.md for component structure")
    click.echo("  - Check examples/ directory for reference implementations")
    click.echo("  - Visit https://docs.ai-op.com for full documentation")


# Export for use in main CLI
__all__ = ['create_component']
