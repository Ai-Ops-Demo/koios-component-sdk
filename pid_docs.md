# Advanced PID Controller

Advanced PID controller with anti-windup, derivative filtering, and gain scheduling

## Component Information

| Property | Value |
|----------|-------|
| Name | Advanced PID Controller |
| Version | 1.0.0 |
| Author | Koios SDK Example |
| Category | control |
| Entry Point | component.AdvancedPIDController |

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| kp | float | Yes | 1.0 | Proportional gain |
| ki | float | Yes | 0.1 | Integral gain |
| kd | float | Yes | 0.01 | Derivative gain |
| sample_time | float | No | 1.0 | Control loop sample time in seconds |
| output_min | float | No | 0.0 | Minimum output value |
| output_max | float | No | 100.0 | Maximum output value |
| integral_min | float | No | -100.0 | Minimum integral term value for anti-windup |
| integral_max | float | No | 100.0 | Maximum integral term value for anti-windup |
| derivative_filter_time | float | No | 0.1 | Derivative filter time constant in seconds |
| output_rate_limit | float | No | None | Maximum output change rate per second (null for no limit) |
| gain_schedule_enabled | boolean | No | False | Enable gain scheduling based on process variable |
| gain_schedule_points | json | No | [] | Gain scheduling points as array of [pv, kp_multiplier, ki_multiplier, kd_multiplier] |

## Tag Bindings

### Input Tags

- **setpoint** (`pid_setpoint`): Control setpoint value
- **process_variable** (`pid_process_variable`): Process variable (measured value)
- **manual_mode** (`pid_manual_mode`): Manual/automatic mode selection
- **manual_output** (`pid_manual_output`): Manual output value when in manual mode

### Output Tags

- **output** (`pid_output`): Control output value
- **error** (`pid_error`): Current control error (setpoint - process_variable)
- **integral_term** (`pid_integral_term`): Integral term value for monitoring
- **derivative_term** (`pid_derivative_term`): Derivative term value for monitoring

## Methods

### metadata

**Decorators:**
- `@property`

### parameter_definitions

**Decorators:**
- `@property`

### setpoint

Setpoint input from Koios tag.

**Decorators:**
- `@bind_to_tag`

### process_variable

Process variable input from Koios tag.

**Decorators:**
- `@bind_to_tag`

### output

Control output to Koios tag.

**Decorators:**
- `@bind_to_tag`

### error

Current error to Koios tag.

**Decorators:**
- `@bind_to_tag`

### integral_term

Integral term for monitoring.

**Decorators:**
- `@bind_to_tag`

### derivative_term

Derivative term for monitoring.

**Decorators:**
- `@bind_to_tag`

### get_bindable_fields

Extended bindable fields for advanced PID.

### initialize_pid_parameters

Initialize PID parameters on start.

**Decorators:**
- `@on_start`

### cleanup_pid

Cleanup on stop.

**Decorators:**
- `@on_stop`

### compute_output

Compute PID output with advanced features.

**Decorators:**
- `@validate_parameters`

### get_advanced_stats

Get advanced PID statistics.

### reset

Enhanced reset with advanced features.

## Usage Example

```python
from component import AdvancedPIDController

# Create component instance
config = {
    "kp": 1.0,
    "ki": 0.1,
    "kd": 0.01,
}

component = AdvancedPIDController("my_component", config)

# Initialize and start
component.initialize()
component.start()

# Execute component
result = component.execute()
print(f'Result: {result}')

# Stop component
component.stop()
```