"""
Selector Component Example

This example demonstrates how to create a logic component that acts as a selector/multiplexer.
Based on a selector input value (1, 2, 3, etc.), it passes through the value from the
corresponding input channel to the output.

This is similar to a selector block from standard PLC/SCADA function blocks.
"""

from typing import Dict, Any, List, Optional
import math

from koios_component_sdk.base import LogicComponent
from koios_component_sdk.base.component import ComponentMetadata, ParameterDefinition, ComponentCategory
from koios_component_sdk.decorators import validate_parameters, bind_to_tag, on_start, on_stop


class Selector(LogicComponent):
    """
    Selector/Multiplexer Logic Component.
    
    Features:
    - Multiple input channels (input_1, input_2, input_3, ...)
    - Selector input determines which channel to pass through
    - Configurable number of inputs
    - Default output value for invalid selections
    - Hold last valid output option
    - Input validation and error handling
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        super().__init__(component_id, parameters)
        
        # Configuration
        self._num_inputs = parameters.get('num_inputs', 3)
        self._default_output = parameters.get('default_output', 0.0)
        self._hold_last_valid = parameters.get('hold_last_valid', False)
        self._selector_input_name = parameters.get('selector_input_name', 'selector')
        
        # State tracking
        self._last_valid_output: Optional[Any] = None
        self._last_selected_channel: Optional[int] = None
        self._selection_count: Dict[int, int] = {}  # Track how many times each channel was selected
        
        # Statistics
        self._invalid_selection_count = 0
        self._missing_input_count = 0
    
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="Selector",
            version="1.0.0",
            author="Koios SDK Example",
            description="Selector/multiplexer component that passes through selected input channel based on selector value",
            category=ComponentCategory.LOGIC,
            koios_version_min="1.0.0",
            tags=["selector", "multiplexer", "mux", "logic", "routing"]
        )
    
    @property
    def parameter_definitions(self) -> List[ParameterDefinition]:
        return [
            ParameterDefinition(
                name="num_inputs",
                type="integer",
                description="Number of input channels (input_1, input_2, ..., input_N)",
                default=3,
                min_value=2,
                max_value=32,
                required=False
            ),
            ParameterDefinition(
                name="default_output",
                type="float",
                description="Default output value when selector is invalid or input is missing",
                default=0.0,
                required=False
            ),
            ParameterDefinition(
                name="hold_last_valid",
                type="boolean",
                description="If true, hold last valid output when selector is invalid; if false, use default_output",
                default=False,
                required=False
            ),
            ParameterDefinition(
                name="selector_input_name",
                type="string",
                description="Name of the input tag for the selector value",
                default="selector",
                required=False
            ),
            ParameterDefinition(
                name="evaluation_interval",
                type="float",
                description="Logic evaluation interval in seconds",
                default=0.1,
                min_value=0.01,
                required=False
            ),
        ]
    
    @bind_to_tag("selector_input", direction="input")
    def selector(self) -> Optional[float]:
        """Selector input - determines which input channel to pass through."""
        return self.get_input(self._selector_input_name)
    
    @bind_to_tag("selector_input_1", direction="input")
    def input_1(self) -> Optional[Any]:
        """Input channel 1."""
        return self.get_input('input_1')
    
    @bind_to_tag("selector_input_2", direction="input")
    def input_2(self) -> Optional[Any]:
        """Input channel 2."""
        return self.get_input('input_2')
    
    @bind_to_tag("selector_input_3", direction="input")
    def input_3(self) -> Optional[Any]:
        """Input channel 3."""
        return self.get_input('input_3')
    
    @bind_to_tag("selector_input_4", direction="input")
    def input_4(self) -> Optional[Any]:
        """Input channel 4."""
        return self.get_input('input_4')
    
    @bind_to_tag("selector_input_5", direction="input")
    def input_5(self) -> Optional[Any]:
        """Input channel 5."""
        return self.get_input('input_5')
    
    @bind_to_tag("selector_output", direction="output")
    def output(self) -> Any:
        """Selected output value."""
        return self.get_output('output', self._default_output)
    
    @bind_to_tag("selector_selected_channel", direction="output")
    def selected_channel(self) -> Optional[int]:
        """Currently selected channel number."""
        return self.get_output('selected_channel')
    
    @bind_to_tag("selector_selection_valid", direction="output")
    def selection_valid(self) -> bool:
        """Boolean indicating if current selection is valid."""
        return self.get_output('selection_valid', False)
    
    def _get_input_channel_name(self, channel_num: int) -> str:
        """Get the input channel name for a given channel number."""
        return f"input_{channel_num}"
    
    def _is_valid_channel(self, channel_num: int) -> bool:
        """Check if channel number is valid."""
        return 1 <= channel_num <= self._num_inputs
    
    def _get_selected_input_value(self, channel_num: int) -> Optional[Any]:
        """Get the value from the selected input channel."""
        if not self._is_valid_channel(channel_num):
            return None
        
        channel_name = self._get_input_channel_name(channel_num)
        return self.get_input(channel_name)
    
    def evaluate_conditions(self) -> Dict[str, bool]:
        """
        Evaluate logic conditions.
        
        Returns:
            Dictionary of condition states
        """
        selector_value = self.get_input(self._selector_input_name)
        
        conditions = {
            'selector_valid': selector_value is not None,
            'selector_in_range': False,
            'selected_input_available': False,
            'using_default': False,
            'using_last_valid': False
        }
        
        if selector_value is not None:
            try:
                # Convert to integer (handle float selectors like 1.0, 2.0, etc.)
                selector_int = int(round(selector_value))
                conditions['selector_in_range'] = self._is_valid_channel(selector_int)
                
                if conditions['selector_in_range']:
                    input_value = self._get_selected_input_value(selector_int)
                    conditions['selected_input_available'] = input_value is not None
            except (ValueError, TypeError):
                conditions['selector_in_range'] = False
        
        return conditions
    
    def execute_logic(self) -> Dict[str, Any]:
        """
        Execute the selector logic.
        
        Returns:
            Dictionary with output value
        """
        selector_value = self.get_input(self._selector_input_name)
        output_value = self._default_output
        selection_valid = False
        
        if selector_value is None:
            self.logger.debug("Selector input is None")
            if self._hold_last_valid and self._last_valid_output is not None:
                output_value = self._last_valid_output
                self.logger.debug(f"Using last valid output: {output_value}")
            else:
                output_value = self._default_output
        else:
            try:
                # Convert selector to integer (handle float values)
                selector_int = int(round(selector_value))
                
                if self._is_valid_channel(selector_int):
                    input_value = self._get_selected_input_value(selector_int)
                    
                    if input_value is not None:
                        output_value = input_value
                        selection_valid = True
                        self._last_valid_output = output_value
                        self._last_selected_channel = selector_int
                        
                        # Update statistics
                        if selector_int not in self._selection_count:
                            self._selection_count[selector_int] = 0
                        self._selection_count[selector_int] += 1
                        
                        self.logger.debug(f"Selected channel {selector_int}, output: {output_value}")
                    else:
                        self._missing_input_count += 1
                        self.logger.warning(f"Input channel {selector_int} is not available")
                        
                        if self._hold_last_valid and self._last_valid_output is not None:
                            output_value = self._last_valid_output
                            self.logger.debug(f"Input missing, using last valid output: {output_value}")
                        else:
                            output_value = self._default_output
                else:
                    self._invalid_selection_count += 1
                    self.logger.warning(f"Invalid selector value: {selector_value} (valid range: 1-{self._num_inputs})")
                    
                    if self._hold_last_valid and self._last_valid_output is not None:
                        output_value = self._last_valid_output
                        self.logger.debug(f"Invalid selector, using last valid output: {output_value}")
                    else:
                        output_value = self._default_output
                        
            except (ValueError, TypeError) as e:
                self._invalid_selection_count += 1
                self.logger.error(f"Failed to process selector value '{selector_value}': {str(e)}")
                
                if self._hold_last_valid and self._last_valid_output is not None:
                    output_value = self._last_valid_output
                else:
                    output_value = self._default_output
        
        result = {
            'output': output_value,
            'selected_channel': self._last_selected_channel if selection_valid else None,
            'selection_valid': selection_valid
        }
        
        # Also update outputs dictionary for bindings
        self.set_output('selected_channel', result['selected_channel'])
        self.set_output('selection_valid', result['selection_valid'])
        
        return result
    
    @on_start
    def initialize_selector(self):
        """Initialize selector on start."""
        self.logger.info(f"Selector started with {self._num_inputs} input channels")
        self.logger.info(f"Default output: {self._default_output}, Hold last valid: {self._hold_last_valid}")
        
        # Initialize all input channels to None if not set
        for i in range(1, self._num_inputs + 1):
            channel_name = self._get_input_channel_name(i)
            if channel_name not in self._inputs:
                self.set_input(channel_name, None)
    
    @on_stop
    def cleanup_selector(self):
        """Cleanup on stop."""
        self.logger.info(f"Selector stopped - Last selected channel: {self._last_selected_channel}")
        self.logger.info(f"Selection statistics: {self._selection_count}")
        self.logger.info(f"Invalid selections: {self._invalid_selection_count}, Missing inputs: {self._missing_input_count}")
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """Get statistics about channel selections."""
        total_selections = sum(self._selection_count.values())
        
        return {
            'num_inputs': self._num_inputs,
            'last_selected_channel': self._last_selected_channel,
            'last_valid_output': self._last_valid_output,
            'selection_counts': self._selection_count.copy(),
            'total_selections': total_selections,
            'invalid_selection_count': self._invalid_selection_count,
            'missing_input_count': self._missing_input_count,
            'selection_distribution': {
                channel: (count / total_selections if total_selections > 0 else 0.0)
                for channel, count in self._selection_count.items()
            }
        }
    
    def set_input_channel(self, channel_num: int, value: Any) -> bool:
        """
        Set an input channel value.
        
        Args:
            channel_num: Channel number (1-based)
            value: Value to set
            
        Returns:
            True if successful
        """
        if not self._is_valid_channel(channel_num):
            self.logger.error(f"Invalid channel number: {channel_num} (valid range: 1-{self._num_inputs})")
            return False
        
        channel_name = self._get_input_channel_name(channel_num)
        return self.set_input(channel_name, value)
    
    def get_input_channel(self, channel_num: int, default: Any = None) -> Any:
        """
        Get an input channel value.
        
        Args:
            channel_num: Channel number (1-based)
            default: Default value if channel doesn't exist
            
        Returns:
            Channel value or default
        """
        if not self._is_valid_channel(channel_num):
            return default
        
        channel_name = self._get_input_channel_name(channel_num)
        return self.get_input(channel_name, default)

