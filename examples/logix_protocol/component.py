"""
Logix Protocol Communication Component

This example demonstrates how to create a communication protocol component
using the Koios Component SDK. It mimics the Logix (Allen-Bradley) EtherNet/IP
protocol implementation from the datacollector.
"""

from typing import Dict, Any, List, Optional
import asyncio
import time
from datetime import datetime, timezone

from koios_component_sdk.base import ProtocolComponent
from koios_component_sdk.base.component import ComponentMetadata, ParameterDefinition, ComponentCategory
from koios_component_sdk.decorators import validate_parameters, on_start, on_stop
from koios_component_sdk.exceptions import ConnectionError, ValidationError

try:
    from pycomm3 import LogixDriver
    from pycomm3.tag import Tag as LogixTag
    PYCOMM3_AVAILABLE = True
except ImportError:
    PYCOMM3_AVAILABLE = False
    LogixDriver = None
    LogixTag = None


class LogixDataType:
    """Logix data type enumeration."""
    INTEGER = 1
    REAL = 2
    BOOLEAN = 3


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
        if self.data_type == LogixDataType.INTEGER:
            return int(value)
        elif self.data_type == LogixDataType.REAL:
            return float(value)
        elif self.data_type == LogixDataType.BOOLEAN:
            return bool(value)
        else:
            raise ValueError(f"Unsupported data type: {self.data_type}")


