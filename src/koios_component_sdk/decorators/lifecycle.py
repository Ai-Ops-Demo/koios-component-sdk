"""
Lifecycle decorators for Koios components.

This module provides decorators for handling component lifecycle events
such as start, stop, error conditions, and state changes.
"""

from functools import wraps
from typing import Callable, Any, Optional, Dict, List
import logging
import time
import traceback


def on_start(func: Callable) -> Callable:
    """
    Decorator to mark a method as a start event handler.
    
    This decorator marks a method to be called when the component starts.
    Multiple methods can be decorated with @on_start and they will all
    be called in the order they were defined.
    
    Args:
        func: Method to decorate
        
    Returns:
        Decorated method
        
    Example:
        @on_start
        def initialize_hardware(self):
            # Called when component starts
            self.setup_hardware()
    """
    # Mark the function as a start handler
    func._koios_lifecycle_event = 'start'
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Copy metadata to wrapper
    wrapper._koios_lifecycle_event = func._koios_lifecycle_event
    
    return wrapper


def on_stop(func: Callable) -> Callable:
    """
    Decorator to mark a method as a stop event handler.
    
    This decorator marks a method to be called when the component stops.
    Multiple methods can be decorated with @on_stop and they will all
    be called in the order they were defined.
    
    Args:
        func: Method to decorate
        
    Returns:
        Decorated method
        
    Example:
        @on_stop
        def cleanup_hardware(self):
            # Called when component stops
            self.shutdown_hardware()
    """
    # Mark the function as a stop handler
    func._koios_lifecycle_event = 'stop'
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Copy metadata to wrapper
    wrapper._koios_lifecycle_event = func._koios_lifecycle_event
    
    return wrapper


def on_error(func: Callable) -> Callable:
    """
    Decorator to mark a method as an error event handler.
    
    This decorator marks a method to be called when the component
    encounters an error. The method should accept an exception
    parameter.
    
    Args:
        func: Method to decorate
        
    Returns:
        Decorated method
        
    Example:
        @on_error
        def handle_error(self, error):
            # Called when component encounters an error
            self.logger.error(f"Component error: {error}")
            self.reset_to_safe_state()
    """
    # Mark the function as an error handler
    func._koios_lifecycle_event = 'error'
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Copy metadata to wrapper
    wrapper._koios_lifecycle_event = func._koios_lifecycle_event
    
    return wrapper


def on_state_change(from_state: Optional[str] = None, to_state: Optional[str] = None) -> Callable:
    """
    Decorator to mark a method as a state change event handler.
    
    This decorator marks a method to be called when the component
    changes state. Optionally, specific state transitions can be
    specified.
    
    Args:
        from_state: Optional source state to filter on
        to_state: Optional target state to filter on
        
    Returns:
        Decorator function
        
    Example:
        @on_state_change(to_state="running")
        def on_running(self, from_state, to_state):
            # Called when component transitions to running state
            self.start_monitoring()
            
        @on_state_change(from_state="running", to_state="stopped")
        def on_stop_from_running(self, from_state, to_state):
            # Called when component transitions from running to stopped
            self.save_state()
    """
    def decorator(func: Callable) -> Callable:
        # Mark the function as a state change handler
        func._koios_lifecycle_event = 'state_change'
        func._koios_from_state = from_state
        func._koios_to_state = to_state
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Copy metadata to wrapper
        wrapper._koios_lifecycle_event = func._koios_lifecycle_event
        wrapper._koios_from_state = func._koios_from_state
        wrapper._koios_to_state = func._koios_to_state
        
        return wrapper
    
    return decorator


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, 
                    backoff_factor: float = 2.0, 
                    exceptions: tuple = (Exception,)) -> Callable:
    """
    Decorator to retry method execution on failure.
    
    This decorator automatically retries method execution if it fails
    with specified exceptions. Useful for network operations and
    other potentially transient failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorator function
        
    Example:
        @retry_on_failure(max_retries=3, delay=1.0, exceptions=(ConnectionError,))
        def connect_to_device(self):
            # Will retry up to 3 times on ConnectionError
            return self.establish_connection()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Log retry attempt
                        if hasattr(self, 'logger'):
                            self.logger.warning(
                                f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                                f"Retrying in {current_delay:.1f}s..."
                            )
                        
                        # Wait before retry
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        # Log final failure
                        if hasattr(self, 'logger'):
                            self.logger.error(
                                f"All {max_retries + 1} attempts failed for {func.__name__}: {str(e)}"
                            )
                        raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    if hasattr(self, 'logger'):
                        self.logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    
    return decorator


def measure_execution_time(log_level: int = logging.DEBUG) -> Callable:
    """
    Decorator to measure and log method execution time.
    
    This decorator measures how long a method takes to execute
    and logs the duration.
    
    Args:
        log_level: Logging level for execution time messages
        
    Returns:
        Decorator function
        
    Example:
        @measure_execution_time(log_level=logging.INFO)
        def complex_calculation(self):
            # Execution time will be logged
            return self.perform_calculation()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(self, *args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log execution time
                if hasattr(self, 'logger'):
                    self.logger.log(
                        log_level,
                        f"{func.__name__} executed in {execution_time:.3f}s"
                    )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Log execution time even on failure
                if hasattr(self, 'logger'):
                    self.logger.log(
                        log_level,
                        f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}"
                    )
                
                raise
        
        return wrapper
    
    return decorator


