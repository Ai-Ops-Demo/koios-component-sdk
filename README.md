# Koios Component SDK

A comprehensive SDK for developing custom components for the Koios industrial automation platform. This SDK provides base classes, utilities, and tools for creating control components, communication protocols, data processors, and logic components that integrate seamlessly with Koios.

## 🚀 Features

- **Base Classes**: Pre-built base classes for different component types (Control, Protocol, Processing, Logic)
- **Parameter Validation**: Automatic parameter validation and configuration management
- **Testing Framework**: Mock Koios environment for component testing
- **CLI Tools**: Command-line tools for component creation, testing, and packaging
- **Template System**: Ready-to-use templates for rapid component development
- **Deployment Utilities**: Tools for packaging and deploying components to Koios

## 📦 Installation

```bash
pip install koios-component-sdk
```

For development:
```bash
pip install koios-component-sdk[dev]
```

## 🏗️ Quick Start

### 1. Create a New Component

```bash
koios-component create --name "My PID Controller" --category control --author "Your Name"
```

### 2. Implement Your Component

```python
from koios_component_sdk.base import ControllerComponent
from koios_component_sdk.decorators import validate_parameters
from koios_component_sdk.base.component import ComponentMetadata, ParameterDefinition, ComponentCategory

class MyPIDController(ControllerComponent):
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="My PID Controller",
            version="1.0.0",
            author="Your Name",
            description="Advanced PID controller with anti-windup",
            category=ComponentCategory.CONTROL,
            koios_version_min="1.0.0"
        )
    
    @property
    def parameter_definitions(self) -> List[ParameterDefinition]:
        return [
            ParameterDefinition(
                name="kp",
                type="float",
                description="Proportional gain",
                default=1.0,
                min_value=0.0
            ),
            ParameterDefinition(
                name="ki",
                type="float", 
                description="Integral gain",
                default=0.1,
                min_value=0.0
            ),
            ParameterDefinition(
                name="kd",
                type="float",
                description="Derivative gain", 
                default=0.01,
                min_value=0.0
            ),
        ]
    
    def compute_output(self) -> float:
        """Implement PID control algorithm"""
        kp = self.get_parameter('kp', 1.0)
        ki = self.get_parameter('ki', 0.1)
        kd = self.get_parameter('kd', 0.01)
        
        # PID calculation
        proportional = kp * self.error
        self._error_sum += self.error * self._dt
        integral = ki * self._error_sum
        derivative = kd * (self.error - self._previous_error) / self._dt
        
        return proportional + integral + derivative
```

### 3. Test Your Component

```bash
koios-component test ./my_pid_controller
```

### 4. Build and Deploy

```bash
koios-component build ./my_pid_controller
koios-component deploy my_pid_controller-1.0.0.kcp --host https://koios.example.com
```

## 🏛️ Architecture

### Component Types

The SDK provides specialized base classes for different types of components:

#### 🎛️ Control Components (`ControllerComponent`)
For implementing control algorithms like PID controllers, fuzzy logic controllers, etc.

```python
from koios_component_sdk.base import ControllerComponent

class MyController(ControllerComponent):
    def compute_output(self) -> float:
        # Implement your control algorithm
        return calculated_output
```

#### 🔌 Protocol Components (`ProtocolComponent`)
For implementing custom communication protocols.

```python
from koios_component_sdk.base import ProtocolComponent

class MyProtocol(ProtocolComponent):
    async def connect_async(self) -> bool:
        # Implement connection logic
        return True
    
    async def read_tag_async(self, address: str) -> Any:
        # Implement tag reading
        return value
```

#### 🔄 Processing Components (`ProcessorComponent`)
For implementing data processing and transformation algorithms.

```python
from koios_component_sdk.base import ProcessorComponent

class MyProcessor(ProcessorComponent):
    def process_data(self, data: List[Any]) -> Any:
        # Implement data processing
        return processed_result
```

#### 🧠 Logic Components (`LogicComponent`)
For implementing business logic, state machines, and decision-making algorithms.

```python
from koios_component_sdk.base import LogicComponent

class MyLogic(LogicComponent):
    def evaluate_conditions(self) -> Dict[str, bool]:
        # Evaluate logic conditions
        return {"condition1": True, "condition2": False}
    
    def execute_logic(self) -> Dict[str, Any]:
        # Execute main logic
        return {"output1": result}
```

### Decorators

The SDK provides powerful decorators for common functionality:

#### Validation Decorators
```python
from koios_component_sdk.decorators import validate_parameters, require_connection

@validate_parameters
def start(self):
    # Method will only execute if parameters are valid
    pass

@require_connection
def read_data(self):
    # Method requires active connection
    pass
```

#### Binding Decorators
```python
from koios_component_sdk.decorators import bind_to_tag, bind_to_device

@bind_to_tag("temperature_setpoint", direction="input")
def setpoint(self):
    return self._setpoint

@bind_to_tag("heater_output", direction="output") 
def output(self):
    return self._output
```

