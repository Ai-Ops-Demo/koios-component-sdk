"""
Binding decorators for Koios components.

This module provides decorators for binding component methods and attributes
to Koios framework objects like tags, devices, and models.
"""

from functools import wraps
from typing import Callable, Any, Optional, Dict, List
import inspect


def bind_to_tag(tag_name: str, direction: str = "bidirectional", 
                field_name: Optional[str] = None) -> Callable:
    """
    Decorator to bind a method or property to a Koios tag.
    
    This decorator marks a method or property for binding to a Koios tag,
    enabling automatic data exchange between the component and the tag.
    
    Args:
        tag_name: Name of the Koios tag to bind to
        direction: Binding direction ("input", "output", "bidirectional")
        field_name: Optional field name override
        
    Returns:
        Decorator function
        
    Example:
        @bind_to_tag("temperature_setpoint", direction="input")
        def setpoint(self):
            return self._setpoint
            
        @bind_to_tag("heater_output", direction="output")
        def output(self):
            return self._output
    """
    def decorator(func: Callable) -> Callable:
        # Add binding metadata to the function
        if not hasattr(func, '_koios_bindings'):
            func._koios_bindings = []
        
        binding_info = {
            'type': 'tag',
            'name': tag_name,
            'direction': direction,
            'field_name': field_name or func.__name__,
            'method_name': func.__name__
        }
        
        func._koios_bindings.append(binding_info)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Copy binding metadata to wrapper
        wrapper._koios_bindings = func._koios_bindings
        
        return wrapper
    
    return decorator


def bind_to_device(device_name: str, field_name: Optional[str] = None) -> Callable:
    """
    Decorator to bind a method or property to a Koios device.
    
    This decorator marks a method or property for binding to a Koios device,
    enabling access to device properties and status.
    
    Args:
        device_name: Name of the Koios device to bind to
        field_name: Optional field name override
        
    Returns:
        Decorator function
        
    Example:
        @bind_to_device("plc_01", field_name="status")
        def device_status(self):
            return self._device_status
    """
    def decorator(func: Callable) -> Callable:
        # Add binding metadata to the function
        if not hasattr(func, '_koios_bindings'):
            func._koios_bindings = []
        
        binding_info = {
            'type': 'device',
            'name': device_name,
            'field_name': field_name or func.__name__,
            'method_name': func.__name__
        }
        
        func._koios_bindings.append(binding_info)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Copy binding metadata to wrapper
        wrapper._koios_bindings = func._koios_bindings
        
        return wrapper
    
    return decorator


def bind_to_model(model_name: str, binding_type: str = "input",
                  binding_order: Optional[int] = None) -> Callable:
    """
    Decorator to bind a method or property to a Koios AI model.
    
    This decorator marks a method or property for binding to a Koios AI model
    input or output, enabling integration with machine learning workflows.
    
    Args:
        model_name: Name of the Koios AI model to bind to
        binding_type: Type of binding ("input", "output")
        binding_order: Optional binding order for model inputs/outputs
        
    Returns:
        Decorator function
        
    Example:
        @bind_to_model("temperature_predictor", binding_type="input", binding_order=1)
        def temperature_input(self):
            return self._temperature
            
        @bind_to_model("temperature_predictor", binding_type="output")
        def predicted_temperature(self):
            return self._predicted_temp
    """
    def decorator(func: Callable) -> Callable:
        # Add binding metadata to the function
        if not hasattr(func, '_koios_bindings'):
            func._koios_bindings = []
        
        binding_info = {
            'type': 'model',
            'name': model_name,
            'binding_type': binding_type,
            'binding_order': binding_order,
            'method_name': func.__name__
        }
        
        func._koios_bindings.append(binding_info)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Copy binding metadata to wrapper
        wrapper._koios_bindings = func._koios_bindings
        
        return wrapper
    
    return decorator


def bind_to_local_value(local_value_name: str, direction: str = "bidirectional") -> Callable:
    """
    Decorator to bind a method or property to a Koios local value.
    
    This decorator marks a method or property for binding to a Koios local value,
    enabling access to system-wide configuration and status values.
    
    Args:
        local_value_name: Name of the Koios local value to bind to
        direction: Binding direction ("input", "output", "bidirectional")
        
    Returns:
        Decorator function
        
    Example:
        @bind_to_local_value("system_enabled", direction="input")
        def system_enabled(self):
            return self._system_enabled
    """
    def decorator(func: Callable) -> Callable:
        # Add binding metadata to the function
        if not hasattr(func, '_koios_bindings'):
            func._koios_bindings = []
        
        binding_info = {
            'type': 'local_value',
            'name': local_value_name,
            'direction': direction,
            'method_name': func.__name__
        }
        
        func._koios_bindings.append(binding_info)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Copy binding metadata to wrapper
        wrapper._koios_bindings = func._koios_bindings
        
        return wrapper
    
    return decorator


