"""
Endress Hauser ProMag/ProMass Component

This component provides a logic block for data input and flow meter analysis
using EtherNet/IP communication with Endress Hauser ProMag and ProMass devices.

Features:
- EtherNet/IP communication with ProMag/ProMass devices
- Real-time flow meter data acquisition
- Flow analysis and validation
- Mass flow, volume flow, density, and temperature monitoring
- Totalizer management
- Device diagnostics and status monitoring
"""

from __future__ import annotations
import socket
import struct
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time

from koios_component_sdk.base import LogicComponent
from koios_component_sdk.base.component import ComponentMetadata, ParameterDefinition, ComponentCategory
from koios_component_sdk.decorators import validate_parameters, bind_to_tag, on_start, on_stop


# EtherNet/IP constants
ENIP_PORT = 44818

ENIP_CMD_REGISTER_SESSION = 0x0065
ENIP_CMD_UNREGISTER_SESSION = 0x0066
ENIP_CMD_SEND_RR_DATA = 0x006F
ENIP_CMD_SEND_UNIT_DATA = 0x0070
ENIP_CMD_LIST_IDENTITY = 0x0063

ENIP_PROTOCOL_VERSION = 1


# --- CIP services -----------------------------------------------------------

class CIPServices:
    GET_ATTRIBUTE_SINGLE = 0x0E
    SET_ATTRIBUTE_SINGLE = 0x10
    FORWARD_OPEN = 0x54
    FORWARD_CLOSE = 0x4E


# --- Exceptions --------------------------------------------------------------

class EnipError(Exception):
    """Low-level EtherNet/IP encapsulation error."""


class CIPError(Exception):
    """CIP-level error (non-zero general status, etc.)."""


# --- EtherNet/IP encapsulation layer ----------------------------------------

@dataclass
class EnipResponse:
    command: int
    status: int
    session_handle: int
    sender_context: bytes
    options: int
    data: bytes