def catch_and_log_exceptions(log_level: int = logging.ERROR, 
                           reraise: bool = True) -> Callable:
    """
    Decorator to catch and log exceptions from method execution.
    
    This decorator catches exceptions, logs them with full traceback,
    and optionally re-raises them.
    
    Args:
        log_level: Logging level for exception messages
        reraise: Whether to re-raise caught exceptions
        
    Returns:
        Decorator function
        
    Example:
        @catch_and_log_exceptions(reraise=False)
        def optional_operation(self):
            # Exceptions will be logged but not re-raised
            self.try_optional_feature()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Log exception with traceback
                if hasattr(self, 'logger'):
                    self.logger.log(
                        log_level,
                        f"Exception in {func.__name__}: {str(e)}\n{traceback.format_exc()}"
                    )
                
                # Call error handlers if they exist
                _call_lifecycle_handlers(self, 'error', e)
                
                if reraise:
                    raise
                
                return None
        
        return wrapper
    
    return decorator


def _call_lifecycle_handlers(obj: Any, event_type: str, *args, **kwargs):
    """
    Call all lifecycle event handlers of a specific type.
    
    Args:
        obj: Object to call handlers on
        event_type: Type of lifecycle event
        *args: Arguments to pass to handlers
        **kwargs: Keyword arguments to pass to handlers
    """
    # Find all methods with the specified lifecycle event
    for name in dir(obj):
        if name.startswith('_'):
            continue
        
        try:
            method = getattr(obj, name)
            if (hasattr(method, '_koios_lifecycle_event') and 
                method._koios_lifecycle_event == event_type):
                
                # For state change handlers, check state filters
                if event_type == 'state_change' and len(args) >= 2:
                    from_state, to_state = args[0], args[1]
                    
                    # Check from_state filter
                    if (hasattr(method, '_koios_from_state') and 
                        method._koios_from_state is not None and
                        method._koios_from_state != from_state):
                        continue
                    
                    # Check to_state filter
                    if (hasattr(method, '_koios_to_state') and 
                        method._koios_to_state is not None and
                        method._koios_to_state != to_state):
                        continue
                
                # Call the handler
                try:
                    method(*args, **kwargs)
                except Exception as e:
                    if hasattr(obj, 'logger'):
                        obj.logger.error(f"Error in lifecycle handler {name}: {str(e)}")
                    
        except (AttributeError, TypeError):
            continue


def get_lifecycle_handlers(obj: Any) -> Dict[str, List[str]]:
    """
    Get all lifecycle event handlers for an object.
    
    Args:
        obj: Object to scan for lifecycle handlers
        
    Returns:
        Dictionary mapping event types to lists of handler method names
    """
    handlers = {}
    
    # Scan all methods
    for name in dir(obj):
        if name.startswith('_'):
            continue
        
        try:
            method = getattr(obj, name)
            if hasattr(method, '_koios_lifecycle_event'):
                event_type = method._koios_lifecycle_event
                if event_type not in handlers:
                    handlers[event_type] = []
                handlers[event_type].append(name)
        except (AttributeError, TypeError):
            continue
    
    return handlers
