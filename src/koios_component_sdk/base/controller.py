"""
Base class for control components.

This module provides the ControllerComponent base class for implementing control
algorithms like PID controllers, fuzzy logic controllers, and other control
strategies in the Koios framework.
"""

from typing import Dict, Any, List, Optional
from abc import abstractmethod

from .component import BaseKoiosComponent, ComponentMetadata, ParameterDefinition, ComponentStatus
from ..exceptions import ValidationError


class ControllerComponent(BaseKoiosComponent):
    """
    Base class for control components (PID, fuzzy logic, etc.).
    
    This class provides common functionality for control components including
    setpoint management, process variable tracking, and output generation.
    Control components typically implement closed-loop control algorithms.
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        """Initialize the controller component."""
        super().__init__(component_id, parameters)
        
        # Control variables
        self._setpoint: float = 0.0
        self._process_variable: float = 0.0
        self._output: float = 0.0
        self._manual_mode: bool = False
        self._manual_output: float = 0.0
        
        # Control limits
        self._output_min: float = parameters.get('output_min', 0.0)
        self._output_max: float = parameters.get('output_max', 100.0)
        
        # Error tracking
        self._error: float = 0.0
        self._previous_error: float = 0.0
        self._error_sum: float = 0.0
        
        # Timing
        self._last_update_time: Optional[float] = None
        self._dt: float = parameters.get('sample_time', 1.0)
    
    @property
    def setpoint(self) -> float:
        """Get the current setpoint."""
        return self._setpoint
    
    @setpoint.setter
    def setpoint(self, value: float):
        """Set the setpoint."""
        self._setpoint = float(value)
        self.logger.debug(f"Setpoint set to {self._setpoint}")
    
    @property
    def process_variable(self) -> float:
        """Get the current process variable."""
        return self._process_variable
    
    @process_variable.setter
    def process_variable(self, value: float):
        """Set the process variable."""
        self._process_variable = float(value)
        self._update_error()
    
    @property
    def output(self) -> float:
        """Get the current output."""
        if self._manual_mode:
            return self._manual_output
        return self._output
    
    @property
    def error(self) -> float:
        """Get the current control error."""
        return self._error
    
    @property
    def manual_mode(self) -> bool:
        """Check if controller is in manual mode."""
        return self._manual_mode
    
    @manual_mode.setter
    def manual_mode(self, value: bool):
        """Set manual mode on/off."""
        self._manual_mode = bool(value)
        if self._manual_mode:
            self.logger.info("Controller switched to manual mode")
        else:
            self.logger.info("Controller switched to automatic mode")
    
    @property
    def manual_output(self) -> float:
        """Get the manual output value."""
        return self._manual_output
    
    @manual_output.setter
    def manual_output(self, value: float):
        """Set the manual output value."""
        self._manual_output = self._clamp_output(float(value))
        self.logger.debug(f"Manual output set to {self._manual_output}")
    
    def get_bindable_fields(self) -> List[str]:
        """Return fields that can be bound to Koios tags."""
        return [
            "setpoint",
            "process_variable", 
            "output",
            "error",
            "manual_mode",
            "manual_output"
        ]
    
    @abstractmethod
    def compute_output(self) -> float:
        """
        Compute the control output.
        
        This method must be implemented by subclasses to define the specific
        control algorithm (PID, fuzzy logic, etc.).
        
        Returns:
            Computed control output value
        """
        pass
    
    def execute(self) -> Dict[str, Any]:
        """Execute the control algorithm."""
        try:
            if self._status != ComponentStatus.RUNNING:
                return {
                    "success": False,
                    "error": f"Controller not running (status: {self._status.value})"
                }
            
            # Update timing
            import time
            current_time = time.time()
            if self._last_update_time is not None:
                self._dt = current_time - self._last_update_time
            self._last_update_time = current_time
            
            # Compute output if in automatic mode
            if not self._manual_mode:
                self._output = self.compute_output()
                self._output = self._clamp_output(self._output)
            
            # Record execution
            self._record_execution()
            
            return {
                "success": True,
                "setpoint": self._setpoint,
                "process_variable": self._process_variable,
                "output": self.output,
                "error": self._error,
                "manual_mode": self._manual_mode,
                "dt": self._dt
            }
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def reset(self):
        """Reset the controller state."""
        self._error = 0.0
        self._previous_error = 0.0
        self._error_sum = 0.0
        self._last_update_time = None
        self.logger.info("Controller reset")
    
    def _update_error(self):
        """Update the control error."""
        self._previous_error = self._error
        self._error = self._setpoint - self._process_variable
    
    def _clamp_output(self, value: float) -> float:
        """Clamp output value to configured limits."""
        return max(self._output_min, min(self._output_max, value))
    
    def validate_parameters(self) -> bool:
        """Validate controller parameters."""
        try:
            # Validate output limits
            output_min = self.parameters.get('output_min', 0.0)
            output_max = self.parameters.get('output_max', 100.0)
            
            if not isinstance(output_min, (int, float)):
                raise ValidationError("output_min must be a number", "output_min", "number", output_min, self.component_id)
            
            if not isinstance(output_max, (int, float)):
                raise ValidationError("output_max must be a number", "output_max", "number", output_max, self.component_id)
            
            if output_min >= output_max:
                raise ValidationError("output_min must be less than output_max", component_id=self.component_id)
            
            # Validate sample time
            sample_time = self.parameters.get('sample_time', 1.0)
            if not isinstance(sample_time, (int, float)) or sample_time <= 0:
                raise ValidationError("sample_time must be a positive number", "sample_time", "positive number", sample_time, self.component_id)
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Parameter validation failed: {str(e)}", component_id=self.component_id)
    
    def initialize(self) -> bool:
        """Initialize the controller."""
        try:
            self._set_status(ComponentStatus.INITIALIZING)
            
            # Set up output limits
            self._output_min = self.parameters.get('output_min', 0.0)
            self._output_max = self.parameters.get('output_max', 100.0)
            self._dt = self.parameters.get('sample_time', 1.0)
            
            # Reset controller state
            self.reset()
            
            self._set_status(ComponentStatus.INITIALIZED)
            self.logger.info("Controller initialized successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def start(self) -> bool:
        """Start the controller."""
        try:
            if self._status != ComponentStatus.INITIALIZED:
                raise ValueError(f"Cannot start from status {self._status.value}")
            
            self._set_status(ComponentStatus.STARTING)
            
            # Perform any start-specific initialization
            self._last_update_time = None
            
            self._set_status(ComponentStatus.RUNNING)
            self.logger.info("Controller started successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def stop(self) -> bool:
        """Stop the controller."""
        try:
            self._set_status(ComponentStatus.STOPPING)
            
            # Set output to safe value if configured
            safe_output = self.parameters.get('safe_output')
            if safe_output is not None:
                self._output = self._clamp_output(float(safe_output))
                self.logger.info(f"Output set to safe value: {self._output}")
            
            self._set_status(ComponentStatus.STOPPED)
            self.logger.info("Controller stopped successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
