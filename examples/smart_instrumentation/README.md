# Endress Hauser ProMag/ProMass Component

A logic component for data input and flow meter analysis using EtherNet/IP communication with Endress Hauser ProMag and ProMass devices. This component provides real-time flow meter data acquisition, validation, and analysis capabilities.

## Features

- **EtherNet/IP Communication**: Full implementation of EtherNet/IP protocol stack for device communication
- **Real-Time Data Acquisition**: Continuous reading of flow meter process values
- **Flow Analysis**: Comprehensive flow value validation and analysis
- **Multi-Parameter Monitoring**: Mass flow, volume flow, density, and temperature tracking
- **Alarm Generation**: Configurable alarms for out-of-range conditions
- **Rate of Change Detection**: Monitors and alerts on rapid flow changes
- **Totalizer Management**: Reset totalizer functionality
- **Device Diagnostics**: Connection status, error tracking, and statistics
- **Automatic Reconnection**: Built-in retry logic for connection failures

## Use Cases

- **Flow Meter Monitoring**: Real-time monitoring of mass and volume flow rates
- **Process Validation**: Validate flow values against configured limits
- **Alarm Management**: Generate alarms for abnormal flow conditions
- **Data Logging**: Collect flow meter data for historical analysis
- **Process Control Integration**: Integrate flow meter data into control systems
- **Quality Assurance**: Monitor density and temperature for process quality

## Component Architecture

The component consists of several layers:

1. **EtherNet/IP Layer**: Low-level EtherNet/IP encapsulation (`EnipClient`)
2. **CIP Layer**: Common Industrial Protocol messaging (`CIPClient`)
3. **Device Layer**: High-level device driver (`PromassDevice`)
4. **Component Layer**: Koios logic component (`PromassProMagComponent`)

## Installation

### Prerequisites

- Python 3.8 or higher
- Koios Component SDK
- Network access to the ProMag/ProMass device

### Component Setup

```bash
# Navigate to the component directory
cd examples/smart_instrumentation

# Validate the component
koios-component validate .

# Test the component
koios-component test .

# Build the component package
koios-component build .
```

## Configuration Parameters

### Device Connection Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_ip` | string | "192.168.1.100" | IP address of the ProMag/ProMass device |
| `device_timeout` | float | 2.0 | Device communication timeout in seconds (0.1-60.0) |
| `input_assembly_instance` | integer | 100 | CIP input assembly instance number |
| `output_assembly_instance` | integer | 150 | CIP output assembly instance number |
| `read_interval` | float | 1.0 | Interval between device reads in seconds (≥0.1) |
| `connection_retry_count` | integer | 3 | Number of connection retry attempts (≥0) |
| `connection_retry_delay` | float | 1.0 | Delay between retry attempts in seconds (≥0.1) |

### Flow Validation Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mass_flow_min` | float | 0.0 | Minimum valid mass flow value |
| `mass_flow_max` | float | 1000.0 | Maximum valid mass flow value |
| `volume_flow_min` | float | 0.0 | Minimum valid volume flow value |
| `volume_flow_max` | float | 1000.0 | Maximum valid volume flow value |
| `density_min` | float | 0.0 | Minimum valid density value |
| `density_max` | float | 2000.0 | Maximum valid density value |
| `temperature_min` | float | -50.0 | Minimum valid temperature value |
| `temperature_max` | float | 200.0 | Maximum valid temperature value |

### Analysis Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_flow_validation` | boolean | true | Enable flow value validation against limits |
| `enable_rate_of_change_check` | boolean | true | Enable rate of change validation |
| `max_rate_of_change` | float | 100.0 | Maximum allowed rate of change (units/second) |
| `evaluation_interval` | float | 1.0 | Logic evaluation interval in seconds (≥0.1) |

## Tag Bindings

### Input Tags

- `promass_reset_totalizer` (boolean): Command to reset totalizer

### Output Tags

- `promass_mass_flow` (float): Mass flow value from device
- `promass_volume_flow` (float): Volume flow value from device
- `promass_density` (float): Density value from device
- `promass_temperature` (float): Temperature value from device
- `promass_device_status` (string): Device connection status (CONNECTED, DISCONNECTED, CONNECTION_FAILED, READ_ERROR)
- `promass_flow_valid` (boolean): Flow validation status (true if all values within limits)

## Usage Examples

### Example 1: Basic Configuration

```python
from component import PromassProMagComponent

# Basic configuration
config = {
    "device_ip": "192.168.1.100",
    "device_timeout": 2.0,
    "read_interval": 1.0
}

component = PromassProMagComponent("flow_meter_001", config)
component.initialize()
component.start()

# Execute component logic
result = component.execute()

# Access flow values
mass_flow = component.mass_flow
volume_flow = component.volume_flow
density = component.density
temperature = component.temperature

print(f"Mass Flow: {mass_flow} kg/h")
print(f"Volume Flow: {volume_flow} m³/h")
print(f"Density: {density} kg/m³")
print(f"Temperature: {temperature} °C")
```

