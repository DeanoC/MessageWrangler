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

    def __init__(self, model: MessageModel, output_dir: str):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
        """
        self.model = model
        self.output_dir = output_dir

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

            # Generate JSON schema file
            json_file = os.path.join(self.output_dir, "messages.json")

            # Create the schema object
            schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Message Definitions",
                "description": "JSON schema for message definitions",
                "definitions": {}
            }

            # Add all message definitions
            for message_name, message in self.model.messages.items():
                schema["definitions"][message_name] = self._create_message_schema(message)

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
                schema["allOf"] = [
                    {"$ref": f"#/definitions/{message.parent}"}
                ]

        # Add properties for each field
        for field in message.fields:
            field_schema = self._create_field_schema(field, message.name)
            schema["properties"][field.name] = field_schema
            schema["required"].append(field.name)  # All fields are required

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

        if field.field_type == FieldType.STRING:
            schema["type"] = "string"

        elif field.field_type == FieldType.INT:
            schema["type"] = "integer"

        elif field.field_type == FieldType.FLOAT:
            schema["type"] = "number"

        elif field.field_type == FieldType.ENUM:
            schema["type"] = "integer"
            schema["enum"] = [value.value for value in field.enum_values]
            schema["enumNames"] = [value.name for value in field.enum_values]

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
        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            return f"Enum ({enum_name})"

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                components = ", ".join(field.compound_components)
                return f"Compound object with components: {components}"
            else:
                return f"Compound object of type {field.compound_base_type}"

        elif field.field_type == FieldType.STRING:
            return "String"

        elif field.field_type == FieldType.INT:
            return "Integer"

        elif field.field_type == FieldType.FLOAT:
            return "Float"

        else:
            return f"Unknown ({field.field_type})"
