# Quick Start Guide - Logix Protocol Component

Get up and running with the Logix Protocol Component in 5 minutes!

## Prerequisites

1. Python 3.9 or higher
2. Allen-Bradley Logix PLC accessible on network
3. Basic understanding of PLC tags

## Step 1: Install Dependencies

```bash
pip install pycomm3>=1.2.14
```

## Step 2: Configure Your PLC Connection

Edit `basic_usage.py` and update the configuration:

```python
config = {
    "host": "192.168.1.100",      # ← Change to your PLC IP
    "controller_slot": 0,          # ← Usually 0 for ControlLogix
    "timeout": 5.0,
    "tags": [
        {
            "name": "temperature",
            "address": "Temperature_PV",    # ← Change to your tag name
            "data_type": LogixDataType.REAL,
            "writable": False
        }
    ]
}
```

## Step 3: Test Connection

Run the basic example:

```bash
python basic_usage.py
```

You should see:
```
✓ Component initialized
✓ Component started and connected
Reading tags...
  temperature         :      72.45 (Quality: Good)
✓ Component stopped
```

## Common Configuration

### Finding Your PLC Settings

**IP Address:**
- Check your PLC's Ethernet module configuration
- Use RSLinx or Studio 5000 to discover devices
- Common ranges: 192.168.1.x or 10.x.x.x

**Controller Slot:**
- Usually `0` for ControlLogix in slot 0
- Check your chassis configuration if unsure

**Tag Addresses:**
- Use exact tag names from PLC (case-sensitive)
- For program-scoped tags: `Program:MainProgram.TagName`
- For controller-scoped tags: `TagName`

### Data Types

```python
LogixDataType.INTEGER  # DINT (32-bit integer)
LogixDataType.REAL     # REAL (32-bit float)
LogixDataType.BOOLEAN  # BOOL (boolean)
```

## Quick Test Without PLC

If you don't have a PLC available, you can still explore the code:

```python
# The component will fail to connect, but you can examine:
component = LogixProtocolComponent("test", config)
print(component.metadata)
print(component.parameter_definitions)
print(component.get_bindable_fields())
```

## Example Configurations

### Temperature Control Loop

```python
config = {
    "host": "192.168.1.100",
    "controller_slot": 0,
    "tags": [
        {
            "name": "temp_pv",
            "address": "Temperature_PV",
            "data_type": LogixDataType.REAL,
            "writable": False
        },
        {
            "name": "temp_sp",
            "address": "Temperature_SP",
            "data_type": LogixDataType.REAL,
            "writable": True
        },
        {
            "name": "heater_output",
            "address": "Heater_Output",
            "data_type": LogixDataType.REAL,
            "writable": True
        }
    ]
}
```

### Digital I/O Monitoring

```python
config = {
    "host": "192.168.1.100",
    "controller_slot": 0,
    "tags": [
        {
            "name": "pump_01",
            "address": "Pump_01_Running",
            "data_type": LogixDataType.BOOLEAN,
            "writable": False
        },
        {
            "name": "valve_01",
            "address": "Valve_01_Open",
            "data_type": LogixDataType.BOOLEAN,
            "writable": False
        },
        {
            "name": "alarm",
            "address": "System_Alarm",
            "data_type": LogixDataType.BOOLEAN,
            "writable": False
        }
    ]
}
```

### Batch Data Collection

```python
config = {
    "host": "192.168.1.100",
    "controller_slot": 0,
    "read_batch_size": 50,  # Read 50 tags at once
    "tags": [
        {
            "name": f"sensor_{i:02d}",
            "address": f"SensorArray[{i}]",
            "data_type": LogixDataType.REAL,
            "writable": False
        }
        for i in range(50)
    ]
}
```

## Minimal Working Example