class EnipClient:
    """
    Minimal EtherNet/IP encapsulation client for explicit CIP messaging.
    """

    def __init__(self, host: str, port: int = ENIP_PORT, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.session_handle: int = 0
        self.sock: Optional[socket.socket] = None

    # --- connection / session management ---

    def connect(self) -> None:
        if self.sock is not None:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect((self.host, self.port))
        self.sock = s
        self._register_session()

    def close(self) -> None:
        try:
            if self.session_handle:
                self._unregister_session()
        finally:
            if self.sock is not None:
                try:
                    self.sock.close()
                finally:
                    self.sock = None
                    self.session_handle = 0

    # context manager helpers
    def __enter__(self) -> "EnipClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --- low-level send/recv ---

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise EnipError("Socket closed while receiving")
            buf += chunk
        return buf

    def _send_enip(self, command: int, data: bytes) -> EnipResponse:
        if self.sock is None:
            raise EnipError("Socket not connected")

        length = len(data)
        status = 0
        sender_context = b"\x00" * 8
        options = 0

        header = struct.pack(
            "<HHII8sI",
            command,
            length,
            self.session_handle,
            status,
            sender_context,
            options,
        )

        packet = header + data
        self.sock.sendall(packet)

        # read fixed header
        hdr = self._recv_exact(24)
        if len(hdr) != 24:
            raise EnipError("Short ENIP header")

        r_command, r_length, r_session, r_status, r_ctx, r_opts = struct.unpack(
            "<HHII8sI", hdr
        )

        # read payload
        payload = self._recv_exact(r_length)
        return EnipResponse(
            command=r_command,
            status=r_status,
            session_handle=r_session,
            sender_context=r_ctx,
            options=r_opts,
            data=payload,
        )

    # --- session commands ---

    def _register_session(self) -> None:
        payload = struct.pack("<HH", ENIP_PROTOCOL_VERSION, 0)
        resp = self._send_enip(ENIP_CMD_REGISTER_SESSION, payload)
        if resp.status != 0:
            raise EnipError(f"RegisterSession failed with status {resp.status}")
        if len(resp.data) < 4:
            raise EnipError("RegisterSession response too short")
        (self.session_handle,) = struct.unpack("<I", resp.data[:4])

    def _unregister_session(self) -> None:
        self._send_enip(ENIP_CMD_UNREGISTER_SESSION, b"")
        self.session_handle = 0

    # --- higher-level helpers ---

    def list_identity(self) -> EnipResponse:
        return self._send_enip(ENIP_CMD_LIST_IDENTITY, b"")

    def send_rr_data(self, cip_payload: bytes) -> bytes:
        """
        Send an unconnected explicit CIP message via SendRRData.
        Returns raw CIP reply bytes.
        """
        # Encapsulation of SendRRData:
        # UINT32 interface_handle (0 for CIP)
        # UINT16 timeout
        # UINT16 item count
        # then items: (ID, length, data)...
        interface_handle = 0
        timeout = 0
        item_count = 2

        # Null address item
        addr_item_id = 0x0000
        addr_length = 0

        # Unconnected data item
        data_item_id = 0x00B2
        data_length = len(cip_payload)

        payload = struct.pack(
            "<IHHHHH",
            interface_handle,
            timeout,
            item_count,
            addr_item_id,
            addr_length,
            data_item_id,
        ) + struct.pack("<H", data_length) + cip_payload

        resp = self._send_enip(ENIP_CMD_SEND_RR_DATA, payload)
        if resp.status != 0:
            raise EnipError(f"SendRRData failed with status {resp.status}")

        # Parse back CPF to extract CIP data
        if len(resp.data) < 10:
            raise EnipError("SendRRData response too short")

        iface, timeout, item_count = struct.unpack("<IHH", resp.data[:8])
        offset = 8
        cip_reply = b""
        for _ in range(item_count):
            item_id, item_len = struct.unpack("<HH", resp.data[offset:offset + 4])
            offset += 4
            item_data = resp.data[offset:offset + item_len]
            offset += item_len
            if item_id == 0x00B2:  # unconnected data item
                cip_reply = item_data
        if not cip_reply:
            raise EnipError("No CIP reply item in SendRRData response")
        return cip_reply


# --- CIP layer --------------------------------------------------------------

class CIPPath:
    """
    Helper for building CIP EPATH (class / instance / attribute).
    Only implements the common 8/16-bit logical segments.
    """

    def __init__(
        self,
        class_id: Optional[int] = None,
        instance_id: Optional[int] = None,
        attribute_id: Optional[int] = None,
    ) -> None:
        self.class_id = class_id
        self.instance_id = instance_id
        self.attribute_id = attribute_id

    def encode(self) -> bytes:
        """
        Encode as EPATH:
        - Class segment (0x20 or 0x21)
        - Instance segment (0x24 or 0x25)
        - Attribute segment (0x30 or 0x31)
        """
        path = b""

        def seg(seg_type, value):
            # choose 8-bit (0x20/0x24/0x30) if value < 256,
            # otherwise 16-bit (0x21/0x25/0x31)
            if value < 0 or value > 0xFFFF:
                raise ValueError("EPATH segment out of range")
            if value < 256:
                return struct.pack("BB", seg_type, value)
            return struct.pack("<BBH", seg_type + 1, 0, value)

        if self.class_id is not None:
            path += seg(0x20, self.class_id)
        if self.instance_id is not None:
            path += seg(0x24, self.instance_id)
        if self.attribute_id is not None:
            path += seg(0x30, self.attribute_id)

        return path


class CIPClient:
    """
    Simple CIP client on top of an EnipClient.
    Supports explicit messaging (Get/Set Attribute Single).
    """

    def __init__(self, enip: EnipClient) -> None:
        self.enip = enip

    def _send_cip(self, service: int, path: CIPPath, data: bytes = b"") -> bytes:
        path_bytes = path.encode()
        # path size is in 16-bit words
        if len(path_bytes) % 2 != 0:
            # pad to even
            path_bytes += b"\x00"
        path_size_words = len(path_bytes) // 2

        req = struct.pack("BB", service, path_size_words) + path_bytes + data
        resp = self.enip.send_rr_data(req)

        if len(resp) < 4:
            raise CIPError("CIP response too short")

        resp_service, _resp_size = struct.unpack("BB", resp[:2])
        # Response service is service | 0x80
        if resp_service != (service | 0x80):
            raise CIPError(f"Unexpected CIP service in response: 0x{resp_service:02X}")

        # Now: general status, additional status size
        gen_status = resp[2]
        add_stat_size = resp[3]
        offset = 4 + add_stat_size * 2  # additional status are 16-bit words

        if gen_status != 0:
            # Extract additional status if present
            add_status = []
            if add_stat_size:
                add_raw = resp[4:4 + add_stat_size * 2]
                add_status = list(struct.unpack("<" + "H" * add_stat_size, add_raw))
            raise CIPError(
                f"CIP error: general_status={gen_status}, additional={add_status}"
            )

        return resp[offset:]

    def get_attribute_single(
        self, class_id: int, instance_id: int, attribute_id: int
    ) -> bytes:
        path = CIPPath(class_id=class_id, instance_id=instance_id, attribute_id=attribute_id)
        return self._send_cip(CIPServices.GET_ATTRIBUTE_SINGLE, path)

    def set_attribute_single(
        self,
        class_id: int,
        instance_id: int,
        attribute_id: int,
        value: bytes,
    ) -> None:
        path = CIPPath(class_id=class_id, instance_id=instance_id, attribute_id=attribute_id)
        _ = self._send_cip(CIPServices.SET_ATTRIBUTE_SINGLE, path, data=value)


# --- Promass / Promag device support ---------------------------------------

class PromassAssemblies:
    """
    Helpers to parse/build assembly data for Promass/Promag.
    Adjust struct layouts and offsets to match your exact E+H model docs.
    """

    # Example layout for an input assembly: this is a placeholder.
    # Replace with real offsets/types from the Endress+Hauser manual.
    # e.g. mass_flow [float], volume_flow [float], density [float], temperature [float]
    INPUT_STRUCT = "<ffff"

    @staticmethod
    def parse_input_assembly(data: bytes) -> Dict[str, Any]:
        """
        Parse T->O data from the input assembly.
        """
        if len(data) < struct.calcsize(PromassAssemblies.INPUT_STRUCT):
            raise ValueError("Input assembly data too short")

        mass_flow, volume_flow, density, temperature = struct.unpack(
            PromassAssemblies.INPUT_STRUCT,
            data[: struct.calcsize(PromassAssemblies.INPUT_STRUCT)],
        )

        return {
            "mass_flow": mass_flow,
            "volume_flow": volume_flow,
            "density": density,
            "temperature": temperature,
        }

    @staticmethod
    def build_output_assembly(
        reset_totalizer: bool = False,
        **kwargs: Any,
    ) -> bytes:
        """
        Build an example O->T command structure.
        Replace with a struct that matches your meter's Output Assembly.
        """
        # Example: first 16-bit word is bitfield of commands.
        cmd_bits = 0
        if reset_totalizer:
            cmd_bits |= 0x0001

        # Simple example: just the command word.
        return struct.pack("<H", cmd_bits)


class PromassDevice:
    """
    High-level driver for an Endress+Hauser Proline Promass/Promag device
    using explicit CIP messaging on EtherNet/IP.
    """

    # Assembly object is class 0x04 per CIP spec
    ASSEMBLY_CLASS_ID = 0x04

    def __init__(self, ip: str, timeout: float = 2.0) -> None:
        self.enip = EnipClient(ip, timeout=timeout)
        self.cip = CIPClient(self.enip)

        # TODO: replace these with your actual instance numbers from the E+H manual:
        self.input_assembly_instance = 100
        self.output_assembly_instance = 150

    def connect(self) -> None:
        self.enip.connect()

    def disconnect(self) -> None:
        self.enip.close()

    def __enter__(self) -> "PromassDevice":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # --- Basic identity / diagnostics ---

    def read_identity_vendor_id(self) -> int:
        """
        Identity object (class 0x01), instance 1, attribute 1 = Vendor ID.
        """
        raw = self.cip.get_attribute_single(0x01, 1, 1)
        if len(raw) < 2:
            raise ValueError("Vendor ID response too short")
        (vendor_id,) = struct.unpack("<H", raw[:2])
        return vendor_id

    def read_identity_product_code(self) -> int:
        """
        Identity object attribute 3 = Product Code (class 0x01, instance 1, attr 3).
        """
        raw = self.cip.get_attribute_single(0x01, 1, 3)
        if len(raw) < 2:
            raise ValueError("Product Code response too short")
        (product_code,) = struct.unpack("<H", raw[:2])
        return product_code

    # --- Explicit read/write on assemblies ---

    def read_input_assembly_raw(self) -> bytes:
        """
        Read raw data from Input Assembly via GetAttributeSingle.
        Attribute 3 (0x03) is typically the data attribute for Assembly Object.
        """
        raw = self.cip.get_attribute_single(
            self.ASSEMBLY_CLASS_ID,
            self.input_assembly_instance,
            3,  # data attribute
        )
        return raw

    def read_process_values(self) -> Dict[str, Any]:
        """
        High-level parsed process values (mass flow, temp, etc.).
        """
        raw = self.read_input_assembly_raw()
        return PromassAssemblies.parse_input_assembly(raw)

    def write_output_assembly_raw(self, data: bytes) -> None:
        """
        Write raw data to Output Assembly via SetAttributeSingle.
        """
        self.cip.set_attribute_single(
            self.ASSEMBLY_CLASS_ID,
            self.output_assembly_instance,
            3,  # data attribute
            data,
        )

    def reset_totalizer(self) -> None:
        """
        Example: raise the "reset totalizer" bit in the output assembly.
        Actual semantics (edge vs level, which totalizer, etc.) must match the E+H manual.
        """
        out_data = PromassAssemblies.build_output_assembly(reset_totalizer=True)
        self.write_output_assembly_raw(out_data)


# --- Koios Component Implementation -----------------------------------------

class PromassProMagComponent(LogicComponent):
    """
    Endress Hauser ProMag/ProMass Component for data input and flow meter analysis.
    
    This logic component communicates with Endress Hauser ProMag and ProMass devices
    via EtherNet/IP, reads flow meter data, and performs analysis including:
    - Mass flow and volume flow monitoring
    - Density and temperature tracking
    - Flow rate validation and alarm generation
    - Totalizer management
    - Device diagnostics
    """

    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        super().__init__(component_id, parameters)
        
        # Device connection parameters
        self._device_ip = parameters.get('device_ip', '192.168.1.100')
        self._device_timeout = parameters.get('device_timeout', 2.0)
        self._input_assembly_instance = parameters.get('input_assembly_instance', 100)
        self._output_assembly_instance = parameters.get('output_assembly_instance', 150)
        
        # Communication settings
        self._read_interval = parameters.get('read_interval', 1.0)
        self._connection_retry_count = parameters.get('connection_retry_count', 3)
        self._connection_retry_delay = parameters.get('connection_retry_delay', 1.0)
        
        # Flow analysis parameters
        self._mass_flow_min = parameters.get('mass_flow_min', 0.0)
        self._mass_flow_max = parameters.get('mass_flow_max', 1000.0)
        self._volume_flow_min = parameters.get('volume_flow_min', 0.0)
        self._volume_flow_max = parameters.get('volume_flow_max', 1000.0)
        self._density_min = parameters.get('density_min', 0.0)
        self._density_max = parameters.get('density_max', 2000.0)
        self._temperature_min = parameters.get('temperature_min', -50.0)
        self._temperature_max = parameters.get('temperature_max', 200.0)
        
        # Analysis settings
        self._enable_flow_validation = parameters.get('enable_flow_validation', True)
        self._enable_rate_of_change_check = parameters.get('enable_rate_of_change_check', True)
        self._max_rate_of_change = parameters.get('max_rate_of_change', 100.0)  # units per second
        
        # Device instance
        self._device: Optional[PromassDevice] = None
        self._connected = False
        
        # Current process values
        self._mass_flow: float = 0.0
        self._volume_flow: float = 0.0
        self._density: float = 0.0
        self._temperature: float = 0.0
        
        # Previous values for rate of change calculation
        self._prev_mass_flow: float = 0.0
        self._prev_volume_flow: float = 0.0
        self._prev_read_time: Optional[float] = None
        
        # Status and diagnostics
        self._device_status: str = "DISCONNECTED"
        self._last_read_time: Optional[float] = None
        self._read_error_count: int = 0
        self._connection_error_count: int = 0
        
        # Analysis results
        self._flow_valid: bool = False
        self._alarms: Dict[str, bool] = {
            'mass_flow_high': False,
            'mass_flow_low': False,
            'volume_flow_high': False,
            'volume_flow_low': False,
            'density_high': False,
            'density_low': False,
            'temperature_high': False,
            'temperature_low': False,
            'rate_of_change_high': False,
            'device_error': False
        }
        
        # Statistics
        self._total_reads: int = 0
        self._successful_reads: int = 0
        self._failed_reads: int = 0

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="Endress Hauser ProMag/ProMass Component",
            version="1.0.0",
            author="Koios SDK Example",
            description="Logic block for data input and flow meter analysis using EtherNet/IP communication",
            category=ComponentCategory.LOGIC,
            koios_version_min="1.0.0",
            tags=["flowmeter", "promass", "promag", "endress-hauser", "ethernet-ip", "analysis"]
        )

    @property
    def parameter_definitions(self) -> List[ParameterDefinition]:
        return [
            ParameterDefinition(
                name="device_ip",
                type="string",
                description="IP address of the ProMag/ProMass device",
                default="192.168.1.100",
                required=True
            ),
            ParameterDefinition(
                name="device_timeout",
                type="float",
                description="Device communication timeout in seconds",
                default=2.0,
                min_value=0.1,
                max_value=60.0,
                required=False
            ),
            ParameterDefinition(
                name="input_assembly_instance",
                type="integer",
                description="CIP input assembly instance number",
                default=100,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="output_assembly_instance",
                type="integer",
                description="CIP output assembly instance number",
                default=150,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="read_interval",
                type="float",
                description="Interval between device reads in seconds",
                default=1.0,
                min_value=0.1,
                required=False
            ),
            ParameterDefinition(
                name="connection_retry_count",
                type="integer",
                description="Number of connection retry attempts",
                default=3,
                min_value=0,
                required=False
            ),
            ParameterDefinition(
                name="connection_retry_delay",
                type="float",
                description="Delay between connection retry attempts in seconds",
                default=1.0,
                min_value=0.1,
                required=False
            ),
            ParameterDefinition(
                name="mass_flow_min",
                type="float",
                description="Minimum valid mass flow value",
                default=0.0,
                required=False
            ),
            ParameterDefinition(
                name="mass_flow_max",
                type="float",
                description="Maximum valid mass flow value",
                default=1000.0,
                required=False
            ),
            ParameterDefinition(
                name="volume_flow_min",
                type="float",
                description="Minimum valid volume flow value",
                default=0.0,
                required=False
            ),
            ParameterDefinition(
                name="volume_flow_max",
                type="float",
                description="Maximum valid volume flow value",
                default=1000.0,
                required=False
            ),
            ParameterDefinition(
                name="density_min",
                type="float",
                description="Minimum valid density value",
                default=0.0,
                required=False
            ),
            ParameterDefinition(
                name="density_max",
                type="float",
                description="Maximum valid density value",
                default=2000.0,
                required=False
            ),
            ParameterDefinition(
                name="temperature_min",
                type="float",
                description="Minimum valid temperature value",
                default=-50.0,
                required=False
            ),
            ParameterDefinition(
                name="temperature_max",
                type="float",
                description="Maximum valid temperature value",
                default=200.0,
                required=False
            ),
            ParameterDefinition(
                name="enable_flow_validation",
                type="boolean",
                description="Enable flow value validation against min/max limits",
                default=True,
                required=False
            ),
            ParameterDefinition(
                name="enable_rate_of_change_check",
                type="boolean",
                description="Enable rate of change validation",
                default=True,
                required=False
            ),
            ParameterDefinition(
                name="max_rate_of_change",
                type="float",
                description="Maximum allowed rate of change (units per second)",
                default=100.0,
                min_value=0.0,
                required=False
            ),
            ParameterDefinition(
                name="evaluation_interval",
                type="float",
                description="Logic evaluation interval in seconds",
                default=1.0,
                min_value=0.1,
                required=False
            ),
        ]

    @bind_to_tag("promass_mass_flow", direction="output")
    def mass_flow(self) -> float:
        """Mass flow output from device."""
        return self._mass_flow

    @bind_to_tag("promass_volume_flow", direction="output")
    def volume_flow(self) -> float:
        """Volume flow output from device."""
        return self._volume_flow

    @bind_to_tag("promass_density", direction="output")
    def density(self) -> float:
        """Density output from device."""
        return self._density

    @bind_to_tag("promass_temperature", direction="output")
    def temperature(self) -> float:
        """Temperature output from device."""
        return self._temperature

    @bind_to_tag("promass_device_status", direction="output")
    def device_status(self) -> str:
        """Device connection status."""
        return self._device_status

    @bind_to_tag("promass_flow_valid", direction="output")
    def flow_valid(self) -> bool:
        """Flow validation status."""
        return self._flow_valid

    @bind_to_tag("promass_reset_totalizer", direction="input")
    def reset_totalizer_command(self) -> bool:
        """Command to reset totalizer."""
        return self.get_input('reset_totalizer', False)

    def get_bindable_fields(self) -> List[str]:
        """Return fields that can be bound to Koios tags."""
        base_fields = super().get_bindable_fields()
        return base_fields + [
            "mass_flow",
            "volume_flow",
            "density",
            "temperature",
            "device_status",
            "flow_valid",
            "total_reads",
            "successful_reads",
            "failed_reads",
            "read_error_count",
            "connection_error_count"
        ]

    def _connect_device(self) -> bool:
        """Connect to the ProMag/ProMass device."""
        if self._connected and self._device is not None:
            return True
        
        for attempt in range(self._connection_retry_count + 1):
            try:
                self._device = PromassDevice(self._device_ip, timeout=self._device_timeout)
                self._device.input_assembly_instance = self._input_assembly_instance
                self._device.output_assembly_instance = self._output_assembly_instance
                self._device.connect()
                self._connected = True
                self._device_status = "CONNECTED"
                self.logger.info(f"Successfully connected to device at {self._device_ip}")
                return True
            except Exception as e:
                self._connection_error_count += 1
                self.logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < self._connection_retry_count:
                    time.sleep(self._connection_retry_delay)
        
        self._connected = False
        self._device_status = "CONNECTION_FAILED"
        self.logger.error(f"Failed to connect to device at {self._device_ip} after {self._connection_retry_count + 1} attempts")
        return False

    def _disconnect_device(self) -> None:
        """Disconnect from the device."""
        if self._device is not None:
            try:
                self._device.disconnect()
            except Exception as e:
                self.logger.warning(f"Error disconnecting device: {str(e)}")
            finally:
                self._device = None
                self._connected = False
                self._device_status = "DISCONNECTED"

    def _read_device_data(self) -> bool:
        """Read data from the device."""
        if not self._connected or self._device is None:
            if not self._connect_device():
                return False
        
        try:
            values = self._device.read_process_values()
            
            # Update current values
            self._mass_flow = values.get('mass_flow', 0.0)
            self._volume_flow = values.get('volume_flow', 0.0)
            self._density = values.get('density', 0.0)
            self._temperature = values.get('temperature', 0.0)
            
            self._last_read_time = time.time()
            self._total_reads += 1
            self._successful_reads += 1
            
            # Update outputs
            self.set_output('mass_flow', self._mass_flow)
            self.set_output('volume_flow', self._volume_flow)
            self.set_output('density', self._density)
            self.set_output('temperature', self._temperature)
            
            return True
            
        except Exception as e:
            self._read_error_count += 1
            self._failed_reads += 1
            self.logger.error(f"Error reading device data: {str(e)}")
            self._connected = False
            self._device_status = "READ_ERROR"
            if self._device is not None:
                self._disconnect_device()
            return False

    def _validate_flow_values(self) -> bool:
        """Validate flow values against configured limits."""
        valid = True
        
        # Reset alarms
        for alarm_key in self._alarms:
            self._alarms[alarm_key] = False
        
        # Mass flow validation
        if self._mass_flow < self._mass_flow_min:
            self._alarms['mass_flow_low'] = True
            valid = False
        elif self._mass_flow > self._mass_flow_max:
            self._alarms['mass_flow_high'] = True
            valid = False
        
        # Volume flow validation
        if self._volume_flow < self._volume_flow_min:
            self._alarms['volume_flow_low'] = True
            valid = False
        elif self._volume_flow > self._volume_flow_max:
            self._alarms['volume_flow_high'] = True
            valid = False
        
        # Density validation
        if self._density < self._density_min:
            self._alarms['density_low'] = True
            valid = False
        elif self._density > self._density_max:
            self._alarms['density_high'] = True
            valid = False
        
        # Temperature validation
        if self._temperature < self._temperature_min:
            self._alarms['temperature_low'] = True
            valid = False
        elif self._temperature > self._temperature_max:
            self._alarms['temperature_high'] = True
            valid = False
        
        return valid

    def _check_rate_of_change(self) -> bool:
        """Check rate of change for flow values."""
        if self._prev_read_time is None:
            self._prev_read_time = time.time()
            self._prev_mass_flow = self._mass_flow
            self._prev_volume_flow = self._volume_flow
            return True
        
        current_time = time.time()
        dt = current_time - self._prev_read_time
        
        if dt > 0:
            # Calculate rate of change
            mass_flow_roc = abs(self._mass_flow - self._prev_mass_flow) / dt
            volume_flow_roc = abs(self._volume_flow - self._prev_volume_flow) / dt
            
            max_roc = max(mass_flow_roc, volume_flow_roc)
            
            if max_roc > self._max_rate_of_change:
                self._alarms['rate_of_change_high'] = True
                self.logger.warning(f"Rate of change exceeded: {max_roc:.2f} > {self._max_rate_of_change}")
                return False
        
        self._prev_read_time = current_time
        self._prev_mass_flow = self._mass_flow
        self._prev_volume_flow = self._volume_flow
        
        return True

    def evaluate_conditions(self) -> Dict[str, bool]:
        """
        Evaluate logic conditions.
        
        Returns:
            Dictionary of condition states
        """
        conditions = {
            'device_connected': self._connected,
            'device_read_successful': False,
            'flow_values_valid': False,
            'rate_of_change_ok': True,
            'any_alarm_active': False
        }
        
        # Check if read was successful
        if self._last_read_time is not None:
            time_since_read = time.time() - self._last_read_time
            conditions['device_read_successful'] = time_since_read < self._read_interval * 2
        
        # Validate flow values if enabled
        if self._enable_flow_validation:
            conditions['flow_values_valid'] = self._validate_flow_values()
            self._flow_valid = conditions['flow_values_valid']
        else:
            conditions['flow_values_valid'] = True
            self._flow_valid = True
        
        # Check rate of change if enabled
        if self._enable_rate_of_change_check:
            conditions['rate_of_change_ok'] = self._check_rate_of_change()
        
        # Check for active alarms
        conditions['any_alarm_active'] = any(self._alarms.values())
        
        return conditions

    def execute_logic(self) -> Dict[str, Any]:
        """
        Execute the main logic algorithm.
        
        Returns:
            Dictionary of output values
        """
        current_time = time.time()
        
        # Check if it's time to read from device
        should_read = (
            self._last_read_time is None or
            (current_time - self._last_read_time) >= self._read_interval
        )
        
        if should_read:
            self._read_device_data()
        
        # Handle reset totalizer command
        reset_cmd = self.get_input('reset_totalizer', False)
        if reset_cmd and self._connected and self._device is not None:
            try:
                self._device.reset_totalizer()
                self.logger.info("Totalizer reset command sent")
                # Clear the command
                self.set_input('reset_totalizer', False)
            except Exception as e:
                self.logger.error(f"Error resetting totalizer: {str(e)}")
                self._alarms['device_error'] = True
        
        # Prepare outputs
        outputs = {
            'mass_flow': self._mass_flow,
            'volume_flow': self._volume_flow,
            'density': self._density,
            'temperature': self._temperature,
            'device_status': self._device_status,
            'flow_valid': self._flow_valid,
            'alarms': self._alarms.copy()
        }
        
        return outputs

    @on_start
    def initialize_device(self):
        """Initialize device connection on start."""
        self.logger.info(f"Initializing ProMag/ProMass component for device at {self._device_ip}")
        self._connect_device()

    @on_stop
    def cleanup_device(self):
        """Cleanup device connection on stop."""
        self.logger.info("Stopping ProMag/ProMass component")
        self._disconnect_device()
        self.logger.info(f"Component stopped - Total reads: {self._total_reads}, "
                        f"Successful: {self._successful_reads}, Failed: {self._failed_reads}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get component statistics."""
        return {
            'total_reads': self._total_reads,
            'successful_reads': self._successful_reads,
            'failed_reads': self._failed_reads,
            'read_error_count': self._read_error_count,
            'connection_error_count': self._connection_error_count,
            'device_status': self._device_status,
            'connected': self._connected,
            'current_values': {
                'mass_flow': self._mass_flow,
                'volume_flow': self._volume_flow,
                'density': self._density,
                'temperature': self._temperature
            },
            'alarms': self._alarms.copy()
        }
