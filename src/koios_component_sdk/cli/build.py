"""
Component build CLI command.

This module provides the 'build' command for building component packages
from component directories.
"""

import click
import sys
from pathlib import Path

from ..utils.packaging import ComponentPackager
from ..exceptions import PackagingError


@click.command()
@click.argument('component_dir', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output directory for package')
@click.option('--compress/--no-compress', default=True, help='Compress package (default: True)')
@click.option('--validate/--no-validate', default=True, help='Validate component before building')
@click.option('--runtime-requirements', type=click.Path(exists=True), 
              help='Path to runtime-available.txt for dependency validation')
def build_package(component_dir: str, output: str, compress: bool, validate: bool, 
                  runtime_requirements: str):
    """
    Build a component package from component directory.
    
    This command creates a deployable package (.kcp file) from a component
    directory. The package includes all component files and metadata.
    
    Examples:
        koios-component build ./my_component
        koios-component build ./my_component --output ./packages
        koios-component build ./my_component --no-compress
    """
    try:
        package_path = build_package_impl(component_dir, output, compress, validate, runtime_requirements)
        click.echo(f"Package built successfully: {package_path}")
        
    except PackagingError as e:
        click.echo(f"Build failed: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


def build_package_impl(component_dir: str, output: str = None, 
                      compress: bool = True, validate: bool = True,
                      runtime_requirements: str = None) -> str:
    """
    Implementation function for building packages.
    
    Args:
        component_dir: Path to component directory
        output: Output directory for package
        compress: Whether to compress package
        validate: Whether to validate before building
        runtime_requirements: Optional path to runtime-available.txt for dependency validation
        
    Returns:
        Path to created package
    """
    component_path = Path(component_dir)
    
    # Create packager
    packager = ComponentPackager(str(component_path))
    
    # Validate if requested
    if validate:
        click.echo("Validating component...")
        validation_errors = packager.validate(runtime_requirements_path=runtime_requirements)
        
        if validation_errors:
            click.echo("Validation failed:")
            for error in validation_errors:
                click.echo(f"  - {error}")
            raise PackagingError("Component validation failed")
        
        click.echo("Component validation passed")
    
    # Build package
    click.echo("Building package...")
    package_path = packager.build(output_dir=output, compress=compress)
    
    return package_path


# Export for use in main CLI
__all__ = ['build_package', 'build_package_impl']
