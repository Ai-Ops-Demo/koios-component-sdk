"""
Documentation generation utilities for the Koios Component SDK.

This module provides functionality for generating documentation from
component code and metadata.
"""

import json
import inspect
from pathlib import Path
from typing import Dict, Any, List, Optional
import ast

from ..exceptions import KoiosComponentError


def generate_docs(component_path: Path, format: str = 'markdown') -> str:
    """
    Generate documentation for a component.
    
    Args:
        component_path: Path to component directory
        format: Documentation format ('markdown', 'html', 'json')
        
    Returns:
        Generated documentation string
    """
    try:
        # Load component manifest
        manifest_path = component_path / "koios_component.json"
        if not manifest_path.exists():
            raise KoiosComponentError(f"Component manifest not found: {manifest_path}")
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Analyze component code
        component_info = _analyze_component_code(component_path, manifest)
        
        # Generate documentation based on format
        if format == 'markdown':
            return _generate_markdown_docs(manifest, component_info)
        elif format == 'html':
            return _generate_html_docs(manifest, component_info)
        elif format == 'json':
            return _generate_json_docs(manifest, component_info)
        else:
            raise KoiosComponentError(f"Unsupported documentation format: {format}")
    
    except Exception as e:
        raise KoiosComponentError(f"Documentation generation failed: {str(e)}")


