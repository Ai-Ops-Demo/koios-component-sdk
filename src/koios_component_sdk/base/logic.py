"""
Base class for logic components.

This module provides the LogicComponent base class for implementing logic
algorithms in the Koios framework. Logic components handle decision making,
state machines, conditional operations, and other logical operations.
"""

from typing import Dict, Any, List, Optional, Union, Callable
from abc import abstractmethod
from enum import Enum
import time

from .component import BaseKoiosComponent, ComponentMetadata, ParameterDefinition, ComponentStatus
from ..exceptions import ValidationError


class LogicState(Enum):
    """Standard logic states."""
    IDLE = "idle"
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETE = "complete"
    ERROR = "error"


class LogicComponent(BaseKoiosComponent):
    """
    Base class for logic components.
    
    This class provides common functionality for logic components including
    state management, condition evaluation, and decision making. Logic
    components implement business logic, state machines, and conditional operations.
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        """Initialize the logic component."""
        super().__init__(component_id, parameters)
        
        # Logic state
        self._logic_state: LogicState = LogicState.IDLE
        self._previous_logic_state: LogicState = LogicState.IDLE
        self._state_change_time: Optional[float] = None
        self._state_duration: float = 0.0
        
        # Inputs and outputs
        self._inputs: Dict[str, Any] = {}
        self._outputs: Dict[str, Any] = {}
        self._conditions: Dict[str, bool] = {}
        
        # Execution control
        self._evaluation_interval: float = parameters.get('evaluation_interval', 1.0)
        self._last_evaluation_time: Optional[float] = None
        
        # Statistics
        self._evaluation_count: int = 0
        self._state_change_count: int = 0
        self._condition_evaluations: Dict[str, int] = {}
        
        # Configuration
        self._auto_reset: bool = parameters.get('auto_reset', False)
        self._reset_delay: float = parameters.get('reset_delay', 0.0)
        self._last_reset_time: Optional[float] = None
    
    @property
    def logic_state(self) -> LogicState:
        """Get current logic state."""
        return self._logic_state
    
    @property
    def previous_logic_state(self) -> LogicState:
        """Get previous logic state."""
        return self._previous_logic_state
    
    @property
    def state_duration(self) -> float:
        """Get duration in current state (seconds)."""
        if self._state_change_time is not None:
            return time.time() - self._state_change_time
        return 0.0
    
    @property
    def inputs(self) -> Dict[str, Any]:
        """Get current input values."""
        return self._inputs.copy()
    
    @property
    def outputs(self) -> Dict[str, Any]:
        """Get current output values."""
        return self._outputs.copy()
    
    @property
    def conditions(self) -> Dict[str, bool]:
        """Get current condition states."""
        return self._conditions.copy()
    
    @property
    def logic_stats(self) -> Dict[str, Any]:
        """Get logic execution statistics."""
        return {
            "logic_state": self._logic_state.value,
            "previous_logic_state": self._previous_logic_state.value,
            "state_duration": self.state_duration,
            "evaluation_count": self._evaluation_count,
            "state_change_count": self._state_change_count,
            "condition_evaluations": self._condition_evaluations.copy()
        }
    
    def get_bindable_fields(self) -> List[str]:
        """Return fields that can be bound to Koios tags."""
        fields = [
            "logic_state",
            "state_duration",
            "evaluation_count",
            "state_change_count"
        ]
        
        # Add input and output fields
        fields.extend([f"input_{name}" for name in self._inputs.keys()])
        fields.extend([f"output_{name}" for name in self._outputs.keys()])
        fields.extend([f"condition_{name}" for name in self._conditions.keys()])
        
        return fields
    
    @abstractmethod
    def evaluate_conditions(self) -> Dict[str, bool]:
        """
        Evaluate logic conditions.
        
        This method must be implemented by subclasses to define the specific
        conditions that drive the logic component's behavior.
        
        Returns:
            Dictionary of condition names and their boolean states
        """
        pass
    
    @abstractmethod
    def execute_logic(self) -> Dict[str, Any]:
        """
        Execute the main logic algorithm.
        
        This method must be implemented by subclasses to define the specific
        logic behavior based on current inputs and conditions.
        
        Returns:
            Dictionary of output values
        """
        pass
    
    def set_input(self, name: str, value: Any) -> bool:
        """
        Set an input value.
        
        Args:
            name: Input name
            value: Input value
            
        Returns:
            True if input was set successfully
        """
        try:
            self._inputs[name] = value
            self.logger.debug(f"Input '{name}' set to {value}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set input '{name}': {str(e)}")
            return False
    
    def get_input(self, name: str, default: Any = None) -> Any:
        """
        Get an input value.
        
        Args:
            name: Input name
            default: Default value if input doesn't exist
            
        Returns:
            Input value or default
        """
        return self._inputs.get(name, default)
    
    def set_output(self, name: str, value: Any) -> bool:
        """
        Set an output value.
        
        Args:
            name: Output name
            value: Output value
            
        Returns:
            True if output was set successfully
        """
        try:
            self._outputs[name] = value
            self.logger.debug(f"Output '{name}' set to {value}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set output '{name}': {str(e)}")
            return False
    
    def get_output(self, name: str, default: Any = None) -> Any:
        """
        Get an output value.
        
        Args:
            name: Output name
            default: Default value if output doesn't exist
            
        Returns:
            Output value or default
        """
        return self._outputs.get(name, default)
    
    def set_logic_state(self, new_state: LogicState) -> bool:
        """
        Change the logic state.
        
        Args:
            new_state: New logic state
            
        Returns:
            True if state change was successful
        """
        try:
            if new_state != self._logic_state:
                self._previous_logic_state = self._logic_state
                self._logic_state = new_state
                self._state_change_time = time.time()
                self._state_change_count += 1
                
                self.logger.info(f"Logic state changed from {self._previous_logic_state.value} to {new_state.value}")
                
                # Call state change handler if implemented
                self._on_state_change(self._previous_logic_state, new_state)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to change logic state: {str(e)}")
            return False
    
    def reset_logic(self) -> bool:
        """
        Reset the logic component to initial state.
        
        Returns:
            True if reset was successful
        """
        try:
            self._logic_state = LogicState.IDLE
            self._previous_logic_state = LogicState.IDLE
            self._state_change_time = time.time()
            self._last_reset_time = time.time()
            
            # Clear conditions
            self._conditions.clear()
            
            # Reset outputs to default values if configured
            default_outputs = self.parameters.get('default_outputs', {})
            for name, value in default_outputs.items():
                self.set_output(name, value)
            
            self.logger.info("Logic component reset")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset logic: {str(e)}")
            return False
    
    def _on_state_change(self, previous_state: LogicState, new_state: LogicState):
        """
        Handle state changes.
        
        Override this method in subclasses to implement custom state change logic.
        
        Args:
            previous_state: Previous logic state
            new_state: New logic state
        """
        pass
    
    def execute(self) -> Dict[str, Any]:
        """Execute logic evaluation and processing."""
        try:
            if self._status != ComponentStatus.RUNNING:
                return {
                    "success": False,
                    "error": f"Logic component not running (status: {self._status.value})"
                }
            
            current_time = time.time()
            
            # Check if it's time to evaluate
            if (self._last_evaluation_time is None or 
                current_time - self._last_evaluation_time >= self._evaluation_interval):
                
                # Evaluate conditions
                try:
                    new_conditions = self.evaluate_conditions()
                    
                    # Update condition statistics
                    for name, value in new_conditions.items():
                        if name not in self._condition_evaluations:
                            self._condition_evaluations[name] = 0
                        self._condition_evaluations[name] += 1
                    
                    self._conditions.update(new_conditions)
                    
                except Exception as e:
                    self.logger.error(f"Condition evaluation failed: {str(e)}")
                    self.set_logic_state(LogicState.ERROR)
                    raise
                
                # Execute main logic
                try:
                    new_outputs = self.execute_logic()
                    self._outputs.update(new_outputs)
                    
                except Exception as e:
                    self.logger.error(f"Logic execution failed: {str(e)}")
                    self.set_logic_state(LogicState.ERROR)
                    raise
                
                self._evaluation_count += 1
                self._last_evaluation_time = current_time
            
            # Handle auto-reset
            if (self._auto_reset and 
                self._logic_state == LogicState.COMPLETE and
                self._last_reset_time is not None and
                current_time - self._last_reset_time >= self._reset_delay):
                
                self.reset_logic()
            
            # Record execution
            self._record_execution()
            
            return {
                "success": True,
                "logic_state": self._logic_state.value,
                "inputs": self._inputs.copy(),
                "outputs": self._outputs.copy(),
                "conditions": self._conditions.copy(),
                "stats": self.logic_stats
            }
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_parameters(self) -> bool:
        """Validate logic component parameters."""
        try:
            # Validate evaluation interval
            evaluation_interval = self.parameters.get('evaluation_interval', 1.0)
            if not isinstance(evaluation_interval, (int, float)) or evaluation_interval <= 0:
                raise ValidationError("evaluation_interval must be a positive number", "evaluation_interval", "positive number", evaluation_interval, self.component_id)
            
            # Validate reset delay
            reset_delay = self.parameters.get('reset_delay', 0.0)
            if not isinstance(reset_delay, (int, float)) or reset_delay < 0:
                raise ValidationError("reset_delay must be a non-negative number", "reset_delay", "non-negative number", reset_delay, self.component_id)
            
            # Validate auto_reset
            auto_reset = self.parameters.get('auto_reset', False)
            if not isinstance(auto_reset, bool):
                raise ValidationError("auto_reset must be a boolean", "auto_reset", "boolean", auto_reset, self.component_id)
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Parameter validation failed: {str(e)}", component_id=self.component_id)
    
    def initialize(self) -> bool:
        """Initialize the logic component."""
        try:
            self._set_status(ComponentStatus.INITIALIZING)
            
            # Set up parameters
            self._evaluation_interval = self.parameters.get('evaluation_interval', 1.0)
            self._auto_reset = self.parameters.get('auto_reset', False)
            self._reset_delay = self.parameters.get('reset_delay', 0.0)
            
            # Initialize inputs with default values
            default_inputs = self.parameters.get('default_inputs', {})
            self._inputs.update(default_inputs)
            
            # Initialize outputs with default values
            default_outputs = self.parameters.get('default_outputs', {})
            self._outputs.update(default_outputs)
            
            # Reset statistics
            self._evaluation_count = 0
            self._state_change_count = 0
            self._condition_evaluations.clear()
            self._last_evaluation_time = None
            
            # Set initial state
            self.reset_logic()
            
            self._set_status(ComponentStatus.INITIALIZED)
            self.logger.info("Logic component initialized successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def start(self) -> bool:
        """Start the logic component."""
        try:
            if self._status != ComponentStatus.INITIALIZED:
                raise ValueError(f"Cannot start from status {self._status.value}")
            
            self._set_status(ComponentStatus.STARTING)
            
            # Reset to initial state
            self.reset_logic()
            
            self._set_status(ComponentStatus.RUNNING)
            self.logger.info("Logic component started successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def stop(self) -> bool:
        """Stop the logic component."""
        try:
            self._set_status(ComponentStatus.STOPPING)
            
            # Set outputs to safe values if configured
            safe_outputs = self.parameters.get('safe_outputs', {})
            for name, value in safe_outputs.items():
                self.set_output(name, value)
            
            # Set logic state to idle
            self.set_logic_state(LogicState.IDLE)
            
            self._set_status(ComponentStatus.STOPPED)
            self.logger.info("Logic component stopped successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
