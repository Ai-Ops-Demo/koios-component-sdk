"""
Development server utilities for the Koios Component SDK.

This module provides functionality for running a development server
with auto-rebuild and testing capabilities.
"""

import time
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..exceptions import KoiosComponentError
from .packaging import ComponentPackager
from .validation import validate_component_structure


class ComponentChangeHandler(FileSystemEventHandler):
    """Handle file system changes for component development."""
    
    def __init__(self, component_path: Path, output_path: Path, 
                 auto_test: bool = False, auto_build: bool = True):
        self.component_path = component_path
        self.output_path = output_path
        self.auto_test = auto_test
        self.auto_build = auto_build
        self.last_build_time = 0
        self.build_delay = 2.0  # Seconds to wait before rebuilding
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        # Only process Python and JSON files
        file_path = Path(event.src_path)
        if file_path.suffix not in ['.py', '.json', '.md']:
            return
        
        # Debounce rapid changes
        current_time = time.time()
        if current_time - self.last_build_time < self.build_delay:
            return
        
        self.last_build_time = current_time
        
        print(f"File changed: {file_path.name}")
        
        # Validate component
        try:
            errors = validate_component_structure(str(self.component_path))
            if errors:
                print("Validation failed:")
                for error in errors:
                    print(f"  - {error}")
                return
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return
        
        # Run tests if enabled
        if self.auto_test:
            try:
                from ..cli.test import test_component_impl
                result = test_component_impl(str(self.component_path))
                
                if result.success:
                    print("Tests passed!")
                else:
                    print("Tests failed:")
                    for error in result.errors:
                        print(f"  - {error}")
                    return
            except Exception as e:
                print(f"Test error: {str(e)}")
                return
        
        # Build package if enabled
        if self.auto_build:
            try:
                from ..cli.build import build_package_impl
                package_path = build_package_impl(
                    str(self.component_path), 
                    str(self.output_path),
                    compress=True,
                    validate=False  # Already validated above
                )
                print(f"Package rebuilt: {Path(package_path).name}")
                
            except Exception as e:
                print(f"Build error: {str(e)}")


def start_dev_server(component_path: Path, output_path: Path, 
                    auto_test: bool = False, auto_build: bool = True):
    """
    Start development server with file watching.
    
    Args:
        component_path: Path to component directory
        output_path: Output path for built packages
        auto_test: Whether to run tests on changes
        auto_build: Whether to build packages on changes
    """
    try:
        print(f"Starting development server for: {component_path}")
        print(f"Output directory: {output_path}")
        print(f"Auto-test: {auto_test}")
        print(f"Auto-build: {auto_build}")
        print()
        
        # Create event handler
        event_handler = ComponentChangeHandler(
            component_path, output_path, auto_test, auto_build
        )
        
        # Set up file watcher
        observer = Observer()
        observer.schedule(event_handler, str(component_path), recursive=True)
        
        # Start watching
        observer.start()
        print("Watching for changes... Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping development server...")
            observer.stop()
        
        observer.join()
        print("Development server stopped.")
    
    except Exception as e:
        raise KoiosComponentError(f"Development server error: {str(e)}")


def run_single_dev_cycle(component_path: Path, output_path: Path,
                        run_tests: bool = True, build_package: bool = True) -> bool:
    """
    Run a single development cycle (validate, test, build).
    
    Args:
        component_path: Path to component directory
        output_path: Output path for built packages
        run_tests: Whether to run tests
        build_package: Whether to build package
        
    Returns:
        True if cycle completed successfully
    """
    try:
        print(f"Running development cycle for: {component_path}")
        
        # Validate
        print("Validating component...")
        errors = validate_component_structure(str(component_path))
        if errors:
            print("Validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print("Validation passed!")
        
        # Test if requested
        if run_tests:
            print("Running tests...")
            try:
                from ..cli.test import test_component_impl
                result = test_component_impl(str(component_path))
                
                if result.success:
                    print("Tests passed!")
                    if result.warnings:
                        print("Warnings:")
                        for warning in result.warnings:
                            print(f"  - {warning}")
                else:
                    print("Tests failed:")
                    for error in result.errors:
                        print(f"  - {error}")
                    return False
            except Exception as e:
                print(f"Test error: {str(e)}")
                return False
        
        # Build if requested
        if build_package:
            print("Building package...")
            try:
                from ..cli.build import build_package_impl
                package_path = build_package_impl(
                    str(component_path),
                    str(output_path),
                    compress=True,
                    validate=False  # Already validated
                )
                print(f"Package built: {Path(package_path).name}")
            except Exception as e:
                print(f"Build error: {str(e)}")
                return False
        
        print("Development cycle completed successfully!")
        return True
    
    except Exception as e:
        print(f"Development cycle error: {str(e)}")
        return False
