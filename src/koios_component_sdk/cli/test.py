"""
Component testing CLI command.

This module provides the 'test' command for testing components
in a mock Koios environment.
"""

import click
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

from ..exceptions import TestingError


@dataclass
class TestResult:
    """Test result container."""
    success: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@click.command()
@click.argument('component_dir', type=click.Path(exists=True))
@click.option('--scenario', help='Specific test scenario to run')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--timeout', default=30, help='Test timeout in seconds')
def test_component(component_dir: str, scenario: Optional[str], 
                  verbose: bool, timeout: int):
    """
    Test a component in mock Koios environment.
    
    This command runs comprehensive tests on a component to ensure
    it works correctly before deployment.
    
    Examples:
        koios-component test ./my_component
        koios-component test ./my_component --scenario startup
        koios-component test ./my_component --verbose
    """
    try:
        result = test_component_impl(component_dir, scenario, verbose, timeout)
        
        if result.success:
            click.echo("✅ All tests passed!")
            if result.warnings:
                click.echo("⚠️  Warnings:")
                for warning in result.warnings:
                    click.echo(f"  - {warning}")
        else:
            click.echo("❌ Tests failed:")
            for error in result.errors:
                click.echo(f"  - {error}")
            sys.exit(1)
            
    except TestingError as e:
        click.echo(f"❌ Test error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


def test_component_impl(component_dir: str, scenario: Optional[str] = None,
                       verbose: bool = False, timeout: int = 30) -> TestResult:
    """
    Implementation function for testing components.
    
    Args:
        component_dir: Path to component directory
        scenario: Specific test scenario
        verbose: Verbose output
        timeout: Test timeout
        
    Returns:
        TestResult object
    """
    component_path = Path(component_dir)
    errors = []
    warnings = []
    
    try:
        # Basic structure validation
        if verbose:
            click.echo("🔍 Validating component structure...")
        
        from ..utils.validation import validate_component_structure
        structure_errors = validate_component_structure(str(component_path))
        
        if structure_errors:
            errors.extend(structure_errors)
            return TestResult(success=False, errors=errors, warnings=warnings)
        
        # Load component manifest
        manifest_path = component_path / "koios_component.json"
        if not manifest_path.exists():
            errors.append("Component manifest (koios_component.json) not found")
            return TestResult(success=False, errors=errors, warnings=warnings)
        
        import json
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        if verbose:
            click.echo(f"📋 Testing component: {manifest.get('name', 'Unknown')}")
        
        # Import and instantiate component
        if verbose:
            click.echo("🔧 Loading component class...")
        
        component_class = _load_component_class(component_path, manifest)
        if component_class is None:
            errors.append("Could not load component class")
            return TestResult(success=False, errors=errors, warnings=warnings)
        
        # Run test scenarios
        if verbose:
            click.echo("🧪 Running test scenarios...")
        
        test_scenarios = _get_test_scenarios(manifest, scenario)
        
        for test_scenario in test_scenarios:
            if verbose:
                click.echo(f"  Running scenario: {test_scenario}")
            
            scenario_result = _run_test_scenario(
                component_class, manifest, test_scenario, timeout
            )
            
            if not scenario_result.success:
                errors.extend(scenario_result.errors)
            
            warnings.extend(scenario_result.warnings)
        
        return TestResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        
    except Exception as e:
        errors.append(f"Test execution error: {str(e)}")
        return TestResult(success=False, errors=errors, warnings=warnings)


def _load_component_class(component_path: Path, manifest: dict):
    """Load component class from entry point."""
    try:
        entry_point = manifest.get('entry_point', '')
        if not entry_point:
            return None
        
        # Parse entry point (e.g., "component.MyComponent")
        parts = entry_point.split('.')
        if len(parts) < 2:
            return None
        
        module_name = parts[0]
        class_name = '.'.join(parts[1:])
        
        # Import module
        import sys
        import importlib.util
        
        module_path = component_path / f"{module_name}.py"
        if not module_path.exists():
            return None
        
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        
        # Register the module in sys.modules BEFORE executing it
        # This is required for dataclass decorator and other features that need to access the module
        sys.modules[module_name] = module
        
        # Add SDK source directory to sys.path so koios_component_sdk can be imported
        # Find the SDK source directory (src/koios_component_sdk)
        sdk_src_path = Path(__file__).parent.parent.parent.parent / "src"
        if sdk_src_path.exists() and str(sdk_src_path) not in sys.path:
            sys.path.insert(0, str(sdk_src_path))
            sdk_path_added = True
        else:
            sdk_path_added = False
        
        # Add component directory to sys.path temporarily
        sys.path.insert(0, str(component_path))
        try:
            try:
                spec.loader.exec_module(module)
            except Exception as module_error:
                # Log the error for debugging
                import traceback
                error_msg = f"Error executing module {module_name}: {str(module_error)}\n{traceback.format_exc()}"
                print(f"DEBUG: {error_msg}", file=sys.stderr)
                return None
        finally:
            if str(component_path) in sys.path:
                sys.path.remove(str(component_path))
            if sdk_path_added and str(sdk_src_path) in sys.path:
                sys.path.remove(str(sdk_src_path))
            # Clean up sys.modules entry if we added it
            if module_name in sys.modules and sys.modules[module_name] is module:
                del sys.modules[module_name]
        
        # Get component class
        if not hasattr(module, class_name):
            # List available attributes for debugging
            available = [attr for attr in dir(module) if not attr.startswith('_')]
            print(f"DEBUG: Class {class_name} not found. Available: {available[:20]}", file=sys.stderr)
            return None
        
        component_class = getattr(module, class_name, None)
        if component_class is None:
            print(f"DEBUG: Class {class_name} is None", file=sys.stderr)
            return None
        
        if not isinstance(component_class, type):
            print(f"DEBUG: Class {class_name} is not a type, got {type(component_class)}", file=sys.stderr)
            return None
        
        return component_class
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Exception in _load_component_class: {str(e)}\n{traceback.format_exc()}", file=sys.stderr)
        return None


def _get_test_scenarios(manifest: dict, requested_scenario: Optional[str]) -> List[str]:
    """Get list of test scenarios to run."""
    # Get scenarios from manifest
    testing_config = manifest.get('testing', {})
    available_scenarios = testing_config.get('test_scenarios', ['basic'])
    
    if requested_scenario:
        if requested_scenario in available_scenarios:
            return [requested_scenario]
        else:
            # Run the requested scenario anyway, even if not in manifest
            return [requested_scenario]
    else:
        return available_scenarios


def _run_test_scenario(component_class, manifest: dict, scenario: str, 
                      timeout: int) -> TestResult:
    """Run a specific test scenario."""
    errors = []
    warnings = []
    
    try:
        # Get test configuration
        testing_config = manifest.get('testing', {})
        mock_tags = testing_config.get('mock_tags', {})
        
        # Create component instance with test parameters
        test_params = _get_test_parameters(manifest, scenario)
        component = component_class("test_component", test_params)
        
        # Run scenario-specific tests
        if scenario == 'basic' or scenario == 'startup':
            result = _test_basic_lifecycle(component)
        elif scenario == 'setpoint_change':
            result = _test_setpoint_change(component)
        elif scenario == 'manual_mode':
            result = _test_manual_mode(component)
        elif scenario == 'parameter_validation':
            result = _test_parameter_validation(component_class)
        else:
            # Generic test
            result = _test_basic_lifecycle(component)
            warnings.append(f"Unknown test scenario '{scenario}', ran basic test")
        
        if not result.success:
            errors.extend(result.errors)
        warnings.extend(result.warnings)
        
    except Exception as e:
        errors.append(f"Scenario '{scenario}' failed: {str(e)}")
    
    return TestResult(
        success=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def _get_test_parameters(manifest: dict, scenario: str) -> dict:
    """Get test parameters for scenario."""
    # Start with default parameters from manifest
    params = {}
    
    manifest_params = manifest.get('parameters', {})
    for param_name, param_config in manifest_params.items():
        if 'default' in param_config:
            params[param_name] = param_config['default']
    
    # Add scenario-specific overrides
    testing_config = manifest.get('testing', {})
    scenario_params = testing_config.get('scenario_parameters', {}).get(scenario, {})
    params.update(scenario_params)
    
    return params


def _test_basic_lifecycle(component) -> TestResult:
    """Test basic component lifecycle."""
    errors = []
    warnings = []
    
    try:
        # Test parameter validation
        if not component.validate_parameters():
            errors.append("Parameter validation failed")
        
        # Test initialization
        if not component.initialize():
            errors.append("Component initialization failed")
            return TestResult(success=False, errors=errors, warnings=warnings)
        
        # Test start
        if not component.start():
            errors.append("Component start failed")
            return TestResult(success=False, errors=errors, warnings=warnings)
        
        # Test execution
        result = component.execute()
        if not result.get('success', False):
            errors.append(f"Component execution failed: {result.get('error', 'Unknown error')}")
        
        # Test stop
        if not component.stop():
            warnings.append("Component stop returned False")
        
    except Exception as e:
        errors.append(f"Lifecycle test error: {str(e)}")
    
    return TestResult(success=len(errors) == 0, errors=errors, warnings=warnings)


def _test_setpoint_change(component) -> TestResult:
    """Test setpoint change response (for controllers)."""
    errors = []
    warnings = []
    
    try:
        # Initialize and start component
        if not component.initialize() or not component.start():
            errors.append("Could not start component for setpoint test")
            return TestResult(success=False, errors=errors, warnings=warnings)
        
        # Test setpoint change (if component supports it)
        if hasattr(component, 'setpoint'):
            original_setpoint = getattr(component, 'setpoint', 0)
            component.setpoint = 75.0
            
            # Execute a few times
            for _ in range(3):
                result = component.execute()
                if not result.get('success', False):
                    errors.append("Execution failed during setpoint test")
                    break
            
            # Restore original setpoint
            component.setpoint = original_setpoint
        else:
            warnings.append("Component does not support setpoint changes")
        
        component.stop()
        
    except Exception as e:
        errors.append(f"Setpoint test error: {str(e)}")
    
    return TestResult(success=len(errors) == 0, errors=errors, warnings=warnings)


def _test_manual_mode(component) -> TestResult:
    """Test manual mode switching (for controllers)."""
    errors = []
    warnings = []
    
    try:
        # Initialize and start component
        if not component.initialize() or not component.start():
            errors.append("Could not start component for manual mode test")
            return TestResult(success=False, errors=errors, warnings=warnings)
        
        # Test manual mode (if component supports it)
        if hasattr(component, 'manual_mode'):
            # Switch to manual mode
            component.manual_mode = True
            
            if hasattr(component, 'manual_output'):
                component.manual_output = 50.0
            
            # Execute in manual mode
            result = component.execute()
            if not result.get('success', False):
                errors.append("Execution failed in manual mode")
            
            # Switch back to automatic
            component.manual_mode = False
            
            # Execute in automatic mode
            result = component.execute()
            if not result.get('success', False):
                errors.append("Execution failed when switching back to automatic")
        else:
            warnings.append("Component does not support manual mode")
        
        component.stop()
        
    except Exception as e:
        errors.append(f"Manual mode test error: {str(e)}")
    
    return TestResult(success=len(errors) == 0, errors=errors, warnings=warnings)


def _test_parameter_validation(component_class) -> TestResult:
    """Test parameter validation."""
    errors = []
    warnings = []
    
    try:
        # Test with invalid parameters
        invalid_params = {
            'invalid_param': 'invalid_value',
            'kp': -1.0,  # Negative gain (usually invalid)
        }
        
        try:
            component = component_class("test_invalid", invalid_params)
            # If this doesn't raise an exception, validation might be weak
            warnings.append("Component accepted potentially invalid parameters")
        except Exception:
            # Expected - invalid parameters should be rejected
            pass
        
        # Test with minimal valid parameters
        try:
            component = component_class("test_minimal", {})
            if not component.validate_parameters():
                warnings.append("Component validation failed with default parameters")
        except Exception as e:
            errors.append(f"Component creation failed with default parameters: {str(e)}")
        
    except Exception as e:
        errors.append(f"Parameter validation test error: {str(e)}")
    
    return TestResult(success=len(errors) == 0, errors=errors, warnings=warnings)


# Export for use in main CLI
__all__ = ['test_component', 'test_component_impl', 'TestResult']
