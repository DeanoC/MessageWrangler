"""
Python Generator

This module provides functionality for generating Python code from the
intermediate representation defined in message_model.py.
It generates Python 3 code with classes for each message type.
It should NEVER have any specific code to handle troublesome cases.

"""

import os
from typing import TextIO
from enum import Enum, IntEnum, IntFlag

from message_model import (
    FieldType,
    Field,
    Message,
    MessageModel,
    Enum as ModelEnum
)


class PythonGenerator:
    """
    Generator for Python code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str, output_name: str = None):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
            output_name: Base name for output files without extension (default: "messages")
        """
        self.model = model
        self.output_dir = output_dir
        self.output_name = output_name if output_name else "messages"

    def _to_cap_words(self, name: str) -> str:
        """
        Convert a name from underscore format to CapWords format.

        Args:
            name: The name to convert

        Returns:
            The name in CapWords format
        """
        # Replace :: with _ first (for namespaced names)
        name = name.replace("::", "_")
        # Split by underscore and capitalize each part
        parts = name.split('_')
        # Join the capitalized parts
        return ''.join(part.capitalize() for part in parts)

    def generate(self) -> bool:
        """
        Generate Python code from the message model.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating Python output in: {self.output_dir}")

            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)

            # Group messages by source file
            messages_by_source = {}
            main_file = None

            for message_name, message in self.model.messages.items():
                source_file = message.source_file
                if source_file is None:
                    # If source_file is None, treat it as part of the main file
                    if main_file is None:
                        # Use the output name as the main file if we don't have a source file
                        main_file = self.output_name
                    source_file = main_file

                if source_file not in messages_by_source:
                    messages_by_source[source_file] = []
                messages_by_source[source_file].append(message)

            # If we don't have a main file yet, use the output name
            if main_file is None:
                main_file = self.output_name

            # Track generated files for import statements
            generated_files = {}

            # Generate a separate file for each source file
            for source_file, messages in messages_by_source.items():
                # Create a filename based on the source file
                base_name = os.path.splitext(os.path.basename(source_file))[0]

                # For the main file, use the output name
                if source_file == main_file:
                    output_base_name = self.output_name
                else:
                    output_base_name = base_name

                py_file = os.path.join(self.output_dir, f"{output_base_name}_msgs.py")
                generated_files[source_file] = py_file

                # Create a filtered model with only the messages from this source file
                filtered_model = MessageModel()
                for message in messages:
                    filtered_model.add_message(message)

                # Add standalone enums to the filtered model
                for enum_name, enum in self.model.enums.items():
                    filtered_model.add_enum(enum)

                # Generate the Python file
                with open(py_file, 'w') as f:
                    self._write_header(f)
                    self._write_imports(f)

                    # Add import statements for parent messages that are in other files
                    self._write_file_imports(f, messages, messages_by_source, generated_files)

                    # Write enums and classes for this file only
                    self._write_enums(f, filtered_model)
                    self._write_classes(f, filtered_model)

                    # Only write serialization utils in the main file
                    if source_file == main_file:
                        self._write_serialization_utils(f)

                print(f"Generated Python file: {py_file}")

            return True

        except Exception as e:
            print(f"Error generating Python output: {str(e)}")
            return False

    def _write_header(self, f: TextIO) -> None:
        """
        Write the header section of the Python file.

        Args:
            f: The file to write to
        """
        f.write("# Auto-generated message definitions for Python\n")
        f.write("# This file contains message definitions for communication between systems.\n")
        f.write("#\n")
        f.write("# DOCUMENTATION FOR MESSAGE FORMAT:\n")
        f.write("# ===============================\n")
        f.write("# This file defines a set of message classes used for communication.\n")
        f.write("# Each message is defined as a Python class.\n")
        f.write("#\n")
        f.write("# Message Structure:\n")
        f.write("# - Messages are defined as classes with specific fields\n")
        f.write("# - Messages can inherit from other messages using standard Python inheritance\n")
        f.write("# - Messages can be organized into namespaces for logical grouping\n")
        f.write("# - Fields can be of the following types:\n")
        f.write("#   * Basic types: int, float, str, bool, int (0-255 for byte)\n")
        f.write("#   * Enum types: defined as Python Enum classes\n")
        f.write("#   * Options types: defined as Python IntFlag classes, can be combined with bitwise OR\n")
        f.write("#   * Compound types: dataclasses with named components\n")
        f.write("#\n")
        f.write("# Field Modifiers:\n")
        f.write("# - Optional fields: Fields that can be omitted from messages (using Optional type hint)\n")
        f.write("# - Default values: Fields can have default values that are used when not explicitly set\n")
        f.write("#\n")
        f.write("# Enum Naming Convention:\n")
        f.write("# - Enums are named as MessageName_fieldName_Enum\n")
        f.write("#\n")
        f.write("# Options Naming Convention:\n")
        f.write("# - Options are named as MessageName_fieldName_Options\n")
        f.write("# - Options are bit flags that can be combined using the bitwise OR operator (|)\n")
        f.write("#\n")
        f.write("# Compound Field Structure:\n")
        f.write("# - Compound fields are defined as dataclasses\n")
        f.write("# - Each component is a named field within the dataclass\n")
        f.write("# - Currently supports float compounds with named components (e.g., position with x, y, z)\n")
        f.write("#\n")
        f.write("# JSON Serialization:\n")
        f.write("# ================\n")
        f.write("# The MessageSerialization class provides utility functions for working with messages:\n")
        f.write("# - serialize(): Serializes a message to a JSON string with message type\n")
        f.write("# - deserialize(): Deserializes a JSON string to a message object\n")
        f.write("# - deserialize_as(): Deserializes a JSON string to a specific message type\n")
        f.write("# - validate_message(): Validates that an object conforms to a specific message type\n")
        f.write("# - create_default(): Creates a new instance of a message with default values\n")
        f.write("#\n")
        f.write("# Message Envelope Structure:\n")
        f.write("# ========================\n")
        f.write("# Messages are serialized with an envelope structure that includes:\n")
        f.write("# - messageType: The type of the message, which matches the name of the message definition\n")
        f.write("# - payload: The actual message data as a JSON object\n")
        f.write("# Example: {\"messageType\": \"MyMessage\", \"payload\": {\"field1\": \"value1\", \"field2\": 42}}\n")
        f.write("#\n")
        f.write("# HOW TO GENERATE A READER:\n")
        f.write("# =====================\n")
        f.write("# To create a reader for these messages:\n")
        f.write("# 1. Create a parser that can deserialize JSON data into these classes\n")
        f.write("# 2. For each message type, implement a handler function\n")
        f.write("# 3. Use a dispatcher to route messages to the appropriate handler based on message type\n")
        f.write("# 4. For inheritance, ensure parent fields are processed before child fields\n")
        f.write("#\n\n")

    def _write_imports(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write the import statements for the Python file.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        f.write("import json\n")
        f.write("import dataclasses\n")
        f.write("from dataclasses import dataclass, field\n")

        # Check if we need to import IntFlag (only if there are options types)
        has_options = False
        # Check if we need to import Optional (only if there are optional fields)
        has_optional_fields = False

        for message in model.messages.values():
            for field in message.fields:
                if field.field_type == FieldType.OPTIONS:
                    has_options = True
                if field.optional:
                    has_optional_fields = True
                if has_options and has_optional_fields:
                    break
            if has_options and has_optional_fields:
                break

        if has_options:
            f.write("from enum import Enum, IntFlag\n")
        else:
            f.write("from enum import Enum\n")

        if has_optional_fields:
            f.write("from typing import Dict, Any, Type, cast, Optional\n\n")
        else:
            f.write("from typing import Dict, Any, Type, cast\n\n")

    def _write_file_imports(self, f: TextIO, messages: list, messages_by_source: dict, generated_files: dict) -> None:
        """
        Write import statements for parent messages that are in other files.

        Args:
            f: The file to write to
            messages: List of messages in the current file
            messages_by_source: Dictionary mapping source files to lists of messages
            generated_files: Dictionary mapping source files to generated Python files
        """
        # Track needed imports
        needed_imports = set()

        # Check each message for parent references to messages in other files
        for message in messages:
            if message.parent:
                # Find the parent message
                parent_message = None
                for source_file, source_messages in messages_by_source.items():
                    for source_message in source_messages:
                        if source_message.get_full_name() == message.parent:
                            parent_message = source_message
                            break
                    if parent_message:
                        break

                # If parent is in a different file, add an import
                if parent_message and parent_message.source_file != message.source_file:
                    parent_source = parent_message.source_file
                    if parent_source in generated_files:
                        # Get the module name from the generated file path
                        parent_module = os.path.splitext(os.path.basename(generated_files[parent_source]))[0]
                        needed_imports.add(parent_module)

        # Write import statements
        for module in sorted(needed_imports):
            f.write(f"from {module} import *\n")

        if needed_imports:
            f.write("\n")

    def _write_enums(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write enum definitions.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        enums_generated = set()

        # Write standalone enums
        for enum_name, enum in model.enums.items():
            py_enum_name_part = enum_name.replace("::", "_")
            # Create CapWords version for class name
            py_enum_name = self._to_cap_words(py_enum_name_part)
            if py_enum_name_part not in enums_generated:
                if enum.is_open:
                    f.write(f"class {py_enum_name}(IntEnum):\n")
                else:
                    f.write(f"class {py_enum_name}(Enum):\n")
                f.write(f"    \"\"\"Standalone enum {enum_name}\"\"\"\n")
                if enum.comment:
                    comment_lines = enum.comment.split('\n')
                    for line in comment_lines:
                        f.write(f"    # {line}\n")
                for enum_value in enum.values:
                    f.write(f"    {enum_value.name} = {enum_value.value}\n")
                f.write("\n")
                enums_generated.add(py_enum_name_part)

        # Write enums for message fields
        for message_name, message in model.messages.items():
            py_message_name_part = message_name.replace("::", "_")
            for field in message.fields:
                if field.field_type == FieldType.ENUM:
                    # Create underscore version for tracking duplicates
                    enum_name_underscore = f"{py_message_name_part}_{field.name}_Enum"
                    # Create CapWords version for class name
                    enum_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Enum")
                    if enum_name_underscore not in enums_generated:
                        f.write(f"class {enum_name}(Enum):\n")
                        f.write(f"    \"\"\"Enum for {message_name}.{field.name}\"\"\"\n")
                        for enum_value in field.enum_values:
                            f.write(f"    {enum_value.name} = {enum_value.value}\n")
                        f.write("\n")
                        enums_generated.add(enum_name_underscore)
                elif field.field_type == FieldType.OPTIONS:
                    # Create underscore version for tracking duplicates
                    enum_name_underscore = f"{py_message_name_part}_{field.name}_Options"
                    # Create CapWords version for class name
                    enum_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Options")
                    if enum_name_underscore not in enums_generated:
                        f.write(f"class {enum_name}(IntFlag):\n")
                        f.write(f"    \"\"\"Options for {message_name}.{field.name}\"\"\"\n")
                        for enum_value in field.enum_values:
                            f.write(f"    {enum_value.name} = {enum_value.value}\n")
                        f.write("\n")
                        enums_generated.add(enum_name_underscore)

    def _write_classes(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write class definitions.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        # First, write any compound field dataclasses
        compound_classes = set()
        for message_name, message in model.messages.items():
            py_message_name_part = message_name.replace("::", "_")
            for field in message.fields:
                if field.field_type == FieldType.COMPOUND:
                    # Create underscore version for tracking duplicates
                    compound_class_name_underscore = f"{py_message_name_part}_{field.name}_Compound"
                    # Create CapWords version for class name
                    compound_class_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Compound")
                    if compound_class_name_underscore not in compound_classes and field.compound_base_type == "float":
                        f.write(f"@dataclass\n")
                        f.write(f"class {compound_class_name}:\n")
                        f.write(f"    \"\"\"Compound type for {message_name}.{field.name}\"\"\"\n")
                        for component in field.compound_components:
                            f.write(f"    {component}: float = 0.0\n")
                        f.write("\n")
                        compound_classes.add(compound_class_name_underscore)

        # Now write the message classes
        for message_name, message in model.messages.items():
            # Create CapWords version for class name
            py_class_name = self._to_cap_words(message_name)
            parent_class_name = self._to_cap_words(message.parent) if message.parent else None

            # Write class docstring
            f.write(f"@dataclass\n")
            if parent_class_name:
                f.write(f"class {py_class_name}({parent_class_name}):\n")
            else:
                f.write(f"class {py_class_name}:\n")

            f.write(f"    \"\"\"{message.description if message.description else f'Message definition for {message_name}'}\n")
            if message.comment:
                comment_lines = message.comment.split('\n')
                for line in comment_lines:
                    f.write(f"    {line}\n")
            f.write(f"    \"\"\"\n")

            # If there are no fields and this is a child class, we still need to define the class
            if not message.fields and parent_class_name:
                f.write(f"    pass\n\n")
                continue

            # Write fields
            for field in message.fields:
                self._write_field(f, message_name, field)

            # Add to_dict and from_dict methods
            self._write_to_dict_method(f, message_name, message)
            self._write_from_dict_method(f, message_name, message)

            f.write("\n")

    def _write_field(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write a field definition.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to write
        """
        py_message_name_part = message_name.replace("::", "_")
        field_type = self._get_python_type(field, py_message_name_part)

        # Add field docstring
        if field.comment or field.description:
            comment = field.comment if field.comment else field.description
            # Split the comment by newlines and add # prefix to each line
            comment_lines = comment.split('\n')
            for line in comment_lines:
                f.write(f"    # {line}\n")

        # Handle optional fields
        if field.optional:
            field_type = f"Optional[{field_type}]"

        # Handle default values
        if field.default_value is not None:
            default_value = self._format_default_value(field, py_message_name_part)
            f.write(f"    {field.name}: {field_type} = {default_value}\n")
        else:
            # For required fields with no default, use field(default=...) for compound types
            if field.field_type == FieldType.COMPOUND:
                compound_class_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Compound")
                f.write(f"    {field.name}: {field_type} = field(default_factory={compound_class_name})\n")
            elif field.optional:
                f.write(f"    {field.name}: {field_type} = None\n")
            else:
                # Use appropriate default values for basic types
                if field.field_type == FieldType.STRING:
                    f.write(f"    {field.name}: {field_type} = \"\"\n")
                elif field.field_type == FieldType.INT or field.field_type == FieldType.BYTE:
                    f.write(f"    {field.name}: {field_type} = 0\n")
                elif field.field_type == FieldType.FLOAT:
                    f.write(f"    {field.name}: {field_type} = 0.0\n")
                elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
                    f.write(f"    {field.name}: {field_type} = False\n")
                elif field.field_type == FieldType.ENUM:
                    enum_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Enum")
                    # Use the first enum value as default
                    if field.enum_values and len(field.enum_values) > 0:
                        first_value = field.enum_values[0].name
                        f.write(f"    {field.name}: {field_type} = {enum_name}.{first_value}\n")
                    else:
                        f.write(f"    {field.name}: {field_type} = None  # No enum values defined\n")
                elif field.field_type == FieldType.OPTIONS:
                    f.write(f"    {field.name}: {field_type} = 0\n")
                else:
                    f.write(f"    {field.name}: {field_type} = None  # Unknown type\n")

    def _get_python_type(self, field: Field, message_name: str) -> str:
        """
        Get the Python type for a field.

        Args:
            field: The field to get the type for
            message_name: The Python-friendly name of the message containing the field

        Returns:
            The Python type as a string
        """
        if field.field_type == FieldType.ENUM:
            enum_name = self._to_cap_words(f"{message_name}_{field.name}_Enum")
            return enum_name

        elif field.field_type == FieldType.OPTIONS:
            enum_name = self._to_cap_words(f"{message_name}_{field.name}_Options")
            return enum_name

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                compound_class_name = self._to_cap_words(f"{message_name}_{field.name}_Compound")
                return compound_class_name
            else:
                return "dict"

        elif field.field_type == FieldType.STRING:
            return "str"

        elif field.field_type == FieldType.INT or field.field_type == FieldType.BYTE:
            return "int"

        elif field.field_type == FieldType.FLOAT:
            return "float"

        elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
            return "bool"

        else:
            return "Any"

    def _format_default_value(self, field: Field, message_name: str) -> str:
        """
        Format a default value for a field.

        Args:
            field: The field to format the default value for
            message_name: The Python-friendly name of the message containing the field

        Returns:
            The formatted default value as a string
        """
        if field.field_type == FieldType.ENUM:
            enum_name = self._to_cap_words(f"{message_name}_{field.name}_Enum")
            return f"{enum_name}.{field.default_value}"

        elif field.field_type == FieldType.OPTIONS:
            enum_name = self._to_cap_words(f"{message_name}_{field.name}_Options")
            # For combined options, use the OR'ed enum values
            if field.default_value_str and '&' in field.default_value_str:
                option_names = [opt.strip() for opt in field.default_value_str.split('&')]
                or_expression = " | ".join([f"{enum_name}.{name}" for name in option_names])
                return or_expression
            elif field.default_value_str and not field.default_value_str.isdigit():
                return f"{enum_name}.{field.default_value_str}"
            else:
                return str(field.default_value)

        elif field.field_type == FieldType.COMPOUND:
            compound_class_name = self._to_cap_words(f"{message_name}_{field.name}_Compound")
            # For compound fields, create a new instance with default values
            return f"field(default_factory={compound_class_name})"

        elif field.field_type == FieldType.STRING:
            # Escape quotes in string default values
            default_value = field.default_value
            if isinstance(default_value, str) and default_value.startswith('"') and default_value.endswith('"'):
                default_value = default_value[1:-1]
            return f"\"{default_value}\""

        elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
            return "True" if field.default_value else "False"

        else:
            # For numbers, etc.
            return str(field.default_value)

    def _write_to_dict_method(self, f: TextIO, message_name: str, message: Message) -> None:
        """
        Write the to_dict method for a message class.

        Args:
            f: The file to write to
            message_name: The name of the message
            message: The message object
        """
        f.write("\n    def to_dict(self) -> dict:\n")
        f.write("        \"\"\"Convert this message to a dictionary.\n\n")
        f.write("        Returns:\n")
        f.write("            dict: Dictionary representation of this message\n")
        f.write("        \"\"\"\n")

        # If this message inherits from another, we need to handle parent fields
        if message.parent:
            f.write("        # Call parent class serialization\n")
            f.write("        parent_dict = super().to_dict()\n")

            # Create a dictionary with this message's fields
            if message.fields:
                f.write("        # Create dictionary with this message's fields\n")
                f.write("        result = {\n")

                # Add each field to the dictionary literal
                for field in message.fields:
                    self._write_field_serialization_literal(f, message_name, field)

                f.write("        }\n")
                f.write("        # Update with parent fields\n")
                f.write("        result.update(parent_dict)\n")
            else:
                # If no fields in this message, just use parent's dictionary
                f.write("        result = parent_dict\n")
        else:
            # No inheritance, create a dictionary literal with all fields
            if message.fields:
                f.write("        result = {\n")

                # Add each field to the dictionary literal
                for field in message.fields:
                    self._write_field_serialization_literal(f, message_name, field)

                f.write("        }\n")
            else:
                # No fields, return empty dictionary
                f.write("        result = {}\n")

        f.write("        return result\n")

    def _write_field_serialization_literal(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write code to serialize a field for inclusion in a dictionary literal.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to serialize
        """
        # For optional fields, we need to handle them differently
        if field.optional:
            # We need to check if the field is None before including it
            f.write(f"            \"{field.name}\": ")

            if field.field_type == FieldType.ENUM:
                f.write(f"self.{field.name}.value if self.{field.name} is not None else None,\n")
            elif field.field_type == FieldType.OPTIONS:
                f.write(f"int(self.{field.name}) if self.{field.name} is not None else None,\n")
            elif field.field_type == FieldType.COMPOUND and field.compound_base_type == "float":
                f.write(f"dataclasses.asdict(self.{field.name}) if self.{field.name} is not None else None,\n")
            else:
                # For basic types (string, int, float, boolean, byte) and other compound types
                f.write(f"self.{field.name} if self.{field.name} is not None else None,\n")
            return

        # For required fields, we can include them directly
        if field.field_type == FieldType.ENUM:
            f.write(f"            \"{field.name}\": self.{field.name}.value,\n")
        elif field.field_type == FieldType.OPTIONS:
            f.write(f"            \"{field.name}\": int(self.{field.name}),\n")
        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                f.write(f"            \"{field.name}\": dataclasses.asdict(self.{field.name}),\n")
            else:
                f.write(f"            \"{field.name}\": self.{field.name},  # Unsupported compound type\n")
        else:
            # For basic types (string, int, float, boolean, byte)
            f.write(f"            \"{field.name}\": self.{field.name},\n")

    def _write_field_serialization(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write code to serialize a field to a dictionary.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to serialize
        """
        # Skip None values for optional fields
        if field.optional:
            f.write(f"        if self.{field.name} is not None:\n")
            indent = "            "
        else:
            indent = "        "

        if field.field_type == FieldType.ENUM:
            f.write(f"{indent}result[\"{field.name}\"] = self.{field.name}.value\n")

        elif field.field_type == FieldType.OPTIONS:
            f.write(f"{indent}result[\"{field.name}\"] = int(self.{field.name})\n")

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                f.write(f"{indent}result[\"{field.name}\"] = dataclasses.asdict(self.{field.name})\n")
            else:
                f.write(f"{indent}result[\"{field.name}\"] = self.{field.name}  # Unsupported compound type\n")

        else:
            # For basic types (string, int, float, boolean, byte)
            f.write(f"{indent}result[\"{field.name}\"] = self.{field.name}\n")

    def _write_from_dict_method(self, f: TextIO, message_name: str, message: Message) -> None:
        """
        Write the from_dict class method for a message class.

        Args:
            f: The file to write to
            message_name: The name of the message
            message: The message object
        """
        py_class_name = self._to_cap_words(message_name)

        f.write("\n    @classmethod\n")
        f.write(f"    def from_dict(cls, data: dict) -> \"{py_class_name}\":\n")
        f.write("        \"\"\"Create a message instance from a dictionary.\n\n")
        f.write("        Args:\n")
        f.write("            data: Dictionary containing message data\n\n")
        f.write("        Returns:\n")
        f.write(f"            {py_class_name}: New message instance\n")
        f.write("        \"\"\"\n")

        # If this message inherits from another, call the parent's from_dict method
        if message.parent:
            parent_class_name = self._to_cap_words(message.parent)
            f.write(f"        # Create instance using parent class deserialization\n")
            f.write(f"        instance = {parent_class_name}.from_dict(data)\n")
            f.write(f"        # Convert to this class type\n")
            f.write(f"        instance.__class__ = cls\n")
        else:
            f.write(f"        instance = cls()\n")

        # Deserialize each field
        for field in message.fields:
            self._write_field_deserialization(f, message_name, field)

        f.write(f"        return cast(\"{py_class_name}\", instance)\n")

    def _write_field_deserialization(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write code to deserialize a field from a dictionary.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to deserialize
        """
        py_message_name_part = message_name.replace("::", "_")

        f.write(f"        if \"{field.name}\" in data:\n")

        if field.field_type == FieldType.ENUM:
            enum_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Enum")
            f.write(f"            instance.{field.name} = {enum_name}(data[\"{field.name}\"])\n")

        elif field.field_type == FieldType.OPTIONS:
            enum_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Options")
            f.write(f"            instance.{field.name} = {enum_name}(data[\"{field.name}\"])\n")

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                compound_class_name = self._to_cap_words(f"{py_message_name_part}_{field.name}_Compound")
                f.write(f"            compound_data = data[\"{field.name}\"]\n")
                f.write(f"            instance.{field.name} = {compound_class_name}()\n")
                for component in field.compound_components:
                    f.write(f"            if \"{component}\" in compound_data:\n")
                    f.write(f"                instance.{field.name}.{component} = compound_data[\"{component}\"]\n")
            else:
                f.write(f"            instance.{field.name} = data[\"{field.name}\"]  # Unsupported compound type\n")

        else:
            # For basic types (string, int, float, boolean, byte)
            f.write(f"            instance.{field.name} = data[\"{field.name}\"]\n")

    def _write_serialization_utils(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write utility functions for message serialization and deserialization.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        f.write("# Message serialization utilities\n\n")

        # Write message registry
        f.write("# Registry of message types\n")
        f.write("_message_registry: Dict[str, Type] = {\n")
        for message_name in model.messages:
            py_class_name = self._to_cap_words(message_name)
            f.write(f"    \"{message_name}\": {py_class_name},\n")
        f.write("}\n\n")

        # Write MessageSerialization class
        f.write("class MessageSerialization:\n")
        f.write("    \"\"\"Utility class for message serialization and deserialization.\"\"\"\n\n")

        # Write serialize method
        f.write("    @staticmethod\n")
        f.write("    def serialize(message_type: str, payload: Any) -> str:\n")
        f.write("        \"\"\"Serialize a message to a JSON string with message type.\n\n")
        f.write("        Args:\n")
        f.write("            message_type: The type of the message\n")
        f.write("            payload: The message payload\n\n")
        f.write("        Returns:\n")
        f.write("            str: JSON string representation of the message\n")
        f.write("        \"\"\"\n")
        f.write("        if hasattr(payload, 'to_dict'):\n")
        f.write("            payload_dict = payload.to_dict()\n")
        f.write("        else:\n")
        f.write("            # Try to convert to dict using dataclasses.asdict\n")
        f.write("            try:\n")
        f.write("                payload_dict = dataclasses.asdict(payload)\n")
        f.write("            except TypeError:\n")
        f.write("                # Fall back to using the payload as-is\n")
        f.write("                payload_dict = payload\n")
        f.write("        \n")
        f.write("        envelope = {\"messageType\": message_type, \"payload\": payload_dict}\n")
        f.write("        return json.dumps(envelope)\n\n")

        # Write deserialize method
        f.write("    @staticmethod\n")
        f.write("    def deserialize(json_string: str) -> tuple[str, dict]:\n")
        f.write("        \"\"\"Deserialize a JSON string to a message type and payload.\n\n")
        f.write("        Args:\n")
        f.write("            json_string: JSON string to parse\n\n")
        f.write("        Returns:\n")
        f.write("            tuple[str, dict]: Tuple containing message type and payload dictionary\n\n")
        f.write("        Raises:\n")
        f.write("            ValueError: If the JSON string is invalid or missing required fields\n")
        f.write("        \"\"\"\n")
        f.write("        envelope = json.loads(json_string)\n")
        f.write("        if \"messageType\" not in envelope or \"payload\" not in envelope:\n")
        f.write("            raise ValueError(\"Invalid message format: missing messageType or payload\")\n")
        f.write("        \n")
        f.write("        return envelope[\"messageType\"], envelope[\"payload\"]\n\n")

        # Write deserialize_as method
        f.write("    @staticmethod\n")
        f.write("    def deserialize_as(json_string: str, expected_type: str) -> Any:\n")
        f.write("        \"\"\"Deserialize a JSON string to a specific message type.\n\n")
        f.write("        Args:\n")
        f.write("            json_string: JSON string to parse\n")
        f.write("            expected_type: Expected message type\n\n")
        f.write("        Returns:\n")
        f.write("            Any: Typed message object\n\n")
        f.write("        Raises:\n")
        f.write("            ValueError: If the JSON string is invalid, missing required fields, or of the wrong type\n")
        f.write("        \"\"\"\n")
        f.write("        message_type, payload = MessageSerialization.deserialize(json_string)\n")
        f.write("        if message_type != expected_type:\n")
        f.write("            raise ValueError(f\"Expected message type {expected_type} but got {message_type}\")\n")
        f.write("        \n")
        f.write("        if expected_type not in _message_registry:\n")
        f.write("            raise ValueError(f\"Unknown message type: {expected_type}\")\n")
        f.write("        \n")
        f.write("        message_class = _message_registry[expected_type]\n")
        f.write("        # Use cast to tell type checker that message_class has from_dict method\n")
        f.write("        return cast(Any, message_class).from_dict(payload)\n\n")

        # Write create_default method
        f.write("    @staticmethod\n")
        f.write("    def create_default(message_type: str) -> Any:\n")
        f.write("        \"\"\"Create a new instance of a message with default values.\n\n")
        f.write("        Args:\n")
        f.write("            message_type: The type of message to create\n\n")
        f.write("        Returns:\n")
        f.write("            Any: A new instance of the specified message type with default values\n\n")
        f.write("        Raises:\n")
        f.write("            ValueError: If the message type is unknown\n")
        f.write("        \"\"\"\n")
        f.write("        if message_type not in _message_registry:\n")
        f.write("            raise ValueError(f\"Unknown message type: {message_type}\")\n")
        f.write("        \n")
        f.write("        message_class = _message_registry[message_type]\n")
        f.write("        return message_class()\n\n")

        # Write validate_message method
        f.write("    @staticmethod\n")
        f.write("    def validate_message(obj: Any, message_type: str) -> bool:\n")
        f.write("        \"\"\"Validate that an object conforms to a specific message type.\n\n")
        f.write("        Args:\n")
        f.write("            obj: Object to validate\n")
        f.write("            message_type: Expected message type\n\n")
        f.write("        Returns:\n")
        f.write("            bool: True if the object is valid for the specified message type\n\n")
        f.write("        Raises:\n")
        f.write("            ValueError: If the message type is unknown\n")
        f.write("        \"\"\"\n")
        f.write("        if message_type not in _message_registry:\n")
        f.write("            raise ValueError(f\"Unknown message type: {message_type}\")\n")
        f.write("        \n")
        f.write("        message_class = _message_registry[message_type]\n")
        f.write("        return isinstance(obj, message_class)\n")
