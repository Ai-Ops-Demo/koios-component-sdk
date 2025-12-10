"""
Base classes for Koios components.

This module provides the foundational classes that all Koios components inherit from.
These base classes define the common interface and behavior expected by the Koios
framework, ensuring consistent integration and management.
"""

from .component import (
    BaseKoiosComponent,
    ComponentMetadata,
    ParameterDefinition,
    ComponentCategory,
)
from .controller import ControllerComponent
from .protocol import ProtocolComponent
from .processor import ProcessorComponent
from .logic import LogicComponent

__all__ = [
    "BaseKoiosComponent",
    "ComponentMetadata",
    "ParameterDefinition", 
    "ComponentCategory",
    "ControllerComponent",
    "ProtocolComponent",
    "ProcessorComponent",
    "LogicComponent",
]
