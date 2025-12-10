# Implementation Comparison: Datacollector vs. Component

This document compares the Logix protocol implementation in the datacollector (`libdc_schema_logix.py`) with the component-based implementation (`component.py`).

## Architecture Comparison

### Datacollector (Schema-Based)

```
DeviceSchema (Base)
└── LogixDeviceSchema
    ├── LogixTagSchema (for each tag)
    └── LogixDriver (pycomm3 client)

Integration: Database-driven, service-managed
Lifecycle: Managed by libdc_service.py
Configuration: PostgreSQL database
```

### Component (SDK-Based)

```
BaseKoiosComponent
└── ProtocolComponent (Base)
    └── LogixProtocolComponent
        ├── LogixTagConfig (for each tag)
        └── LogixDriver (pycomm3 client)

Integration: Component framework
Lifecycle: Component lifecycle (initialize/start/stop)
Configuration: JSON parameters
```

## Key Differences

### 1. Configuration Management

**Datacollector:**
```python
# Database-driven configuration
class LogixDeviceSchema(DeviceSchema):
    ethernet_ip_controller_slot: int
    ethernet_ip_hostname: str | None
    ethernet_ip_type: int
    ethernet_ip_timeout: int
    
    config_fields: list[str] = [
        "ethernet_ip_controller_slot",
        "ethernet_ip_hostname",
        "ethernet_ip_type",
        "ethernet_ip_timeout",
    ]
```

**Component:**
```python
# Parameter-driven configuration
@property
def parameter_definitions(self) -> List[ParameterDefinition]:
    return [
        ParameterDefinition(
            name="host",
            type="string",
            description="PLC hostname or IP address",
            required=True,
            default="192.168.1.1"
        ),
        # ... more definitions
    ]
```

**Why the difference:**
- Datacollector needs database integration for multi-device management
- Component uses declarative parameters for flexibility and validation
- Component approach is more portable and easier to test

### 2. Tag Management

**Datacollector:**
```python
class LogixTagSchema(TagSchema):
    # DB Fields
    ethernet_ip_logix_tagname: str | None
    ethernet_ip_logix_tag_type: int
    
    # Extra
    ethernet_ip_logix_output_value: int | float | bool | None = None
    
    def validate_read_config(self):
        """Validate read config for Logix tags"""
        if super().validate_read_config():
            if not self.ethernet_ip_logix_tagname:
                raise TagException("Logix tagname required")
            self.valid_read_config = True
```

**Component:**
```python
class LogixTagConfig:
    """Configuration for a Logix tag."""
    
    def __init__(self, name: str, address: str, data_type: int, writable: bool = False):
        self.name = name
        self.address = address
        self.data_type = data_type
        self.writable = writable
        self.value: Optional[Any] = None
        self.quality: str = "Unknown"
        self.timestamp: Optional[datetime] = None
        self.error: Optional[str] = None
    
    def convert_value(self, value: Any) -> Any:
        """Convert value to appropriate data type."""
        # Conversion logic
```

**Why the difference:**
- Datacollector tags are database records with full ORM support
- Component tags are lightweight in-memory objects
- Component approach is simpler for standalone operation
- Datacollector approach is better for persistence and audit trails

### 3. Connection Management

**Datacollector:**
```python
def connect(self):
    """Connect to device"""
    logger.debug("Building Logix client object - device_id: %s", self.id)
    
    # Check if configuration has changed
    if self.client is not None and self.config_changed():
        logger.debug("Configuration change detected, closing old connection")
        self.client.close()
        self.client = None
    
    if self.client is None:
        self.client = self.get_logix_client()
    
    if not self.client.connected:
        raise DeviceException("Client is not connected")
```

**Component:**
```python
async def connect_async(self) -> bool:
    """Establish connection to Logix PLC asynchronously."""
    try:
        logger.info(f"Connecting to Logix PLC at {self.connection_path}")
        
        if self._client is None:
            self._client = self._build_client()
        
        result = await asyncio.to_thread(self._client.open)
        
        if result:
            self._connected = True
            self._connection_time = time.time()
            return True
        return False
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        self._client = None
        return False
```

**Why the difference:**
- Datacollector uses synchronous operations (service runs in thread)
- Component uses async/await for better concurrency
- Component approach is more modern and scalable
- Datacollector approach is simpler for existing architecture

### 4. Read Operations

**Datacollector:**
```python
def read_from_device(self, read_id_list: list[int] | None = None):
    """Read tags from device"""
    read_tag_list = super().read_from_device(read_id_list)
    
    if not read_tag_list:
        return
    
    _tagname_list = [tag.ethernet_ip_logix_tagname for tag in read_tag_list]
    _koios_ts = datetime.now(timezone.utc)
    
    # Read from client
    _read_results = self.client.read(*_tagname_list)
    
    # If single result, convert to list
    if isinstance(_read_results, LogixTag):
        _read_results = [_read_results]
    
    # Process results
    for tag in read_tag_list:
        if tag.ethernet_ip_logix_tagname in _tagname_list:
            _result_index = _tagname_list.index(tag.ethernet_ip_logix_tagname)
            _result = _read_results[_result_index]
            
            if _result.error is not None:
                raise TagException(_result.error)
            
            tag.assign_value(value=_result.value, ts=_koios_ts)
```