def auto_bind(prefix: str = "", exclude: Optional[List[str]] = None) -> Callable:
    """
    Class decorator to automatically bind methods based on naming conventions.
    
    This decorator automatically creates tag bindings for methods that follow
    naming conventions (e.g., methods starting with "get_" for outputs,
    "set_" for inputs).
    
    Args:
        prefix: Optional prefix for tag names
        exclude: List of method names to exclude from auto-binding
        
    Returns:
        Class decorator function
        
    Example:
        @auto_bind(prefix="reactor_", exclude=["get_internal_state"])
        class ReactorController(ControllerComponent):
            def get_temperature(self):  # Auto-bound to "reactor_temperature" output
                return self._temperature
                
            def set_setpoint(self, value):  # Auto-bound to "reactor_setpoint" input
                self._setpoint = value
    """
    def decorator(cls):
        exclude_list = exclude or []
        
        # Scan class methods for auto-binding candidates
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name in exclude_list:
                continue
            
            # Skip private methods and special methods
            if name.startswith('_'):
                continue
            
            # Auto-bind getter methods (outputs)
            if name.startswith('get_'):
                tag_name = prefix + name[4:]  # Remove 'get_' prefix
                method = bind_to_tag(tag_name, direction="output")(method)
                setattr(cls, name, method)
            
            # Auto-bind setter methods (inputs)
            elif name.startswith('set_'):
                tag_name = prefix + name[4:]  # Remove 'set_' prefix
                method = bind_to_tag(tag_name, direction="input")(method)
                setattr(cls, name, method)
            
            # Auto-bind property-like methods (bidirectional)
            elif not name.startswith(('initialize', 'start', 'stop', 'execute', 'validate')):
                # Check if it's a simple getter (no parameters except self)
                sig = inspect.signature(method)
                if len(sig.parameters) == 1:  # Only 'self' parameter
                    tag_name = prefix + name
                    method = bind_to_tag(tag_name, direction="output")(method)
                    setattr(cls, name, method)
        
        return cls
    
    return decorator


def get_bindings(obj: Any) -> List[Dict[str, Any]]:
    """
    Extract binding information from an object.
    
    This function scans an object for methods with binding metadata
    and returns a list of all bindings.
    
    Args:
        obj: Object to scan for bindings
        
    Returns:
        List of binding dictionaries
        
    Example:
        bindings = get_bindings(my_component)
        for binding in bindings:
            print(f"Binding: {binding['type']} -> {binding['name']}")
    """
    bindings = []
    
    # Scan all methods and attributes
    for name in dir(obj):
        if name.startswith('_'):
            continue
        
        try:
            attr = getattr(obj, name)
            if hasattr(attr, '_koios_bindings'):
                bindings.extend(attr._koios_bindings)
        except (AttributeError, TypeError):
            continue
    
    return bindings


def create_binding_map(obj: Any) -> Dict[str, Dict[str, Any]]:
    """
    Create a mapping of binding names to binding information.
    
    Args:
        obj: Object to create binding map for
        
    Returns:
        Dictionary mapping binding names to binding info
    """
    binding_map = {}
    bindings = get_bindings(obj)
    
    for binding in bindings:
        key = f"{binding['type']}:{binding['name']}"
        binding_map[key] = binding
    
    return binding_map


def validate_bindings(obj: Any) -> List[str]:
    """
    Validate component bindings and return any errors.
    
    Args:
        obj: Object to validate bindings for
        
    Returns:
        List of validation error messages
    """
    errors = []
    bindings = get_bindings(obj)
    
    # Check for duplicate bindings
    seen_bindings = set()
    for binding in bindings:
        key = f"{binding['type']}:{binding['name']}:{binding.get('direction', '')}"
        if key in seen_bindings:
            errors.append(f"Duplicate binding: {key}")
        seen_bindings.add(key)
    
    # Validate binding directions
    valid_directions = {'input', 'output', 'bidirectional'}
    for binding in bindings:
        direction = binding.get('direction')
        if direction and direction not in valid_directions:
            errors.append(f"Invalid binding direction '{direction}' for {binding['name']}")
    
    # Validate model binding orders
    model_bindings = [b for b in bindings if b['type'] == 'model']
    for model_name in set(b['name'] for b in model_bindings):
        model_specific = [b for b in model_bindings if b['name'] == model_name]
        
        # Check for duplicate binding orders within the same model
        input_orders = [b.get('binding_order') for b in model_specific if b.get('binding_type') == 'input' and b.get('binding_order') is not None]
        output_orders = [b.get('binding_order') for b in model_specific if b.get('binding_type') == 'output' and b.get('binding_order') is not None]
        
        if len(input_orders) != len(set(input_orders)):
            errors.append(f"Duplicate input binding orders for model '{model_name}'")
        
        if len(output_orders) != len(set(output_orders)):
            errors.append(f"Duplicate output binding orders for model '{model_name}'")
    
    return errors
