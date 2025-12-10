# Logix Protocol Communication Component

This example demonstrates how to create a communication protocol component using the Koios Component SDK. It implements support for Allen-Bradley Logix PLCs using the EtherNet/IP protocol, mirroring the functionality from the Koios datacollector.

## Overview

The Logix Protocol Component provides a complete implementation of a communication protocol component for connecting to Allen-Bradley PLCs (ControlLogix, CompactLogix, Micro800, etc.) using EtherNet/IP. This example shows how protocol components differ from control or logic components and how to properly structure communication drivers.

## Features

### Core Communication Features
- **EtherNet/IP Protocol Support**: Native support for Allen-Bradley PLCs
- **Connection Management**: Automatic connection/disconnection with error handling
- **Tag Operations**: Single and batch read/write operations
- **Data Type Support**: INTEGER, REAL, and BOOLEAN data types
- **Auto-Reconnection**: Configurable automatic reconnection on connection loss
- **Health Monitoring**: Periodic health checks and diagnostics

### Advanced Features
- **Batch Operations**: Efficient multi-tag reading and writing
- **Connection Statistics**: Detailed read/write statistics and timing
- **Error Handling**: Comprehensive error detection and reporting
- **Tag Configuration**: Flexible tag definition via JSON configuration
- **Quality Tracking**: Tag quality and timestamp tracking
- **Retry Logic**: Configurable retry attempts with delays

## Architecture

### Component Structure

```
LogixProtocolComponent (extends ProtocolComponent)
├── Connection Management
│   ├── connect_async()
│   ├── disconnect_async()
│   └── health_check_async()
├── Tag Operations
│   ├── read_tag_async()
│   ├── write_tag_async()
│   ├── read_tags_batch_async()
│   └── write_tags_batch_async()
├── Tag Management
│   ├── LogixTagConfig
│   └── Tag definitions
└── Statistics & Monitoring
    ├── Connection stats
    ├── Read/Write counts
    └── Error tracking
```

### Key Differences from Control Components

Unlike control components (like PID controllers), protocol components:

1. **Focus on Communication**: Handle external device communication rather than calculations
2. **Async Operations**: Heavily use async/await for non-blocking I/O
3. **Connection Lifecycle**: Manage connection state and health
4. **Batch Processing**: Optimize network communication with batch operations
5. **Error Resilience**: Handle network errors and implement retry logic

## Installation

### Prerequisites

The component requires the `pycomm3` library for EtherNet/IP communication:

```bash
pip install pycomm3>=1.2.14
```

### Component Installation

```bash
# Build the component
koios-component build ./examples/logix_protocol

# Deploy to Koios server
koios-component deploy logix_protocol-1.0.0.kcp --host https://koios.example.com
```

## Configuration

### Basic Configuration

```python
from component import LogixProtocolComponent, LogixDataType

# Minimal configuration
config = {
    "host": "192.168.1.100",
    "controller_slot": 0,
    "tags": [
        {
            "name": "temperature",
            "address": "Temperature_PV",
            "data_type": LogixDataType.REAL,
            "writable": False
        }
    ]
}

component = LogixProtocolComponent("logix_01", config)
```

### Advanced Configuration

```python
# Full configuration with all options
config = {
    # Connection parameters
    "host": "192.168.1.100",
    "controller_slot": 0,
    "timeout": 5.0,
    "retry_count": 3,
    "retry_delay": 1.0,
    
    # Protocol-specific settings
    "enable_auto_reconnect": True,
    "read_batch_size": 20,
    "write_batch_size": 20,
    "health_check_interval": 30.0,
    
    # Tag definitions
    "tags": [
        {
            "name": "temperature",
            "address": "Temperature_PV",
            "data_type": LogixDataType.REAL,
            "writable": False
        },
        {
            "name": "setpoint",
            "address": "Temperature_SP",
            "data_type": LogixDataType.REAL,
            "writable": True
        },
        {
            "name": "pump_running",
            "address": "Pump_01_Running",
            "data_type": LogixDataType.BOOLEAN,
            "writable": False
        },
        {
            "name": "valve_position",
            "address": "Valve_01_Position",
            "data_type": LogixDataType.INTEGER,
            "writable": True
        }
    ]
}
```

## Usage Examples

### Example 1: Basic Connection and Reading

```python
import logging
from component import LogixProtocolComponent, LogixDataType

# Set up logging
logging.basicConfig(level=logging.INFO)

# Configuration
config = {
    "host": "192.168.1.100",
    "controller_slot": 0,
    "tags": [
        {
            "name": "temperature",
            "address": "Temperature_PV",
            "data_type": LogixDataType.REAL,
            "writable": False
        }
    ]
}

# Create and initialize component
component = LogixProtocolComponent("logix_01", config)

if component.initialize():
    if component.start():
        # Read all tags
        values = component.read_all_tags()
        print(f"Temperature: {values['temperature']}")
        
        # Get detailed tag info
        tag_info = component.get_tag_info("temperature")
        print(f"Quality: {tag_info['quality']}")
        print(f"Timestamp: {tag_info['timestamp']}")
        
        component.stop()
```

