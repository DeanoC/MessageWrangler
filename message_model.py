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
    BOOL = "bool"
    BOOLEAN = "boolean"  # Alias for BOOL, for compatibility
    BYTE = "byte"
    ENUM = "enum"
    COMPOUND = "compound"
    INLINE_COMPOUND = "inline_compound"
    OPTIONS = "options"
    MESSAGE_REFERENCE = "message_reference"
    INLINE_MESSAGE = "inline_message"
    INLINE_ENUM = "inline_enum"
    INLINE_OPTIONS = "inline_options"
    ARRAY = "array"
    MAP = "map"
    UNKNOWN = "unknown"


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

    def __init__(self, name: str, value: int, options: Dict[str, str] = None):
        """
        Initialize an enum value.

        Args:
            name: The name of the enum value
            value: The numeric value of the enum value
            options: Optional dictionary of options for the enum value
        """
        self.name = name
        self.value = value
        self.options = options if options is not None else {}


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

    def __init__(self, name: str, field_type: FieldType, description: str = "", comment: str = "", optional: bool = False, default_value: Any = None, default_value_str: Optional[str] = None, enum_values: List[EnumValue] = None, compound_base_type: str = "", compound_components: List[str] = None, enum_reference: Optional[str] = None, additional_enum_values: List[EnumValue] = None, message_reference: Optional[str] = None, inline_message: Optional['Message'] = None, inline_enum: Optional['Enum'] = None, compound_reference: Optional[str] = None, inline_compound: Optional[Any] = None, options_reference: Optional[str] = None, inline_options: Optional[Dict[str, str]] = None, is_array: bool = False, array_size: Optional[int] = None, is_map: bool = False, map_key_type: Optional[str] = None, map_value_type: Optional[str] = None, options: Dict[str, str] = None, source_file: Optional[str] = None, line_number: Optional[int] = None, type_name: Optional[str] = None, modifiers: Optional[list] = None):
        """
        Initialize a field.

        Args:
            name: The name of the field
            field_type: The type of the field
            description: Optional description of the field
            comment: Optional user-supplied comment for the field
            optional: Whether the field is optional (can be omitted)
            default_value: Optional default value for the field
            default_value_str: Original string representation of default value for options
            enum_values: List of enum values for inline enum fields
            compound_base_type: Base type for compound fields
            compound_components: List of component names for compound fields
            enum_reference: Reference to an enum
            additional_enum_values: Additional enum values for extended enum references
            message_reference: Reference to a message
            inline_message: Inline message definition
            inline_enum: Inline enum definition
            compound_reference: Reference to a compound type
            inline_compound: Inline compound definition
            options_reference: Reference to options
            inline_options: Inline options definition
            is_array: Whether the field is an array
            array_size: Size of the array (if fixed-size)
            is_map: Whether the field is a map
            map_key_type: Key type for the map
            options: Dictionary of options for the field
            source_file: Source file where the field was defined
            line_number: Line number where the field was defined
            type_name: Original type name for unresolved references
            modifiers: List of field modifiers (e.g., ['optional', 'repeated'])
        """
        self.name = name
        self.field_type = field_type
        self.description = description
        self.comment = comment
        self.optional = optional
        self.default_value = default_value
        self.default_value_str = default_value_str
        self.enum_values = enum_values if enum_values is not None else []
        self.compound_base_type = compound_base_type
        self.compound_components = compound_components if compound_components is not None else []
        self.enum_reference = enum_reference
        self.additional_enum_values = additional_enum_values if additional_enum_values is not None else []
        self.message_reference = message_reference
        self.message: Optional[Message] = None # Resolved message object
        self.inline_message = inline_message
        self.inline_enum = inline_enum
        self.compound_reference = compound_reference
        self.inline_compound = inline_compound
        self.options_reference = options_reference
        self.options_obj: Optional[Dict[str, str]] = None # Resolved options object
        self.inline_options = inline_options
        self.is_array = is_array
        self.array_size = array_size
        self.is_map = is_map
        self.map_key_type = map_key_type
        self.map_value_type = map_value_type
        self.options = options if options is not None else {}
        self.source_file = source_file
        self.line_number = line_number
        self.type_name = type_name

        # --- PATCH: Add enum_type and options_type for generator compatibility ---
        self.enum_type = None  # Name of the enum type for enum fields
        self.options_type = None  # Name of the options type for options fields
        self.enum = None  # Resolved enum object

        self.modifiers = modifiers if modifiers is not None else []