#### Lifecycle Decorators
```python
from koios_component_sdk.decorators import on_start, on_stop, on_error

@on_start
def initialize_hardware(self):
    # Called when component starts
    pass

@on_stop
def cleanup_resources(self):
    # Called when component stops
    pass

@on_error
def handle_error(self, error):
    # Called when component encounters an error
    pass
```

## 🛠️ CLI Tools

The SDK includes comprehensive CLI tools:

### Component Creation
```bash
# Interactive creation
koios-component create

# Non-interactive with options
koios-component create --name "My Component" --category control --author "Me"

# Use specific template
koios-component create --template pid_controller --name "Advanced PID"
```

### Testing
```bash
# Test component
koios-component test ./my_component

# Test with verbose output
koios-component test ./my_component --verbose

# Test specific scenarios
koios-component test ./my_component --scenario startup
```

### Building
```bash
# Build component package
koios-component build ./my_component

# Build with custom output directory
koios-component build ./my_component --output ./packages

# Build with compression
koios-component build ./my_component --compress

# Build with dependency validation against runtime requirements
koios-component build ./my_component --runtime-requirements ./docs/runtime-available.txt
```

### Deployment

**Note**: The `deploy` command is only available for Koios instances that have the deployment feature enabled. For most Koios installations, component packages should be uploaded through the web interface.

#### Web Interface Upload (Recommended)

The Koios user interface provides a managed Package Upload process for uploading component packages:

![Components Dashboard](docs/images/components-dashboard.png)

To upload a component package:

1. Navigate to the **Components** section in the Koios web interface
2. Click the **"↑ Upload New Package"** button
3. Select your `.kcp` package file
4. The package will be validated and installed automatically

#### CLI Deployment (Advanced)

For Koios instances with CLI deployment enabled:

```bash
# Deploy to Koios server
koios-component deploy my_component-1.0.0.kcp --host https://koios.example.com

# Deploy with authentication
koios-component login --host koios.example.com --username admin
koios-component deploy my_component-1.0.0.kcp
```

**Note**: If the `deploy` command is not available or fails, use the web interface upload method instead.

### Development Mode
```bash
# Development mode with auto-rebuild
koios-component dev ./my_component --watch

# Development server with testing
koios-component dev ./my_component --watch --test
```

## 📋 Component Structure

A typical component directory structure:

```
my_component/
├── koios_component.json    # Component metadata and configuration
├── component.py           # Main component implementation
├── README.md             # Component documentation
├── requirements.txt      # Python dependencies
├── tests/               # Component tests
│   ├── __init__.py
│   ├── test_component.py
│   └── test_integration.py
└── examples/            # Usage examples
    └── basic_usage.py
```

### Component Manifest (`koios_component.json`)

```json
{
  "name": "My PID Controller",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Advanced PID controller with anti-windup",
  "category": "control",
  "koios_version_min": "1.0.0",
  "entry_point": "component.MyPIDController",
  "dependencies": [
    "numpy>=1.20.0",
    "scipy>=1.7.0"
  ],
  "parameters": {
    "kp": {
      "type": "float",
      "description": "Proportional gain",
      "required": true,
      "default": 1.0,
      "validation": {"minimum": 0.0}
    },
    "ki": {
      "type": "float",
      "description": "Integral gain", 
      "required": true,
      "default": 0.1,
      "validation": {"minimum": 0.0}
    }
  },
  "tags": ["pid", "control", "advanced"],
  "license": "MIT"
}
```

## 🧪 Testing Framework

The SDK includes a comprehensive testing framework with mock Koios environment:

```python
from koios_component_sdk.testing import MockKoiosEnvironment, TestResult

def test_my_component():
    # Create mock environment
    mock_env = MockKoiosEnvironment()
    
    # Create mock tags
    setpoint_tag = mock_env.create_tag("setpoint", 50.0)
    pv_tag = mock_env.create_tag("process_variable", 45.0)
    output_tag = mock_env.create_tag("output", 0.0)
    
    # Test component
    component = MyPIDController("test_pid", {
        "kp": 1.0,
        "ki": 0.1,
        "kd": 0.01
    })
    
    # Run test sequence
    result = mock_env.test_component(component)
    
    assert result.success
    assert len(result.errors) == 0
```

## 📚 Examples

The SDK includes comprehensive examples for each component type:

- **PID Controller**: Advanced PID with anti-windup and gain scheduling
- **Modbus Protocol**: Custom Modbus TCP implementation
- **Data Filter**: Moving average and outlier detection
- **State Machine**: Traffic light controller logic
- **Fuzzy Controller**: Temperature control with fuzzy logic

Access examples:
```bash
koios-component examples --category control
koios-component examples --list-all
```

## 🌐 Runtime Environment

Components execute in a controlled runtime environment with pre-installed packages. Understanding what's available helps you build components that work seamlessly.

### Available Packages

