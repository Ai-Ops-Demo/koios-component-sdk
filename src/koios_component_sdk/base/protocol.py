"""
Base class for communication protocol components.

This module provides the ProtocolComponent base class for implementing custom
communication protocols in the Koios framework. Protocol components handle
data exchange with external devices and systems.
"""

from typing import Dict, Any, List, Optional, Union
from abc import abstractmethod
import asyncio
import time

from .component import BaseKoiosComponent, ComponentMetadata, ParameterDefinition, ComponentStatus
from ..exceptions import ConnectionError, ValidationError


class ProtocolComponent(BaseKoiosComponent):
    """
    Base class for communication protocol components.
    
    This class provides common functionality for protocol components including
    connection management, data exchange, and health monitoring. Protocol
    components implement communication with external devices and systems.
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        """Initialize the protocol component."""
        super().__init__(component_id, parameters)
        
        # Connection state
        self._connected: bool = False
        self._connection_time: Optional[float] = None
        self._last_communication_time: Optional[float] = None
        
        # Connection parameters
        self._host: str = parameters.get('host', 'localhost')
        self._port: int = parameters.get('port', 502)
        self._timeout: float = parameters.get('timeout', 5.0)
        self._retry_count: int = parameters.get('retry_count', 3)
        self._retry_delay: float = parameters.get('retry_delay', 1.0)
        
        # Statistics
        self._read_count: int = 0
        self._write_count: int = 0
        self._error_count: int = 0
        self._last_error_time: Optional[float] = None
        
        # Health monitoring
        self._health_check_interval: float = parameters.get('health_check_interval', 30.0)
        self._last_health_check: Optional[float] = None
        self._health_status: str = "unknown"
    
    @property
    def connected(self) -> bool:
        """Check if protocol is connected."""
        return self._connected
    
    @property
    def host(self) -> str:
        """Get the connection host."""
        return self._host
    
    @property
    def port(self) -> int:
        """Get the connection port."""
        return self._port
    
    @property
    def connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "connected": self._connected,
            "connection_time": self._connection_time,
            "last_communication_time": self._last_communication_time,
            "read_count": self._read_count,
            "write_count": self._write_count,
            "error_count": self._error_count,
            "last_error_time": self._last_error_time,
            "health_status": self._health_status
        }
    
    def get_bindable_fields(self) -> List[str]:
        """Return fields that can be bound to Koios tags."""
        return [
            "connected",
            "read_count",
            "write_count", 
            "error_count",
            "health_status"
        ]
    
    @abstractmethod
    async def connect_async(self) -> bool:
        """
        Establish connection asynchronously.
        
        This method must be implemented by subclasses to define the specific
        connection logic for the protocol.
        
        Returns:
            True if connection succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect_async(self) -> bool:
        """
        Close connection asynchronously.
        
        This method must be implemented by subclasses to define the specific
        disconnection logic for the protocol.
        
        Returns:
            True if disconnection succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    async def read_tag_async(self, address: str) -> Any:
        """
        Read a single tag asynchronously.
        
        Args:
            address: Tag address/identifier
            
        Returns:
            Tag value
        """
        pass
    
    @abstractmethod
    async def write_tag_async(self, address: str, value: Any) -> bool:
        """
        Write a single tag asynchronously.
        
        Args:
            address: Tag address/identifier
            value: Value to write
            
        Returns:
            True if write succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check_async(self) -> Dict[str, Any]:
        """
        Check connection health asynchronously.
        
        Returns:
            Dictionary containing health status information
        """
        pass
    
    def connect(self) -> bool:
        """Establish connection (synchronous wrapper)."""
        try:
            return asyncio.run(self.connect_async())
        except Exception as e:
            self.logger.error(f"Connection failed: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """Close connection (synchronous wrapper)."""
        try:
            return asyncio.run(self.disconnect_async())
        except Exception as e:
            self.logger.error(f"Disconnection failed: {str(e)}")
            return False
    
    def read_tag(self, address: str) -> Any:
        """Read a single tag (synchronous wrapper)."""
        try:
            if not self._connected:
                raise ConnectionError("Not connected", self._host, self._port, self.component_id)
            
            result = asyncio.run(self.read_tag_async(address))
            self._read_count += 1
            self._last_communication_time = time.time()
            return result
            
        except Exception as e:
            self._error_count += 1
            self._last_error_time = time.time()
            self.logger.error(f"Read failed for {address}: {str(e)}")
            raise
    
    def write_tag(self, address: str, value: Any) -> bool:
        """Write a single tag (synchronous wrapper)."""
        try:
            if not self._connected:
                raise ConnectionError("Not connected", self._host, self._port, self.component_id)
            
            result = asyncio.run(self.write_tag_async(address, value))
            if result:
                self._write_count += 1
                self._last_communication_time = time.time()
            else:
                self._error_count += 1
                self._last_error_time = time.time()
            
            return result
            
        except Exception as e:
            self._error_count += 1
            self._last_error_time = time.time()
            self.logger.error(f"Write failed for {address}: {str(e)}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Check connection health (synchronous wrapper)."""
        try:
            result = asyncio.run(self.health_check_async())
            self._last_health_check = time.time()
            self._health_status = result.get('status', 'unknown')
            return result
            
        except Exception as e:
            self._health_status = 'error'
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }
    
    def execute(self) -> Dict[str, Any]:
        """Execute protocol maintenance tasks."""
        try:
            if self._status != ComponentStatus.RUNNING:
                return {
                    "success": False,
                    "error": f"Protocol not running (status: {self._status.value})"
                }
            
            current_time = time.time()
            
            # Perform periodic health check
            if (self._last_health_check is None or 
                current_time - self._last_health_check > self._health_check_interval):
                
                health_result = self.health_check()
                if not health_result.get('success', False):
                    self.logger.warning("Health check failed")
            
            # Record execution
            self._record_execution()
            
            return {
                "success": True,
                "connected": self._connected,
                "health_status": self._health_status,
                "stats": self.connection_stats
            }
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_parameters(self) -> bool:
        """Validate protocol parameters."""
        try:
            # Validate host
            host = self.parameters.get('host', 'localhost')
            if not isinstance(host, str) or not host.strip():
                raise ValidationError("host must be a non-empty string", "host", "string", host, self.component_id)
            
            # Validate port
            port = self.parameters.get('port', 502)
            if not isinstance(port, int) or port < 1 or port > 65535:
                raise ValidationError("port must be an integer between 1 and 65535", "port", "integer", port, self.component_id)
            
            # Validate timeout
            timeout = self.parameters.get('timeout', 5.0)
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValidationError("timeout must be a positive number", "timeout", "positive number", timeout, self.component_id)
            
            # Validate retry parameters
            retry_count = self.parameters.get('retry_count', 3)
            if not isinstance(retry_count, int) or retry_count < 0:
                raise ValidationError("retry_count must be a non-negative integer", "retry_count", "integer", retry_count, self.component_id)
            
            retry_delay = self.parameters.get('retry_delay', 1.0)
            if not isinstance(retry_delay, (int, float)) or retry_delay < 0:
                raise ValidationError("retry_delay must be a non-negative number", "retry_delay", "number", retry_delay, self.component_id)
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Parameter validation failed: {str(e)}", component_id=self.component_id)
    
    def initialize(self) -> bool:
        """Initialize the protocol."""
        try:
            self._set_status(ComponentStatus.INITIALIZING)
            
            # Set up connection parameters
            self._host = self.parameters.get('host', 'localhost')
            self._port = self.parameters.get('port', 502)
            self._timeout = self.parameters.get('timeout', 5.0)
            self._retry_count = self.parameters.get('retry_count', 3)
            self._retry_delay = self.parameters.get('retry_delay', 1.0)
            self._health_check_interval = self.parameters.get('health_check_interval', 30.0)
            
            # Reset statistics
            self._read_count = 0
            self._write_count = 0
            self._error_count = 0
            self._last_error_time = None
            self._last_health_check = None
            self._health_status = "unknown"
            
            self._set_status(ComponentStatus.INITIALIZED)
            self.logger.info("Protocol initialized successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def start(self) -> bool:
        """Start the protocol."""
        try:
            if self._status != ComponentStatus.INITIALIZED:
                raise ValueError(f"Cannot start from status {self._status.value}")
            
            self._set_status(ComponentStatus.STARTING)
            
            # Establish connection
            if not self.connect():
                raise ConnectionError(f"Failed to connect to {self._host}:{self._port}", 
                                    self._host, self._port, self.component_id)
            
            self._connected = True
            self._connection_time = time.time()
            
            self._set_status(ComponentStatus.RUNNING)
            self.logger.info(f"Protocol started and connected to {self._host}:{self._port}")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def stop(self) -> bool:
        """Stop the protocol."""
        try:
            self._set_status(ComponentStatus.STOPPING)
            
            # Close connection
            if self._connected:
                self.disconnect()
                self._connected = False
                self._connection_time = None
            
            self._set_status(ComponentStatus.STOPPED)
            self.logger.info("Protocol stopped successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