class Message:
    """Represents a message definition."""

    def __init__(self, name: str, parent: Optional[str] = None, namespace: Optional[str] = None, description: str = "", comment: str = "", source_file: Optional[str] = None, line_number: Optional[int] = None):
        """
        Initialize a message.

        Args:
            name: The name of the message
            parent: Optional parent message name (for inheritance)
            namespace: Optional namespace name
            description: Optional description of the message
            comment: Optional user-supplied comment for the message
            source_file: Optional source file path where the message was defined
            line_number: Optional line number where the message was defined
        """
        self.name = name
        self.parent = parent
        self.parent_message: Optional[Message] = None # Resolved parent message object
        self.namespace = namespace
        self.description = description
        self.comment = comment
        self.source_file = source_file
        self.line_number = line_number
        self.fields: List[Field] = []
        self.inline_enums: Dict[str, Enum] = {} # Store inline enums keyed by name
        self.options: Dict[str, str] = {} # Store message options

    def add_field(self, field: Field) -> None:
        """
        Add a field to the message.

        Args:
            field: The field to add
        """
        self.fields.append(field)
        # Register inline enums for reference resolution, regardless of field_type
        if field.inline_enum is not None:
            self.inline_enums[field.inline_enum.name] = field.inline_enum


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
    def get_all_values(self) -> List['EnumValue']:
        """
        Get all enum values, including inherited values from parent enums (if any).
        Child values override parent values with the same name.
        """
        values_by_name = {}
        # Recursively add parent values first
        if self.parent_enum:
            for v in self.parent_enum.get_all_values():
                values_by_name[v.name] = v
        # Add/override with own values
        for v in self.values:
            values_by_name[v.name] = v
        return list(values_by_name.values())
    """Represents a standalone enum definition."""

    def __init__(self, name: str, values: List[EnumValue], parent: Optional[str] = None, namespace: Optional[str] = None, description: str = "", comment: str = "", source_file: Optional[str] = None, is_open: bool = False, line_number: Optional[int] = None):
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
            line_number: Optional line number where the enum was defined
        """
        self.name = name
        self.values = values
        self.parent = parent
        self.parent_enum: Optional[Enum] = None # Resolved parent enum object
        self.namespace = namespace
        self.description = description
        self.comment = comment
        self.source_file = source_file
        self.is_open = is_open
        self.line_number = line_number
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
        self.options: Dict[str, Dict[str, str]] = {} # Store standalone options keyed by name
        self.imports: Dict[str, str] = {} # Stores import alias -> resolved file path
        self.main_file_path: Optional[str] = None # NEW: Stores the path of the main file being parsed

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
        name = name.strip()  # <-- Strip whitespace
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
        message = self.messages.get(name)
        if message:
            return message

        # If still not found, try to find it by simple name in any namespace
        for namespace in self.namespaces.values():
            message = namespace.messages.get(name)
            if message:
                return message

        return None

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
        if enum.namespace:
            if enum.namespace not in self.namespaces:
                self.namespaces[enum.namespace] = Namespace(enum.namespace)
            namespace = self.namespaces[enum.namespace]
            if not hasattr(namespace, 'enums'):
                namespace.enums = {}
            namespace.enums[enum.name] = enum

    def get_enum(self, name: str) -> Optional[Enum]:
        """
        Get an enum by name.

        Args:
            name: The name of the enum to get (can be fully qualified or not)

        Returns:
            The enum, or None if not found
        """
        name = name.strip()  # <-- Strip whitespace
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

    def add_options(self, name: str, options: Dict[str, str], namespace: Optional[str] = None) -> None:
        """
        Add standalone options to the model.

        Args:
            name: The name of the options
            options: The dictionary of options
            namespace: Optional namespace name
        """
        full_name = f"{namespace}::{name}" if namespace else name
        self.options[full_name] = options

        # If options have a namespace, add it to the namespace
        if namespace and namespace in self.namespaces:
            if not hasattr(self.namespaces[namespace], 'options'):
                self.namespaces[namespace].options = {}
            self.namespaces[namespace].options[name] = options


    def get_options(self, name: str) -> Optional[Dict[str, str]]:
        """
        Get standalone options by name.

        Args:
            name: The name of the options to get (can be fully qualified or not)

        Returns:
            The options dictionary, or None if not found
        """
        # First try to get the options directly (assuming it's a fully qualified name)
        options = self.options.get(name)
        if options:
            return options

        # If not found, try to parse as namespace::options
        if '::' in name:
            namespace_name, options_name = name.split('::', 1)
            namespace = self.namespaces.get(namespace_name)
            if namespace and hasattr(namespace, 'options'):
                return namespace.options.get(options_name)

        return None
