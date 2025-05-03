"""
C++ Generator

This module provides functionality for generating C++ code from the
intermediate representation defined in message_model.py.
It supports both Unreal Engine C++ and standard C++ code generation.
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


class BaseCppGenerator:
    """
    Base generator for C++ code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str, output_name: str = None):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
            output_name: Base name for output files without extension (default: "Messages")
        """
        self.model = model
        self.output_dir = output_dir
        self.output_name = output_name if output_name else "Messages"

    def _write_namespace_start(self, f: TextIO) -> None:
        """
        Write the start of the namespace.

        Args:
            f: The file to write to
        """
        f.write(f"namespace {self.output_name} {{\n\n")

        # We don't write nested namespaces here anymore
        # They will be written as needed when writing structs and enums

    def _write_namespace_end(self, f: TextIO) -> None:
        """
        Write the end of the namespace.

        Args:
            f: The file to write to
        """
        # We don't close nested namespaces here anymore
        # They will be closed as needed when writing structs and enums

        f.write(f"}} // namespace {self.output_name}\n")

    def _write_forward_declarations(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write forward declarations for all structs.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        # Group messages by namespace
        global_messages = []
        namespaced_messages = {}

        for message_name, message in model.messages.items():
            # Skip the "Base" namespace for messages in the base file
            # This namespace is added by the import statement but shouldn't be in the generated base file
            if message.namespace == "Base" and message.source_file and os.path.basename(message.source_file).startswith("sh4c_base"):
                global_messages.append(message.name)
            elif message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                namespaced_messages[message.namespace].append(message.name)
            else:
                global_messages.append(message.name)

        # Write forward declarations for global messages
        for message_name in global_messages:
            f.write(f"    struct {message_name};\n")

        # Write forward declarations for namespaced messages
        for namespace_name, messages in namespaced_messages.items():
            f.write(f"    namespace {namespace_name} {{\n")
            for message_name in messages:
                f.write(f"        struct {message_name};\n")
            f.write(f"    }} // namespace {namespace_name}\n")

        f.write("\n")


class UnrealCppGenerator(BaseCppGenerator):
    """
    Generator for Unreal Engine C++ code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str, output_name: str = None):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
            output_name: Base name for output files without extension (default: "Messages")
        """
        super().__init__(model, output_dir, output_name)

    def _write_namespace_start(self, f: TextIO, output_base_name=None) -> None:
        """
        Write the start of the namespace, using the ue_ prefix.

        Args:
            f: The file to write to
            output_base_name: Optional base name to use for the namespace (defaults to self.output_name)
        """
        namespace_name = output_base_name if output_base_name else self.output_name
        f.write(f"namespace ue_{namespace_name} {{\n")

    def _write_namespace_end(self, f: TextIO, output_base_name=None) -> None:
        """
        Write the end of the namespace, using the ue_ prefix.

        Args:
            f: The file to write to
            output_base_name: Optional base name to use for the namespace (defaults to self.output_name)
        """
        namespace_name = output_base_name if output_base_name else self.output_name
        f.write(f"}} // namespace ue_{namespace_name}\n")

    def generate(self) -> bool:
        """
        Generate Unreal Engine C++ code from the message model.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating Unreal C++ output in: {self.output_dir}")

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

            # Track generated files for include statements
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

                # Add ue_ prefix for Unreal C++ files
                header_file = os.path.join(self.output_dir, f"ue_{output_base_name}_msgs.h")
                generated_files[source_file] = header_file

                # Create a filtered model with only the messages from this source file
                filtered_model = MessageModel()
                for message in messages:
                    filtered_model.add_message(message)

                # Add standalone enums to the filtered model, but only from the current file
                for enum_name, enum in self.model.enums.items():
                    if enum.source_file == source_file:
                        filtered_model.add_enum(enum)

                # Generate the header file
                with open(header_file, 'w') as f:
                    self._write_header(f)

                    # Add include statements for parent messages that are in other files
                    self._write_file_includes(f, messages, messages_by_source, generated_files)

                    self._write_namespace_start(f, output_base_name)
                    f.write("\n")  # Add a newline after the namespace declaration

                    self._write_enums(f, filtered_model)

                    self._write_forward_declarations(f, filtered_model)
                    self._write_structs(f, filtered_model)

                    # Only write serialization utils in the main file
                    if source_file == main_file:
                        self._write_serialization_utils(f)

                    self._write_namespace_end(f, output_base_name)

                print(f"Generated Unreal C++ header file: {header_file}")

            return True

        except Exception as e:
            print(f"Error generating Unreal C++ output: {str(e)}")
            return False

    def _write_file_includes(self, f: TextIO, messages: list, messages_by_source: dict, generated_files: dict) -> None:
        """
        Write include statements for parent messages that are in other files.

        Args:
            f: The file to write to
            messages: List of messages in the current file
            messages_by_source: Dictionary mapping source files to lists of messages
            generated_files: Dictionary mapping source files to generated header files
        """
        # Track needed includes and namespace aliases
        needed_includes = set()
        namespace_aliases = {}

        # We'll collect namespace aliases as we process parent references

        # Check each message for parent references to messages in other files
        for message in messages:
            if message.parent:
                # Check if the parent reference contains a namespace
                if '::' in message.parent:
                    namespace, _ = message.parent.split('::', 1)

                # Find the parent message
                parent_message = None
                for source_file, source_messages in messages_by_source.items():
                    for source_message in source_messages:
                        if source_message.get_full_name() == message.parent:
                            parent_message = source_message
                            break
                    if parent_message:
                        break

                # If parent is in a different file, add an include
                if parent_message and parent_message.source_file != message.source_file:
                    parent_source = parent_message.source_file
                    if parent_source in generated_files:
                        # Get the header file name from the generated file path
                        parent_header = os.path.basename(generated_files[parent_source])
                        needed_includes.add(parent_header)

                        # Extract the base name for namespace alias
                        # Keep 'ue_' prefix but remove '_msgs.h' suffix
                        if parent_header.startswith('ue_') and parent_header.endswith('_msgs.h'):
                            # Get the base name from the parent header file (without extension)
                            base_name = os.path.splitext(os.path.basename(parent_source))[0]
                            # Store the namespace alias for this include
                            if parent_message.namespace:
                                # If the namespace is "Base", it's a special case for import aliases
                                if parent_message.namespace == "Base":
                                    namespace_aliases["Base"] = f"ue_{base_name}"
                                else:
                                    namespace_aliases[parent_message.namespace] = f"ue_{base_name}"

        # Write include statements
        for header in sorted(needed_includes):
            f.write(f"#include \"{header}\"\n")

        if needed_includes:
            f.write("\n")

        # Write namespace aliases
        for namespace, base_name in namespace_aliases.items():
            f.write(f"namespace {namespace} = {base_name};\n")

        if namespace_aliases:
            f.write("\n")

    def _write_header(self, f: TextIO) -> None:
        """
        Write the header section of the C++ file.

        Args:
            f: The file to write to
        """
        f.write("// Auto-generated message definitions for Unreal Engine C++\n")
        f.write("// This file contains message definitions for communication between systems.\n")
        f.write("//\n")
        f.write("// DOCUMENTATION FOR MESSAGE FORMAT:\n")
        f.write("// ===============================\n")
        f.write("// This file defines a set of message structures used for communication.\n")
        f.write(f"// Each message is defined as a C++ struct within the ue_{self.output_name} namespace.\n")
        f.write("//\n")
        f.write("// Message Structure:\n")
        f.write("// - Messages are defined as structs with specific fields\n")
        f.write("// - Messages can inherit from other messages using standard C++ inheritance\n")
        f.write("// - Messages can be organized into namespaces for logical grouping\n")
        f.write("// - Fields can be of the following types:\n")
        f.write("//   * Basic types: int32 (integer), float, FString (string), bool (boolean), uint8 (byte)\n")
        f.write("//   * Enum types: defined as enum class with uint8 underlying type\n")
        f.write("//   * Options types: defined as enum class with uint32 underlying type, can be combined with bitwise OR\n")
        f.write("//   * Compound types: struct with named components\n")
        f.write("//\n")
        f.write("// Field Modifiers:\n")
        f.write("// - Optional fields: Fields that can be omitted from messages\n")
        f.write("//   * Optional fields are documented in comments\n")
        f.write("//   * Deserialization code doesn't fail if optional fields are missing\n")
        f.write("// - Default values: Fields can have default values that are used when not explicitly set\n")
        f.write("//   * Default values are initialized in the struct definition\n")
        f.write("//   * For enums, the default value is the enum value name\n")
        f.write("//   * For options, the default value can be a single option or a combination (e.g., OptionA | OptionB)\n")
        f.write("//   * Default values are used when deserializing if the field is missing from the JSON\n")
        f.write("//\n")
        f.write("// Enum Naming Convention:\n")
        f.write("// - Enums are named as MessageName_fieldName_Enum\n")
        f.write("//\n")
        f.write("// Options Naming Convention:\n")
        f.write("// - Options are named as MessageName_fieldName_Options\n")
        f.write("// - Options are bit flags that can be combined using the bitwise OR operator (|)\n")
        f.write("//\n")
        f.write("// Compound Field Structure:\n")
        f.write("// - Compound fields are defined as anonymous structs within the message\n")
        f.write("// - Each component is a named field within the anonymous struct\n")
        f.write("// - Currently supports float compounds with named components (e.g., position with x, y, z)\n")
        f.write("//\n")
        f.write("// JSON Serialization:\n")
        f.write("// ================\n")
        f.write("// Each message struct includes ToJson() and FromJson() methods for serialization and deserialization.\n")
        f.write("// - ToJson(): Converts the message to a JSON object\n")
        f.write("// - FromJson(): Populates the message from a JSON object\n")
        f.write("//\n")
        f.write("// The MessageSerialization namespace provides utility functions for working with messages:\n")
        f.write("// - RegisterMessageTypes(): Registers all message types for dynamic creation and parsing\n")
        f.write("// - SerializeMessage(): Serializes a message to a JSON string with message type\n")
        f.write("// - DeserializeMessage(): Deserializes a JSON string to a message object\n")
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
        f.write("// 1. Create a parser that can deserialize data into these structs\n")
        f.write("// 2. For each message type, implement a handler function\n")
        f.write("// 3. Use a dispatcher to route messages to the appropriate handler based on message type\n")
        f.write("// 4. For inheritance, ensure parent fields are processed before child fields\n")
        f.write("//\n")
        f.write("#pragma once\n\n")
        f.write("#include \"CoreMinimal.h\"\n")
        f.write("#include \"Dom/JsonObject.h\"\n")
        f.write("#include \"Serialization/JsonSerializer.h\"\n\n")

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

        # Group standalone enums by namespace
        global_enums = []
        namespaced_enums = {}

        for enum_name, enum in model.enums.items():
            if enum.namespace:
                if enum.namespace not in namespaced_enums:
                    namespaced_enums[enum.namespace] = []
                namespaced_enums[enum.namespace].append(enum)
            else:
                global_enums.append(enum)

        # Write standalone enums for global scope
        for enum in global_enums:
            if enum.name not in enums_generated:
                f.write(f"    // Standalone enum {enum.name}\n")
                # Determine the appropriate size for the enum
                size_bits = enum.get_min_size_bits()
                if enum.is_open:
                    f.write(f"    enum {enum.name} : uint{size_bits}\n")
                else:
                    f.write(f"    enum class {enum.name} : uint{size_bits}\n")
                f.write("    {\n")
                for enum_value in enum.values:
                    f.write(f"        {enum_value.name} = {enum_value.value},\n")
                f.write("    };\n\n")
                enums_generated.add(enum.name)

        # Write standalone enums for namespaced scope
        for namespace_name, enums in namespaced_enums.items():
            f.write(f"    namespace {namespace_name} {{\n")
            for enum in enums:
                if enum.name not in enums_generated:
                    f.write(f"        // Standalone enum {enum.name}\n")
                    # Determine the appropriate size for the enum
                    size_bits = enum.get_min_size_bits()
                    if enum.is_open:
                        f.write(f"        enum {enum.name} : uint{size_bits}\n")
                    else:
                        f.write(f"        enum class {enum.name} : uint{size_bits}\n")
                    f.write("        {\n")
                    for enum_value in enum.values:
                        f.write(f"            {enum_value.name} = {enum_value.value},\n")
                    f.write("        };\n\n")
                    enums_generated.add(enum.name)
            f.write(f"    }} // namespace {namespace_name}\n\n")

        # Group messages by namespace
        global_messages = []
        global_message_field_enums = []  # Separate list for global message field enums
        namespaced_messages = {}
        # Also track message field enums by namespace
        message_field_enums = {}

        # First, collect all messages and their field enums
        for message_name, message in model.messages.items():
            # Skip the "Base" namespace for messages in the base file
            # This namespace is added by the import statement but shouldn't be in the generated base file
            if message.namespace == "Base" and message.source_file and os.path.basename(message.source_file).startswith("sh4c_base"):
                global_messages.append(message)
            elif message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                    message_field_enums[message.namespace] = []
                namespaced_messages[message.namespace].append(message)
            else:
                global_messages.append(message)

        # Now, collect all field enums for all messages
        for message_name, message in model.messages.items():
            # Skip messages in the "Base" namespace for the base file
            if message.namespace == "Base" and message.source_file and os.path.basename(message.source_file).startswith("sh4c_base"):
                continue

            # Determine the namespace for this message's field enums
            namespace = message.namespace
            if namespace:
                # For messages with a namespace, add their field enums to that namespace
                if namespace not in message_field_enums:
                    message_field_enums[namespace] = []

                for field in message.fields:
                    if field.field_type == FieldType.ENUM:
                        enum_name = f"{message.name}_{field.name}_Enum"
                        if enum_name not in enums_generated:
                            message_field_enums[namespace].append((message, field, enum_name))
                    elif field.field_type == FieldType.OPTIONS:
                        enum_name = f"{message.name}_{field.name}_Options"
                        if enum_name not in enums_generated:
                            message_field_enums[namespace].append((message, field, enum_name))
            else:
                # For messages without a namespace, add their field enums to the global scope
                for field in message.fields:
                    if field.field_type == FieldType.ENUM:
                        enum_name = f"{message.name}_{field.name}_Enum"
                        if enum_name not in enums_generated:
                            global_message_field_enums.append((message, field, enum_name))
                    elif field.field_type == FieldType.OPTIONS:
                        enum_name = f"{message.name}_{field.name}_Options"
                        if enum_name not in enums_generated:
                            global_message_field_enums.append((message, field, enum_name))

        # Write enums for global messages
        for message in global_messages:
            for field in message.fields:
                if field.field_type == FieldType.ENUM:
                    enum_name = f"{message.name}_{field.name}_Enum"
                    if enum_name not in enums_generated:
                        f.write(f"    // Enum for {message.name}.{field.name}\n")
                        # Create a temporary enum object to determine the size
                        temp_enum = Enum(enum_name, field.enum_values)
                        size_bits = temp_enum.get_min_size_bits()
                        f.write(f"    enum class {enum_name} : uint{size_bits}\n")
                        f.write("    {\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    };\n\n")
                        enums_generated.add(enum_name)
                elif field.field_type == FieldType.OPTIONS:
                    enum_name = f"{message.name}_{field.name}_Options"
                    if enum_name not in enums_generated:
                        f.write(f"    // Options for {message.name}.{field.name}\n")
                        # Options are always uint32 as they're used as bit flags
                        f.write(f"    enum class {enum_name} : uint32\n")
                        f.write("    {\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    };\n\n")
                        enums_generated.add(enum_name)

        # Write enums for global message fields
        for message, field, enum_name in global_message_field_enums:
            if field.field_type == FieldType.ENUM:
                if enum_name not in enums_generated:
                    f.write(f"    // Enum for {message.name}.{field.name}\n")
                    # Create a temporary enum object to determine the size
                    temp_enum = Enum(enum_name, field.enum_values)
                    size_bits = temp_enum.get_min_size_bits()
                    f.write(f"    enum class {enum_name} : uint{size_bits}\n")
                    f.write("    {\n")
                    for enum_value in field.enum_values:
                        f.write(f"        {enum_value.name} = {enum_value.value},\n")
                    f.write("    };\n\n")
                    enums_generated.add(enum_name)
            elif field.field_type == FieldType.OPTIONS:
                if enum_name not in enums_generated:
                    f.write(f"    // Options for {message.name}.{field.name}\n")
                    # Options are always uint32 as they're used as bit flags
                    f.write(f"    enum class {enum_name} : uint32\n")
                    f.write("    {\n")
                    for enum_value in field.enum_values:
                        f.write(f"        {enum_value.name} = {enum_value.value},\n")
                    f.write("    };\n\n")
                    enums_generated.add(enum_name)

        # Write enums for namespaced messages
        for namespace_name, messages in namespaced_messages.items():
            # Check if we've already written this namespace
            if namespace_name not in namespaced_enums:
                f.write(f"    namespace {namespace_name} {{\n")
                namespace_written = False
            else:
                namespace_written = True

            # Write message field enums for this namespace
            for message, field, enum_name in message_field_enums.get(namespace_name, []):
                if enum_name not in enums_generated:
                    if field.field_type == FieldType.ENUM:
                        f.write(f"        // Enum for {message.name}.{field.name}\n")
                        # Create a temporary enum object to determine the size
                        temp_enum = Enum(enum_name, field.enum_values)
                        size_bits = temp_enum.get_min_size_bits()
                        f.write(f"        enum class {enum_name} : uint{size_bits}\n")
                        f.write("        {\n")
                        for enum_value in field.enum_values:
                            f.write(f"            {enum_value.name} = {enum_value.value},\n")
                        f.write("        };\n\n")
                        enums_generated.add(enum_name)
                    elif field.field_type == FieldType.OPTIONS:
                        f.write(f"        // Options for {message.name}.{field.name}\n")
                        # Options are always uint32 as they're used as bit flags
                        f.write(f"        enum class {enum_name} : uint32\n")
                        f.write("        {\n")
                        for enum_value in field.enum_values:
                            f.write(f"            {enum_value.name} = {enum_value.value},\n")
                        f.write("        };\n\n")
                        enums_generated.add(enum_name)

            # Only close the namespace if we opened it
            if not namespace_written:
                f.write(f"    }} // namespace {namespace_name}\n\n")

        # All message field enums should now be written

    def _write_serialization_utils(self, f: TextIO) -> None:
        """
        Write utility functions for message serialization and deserialization.

        Args:
            f: The file to write to
        """
        f.write("    // Message serialization utilities\n")
        f.write("    namespace MessageSerialization {\n\n")

        # Write message type registry
        f.write("        // Registry of message types to their creation functions\n")
        f.write("        using MessageCreationFunc = TFunction<TSharedPtr<FJsonObject>()>;\n")
        f.write("        using MessageParseFunc = TFunction<bool(const TSharedPtr<FJsonObject>&, void*)>;\n\n")

        f.write("        // Registry of message types\n")
        f.write("        struct MessageTypeInfo {\n")
        f.write("            FString TypeName;\n")
        f.write("            MessageCreationFunc CreateFunc;\n")
        f.write("            MessageParseFunc ParseFunc;\n")
        f.write("        };\n\n")

        f.write("        // Get the registry of message types\n")
        f.write("        inline TMap<FString, MessageTypeInfo>& GetMessageRegistry() {\n")
        f.write("            static TMap<FString, MessageTypeInfo> Registry;\n")
        f.write("            return Registry;\n")
        f.write("        }\n\n")

        # Write registration function for each message type
        f.write("        // Register all message types\n")
        f.write("        inline void RegisterMessageTypes() {\n")
        f.write("            static bool Registered = false;\n")
        f.write("            if (Registered) return;\n")
        f.write("            Registered = true;\n\n")

        f.write("            TMap<FString, MessageTypeInfo>& Registry = GetMessageRegistry();\n\n")

        # Register each message type
        for message_name in self.model.messages:
            f.write(f"            // Register {message_name}\n")
            f.write(f"            Registry.Add(\"{message_name}\", {{\n")
            f.write(f"                \"{message_name}\",\n")
            f.write(f"                []() -> TSharedPtr<FJsonObject> {{ return MakeShared<{message_name}>()->ToJson(); }},\n")
            f.write(f"                [](const TSharedPtr<FJsonObject>& Json, void* OutMsg) -> bool {{ \n")
            f.write(f"                    return {message_name}::FromJson(Json, *static_cast<{message_name}*>(OutMsg)); \n")
            f.write(f"                }}\n")
            f.write(f"            }});\n\n")

        f.write("        }\n\n")

        # Write serialization function
        f.write("        // Serialize a message to JSON string with a message type\n")
        f.write("        template<typename T>\n")
        f.write("        FString SerializeMessage(const FString& MessageType, const T& Message) {\n")
        f.write("            // Create the envelope\n")
        f.write("            TSharedPtr<FJsonObject> EnvelopeObj = MakeShared<FJsonObject>();\n")
        f.write("            EnvelopeObj->SetStringField(\"messageType\", MessageType);\n")
        f.write("            \n")
        f.write("            // Convert Message to JSON\n")
        f.write("            TSharedPtr<FJsonObject> PayloadObj = Message.ToJson();\n")
        f.write("            EnvelopeObj->SetObjectField(\"payload\", PayloadObj);\n")
        f.write("            \n")
        f.write("            // Serialize to string\n")
        f.write("            FString OutputString;\n")
        f.write("            TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);\n")
        f.write("            FJsonSerializer::Serialize(EnvelopeObj.ToSharedRef(), Writer);\n")
        f.write("            \n")
        f.write("            return OutputString;\n")
        f.write("        }\n\n")

        # Write deserialization function
        f.write("        // Deserialize a JSON string to a message object\n")
        f.write("        template<typename T>\n")
        f.write("        bool DeserializeMessage(const FString& JsonString, FString& OutMessageType, T& OutMessage) {\n")
        f.write("            // Parse the JSON string\n")
        f.write("            TSharedPtr<FJsonObject> EnvelopeObj;\n")
        f.write("            TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<>::Create(JsonString);\n")
        f.write("            if (!FJsonSerializer::Deserialize(Reader, EnvelopeObj) || !EnvelopeObj.IsValid()) {\n")
        f.write("                return false;\n")
        f.write("            }\n")
        f.write("            \n")
        f.write("            // Extract message type\n")
        f.write("            if (!EnvelopeObj->TryGetStringField(StringCast<TCHAR>(\"messageType\").Get(), OutMessageType)) {\n")
        f.write("                return false;\n")
        f.write("            }\n")
        f.write("            \n")
        f.write("            // Extract payload\n")
        f.write("            const TSharedPtr<FJsonObject>* PayloadObjPtr;\n")
        f.write("            if (!EnvelopeObj->TryGetObjectField(StringCast<TCHAR>(\"payload\").Get(), PayloadObjPtr)) {\n")
        f.write("                return false;\n")
        f.write("            }\n")
        f.write("            \n")
        f.write("            // Deserialize payload to message\n")
        f.write("            return T::FromJson(*PayloadObjPtr, OutMessage);\n")
        f.write("        }\n")

        f.write("    } // namespace MessageSerialization\n\n")

    def _write_structs(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write struct definitions with JSON serialization methods.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        # Group messages by namespace
        global_messages = []
        namespaced_messages = {}

        for message_name, message in model.messages.items():
            # Skip the "Base" namespace for messages in the base file
            # This namespace is added by the import statement but shouldn't be in the generated base file
            if message.namespace == "Base" and message.source_file and os.path.basename(message.source_file).startswith("sh4c_base"):
                global_messages.append(message)
            elif message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                namespaced_messages[message.namespace].append(message)
            else:
                global_messages.append(message)

        # Write structs for global messages
        for message in global_messages:
            self._write_struct(f, message, "    ", "")

        # Write structs for namespaced messages
        for namespace_name, messages in namespaced_messages.items():
            f.write(f"    namespace {namespace_name} {{\n\n")
            for message in messages:
                self._write_struct(f, message, "        ", namespace_name)
            f.write(f"    }} // namespace {namespace_name}\n\n")

    def _write_struct(self, f: TextIO, message: Message, indent: str, namespace: str) -> None:
        """
        Write a struct definition with JSON serialization methods.

        Args:
            f: The file to write to
            message: The message to write
            indent: The indentation to use
            namespace: The namespace of the message (empty for global messages)
        """
        # Write detailed documentation for the message
        f.write(f"{indent}/**\n")
        f.write(f"{indent} * @struct {message.name}\n")
        if message.description:
            f.write(f"{indent} * @brief {message.description}\n")
        else:
            f.write(f"{indent} * @brief Message definition for {message.name}\n")

        # Include user-supplied comment if available
        if message.comment:
            # Split multi-line comments and format each line
            comment_lines = message.comment.split('\n')
            for line in comment_lines:
                f.write(f"{indent} * {line}\n")

        if message.parent:
            # If parent is in a namespace, include the namespace in the parent name
            parent_message = self.model.get_message(message.parent)

            # Check if parent message is in the same file as this message
            same_file = parent_message and parent_message.source_file and message.source_file and parent_message.source_file == message.source_file

            if parent_message and parent_message.namespace and not same_file:
                # Use the namespace directly without the output_name prefix
                parent_name = f"{parent_message.namespace}::{parent_message.name}"
            else:
                # If the parent message is not found, doesn't have a namespace, or is in the same file,
                # try to extract the namespace from the parent name
                if '::' in message.parent and not same_file:
                    namespace_name, message_name = message.parent.split('::', 1)
                    # Use the namespace directly
                    parent_name = message.parent
                else:
                    # If the parent is in the same file or doesn't have a namespace,
                    # use just the message name without the namespace
                    if '::' in message.parent:
                        parent_name = message.parent.split("::", 1)[1]
                    else:
                        parent_name = message.parent

            f.write(f"{indent} * @extends {parent_name}\n")

        # Document all fields in the message
        if message.fields:
            f.write(f"{indent} *\n")
            f.write(f"{indent} * @details Fields:\n")
            for field in message.fields:
                field_type_str = self._get_field_type_description(field, message.name)
                f.write(f"{indent} * - {field.name}: {field_type_str}")
                if field.description:
                    f.write(f" - {field.description}")
                f.write("\n")

        f.write(f"{indent} */\n")

        # Handle inheritance
        if message.parent:
            # If parent is in a namespace, include the namespace in the parent name
            parent_message = self.model.get_message(message.parent)

            # Check if parent message is in the same file as this message
            same_file = parent_message and parent_message.source_file and message.source_file and parent_message.source_file == message.source_file

            if parent_message and parent_message.namespace and not same_file:
                # Use the namespace directly without the output_name prefix
                parent_name = f"{parent_message.namespace}::{parent_message.name}"
            else:
                # If the parent message is not found, doesn't have a namespace, or is in the same file,
                # try to extract the namespace from the parent name
                if '::' in message.parent and not same_file:
                    # Use the namespace directly
                    parent_name = message.parent
                else:
                    # If the parent is in the same file or doesn't have a namespace,
                    # use just the message name without the namespace
                    if '::' in message.parent:
                        parent_name = message.parent.split("::", 1)[1]
                    else:
                        parent_name = message.parent

            f.write(f"{indent}struct {message.name} : public {parent_name}\n")
        else:
            f.write(f"{indent}struct {message.name}\n")

        f.write(f"{indent}{{\n")

        # Generate fields
        for field in message.fields:
            self._write_field(f, message.name, field, indent + "    ")

        # Add ToJson method
        f.write(f"\n{indent}    /**\n")
        f.write(f"{indent}     * Convert this message to a JSON object\n")
        f.write(f"{indent}     * @return JSON object representation of this message\n")
        f.write(f"{indent}     */\n")
        f.write(f"{indent}    TSharedPtr<FJsonObject> ToJson() const {{\n")
        f.write(f"{indent}        TSharedPtr<FJsonObject> JsonObj = MakeShared<FJsonObject>();\n")

        # If this message inherits from another, call the parent's ToJson method
        if message.parent:
            # If parent is in a namespace, include the namespace in the parent name
            parent_message = self.model.get_message(message.parent)

            # Check if parent message is in the same file as this message
            same_file = parent_message and parent_message.source_file and message.source_file and parent_message.source_file == message.source_file

            if parent_message and parent_message.namespace and not same_file:
                # Use the namespace directly without the output_name prefix
                parent_name = f"{parent_message.namespace}::{parent_message.name}"
            else:
                # If the parent message is not found, doesn't have a namespace, or is in the same file,
                # try to extract the namespace from the parent name
                if '::' in message.parent and not same_file:
                    # Use the namespace directly
                    parent_name = message.parent
                else:
                    # If the parent is in the same file or doesn't have a namespace,
                    # use just the message name without the namespace
                    if '::' in message.parent:
                        parent_name = message.parent.split("::", 1)[1]
                    else:
                        parent_name = message.parent

            f.write(f"{indent}        // Call parent class serialization\n")
            f.write(f"{indent}        TSharedPtr<FJsonObject> ParentJson = {parent_name}::ToJson();\n")
            f.write(f"{indent}        for (const auto& Pair : ParentJson->Values) {{\n")
            f.write(f"{indent}            JsonObj->SetField(Pair.Key, Pair.Value);\n")
            f.write(f"{indent}        }}\n\n")

        # Serialize each field
        for field in message.fields:
            self._write_field_serialization(f, message.name, field, indent + "        ")

        f.write(f"{indent}        return JsonObj;\n")
        f.write(f"{indent}    }}\n\n")

        # Add FromJson method
        f.write(f"{indent}    /**\n")
        f.write(f"{indent}     * Populate this message from a JSON object\n")
        f.write(f"{indent}     * @param JsonObject JSON object to parse\n")
        f.write(f"{indent}     * @param OutMessage Message to populate\n")
        f.write(f"{indent}     * @return True if parsing was successful, false otherwise\n")
        f.write(f"{indent}     */\n")
        f.write(f"{indent}    static bool FromJson(const TSharedPtr<FJsonObject>& JsonObject, {message.name}& OutMessage) {{\n")

        # If this message inherits from another, call the parent's FromJson method
        if message.parent:
            # If parent is in a namespace, include the namespace in the parent name
            parent_message = self.model.get_message(message.parent)

            # Check if parent message is in the same file as this message
            same_file = parent_message and parent_message.source_file and message.source_file and parent_message.source_file == message.source_file

            if parent_message and parent_message.namespace and not same_file:
                # Use the namespace directly without the output_name prefix
                parent_name = f"{parent_message.namespace}::{parent_message.name}"
            else:
                # If the parent message is not found, doesn't have a namespace, or is in the same file,
                # try to extract the namespace from the parent name
                if '::' in message.parent and not same_file:
                    # Use the namespace directly
                    parent_name = message.parent
                else:
                    # If the parent is in the same file or doesn't have a namespace,
                    # use just the message name without the namespace
                    if '::' in message.parent:
                        parent_name = message.parent.split("::", 1)[1]
                    else:
                        parent_name = message.parent

            f.write(f"{indent}        // Call parent class deserialization\n")
            f.write(f"{indent}        if (!{parent_name}::FromJson(JsonObject, OutMessage)) {{\n")
            f.write(f"{indent}            return false;\n")
            f.write(f"{indent}        }}\n\n")

        # Deserialize each field
        for field in message.fields:
            self._write_field_deserialization(f, message.name, field, indent + "        ")

        f.write(f"{indent}        return true;\n")
        f.write(f"{indent}    }}\n")

        f.write(f"{indent}}};\n\n")

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
            enum_name = f"{message_name}_{field.name}_Options"
            return f"Options ({enum_name}){optional_text}{default_text}"

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                components = ", ".join(field.compound_components)
                return f"Compound ({components}){optional_text}{default_text}"
            else:
                return f"Compound ({field.compound_base_type}){optional_text}{default_text}"

        elif field.field_type == FieldType.STRING:
            return f"String (FString){optional_text}{default_text}"

        elif field.field_type == FieldType.INT:
            return f"Integer (int32){optional_text}{default_text}"

        elif field.field_type == FieldType.FLOAT:
            return f"Float (float){optional_text}{default_text}"

        elif field.field_type == FieldType.BOOLEAN:
            return f"Boolean (bool){optional_text}{default_text}"

        elif field.field_type == FieldType.BYTE:
            return f"Byte (uint8){optional_text}{default_text}"

        else:
            return f"Unknown ({field.field_type}){optional_text}{default_text}"

    def _write_field(self, f: TextIO, message_name: str, field: Field, indent: str) -> None:
        """
        Write a field definition.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to write
            indent: The indentation to use
        """
        # Add documentation comment for the field
        if field.comment:
            # Use user-supplied comment if available
            f.write(f"{indent}/**\n")
            # Split multi-line comments and format each line
            comment_lines = field.comment.split('\n')
            for line in comment_lines:
                f.write(f"{indent} * {line}\n")
            f.write(f"{indent} */\n")
        elif field.description:
            f.write(f"{indent}/** {field.description} */\n")
        else:
            field_type_desc = self._get_field_type_description(field, message_name)
            f.write(f"{indent}/** {field_type_desc} field */\n")

        if field.field_type == FieldType.ENUM:
            # If the message is in a namespace, use the namespace in the enum name
            if "::" in message_name:
                namespace, msg_name = message_name.split("::", 1)
                enum_name = f"{msg_name}_{field.name}_Enum"
            else:
                enum_name = f"{message_name}_{field.name}_Enum"

            # Add default value if specified
            if field.default_value is not None:
                f.write(f"{indent}{enum_name} {field.name} = {enum_name}::{field.default_value};\n")
            else:
                f.write(f"{indent}{enum_name} {field.name};\n")

        elif field.field_type == FieldType.OPTIONS:
            # If the message is in a namespace, use the namespace in the enum name
            if "::" in message_name:
                namespace, msg_name = message_name.split("::", 1)
                enum_name = f"{msg_name}_{field.name}_Options"
            else:
                enum_name = f"{message_name}_{field.name}_Options"

            # Add default value if specified
            if field.default_value is not None:
                # For combined options, use the OR'ed enum values for readability
                if field.default_value_str and '&' in field.default_value_str:
                    option_names = [opt.strip() for opt in field.default_value_str.split('&')]
                    or_expression = " | ".join([f"{enum_name}::{name}" for name in option_names])
                    f.write(f"{indent}uint32 {field.name} = {or_expression}; // Combination of {enum_name} values\n")
                # For single option values or numeric values
                else:
                    # If the default value is a string (enum value name), use the enum value
                    if field.default_value_str and not field.default_value_str.isdigit():
                        f.write(f"{indent}uint32 {field.name} = {enum_name}::{field.default_value_str}; // {enum_name} value\n")
                    else:
                        # Use the numeric value directly
                        default_value = field.default_value
                        f.write(f"{indent}uint32 {field.name} = {default_value}; // Combination of {enum_name} values\n")
            else:
                f.write(f"{indent}uint32 {field.name} = 0;\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"{indent}struct {{\n")
                for component in field.compound_components:
                    f.write(f"{indent}    /** {component} component of {field.name} */\n")
                    f.write(f"{indent}    float {component};\n")
                f.write(f"{indent}}} {field.name};\n")
            else:
                # Handle other compound types if needed
                f.write(f"{indent}// Unsupported compound type: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            if field.default_value is not None:
                # Remove extra quotes and escape remaining quotes in the default value
                default_value = field.default_value
                if isinstance(default_value, str) and default_value.startswith('"') and default_value.endswith('"'):
                    default_value = default_value[1:-1]
                default_value = default_value.replace('"', '\\"')
                f.write(f"{indent}FString {field.name} = TEXT(\"{default_value}\");\n")
            else:
                f.write(f"{indent}FString {field.name};\n")

        elif field.field_type == FieldType.INT:
            if field.default_value is not None:
                f.write(f"{indent}int32 {field.name} = {field.default_value};\n")
            else:
                f.write(f"{indent}int32 {field.name};\n")

        elif field.field_type == FieldType.FLOAT:
            if field.default_value is not None:
                f.write(f"{indent}float {field.name} = {field.default_value}f;\n")
            else:
                f.write(f"{indent}float {field.name};\n")

        elif field.field_type == FieldType.BOOLEAN:
            if field.default_value is not None:
                # Convert Python bool to C++ bool
                bool_value = "true" if field.default_value else "false"
                f.write(f"{indent}bool {field.name} = {bool_value};\n")
            else:
                f.write(f"{indent}bool {field.name} = false;\n")

        elif field.field_type == FieldType.BYTE:
            if field.default_value is not None:
                f.write(f"{indent}uint8 {field.name} = {field.default_value};\n")
            else:
                f.write(f"{indent}uint8 {field.name} = 0;\n")

        else:
            f.write(f"{indent}// Unsupported type: {field.field_type}\n")

    def _write_field_serialization(self, f: TextIO, message_name: str, field: Field, indent: str) -> None:
        """
        Write code to serialize a field to JSON.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to serialize
            indent: The indentation to use
        """
        if field.field_type == FieldType.ENUM:
            f.write(f"{indent}JsonObj->SetNumberField(\"{field.name}\", static_cast<int32>({field.name}));\n")

        elif field.field_type == FieldType.OPTIONS:
            f.write(f"{indent}JsonObj->SetNumberField(\"{field.name}\", {field.name});\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"{indent}TSharedPtr<FJsonObject> {field.name}Obj = MakeShared<FJsonObject>();\n")
                for component in field.compound_components:
                    f.write(f"{indent}{field.name}Obj->SetNumberField(\"{component}\", {field.name}.{component});\n")
                f.write(f"{indent}JsonObj->SetObjectField(\"{field.name}\", {field.name}Obj);\n")
            else:
                # Handle other compound types if needed
                f.write(f"{indent}// Unsupported compound type serialization: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"{indent}JsonObj->SetStringField(\"{field.name}\", {field.name});\n")

        elif field.field_type == FieldType.INT:
            f.write(f"{indent}JsonObj->SetNumberField(\"{field.name}\", {field.name});\n")

        elif field.field_type == FieldType.FLOAT:
            f.write(f"{indent}JsonObj->SetNumberField(\"{field.name}\", {field.name});\n")

        elif field.field_type == FieldType.BOOLEAN:
            f.write(f"{indent}JsonObj->SetBoolField(\"{field.name}\", {field.name});\n")

        elif field.field_type == FieldType.BYTE:
            f.write(f"{indent}JsonObj->SetNumberField(\"{field.name}\", {field.name});\n")

        else:
            f.write(f"{indent}// Unsupported type serialization: {field.field_type}\n")

    def _write_field_deserialization(self, f: TextIO, message_name: str, field: Field, indent: str) -> None:
        """
        Write code to deserialize a field from JSON.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to deserialize
            indent: The indentation to use
        """
        if field.field_type == FieldType.ENUM:
            # If the message is in a namespace, use the namespace in the enum name
            if "::" in message_name:
                namespace, msg_name = message_name.split("::", 1)
                enum_name = f"{msg_name}_{field.name}_Enum"
            else:
                enum_name = f"{message_name}_{field.name}_Enum"
            f.write(f"{indent}int32 {field.name}Value;\n")
            f.write(f"{indent}if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    OutMessage.{field.name} = static_cast<{enum_name}>({field.name}Value);\n")
            f.write(f"{indent}}}\n")
            f.write(f"{indent}else\n")
            f.write(f"{indent}{{\n")
            if field.optional:
                f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
            elif field.default_value is not None:
                f.write(f"{indent}    // Use default value\n")
                f.write(f"{indent}    OutMessage.{field.name} = {enum_name}::{field.default_value};\n")
            else:
                f.write(f"{indent}    return false;\n")
            f.write(f"{indent}}}\n")

        elif field.field_type == FieldType.OPTIONS:
            # If the message is in a namespace, use the namespace in the enum name
            if "::" in message_name:
                namespace, msg_name = message_name.split("::", 1)
                enum_name = f"{msg_name}_{field.name}_Options"
            else:
                enum_name = f"{message_name}_{field.name}_Options"
            f.write(f"{indent}uint32 {field.name}Value;\n")
            f.write(f"{indent}if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    OutMessage.{field.name} = {field.name}Value;\n")
            f.write(f"{indent}}}\n")
            f.write(f"{indent}else\n")
            f.write(f"{indent}{{\n")
            if field.optional:
                f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
            elif field.default_value is not None:
                f.write(f"{indent}    // Use default value\n")
                # For combined options, use the OR'ed enum values for readability
                if field.default_value_str and '&' in field.default_value_str:
                    option_names = [opt.strip() for opt in field.default_value_str.split('&')]
                    or_expression = " | ".join([f"{enum_name}::{name}" for name in option_names])
                    f.write(f"{indent}    OutMessage.{field.name} = {or_expression}; // Combination of {enum_name} values\n")
                # For single option values or numeric values
                else:
                    # If the default value is a string (enum value name), use the enum value
                    if field.default_value_str and not field.default_value_str.isdigit():
                        f.write(f"{indent}    OutMessage.{field.name} = {enum_name}::{field.default_value_str}; // {enum_name} value\n")
                    else:
                        # Use the numeric value directly
                        f.write(f"{indent}    OutMessage.{field.name} = {field.default_value}; // Combination of {enum_name} values\n")
            else:
                f.write(f"{indent}    return false;\n")
            f.write(f"{indent}}}\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"{indent}const TSharedPtr<FJsonObject>* {field.name}Obj;\n")
                f.write(f"{indent}if (JsonObject->TryGetObjectField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Obj))\n")
                f.write(f"{indent}{{\n")
                for component in field.compound_components:
                    f.write(f"{indent}    double {component}Value;\n")
                    f.write(f"{indent}    if ((*{field.name}Obj)->TryGetNumberField(StringCast<TCHAR>(\"{component}\").Get(), {component}Value))\n")
                    f.write(f"{indent}    {{\n")
                    f.write(f"{indent}        OutMessage.{field.name}.{component} = static_cast<float>({component}Value);\n")
                    f.write(f"{indent}    }}\n")
                    f.write(f"{indent}    else\n")
                    f.write(f"{indent}    {{\n")
                    f.write(f"{indent}        return false;\n")
                    f.write(f"{indent}    }}\n")
                f.write(f"{indent}}}\n")
                f.write(f"{indent}else\n")
                f.write(f"{indent}{{\n")
                if field.optional:
                    f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
                elif field.default_value is not None:
                    f.write(f"{indent}    // Compound fields don't support default values yet\n")
                    f.write(f"{indent}    return false;\n")
                else:
                    f.write(f"{indent}    return false;\n")
                f.write(f"{indent}}}\n")
            else:
                # Handle other compound types if needed
                f.write(f"{indent}// Unsupported compound type deserialization: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"{indent}FString {field.name}Value;\n")
            f.write(f"{indent}if (JsonObject->TryGetStringField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    OutMessage.{field.name} = {field.name}Value;\n")
            f.write(f"{indent}}}\n")
            f.write(f"{indent}else\n")
            f.write(f"{indent}{{\n")
            if field.optional:
                f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
            elif field.default_value is not None:
                # Remove extra quotes and escape remaining quotes in the default value
                default_value = field.default_value
                if isinstance(default_value, str) and default_value.startswith('"') and default_value.endswith('"'):
                    default_value = default_value[1:-1]
                default_value = default_value.replace('"', '\\"')
                f.write(f"{indent}    // Use default value\n")
                f.write(f"{indent}    OutMessage.{field.name} = TEXT(\"{default_value}\");\n")
            else:
                f.write(f"{indent}    return false;\n")
            f.write(f"{indent}}}\n")

        elif field.field_type == FieldType.INT:
            f.write(f"{indent}int32 {field.name}Value;\n")
            f.write(f"{indent}if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    OutMessage.{field.name} = {field.name}Value;\n")
            f.write(f"{indent}}}\n")
            f.write(f"{indent}else\n")
            f.write(f"{indent}{{\n")
            if field.optional:
                f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
            elif field.default_value is not None:
                f.write(f"{indent}    // Use default value\n")
                f.write(f"{indent}    OutMessage.{field.name} = {field.default_value};\n")
            else:
                f.write(f"{indent}    return false;\n")
            f.write(f"{indent}}}\n")

        elif field.field_type == FieldType.FLOAT:
            f.write(f"{indent}double {field.name}Value;\n")
            f.write(f"{indent}if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    OutMessage.{field.name} = static_cast<float>({field.name}Value);\n")
            f.write(f"{indent}}}\n")
            f.write(f"{indent}else\n")
            f.write(f"{indent}{{\n")
            if field.optional:
                f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
            elif field.default_value is not None:
                f.write(f"{indent}    // Use default value\n")
                f.write(f"{indent}    OutMessage.{field.name} = {field.default_value}f;\n")
            else:
                f.write(f"{indent}    return false;\n")
            f.write(f"{indent}}}\n")

        elif field.field_type == FieldType.BOOLEAN:
            f.write(f"{indent}bool {field.name}Value;\n")
            f.write(f"{indent}if (JsonObject->TryGetBoolField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    OutMessage.{field.name} = {field.name}Value;\n")
            f.write(f"{indent}}}\n")
            f.write(f"{indent}else\n")
            f.write(f"{indent}{{\n")
            if field.optional:
                f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
            elif field.default_value is not None:
                bool_value = "true" if field.default_value else "false"
                f.write(f"{indent}    // Use default value\n")
                f.write(f"{indent}    OutMessage.{field.name} = {bool_value};\n")
            else:
                f.write(f"{indent}    return false;\n")
            f.write(f"{indent}}}\n")

        elif field.field_type == FieldType.BYTE:
            f.write(f"{indent}int32 {field.name}Value;\n")
            f.write(f"{indent}if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    OutMessage.{field.name} = static_cast<uint8>({field.name}Value);\n")
            f.write(f"{indent}}}\n")
            f.write(f"{indent}else\n")
            f.write(f"{indent}{{\n")
            if field.optional:
                f.write(f"{indent}    // Field is optional, so it's okay if it's missing\n")
            elif field.default_value is not None:
                f.write(f"{indent}    // Use default value\n")
                f.write(f"{indent}    OutMessage.{field.name} = {field.default_value};\n")
            else:
                f.write(f"{indent}    return false;\n")
            f.write(f"{indent}}}\n")

        else:
            f.write(f"{indent}// Unsupported type deserialization: {field.field_type}\n")


class StandardCppGenerator(BaseCppGenerator):
    """
    Generator for standard C++ code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str, output_name: str = None):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
            output_name: Base name for output files without extension (default: "Messages")
        """
        super().__init__(model, output_dir, output_name)

    def _write_namespace_start(self, f: TextIO, output_base_name=None) -> None:
        """
        Write the start of the namespace, using the c_ prefix.

        Args:
            f: The file to write to
            output_base_name: Optional base name to use for the namespace (defaults to self.output_name)
        """
        namespace_name = output_base_name if output_base_name else self.output_name
        f.write(f"namespace c_{namespace_name} {{\n\n")

    def _write_namespace_end(self, f: TextIO, output_base_name=None) -> None:
        """
        Write the end of the namespace, using the c_ prefix.

        Args:
            f: The file to write to
            output_base_name: Optional base name to use for the namespace (defaults to self.output_name)
        """
        namespace_name = output_base_name if output_base_name else self.output_name
        f.write(f"}} // namespace c_{namespace_name}\n")

    def generate(self) -> bool:
        """
        Generate standard C++ code from the message model.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating standard C++ output in: {self.output_dir}")

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

            # Track generated files for include statements
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

                # Add c_ prefix for standard C++ files
                header_file = os.path.join(self.output_dir, f"c_{output_base_name}_msgs.h")
                generated_files[source_file] = header_file

                # Create a filtered model with only the messages from this source file
                filtered_model = MessageModel()
                for message in messages:
                    filtered_model.add_message(message)

                # Add standalone enums to the filtered model, but only from the current file
                for enum_name, enum in self.model.enums.items():
                    if enum.source_file == source_file:
                        filtered_model.add_enum(enum)

                # Generate the header file
                with open(header_file, 'w') as f:
                    self._write_header(f)

                    # Add include statements for parent messages that are in other files
                    self._write_file_includes(f, messages, messages_by_source, generated_files)

                    self._write_namespace_start(f, output_base_name)
                    self._write_enums(f, filtered_model)
                    self._write_forward_declarations(f, filtered_model)
                    self._write_structs(f, filtered_model)
                    self._write_namespace_end(f, output_base_name)

                print(f"Generated standard C++ header file: {header_file}")

            return True

        except Exception as e:
            print(f"Error generating standard C++ output: {str(e)}")
            return False

    def _write_file_includes(self, f: TextIO, messages: list, messages_by_source: dict, generated_files: dict) -> None:
        """
        Write include statements for parent messages that are in other files.

        Args:
            f: The file to write to
            messages: List of messages in the current file
            messages_by_source: Dictionary mapping source files to lists of messages
            generated_files: Dictionary mapping source files to generated header files
        """
        # Track needed includes and namespace aliases
        needed_includes = set()
        namespace_aliases = {}

        # We'll collect namespace aliases as we process parent references

        # Check each message for parent references to messages in other files
        for message in messages:
            if message.parent:
                # Check if the parent reference contains a namespace
                if '::' in message.parent:
                    namespace, _ = message.parent.split('::', 1)

                # Find the parent message
                parent_message = None
                for source_file, source_messages in messages_by_source.items():
                    for source_message in source_messages:
                        if source_message.get_full_name() == message.parent:
                            parent_message = source_message
                            break
                    if parent_message:
                        break

                # If parent is in a different file, add an include
                if parent_message and parent_message.source_file != message.source_file:
                    parent_source = parent_message.source_file
                    if parent_source in generated_files:
                        # Get the header file name from the generated file path
                        parent_header = os.path.basename(generated_files[parent_source])
                        needed_includes.add(parent_header)

                        # Extract the base name for namespace alias
                        # Keep 'c_' prefix but remove '_msgs.h' suffix
                        if parent_header.startswith('c_') and parent_header.endswith('_msgs.h'):
                            # Get the base name from the parent header file (without extension)
                            base_name = os.path.splitext(os.path.basename(parent_source))[0]
                            # Store the namespace alias for this include
                            if parent_message.namespace:
                                # If the namespace is "Base", it's a special case for import aliases
                                if parent_message.namespace == "Base":
                                    namespace_aliases["Base"] = f"c_{base_name}"
                                else:
                                    namespace_aliases[parent_message.namespace] = f"c_{base_name}"

        # Write include statements
        for header in sorted(needed_includes):
            f.write(f"#include \"{header}\"\n")

        if needed_includes:
            f.write("\n")

        # Write namespace aliases
        for namespace, base_name in namespace_aliases.items():
            f.write(f"namespace {namespace} = {base_name};\n")

        if namespace_aliases:
            f.write("\n")

    def _write_header(self, f: TextIO) -> None:
        """
        Write the header section of the C++ file.

        Args:
            f: The file to write to
        """
        f.write("// Auto-generated message definitions for standard C++\n")
        f.write("// This file contains message definitions for communication between systems.\n")
        f.write("//\n")
        f.write("// DOCUMENTATION FOR MESSAGE FORMAT:\n")
        f.write("// ===============================\n")
        f.write("// This file defines a set of message structures used for communication.\n")
        f.write(f"// Each message is defined as a C++ struct within the c_{self.output_name} namespace.\n")
        f.write("//\n")
        f.write("// Message Structure:\n")
        f.write("// - Messages are defined as structs with specific fields\n")
        f.write("// - Messages can inherit from other messages using standard C++ inheritance\n")
        f.write("// - Messages can be organized into namespaces for logical grouping\n")
        f.write("// - Fields can be of the following types:\n")
        f.write("//   * Basic types: int32_t (integer), float, std::string (string), bool (boolean), uint8_t (byte)\n")
        f.write("//   * Enum types: defined as enum class with uint8_t underlying type\n")
        f.write("//   * Options types: defined as enum class with uint32_t underlying type, can be combined with bitwise OR\n")
        f.write("//   * Compound types: struct with named components\n")
        f.write("//\n")
        f.write("// Field Modifiers:\n")
        f.write("// - Optional fields: Fields that can be omitted from messages\n")
        f.write("//   * Optional fields are documented in comments\n")
        f.write("// - Default values: Fields can have default values that are used when not explicitly set\n")
        f.write("//   * Default values are initialized in the struct definition\n")
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
        f.write("// - Compound fields are defined as anonymous structs within the message\n")
        f.write("// - Each component is a named field within the anonymous struct\n")
        f.write("// - Currently supports float compounds with named components (e.g., position with x, y, z)\n")
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
        f.write("// 1. Create a parser that can deserialize data into these structs\n")
        f.write("// 2. For each message type, implement a handler function\n")
        f.write("// 3. Use a dispatcher to route messages to the appropriate handler based on message type\n")
        f.write("// 4. For inheritance, ensure parent fields are processed before child fields\n")
        f.write("//\n")
        f.write("#pragma once\n\n")
        f.write("#include <string>\n")
        f.write("#include <cstdint>\n\n")

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

        # Group standalone enums by namespace
        global_enums = []
        namespaced_enums = {}

        for enum_name, enum in model.enums.items():
            if enum.namespace:
                if enum.namespace not in namespaced_enums:
                    namespaced_enums[enum.namespace] = []
                namespaced_enums[enum.namespace].append(enum)
            else:
                global_enums.append(enum)

        # Write standalone enums for global scope
        for enum in global_enums:
            if enum.name not in enums_generated:
                f.write(f"    // Standalone enum {enum.name}\n")
                # Determine the appropriate size for the enum
                size_bits = enum.get_min_size_bits()
                if enum.is_open:
                    f.write(f"    enum {enum.name} : uint{size_bits}_t\n")
                else:
                    f.write(f"    enum class {enum.name} : uint{size_bits}_t\n")
                f.write("    {\n")
                for enum_value in enum.values:
                    f.write(f"        {enum_value.name} = {enum_value.value},\n")
                f.write("    };\n\n")
                enums_generated.add(enum.name)

        # Write standalone enums for namespaced scope
        for namespace_name, enums in namespaced_enums.items():
            f.write(f"    namespace {namespace_name} {{\n")
            for enum in enums:
                if enum.name not in enums_generated:
                    f.write(f"        // Standalone enum {enum.name}\n")
                    # Determine the appropriate size for the enum
                    size_bits = enum.get_min_size_bits()
                    if enum.is_open:
                        f.write(f"        enum {enum.name} : uint{size_bits}_t\n")
                    else:
                        f.write(f"        enum class {enum.name} : uint{size_bits}_t\n")
                    f.write("        {\n")
                    for enum_value in enum.values:
                        f.write(f"            {enum_value.name} = {enum_value.value},\n")
                    f.write("        };\n\n")
                    enums_generated.add(enum.name)
            f.write(f"    }} // namespace {namespace_name}\n\n")

        # Group messages by namespace
        global_messages = []
        namespaced_messages = {}

        for message_name, message in model.messages.items():
            # Skip the "Base" namespace for messages in the base file
            # This namespace is added by the import statement but shouldn't be in the generated base file
            if message.namespace == "Base" and message.source_file and os.path.basename(message.source_file).startswith("sh4c_base"):
                global_messages.append(message)
            elif message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                namespaced_messages[message.namespace].append(message)
            else:
                global_messages.append(message)

        # Write enums for global messages
        for message in global_messages:
            for field in message.fields:
                if field.field_type == FieldType.ENUM:
                    enum_name = f"{message.name}_{field.name}_Enum"
                    if enum_name not in enums_generated:
                        f.write(f"    // Enum for {message.name}.{field.name}\n")
                        # Create a temporary enum object to determine the size
                        temp_enum = Enum(enum_name, field.enum_values)
                        size_bits = temp_enum.get_min_size_bits()
                        f.write(f"    enum class {enum_name} : uint{size_bits}_t\n")
                        f.write("    {\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    };\n\n")
                        enums_generated.add(enum_name)
                elif field.field_type == FieldType.OPTIONS:
                    enum_name = f"{message.name}_{field.name}_Options"
                    if enum_name not in enums_generated:
                        f.write(f"    // Options for {message.name}.{field.name}\n")
                        # Options are always uint32_t as they're used as bit flags
                        f.write(f"    enum class {enum_name} : uint32_t\n")
                        f.write("    {\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    };\n\n")
                        enums_generated.add(enum_name)

        # Write enums for namespaced messages
        for namespace_name, messages in namespaced_messages.items():
            # Check if we've already written this namespace
            if namespace_name not in namespaced_enums:
                f.write(f"    namespace {namespace_name} {{\n")
                namespace_written = False
            else:
                namespace_written = True

            for message in messages:
                for field in message.fields:
                    if field.field_type == FieldType.ENUM:
                        enum_name = f"{message.name}_{field.name}_Enum"
                        if enum_name not in enums_generated:
                            f.write(f"        // Enum for {message.name}.{field.name}\n")
                            # Create a temporary enum object to determine the size
                            temp_enum = Enum(enum_name, field.enum_values)
                            size_bits = temp_enum.get_min_size_bits()
                            f.write(f"        enum class {enum_name} : uint{size_bits}_t\n")
                            f.write("        {\n")
                            for enum_value in field.enum_values:
                                f.write(f"            {enum_value.name} = {enum_value.value},\n")
                            f.write("        };\n\n")
                            enums_generated.add(enum_name)
                    elif field.field_type == FieldType.OPTIONS:
                        enum_name = f"{message.name}_{field.name}_Options"
                        if enum_name not in enums_generated:
                            f.write(f"        // Options for {message.name}.{field.name}\n")
                            # Options are always uint32_t as they're used as bit flags
                            f.write(f"        enum class {enum_name} : uint32_t\n")
                            f.write("        {\n")
                            for enum_value in field.enum_values:
                                f.write(f"            {enum_value.name} = {enum_value.value},\n")
                            f.write("        };\n\n")
                            enums_generated.add(enum_name)

            # Only close the namespace if we opened it
            if not namespace_written:
                f.write(f"    }} // namespace {namespace_name}\n\n")

    def _write_structs(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write struct definitions.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        # Group messages by namespace
        global_messages = []
        namespaced_messages = {}

        for message_name, message in model.messages.items():
            # Skip the "Base" namespace for messages in the base file
            # This namespace is added by the import statement but shouldn't be in the generated base file
            if message.namespace == "Base" and message.source_file and os.path.basename(message.source_file).startswith("sh4c_base"):
                global_messages.append(message)
            elif message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                namespaced_messages[message.namespace].append(message)
            else:
                global_messages.append(message)

        # Write structs for global messages
        for message in global_messages:
            self._write_struct(f, message)

        # Write structs for namespaced messages
        for namespace_name, messages in namespaced_messages.items():
            f.write(f"    namespace {namespace_name} {{\n\n")
            for message in messages:
                self._write_struct(f, message)
            f.write(f"    }} // namespace {namespace_name}\n\n")

    def _write_struct(self, f: TextIO, message: Message) -> None:
        """
        Write a struct definition.

        Args:
            f: The file to write to
            message: The message to write
        """
        message_name = message.name

        # Write detailed documentation for the message
        f.write(f"    /**\n")
        f.write(f"     * @struct {message_name}\n")
        if message.description:
            f.write(f"     * @brief {message.description}\n")
        else:
            f.write(f"     * @brief Message definition for {message_name}\n")

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
            f.write(f"     * @details Fields:\n")
            for field in message.fields:
                field_type_str = self._get_field_type_description(field, message_name)
                f.write(f"     * - {field.name}: {field_type_str}")
                if field.description:
                    f.write(f" - {field.description}")
                f.write("\n")

        f.write(f"     */\n")

        # Handle inheritance
        if message.parent:
            # If parent is in a namespace, include the namespace in the parent name
            parent_message = self.model.get_message(message.parent)

            # Check if parent message is in the same file as this message
            same_file = parent_message and parent_message.source_file and message.source_file and parent_message.source_file == message.source_file

            if parent_message and parent_message.namespace and not same_file:
                # Use the namespace directly without the output_name prefix
                parent_name = f"{parent_message.namespace}::{parent_message.name}"
            else:
                # If the parent message is not found, doesn't have a namespace, or is in the same file,
                # try to extract the namespace from the parent name
                if '::' in message.parent and not same_file:
                    # Use the namespace directly
                    parent_name = message.parent
                else:
                    # If the parent is in the same file or doesn't have a namespace,
                    # use just the message name without the namespace
                    if '::' in message.parent:
                        parent_name = message.parent.split("::", 1)[1]
                    else:
                        parent_name = message.parent

            f.write(f"    struct {message_name} : public {parent_name}\n")
        else:
            f.write(f"    struct {message_name}\n")

        f.write("    {\n")

        # Generate fields
        for field in message.fields:
            self._write_field(f, message_name, field, "        ")

        f.write("    };\n\n")

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
            enum_name = f"{message_name}_{field.name}_Options"
            return f"Options ({enum_name}){optional_text}{default_text}"

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                components = ", ".join(field.compound_components)
                return f"Compound ({components}){optional_text}{default_text}"
            else:
                return f"Compound ({field.compound_base_type}){optional_text}{default_text}"

        elif field.field_type == FieldType.STRING:
            return f"String (std::string){optional_text}{default_text}"

        elif field.field_type == FieldType.INT:
            return f"Integer (int32_t){optional_text}{default_text}"

        elif field.field_type == FieldType.FLOAT:
            return f"Float (float){optional_text}{default_text}"

        elif field.field_type == FieldType.BOOLEAN:
            return f"Boolean (bool){optional_text}{default_text}"

        elif field.field_type == FieldType.BYTE:
            return f"Byte (uint8_t){optional_text}{default_text}"

        else:
            return f"Unknown ({field.field_type}){optional_text}{default_text}"

    def _write_field(self, f: TextIO, message_name: str, field: Field, indent: str) -> None:
        """
        Write a field definition.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to write
            indent: The indentation to use
        """
        # Add documentation comment for the field
        if field.comment:
            # Use user-supplied comment if available
            f.write(f"{indent}/**\n")
            # Split multi-line comments and format each line
            comment_lines = field.comment.split('\n')
            for line in comment_lines:
                f.write(f"{indent} * {line}\n")
            f.write(f"{indent} */\n")
        elif field.description:
            f.write(f"{indent}/** {field.description} */\n")
        else:
            field_type_desc = self._get_field_type_description(field, message_name)
            f.write(f"{indent}/** {field_type_desc} field */\n")

        if field.field_type == FieldType.ENUM:
            # Get the message object to check if it's in a namespace
            message = None
            for msg_name, msg in self.model.messages.items():
                if msg_name == message_name:
                    message = msg
                    break

            # If the message is in a namespace, use the namespace in the enum name
            if message and message.namespace and message.namespace != "Base":
                namespace_prefix = f"{message.namespace}::"
                enum_name = f"{message_name}_{field.name}_Enum"
                full_enum_name = f"{namespace_prefix}{enum_name}"
            else:
                namespace_prefix = ""
                enum_name = f"{message_name}_{field.name}_Enum"
                full_enum_name = enum_name

            if field.default_value is not None:
                f.write(f"{indent}{enum_name} {field.name} = {full_enum_name}::{field.default_value};\n")
            else:
                f.write(f"{indent}{enum_name} {field.name};\n")

        elif field.field_type == FieldType.OPTIONS:
            # Get the message object to check if it's in a namespace
            message = None
            for msg_name, msg in self.model.messages.items():
                if msg_name == message_name:
                    message = msg
                    break

            # If the message is in a namespace, use the namespace in the enum name
            if message and message.namespace and message.namespace != "Base":
                namespace_prefix = f"{message.namespace}::"
                enum_name = f"{message_name}_{field.name}_Options"
                full_enum_name = f"{namespace_prefix}{enum_name}"
            else:
                namespace_prefix = ""
                enum_name = f"{message_name}_{field.name}_Options"
                full_enum_name = enum_name

            if field.default_value is not None:
                # For default values, we need to use the enum values directly
                # We can't use the enum type for the default value because it's a bit field
                # If the default value is a string (enum value name), convert it to its numeric value
                # For combined options, use the OR'ed enum values for readability
                if field.default_value_str and '&' in field.default_value_str:
                    option_names = [opt.strip() for opt in field.default_value_str.split('&')]
                    or_expression = " | ".join([f"{full_enum_name}::{name}" for name in option_names])
                    f.write(f"{indent}uint32_t {field.name} = {or_expression}; // Combination of {enum_name} values\n")
                # For single option values or numeric values
                else:
                    # If the default value is a string (enum value name), use the enum value
                    if field.default_value_str and not field.default_value_str.isdigit():
                        f.write(f"{indent}uint32_t {field.name} = {full_enum_name}::{field.default_value_str}; // {enum_name} value\n")
                    else:
                        # Use the numeric value directly
                        default_value = field.default_value
                        f.write(f"{indent}uint32_t {field.name} = {default_value}; // Combination of {enum_name} values\n")
            else:
                f.write(f"{indent}uint32_t {field.name} = 0;\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"{indent}struct {{\n")
                for component in field.compound_components:
                    f.write(f"{indent}    /** {component} component of {field.name} */\n")
                    f.write(f"{indent}    float {component};\n")
                f.write(f"{indent}}} {field.name};\n")
            else:
                # Handle other compound types if needed
                f.write(f"{indent}// Unsupported compound type: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            if field.default_value is not None:
                # Remove extra quotes and escape remaining quotes in the default value
                default_value = field.default_value
                if isinstance(default_value, str) and default_value.startswith('"') and default_value.endswith('"'):
                    default_value = default_value[1:-1]
                default_value = default_value.replace('"', '\\"')
                f.write(f"{indent}std::string {field.name} = \"{default_value}\";\n")
            else:
                f.write(f"{indent}std::string {field.name};\n")

        elif field.field_type == FieldType.INT:
            if field.default_value is not None:
                f.write(f"{indent}int32_t {field.name} = {field.default_value};\n")
            else:
                f.write(f"{indent}int32_t {field.name};\n")

        elif field.field_type == FieldType.FLOAT:
            if field.default_value is not None:
                f.write(f"{indent}float {field.name} = {field.default_value}f;\n")
            else:
                f.write(f"{indent}float {field.name};\n")

        elif field.field_type == FieldType.BOOLEAN:
            if field.default_value is not None:
                # Convert Python bool to C++ bool
                bool_value = "true" if field.default_value else "false"
                f.write(f"{indent}bool {field.name} = {bool_value};\n")
            else:
                f.write(f"{indent}bool {field.name} = false;\n")

        elif field.field_type == FieldType.BYTE:
            if field.default_value is not None:
                f.write(f"{indent}uint8_t {field.name} = {field.default_value};\n")
            else:
                f.write(f"{indent}uint8_t {field.name} = 0;\n")

        else:
            f.write(f"{indent}// Unsupported type: {field.field_type}\n")