```python
from component import LogixProtocolComponent, LogixDataType

# Configure
config = {
    "host": "192.168.1.100",
    "controller_slot": 0,
    "tags": [
        {
            "name": "my_tag",
            "address": "MyTagName",
            "data_type": LogixDataType.REAL,
            "writable": False
        }
    ]
}

# Create component
component = LogixProtocolComponent("test", config)

# Initialize and start
if component.initialize() and component.start():
    # Read tags
    values = component.read_all_tags()
    print(f"Tag value: {values['my_tag']}")
    
    # Stop
    component.stop()
```

## Troubleshooting

### Cannot Connect

**Error:** `Connection failed: timeout`

**Solutions:**
1. Verify PLC IP address: `ping 192.168.1.100`
2. Check firewall settings (allow port 44818)
3. Verify controller slot number
4. Ensure PLC is powered on and in Run mode

### Tag Not Found

**Error:** `Tag doesn't exist`

**Solutions:**
1. Check tag name spelling (case-sensitive)
2. Verify tag scope (controller vs. program)
3. Use correct syntax for program-scoped tags
4. Check tag exists in PLC using Studio 5000

### Data Type Mismatch

**Error:** `Type mismatch` or `Cannot convert value`

**Solutions:**
1. Use INTEGER for DINT tags
2. Use REAL for REAL tags
3. Use BOOLEAN for BOOL tags
4. Check PLC tag data type in Studio 5000

### Write Fails

**Error:** `Write failed` or `Tag not writable`

**Solutions:**
1. Set `writable: True` in tag configuration
2. Verify PLC is in Run or Remote Run mode
3. Check tag is not read-only in PLC
4. Verify user has write permissions

## Next Steps

Once you have basic communication working:

1. **Read the Full README**
   - `README.md` - Comprehensive documentation

2. **Try Batch Operations**
   - `batch_operations.py` - Efficient multi-tag operations

3. **Study the Implementation**
   - `component.py` - Full source code
   - `IMPLEMENTATION_COMPARISON.md` - Learn from datacollector

4. **Build Your Own**
   - Use this as a template for other protocols
   - Customize for your specific needs

## Common Use Patterns

### Read-Only Monitoring

```python
# Read tags periodically
while True:
    values = component.read_all_tags()
    print(f"Temperature: {values['temperature']:.2f}")
    time.sleep(1)
```

### Write Control Values

```python
# Update setpoint
component.write_tags({
    "setpoint": 75.0
})

# Verify write
time.sleep(0.1)
values = component.read_all_tags()
print(f"New setpoint: {values['setpoint']}")
```

### Error Handling

```python
try:
    if component.initialize() and component.start():
        values = component.read_all_tags()
        # Process values...
except Exception as e:
    print(f"Error: {e}")
finally:
    component.stop()
```

### Health Monitoring

```python
# Check connection health
health = component.health_check()
if health['status'] == 'healthy':
    print("Connection OK")
else:
    print(f"Problem: {health['message']}")
```

## Tips for Success

1. **Start Simple**
   - Begin with one or two tags
   - Verify communication works
   - Then add more tags

2. **Test Incrementally**
   - Test reading before writing
   - Verify each tag individually
   - Use batch operations for efficiency

3. **Monitor Statistics**
   - Check read/write counts
   - Watch for errors
   - Use health checks

4. **Handle Errors Gracefully**
   - Always use try/except
   - Clean up with finally
   - Log errors for debugging

5. **Optimize Performance**
   - Use batch operations
   - Adjust batch sizes
   - Tune timeout values

## Getting Help

- **Detailed docs:** See `README.md`
- **Examples:** Run `basic_usage.py` and `batch_operations.py`
- **Comparison:** Read `IMPLEMENTATION_COMPARISON.md`
- **Issues:** Check troubleshooting section above

## Summary

You're now ready to use the Logix Protocol Component! Remember:

✅ Install `pycomm3`  
✅ Configure your PLC IP and tags  
✅ Test with `basic_usage.py`  
✅ Check troubleshooting if issues  
✅ Read full README for advanced features  

Happy coding! 🚀

