"""
Base component class and supporting types for the Koios Component SDK.

This module defines the core interfaces and data structures that all Koios components
must implement. It provides the foundation for component lifecycle management,
parameter validation, and integration with the Koios framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import logging
import time
from datetime import datetime

from ..exceptions import ValidationError, ComponentStateError


class ComponentCategory(Enum):
    """Categories of Koios components."""
    CONTROL = "control"
    LOGIC = "logic"
    COMMUNICATION = "communication"
    PROCESSING = "processing"


class ComponentStatus(Enum):
    """Component execution status."""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class ComponentMetadata:
    """Metadata describing a Koios component."""
    name: str
    version: str
    author: str
    description: str
    category: ComponentCategory
    koios_version_min: str
    koios_version_max: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    license: Optional[str] = None
    homepage: Optional[str] = None
    documentation: Optional[str] = None


@dataclass
class ParameterDefinition:
    """Definition of a component parameter."""
    name: str
    type: str  # 'string', 'integer', 'float', 'boolean', 'json', 'list'
    description: str
    required: bool = True
    default: Any = None
    validation: Optional[Dict[str, Any]] = None  # JSON schema validation rules
    units: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    
    def validate_value(self, value: Any) -> bool:
        """Validate a value against this parameter definition."""
        # Type validation
        if self.type == 'string' and not isinstance(value, str):
            return False
        elif self.type == 'integer' and not isinstance(value, int):
            return False
        elif self.type == 'float' and not isinstance(value, (int, float)):
            return False
        elif self.type == 'boolean' and not isinstance(value, bool):
            return False
        elif self.type == 'list' and not isinstance(value, list):
            return False
        
        # Range validation
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        
        # Choice validation
        if self.choices is not None and value not in self.choices:
            return False
        
        return True


class BaseKoiosComponent(ABC):
    """
    Base class for all Koios custom components.
    
    This abstract base class defines the interface that all Koios components must
    implement. It provides common functionality for parameter management, lifecycle
    control, status tracking, and error handling.
    
    Subclasses must implement the abstract methods to define component-specific
    behavior while inheriting the standard Koios integration capabilities.
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        """
        Initialize the component.
        
        Args:
            component_id: Unique identifier for this component instance
            parameters: Dictionary of component parameters
        """
        self.component_id = component_id
        self.parameters = parameters.copy()
        self._status = ComponentStatus.STOPPED
        self._error_message: Optional[str] = None
        self._error_details: Dict[str, Any] = {}
        self._start_time: Optional[datetime] = None
        self._last_execution_time: Optional[datetime] = None
        self._execution_count = 0
        
        # Set up logging
        self.logger = logging.getLogger(f"koios.component.{self.component_id}")
        
        # Validate parameters on initialization
        try:
            if not self.validate_parameters():
                raise ValidationError("Parameter validation failed during initialization", 
                                    component_id=self.component_id)
        except Exception as e:
            self._status = ComponentStatus.ERROR
            self._error_message = str(e)
            raise
    
    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Component metadata - must be implemented by subclasses."""
        pass
    
    @property
    @abstractmethod
    def parameter_definitions(self) -> List[ParameterDefinition]:
        """Parameter definitions - must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def validate_parameters(self) -> bool:
        """
        Validate component parameters.
        
        Returns:
            True if all parameters are valid, False otherwise
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the component.
        
        This method is called once before the component starts running.
        Use it to set up resources, validate configuration, and prepare
        for execution.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start component execution.
        
        This method is called to begin component operation. The component
        should transition to a running state and be ready to execute.
        
        Returns:
            True if start succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop component execution.
        
        This method is called to halt component operation. The component
        should clean up resources and transition to a stopped state.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Execute component logic.
        
        This method is called periodically by the Koios framework to perform
        the component's main function. It should be designed to complete
        quickly and return status information.
        
        Returns:
            Dictionary containing execution results and status
        """
        pass
    
    def get_status(self) -> ComponentStatus:
        """Get current component status."""
        return self._status
    
    def get_error_message(self) -> Optional[str]:
        """Get last error message."""
        return self._error_message
    
    def get_error_details(self) -> Dict[str, Any]:
        """Get detailed error information."""
        return self._error_details.copy()
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get a parameter value."""
        return self.parameters.get(name, default)
    
    def set_parameter(self, name: str, value: Any) -> bool:
        """
        Set a parameter value.
        
        Args:
            name: Parameter name
            value: Parameter value
            
        Returns:
            True if parameter was set successfully, False otherwise
        """
        # Find parameter definition
        param_def = None
        for param in self.parameter_definitions:
            if param.name == name:
                param_def = param
                break
        
        if param_def is None:
            self.logger.warning(f"Unknown parameter: {name}")
            return False
        
        # Validate value
        if not param_def.validate_value(value):
            self.logger.error(f"Invalid value for parameter {name}: {value}")
            return False
        
        # Set parameter
        self.parameters[name] = value
        self.logger.info(f"Parameter {name} set to {value}")
        return True
    
    def get_bindable_fields(self) -> List[str]:
        """
        Return fields that can be bound to Koios tags.
        
        Override this method to specify which component attributes
        can be bound to Koios tags for data exchange.
        
        Returns:
            List of field names that can be bound to tags
        """
        return []
    
    def get_runtime_info(self) -> Dict[str, Any]:
        """Get runtime information about the component."""
        return {
            "component_id": self.component_id,
            "status": self._status.value,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "last_execution_time": self._last_execution_time.isoformat() if self._last_execution_time else None,
            "execution_count": self._execution_count,
            "error_message": self._error_message,
            "metadata": {
                "name": self.metadata.name,
                "version": self.metadata.version,
                "category": self.metadata.category.value,
            }
        }
    
    def _set_status(self, status: ComponentStatus, error_message: Optional[str] = None,
                   error_details: Optional[Dict[str, Any]] = None):
        """Internal method to set component status."""
        self._status = status
        if error_message:
            self._error_message = error_message
            self.logger.error(f"Component error: {error_message}")
        if error_details:
            self._error_details = error_details
    
    def _validate_state_transition(self, target_status: ComponentStatus) -> bool:
        """Validate if a state transition is allowed."""
        current = self._status
        
        # Define valid transitions
        valid_transitions = {
            ComponentStatus.STOPPED: [ComponentStatus.INITIALIZING],
            ComponentStatus.INITIALIZING: [ComponentStatus.INITIALIZED, ComponentStatus.ERROR],
            ComponentStatus.INITIALIZED: [ComponentStatus.STARTING, ComponentStatus.STOPPED],
            ComponentStatus.STARTING: [ComponentStatus.RUNNING, ComponentStatus.ERROR],
            ComponentStatus.RUNNING: [ComponentStatus.STOPPING, ComponentStatus.ERROR],
            ComponentStatus.STOPPING: [ComponentStatus.STOPPED, ComponentStatus.ERROR],
            ComponentStatus.FAILED: [ComponentStatus.STOPPED],
            ComponentStatus.ERROR: [ComponentStatus.STOPPED],
        }
        
        return target_status in valid_transitions.get(current, [])
    
    def _record_execution(self):
        """Record execution statistics."""
        self._last_execution_time = datetime.now()
        self._execution_count += 1
    
    def __str__(self) -> str:
        """String representation of the component."""
        return f"{self.metadata.name} ({self.component_id}) - {self._status.value}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the component."""
        return (f"{self.__class__.__name__}(component_id='{self.component_id}', "
                f"status='{self._status.value}', parameters={len(self.parameters)})")