**Component:**
```python
async def read_tags_batch_async(self, tag_addresses: List[str]) -> Dict[str, Any]:
    """Read multiple tags in a batch operation."""
    if not self._client or not self._connected:
        raise ConnectionError("Not connected")
    
    results = {}
    
    try:
        # Read all tags at once
        read_results = await asyncio.to_thread(self._client.read, *tag_addresses)
        
        # Handle single or multiple results
        if isinstance(read_results, LogixTag):
            read_results = [read_results]
        
        # Process results
        for i, address in enumerate(tag_addresses):
            result = read_results[i]
            
            if result.error is not None:
                logger.warning(f"Error reading {address}: {result.error}")
                results[address] = None
            else:
                results[address] = result.value
        
        return results
    except Exception as e:
        logger.error(f"Batch read failed: {e}")
        raise
```

**Why the difference:**
- Datacollector integrates with database timestamp and status tracking
- Component returns dictionary for simpler API
- Component uses async for non-blocking I/O
- Both handle batch operations similarly
- Component has more explicit error handling per tag

### 5. Write Operations

**Datacollector:**
```python
def write_to_device(self, write_id_list: list[int] | None = None):
    """Write tags to device"""
    write_tag_list = super().write_to_device(write_id_list)
    
    if not write_tag_list:
        return
    
    _tagname_list = [tag.ethernet_ip_logix_tagname for tag in write_tag_list]
    _value_list = [
        (tag.ethernet_ip_logix_tagname, tag.ethernet_ip_logix_output_value)
        for tag in write_tag_list
    ]
    
    # Write to device
    _write_results = self.client.write(*_value_list)
    
    # Handle single or multiple results
    if isinstance(_write_results, LogixTag):
        _write_results = [_write_results]
    
    # Process results
    for tag in write_tag_list:
        if tag.ethernet_ip_logix_tagname in _tagname_list:
            _result_index = _tagname_list.index(tag.ethernet_ip_logix_tagname)
            _result = _write_results[_result_index]
            
            if _result.error is not None:
                raise TagException(_result.error)
            
            tag.post_write()
```

**Component:**
```python
async def write_tags_batch_async(self, tag_values: Dict[str, Any]) -> Dict[str, bool]:
    """Write multiple tags in a batch operation."""
    if not self._client or not self._connected:
        raise ConnectionError("Not connected")
    
    results = {}
    
    try:
        # Prepare write list as tuples
        write_list = [(addr, val) for addr, val in tag_values.items()]
        
        # Write all tags at once
        write_results = await asyncio.to_thread(self._client.write, *write_list)
        
        # Handle single or multiple results
        if isinstance(write_results, LogixTag):
            write_results = [write_results]
        
        # Process results
        addresses = list(tag_values.keys())
        for i, address in enumerate(addresses):
            result = write_results[i]
            
            if result.error is not None:
                logger.warning(f"Error writing {address}: {result.error}")
                results[address] = False
            else:
                results[address] = True
        
        return results
    except Exception as e:
        logger.error(f"Batch write failed: {e}")
        raise
```

**Why the difference:**
- Datacollector handles write request flags and timing
- Component returns success/failure per tag
- Both use similar pycomm3 API patterns
- Component approach is more functional (input/output focused)

### 6. Error Handling

**Datacollector:**
```python
except Exception as e:
    traceback.print_exc()
    
    tag.value = None
    tag.quality = "Bad"
    tag.timestamp = _koios_ts
    tag.set_status(Status.FAILED)
    tag.error_code = TagErrorCode.BAD_READ_FAIL
    tag.error_message = "Failed to read"
    tag.error_detail = str(e)
    
    if "Tag doesn't exist" in tag.error_detail:
        tag.info_message = (
            "If this is a new tag or the tagname/datatype has been modified,"
            + " try refreshing the device connection..."
        )
```

**Component:**
```python
except Exception as e:
    tag_config.quality = "Bad"
    tag_config.error = str(e)
    self._failed_reads += 1
    
    logger.error(f"Failed to read tag {tag_name}: {e}")
```

**Why the difference:**
- Datacollector has detailed error codes and messages for UI display
- Datacollector provides helpful troubleshooting messages
- Component has simpler error tracking focused on statistics
- Datacollector approach is better for end-user diagnostics
- Component approach is simpler for programmatic access

## Statistics and Monitoring