### Example 2: Writing Tags

```python
# ... (initialization code) ...

if component.initialize() and component.start():
    # Write single value
    success = component.write_tags({
        "setpoint": 75.5
    })
    
    if success:
        print("Setpoint updated successfully")
    
    # Write multiple values
    success = component.write_tags({
        "setpoint": 80.0,
        "valve_position": 65
    })
    
    component.stop()
```

### Example 3: Monitoring and Statistics

```python
# ... (initialization code) ...

if component.initialize() and component.start():
    # Perform operations
    component.read_all_tags()
    component.write_tags({"setpoint": 75.0})
    
    # Check health
    health = component.health_check()
    print(f"Health Status: {health['status']}")
    print(f"Message: {health['message']}")
    
    # Get statistics
    stats = component.get_statistics()
    print(f"Connection: {stats['connection']}")
    print(f"Reads: {stats['reads']['successful']}/{stats['reads']['failed']}")
    print(f"Writes: {stats['writes']['successful']}/{stats['writes']['failed']}")
    
    component.stop()
```

### Example 4: Integration with Koios Tags

```python
# In a Koios application, the component automatically binds to tags:

# The component exposes bindable fields:
# - connected (bool): Connection status
# - read_count (int): Total successful reads
# - write_count (int): Total successful writes
# - error_count (int): Total errors
# - health_status (str): Current health status
# - temperature_value: Current temperature value
# - temperature_quality: Temperature quality
# - temperature_timestamp: Last update time

# These can be bound to Koios tags for monitoring and control
```

## Configuration Parameters

### Connection Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | string | "192.168.1.1" | PLC IP address or hostname |
| `controller_slot` | integer | 0 | Controller slot number (0-16) |
| `timeout` | float | 5.0 | Communication timeout in seconds |
| `retry_count` | integer | 3 | Number of retry attempts |
| `retry_delay` | float | 1.0 | Delay between retries in seconds |

### Protocol Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_auto_reconnect` | boolean | true | Enable automatic reconnection |
| `read_batch_size` | integer | 20 | Max tags per read batch |
| `write_batch_size` | integer | 20 | Max tags per write batch |
| `health_check_interval` | float | 30.0 | Health check interval in seconds |

### Tag Configuration

Each tag in the `tags` array requires:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique tag name |
| `address` | string | Yes | PLC tag address |
| `data_type` | integer | No | 1=INTEGER, 2=REAL, 3=BOOLEAN (default: 2) |
| `writable` | boolean | No | Whether tag can be written (default: false) |

## Data Types

The component supports three Logix data types:

```python
class LogixDataType:
    INTEGER = 1  # DINT (32-bit signed integer)
    REAL = 2     # REAL (32-bit float)
    BOOLEAN = 3  # BOOL (boolean)
```

## Comparison with Datacollector Implementation

This component mirrors the datacollector's Logix implementation from `libdc_schema_logix.py`:

### Similarities
- Uses `pycomm3` library for EtherNet/IP communication
- Supports same data types (INTEGER, REAL, BOOLEAN)
- Implements batch read/write operations
- Provides connection management and error handling
- Tracks tag status and quality

### Differences
- **Architecture**: Component-based vs. schema-based
- **Lifecycle**: Uses component lifecycle (initialize/start/stop)
- **Async Operations**: Explicit async methods for better concurrency
- **Integration**: Direct Koios tag binding support
- **Configurability**: JSON-based configuration vs. database schema
- **Monitoring**: Built-in statistics and health checks

### Key Datacollector Concepts Implemented

1. **DeviceSchema Connection Management**
   - `connect()` method for establishing connections
   - `disconnect()` for cleanup
   - `device_failure()` for error handling

2. **TagSchema Value Handling**
   - `assign_value()` for tag value assignment
   - `validate_read_config()` and `validate_write_config()`
   - Quality tracking (Good/Bad)

3. **Batch Operations**
   - `read_from_device()` with batch processing
   - `write_to_device()` with batch processing
   - Efficient network utilization

## Best Practices

### 1. Tag Organization
```python
# Group related tags logically
tags = [
    # Temperature loop
    {"name": "temp_pv", "address": "Temperature_PV", ...},
    {"name": "temp_sp", "address": "Temperature_SP", ...},
    
    # Pressure loop
    {"name": "press_pv", "address": "Pressure_PV", ...},
    {"name": "press_sp", "address": "Pressure_SP", ...},
]
```

