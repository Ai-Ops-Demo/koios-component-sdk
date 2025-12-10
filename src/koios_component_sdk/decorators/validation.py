"""
Validation decorators for Koios components.

This module provides decorators for parameter validation, state validation,
and connection requirements that can be applied to component methods.
"""

from functools import wraps
from typing import Callable, Any, List, Optional
import inspect

from ..exceptions import ValidationError, ConnectionError, ComponentStateError
from ..base.component import ComponentStatus


def validate_parameters(func: Callable) -> Callable:
    """
    Decorator to validate component parameters before method execution.
    
    This decorator automatically calls the component's validate_parameters()
    method before executing the decorated method. If validation fails,
    a ValidationError is raised.
    
    Args:
        func: Method to decorate
        
    Returns:
        Decorated method
        
    Example:
        @validate_parameters
        def start(self):
            # Method will only execute if parameters are valid
            pass
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Check if the object has a validate_parameters method
        if hasattr(self, 'validate_parameters'):
            if not self.validate_parameters():
                raise ValidationError(
                    f"Parameter validation failed before calling {func.__name__}",
                    component_id=getattr(self, 'component_id', None)
                )
        else:
            # Log warning if validate_parameters method is missing
            if hasattr(self, 'logger'):
                self.logger.warning(f"validate_parameters method not found on {self.__class__.__name__}")
        
        return func(self, *args, **kwargs)
    
    return wrapper


def require_connection(func: Callable) -> Callable:
    """
    Decorator to ensure component is connected before method execution.
    
    This decorator checks if the component has a 'connected' attribute and
    raises a ConnectionError if the component is not connected.
    
    Args:
        func: Method to decorate
        
    Returns:
        Decorated method
        
    Example:
        @require_connection
        def read_tag(self, address):
            # Method will only execute if component is connected
            pass
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Check if the object has a connected attribute
        if hasattr(self, 'connected'):
            if not self.connected:
                raise ConnectionError(
                    f"Connection required for {func.__name__}",
                    host=getattr(self, 'host', None),
                    port=getattr(self, 'port', None),
                    component_id=getattr(self, 'component_id', None)
                )
        elif hasattr(self, '_connected'):
            if not self._connected:
                raise ConnectionError(
                    f"Connection required for {func.__name__}",
                    host=getattr(self, '_host', None),
                    port=getattr(self, '_port', None),
                    component_id=getattr(self, 'component_id', None)
                )
        else:
            # Log warning if connected attribute is missing
            if hasattr(self, 'logger'):
                self.logger.warning(f"Connected attribute not found on {self.__class__.__name__}")
        
        return func(self, *args, **kwargs)
    
    return wrapper


def validate_state(*required_states: ComponentStatus) -> Callable:
    """
    Decorator to validate component state before method execution.
    
    This decorator checks if the component is in one of the required states
    before executing the decorated method.
    
    Args:
        *required_states: Required component states
        
    Returns:
        Decorator function
        
    Example:
        @validate_state(ComponentStatus.RUNNING)
        def execute(self):
            # Method will only execute if component is running
            pass
            
        @validate_state(ComponentStatus.STOPPED, ComponentStatus.INITIALIZED)
        def start(self):
            # Method will execute if component is stopped or initialized
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get current status
            current_status = None
            if hasattr(self, 'get_status'):
                current_status = self.get_status()
            elif hasattr(self, '_status'):
                current_status = self._status
            else:
                # Log warning if status attribute is missing
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Status attribute not found on {self.__class__.__name__}")
                return func(self, *args, **kwargs)
            
            # Check if current status is in required states
            if current_status not in required_states:
                required_names = [state.value for state in required_states]
                raise ComponentStateError(
                    f"Invalid state for {func.__name__}. Required: {required_names}, Current: {current_status.value}",
                    current_state=current_status.value,
                    required_state=', '.join(required_names),
                    component_id=getattr(self, 'component_id', None)
                )
            
            return func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator


def validate_parameter_types(**type_specs) -> Callable:
    """
    Decorator to validate parameter types for method arguments.
    
    This decorator validates that method arguments match the specified types.
    
    Args:
        **type_specs: Mapping of parameter names to expected types
        
    Returns:
        Decorator function
        
    Example:
        @validate_parameter_types(address=str, value=(int, float))
        def write_tag(self, address, value):
            # address must be str, value must be int or float
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate parameter types
            for param_name, expected_type in type_specs.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    
                    # Skip None values unless explicitly checking for None
                    if value is None and type(None) not in (expected_type if isinstance(expected_type, tuple) else (expected_type,)):
                        continue
                    
                    if not isinstance(value, expected_type):
                        type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
                        raise ValidationError(
                            f"Parameter '{param_name}' must be of type {type_name}, got {type(value).__name__}",
                            parameter_name=param_name,
                            expected_type=type_name,
                            actual_value=value
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def validate_parameter_range(**range_specs) -> Callable:
    """
    Decorator to validate parameter value ranges.
    
    This decorator validates that numeric method arguments fall within
    specified ranges.
    
    Args:
        **range_specs: Mapping of parameter names to (min, max) tuples
        
    Returns:
        Decorator function
        
    Example:
        @validate_parameter_range(temperature=(0, 100), pressure=(0, None))
        def set_values(self, temperature, pressure):
            # temperature must be 0-100, pressure must be >= 0
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate parameter ranges
            for param_name, (min_val, max_val) in range_specs.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    
                    # Skip None values
                    if value is None:
                        continue
                    
                    # Check minimum value
                    if min_val is not None and value < min_val:
                        raise ValidationError(
                            f"Parameter '{param_name}' must be >= {min_val}, got {value}",
                            parameter_name=param_name,
                            actual_value=value
                        )
                    
                    # Check maximum value
                    if max_val is not None and value > max_val:
                        raise ValidationError(
                            f"Parameter '{param_name}' must be <= {max_val}, got {value}",
                            parameter_name=param_name,
                            actual_value=value
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def validate_not_none(*param_names: str) -> Callable:
    """
    Decorator to validate that specified parameters are not None.
    
    Args:
        *param_names: Names of parameters that must not be None
        
    Returns:
        Decorator function
        
    Example:
        @validate_not_none('address', 'value')
        def write_tag(self, address, value):
            # address and value must not be None
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Check for None values
            for param_name in param_names:
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if value is None:
                        raise ValidationError(
                            f"Parameter '{param_name}' cannot be None",
                            parameter_name=param_name,
                            actual_value=value
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
