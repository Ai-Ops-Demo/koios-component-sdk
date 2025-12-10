"""
Component validation CLI command.

This module provides the 'validate' command for validating component
structure, configuration, and code without running tests.
"""

import click
import sys
from pathlib import Path
import json

from ..utils.validation import validate_component_structure, validate_component_manifest
from ..exceptions import ValidationError


@click.command()
@click.argument('component_dir', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--check-syntax', is_flag=True, help='Check Python syntax')
@click.option('--check-imports', is_flag=True, help='Check import statements')
def validate_component(component_dir: str, verbose: bool, 
                      check_syntax: bool, check_imports: bool):
    """
    Validate component structure and configuration.
    
    This command performs comprehensive validation of a component without
    running it, checking structure, manifest, and optionally code syntax.
    
    Examples:
        koios-component validate ./my_component
        koios-component validate ./my_component --verbose
        koios-component validate ./my_component --check-syntax --check-imports
    """
    try:
        component_path = Path(component_dir)
        errors = []
        warnings = []
        
        if verbose:
            click.echo(f"Validating component: {component_path}")
        
        # Basic structure validation
        if verbose:
            click.echo("Checking directory structure...")
        
        structure_errors = validate_component_structure(str(component_path))
        if structure_errors:
            errors.extend(structure_errors)
        elif verbose:
            click.echo("Directory structure is valid")
        
        # Manifest validation
        manifest_path = component_path / "koios_component.json"
        manifest = None
        
        if manifest_path.exists():
            if verbose:
                click.echo("Validating manifest...")
            
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                validate_component_manifest(manifest)
                
                if verbose:
                    click.echo("Manifest is valid")
                    click.echo(f"   Name: {manifest.get('name', 'Unknown')}")
                    click.echo(f"   Version: {manifest.get('version', 'Unknown')}")
                    click.echo(f"   Category: {manifest.get('category', 'Unknown')}")
                
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in manifest: {str(e)}")
            except ValidationError as e:
                errors.append(f"Invalid manifest: {str(e)}")
            except Exception as e:
                errors.append(f"Error reading manifest: {str(e)}")
        
        # Parameter validation
        if manifest and verbose:
            click.echo("Checking parameters...")
            
            parameters = manifest.get('parameters', {})
            if parameters:
                click.echo(f"   Found {len(parameters)} parameters:")
                for param_name, param_config in parameters.items():
                    param_type = param_config.get('type', 'unknown')
                    required = param_config.get('required', False)
                    default = param_config.get('default')
                    
                    req_str = "required" if required else "optional"
                    default_str = f", default={default}" if default is not None else ""
                    
                    click.echo(f"     - {param_name}: {param_type} ({req_str}{default_str})")
            else:
                click.echo("   No parameters defined")
        
        # Syntax checking
        if check_syntax:
            if verbose:
                click.echo("Checking Python syntax...")
            
            syntax_errors = _check_python_syntax(component_path)
            if syntax_errors:
                errors.extend(syntax_errors)
            elif verbose:
                click.echo("Python syntax is valid")
        
        # Import checking
        if check_imports:
            if verbose:
                click.echo("Checking imports...")
            
            import_warnings = _check_imports(component_path, manifest)
            if import_warnings:
                warnings.extend(import_warnings)
            elif verbose:
                click.echo("Imports look good")
        
        # Entry point validation
        if manifest:
            entry_point = manifest.get('entry_point')
            if entry_point:
                if verbose:
                    click.echo(f"Validating entry point: {entry_point}")
                
                entry_errors = _validate_entry_point(component_path, entry_point)
                if entry_errors:
                    errors.extend(entry_errors)
                elif verbose:
                    click.echo("Entry point is valid")
        
        # Dependencies validation
        if manifest:
            dependencies = manifest.get('dependencies', [])
            if dependencies and verbose:
                click.echo(f"Found {len(dependencies)} dependencies:")
                for dep in dependencies:
                    click.echo(f"   - {dep}")
        
        # Summary
        if errors:
            click.echo(f"\nValidation failed with {len(errors)} error(s):")
            for error in errors:
                click.echo(f"  - {error}")
            
            if warnings:
                click.echo(f"\n{len(warnings)} warning(s):")
                for warning in warnings:
                    click.echo(f"  - {warning}")
            
            sys.exit(1)
        else:
            click.echo("\nComponent validation passed!")
            
            if warnings:
                click.echo(f"\n{len(warnings)} warning(s):")
                for warning in warnings:
                    click.echo(f"  - {warning}")
        
    except Exception as e:
        click.echo(f"Validation error: {str(e)}", err=True)
        sys.exit(1)


def _check_python_syntax(component_path: Path) -> list:
    """Check Python syntax in component files."""
    errors = []
    
    # Find all Python files
    python_files = list(component_path.glob("*.py"))
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Compile to check syntax
            compile(code, str(py_file), 'exec')
            
        except SyntaxError as e:
            errors.append(f"Syntax error in {py_file.name}: {str(e)}")
        except UnicodeDecodeError as e:
            errors.append(f"Encoding error in {py_file.name}: {str(e)}")
        except Exception as e:
            errors.append(f"Error checking {py_file.name}: {str(e)}")
    
    return errors


def _check_imports(component_path: Path, manifest: dict) -> list:
    """Check import statements in component files."""
    warnings = []
    
    # Find main component file
    entry_point = manifest.get('entry_point', '') if manifest else ''
    if entry_point:
        module_name = entry_point.split('.')[0]
        main_file = component_path / f"{module_name}.py"
        
        if main_file.exists():
            try:
                with open(main_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Check for SDK imports
                if 'koios_component_sdk' not in code:
                    warnings.append(f"No Koios SDK imports found in {main_file.name}")
                
                # Check for common import issues
                lines = code.split('\n')
                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        # Check for relative imports that might cause issues
                        if line.startswith('from .') and 'koios_component_sdk' not in line:
                            warnings.append(f"Relative import in {main_file.name}:{i} might cause issues")
                
            except Exception as e:
                warnings.append(f"Could not check imports in {main_file.name}: {str(e)}")
    
    return warnings


def _validate_entry_point(component_path: Path, entry_point: str) -> list:
    """Validate component entry point."""
    errors = []
    
    try:
        # Parse entry point (e.g., "component.MyComponent")
        parts = entry_point.split('.')
        if len(parts) < 2:
            errors.append(f"Invalid entry point format: {entry_point}")
            return errors
        
        module_name = parts[0]
        class_name = '.'.join(parts[1:])
        
        # Check if module file exists
        module_path = component_path / f"{module_name}.py"
        if not module_path.exists():
            errors.append(f"Entry point module not found: {module_name}.py")
            return errors
        
        # Try to import and find the class
        try:
            import sys
            import importlib.util
            
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if not spec or not spec.loader:
                errors.append(f"Could not load module: {module_name}")
                return errors
            
            module = importlib.util.module_from_spec(spec)
            
            # Add component directory to sys.path temporarily
            sys.path.insert(0, str(component_path))
            try:
                spec.loader.exec_module(module)
            finally:
                if str(component_path) in sys.path:
                    sys.path.remove(str(component_path))
            
            # Check if class exists
            if not hasattr(module, class_name):
                errors.append(f"Entry point class not found: {class_name}")
                return errors
            
            # Check if class is a valid component
            component_class = getattr(module, class_name)
            
            # Basic checks
            if not hasattr(component_class, 'metadata'):
                errors.append(f"Component class {class_name} missing 'metadata' property")
            
            if not hasattr(component_class, 'parameter_definitions'):
                errors.append(f"Component class {class_name} missing 'parameter_definitions' property")
            
            if not hasattr(component_class, 'execute'):
                errors.append(f"Component class {class_name} missing 'execute' method")
            
        except ImportError as e:
            errors.append(f"Import error in entry point: {str(e)}")
        except Exception as e:
            errors.append(f"Error validating entry point: {str(e)}")
    
    except Exception as e:
        errors.append(f"Entry point validation error: {str(e)}")
    
    return errors


# Export for use in main CLI
__all__ = ['validate_component']