### 2. Error Handling
```python
try:
    if component.initialize() and component.start():
        values = component.read_all_tags()
        # Process values...
except Exception as e:
    logger.error(f"Component error: {e}")
finally:
    component.stop()
```

### 3. Health Monitoring
```python
# Implement periodic health checks
import time

while running:
    health = component.health_check()
    if health['status'] != 'healthy':
        logger.warning(f"Health check failed: {health['message']}")
    
    time.sleep(30)  # Check every 30 seconds
```

### 4. Batch Operations
```python
# Prefer batch operations over individual reads/writes
# Good: One batch read
values = component.read_all_tags()

# Less efficient: Multiple individual reads
for tag_name in tag_names:
    value = component.read_tag(tag_name)
```

## Testing

### Unit Tests

```bash
# Run component tests
koios-component test ./examples/logix_protocol

# Test specific scenario
koios-component test ./examples/logix_protocol --scenario connection
```

### Integration Testing

For integration testing with a real PLC:

1. Update configuration with PLC IP address
2. Ensure PLC is accessible on the network
3. Verify tag addresses exist in PLC
4. Run the example script:

```bash
python component.py
```

### Mock Testing

For testing without a PLC, implement a mock server or use pycomm3's simulation capabilities.

## Troubleshooting

### Common Issues

#### 1. Connection Timeout
**Problem**: Cannot connect to PLC

**Solutions**:
- Verify PLC IP address and slot number
- Check network connectivity (`ping <PLC_IP>`)
- Ensure firewall allows EtherNet/IP traffic (port 44818)
- Verify PLC is in Run mode

#### 2. Tag Not Found
**Problem**: "Tag doesn't exist" error

**Solutions**:
- Verify tag address matches PLC tag name exactly (case-sensitive)
- Check tag scope (controller-scoped vs. program-scoped)
- Use correct tag path (e.g., "Program:MainProgram.TagName")

#### 3. Data Type Mismatch
**Problem**: Value conversion errors

**Solutions**:
- Verify data_type matches PLC tag type
- Use INTEGER for DINT, REAL for REAL, BOOLEAN for BOOL
- Check for array vs. scalar tags

#### 4. Write Failures
**Problem**: Cannot write to tag

**Solutions**:
- Ensure tag is marked as `writable: true`
- Verify PLC is in Run mode (Remote Run for online writes)
- Check tag is not read-only in PLC

### Diagnostic Commands

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed statistics
stats = component.get_statistics()
print(json.dumps(stats, indent=2))

# Check individual tag status
for tag_name in component._tags.keys():
    info = component.get_tag_info(tag_name)
    print(f"{tag_name}: {info}")
```

## Performance Considerations

### Batch Size Tuning
- **Small batches (1-10)**: Better for real-time updates, more network overhead
- **Medium batches (10-30)**: Good balance for most applications
- **Large batches (30-100)**: Better throughput, higher latency

### Network Optimization
- Use batch operations whenever possible
- Adjust timeout based on network latency
- Consider health check interval for your application

### Memory Usage
- Each tag stores value, quality, timestamp, and error
- Monitor memory with many tags (100+)
- Consider tag cleanup for dynamic configurations

## Advanced Topics

### Custom Data Types

Extend the component to support additional Logix data types:

```python
class LogixDataType:
    INTEGER = 1
    REAL = 2
    BOOLEAN = 3
    STRING = 4    # Add STRING support
    DINT = 5      # Explicit DINT
    LINT = 6      # Long integer
```

### Tag Discovery

Implement automatic tag discovery from PLC:

```python
async def discover_tags_async(self):
    """Discover available tags from PLC."""
    if self._client and self._connected:
        tags = await asyncio.to_thread(self._client.get_tag_list)
        return tags
```

### Connection Pooling

For multiple PLCs, implement connection pooling:

```python
class LogixConnectionPool:
    def __init__(self, max_connections=10):
        self._pool = []
        self._max_connections = max_connections
    
    def get_connection(self, host, slot):
        # Connection pool implementation
        pass
```

## Related Examples

- [PID Controller Component](../pid_controller/README.md) - Control component example
- [Modbus Protocol](../modbus_protocol/README.md) - Similar protocol component
- [OPC UA Protocol](../opcua_protocol/README.md) - Another industrial protocol

## References

- [pycomm3 Documentation](https://github.com/ottowayi/pycomm3)
- [EtherNet/IP Specification](https://www.odva.org/technology-standards/key-technologies/ethernet-ip/)
- [Koios Component SDK Documentation](https://docs.ai-op.com/component-sdk/)
- [Allen-Bradley Logix Documentation](https://www.rockwellautomation.com/)

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- GitHub Issues: [koios-component-sdk/issues](https://github.com/ai-op/koios-component-sdk/issues)
- Documentation: [docs.ai-op.com](https://docs.ai-op.com)
- Email: support@ai-op.com