def _analyze_component_code(component_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze component code to extract information."""
    info = {
        'methods': [],
        'properties': [],
        'bindings': [],
        'docstring': None
    }
    
    # Get entry point
    entry_point = manifest.get('entry_point', '')
    if not entry_point:
        return info
    
    parts = entry_point.split('.')
    if len(parts) < 2:
        return info
    
    module_name = parts[0]
    class_name = '.'.join(parts[1:])
    
    # Read component file
    component_file = component_path / f"{module_name}.py"
    if not component_file.exists():
        return info
    
    try:
        with open(component_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Parse AST
        tree = ast.parse(code)
        
        # Find the component class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Get class docstring
                if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant)):
                    info['docstring'] = node.body[0].value.value
                
                # Analyze methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            'name': item.name,
                            'docstring': ast.get_docstring(item),
                            'args': [arg.arg for arg in item.args.args if arg.arg != 'self'],
                            'decorators': [_get_decorator_name(dec) for dec in item.decorator_list]
                        }
                        info['methods'].append(method_info)
                
                break
    
    except Exception:
        pass  # Ignore parsing errors
    
    return info


def _get_decorator_name(decorator_node) -> str:
    """Extract decorator name from AST node."""
    if isinstance(decorator_node, ast.Name):
        return decorator_node.id
    elif isinstance(decorator_node, ast.Attribute):
        return decorator_node.attr
    elif isinstance(decorator_node, ast.Call):
        if isinstance(decorator_node.func, ast.Name):
            return decorator_node.func.id
        elif isinstance(decorator_node.func, ast.Attribute):
            return decorator_node.func.attr
    return "unknown"


def _generate_markdown_docs(manifest: Dict[str, Any], component_info: Dict[str, Any]) -> str:
    """Generate Markdown documentation."""
    lines = []
    
    # Title
    name = manifest.get('name', 'Unknown Component')
    lines.append(f"# {name}")
    lines.append("")
    
    # Description
    description = manifest.get('description', 'No description available')
    lines.append(description)
    lines.append("")
    
    # Metadata table
    lines.append("## Component Information")
    lines.append("")
    lines.append("| Property | Value |")
    lines.append("|----------|-------|")
    lines.append(f"| Name | {manifest.get('name', 'Unknown')} |")
    lines.append(f"| Version | {manifest.get('version', 'Unknown')} |")
    lines.append(f"| Author | {manifest.get('author', 'Unknown')} |")
    lines.append(f"| Category | {manifest.get('category', 'Unknown')} |")
    lines.append(f"| Entry Point | {manifest.get('entry_point', 'Unknown')} |")
    lines.append("")
    
    # Parameters
    parameters = manifest.get('parameters', {})
    if parameters:
        lines.append("## Parameters")
        lines.append("")
        lines.append("| Parameter | Type | Required | Default | Description |")
        lines.append("|-----------|------|----------|---------|-------------|")
        
        for param_name, param_config in parameters.items():
            param_type = param_config.get('type', 'unknown')
            required = 'Yes' if param_config.get('required', False) else 'No'
            default = param_config.get('default', 'None')
            desc = param_config.get('description', 'No description')
            
            lines.append(f"| {param_name} | {param_type} | {required} | {default} | {desc} |")
        
        lines.append("")
    
    # Bindings
    bindings = manifest.get('bindings', {})
    if bindings:
        lines.append("## Tag Bindings")
        lines.append("")
        
        inputs = bindings.get('inputs', [])
        if inputs:
            lines.append("### Input Tags")
            lines.append("")
            for binding in inputs:
                lines.append(f"- **{binding['name']}** (`{binding['tag']}`): {binding['description']}")
            lines.append("")
        
        outputs = bindings.get('outputs', [])
        if outputs:
            lines.append("### Output Tags")
            lines.append("")
            for binding in outputs:
                lines.append(f"- **{binding['name']}** (`{binding['tag']}`): {binding['description']}")
            lines.append("")
    
    # Methods
    methods = component_info.get('methods', [])
    if methods:
        lines.append("## Methods")
        lines.append("")
        
        for method in methods:
            if not method['name'].startswith('_'):  # Skip private methods
                lines.append(f"### {method['name']}")
                lines.append("")
                
                if method['docstring']:
                    lines.append(method['docstring'])
                    lines.append("")
                
                if method['args']:
                    lines.append("**Arguments:**")
                    for arg in method['args']:
                        lines.append(f"- `{arg}`")
                    lines.append("")
                
                if method['decorators']:
                    lines.append("**Decorators:**")
                    for decorator in method['decorators']:
                        lines.append(f"- `@{decorator}`")
                    lines.append("")
    
    # Dependencies
    dependencies = manifest.get('dependencies', [])
    if dependencies:
        lines.append("## Dependencies")
        lines.append("")
        for dep in dependencies:
            lines.append(f"- {dep}")
        lines.append("")
    
    # Usage example
    lines.append("## Usage Example")
    lines.append("")
    lines.append("```python")
    lines.append(f"from {manifest.get('entry_point', 'component').split('.')[0]} import {manifest.get('entry_point', 'Component').split('.')[-1]}")
    lines.append("")
    lines.append("# Create component instance")
    lines.append("config = {")
    
    # Add sample parameters
    for param_name, param_config in list(parameters.items())[:3]:
        default = param_config.get('default')
        if default is not None:
            if isinstance(default, str):
                lines.append(f'    "{param_name}": "{default}",')
            else:
                lines.append(f'    "{param_name}": {default},')
    
    lines.append("}")
    lines.append("")
    class_name = manifest.get('entry_point', 'Component').split('.')[-1]
    lines.append(f'component = {class_name}("my_component", config)')
    lines.append("")
    lines.append("# Initialize and start")
    lines.append("component.initialize()")
    lines.append("component.start()")
    lines.append("")
    lines.append("# Execute component")
    lines.append("result = component.execute()")
    lines.append("print(f'Result: {result}')")
    lines.append("")
    lines.append("# Stop component")
    lines.append("component.stop()")
    lines.append("```")
    
    return "\n".join(lines)


def _generate_html_docs(manifest: Dict[str, Any], component_info: Dict[str, Any]) -> str:
    """Generate HTML documentation."""
    # Convert markdown to HTML (basic implementation)
    markdown_docs = _generate_markdown_docs(manifest, component_info)
    
    # Simple markdown to HTML conversion
    html_lines = ["<!DOCTYPE html>", "<html>", "<head>", 
                  f"<title>{manifest.get('name', 'Component')} Documentation</title>",
                  "<style>body { font-family: Arial, sans-serif; margin: 40px; }</style>",
                  "</head>", "<body>"]
    
    # Convert basic markdown elements
    for line in markdown_docs.split('\n'):
        if line.startswith('# '):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith('## '):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith('### '):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith('- '):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.startswith('```'):
            if 'python' in line:
                html_lines.append("<pre><code class='python'>")
            elif line == '```':
                html_lines.append("</code></pre>")
        else:
            if line.strip():
                html_lines.append(f"<p>{line}</p>")
    
    html_lines.extend(["</body>", "</html>"])
    
    return "\n".join(html_lines)


def _generate_json_docs(manifest: Dict[str, Any], component_info: Dict[str, Any]) -> str:
    """Generate JSON documentation."""
    docs = {
        'manifest': manifest,
        'component_info': component_info,
        'generated_at': _get_current_timestamp()
    }
    
    return json.dumps(docs, indent=2)


def _get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime
    return datetime.now().isoformat()
