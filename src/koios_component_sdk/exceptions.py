"""
Custom exceptions for the Koios Component SDK.

This module defines all the custom exceptions that can be raised by components
and SDK utilities. These exceptions provide clear error messages and context
for debugging component issues.
"""

from typing import Optional, Dict, Any


class KoiosComponentError(Exception):
    """Base exception for all Koios component errors."""
    
    def __init__(self, message: str, component_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.component_id = component_id
        self.details = details or {}
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.component_id:
            base_msg = f"[{self.component_id}] {base_msg}"
        return base_msg


class ValidationError(KoiosComponentError):
    """Raised when component parameter validation fails."""
    
    def __init__(self, message: str, parameter_name: Optional[str] = None, 
                 expected_type: Optional[str] = None, actual_value: Any = None,
                 component_id: Optional[str] = None):
        details = {}
        if parameter_name:
            details["parameter_name"] = parameter_name
        if expected_type:
            details["expected_type"] = expected_type
        if actual_value is not None:
            details["actual_value"] = actual_value
            
        super().__init__(message, component_id, details)
        self.parameter_name = parameter_name
        self.expected_type = expected_type
        self.actual_value = actual_value


class ConnectionError(KoiosComponentError):
    """Raised when component connection operations fail."""
    
    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None,
                 component_id: Optional[str] = None):
        details = {}
        if host:
            details["host"] = host
        if port:
            details["port"] = port
            
        super().__init__(message, component_id, details)
        self.host = host
        self.port = port


class ConfigurationError(KoiosComponentError):
    """Raised when component configuration is invalid."""
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 component_id: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
            
        super().__init__(message, component_id, details)
        self.config_key = config_key


class ComponentNotFoundError(KoiosComponentError):
    """Raised when a requested component cannot be found."""
    pass


class ComponentAlreadyExistsError(KoiosComponentError):
    """Raised when trying to register a component that already exists."""
    pass


class ComponentStateError(KoiosComponentError):
    """Raised when component is in an invalid state for the requested operation."""
    
    def __init__(self, message: str, current_state: Optional[str] = None,
                 required_state: Optional[str] = None, component_id: Optional[str] = None):
        details = {}
        if current_state:
            details["current_state"] = current_state
        if required_state:
            details["required_state"] = required_state
            
        super().__init__(message, component_id, details)
        self.current_state = current_state
        self.required_state = required_state


class PackagingError(KoiosComponentError):
    """Raised when component packaging operations fail."""
    pass


class DeploymentError(KoiosComponentError):
    """Raised when component deployment operations fail."""
    
    def __init__(self, message: str, target_host: Optional[str] = None,
                 component_id: Optional[str] = None):
        details = {}
        if target_host:
            details["target_host"] = target_host
            
        super().__init__(message, component_id, details)
        self.target_host = target_host


class TestingError(KoiosComponentError):
    """Raised when component testing operations fail."""
    
    def __init__(self, message: str, test_name: Optional[str] = None,
                 component_id: Optional[str] = None):
        details = {}
        if test_name:
            details["test_name"] = test_name
            
        super().__init__(message, component_id, details)
        self.test_name = test_name
