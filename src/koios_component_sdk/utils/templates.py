"""
Template management utilities for the Koios Component SDK.

This module provides functionality for managing component templates,
including template discovery, loading, and rendering.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from jinja2 import Environment, FileSystemLoader, Template

from ..exceptions import KoiosComponentError


class TemplateManager:
    """
    Manages component templates for the SDK.
    
    This class handles template discovery, loading, and rendering
    for creating new components from templates.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            template_dir: Optional custom template directory
        """
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Use default template directory
            sdk_root = Path(__file__).parent.parent.parent.parent
            self.template_dir = sdk_root / "templates"
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available templates."""
        templates = []
        
        if not self.template_dir.exists():
            return templates
        
        for template_dir in self.template_dir.iterdir():
            if template_dir.is_dir():
                template_info = self._load_template_info(template_dir)
                if template_info:
                    templates.append(template_info)
        
        return templates
    
    def _load_template_info(self, template_path: Path) -> Optional[Dict[str, Any]]:
        """Load template information from template.json."""
        info_file = template_path / "template.json"
        
        if not info_file.exists():
            # Create basic info from directory name
            return {
                "name": template_path.name,
                "description": f"Template for {template_path.name}",
                "category": "unknown",
                "path": str(template_path)
            }
        
        try:
            with open(info_file, 'r') as f:
                info = json.load(f)
            
            info["path"] = str(template_path)
            return info
            
        except Exception:
            return None
    
    def create_component(self, template_name: str, output_path: Path,
                        context: Dict[str, Any], force: bool = False) -> List[str]:
        """
        Create component from template.
        
        Args:
            template_name: Name of template to use
            output_path: Output directory path
            context: Template context variables
            force: Whether to overwrite existing files
            
        Returns:
            List of created file paths
        """
        # Find template
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            raise KoiosComponentError(f"Template not found: {template_name}")
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        
        # Process all template files
        for template_file in template_path.rglob("*"):
            if template_file.is_file() and not template_file.name.startswith('.'):
                # Skip template.json
                if template_file.name == "template.json":
                    continue
                
                # Calculate relative path
                rel_path = template_file.relative_to(template_path)
                output_file = output_path / rel_path
                
                # Create parent directories
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if file exists
                if output_file.exists() and not force:
                    continue
                
                # Render template
                try:
                    if template_file.suffix in ['.py', '.json', '.md', '.txt', '.yml', '.yaml']:
                        # Text file - render as template
                        template_content = template_file.read_text(encoding='utf-8')
                        template = Template(template_content)
                        rendered_content = template.render(**context)
                        
                        output_file.write_text(rendered_content, encoding='utf-8')
                    else:
                        # Binary file - copy as-is
                        output_file.write_bytes(template_file.read_bytes())
                    
                    created_files.append(str(output_file))
                    
                except Exception as e:
                    raise KoiosComponentError(f"Error processing template file {template_file}: {str(e)}")
        
        return created_files


def get_available_templates() -> List[Dict[str, Any]]:
    """
    Get list of available component templates.
    
    Returns:
        List of template information dictionaries
    """
    # For now, return a basic set of templates
    # In a full implementation, this would scan the templates directory
    return [
        {
            "name": "basic_controller",
            "description": "Basic controller component template",
            "category": "control",
            "config_prompts": {}
        },
        {
            "name": "pid_controller", 
            "description": "PID controller with advanced features",
            "category": "control",
            "config_prompts": {
                "kp": {
                    "prompt": "Proportional gain",
                    "type": float,
                    "default": 1.0
                },
                "ki": {
                    "prompt": "Integral gain", 
                    "type": float,
                    "default": 0.1
                },
                "kd": {
                    "prompt": "Derivative gain",
                    "type": float,
                    "default": 0.01
                }
            }
        },
        {
            "name": "basic_protocol",
            "description": "Basic communication protocol template",
            "category": "communication",
            "config_prompts": {
                "default_port": {
                    "prompt": "Default port number",
                    "type": int,
                    "default": 502
                }
            }
        },
        {
            "name": "data_processor",
            "description": "Data processing component template", 
            "category": "processing",
            "config_prompts": {}
        },
        {
            "name": "logic_component",
            "description": "Logic component template",
            "category": "logic",
            "config_prompts": {}
        }
    ]