### Example 2: Advanced Configuration with Validation

```python
# Advanced configuration with flow validation
advanced_config = {
    "device_ip": "192.168.1.50",
    "device_timeout": 3.0,
    "read_interval": 0.5,
    "connection_retry_count": 5,
    "connection_retry_delay": 2.0,
    
    # Flow limits
    "mass_flow_min": 10.0,
    "mass_flow_max": 500.0,
    "volume_flow_min": 5.0,
    "volume_flow_max": 250.0,
    "density_min": 800.0,
    "density_max": 1200.0,
    "temperature_min": 0.0,
    "temperature_max": 100.0,
    
    # Analysis settings
    "enable_flow_validation": True,
    "enable_rate_of_change_check": True,
    "max_rate_of_change": 50.0,  # Max 50 units/second change
    "evaluation_interval": 0.5
}

component = PromassProMagComponent("flow_meter_002", advanced_config)
component.initialize()
component.start()

# Monitor flow values
while component.status == ComponentStatus.RUNNING:
    result = component.execute()
    
    if result["success"]:
        # Check validation status
        if component.flow_valid:
            print("Flow values are valid")
        else:
            print("Flow validation failed - check alarms")
        
        # Get statistics
        stats = component.get_statistics()
        print(f"Total reads: {stats['total_reads']}")
        print(f"Successful reads: {stats['successful_reads']}")
        print(f"Failed reads: {stats['failed_reads']}")
    
    time.sleep(0.5)
```

### Example 3: Alarm Monitoring

```python
# Monitor alarms
component = PromassProMagComponent("flow_meter_003", config)
component.initialize()
component.start()

while True:
    result = component.execute()
    conditions = component.evaluate_conditions()
    
    # Check for active alarms
    if conditions.get('any_alarm_active'):
        outputs = component.execute_logic()
        alarms = outputs.get('alarms', {})
        
        # Check specific alarms
        if alarms.get('mass_flow_high'):
            print("ALARM: Mass flow exceeds maximum limit")
        if alarms.get('mass_flow_low'):
            print("ALARM: Mass flow below minimum limit")
        if alarms.get('rate_of_change_high'):
            print("ALARM: Rate of change exceeded")
        if alarms.get('device_error'):
            print("ALARM: Device communication error")
    
    time.sleep(1.0)
```

### Example 4: Totalizer Reset

```python
# Reset totalizer via input tag
component = PromassProMagComponent("flow_meter_004", config)
component.initialize()
component.start()

# Set reset command via input
component.set_input('reset_totalizer', True)
component.execute()

# Command is automatically cleared after execution
```

### Example 5: Integration with Koios Tags

```python
# Component automatically binds to Koios tags
# Based on bindings in koios_component.json:
# - promass_reset_totalizer tag -> reset_totalizer input
# - promass_mass_flow tag <- mass_flow output
# - promass_volume_flow tag <- volume_flow output
# - promass_density tag <- density output
# - promass_temperature tag <- temperature output
# - promass_device_status tag <- device_status output
# - promass_flow_valid tag <- flow_valid output

component = PromassProMagComponent("flow_meter_005", config)
component.initialize()
component.start()

# Values are automatically read from/written to Koios tags
component.execute()
```

## Flow Validation

The component performs comprehensive flow validation:

### Value Range Validation

- **Mass Flow**: Validates against `mass_flow_min` and `mass_flow_max`
- **Volume Flow**: Validates against `volume_flow_min` and `volume_flow_max`
- **Density**: Validates against `density_min` and `density_max`
- **Temperature**: Validates against `temperature_min` and `temperature_max`

### Rate of Change Validation

Monitors the rate of change for mass flow and volume flow:

```
Rate of Change = |Current Value - Previous Value| / Time Delta
```

If the rate exceeds `max_rate_of_change`, an alarm is generated.

### Alarm Types

The component generates the following alarms:

- `mass_flow_high`: Mass flow exceeds maximum limit
- `mass_flow_low`: Mass flow below minimum limit
- `volume_flow_high`: Volume flow exceeds maximum limit
- `volume_flow_low`: Volume flow below minimum limit
- `density_high`: Density exceeds maximum limit
- `density_low`: Density below minimum limit
- `temperature_high`: Temperature exceeds maximum limit
- `temperature_low`: Temperature below minimum limit
- `rate_of_change_high`: Rate of change exceeded
- `device_error`: Device communication error

## Device Status

The component tracks device connection status:

- **CONNECTED**: Device is connected and communicating
- **DISCONNECTED**: Device is not connected
- **CONNECTION_FAILED**: Connection attempt failed
- **READ_ERROR**: Error occurred during data read

