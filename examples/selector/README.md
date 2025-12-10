# Selector Component

A logic component that acts as a selector/multiplexer, routing one of multiple input channels to the output based on a selector value. This is similar to a selector block from standard PLC/SCADA function blocks.

## Features

- **Multiple Input Channels**: Configurable number of input channels (input_1, input_2, ..., input_N)
- **Selector-Based Routing**: Select which input to pass through using a selector value (1, 2, 3, etc.)
- **Error Handling**: Handles invalid selector values and missing inputs gracefully
- **Hold Last Valid**: Option to hold the last valid output when selector is invalid
- **Statistics Tracking**: Tracks selection counts and distribution
- **Flexible Configuration**: Configurable number of inputs, default output, and behavior

## Use Cases

- **Signal Routing**: Route different sensor signals to a single processing path
- **Mode Selection**: Switch between different control modes or setpoints
- **Data Multiplexing**: Select one of multiple data sources for processing
- **Manual Override**: Allow operators to manually select input sources
- **Redundancy Switching**: Switch between primary and backup signals

## Component Parameters

- `num_inputs` (integer, default: 3): Number of input channels (2-32)
- `default_output` (float, default: 0.0): Default output value when selector is invalid or input is missing
- `hold_last_valid` (boolean, default: false): 
  - `true`: Hold last valid output when selector is invalid
  - `false`: Use default_output when selector is invalid
- `selector_input_name` (string, default: "selector"): Name of the input tag for selector value
- `evaluation_interval` (float, default: 0.1): Logic evaluation interval in seconds

## Tag Bindings

### Input Tags

- `selector_input`: Selector value (1, 2, 3, etc.) determining which channel to pass through
- `selector_input_1`: Input channel 1
- `selector_input_2`: Input channel 2
- `selector_input_3`: Input channel 3
- `selector_input_N`: Additional input channels (up to `num_inputs`)

### Output Tags

- `selector_output`: Selected output value (from the channel specified by selector)
- `selector_selected_channel`: Currently selected channel number (1-based, null if invalid)
- `selector_selection_valid`: Boolean indicating if current selection is valid

## Usage Examples

### Example 1: Basic 3-Channel Selector

```python
from koios_component_sdk.base import Selector

# Initialize component with 3 input channels
parameters = {
    'num_inputs': 3,
    'default_output': 0.0,
    'hold_last_valid': False
}

component = Selector('selector_001', parameters)
component.initialize()
component.start()

# Set input channel values
component.set_input_channel(1, 10.0)
component.set_input_channel(2, 20.0)
component.set_input_channel(3, 30.0)

# Set selector to channel 2
component.set_input('selector', 2)
component.execute()

# Get output
output = component.get_output('output')
print(f"Output: {output}")  # Should be 20.0
```

### Example 2: Selector with Hold Last Valid

```python
# Configure to hold last valid output
parameters = {
    'num_inputs': 4,
    'default_output': 0.0,
    'hold_last_valid': True  # Hold last valid when selector is invalid
}

component = Selector('selector_002', parameters)
component.initialize()
component.start()

# Set inputs
component.set_input_channel(1, 100.0)
component.set_input_channel(2, 200.0)
component.set_input_channel(3, 300.0)
component.set_input_channel(4, 400.0)

# Select channel 2
component.set_input('selector', 2)
component.execute()
output = component.get_output('output')  # 200.0

# Invalid selector - will hold last valid (200.0)
component.set_input('selector', 99)
component.execute()
output = component.get_output('output')  # Still 200.0 (last valid)
```

### Example 3: Signal Routing

