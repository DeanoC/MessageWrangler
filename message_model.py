"""
Message Model

This module defines the intermediate representation for message definitions.
It provides classes for representing messages, fields, enums, namespaces, and other components
of the message definition format.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum


class FieldType(Enum):
    """Enumeration of supported field types."""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    BYTE = "byte"
    ENUM = "enum"
    COMPOUND = "compound"
    OPTIONS = "options"
    MESSAGE = "message"  # Reference to another message


class Namespace:
    """Represents a namespace containing messages."""

    def __init__(self, name: str, description: str = "", comment: str = ""):
        """
        Initialize a namespace.

        Args:
            name: The name of the namespace
            description: Optional description of the namespace
            comment: Optional user-supplied comment for the namespace
        """
        self.name = name
        self.description = description
        self.comment = comment
        self.messages: Dict[str, Message] = {}


class EnumValue:
    """Represents a value in an enumeration."""

    def __init__(self, name: str, value: int):
        """
        Initialize an enum value.

        Args:
            name: The name of the enum value
            value: The numeric value of the enum value
        """
        self.name = name
        self.value = value


class EnumField:
    """Represents an enumeration field."""

    def __init__(self, name: str, values: List[EnumValue]):
        """
        Initialize an enum field.

        Args:
            name: The name of the enum field
            values: The list of enum values
        """
        self.name = name
        self.values = values


class CompoundField:
    """Represents a compound field with multiple components."""

    def __init__(self, name: str, base_type: str, components: List[str]):
        """
        Initialize a compound field.

        Args:
            name: The name of the compound field
            base_type: The base type of the compound field (e.g., "float")
            components: The list of component names
        """
        self.name = name
        self.base_type = base_type
        self.components = components


class Field:
    """Represents a field in a message."""

    def __init__(self, name: str, field_type: FieldType, description: str = "", comment: str = "", optional: bool = False, default_value: Any = None):
        """
        Initialize a field.

        Args:
            name: The name of the field
            field_type: The type of the field
            description: Optional description of the field
            comment: Optional user-supplied comment for the field
            optional: Whether the field is optional (can be omitted)
            default_value: Optional default value for the field
        """
        self.name = name
        self.field_type = field_type
        self.description = description
        self.comment = comment
        self.optional = optional
        self.default_value = default_value
        self.default_value_str: Optional[str] = None  # Original string representation of default value for options
        self.enum_values: List[EnumValue] = []
        self.compound_base_type: str = ""
        self.compound_components: List[str] = []
        self.enum_reference: Optional[str] = None  # Reference to an enum in another message
        self.additional_enum_values: List[EnumValue] = []  # Additional enum values for extended enum references


class Message:
    """Represents a message definition."""

    def __init__(self, name: str, parent: Optional[str] = None, namespace: Optional[str] = None, description: str = "", comment: str = "", source_file: Optional[str] = None):
        """
        Initialize a message.

        Args:
            name: The name of the message
            parent: Optional parent message name (for inheritance)
            namespace: Optional namespace name
            description: Optional description of the message
            comment: Optional user-supplied comment for the message
            source_file: Optional source file path where the message was defined
        """
        self.name = name
        self.parent = parent
        self.namespace = namespace
        self.description = description
        self.comment = comment
        self.source_file = source_file
        self.fields: List[Field] = []

    def get_full_name(self) -> str:
        """
        Get the fully qualified name of the message, including namespace.

        Returns:
            The fully qualified name of the message
        """
        if self.namespace:
            return f"{self.namespace}::{self.name}"
        return self.name


class Enum:
    """Represents a standalone enum definition."""

    def __init__(self, name: str, values: List[EnumValue], parent: Optional[str] = None, namespace: Optional[str] = None, description: str = "", comment: str = "", source_file: Optional[str] = None, is_open: bool = False):
        """
        Initialize a standalone enum.

        Args:
            name: The name of the enum
            values: The list of enum values
            parent: Optional parent enum name (for inheritance)
            namespace: Optional namespace name
            description: Optional description of the enum
            comment: Optional user-supplied comment for the enum
            source_file: Optional source file path where the enum was defined
            is_open: Whether the enum is an open enum
        """
        self.name = name
        self.values = values
        self.parent = parent
        self.namespace = namespace
        self.description = description
        self.comment = comment
        self.source_file = source_file
        self.is_open = is_open
        self._min_size_bits = None

    def get_full_name(self) -> str:
        """
        Get the fully qualified name of the enum, including namespace.

        Returns:
            The fully qualified name of the enum
        """
        if self.namespace:
            return f"{self.namespace}::{self.name}"
        return self.name

    def get_min_size_bits(self) -> int:
        """
        Get the minimum number of bits needed to represent all values in the enum.

        For closed enums, this is the smallest power of 2 that can hold the maximum value.
        For open enums, this defaults to 32 bits unless a value exceeds that range, then it uses 64 bits.

        Returns:
            The minimum number of bits (8, 16, 32, or 64)
        """
        if self._min_size_bits is not None:
            return self._min_size_bits

        # Find the maximum value in the enum
        max_value = 0
        for value in self.values:
            if value.value > max_value:
                max_value = value.value

        # For open enums, default to 32 bits unless a value exceeds that range
        if self.is_open:
            if max_value > 0xFFFFFFFF:  # 2^32 - 1
                self._min_size_bits = 64
            else:
                self._min_size_bits = 32
            return self._min_size_bits

        # For closed enums, find the smallest power of 2 that can hold the maximum value
        if max_value <= 0xFF:  # 2^8 - 1
            self._min_size_bits = 8
        elif max_value <= 0xFFFF:  # 2^16 - 1
            self._min_size_bits = 16
        elif max_value <= 0xFFFFFFFF:  # 2^32 - 1
            self._min_size_bits = 32
        else:
            self._min_size_bits = 64

        return self._min_size_bits


class MessageModel:
    """
    Represents the complete model of all message definitions.
    This is the intermediate representation that will be used
    for code generation.
    """

    def __init__(self):
        """Initialize an empty message model."""
        self.messages: Dict[str, Message] = {}
        self.namespaces: Dict[str, Namespace] = {}
        self.enums: Dict[str, Enum] = {}

    def add_message(self, message: Message) -> None:
        """
        Add a message to the model.

        Args:
            message: The message to add
        """
        # Add to global messages dictionary
        self.messages[message.get_full_name()] = message

        # If message has a namespace, add it to the namespace's messages
        if message.namespace:
            if message.namespace not in self.namespaces:
                self.namespaces[message.namespace] = Namespace(message.namespace)
            self.namespaces[message.namespace].messages[message.name] = message

    def add_namespace(self, namespace: Namespace) -> None:
        """
        Add a namespace to the model.

        Args:
            namespace: The namespace to add
        """
        self.namespaces[namespace.name] = namespace

    def get_message(self, name: str) -> Optional[Message]:
        """
        Get a message by name.

        Args:
            name: The name of the message to get (can be fully qualified or not)

        Returns:
            The message, or None if not found
        """
        # First try to get the message directly (assuming it's a fully qualified name)
        message = self.messages.get(name)
        if message:
            return message

        # If not found, try to parse as namespace::message
        if '::' in name:
            namespace_name, message_name = name.split('::', 1)
            namespace = self.namespaces.get(namespace_name)
            if namespace:
                return namespace.messages.get(message_name)

        # If still not found, try to find it in the global scope (no namespace)
        return self.messages.get(name)

    def get_namespace(self, name: str) -> Optional[Namespace]:
        """
        Get a namespace by name.

        Args:
            name: The name of the namespace to get

        Returns:
            The namespace, or None if not found
        """
        return self.namespaces.get(name)

    def add_enum(self, enum: Enum) -> None:
        """
        Add an enum to the model.

        Args:
            enum: The enum to add
        """
        # Add to global enums dictionary
        self.enums[enum.get_full_name()] = enum

        # If enum has a namespace, add it to the namespace
        if enum.namespace and enum.namespace in self.namespaces:
            if not hasattr(self.namespaces[enum.namespace], 'enums'):
                self.namespaces[enum.namespace].enums = {}
            self.namespaces[enum.namespace].enums[enum.name] = enum

    def get_enum(self, name: str) -> Optional[Enum]:
        """
        Get an enum by name.

        Args:
            name: The name of the enum to get (can be fully qualified or not)

        Returns:
            The enum, or None if not found
        """
        # First try to get the enum directly (assuming it's a fully qualified name)
        enum = self.enums.get(name)
        if enum:
            return enum

        # If not found, try to parse as namespace::enum
        if '::' in name:
            namespace_name, enum_name = name.split('::', 1)
            namespace = self.namespaces.get(namespace_name)
            if namespace and hasattr(namespace, 'enums'):
                return namespace.enums.get(enum_name)

        return None