## Statistics and Diagnostics

The component provides comprehensive statistics:

```python
stats = component.get_statistics()
print(stats)
# {
#     'total_reads': 1000,
#     'successful_reads': 995,
#     'failed_reads': 5,
#     'read_error_count': 3,
#     'connection_error_count': 2,
#     'device_status': 'CONNECTED',
#     'connected': True,
#     'current_values': {
#         'mass_flow': 125.5,
#         'volume_flow': 62.3,
#         'density': 1005.2,
#         'temperature': 25.8
#     },
#     'alarms': {...}
# }
```

## EtherNet/IP Protocol Details

### Assembly Instances

The component uses CIP (Common Industrial Protocol) assembly objects:

- **Input Assembly**: Contains process values (mass flow, volume flow, density, temperature)
- **Output Assembly**: Contains commands (totalizer reset, etc.)

Default assembly instances:
- Input Assembly Instance: 100
- Output Assembly Instance: 150

**Note**: These values may need to be adjusted based on your specific Endress Hauser device configuration. Consult your device manual for the correct assembly instance numbers.

### Data Structure

The input assembly structure (default):
- Mass Flow (float, 4 bytes)
- Volume Flow (float, 4 bytes)
- Density (float, 4 bytes)
- Temperature (float, 4 bytes)

**Note**: The actual structure may vary depending on your device model and configuration. Adjust `PromassAssemblies.INPUT_STRUCT` in the component code to match your device's assembly structure.

## Best Practices

1. **Network Configuration**: Ensure stable network connectivity to the device
2. **Timeout Settings**: Set appropriate timeout values based on network latency
3. **Read Interval**: Balance between update rate and network load
4. **Validation Limits**: Set realistic limits based on your process requirements
5. **Rate of Change**: Configure based on expected process dynamics
6. **Error Handling**: Monitor connection errors and implement appropriate alerts
7. **Assembly Instances**: Verify assembly instance numbers match your device configuration
8. **Data Structure**: Confirm the assembly data structure matches your device

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify device IP address is correct
   - Check network connectivity (ping device)
   - Verify device is powered on and EtherNet/IP is enabled
   - Check firewall settings

2. **Read Errors**
   - Verify assembly instance numbers are correct
   - Check device configuration matches component settings
   - Verify device is not in maintenance mode
   - Check for network timeouts

3. **Invalid Flow Values**
   - Verify assembly data structure matches device output
   - Check byte order (little-endian vs big-endian)
   - Verify data types match (float, integer, etc.)

4. **Alarms Not Clearing**
   - Check validation limits are set correctly
   - Verify flow values are within expected range
   - Check rate of change limits

### Diagnostic Steps

1. **Check Device Status**
   ```python
   status = component.device_status
   print(f"Device Status: {status}")
   ```

2. **Check Connection Statistics**
   ```python
   stats = component.get_statistics()
   print(f"Connection Errors: {stats['connection_error_count']}")
   print(f"Read Errors: {stats['read_error_count']}")
   ```

3. **Verify Assembly Instances**
   - Check device configuration
   - Verify assembly instance numbers in component parameters
   - Test with device configuration tool

4. **Monitor Network Traffic**
   - Use network analyzer to verify EtherNet/IP packets
   - Check for packet loss or delays
   - Verify correct port (44818)

## Testing

Test the component:

```bash
# Validate component structure
koios-component validate examples/smart_instrumentation

# Run component tests
koios-component test examples/smart_instrumentation

# Test specific scenarios
koios-component test examples/smart_instrumentation --scenario device_connection
koios-component test examples/smart_instrumentation --scenario flow_validation
```

## Deployment

Build and deploy the component:

```bash
# Build component package
koios-component build examples/smart_instrumentation

# Deploy to Koios server
koios-component deploy promass_promag_component-1.0.0.kcp --host https://koios.example.com
```

## Limitations

- Requires EtherNet/IP enabled device
- Assembly instance numbers must match device configuration
- Assembly data structure must match device output format
- Network connectivity required for device communication
- Device must support CIP explicit messaging

## Related Components

- [Logix Protocol Component](../logix_protocol/README.md) - Allen-Bradley PLC communication
- [Selector Component](../selector/README.md) - Signal routing and selection

## References

- [Endress+Hauser Documentation](https://www.endress.com/)
- [EtherNet/IP Specification](https://www.odva.org/technology-standards/ethernet-ip/)
- [CIP Specification](https://www.odva.org/technology-standards/cip/)

## License

Copyright 2025 Koios Component SDK Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Support

For issues, questions, or contributions, please visit:
- [Koios Component SDK Documentation](https://docs.ai-op.com/components)
- [GitHub Issues](https://github.com/ai-op/koios-component-sdk/issues)

