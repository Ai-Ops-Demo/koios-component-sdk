"""
Component packaging utilities for the Koios Component SDK.

This module provides functionality for building, packaging, and validating
Koios components for deployment.
"""

import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib
import datetime

from ..exceptions import PackagingError, ValidationError
from .validation import validate_component_structure, validate_component_manifest


class ComponentPackager:
    """
    Handles packaging of Koios components into deployable packages.
    
    This class provides functionality to build component packages (.kcp files)
    that can be deployed to Koios servers.
    """
    
    def __init__(self, component_dir: str):
        """
        Initialize the packager.
        
        Args:
            component_dir: Path to component directory
        """
        self.component_dir = Path(component_dir)
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load and validate component manifest."""
        manifest_path = self.component_dir / "koios_component.json"
        
        if not manifest_path.exists():
            raise PackagingError(f"Manifest file not found: {manifest_path}")
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Validate manifest
            validate_component_manifest(manifest)
            return manifest
            
        except json.JSONDecodeError as e:
            raise PackagingError(f"Invalid JSON in manifest: {str(e)}")
        except ValidationError as e:
            raise PackagingError(f"Invalid manifest: {str(e)}")
        except Exception as e:
            raise PackagingError(f"Error loading manifest: {str(e)}")
    
    def validate(self) -> List[str]:
        """
        Validate component structure and files.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate directory structure
        structure_errors = validate_component_structure(str(self.component_dir))
        errors.extend(structure_errors)
        
        # Check entry point
        entry_point = self.manifest.get('entry_point', '')
        if entry_point:
            # Parse entry point (e.g., "component.MyComponent")
            parts = entry_point.split('.')
            if len(parts) >= 2:
                module_name = parts[0]
                class_name = '.'.join(parts[1:])
                
                # Check if module file exists
                module_path = self.component_dir / f"{module_name}.py"
                if not module_path.exists():
                    errors.append(f"Entry point module not found: {module_name}.py")
                else:
                    # Try to import and find the class
                    try:
                        import sys
                        import importlib.util
                        
                        spec = importlib.util.spec_from_file_location(module_name, module_path)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            
                            # Check if class exists
                            if not hasattr(module, class_name):
                                errors.append(f"Entry point class not found: {class_name}")
                    except Exception as e:
                        errors.append(f"Error validating entry point: {str(e)}")
            else:
                errors.append(f"Invalid entry point format: {entry_point}")
        
        # Check dependencies
        dependencies = self.manifest.get('dependencies', [])
        for dep in dependencies:
            if not isinstance(dep, str):
                errors.append(f"Invalid dependency format: {dep}")
        
        return errors
    
    def build(self, output_dir: Optional[str] = None, compress: bool = True) -> str:
        """
        Build component package.
        
        Args:
            output_dir: Output directory for package (default: component parent dir)
            compress: Whether to compress the package
            
        Returns:
            Path to created package file
        """
        # Validate component first
        validation_errors = self.validate()
        if validation_errors:
            raise PackagingError(f"Component validation failed: {'; '.join(validation_errors)}")
        
        # Determine output path
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.component_dir.parent
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create package filename
        name = self.manifest['name'].replace(' ', '_').lower()
        version = self.manifest['version']
        package_filename = f"{name}-{version}.kcp"
        package_path = output_path / package_filename
        
        try:
            # Create package
            compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
            
            with zipfile.ZipFile(package_path, 'w', compression) as zf:
                # Add all component files
                for file_path in self.component_dir.rglob('*'):
                    if file_path.is_file():
                        # Skip certain files
                        if self._should_skip_file(file_path):
                            continue
                        
                        # Calculate relative path
                        arcname = file_path.relative_to(self.component_dir)
                        zf.write(file_path, arcname)
                
                # Add package metadata
                package_info = self._create_package_info()
                zf.writestr('_package_info.json', json.dumps(package_info, indent=2))
            
            return str(package_path)
            
        except Exception as e:
            # Clean up on error
            if package_path.exists():
                package_path.unlink()
            raise PackagingError(f"Failed to create package: {str(e)}")
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during packaging."""
        skip_patterns = [
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '.git',
            '.gitignore',
            '.DS_Store',
            'Thumbs.db',
            '*.tmp',
            '*.temp'
        ]
        
        file_str = str(file_path)
        for pattern in skip_patterns:
            if pattern in file_str or file_path.name == pattern:
                return True
        
        return False
    
    def _create_package_info(self) -> Dict[str, Any]:
        """Create package metadata."""
        return {
            'package_format_version': '1.0',
            'created_at': datetime.datetime.now().isoformat(),
            'created_by': 'koios-component-sdk',
            'sdk_version': '1.0.0',
            'component_manifest': self.manifest,
            'file_count': len(list(self.component_dir.rglob('*'))),
            'package_hash': self._calculate_package_hash()
        }
    
    def _calculate_package_hash(self) -> str:
        """Calculate hash of component files."""
        hasher = hashlib.sha256()
        
        # Sort files for consistent hashing
        files = sorted(self.component_dir.rglob('*'))
        
        for file_path in files:
            if file_path.is_file() and not self._should_skip_file(file_path):
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    @staticmethod
    def extract_package(package_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Extract a component package.
        
        Args:
            package_path: Path to package file
            output_dir: Directory to extract to
            
        Returns:
            Package information dictionary
        """
        package_file = Path(package_path)
        output_path = Path(output_dir)
        
        if not package_file.exists():
            raise PackagingError(f"Package file not found: {package_path}")
        
        try:
            with zipfile.ZipFile(package_file, 'r') as zf:
                # Extract all files
                zf.extractall(output_path)
                
                # Read package info
                try:
                    package_info_data = zf.read('_package_info.json')
                    package_info = json.loads(package_info_data.decode('utf-8'))
                    return package_info
                except KeyError:
                    # Old format package without metadata
                    return {'package_format_version': 'unknown'}
                
        except zipfile.BadZipFile:
            raise PackagingError(f"Invalid package file: {package_path}")
        except Exception as e:
            raise PackagingError(f"Failed to extract package: {str(e)}")
    
    @staticmethod
    def list_package_contents(package_path: str) -> List[str]:
        """
        List contents of a component package.
        
        Args:
            package_path: Path to package file
            
        Returns:
            List of file paths in package
        """
        package_file = Path(package_path)
        
        if not package_file.exists():
            raise PackagingError(f"Package file not found: {package_path}")
        
        try:
            with zipfile.ZipFile(package_file, 'r') as zf:
                return zf.namelist()
        except zipfile.BadZipFile:
            raise PackagingError(f"Invalid package file: {package_path}")
        except Exception as e:
            raise PackagingError(f"Failed to read package: {str(e)}")
    
    @staticmethod
    def get_package_info(package_path: str) -> Dict[str, Any]:
        """
        Get package information without extracting.
        
        Args:
            package_path: Path to package file
            
        Returns:
            Package information dictionary
        """
        package_file = Path(package_path)
        
        if not package_file.exists():
            raise PackagingError(f"Package file not found: {package_path}")
        
        try:
            with zipfile.ZipFile(package_file, 'r') as zf:
                try:
                    package_info_data = zf.read('_package_info.json')
                    return json.loads(package_info_data.decode('utf-8'))
                except KeyError:
                    # Try to read manifest directly
                    try:
                        manifest_data = zf.read('koios_component.json')
                        manifest = json.loads(manifest_data.decode('utf-8'))
                        return {
                            'package_format_version': 'legacy',
                            'component_manifest': manifest
                        }
                    except KeyError:
                        raise PackagingError("Package does not contain valid metadata")
                
        except zipfile.BadZipFile:
            raise PackagingError(f"Invalid package file: {package_path}")
        except Exception as e:
            raise PackagingError(f"Failed to read package info: {str(e)}")
