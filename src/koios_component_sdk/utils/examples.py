"""
Example management utilities for the Koios Component SDK.

This module provides functionality for managing and describing
example components included with the SDK.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json

from ..exceptions import KoiosComponentError


def get_examples(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get list of available example components.
    
    Args:
        category: Optional category filter
        
    Returns:
        List of example component information
    """
    examples = []
    
    # Get SDK root directory
    sdk_root = Path(__file__).parent.parent.parent.parent
    examples_dir = sdk_root / "examples"
    
    if not examples_dir.exists():
        return examples
    
    # Scan example directories
    for example_dir in examples_dir.iterdir():
        if example_dir.is_dir():
            example_info = _load_example_info(example_dir)
            if example_info:
                # Filter by category if specified
                if category is None or example_info.get('category') == category:
                    examples.append(example_info)
    
    return examples


def describe_example(example_path: str) -> str:
    """
    Get detailed description of an example component.
    
    Args:
        example_path: Path to example directory
        
    Returns:
        Detailed description string
    """
    example_dir = Path(example_path)
    
    # Try to load README
    readme_path = example_dir / "README.md"
    if readme_path.exists():
        try:
            return readme_path.read_text(encoding='utf-8')
        except Exception:
            pass
    
    # Fallback to manifest description
    manifest_path = example_dir / "koios_component.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            return manifest.get('description', 'No description available')
        except Exception:
            pass
    
    return "No description available"


def _load_example_info(example_path: Path) -> Optional[Dict[str, Any]]:
    """Load example information from manifest."""
    manifest_path = example_path / "koios_component.json"
    
    if not manifest_path.exists():
        return None
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        return {
            'name': manifest.get('name', example_path.name),
            'description': manifest.get('description', 'No description'),
            'category': manifest.get('category', 'unknown'),
            'version': manifest.get('version', 'unknown'),
            'author': manifest.get('author', 'unknown'),
            'path': str(example_path),
            'tags': manifest.get('tags', [])
        }
    
    except Exception:
        return None


def list_example_files(example_path: str) -> List[str]:
    """
    List files in an example directory.
    
    Args:
        example_path: Path to example directory
        
    Returns:
        List of file paths
    """
    example_dir = Path(example_path)
    
    if not example_dir.exists():
        return []
    
    files = []
    for file_path in example_dir.rglob('*'):
        if file_path.is_file():
            files.append(str(file_path.relative_to(example_dir)))
    
    return sorted(files)


def copy_example(example_name: str, destination: str) -> bool:
    """
    Copy an example to a destination directory.
    
    Args:
        example_name: Name of example to copy
        destination: Destination directory
        
    Returns:
        True if copy succeeded
    """
    try:
        # Find example
        examples = get_examples()
        example_info = None
        
        for example in examples:
            if example['name'].lower() == example_name.lower():
                example_info = example
                break
        
        if not example_info:
            raise KoiosComponentError(f"Example not found: {example_name}")
        
        # Copy files
        import shutil
        source_path = Path(example_info['path'])
        dest_path = Path(destination)
        
        if dest_path.exists():
            shutil.rmtree(dest_path)
        
        shutil.copytree(source_path, dest_path)
        
        return True
    
    except Exception as e:
        raise KoiosComponentError(f"Failed to copy example: {str(e)}")


def validate_example(example_path: str) -> List[str]:
    """
    Validate an example component.
    
    Args:
        example_path: Path to example directory
        
    Returns:
        List of validation errors
    """
    from .validation import validate_component_structure
    
    return validate_component_structure(example_path)
