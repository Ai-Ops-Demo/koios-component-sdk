"""
Decorators for Koios components.

This module provides decorators that add common functionality to component methods,
such as parameter validation, connection requirements, binding management, and
lifecycle event handling.
"""

from .validation import validate_parameters, require_connection, validate_state
from .binding import bind_to_tag, bind_to_device, bind_to_model
from .lifecycle import on_start, on_stop, on_error, on_state_change

__all__ = [
    "validate_parameters",
    "require_connection",
    "validate_state",
    "bind_to_tag",
    "bind_to_device", 
    "bind_to_model",
    "on_start",
    "on_stop",
    "on_error",
    "on_state_change",
]
