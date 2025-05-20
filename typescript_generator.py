"""
TypeScript Generator

This module provides functionality for generating TypeScript code from the
intermediate representation defined in message_model.py.
It generates ES2015 standard TypeScript (no namespaces, etc.).
It should NEVER have any specific code to handle troublesome cases.
"""

import os
from typing import List, Set, TextIO

from message_model import (
    FieldType,
    Field,
    Message,
    MessageModel,
    Enum
)


class TypeScriptGenerator:
    """
    Generator for TypeScript code from the intermediate representation.
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
        Generate TypeScript code from the message model.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating TypeScript output in: {self.output_dir}")

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

                ts_file = os.path.join(self.output_dir, f"{output_base_name}_msgs.ts")
                generated_files[source_file] = ts_file

                # Create a filtered model with only the messages from this source file
                filtered_model = MessageModel()
                for message in messages:
                    filtered_model.add_message(message)

                # Add standalone enums to the filtered model
                for enum_name, enum in self.model.enums.items():
                    filtered_model.add_enum(enum)

                # Generate the TypeScript file
                with open(ts_file, 'w') as f:
                    self._write_header(f)
                    self._write_namespace_start(f)

                    # Add import statements for parent messages that are in other files
                    self._write_file_imports(f, messages, messages_by_source, generated_files)

                    # Write enums and interfaces for this file only
                    self._write_enums(f, filtered_model)
                    self._write_interfaces(f, filtered_model)
                    self._write_type_guards(f, filtered_model)

                    # Only write serialization utils in the main file
                    if source_file == main_file:
                        self._write_serialization_utils(f)

                    self._write_namespace_end(f)

                print(f"Generated TypeScript file: {ts_file}")

            return True

        except Exception as e:
            print(f"Error generating TypeScript output: {str(e)}")
            return False

    def _write_file_imports(self, f: TextIO, messages: list, messages_by_source: dict, generated_files: dict) -> None:
        """
        Write import statements for parent messages that are in other files.

        Args:
            f: The file to write to
            messages: List of messages in the current file
            messages_by_source: Dictionary mapping source files to lists of messages
            generated_files: Dictionary mapping source files to generated TypeScript files
        """
        # Track needed imports with specific types
        needed_imports = {}  # module -> set of types

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

                        # Get the TypeScript interface name for the parent message
                        parent_ts_interface_name = parent_message.get_full_name().replace("::", "_")

                        # Get the type guard function name for the parent message
                        parent_type_guard_name = "is" + parent_ts_interface_name

                        # Add the parent interface and type guard function to the imports for this module
                        if parent_module not in needed_imports:
                            needed_imports[parent_module] = set()
                        needed_imports[parent_module].add(parent_ts_interface_name)
                        needed_imports[parent_module].add(parent_type_guard_name)

        # Write import statements
        for module in sorted(needed_imports.keys()):
            types = sorted(needed_imports[module])
            types_str = ", ".join(types)
            f.write(f"import {{ {types_str} }} from './{module}';\n")

        if needed_imports:
            f.write("\n")

    def _write_type_guards(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write type guard functions for each message type.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        f.write("// Type guard functions\n")

        for message_name, message in model.messages.items():
            # Create a TypeScript-friendly interface name, replacing :: with _
            ts_interface_name = message_name.replace("::", "_")
            display_name = ts_interface_name

            # Create a valid function name (no dots or colons)
            function_name = "is" + ts_interface_name

            f.write(f"/**\n")
            f.write(f" * Type guard for {display_name}\n")
            f.write(f" * @param obj Object to check\n")
            f.write(f" * @returns True if the object is a {display_name}\n")
            f.write(f" */\n")
            f.write(f"export function {function_name}(obj: unknown): obj is {ts_interface_name} {{\n")
            f.write(f"    return obj !== null && typeof obj === 'object'")

            # Check parent properties if this message inherits from another
            if message.parent:
                parent_ts_interface_name = message.parent.replace("::", "_")
                parent_function_name = "is" + parent_ts_interface_name
                f.write(f" && {parent_function_name}(obj)")

            # Check each field
            for field in message.fields:
                if field.optional:
                    f.write(f" && (!('{field.name}' in obj) || (")
                    if field.field_type == FieldType.ENUM:
                        f.write(f"typeof obj.{field.name} === 'number'")
                    elif field.field_type == FieldType.OPTIONS:
                        f.write(f"typeof obj.{field.name} === 'number'")
                    elif field.field_type == FieldType.STRING:
                        f.write(f"typeof obj.{field.name} === 'string'")
                    elif field.field_type == FieldType.INT or field.field_type == FieldType.FLOAT or field.field_type == FieldType.BYTE:
                        f.write(f"typeof obj.{field.name} === 'number'")
                    elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
                        f.write(f"typeof obj.{field.name} === 'boolean'")
                    elif field.field_type == FieldType.COMPOUND:
                        f.write(f"obj.{field.name} !== null && typeof obj.{field.name} === 'object'")
                        if field.compound_base_type == "float" and field.compound_components:
                            for i, component in enumerate(field.compound_components):
                                if i > 0:
                                    f.write(" && ")
                                f.write(f"'{component}' in obj.{field.name} && typeof obj.{field.name}.{component} === 'number'")

                    f.write("))")
                else:
                    f.write(f" && '{field.name}' in obj")
                    if field.field_type == FieldType.ENUM:
                        f.write(f" && typeof obj.{field.name} === 'number'")
                    elif field.field_type == FieldType.OPTIONS:
                        f.write(f" && typeof obj.{field.name} === 'number'")
                    elif field.field_type == FieldType.STRING:
                        f.write(f" && typeof obj.{field.name} === 'string'")
                    elif field.field_type == FieldType.INT or field.field_type == FieldType.FLOAT or field.field_type == FieldType.BYTE:
                        f.write(f" && typeof obj.{field.name} === 'number'")
                    elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
                        f.write(f" && typeof obj.{field.name} === 'boolean'")
                    elif field.field_type == FieldType.COMPOUND:
                        f.write(f" && obj.{field.name} !== null && typeof obj.{field.name} === 'object'")
                        if field.compound_base_type == "float" and field.compound_components:
                            for component in field.compound_components:
                                f.write(f" && '{component}' in obj.{field.name} && typeof obj.{field.name}.{component} === 'number'")

            f.write(";\n")
            f.write("}\n\n")

    def _write_serialization_utils(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write utility functions for message serialization and deserialization.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        f.write("// Message serialization utilities\n")
        f.write("// These utilities help with serializing and deserializing messages\n\n")

        f.write("// Registry of message types\n")
        f.write("interface MessageTypeInfo {\n")
        f.write("    typeName: string;\n")
        f.write("    typeGuard: (obj: unknown) => boolean;\n")
        f.write("    defaultValues?: Record<string, unknown>;\n")
        f.write("}\n\n")

        f.write("// Registry of message types\n")
        f.write("const messageRegistry: Record<string, MessageTypeInfo> = {\n")

        # Register each message type
        for message_name, message in model.messages.items():
            # Create a TypeScript-friendly interface name, replacing :: with _
            ts_interface_name = message_name.replace("::", "_")
            display_name = ts_interface_name

            # Create a valid function name (no dots or colons)
            function_name = "is" + ts_interface_name

            f.write(f"    '{display_name}': {{\n")
            f.write(f"        typeName: '{display_name}',\n")
            f.write(f"        typeGuard: {function_name},\n")

            # Add default values if any fields have them
            has_defaults = any(field.default_value is not None for field in message.fields)
            if has_defaults:
                f.write(f"        defaultValues: {{\n")
                for field in message.fields:
                    if field.default_value is not None:
                        # Format the default value based on its type
                        if field.field_type == FieldType.STRING:
                            # Remove extra quotes if present
                            default_value = field.default_value
                            if isinstance(default_value, str) and default_value.startswith('"') and default_value.endswith('"'):
                                default_value = default_value[1:-1]
                            f.write(f"            {field.name}: \"{default_value}\",\n")
                        elif field.field_type == FieldType.ENUM:
                            # Use the enum value
                            f.write(f"            {field.name}: {ts_interface_name}_{field.name}_Enum.{field.default_value},\n")
                        elif field.field_type == FieldType.OPTIONS:
                            # Handle options fields
                            if field.default_value_str and '&' in field.default_value_str:
                                # For combined options (e.g., "OptionA & OptionB"), use the OR'ed enum values
                                option_names = [opt.strip() for opt in field.default_value_str.split('&')]
                                enum_prefix = f"{ts_interface_name}_{field.name}_Options"
                                or_expression = " | ".join([f"{enum_prefix}.{name}" for name in option_names])
                                f.write(f"            {field.name}: {or_expression},\n")
                            elif isinstance(field.default_value, int) or (isinstance(field.default_value, str) and field.default_value.isdigit()):
                                # If it's already a numeric value and we don't have the original string, use it directly
                                if not field.default_value_str:
                                    f.write(f"            {field.name}: {field.default_value},\n")
                                else:
                                    # Use the enum value
                                    f.write(f"            {field.name}: {ts_interface_name}_{field.name}_Options.{field.default_value_str},\n")
                            else:
                                # For single option values, use the enum
                                f.write(f"            {field.name}: {ts_interface_name}_{field.name}_Options.{field.default_value},\n")
                        else:
                            # For numbers, booleans, etc.
                            f.write(f"            {field.name}: {field.default_value},\n")
                f.write(f"        }}\n")
            else:
                f.write(f"        defaultValues: {{}}\n")

            f.write("    },\n")

        f.write("};\n\n")

        f.write("/**\n")
        f.write(" * Serialize a message to a JSON string with message type\n")
        f.write(" * @param messageType The type of the message\n")
        f.write(" * @param payload The message payload\n")
        f.write(" * @returns JSON string representation of the message\n")
        f.write(" */\n")
        f.write("export function serialize<T>(messageType: string, payload: T): string {\n")
        f.write("    const envelope = {\n")
        f.write("        messageType,\n")
        f.write("        payload\n")
        f.write("    };\n")
        f.write("    return JSON.stringify(envelope);\n")
        f.write("}\n\n")

        f.write("/**\n")
        f.write(" * Deserialize a JSON string to a message object\n")
        f.write(" * @param jsonString JSON string to parse\n")
        f.write(" * @returns Object containing messageType and payload\n")
        f.write(" * @throws Error if the JSON string is invalid or missing required fields\n")
        f.write(" */\n")
        f.write("export function deserialize(jsonString: string): { messageType: string, payload: unknown } {\n")
        f.write("    const envelope = JSON.parse(jsonString);\n")
        f.write("    if (!envelope.messageType || !envelope.payload) {\n")
        f.write("        throw new Error('Invalid message format: missing messageType or payload');\n")
        f.write("    }\n")
        f.write("    return envelope;\n")
        f.write("}\n\n")

        f.write("/**\n")
        f.write(" * Deserialize a JSON string to a specific message type\n")
        f.write(" * @param jsonString JSON string to parse\n")
        f.write(" * @param expectedType Expected message type\n")
        f.write(" * @returns Typed message payload\n")
        f.write(" * @throws Error if the JSON string is invalid, missing required fields, or of the wrong type\n")
        f.write(" */\n")
        f.write("export function deserializeAs<T>(jsonString: string, expectedType: string): T {\n")
        f.write("    const { messageType, payload } = deserialize(jsonString);\n")
        f.write("    if (messageType !== expectedType) {\n")
        f.write("        throw new Error(`Expected message type ${expectedType} but got ${messageType}`);\n")
        f.write("    }\n")
        f.write("    return payload as T;\n")
        f.write("}\n\n")

        f.write("/**\n")
        f.write(" * Validate that an object conforms to a specific message type\n")
        f.write(" * @param obj Object to validate\n")
        f.write(" * @param messageType Expected message type\n")
        f.write(" * @returns True if the object is valid for the specified message type\n")
        f.write(" */\n")
        f.write("export function validateMessage(obj: unknown, messageType: string): boolean {\n")
        f.write("    const typeInfo = messageRegistry[messageType];\n")
        f.write("    if (!typeInfo) {\n")
        f.write("        throw new Error(`Unknown message type: ${messageType}`);\n")
        f.write("    }\n")
        f.write("    return typeInfo.typeGuard(obj);\n")
        f.write("}\n\n")
        f.write("/**\n")
        f.write(" * Create a new instance of a message with default values\n")
        f.write(" * @param messageType The type of message to create\n")
        f.write(" * @returns A new instance of the specified message type with default values\n")
        f.write(" */\n")
        f.write("export function createDefault<T>(messageType: string): T {\n")
        f.write("    const typeInfo = messageRegistry[messageType];\n")
        f.write("    if (!typeInfo) {\n")
        f.write("        throw new Error(`Unknown message type: ${messageType}`);\n")
        f.write("    }\n")
        f.write("    \n")
        f.write("    // Start with an empty object\n")
        f.write("    const result: Record<string, unknown> = {};\n")
        f.write("    \n")
        f.write("    // Apply default values if available\n")
        f.write("    if (typeInfo.defaultValues) {\n")
        f.write("        // Use for...in loop instead of Object.assign for better compatibility with older ECMAScript versions\n")
        f.write("        for (const key in typeInfo.defaultValues) {\n")
        f.write("            if (Object.prototype.hasOwnProperty.call(typeInfo.defaultValues, key)) {\n")
        f.write("                result[key] = typeInfo.defaultValues[key];\n")
        f.write("            }\n")
        f.write("        }\n")
        f.write("    }\n")
        f.write("    \n")
        f.write("    return result as T;\n")
        f.write("}\n")

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
        f.write("// - Messages can be organized into namespaces for logical grouping\n")
        f.write("// - Fields can be of the following types:\n")
        f.write("//   * Basic types: number (for both integer and float), string, boolean, byte (0-255)\n")
        f.write("//   * Enum types: defined as TypeScript enums\n")
        f.write("//   * Options types: defined as TypeScript enums, can be combined with bitwise OR\n")
        f.write("//   * Compound types: object with named properties\n")
        f.write("//\n")
        f.write("// Field Modifiers:\n")
        f.write("// - Optional fields: Fields that can be omitted from messages (marked with ?)\n")
        f.write("// - Default values: Fields can have default values that are used when not explicitly set\n")
        f.write("//   * Default values are documented in JSDoc comments using @default\n")
        f.write("//   * For enums, the default value is the enum value name\n")
        f.write("//   * For options, the default value can be a single option or a combination (e.g., OptionA | OptionB)\n")
        f.write("//\n")
        f.write("// Enum Naming Convention:\n")
        f.write("// - Enums are named as MessageName_fieldName_Enum\n")
        f.write("//\n")
        f.write("// Options Naming Convention:\n")
        f.write("// - Options are named as MessageName_fieldName_Options\n")
        f.write("// - Options are bit flags that can be combined using the bitwise OR operator (|)\n")
        f.write("//\n")
        f.write("// Compound Field Structure:\n")
        f.write("// - Compound fields are defined as inline object types\n")
        f.write("// - Each component is a named property within the object\n")
        f.write("// - Currently supports float compounds with named components (e.g., position: { x: number, y: number, z: number })\n")
        f.write("//\n")
        f.write("// JSON Serialization:\n")
        f.write("// ================\n")
        f.write("// The MessageSerialization namespace provides utility functions for working with messages:\n")
        f.write("// - serialize(): Serializes a message to a JSON string with message type\n")
        f.write("// - deserialize(): Deserializes a JSON string to a message object\n")
        f.write("// - deserializeAs(): Deserializes a JSON string to a specific message type\n")
        f.write("// - validateMessage(): Validates that an object conforms to a specific message type\n")
        f.write("// - createDefault(): Creates a new instance of a message with default values\n")
        f.write("// - isMessageType(): Type guard functions to check if an object is a specific message type\n")
        f.write("//\n")
        f.write("// Message Envelope Structure:\n")
        f.write("// ========================\n")
        f.write("// Messages are serialized with an envelope structure that includes:\n")
        f.write("// - messageType: The type of the message, which matches the name of the message definition\n")
        f.write("// - payload: The actual message data as a JSON object\n")
        f.write("// Example: {\"messageType\": \"MyMessage\", \"payload\": {\"field1\": \"value1\", \"field2\": 42}}\n")
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
        Write the start of the module exports.

        Args:
            f: The file to write to
        """
        # No namespace wrapper needed with ES2015 module syntax
        # Just start exporting the interfaces and types directly

    def _write_namespace_end(self, f: TextIO) -> None:
        """
        Write the end of the module exports.

        Args:
            f: The file to write to
        """
        # No namespace closing needed with ES2015 module syntax

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
            ts_enum_name = enum_name.replace("::", "_")
            if ts_enum_name not in enums_generated:
                f.write(f"// Standalone enum {enum_name}\n")
                if enum.comment:
                    comment_lines = enum.comment.split('\n')
                    for line in comment_lines:
                        f.write(f"// {line}\n")
                f.write(f"export enum {ts_enum_name} {{\n")
                for enum_value in enum.values:
                    f.write(f"    {enum_value.name} = {enum_value.value},\n")
                f.write("}\n\n")
                enums_generated.add(ts_enum_name)

        # Write enums for message fields
        for message_name, message in model.messages.items():
            ts_message_name_part = message_name.replace("::", "_")
            for field in message.fields:
                if field.field_type == FieldType.ENUM:
                    enum_name = f"{ts_message_name_part}_{field.name}_Enum"
                    if enum_name not in enums_generated:
                        f.write(f"// Enum for {message_name}.{field.name}\n")
                        f.write(f"export enum {enum_name} {{\n")
                        for enum_value in field.enum_values:
                            f.write(f"    {enum_value.name} = {enum_value.value},\n")
                        f.write("}\n\n")
                        enums_generated.add(enum_name)
                elif field.field_type == FieldType.OPTIONS:
                    enum_name = f"{ts_message_name_part}_{field.name}_Options"
                    if enum_name not in enums_generated:
                        f.write(f"// Options for {message_name}.{field.name}\n")
                        f.write(f"export enum {enum_name} {{\n")
                        for enum_value in field.enum_values:
                            f.write(f"    {enum_value.name} = {enum_value.value},\n")
                        f.write("}\n\n")
                        enums_generated.add(enum_name)

    def _write_interfaces(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write interface definitions.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        for message_name, message in model.messages.items():
            ts_interface_name = message_name.replace("::", "_")
            parent_ts_interface_name = message.parent.replace("::", "_") if message.parent else None

            f.write(f"/**\n")
            f.write(f" * {message.description if message.description else f'Message definition for {message_name}'}\n")

            if message.comment:
                comment_lines = message.comment.split('\n')
                for line in comment_lines:
                    f.write(f" * {line}\n")

            if parent_ts_interface_name:
                f.write(f" * @extends {parent_ts_interface_name}\n")

            if message.fields:
                f.write(f" *\n")
                for field in message.fields:
                    field_type_str = self._get_field_type_description(field, message_name)
                    ts_type = self._get_ts_type(field, message_name)
                    f.write(f" * @property {{{ts_type}}} {field.name}")
                    if field.description:
                        f.write(f" - {field.description}")
                    else:
                        f.write(f" - {field_type_str}")
                    f.write("\n")

            f.write(f" */\n")

            if not message.fields and parent_ts_interface_name:
                f.write(f"export type {ts_interface_name} = {parent_ts_interface_name};\n\n")
            else:
                if parent_ts_interface_name:
                    f.write(f"export interface {ts_interface_name} extends {parent_ts_interface_name} {{\n")
                else:
                    f.write(f"export interface {ts_interface_name} {{\n")

                for field in message.fields:
                    self._write_field(f, message_name, field)

                f.write("}\n\n")

    def _get_ts_type(self, field: Field, message_name: str) -> str:
        """
        Get the TypeScript type for a field.

        Args:
            field: The field to get the type for
            message_name: The original name of the message containing the field (may contain ::)

        Returns:
            The TypeScript type as a string
        """
        if field.field_type == FieldType.ENUM:
            ts_message_name_part = message_name.replace("::", "_")
            enum_name = f"{ts_message_name_part}_{field.name}_Enum"
            return enum_name

        elif field.field_type == FieldType.OPTIONS:
            return "number"

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

        elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
            return "boolean"

        elif field.field_type == FieldType.BYTE:
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
        optional_text = " (optional)" if field.optional else ""
        default_text = f" default({field.default_value})" if field.default_value is not None else ""

        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name.replace('::', '_')}_{field.name}_Enum"
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
            return f"Integer (number){optional_text}{default_text}"

        elif field.field_type == FieldType.FLOAT:
            return f"Float (number){optional_text}{default_text}"

        elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
            return f"Boolean{optional_text}{default_text}"

        elif field.field_type == FieldType.BYTE:
            return f"Byte (0-255){optional_text}{default_text}"

        else:
            return f"Unknown ({field.field_type}){optional_text}{default_text}"

    def _write_field(self, f: TextIO, message_name: str, field: Field, indent: str = "  ") -> None:
        """
        Write a field definition.

        Args:
            f: The file to write to
            message_name: The original name of the message containing the field (may contain ::)
            field: The field to write
            indent: The indentation to use
        """
        field_indent = indent
        optional_mark = "?" if field.optional else ""

        if field.comment:
            f.write(f"{field_indent}/**\n")
            comment_lines = field.comment.split('\n')
            for line in comment_lines:
                f.write(f"{field_indent} * {line}\n")
            if field.default_value is not None:
                if isinstance(field.default_value, bool):
                    default_value = "true" if field.default_value else "false"
                else:
                    default_value = field.default_value
                f.write(f"{field_indent} * @default {default_value}\n")
            f.write(f"{field_indent} */\n")
        elif field.description:
            if field.default_value is not None:
                if isinstance(field.default_value, bool):
                    default_value = "true" if field.default_value else "false"
                else:
                    default_value = field.default_value
                f.write(f"{field_indent}/** {field.description} @default {default_value} */\n")
            else:
                f.write(f"{field_indent}/** {field.description} */\n")
        else:
            field_type_desc = self._get_field_type_description(field, message_name)
            f.write(f"{field_indent}/** {field_type_desc} */\n")

        if field.field_type == FieldType.ENUM:
            ts_message_name_part = message_name.replace("::", "_")
            enum_name = f"{ts_message_name_part}_{field.name}_Enum"
            f.write(f"{field_indent}{field.name}{optional_mark}: {enum_name};\n")

        elif field.field_type == FieldType.OPTIONS:
            f.write(f"{field_indent}{field.name}{optional_mark}: number;\n")

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                f.write(f"{field_indent}{field.name}{optional_mark}: {{\n")
                for component in field.compound_components:
                    f.write(f"{field_indent}    /** {component} component */\n")
                    f.write(f"{field_indent}    {component}: number;\n")
                f.write(f"{field_indent}}};\n")
            else:
                f.write(f"{field_indent}// Unsupported compound type: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"{field_indent}{field.name}{optional_mark}: string;\n")

        elif field.field_type == FieldType.INT or field.field_type == FieldType.FLOAT:
            f.write(f"{field_indent}{field.name}{optional_mark}: number;\n")

        elif field.field_type == FieldType.BOOLEAN or field.field_type == FieldType.BOOL:
            f.write(f"{field_indent}{field.name}{optional_mark}: boolean;\n")

        elif field.field_type == FieldType.BYTE:
            f.write(f"{field_indent}{field.name}{optional_mark}: number;\n")

        else:
            f.write(f"{field_indent}// Unsupported type: {field.field_type}\n")