class LogixProtocolComponent(ProtocolComponent):
    """
    Logix (Allen-Bradley) EtherNet/IP Protocol Component.
    
    This component provides communication with Allen-Bradley PLCs using
    the EtherNet/IP protocol. It supports reading and writing tags,
    batch operations, and connection management.
    
    Features:
    - Connection to Logix PLCs via EtherNet/IP
    - Tag reading (single and batch)
    - Tag writing (single and batch)
    - Automatic reconnection on failure
    - Health monitoring and diagnostics
    - Support for INTEGER, REAL, and BOOLEAN data types
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        """Initialize the Logix protocol component."""
        super().__init__(component_id, parameters)
        
        # Logix-specific parameters
        self._controller_slot = parameters.get('controller_slot', 0)
        self._enable_auto_reconnect = parameters.get('enable_auto_reconnect', True)
        self._read_batch_size = parameters.get('read_batch_size', 20)
        self._write_batch_size = parameters.get('write_batch_size', 20)
        
        # Client and tag management
        self._client: Optional[LogixDriver] = None
        self._tags: Dict[str, LogixTagConfig] = {}
        self._tag_definitions: List[Dict[str, Any]] = parameters.get('tags', [])
        
        # Statistics
        self._successful_reads = 0
        self._failed_reads = 0
        self._successful_writes = 0
        self._failed_writes = 0
        self._last_read_time: Optional[float] = None
        self._last_write_time: Optional[float] = None
        
        # Check if pycomm3 is available
        if not PYCOMM3_AVAILABLE:
            self.logger.error("pycomm3 library is not installed. Install with: pip install pycomm3")
    
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="Logix Protocol Component",
            version="1.0.0",
            author="Koios Component SDK Example",
            description="EtherNet/IP communication component for Allen-Bradley Logix PLCs",
            category=ComponentCategory.COMMUNICATION,
            koios_version_min="1.0.0",
            dependencies=["pycomm3>=1.2.14"],
            tags=["ethernet/ip", "logix", "allen-bradley", "protocol", "communication"]
        )
    
    @property
    def parameter_definitions(self) -> List[ParameterDefinition]:
        return [
            # Connection parameters
            ParameterDefinition(
                name="host",
                type="string",
                description="PLC hostname or IP address",
                required=True,
                default="192.168.1.137"
            ),
            ParameterDefinition(
                name="controller_slot",
                type="integer",
                description="Controller slot number in the chassis",
                required=False,
                default=0,
                min_value=0,
                max_value=16
            ),
            ParameterDefinition(
                name="timeout",
                type="float",
                description="Communication timeout in seconds",
                required=False,
                default=5.0,
                min_value=0.1,
                max_value=60.0
            ),
            ParameterDefinition(
                name="retry_count",
                type="integer",
                description="Number of retry attempts on communication failure",
                required=False,
                default=3,
                min_value=0,
                max_value=10
            ),
            ParameterDefinition(
                name="retry_delay",
                type="float",
                description="Delay between retry attempts in seconds",
                required=False,
                default=1.0,
                min_value=0.1,
                max_value=10.0
            ),
            
            # Protocol-specific parameters
            ParameterDefinition(
                name="enable_auto_reconnect",
                type="boolean",
                description="Enable automatic reconnection on connection loss",
                required=False,
                default=True
            ),
            ParameterDefinition(
                name="read_batch_size",
                type="integer",
                description="Maximum number of tags to read in a single batch",
                required=False,
                default=20,
                min_value=1,
                max_value=100
            ),
            ParameterDefinition(
                name="write_batch_size",
                type="integer",
                description="Maximum number of tags to write in a single batch",
                required=False,
                default=20,
                min_value=1,
                max_value=100
            ),
            ParameterDefinition(
                name="health_check_interval",
                type="float",
                description="Interval between health checks in seconds",
                required=False,
                default=30.0,
                min_value=5.0,
                max_value=300.0
            ),
            
            # Tag definitions
            ParameterDefinition(
                name="tags",
                type="json",
                description="List of tag definitions with name, address, data_type, and writable flag",
                required=False,
                default=[]
            ),
        ]
    
    def get_bindable_fields(self) -> List[str]:
        """Extended bindable fields for Logix protocol."""
        base_fields = super().get_bindable_fields()
        
        # Add tag-specific bindable fields
        tag_fields = []
        for tag_name in self._tags.keys():
            tag_fields.extend([
                f"{tag_name}_value",
                f"{tag_name}_quality",
                f"{tag_name}_timestamp"
            ])
        
        return base_fields + tag_fields + [
            "successful_reads",
            "failed_reads",
            "successful_writes",
            "failed_writes",
            "connection_path"
        ]
    
    @property
    def connection_path(self) -> str:
        """Get the full connection path."""
        return f"{self._host}/{self._controller_slot}"
    
    def _build_client(self) -> LogixDriver:
        """Build and configure a Logix client."""
        if not PYCOMM3_AVAILABLE:
            raise ImportError("pycomm3 library is not installed")
        
        if not self._host:
            raise ValueError("Host is required")
        
        if self._controller_slot is None:
            raise ValueError("Controller slot is required")
        
        self.logger.info(f"Building Logix client: {self.connection_path}")
        
        client = LogixDriver(self.connection_path)
        return client
    
    def _initialize_tags(self):
        """Initialize tag configurations from parameter definitions."""
        self._tags.clear()
        
        for tag_def in self._tag_definitions:
            try:
                name = tag_def.get('name')
                address = tag_def.get('address')
                data_type = tag_def.get('data_type', LogixDataType.REAL)
                writable = tag_def.get('writable', False)
                
                if not name or not address:
                    self.logger.warning(f"Skipping tag with missing name or address: {tag_def}")
                    continue
                
                tag_config = LogixTagConfig(name, address, data_type, writable)
                self._tags[name] = tag_config
                
                self.logger.debug(f"Initialized tag: {name} -> {address} (type: {data_type}, writable: {writable})")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize tag {tag_def}: {e}")
    
    @on_start
    def on_component_start(self):
        """Initialize on component start."""
        self.logger.info("Logix protocol component starting")
        self._initialize_tags()
        self.logger.info(f"Initialized {len(self._tags)} tags")
    
    @on_stop
    def on_component_stop(self):
        """Cleanup on component stop."""
        self.logger.info(f"Logix protocol component stopping - Stats: "
                        f"Reads: {self._successful_reads}/{self._successful_reads + self._failed_reads}, "
                        f"Writes: {self._successful_writes}/{self._successful_writes + self._failed_writes}")
    
    async def connect_async(self) -> bool:
        """Establish connection to Logix PLC asynchronously."""
        try:
            self.logger.info(f"Connecting to Logix PLC at {self.connection_path}")
            
            # Build client if it doesn't exist
            if self._client is None:
                self._client = self._build_client()
            
            # Open connection
            result = await asyncio.to_thread(self._client.open)
            
            if result:
                self._connected = True
                self._connection_time = time.time()
                self.logger.info(f"Successfully connected to {self.connection_path}")
                return True
            else:
                self.logger.error(f"Failed to connect to {self.connection_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self._client = None
            return False
    
    async def disconnect_async(self) -> bool:
        """Close connection to Logix PLC asynchronously."""
        try:
            if self._client:
                self.logger.info(f"Disconnecting from {self.connection_path}")
                await asyncio.to_thread(self._client.close)
                self._client = None
                self._connected = False
                self.logger.info("Disconnected successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Disconnection failed: {e}")
            return False
    
    async def read_tag_async(self, address: str) -> Any:
        """
        Read a single tag asynchronously.
        
        Args:
            address: Tag address in the PLC
            
        Returns:
            Tag value
        """
        if not self._client or not self._connected:
            raise ConnectionError("Not connected", self._host, self._port, self.component_id)
        
        try:
            result = await asyncio.to_thread(self._client.read, address)
            
            if isinstance(result, LogixTag):
                if result.error is not None:
                    raise ValueError(f"Tag read error: {result.error}")
                
                if result.value is None:
                    raise ValueError("Tag read returned None")
                
                return result.value
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            self.logger.error(f"Failed to read tag {address}: {e}")
            raise
    
    async def write_tag_async(self, address: str, value: Any) -> bool:
        """
        Write a single tag asynchronously.
        
        Args:
            address: Tag address in the PLC
            value: Value to write
            
        Returns:
            True if write succeeded
        """
        if not self._client or not self._connected:
            raise ConnectionError("Not connected", self._host, self._port, self.component_id)
        
        try:
            result = await asyncio.to_thread(self._client.write, (address, value))
            
            if isinstance(result, LogixTag):
                if result.error is not None:
                    raise ValueError(f"Tag write error: {result.error}")
                
                return True
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            self.logger.error(f"Failed to write tag {address}: {e}")
            raise
    
    async def read_tags_batch_async(self, tag_addresses: List[str]) -> Dict[str, Any]:
        """
        Read multiple tags in a batch operation.
        
        Args:
            tag_addresses: List of tag addresses to read
            
        Returns:
            Dictionary mapping tag addresses to their values
        """
        if not self._client or not self._connected:
            raise ConnectionError("Not connected", self._host, self._port, self.component_id)
        
        results = {}
        
        try:
            # Read all tags at once using pycomm3's multi-read capability
            read_results = await asyncio.to_thread(self._client.read, *tag_addresses)
            
            # Handle single or multiple results
            if isinstance(read_results, LogixTag):
                read_results = [read_results]
            
            # Process results
            for i, address in enumerate(tag_addresses):
                try:
                    result = read_results[i]
                    
                    if result.error is not None:
                        self.logger.warning(f"Error reading {address}: {result.error}")
                        results[address] = None
                    elif result.value is None:
                        self.logger.warning(f"Tag {address} returned None")
                        results[address] = None
                    else:
                        results[address] = result.value
                        
                except IndexError:
                    self.logger.error(f"Result index mismatch for {address}")
                    results[address] = None
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch read failed: {e}")
            raise
    
    async def write_tags_batch_async(self, tag_values: Dict[str, Any]) -> Dict[str, bool]:
        """
        Write multiple tags in a batch operation.
        
        Args:
            tag_values: Dictionary mapping tag addresses to values
            
        Returns:
            Dictionary mapping tag addresses to write success status
        """
        if not self._client or not self._connected:
            raise ConnectionError("Not connected", self._host, self._port, self.component_id)
        
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
                try:
                    result = write_results[i]
                    
                    if result.error is not None:
                        self.logger.warning(f"Error writing {address}: {result.error}")
                        results[address] = False
                    else:
                        results[address] = True
                        
                except IndexError:
                    self.logger.error(f"Result index mismatch for {address}")
                    results[address] = False
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch write failed: {e}")
            raise
    
    async def health_check_async(self) -> Dict[str, Any]:
        """
        Check connection health asynchronously.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            if not self._client:
                return {
                    'success': False,
                    'status': 'disconnected',
                    'message': 'Client not initialized'
                }
            
            # Check if client is connected
            if not self._client.connected:
                return {
                    'success': False,
                    'status': 'disconnected',
                    'message': 'Client is not connected'
                }
            
            # Try a simple operation to verify connection
            # Read a system tag or the first configured tag
            if self._tags:
                first_tag = next(iter(self._tags.values()))
                try:
                    await self.read_tag_async(first_tag.address)
                    
                    return {
                        'success': True,
                        'status': 'healthy',
                        'message': 'Connection is healthy',
                        'stats': {
                            'successful_reads': self._successful_reads,
                            'failed_reads': self._failed_reads,
                            'successful_writes': self._successful_writes,
                            'failed_writes': self._failed_writes
                        }
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'status': 'error',
                        'message': f'Health check read failed: {e}'
                    }
            else:
                # No tags configured, just check connection status
                return {
                    'success': True,
                    'status': 'healthy',
                    'message': 'Connected (no tags configured for verification)'
                }
                
        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'message': f'Health check failed: {e}'
            }
    
    @validate_parameters
    def read_all_tags(self) -> Dict[str, Any]:
        """
        Read all configured tags.
        
        Returns:
            Dictionary of tag read results
        """
        if not self._connected:
            self.logger.warning("Cannot read tags: not connected")
            return {}
        
        start_time = time.time()
        tag_addresses = [tag.address for tag in self._tags.values()]
        
        try:
            results = asyncio.run(self.read_tags_batch_async(tag_addresses))
            
            # Update tag configurations
            for tag_name, tag_config in self._tags.items():
                value = results.get(tag_config.address)
                if value is not None:
                    try:
                        tag_config.value = tag_config.convert_value(value)
                        tag_config.quality = "Good"
                        tag_config.timestamp = datetime.now(timezone.utc)
                        tag_config.error = None
                        self._successful_reads += 1
                    except Exception as e:
                        tag_config.quality = "Bad"
                        tag_config.error = str(e)
                        self._failed_reads += 1
                else:
                    tag_config.quality = "Bad"
                    tag_config.error = "Read returned None"
                    self._failed_reads += 1
            
            self._last_read_time = time.time() - start_time
            return {tag_name: tag.value for tag_name, tag in self._tags.items()}
            
        except Exception as e:
            self.logger.error(f"Failed to read tags: {e}")
            self._failed_reads += len(tag_addresses)
            return {}
    
    @validate_parameters
    def write_tags(self, tag_values: Dict[str, Any]) -> bool:
        """
        Write values to specified tags.
        
        Args:
            tag_values: Dictionary mapping tag names to values
            
        Returns:
            True if all writes succeeded
        """
        if not self._connected:
            self.logger.warning("Cannot write tags: not connected")
            return False
        
        start_time = time.time()
        
        # Build write list with addresses
        write_dict = {}
        for tag_name, value in tag_values.items():
            if tag_name in self._tags:
                tag_config = self._tags[tag_name]
                if tag_config.writable:
                    try:
                        converted_value = tag_config.convert_value(value)
                        write_dict[tag_config.address] = converted_value
                    except Exception as e:
                        self.logger.error(f"Failed to convert value for {tag_name}: {e}")
                        self._failed_writes += 1
                else:
                    self.logger.warning(f"Tag {tag_name} is not writable")
                    self._failed_writes += 1
            else:
                self.logger.warning(f"Tag {tag_name} not found")
                self._failed_writes += 1
        
        if not write_dict:
            return False
        
        try:
            results = asyncio.run(self.write_tags_batch_async(write_dict))
            
            success_count = sum(1 for success in results.values() if success)
            fail_count = len(results) - success_count
            
            self._successful_writes += success_count
            self._failed_writes += fail_count
            
            self._last_write_time = time.time() - start_time
            
            return fail_count == 0
            
        except Exception as e:
            self.logger.error(f"Failed to write tags: {e}")
            self._failed_writes += len(write_dict)
            return False
    
    def get_tag_value(self, tag_name: str) -> Any:
        """Get the current value of a tag."""
        if tag_name in self._tags:
            return self._tags[tag_name].value
        return None
    
    def get_tag_info(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tag."""
        if tag_name in self._tags:
            tag = self._tags[tag_name]
            return {
                'name': tag.name,
                'address': tag.address,
                'data_type': tag.data_type,
                'writable': tag.writable,
                'value': tag.value,
                'quality': tag.quality,
                'timestamp': tag.timestamp.isoformat() if tag.timestamp else None,
                'error': tag.error
            }
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get protocol statistics."""
        return {
            'connection': {
                'connected': self._connected,
                'connection_path': self.connection_path,
                'connection_time': self._connection_time,
                'last_communication_time': self._last_communication_time
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
            },
            'tags': {
                'total': len(self._tags),
                'configured': [tag.name for tag in self._tags.values()]
            }
        }


# Example usage and testing
if __name__ == "__main__":
    import logging
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example configuration
    config = {
        "host": "192.168.1.137",
        "controller_slot": 0,
        "timeout": 5.0,
        "retry_count": 3,
        "enable_auto_reconnect": True,
        "read_batch_size": 20,
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
    
    # Create component instance
    component = LogixProtocolComponent("logix_01", config)
    
    # Initialize and start
    if component.initialize():
        print("✓ Component initialized")
        
        if component.start():
            print("✓ Component started and connected")
            
            # Read all tags
            print("\nReading all tags...")
            tag_values = component.read_all_tags()
            for tag_name, value in tag_values.items():
                tag_info = component.get_tag_info(tag_name)
                print(f"  {tag_name}: {value} (Quality: {tag_info['quality']})")
            
            # Write some tags
            print("\nWriting tags...")
            write_success = component.write_tags({
                "setpoint": 75.5,
                "valve_position": 50
            })
            print(f"  Write {'succeeded' if write_success else 'failed'}")
            
            # Health check
            print("\nPerforming health check...")
            health = component.health_check()
            print(f"  Status: {health.get('status')}")
            print(f"  Message: {health.get('message')}")
            
            # Get statistics
            print("\nStatistics:")
            stats = component.get_statistics()
            print(f"  Successful reads: {stats['reads']['successful']}")
            print(f"  Failed reads: {stats['reads']['failed']}")
            print(f"  Successful writes: {stats['writes']['successful']}")
            print(f"  Failed writes: {stats['writes']['failed']}")
            
            # Stop component
            component.stop()
            print("\n✓ Component stopped")
        else:
            print("✗ Failed to start component")
    else:
        print("✗ Failed to initialize component")

