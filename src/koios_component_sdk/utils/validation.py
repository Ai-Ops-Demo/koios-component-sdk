"""
Validation utilities for the Koios Component SDK.

This module provides functions for validating component parameters,
configurations, and schemas using JSON Schema validation.
"""

from typing import Any, Dict, List, Optional, Union, Set, Tuple
from pathlib import Path
import ast
import re
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


def extract_imports_from_file(file_path: Path) -> Set[str]:
    """
    Extract all import statements from a Python file.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        Set of imported module names (top-level packages only)
    """
    imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get top-level package name
                    module_name = alias.name.split('.')[0]
                    imports.add(module_name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get top-level package name
                    module_name = node.module.split('.')[0]
                    imports.add(module_name)
    
    except Exception:
        # If parsing fails, return empty set (will be caught by syntax validation)
        pass
    
    return imports


def parse_runtime_requirements_file(requirements_path: Path) -> Dict[str, str]:
    """
    Parse a runtime-available.txt file and extract package names and version specifications.
    
    Args:
        requirements_path: Path to runtime-available.txt file
        
    Returns:
        Dictionary mapping package names to version specifications
    """
    packages = {}
    
    if not requirements_path.exists():
        return packages
    
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Handle -e, --editable, etc.
                if line.startswith('-e ') or line.startswith('--editable '):
                    # Extract package name from editable install
                    match = re.search(r'#egg=([\w\-]+)', line)
                    if match:
                        package_name = match.group(1).lower()
                        packages[package_name] = line
                    continue
                
                # Parse standard requirement line: package==version or package>=version, etc.
                # Remove extras: package[extra]==version -> package==version
                line_no_extras = re.sub(r'\[.*?\]', '', line)
                
                # Extract package name (everything before ==, >=, <=, >, <, ~=, !=
                match = re.match(r'^([a-zA-Z0-9_\-\.]+)', line_no_extras)
                if match:
                    package_name = match.group(1).lower()
                    # Normalize package name (replace dots and underscores with hyphens)
                    package_name = re.sub(r'[._]', '-', package_name)
                    packages[package_name] = line
    
    except Exception:
        # If parsing fails, return empty dict
        pass
    
    return packages


def normalize_package_name(package_name: str) -> str:
    """
    Normalize a Python package name for comparison.
    
    Python package names can use dots, underscores, or hyphens, but
    pip normalizes them. This function normalizes to the standard format.
    
    Args:
        package_name: Package name to normalize
        
    Returns:
        Normalized package name
    """
    # Replace dots and underscores with hyphens, then lowercase
    normalized = re.sub(r'[._]', '-', package_name.lower())
    return normalized


def check_dependencies_against_runtime(
    component_dir: Path,
    runtime_requirements_path: Path,
    ignore_stdlib: bool = True
) -> Tuple[List[str], List[str]]:
    """
    Check component imports against runtime available packages.
    
    Args:
        component_dir: Component directory path
        runtime_requirements_path: Path to runtime-available.txt file
        ignore_stdlib: Whether to ignore standard library imports
        
    Returns:
        Tuple of (warnings, errors)
        - warnings: Missing dependencies that might be available but not in requirements
        - errors: Missing dependencies that are definitely not available
    """
    warnings = []
    errors = []
    
    # Standard library modules (don't need to be in requirements)
    stdlib_modules = {
        'abc', 'argparse', 'array', 'ast', 'asyncio', 'base64', 'binascii',
        'bisect', 'builtins', 'bz2', 'calendar', 'collections', 'copy',
        'csv', 'datetime', 'decimal', 'difflib', 'dis', 'doctest', 'email',
        'encodings', 'enum', 'errno', 'fileinput', 'fnmatch', 'fractions',
        'ftplib', 'functools', 'gc', 'getopt', 'getpass', 'glob', 'gzip',
        'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'importlib',
        'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3',
        'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
        'marshal', 'math', 'mimetypes', 'mmap', 'multiprocessing', 'netrc',
        'nis', 'nntplib', 'numbers', 'operator', 'optparse', 'os', 'pathlib',
        'pickle', 'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib',
        'posixpath', 'pprint', 'profile', 'pstats', 'pty', 'py_compile',
        'pyclbr', 'pydoc', 'queue', 'quopri', 'random', 're', 'readline',
        'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched', 'secrets',
        'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal',
        'site', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd',
        'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
        'struct', 'subprocess', 'sunau', 'symbol', 'symtable', 'sys',
        'sysconfig', 'syslog', 'tarfile', 'telnetlib', 'tempfile', 'termios',
        'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token',
        'tokenize', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle',
        'turtledemo', 'types', 'typing', 'unicodedata', 'unittest', 'urllib',
        'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser',
        'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp',
        'zipfile', 'zipimport', 'zlib'
    }
    
    # SDK library (part of the SDK itself, not a dependency)
    sdk_modules = {
        'koios_component_sdk'
    }
    
    # Extract imports from all Python files in component
    component_imports = set()
    for py_file in component_dir.rglob('*.py'):
        if py_file.is_file():
            file_imports = extract_imports_from_file(py_file)
            component_imports.update(file_imports)
    
    # Parse runtime requirements
    runtime_packages = parse_runtime_requirements_file(runtime_requirements_path)
    runtime_package_names = {normalize_package_name(name) for name in runtime_packages.keys()}
    
    # Get dependencies from manifest
    manifest_path = component_dir / "koios_component.json"
    manifest_dependencies = set()
    if manifest_path.exists():
        try:
            import json
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            deps = manifest.get('dependencies', [])
            for dep in deps:
                # Extract package name from dependency string (e.g., "numpy>=1.0" -> "numpy")
                dep_name = re.match(r'^([a-zA-Z0-9_\-\.]+)', dep)
                if dep_name:
                    manifest_dependencies.add(normalize_package_name(dep_name.group(1)))
        except Exception:
            pass
    
    # Check each import
    for import_name in component_imports:
        # Skip standard library if requested
        if ignore_stdlib and import_name in stdlib_modules:
            continue
        
        # Skip SDK library (part of the SDK itself)
        if import_name in sdk_modules:
            continue
        
        normalized_import = normalize_package_name(import_name)
        
        # Check if it's in runtime requirements
        if normalized_import not in runtime_package_names:
            # Check if it's declared in manifest dependencies
            if normalized_import not in manifest_dependencies:
                error_msg = (
                    f"Import '{import_name}' is not available in the runtime environment "
                    f"and is not declared in component dependencies. "
                    f"Add it to manifest dependencies or use an available package from runtime-available.txt"
                )
                errors.append(error_msg)
            else:
                warning_msg = (
                    f"Import '{import_name}' is declared in component dependencies "
                    f"but not found in runtime-available.txt. "
                    f"Ensure this package is available in the runtime environment or submit a request "
                    f"to add it to the available packages list."
                )
                warnings.append(warning_msg)
    
    return warnings, errors
