"""
TypeScript Generator

This module provides functionality for generating TypeScript code from the
intermediate representation defined in message_model.py.
"""

import os
from typing import List, Set, TextIO

from message_model import (
    FieldType,
    Field,
    Message,
    MessageModel
)


class TypeScriptGenerator:
    """
    Generator for TypeScript code from the intermediate representation.
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
        Generate TypeScript code from the message model.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating TypeScript output in: {self.output_dir}")

            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)

            # Generate TypeScript file
            ts_file = os.path.join(self.output_dir, "messages.ts")
            with open(ts_file, 'w') as f:
                self._write_header(f)
                self._write_namespace_start(f)
                self._write_enums(f)
                self._write_interfaces(f)
                self._write_type_guards(f)
                self._write_serialization_utils(f)
                self._write_namespace_end(f)

            print(f"Generated TypeScript file: {ts_file}")
            return True

        except Exception as e:
            print(f"Error generating TypeScript output: {str(e)}")
            return False

    def _write_type_guards(self, f: TextIO) -> None:
        """
        Write type guard functions for each message type.

        Args:
            f: The file to write to
        """
        f.write("    // Type guard functions\n")

        for message_name, message in self.model.messages.items():
            f.write(f"    /**\n")
            f.write(f"     * Type guard for {message_name}\n")
            f.write(f"     * @param obj Object to check\n")
            f.write(f"     * @returns True if the object is a {message_name}\n")
            f.write(f"     */\n")
            f.write(f"    export function is{message_name}(obj: any): obj is {message_name} {{\n")
            f.write(f"        return obj !== null && typeof obj === 'object'")

            # Check parent properties if this message inherits from another
            if message.parent:
                f.write(f" && is{message.parent}(obj)")

            # Check each field
            for field in message.fields:
                if field.field_type == FieldType.ENUM:
                    f.write(f" && typeof obj.{field.name} === 'number'")
                elif field.field_type == FieldType.STRING:
                    f.write(f" && typeof obj.{field.name} === 'string'")
                elif field.field_type == FieldType.INT or field.field_type == FieldType.FLOAT:
                    f.write(f" && typeof obj.{field.name} === 'number'")
                elif field.field_type == FieldType.COMPOUND:
                    # Use type assertion (as any) to avoid TypeScript errors when checking properties
                    # that might not exist on the parent type
                    f.write(f" && (obj as any).{field.name} !== null && typeof (obj as any).{field.name} === 'object'")
                    if field.compound_base_type == "float" and field.compound_components:
                        for component in field.compound_components:
                            f.write(f" && typeof (obj as any).{field.name}.{component} === 'number'")

            f.write(";\n")
            f.write("    }\n\n")

    def _write_serialization_utils(self, f: TextIO) -> None:
        """
        Write utility functions for message serialization and deserialization.

        Args:
            f: The file to write to
        """
        f.write("    // Message serialization utilities\n")
        f.write("    export namespace MessageSerialization {\n\n")

        # Write message type registry
        f.write("        // Registry of message types\n")
        f.write("        interface MessageTypeInfo {\n")
        f.write("            typeName: string;\n")
        f.write("            typeGuard: (obj: any) => boolean;\n")
        f.write("        }\n\n")

        f.write("        // Registry of message types\n")
        f.write("        const messageRegistry: Record<string, MessageTypeInfo> = {\n")

        # Register each message type
        for message_name in self.model.messages:
            f.write(f"            '{message_name}': {{\n")
            f.write(f"                typeName: '{message_name}',\n")
            f.write(f"                typeGuard: is{message_name}\n")
            f.write("            },\n")

        f.write("        };\n\n")

        # Write serialization function
        f.write("        /**\n")
        f.write("         * Serialize a message to a JSON string with message type\n")
        f.write("         * @param messageType The type of the message\n")
        f.write("         * @param payload The message payload\n")
        f.write("         * @returns JSON string representation of the message\n")
        f.write("         */\n")
        f.write("        export function serialize<T>(messageType: string, payload: T): string {\n")
        f.write("            const envelope = {\n")
        f.write("                messageType,\n")
        f.write("                payload\n")
        f.write("            };\n")
        f.write("            return JSON.stringify(envelope);\n")
        f.write("        }\n\n")

        # Write deserialization function
        f.write("        /**\n")
        f.write("         * Deserialize a JSON string to a message object\n")
        f.write("         * @param jsonString JSON string to parse\n")
        f.write("         * @returns Object containing messageType and payload\n")
        f.write("         * @throws Error if the JSON string is invalid or missing required fields\n")
        f.write("         */\n")
        f.write("        export function deserialize(jsonString: string): { messageType: string, payload: any } {\n")
        f.write("            const envelope = JSON.parse(jsonString);\n")
        f.write("            if (!envelope.messageType || !envelope.payload) {\n")
        f.write("                throw new Error('Invalid message format: missing messageType or payload');\n")
        f.write("            }\n")
        f.write("            return envelope;\n")
        f.write("        }\n\n")

        # Write type-safe deserialization function
        f.write("        /**\n")
        f.write("         * Deserialize a JSON string to a specific message type\n")
        f.write("         * @param jsonString JSON string to parse\n")
        f.write("         * @param expectedType Expected message type\n")
        f.write("         * @returns Typed message payload\n")
        f.write("         * @throws Error if the JSON string is invalid, missing required fields, or of the wrong type\n")
        f.write("         */\n")
        f.write("        export function deserializeAs<T>(jsonString: string, expectedType: string): T {\n")
        f.write("            const { messageType, payload } = deserialize(jsonString);\n")
        f.write("            if (messageType !== expectedType) {\n")
        f.write("                throw new Error(`Expected message type ${expectedType} but got ${messageType}`);\n")
        f.write("            }\n")
        f.write("            return payload as T;\n")
        f.write("        }\n\n")

        # Write message validation function
        f.write("        /**\n")
        f.write("         * Validate that an object conforms to a specific message type\n")
        f.write("         * @param obj Object to validate\n")
        f.write("         * @param messageType Expected message type\n")
        f.write("         * @returns True if the object is valid for the specified message type\n")
        f.write("         */\n")
        f.write("        export function validateMessage(obj: any, messageType: string): boolean {\n")
        f.write("            const typeInfo = messageRegistry[messageType];\n")
        f.write("            if (!typeInfo) {\n")
        f.write("                throw new Error(`Unknown message type: ${messageType}`);\n")
        f.write("            }\n")
        f.write("            return typeInfo.typeGuard(obj);\n")
        f.write("        }\n")

        f.write("    } // namespace MessageSerialization\n")

    def _write_header(self, f: TextIO) -> None:
        """
        Write the header section of the TypeScript file.

        Args:
            f: The file to write to
        """
        f.write("// Auto-generated message definitions for TypeScript\n")
        f.write("// This file contains message definitions for communication between systems.\n")
        f.write("//\n")
        f.write("// DOCUMENTATION FOR MESSAGE FORMAT:\n")
        f.write("// ===============================\n")
        f.write("// This file defines a set of message interfaces used for communication.\n")
        f.write("// Each message is defined as a TypeScript interface within the Messages namespace.\n")
        f.write("//\n")
        f.write("// Message Structure:\n")
        f.write("// - Messages are defined as interfaces with specific fields\n")
        f.write("// - Messages can inherit from other messages using TypeScript interface extension\n")
        f.write("// - Fields can be of the following types:\n")
        f.write("//   * Basic types: number (for both integer and float), string\n")
        f.write("//   * Enum types: defined as TypeScript enums\n")
        f.write("//   * Compound types: object with named properties\n")
        f.write("//\n")
        f.write("// Enum Naming Convention:\n")
        f.write("// - Enums are named as MessageName_fieldName_Enum\n")
        f.write("//\n")
        f.write("// Compound Field Structure:\n")
        f.write("// - Compound fields are defined as inline object types\n")
        f.write("// - Each component is a named property within the object\n")
        f.write("//\n")
        f.write("// JSON Serialization:\n")
        f.write("// ================\n")
        f.write("// The MessageSerialization namespace provides utility functions for working with messages:\n")
        f.write("// - serialize(): Serializes a message to a JSON string with message type\n")
        f.write("// - deserialize(): Deserializes a JSON string to a message object\n")
        f.write("// - isMessageType(): Type guard functions to check if an object is a specific message type\n")
        f.write("//\n")
        f.write("// HOW TO GENERATE A READER:\n")
        f.write("// =====================\n")
        f.write("// To create a reader for these messages:\n")
        f.write("// 1. Create a parser that can deserialize JSON data into these interfaces\n")
        f.write("// 2. For each message type, implement a handler function\n")
        f.write("// 3. Use a dispatcher to route messages to the appropriate handler based on message type\n")
        f.write("// 4. For inheritance, ensure parent fields are processed before child fields\n")
        f.write("//\n\n")

    def _write_namespace_start(self, f: TextIO) -> None:
        """
        Write the start of the namespace.

        Args:
            f: The file to write to
        """
        f.write("export namespace Messages {\n\n")

    def _write_namespace_end(self, f: TextIO) -> None:
        """
        Write the end of the namespace.

        Args:
            f: The file to write to
        """
        f.write("} // namespace Messages\n")

    def _write_enums(self, f: TextIO) -> None:
        """
        Write enum definitions.

        Args:
            f: The file to write to
        """
        enums_generated = set()

        for message_name, message in self.model.messages.items():
            for field in message.fields:
                if field.field_type == FieldType.ENUM:
                    enum_name = f"{message_name}_{field.name}_Enum"
                    if enum_name not in enums_generated:
                        f.write(f"    // Enum for {message_name}.{field.name}\n")
                        f.write(f"    export enum {enum_name} {{\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    }\n\n")
                        enums_generated.add(enum_name)

    def _write_interfaces(self, f: TextIO) -> None:
        """
        Write interface definitions.

        Args:
            f: The file to write to
        """
        for message_name, message in self.model.messages.items():
            # Write detailed documentation for the message using JSDoc format
            f.write(f"    /**\n")
            f.write(f"     * {message.description if message.description else f'Message definition for {message_name}'}\n")

            # Include user-supplied comment if available
            if message.comment:
                # Split multi-line comments and format each line
                comment_lines = message.comment.split('\n')
                for line in comment_lines:
                    f.write(f"     * {line}\n")

            if message.parent:
                f.write(f"     * @extends {message.parent}\n")

            # Document all fields in the message
            if message.fields:
                f.write(f"     *\n")
                for field in message.fields:
                    field_type_str = self._get_field_type_description(field, message_name)
                    f.write(f"     * @property {{{self._get_ts_type(field, message_name)}}} {field.name}")
                    if field.description:
                        f.write(f" - {field.description}")
                    else:
                        f.write(f" - {field_type_str}")
                    f.write("\n")

            f.write(f"     */\n")

            # Handle inheritance
            if message.parent:
                f.write(f"    export interface {message_name} extends {message.parent} {{\n")
            else:
                f.write(f"    export interface {message_name} {{\n")

            # Generate fields
            for field in message.fields:
                self._write_field(f, message_name, field)

            f.write("    }\n\n")

    def _get_ts_type(self, field: Field, message_name: str) -> str:
        """
        Get the TypeScript type for a field.

        Args:
            field: The field to get the type for
            message_name: The name of the message containing the field

        Returns:
            The TypeScript type as a string
        """
        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            return enum_name

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                components = ", ".join([f"{c}: number" for c in field.compound_components])
                return f"{{ {components} }}"
            else:
                return "object"

        elif field.field_type == FieldType.STRING:
            return "string"

        elif field.field_type == FieldType.INT or field.field_type == FieldType.FLOAT:
            return "number"

        else:
            return "any"

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
            return "Integer (number)"

        elif field.field_type == FieldType.FLOAT:
            return "Float (number)"

        else:
            return f"Unknown ({field.field_type})"

    def _write_field(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write a field definition.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to write
        """
        # Add inline documentation comment for the field
        if field.comment:
            # Use user-supplied comment if available
            f.write(f"        /**\n")
            # Split multi-line comments and format each line
            comment_lines = field.comment.split('\n')
            for line in comment_lines:
                f.write(f"         * {line}\n")
            f.write(f"         */\n")
        elif field.description:
            f.write(f"        /** {field.description} */\n")
        else:
            field_type_desc = self._get_field_type_description(field, message_name)
            f.write(f"        /** {field_type_desc} */\n")

        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            f.write(f"        {field.name}: {enum_name};\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"        {field.name}: {{\n")
                for component in field.compound_components:
                    f.write(f"            /** {component} component */\n")
                    f.write(f"            {component}: number;\n")
                f.write("        };\n")
            else:
                # Handle other compound types if needed
                f.write(f"        // Unsupported compound type: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"        {field.name}: string;\n")

        elif field.field_type == FieldType.INT or field.field_type == FieldType.FLOAT:
            f.write(f"        {field.name}: number;\n")

        else:
            f.write(f"        // Unsupported type: {field.field_type}\n")
