"""
JSON Generator

This module provides functionality for generating JSON schema definitions from the
intermediate representation defined in message_model.py.
"""

import os
import json
from typing import Dict, List, Any, TextIO

from message_model import (
    FieldType,
    Field,
    Message,
    MessageModel
)


class JsonGenerator:
    """
    Generator for JSON schema definitions from the intermediate representation.
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

    def generate(self) -> bool:
        """
        Generate JSON schema definitions from the message model.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating JSON output in: {self.output_dir}")

            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)

            # Generate JSON schema file with custom name
            json_file = os.path.join(self.output_dir, f"{self.output_name}.json")

            # Create the schema object
            schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Message Definitions",
                "description": "JSON schema for message definitions",
                "definitions": {}
            }

            # Add all message definitions, using fully qualified names for namespaced messages
            for message_name, message in self.model.messages.items():
                # Use fully qualified name for the schema definition
                schema_key = message.get_full_name()
                schema["definitions"][schema_key] = self._create_message_schema(message)

            # Write the schema to file
            with open(json_file, 'w') as f:
                json.dump(schema, f, indent=2)

            print(f"Generated JSON schema file: {json_file}")
            return True

        except Exception as e:
            print(f"Error generating JSON output: {str(e)}")
            return False

    def _create_message_schema(self, message: Message) -> Dict[str, Any]:
        """
        Create a JSON schema definition for a message.

        Args:
            message: The message to create a schema for

        Returns:
            A dictionary representing the JSON schema for the message
        """
        # Use user-supplied comment if available, otherwise use description
        description = message.description if message.description else f"Message definition for {message.name}"
        if message.comment:
            description = message.comment

        # If message has a namespace, include it in the description
        if message.namespace:
            description = f"[Namespace: {message.namespace}] {description}"

        schema = {
            "type": "object",
            "description": description,
            "properties": {},
            "required": []
        }

        # Handle inheritance
        if message.parent:
            parent_message = self.model.get_message(message.parent)
            if parent_message:
                # If parent is in a namespace, include the namespace in the reference
                parent_ref = message.parent
                if parent_message.namespace:
                    parent_ref = f"{parent_message.namespace}::{parent_message.name}"
                schema["allOf"] = [
                    {"$ref": f"#/definitions/{parent_ref}"}
                ]

        # Add properties for each field
        for field in message.fields:
            field_schema = self._create_field_schema(field, message.name)
            schema["properties"][field.name] = field_schema
            if not field.optional:  # Only add non-optional fields to required array
                schema["required"].append(field.name)

        return schema

    def _create_field_schema(self, field: Field, message_name: str) -> Dict[str, Any]:
        """
        Create a JSON schema definition for a field.

        Args:
            field: The field to create a schema for
            message_name: The name of the message containing the field

        Returns:
            A dictionary representing the JSON schema for the field
        """
        # Use user-supplied comment if available, otherwise use description or type description
        description = field.description if field.description else self._get_field_type_description(field, message_name)
        if field.comment:
            description = field.comment

        schema = {
            "description": description
        }

        # Add default value if specified
        if field.default_value is not None:
            # For enum fields, use the numeric value
            if field.field_type == FieldType.ENUM:
                # Find the enum value with the matching name
                for enum_value in field.enum_values:
                    if enum_value.name == field.default_value:
                        schema["default"] = enum_value.value
                        break
            elif field.field_type == FieldType.STRING:
                # Remove extra quotes from string default values
                default_value = field.default_value
                if isinstance(default_value, str) and default_value.startswith('"') and default_value.endswith('"'):
                    default_value = default_value[1:-1]
                schema["default"] = default_value
            else:
                schema["default"] = field.default_value

        if field.field_type == FieldType.STRING:
            schema["type"] = "string"

        elif field.field_type == FieldType.INT:
            schema["type"] = "integer"

        elif field.field_type == FieldType.FLOAT:
            schema["type"] = "number"

        elif field.field_type == FieldType.BOOLEAN:
            schema["type"] = "boolean"

        elif field.field_type == FieldType.BYTE:
            schema["type"] = "integer"
            schema["minimum"] = 0
            schema["maximum"] = 255

        elif field.field_type == FieldType.ENUM:
            schema["type"] = "integer"
            schema["enum"] = [value.value for value in field.enum_values]
            schema["enumNames"] = [value.name for value in field.enum_values]

        elif field.field_type == FieldType.OPTIONS:
            schema["type"] = "integer"
            schema["description"] = f"{description} (bit flags)"
            # Add information about the available options
            schema["options"] = [{"name": value.name, "value": value.value} for value in field.enum_values]

        elif field.field_type == FieldType.COMPOUND:
            schema["type"] = "object"
            schema["properties"] = {}
            schema["required"] = []

            for component in field.compound_components:
                component_type = "number" if field.compound_base_type == "float" else "string"
                schema["properties"][component] = {
                    "type": component_type,
                    "description": f"{component} component"
                }
                schema["required"].append(component)

        return schema

    def _get_field_type_description(self, field: Field, message_name: str) -> str:
        """
        Get a human-readable description of a field type.

        Args:
            field: The field to describe
            message_name: The name of the message containing the field

        Returns:
            A human-readable description of the field type
        """
        optional_text = " (optional)" if field.optional else ""
        default_text = f" default({field.default_value})" if field.default_value is not None else ""

        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            return f"Enum ({enum_name}){optional_text}{default_text}"

        elif field.field_type == FieldType.OPTIONS:
            options_values = ", ".join([value.name for value in field.enum_values])
            return f"Options (bit flags: {options_values}){optional_text}{default_text}"

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                components = ", ".join(field.compound_components)
                return f"Compound object with components: {components}{optional_text}{default_text}"
            else:
                return f"Compound object of type {field.compound_base_type}{optional_text}{default_text}"

        elif field.field_type == FieldType.STRING:
            return f"String{optional_text}{default_text}"

        elif field.field_type == FieldType.INT:
            return f"Integer{optional_text}{default_text}"

        elif field.field_type == FieldType.FLOAT:
            return f"Float{optional_text}{default_text}"

        elif field.field_type == FieldType.BOOLEAN:
            return f"Boolean{optional_text}{default_text}"

        elif field.field_type == FieldType.BYTE:
            return f"Byte (0-255){optional_text}{default_text}"

        else:
            return f"Unknown ({field.field_type}){optional_text}{default_text}"
