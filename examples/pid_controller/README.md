# Advanced PID Controller Example

This example demonstrates how to create a sophisticated PID controller component using the Koios Component SDK. The controller includes advanced features typically found in industrial control systems.

## Features

- **Standard PID Algorithm**: Proportional, Integral, and Derivative control
- **Anti-Windup Protection**: Prevents integral windup using back-calculation method
- **Derivative Filtering**: First-order low-pass filter to reduce derivative kick
- **Gain Scheduling**: Automatic gain adjustment based on process variable
- **Manual/Automatic Mode**: Seamless switching between manual and automatic control
- **Output Rate Limiting**: Prevents rapid output changes that could damage equipment
- **Comprehensive Monitoring**: Detailed statistics and diagnostic information

## Usage

### Basic Usage

```python
from component import AdvancedPIDController

# Create controller with basic configuration
config = {
    "kp": 1.0,
    "ki": 0.1, 
    "kd": 0.01,
    "sample_time": 1.0,
    "output_min": 0.0,
    "output_max": 100.0
}

controller = AdvancedPIDController("my_pid", config)

# Initialize and start
controller.initialize()
controller.start()

# Set control parameters
controller.setpoint = 75.0
controller.process_variable = 70.0

# Execute control loop
result = controller.execute()
print(f"Control output: {controller.output}")

# Stop controller
controller.stop()
```

### Advanced Configuration with Gain Scheduling

```python
# Advanced configuration with gain scheduling
advanced_config = {
    "kp": 2.0,
    "ki": 0.5,
    "kd": 0.1,
    "sample_time": 1.0,
    "output_min": 0.0,
    "output_max": 100.0,
    
    # Anti-windup settings
    "integral_min": -50.0,
    "integral_max": 50.0,
    
    # Derivative filtering
    "derivative_filter_time": 0.2,
    
    # Rate limiting
    "output_rate_limit": 10.0,  # Max 10 units/second change
    
    # Gain scheduling
    "gain_schedule_enabled": True,
    "gain_schedule_points": [
        [0, 1.0, 1.0, 1.0],    # At PV=0: normal gains
        [50, 1.2, 0.8, 1.1],  # At PV=50: higher P, lower I
        [100, 0.8, 1.2, 0.9]  # At PV=100: lower P, higher I
    ]
}

controller = AdvancedPIDController("advanced_pid", advanced_config)
```

### Integration with Koios Tags

The controller automatically binds to Koios tags for seamless integration:

```python
# Input tags (automatically read by controller)
# - pid_setpoint: Control setpoint
# - pid_process_variable: Measured process variable
# - pid_manual_mode: Manual/auto mode selection
# - pid_manual_output: Manual output value

# Output tags (automatically written by controller)  
# - pid_output: Control output
# - pid_error: Current error
# - pid_integral_term: Integral term for monitoring
# - pid_derivative_term: Derivative term for monitoring
```

## Configuration Parameters

### Basic PID Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kp` | float | 1.0 | Proportional gain |
| `ki` | float | 0.1 | Integral gain |
| `kd` | float | 0.01 | Derivative gain |
| `sample_time` | float | 1.0 | Control loop sample time (seconds) |
| `output_min` | float | 0.0 | Minimum output value |
| `output_max` | float | 100.0 | Maximum output value |

### Anti-Windup Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `integral_min` | float | -100.0 | Minimum integral term value |
| `integral_max` | float | 100.0 | Maximum integral term value |

### Advanced Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `derivative_filter_time` | float | 0.1 | Derivative filter time constant (seconds) |
| `output_rate_limit` | float | null | Maximum output change rate (units/second) |
| `gain_schedule_enabled` | boolean | false | Enable gain scheduling |
| `gain_schedule_points` | array | [] | Gain scheduling points [PV, Kp_mult, Ki_mult, Kd_mult] |

## Gain Scheduling

Gain scheduling allows the controller to automatically adjust its gains based on the process variable value. This is useful for nonlinear processes where different operating points require different control parameters.

### Configuration

```python
"gain_schedule_points": [
    [0, 1.0, 1.0, 1.0],      # At PV=0: use base gains
    [25, 1.2, 0.8, 1.1],    # At PV=25: 20% higher Kp, 20% lower Ki
    [50, 1.5, 0.6, 1.2],    # At PV=50: 50% higher Kp, 40% lower Ki  
    [75, 1.2, 0.9, 1.0],    # At PV=75: 20% higher Kp, 10% lower Ki
    [100, 1.0, 1.0, 1.0]    # At PV=100: use base gains
]
```

The controller performs linear interpolation between points for smooth gain transitions.

## Anti-Windup Protection

The controller implements back-calculation anti-windup protection:

1. **Integral Limiting**: The integral term is clamped to configured limits
2. **Back-Calculation**: When the integral term saturates, the error sum is recalculated to prevent further windup
3. **Monitoring**: Saturation events are counted and logged for diagnostics

## Derivative Filtering

To reduce derivative kick and noise sensitivity, the controller applies a first-order low-pass filter to the derivative term:

```
Filtered_D(n) = (1-α) × Filtered_D(n-1) + α × Raw_D(n)
```

Where `α = dt / (filter_time + dt)`

## Output Rate Limiting

Rate limiting prevents rapid output changes that could damage equipment or cause process upsets:

- Maximum change rate is specified in units per second
- Rate limiting events are counted and logged
- Useful for valve positioning, heater control, etc.

## Monitoring and Diagnostics

The controller provides comprehensive monitoring capabilities:

### Statistics

```python
stats = controller.get_advanced_stats()
print(f"Effective gains: Kp={stats['effective_kp']:.2f}")
print(f"Integral saturations: {stats['integral_saturation_count']}")
print(f"Rate limit events: {stats['rate_limit_count']}")
```

### Logging

The controller logs important events:
- Parameter changes
- Saturation events  
- Rate limiting events
- Periodic status updates

## Testing

The example includes comprehensive test scenarios:

```bash
# Test the component
koios-component test ./examples/pid_controller

# Test specific scenarios
koios-component test ./examples/pid_controller --scenario gain_scheduling
koios-component test ./examples/pid_controller --scenario windup_protection
```

## Deployment

Build and deploy the component:

```bash
# Build component package
koios-component build ./examples/pid_controller

# Deploy to Koios server
koios-component deploy advanced_pid_controller-1.1.0.kcp --host https://koios.example.com
```

## Best Practices

1. **Tuning**: Start with conservative gains and tune incrementally
2. **Gain Scheduling**: Use sparingly and only when process nonlinearity is significant
3. **Rate Limiting**: Set based on actuator capabilities and process dynamics
4. **Monitoring**: Regularly check saturation and rate limiting statistics
5. **Testing**: Always test in simulation before deploying to production

## Troubleshooting

### Common Issues

1. **Oscillation**: Reduce Kp or increase derivative filter time
2. **Slow Response**: Increase Kp or Ki (carefully)
3. **Overshoot**: Reduce Kp or increase Kd
4. **Steady-State Error**: Increase Ki (check for windup)

### Diagnostic Tools

- Monitor integral and derivative terms separately
- Check saturation and rate limiting counters
- Use gain scheduling diagnostics for nonlinear processes
- Enable detailed logging for troubleshooting

## Related Examples

- [Basic PID Controller](../basic_pid/README.md)
- [Fuzzy Logic Controller](../fuzzy_controller/README.md)
- [Cascade Control](../cascade_control/README.md)