**Datacollector:**
```python
# Built into device lifecycle
def toggle_heartbeat(self):
    """Toggles a heartbeat parameter"""
    if self.system_ok:
        self.heartbeat_scan_count += 1
        if self.heartbeat_scan_count >= self.heartbeat_scans:
            self.heartbeat = 0 if self.heartbeat == 1 else 1
            self.heartbeat_scan_count = 0

# Stored in database
def write_device_status_to_db(self):
    """Write device status to the database"""
    with db_manager.get_session() as session:
        session.execute(update(Device), _device_data)
        session.commit()
```

**Component:**
```python
# Explicit statistics tracking
def get_statistics(self) -> Dict[str, Any]:
    """Get protocol statistics."""
    return {
        'connection': {
            'connected': self._connected,
            'connection_path': self.connection_path,
            'connection_time': self._connection_time
        },
        'reads': {
            'successful': self._successful_reads,
            'failed': self._failed_reads,
            'last_duration': self._last_read_time
        },
        'writes': {
            'successful': self._successful_writes,
            'failed': self._failed_writes,
            'last_duration': self._last_write_time
        }
    }

# Health checks
async def health_check_async(self) -> Dict[str, Any]:
    """Check connection health asynchronously."""
    # Health check implementation
```

**Why the difference:**
- Datacollector persists all state to database
- Component keeps statistics in memory
- Component has explicit health check API
- Datacollector approach better for long-term monitoring
- Component approach better for real-time diagnostics

## Lifecycle Management

**Datacollector:**
```python
# Managed by CollectionEngine thread
class CollectionThread(Thread):
    def run(self):
        """Perform all device actions"""
        try:
            self.device.update_from_db()
            self.device.initialize_status()
            self.device.build_tags_from_db()
            self.device.connect()
            self.device.validate_tag_config()
            self.device.read_from_device()
            self.device.write_to_device()
            self.device.write_history_to_influx()
            self.device.toggle_heartbeat()
        except Exception:
            self.device.set_status(Status.FAILED)
```

**Component:**
```python
# Component lifecycle methods
def initialize(self) -> bool:
    """Initialize the protocol."""
    self._set_status(ComponentStatus.INITIALIZING)
    # Setup code
    self._set_status(ComponentStatus.INITIALIZED)
    return True

def start(self) -> bool:
    """Start the protocol."""
    self._set_status(ComponentStatus.STARTING)
    if not self.connect():
        raise ConnectionError(...)
    self._set_status(ComponentStatus.RUNNING)
    return True

def stop(self) -> bool:
    """Stop the protocol."""
    self._set_status(ComponentStatus.STOPPING)
    self.disconnect()
    self._set_status(ComponentStatus.STOPPED)
    return True

def execute(self) -> Dict[str, Any]:
    """Execute protocol maintenance tasks."""
    # Periodic operations
    return {"success": True, ...}
```

**Why the difference:**
- Datacollector lifecycle is service-managed with threads
- Component lifecycle is explicit and state-based
- Component approach allows for easier testing
- Datacollector approach integrates with database lifecycle
- Component approach is more portable

## Integration Points

**Datacollector:**
- Database integration (PostgreSQL)
- InfluxDB for time-series data
- Event system for UI notifications
- Service thread management
- Configuration from DB

**Component:**
- Koios tag binding
- Component framework integration
- Parameter-based configuration
- Independent lifecycle
- Programmatic API

## Use Cases

**Datacollector Best For:**
- Multi-device management
- Persistent configuration
- Historical data storage
- System-wide monitoring
- Enterprise deployments

**Component Best For:**
- Embedded in applications
- Programmatic control
- Testing and development
- Portable solutions
- Custom integrations

## Performance Considerations

**Datacollector:**
- Thread-per-device model
- Database queries on each scan
- InfluxDB writes with compression
- Batch operations for efficiency
- Configuration change detection

**Component:**
- Async/await for concurrency
- In-memory state
- No database overhead
- Batch operations supported
- Parameter-based configuration

## Summary

| Aspect | Datacollector | Component |
|--------|--------------|-----------|
| **Architecture** | Schema-based, database-driven | Parameter-based, standalone |
| **Configuration** | PostgreSQL database | JSON parameters |
| **Lifecycle** | Service-managed threads | Explicit initialize/start/stop |
| **Async** | Synchronous (in threads) | Async/await |
| **State** | Database-persisted | In-memory |
| **Statistics** | Database + heartbeat | In-memory metrics |
| **Error Handling** | Detailed codes + UI messages | Simple error tracking |
| **Use Case** | Enterprise system | Portable component |
| **Complexity** | Higher (full system) | Lower (focused) |
| **Testing** | Requires database | Self-contained |

## Conclusion

Both implementations serve their purposes well:

- **Datacollector** is ideal for the full Koios system with database integration, multi-device management, and enterprise features
- **Component** is perfect for portable, reusable communication modules that can be embedded in various applications

The component approach demonstrates how to build communication components that:
- Are self-contained and testable
- Have clear lifecycle management
- Use modern async patterns
- Provide simple APIs
- Are easily portable

This makes components ideal for:
- Custom applications
- Third-party integrations
- Testing and development
- Embedded solutions
- Library-like usage

