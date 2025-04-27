"""
Message Model

This module defines the intermediate representation for message definitions.
It provides classes for representing messages, fields, enums, and other components
of the message definition format.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum


class FieldType(Enum):
    """Enumeration of supported field types."""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    ENUM = "enum"
    COMPOUND = "compound"


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

    def __init__(self, name: str, field_type: FieldType, description: str = "", comment: str = ""):
        """
        Initialize a field.

        Args:
            name: The name of the field
            field_type: The type of the field
            description: Optional description of the field
            comment: Optional user-supplied comment for the field
        """
        self.name = name
        self.field_type = field_type
        self.description = description
        self.comment = comment
        self.enum_values: List[EnumValue] = []
        self.compound_base_type: str = ""
        self.compound_components: List[str] = []


class Message:
    """Represents a message definition."""

    def __init__(self, name: str, parent: Optional[str] = None, description: str = "", comment: str = ""):
        """
        Initialize a message.

        Args:
            name: The name of the message
            parent: Optional parent message name (for inheritance)
            description: Optional description of the message
            comment: Optional user-supplied comment for the message
        """
        self.name = name
        self.parent = parent
        self.description = description
        self.comment = comment
        self.fields: List[Field] = []


class MessageModel:
    """
    Represents the complete model of all message definitions.
    This is the intermediate representation that will be used
    for code generation.
    """

    def __init__(self):
        """Initialize an empty message model."""
        self.messages: Dict[str, Message] = {}

    def add_message(self, message: Message) -> None:
        """
        Add a message to the model.

        Args:
            message: The message to add
        """
        self.messages[message.name] = message

    def get_message(self, name: str) -> Optional[Message]:
        """
        Get a message by name.

        Args:
            name: The name of the message to get

        Returns:
            The message, or None if not found
        """
        return self.messages.get(name)
