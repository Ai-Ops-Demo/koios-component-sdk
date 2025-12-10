"""
Validation utilities for the Koios Component SDK.

This module provides functions for validating component parameters,
configurations, and schemas using JSON Schema validation.
"""

from typing import Any, Dict, List, Optional, Union
import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from ..exceptions import ValidationError
from ..base.component import ParameterDefinition


def validate_schema(data: Any, schema: Dict[str, Any]) -> bool:
    """
    Validate data against a JSON schema.
    
    Args:
        data: Data to validate
        schema: JSON schema to validate against
        
    Returns:
        True if validation passes
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        jsonschema.validate(data, schema)
        return True
    except JsonSchemaValidationError as e:
        raise ValidationError(f"Schema validation failed: {e.message}")
    except Exception as e:
        raise ValidationError(f"Validation error: {str(e)}")


def validate_parameters(parameters: Dict[str, Any], 
                       parameter_definitions: List[ParameterDefinition]) -> bool:
    """
    Validate component parameters against their definitions.
    
    Args:
        parameters: Parameter values to validate
        parameter_definitions: List of parameter definitions
        
    Returns:
        True if all parameters are valid
        
    Raises:
        ValidationError: If any parameter is invalid
    """
    # Create a mapping of parameter names to definitions
    param_defs = {param.name: param for param in parameter_definitions}
    
    # Check required parameters
    for param_def in parameter_definitions:
        if param_def.required and param_def.name not in parameters:
            if param_def.default is None:
                raise ValidationError(
                    f"Required parameter '{param_def.name}' is missing",
                    parameter_name=param_def.name
                )
    
    # Validate each provided parameter
    for param_name, param_value in parameters.items():
        if param_name in param_defs:
            param_def = param_defs[param_name]
            
            # Use parameter definition's validate_value method
            if not param_def.validate_value(param_value):
                raise ValidationError(
                    f"Invalid value for parameter '{param_name}': {param_value}",
                    parameter_name=param_name,
                    actual_value=param_value
                )
    
    return True


def validate_component_manifest(manifest: Dict[str, Any]) -> bool:
    """
    Validate a component manifest file.
    
    Args:
        manifest: Component manifest dictionary
        
    Returns:
        True if manifest is valid
        
    Raises:
        ValidationError: If manifest is invalid
    """
    # Define the manifest schema
    manifest_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+"},
            "author": {"type": "string", "minLength": 1},
            "description": {"type": "string", "minLength": 1},
            "category": {
                "type": "string",
                "enum": ["control", "logic", "communication", "processing"]
            },
            "koios_version_min": {"type": "string"},
            "koios_version_max": {"type": "string"},
            "entry_point": {"type": "string", "minLength": 1},
            "dependencies": {
                "type": "array",
                "items": {"type": "string"}
            },
            "parameters": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["string", "integer", "float", "boolean", "json", "list"]
                        },
                        "description": {"type": "string"},
                        "required": {"type": "boolean"},
                        "default": {},
                        "validation": {"type": "object"}
                    },
                    "required": ["type", "description"]
                }
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"}
            },
            "license": {"type": "string"}
        },
        "required": ["name", "version", "author", "description", "category", "entry_point"]
    }
    
    return validate_schema(manifest, manifest_schema)


def validate_component_structure(component_path: str) -> List[str]:
    """
    Validate component directory structure.
    
    Args:
        component_path: Path to component directory
        
    Returns:
        List of validation errors (empty if valid)
    """
    from pathlib import Path
    
    errors = []
    component_dir = Path(component_path)
    
    # Check if directory exists
    if not component_dir.exists():
        errors.append(f"Component directory does not exist: {component_path}")
        return errors
    
    # Check required files
    required_files = [
        "koios_component.json",
        "component.py"
    ]
    
    for required_file in required_files:
        file_path = component_dir / required_file
        if not file_path.exists():
            errors.append(f"Required file missing: {required_file}")
    
    # Check manifest if it exists
    manifest_path = component_dir / "koios_component.json"
    if manifest_path.exists():
        try:
            import json
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            validate_component_manifest(manifest)
        except Exception as e:
            errors.append(f"Invalid manifest file: {str(e)}")
    
    # Check component.py if it exists
    component_py_path = component_dir / "component.py"
    if component_py_path.exists():
        try:
            # Basic syntax check
            with open(component_py_path, 'r') as f:
                code = f.read()
            compile(code, str(component_py_path), 'exec')
        except SyntaxError as e:
            errors.append(f"Syntax error in component.py: {str(e)}")
        except Exception as e:
            errors.append(f"Error in component.py: {str(e)}")
    
    return errors


def validate_parameter_value(value: Any, param_type: str, 
                           validation_rules: Optional[Dict[str, Any]] = None) -> bool:
    """
    Validate a single parameter value.
    
    Args:
        value: Value to validate
        param_type: Expected parameter type
        validation_rules: Optional validation rules
        
    Returns:
        True if value is valid
        
    Raises:
        ValidationError: If value is invalid
    """
    # Type validation
    if param_type == 'string' and not isinstance(value, str):
        raise ValidationError(f"Expected string, got {type(value).__name__}")
    elif param_type == 'integer' and not isinstance(value, int):
        raise ValidationError(f"Expected integer, got {type(value).__name__}")
    elif param_type == 'float' and not isinstance(value, (int, float)):
        raise ValidationError(f"Expected float, got {type(value).__name__}")
    elif param_type == 'boolean' and not isinstance(value, bool):
        raise ValidationError(f"Expected boolean, got {type(value).__name__}")
    elif param_type == 'list' and not isinstance(value, list):
        raise ValidationError(f"Expected list, got {type(value).__name__}")
    elif param_type == 'json':
        # JSON can be any serializable type
        try:
            import json
            json.dumps(value)
        except (TypeError, ValueError):
            raise ValidationError("Value is not JSON serializable")
    
    # Apply validation rules if provided
    if validation_rules:
        # Minimum value
        if 'minimum' in validation_rules:
            if isinstance(value, (int, float)) and value < validation_rules['minimum']:
                raise ValidationError(f"Value {value} is below minimum {validation_rules['minimum']}")
        
        # Maximum value
        if 'maximum' in validation_rules:
            if isinstance(value, (int, float)) and value > validation_rules['maximum']:
                raise ValidationError(f"Value {value} is above maximum {validation_rules['maximum']}")
        
        # String length
        if 'minLength' in validation_rules:
            if isinstance(value, str) and len(value) < validation_rules['minLength']:
                raise ValidationError(f"String length {len(value)} is below minimum {validation_rules['minLength']}")
        
        if 'maxLength' in validation_rules:
            if isinstance(value, str) and len(value) > validation_rules['maxLength']:
                raise ValidationError(f"String length {len(value)} is above maximum {validation_rules['maxLength']}")
        
        # Pattern matching
        if 'pattern' in validation_rules and isinstance(value, str):
            import re
            if not re.match(validation_rules['pattern'], value):
                raise ValidationError(f"String '{value}' does not match pattern '{validation_rules['pattern']}'")
        
        # Enum values
        if 'enum' in validation_rules:
            if value not in validation_rules['enum']:
                raise ValidationError(f"Value '{value}' is not in allowed values: {validation_rules['enum']}")
    
    return True