```python
# Route different sensor signals to a single processing path
parameters = {
    'num_inputs': 5,
    'default_output': None,
    'hold_last_valid': True,
    'evaluation_interval': 0.05  # Fast evaluation for real-time routing
}

component = Selector('sensor_router', parameters)
component.initialize()
component.start()

# Bind to sensor inputs (via Koios tags)
# sensor_1 -> input_1
# sensor_2 -> input_2
# sensor_3 -> input_3
# sensor_4 -> input_4
# sensor_5 -> input_5

# Operator selects which sensor to monitor
component.set_input('selector', 3)  # Select sensor 3

# Continuously execute
while component.status == ComponentStatus.RUNNING:
    component.execute()
    selected_value = component.get_output('output')
    print(f"Selected sensor value: {selected_value}")
    time.sleep(0.1)
```

### Example 4: Mode Selection

```python
# Switch between different control setpoints based on mode
parameters = {
    'num_inputs': 4,
    'default_output': 50.0,  # Default setpoint
    'hold_last_valid': False
}

component = Selector('mode_selector', parameters)
component.initialize()
component.start()

# Set different setpoints for different modes
# Mode 1: Manual
component.set_input_channel(1, 45.0)
# Mode 2: Auto
component.set_input_channel(2, 50.0)
# Mode 3: Optimized
component.set_input_channel(3, 55.0)
# Mode 4: Emergency
component.set_input_channel(4, 40.0)

# Switch to mode 3 (Optimized)
component.set_input('selector', 3)
component.execute()
setpoint = component.get_output('output')  # 55.0
```

### Example 5: Using with Koios Tags

```python
# Component automatically binds to Koios tags
# Based on the bindings defined in koios_component.json:
# - selector_input tag -> selector input
# - selector_input_1 tag -> input_1
# - selector_input_2 tag -> input_2
# - selector_input_3 tag -> input_3
# - selector_output tag <- output

component = Selector('tag_selector', {'num_inputs': 3})
component.initialize()
component.start()

# Values come from Koios tags automatically
# Selector value from Koios tag "selector_input"
# Input values from Koios tags "selector_input_1", "selector_input_2", etc.

component.execute()
output_value = component.get_output('output')
```

## Behavior Details

### Selector Value Processing

- Selector value is converted to integer (rounds float values like 1.5 → 2)
- Valid range: 1 to `num_inputs`
- Values outside range are considered invalid

### Invalid Selector Handling

When selector is invalid:
- If `hold_last_valid=True`: Output holds last valid value
- If `hold_last_valid=False`: Output uses `default_output`

### Missing Input Handling

When selected channel has no input value:
- If `hold_last_valid=True`: Output holds last valid value
- If `hold_last_valid=False`: Output uses `default_output`

### Output Updates

- Output updates immediately when selector changes to a valid channel with available input
- Output holds or defaults when selector is invalid or input is missing

## Statistics

The component tracks selection statistics:

```python
stats = component.get_selection_statistics()
print(stats)
# {
#     'num_inputs': 3,
#     'last_selected_channel': 2,
#     'last_valid_output': 20.0,
#     'selection_counts': {1: 10, 2: 5, 3: 3},
#     'total_selections': 18,
#     'invalid_selection_count': 2,
#     'missing_input_count': 1,
#     'selection_distribution': {1: 0.556, 2: 0.278, 3: 0.167}
# }
```

## Best Practices

1. **Default Output**: Set `default_output` to a safe value for your application
2. **Hold Last Valid**: Use `hold_last_valid=True` for critical applications where you want to maintain last known good value
3. **Evaluation Interval**: Set `evaluation_interval` based on your update rate requirements
4. **Input Validation**: Always validate selector values in your application logic
5. **Channel Count**: Choose `num_inputs` based on actual needs (2-32 supported)

## Limitations

- Maximum 32 input channels
- Selector value must be numeric (integer or float)
- Input values can be any type, but should be consistent across channels
- No built-in debouncing for selector changes

## Comparison with Standard Function Blocks

This component is similar to:

- **Siemens S7**: MUX (Multiplexer) function block
- **Allen-Bradley**: Select (SEL) instruction
- **IEC 61131-3**: MUX function block
- **Modicon**: Select function block

## License

MIT