The runtime environment includes a curated set of public Python packages. See [`docs/runtime-available.txt`](docs/runtime-available.txt) for the complete list with version ranges.

**Key packages include:**
- **Async & Networking**: `aiohttp`, `httpx`, `anyio`
- **Database**: `SQLAlchemy`, `psycopg` (PostgreSQL)
- **Utilities**: `python-dateutil`, `pytz`, `python-dotenv`
- **Data Structures**: `sortedcontainers`, `multidict`
- **And more...**

### SDK Library

The **`koios_component_sdk`** library is part of the SDK itself and is automatically available to all components. It provides base classes, decorators, and utilities for component development.

### Standard Library

All Python standard library modules are available (`os`, `sys`, `json`, `logging`, `datetime`, `asyncio`, etc.).

### Dependency Validation

When building components, you can validate imports against available runtime packages:

```bash
koios-component build ./my_component --runtime-requirements ./docs/runtime-available.txt
```

This will:
- ✅ Check that all imports are available in the runtime
- ⚠️ Warn about dependencies declared but not in runtime-available.txt
- ❌ Error on imports that aren't available and not declared

### Adding New Packages

**⚠️ Important**: If your component requires a public library that's not in `runtime-available.txt`, you must submit a **formal approval request** before deployment.

**Approval Process:**

1. **Check Availability**: First verify the package isn't already available or can't be replaced with an existing package
2. **Submit Request**: Submit a formal request including:
   - Package name and version requirement
   - Justification for why it's needed
   - Security and compatibility assessment
   - Alternative solutions considered
3. **Review**: The request will be reviewed for:
   - Security implications
   - Compatibility with existing packages
   - Maintenance burden
   - Alignment with platform goals
4. **Approval**: If approved, the package will be added to the runtime environment
5. **Update**: The `runtime-available.txt` file will be updated accordingly

**Note**: Components using unapproved packages will fail validation and cannot be deployed until approval is granted and the package is added to the runtime.

### Best Practices

1. **Use Available Packages**: Prefer packages already in `runtime-available.txt`
2. **Declare Dependencies**: Always declare dependencies in `koios_component.json`
3. **Validate Early**: Run dependency validation during development
4. **Plan Ahead**: Submit approval requests well before deployment deadlines
5. **Document Usage**: Explain why specific packages are needed in your component README

## 🔧 Advanced Features

### Custom Parameter Types
```python
from koios_component_sdk.base.component import ParameterDefinition

# Complex parameter with validation
ParameterDefinition(
    name="temperature_range",
    type="json",
    description="Temperature operating range",
    validation={
        "type": "object",
        "properties": {
            "min": {"type": "number", "minimum": -50},
            "max": {"type": "number", "maximum": 200}
        },
        "required": ["min", "max"]
    }
)
```

### Async Support
```python
from koios_component_sdk.base import ProtocolComponent

class AsyncProtocol(ProtocolComponent):
    async def read_multiple_tags(self, addresses: List[str]) -> Dict[str, Any]:
        # Implement async batch reading
        results = {}
        for address in addresses:
            results[address] = await self.read_tag_async(address)
        return results
```

### State Management
```python
from koios_component_sdk.base.logic import LogicComponent, LogicState

class StateMachine(LogicComponent):
    def evaluate_conditions(self) -> Dict[str, bool]:
        return {
            "start_condition": self.get_input("start_button", False),
            "stop_condition": self.get_input("stop_button", False),
            "error_condition": self.get_input("error_signal", False)
        }
    
    def execute_logic(self) -> Dict[str, Any]:
        conditions = self.conditions
        
        if conditions["error_condition"]:
            self.set_logic_state(LogicState.ERROR)
        elif conditions["start_condition"] and self.logic_state == LogicState.IDLE:
            self.set_logic_state(LogicState.ACTIVE)
        elif conditions["stop_condition"]:
            self.set_logic_state(LogicState.IDLE)
        
        return {
            "running": self.logic_state == LogicState.ACTIVE,
            "error": self.logic_state == LogicState.ERROR
        }
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/ai-ops/koios-component-sdk.git
cd koios-component-sdk
pip install -e .[dev]
pre-commit install
```

### Running Tests

```bash
pytest
pytest --cov=koios_component_sdk
pytest -m "not slow"  # Skip slow tests
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Documentation](https://docs.ai-op.com)
- 🐛 [Issue Tracker](https://github.com/ai-ops/koios-component-sdk/issues)
- 💬 [Community Forum](https://community.ai-op.com)
- 📧 [Email Support](mailto:support@ai-op.com)

## 🗺️ Roadmap

- [ ] Visual component designer
- [ ] Real-time debugging tools
- [ ] Component marketplace integration
- [ ] Advanced simulation capabilities
- [ ] Multi-language support (C++, C#)
- [ ] Cloud deployment options

---

**Made with ❤️ by [Ai-OPs, Inc.](https://ai-op.com)**
