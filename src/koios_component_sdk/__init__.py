"""
Koios Component SDK

A comprehensive SDK for developing custom components for the Koios industrial automation platform.
This SDK provides base classes, utilities, and tools for creating control components, communication
protocols, data processors, and logic components that integrate seamlessly with Koios.

Key Features:
- Base classes for different component types (Control, Protocol, Processing, Logic)
- Parameter validation and configuration management
- Testing framework with mock Koios environment
- CLI tools for component creation, testing, and packaging
- Template system for rapid component development
- Deployment utilities for Koios integration

Example Usage:
    from koios_component_sdk.base import ControllerComponent
    from koios_component_sdk.decorators import validate_parameters
    
    class MyPIDController(ControllerComponent):
        # Implementation here
        pass
"""

__version__ = "1.0.0"
__author__ = "Ai-OPs, Inc."
__email__ = "support@ai-op.com"

# Core imports
from .base.component import (
    BaseKoiosComponent,
    ComponentMetadata,
    ParameterDefinition,
    ComponentCategory,
)
from .base.controller import ControllerComponent
from .base.protocol import ProtocolComponent
from .base.processor import ProcessorComponent
from .base.logic import LogicComponent

# Decorator imports
from .decorators.validation import validate_parameters, require_connection
from .decorators.binding import bind_to_tag, bind_to_device
from .decorators.lifecycle import on_start, on_stop, on_error

# Exception imports
from .exceptions import (
    KoiosComponentError,
    ValidationError,
    ConnectionError,
    ConfigurationError,
)

# Utility imports
from .utils.validation import validate_schema, validate_parameters as validate_params
from .utils.packaging import ComponentPackager
from .utils.deployment import ComponentDeployer

__all__ = [
    # Core classes
    "BaseKoiosComponent",
    "ComponentMetadata", 
    "ParameterDefinition",
    "ComponentCategory",
    "ControllerComponent",
    "ProtocolComponent",
    "ProcessorComponent",
    "LogicComponent",
    
    # Decorators
    "validate_parameters",
    "require_connection",
    "bind_to_tag",
    "bind_to_device",
    "on_start",
    "on_stop", 
    "on_error",
    
    # Exceptions
    "KoiosComponentError",
    "ValidationError",
    "ConnectionError",
    "ConfigurationError",
    
    # Utilities
    "validate_schema",
    "validate_params",
    "ComponentPackager",
    "ComponentDeployer",
]
