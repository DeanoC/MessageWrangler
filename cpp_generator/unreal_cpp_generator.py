"""
Generator for Unreal Engine C++ code from the intermediate representation.
"""

import os
from typing import TextIO, Dict, List, Optional, Any
from io import StringIO

from message_model import (
    MessageModel,
    Message,
    Field,
    FieldType,
    EnumValue,
    Enum
)

from .base_cpp_generator import BaseCppGenerator


class UnrealCppGenerator(BaseCppGenerator):
    """
    Generator for Unreal Engine C++ code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str, output_base_name: str = "Messages"):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
            output_base_name: Base name for output files without extension (default: "Messages")
        """
        self.output_base_name = output_base_name
        super().__init__(model, output_dir, output_base_name)

# Ensure output_base_name has a default value
        if output_base_name is None:
            raise ValueError("output_base_name must be explicitly provided.")
        print(f"[DEBUG] Using output_base_name: {output_base_name}")
    def _write_namespace_start(self, f: TextIO, output_base_name: str) -> None: # NEW
        """
        Write the start of the namespace, using the ue_ prefix.

        Args:
            f: The file to write to
            output_base_name: The base name for the current file's namespace
        """
        namespace_name = output_base_name # NEW
        print(f"[DEBUG] Writing namespace: ue_{namespace_name}")
        f.write(f"namespace ue_{namespace_name} {{\n")
        # Removed duplicate write


    def _write_namespace_end(self, f: TextIO, output_base_name: str) -> None: # NEW
        """
        Write the end of the namespace, using the ue_ prefix.

        Args:
            f: The file to write to
            output_base_name: The base name for the current file's namespace
        """
        f.write(f"}} // namespace ue_{output_base_name}\n") # NEW

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
                    output_base_name = self.output_base_name
                else:
                    output_base_name = base_name

                # Ensure output_base_name is initialized
                if not output_base_name:
                    output_base_name = "Messages"

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
                    # Pass the correct output_base_name for this file
                    self._write_header(f, output_base_name) # Pass output_base_name

                    # Add include statements for parent messages that are in other files
                    self._write_file_includes(f, messages, messages_by_source, generated_files)

                    # Pass the correct output_base_name for this file
                    self._write_namespace_start(f, output_base_name) # Pass output_base_name
                    f.write("\n")  # Add a newline after the namespace declaration

                    # These methods operate on the filtered_model, don't need output_base_name
                    self._write_enums(f, filtered_model)
                    self._write_forward_declarations(f, filtered_model)
                    self._write_structs(f, filtered_model)

                    # Only write serialization utils in the main file
                    if source_file == main_file:
                        # _write_serialization_utils doesn't seem to depend on output_base_name
                        self._write_serialization_utils(f)

                    # Pass the correct output_base_name for this file
                    self._write_namespace_end(f, output_base_name) # Pass output_base_name

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
        # Use a dictionary to store namespace aliases: alias -> generated_namespace
        namespace_aliases: Dict[str, str] = {} # NEW: Use dictionary for aliases

        # We'll collect needed includes by checking parent references and import aliases

        # Check each message for parent references to messages in other files
        for message in messages:
            if message.parent:
                # Find the parent message in the full model
                parent_message = self.model.get_message(message.parent)

                # If parent is found and is in a different file, add an include
                if parent_message and parent_message.source_file != message.source_file:
                    parent_source = parent_message.source_file
                    # Determine the generated header file name for the parent's source file
                    # This logic should match how header filenames are generated in the generate method
                    parent_source_base_name = os.path.splitext(os.path.basename(parent_source))[0]
                    # If the parent source is the main file, use the main output base name
                    if parent_source == self.model.main_file_path: # Assuming main_file_path is stored in model
                         parent_output_base_name = self.output_base_name
                    else:
                         parent_output_base_name = parent_source_base_name

                    parent_header = f"ue_{parent_output_base_name}_msgs.h"
                    needed_includes.add(parent_header)

        # Add includes for files imported with aliases that are relevant to this file
        current_file_path = messages[0].source_file if messages else None # Assuming all messages in list are from same file
        if current_file_path:
            for alias, imported_file_path in self.model.imports.items():
                # Check if any message in the current file uses this alias in a parent reference
                uses_alias = any(
                    msg.parent and msg.parent.startswith(f"{alias}::")
                    for msg in messages
                )
                # Also check if any standalone enum in the current file uses this alias in a parent reference
                uses_alias = uses_alias or any(
                    enum.parent and enum.parent.startswith(f"{alias}::")
                    for enum_name, enum in self.model.enums.items()
                    if enum.source_file == current_file_path and enum.parent and enum.parent.startswith(f"{alias}::")
                )


                if uses_alias:
                    # Determine the generated header file name for the imported file
                    imported_source_base_name = os.path.splitext(os.path.basename(imported_file_path))[0]
                    # If the imported source is the main file, use the main output base name
                    if imported_file_path == self.model.main_file_path: # Assuming main_file_path is stored in model
                         imported_output_base_name = self.output_base_name
                    else:
                         imported_output_base_name = imported_source_base_name

                    imported_header = f"ue_{imported_output_base_name}_msgs.h"
                    needed_includes.add(imported_header)

                    # Add the namespace alias mapping
                    namespace_aliases[alias] = f"ue_{imported_output_base_name}"


        # Write include statements
        for header in sorted(list(needed_includes)): # Convert set to list for sorting
            f.write(f"#include \"{header}\"\n")

        if needed_includes:
            f.write("\n")

        # Write namespace aliases
        for alias, generated_namespace in namespace_aliases.items():
            f.write(f"namespace {alias} = {generated_namespace};\n")

        if namespace_aliases:
            f.write("\n")

    def _write_header(self, f: TextIO, output_base_name: str) -> None: # NEW
        """
        Write the header section of the C++ file.

        Args:
            f: The file to write to
            output_base_name: The base name for the current file's namespace
        """
        f.write("// Auto-generated message definitions for Unreal Engine C++\n")
        f.write("// This file contains message definitions for communication between systems.\n")
        f.write("//\n")
        f.write("// DOCUMENTATION FOR MESSAGE FORMAT:\n")
        f.write("// ===============================\n")
        f.write("// This file defines a set of message structures used for communication.\n")
        f.write(f"// Each message is defined as a C++ struct within the ue_{output_base_name} namespace.\n") # NEW
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
            if message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                    message_field_enums[message.namespace] = []
                namespaced_messages[message.namespace].append(message)
            else:
                global_messages.append(message)

        # Now, collect all field enums for all messages
        for message_name, message in model.messages.items():
            # Determine the namespace for this message's field enums
            namespace = message.namespace
            if namespace:
                # For messages with a namespace, add their field enums to that namespace
                if namespace not in message_field_enums:
                    message_field_enums[namespace] = []

                for field in message.fields:
                    # Skip fields that reference existing enums
                    if field.enum_reference:
                        continue

                    if field.field_type == FieldType.ENUM or field.field_type == FieldType.OPTIONS:
                        # Create a unique name for the enum based on message and field name
                        enum_name = f"{message.name}_{field.name}_{field.field_type.name}"
                        # Check if this enum has already been generated (can happen with inherited fields)
                        if enum_name not in enums_generated:
                            # Create a temporary Enum object for generation
                            temp_enum = Enum(
                                name=enum_name,
                                values=field.enum_values,
                                is_open=field.field_type == FieldType.OPTIONS, # Options are open enums
                                source_file=message.source_file, # Associate with the message's source file
                                namespace=namespace # Use the message's namespace
                            )
                            if namespace:
                                message_field_enums[namespace].append(temp_enum)
                            else:
                                global_message_field_enums.append(temp_enum)
                            enums_generated.add(enum_name)

            else:
                # For global messages, add their field enums to the global list
                for field in message.fields:
                    # Skip fields that reference existing enums
                    if field.enum_reference:
                        continue

                    if field.field_type == FieldType.ENUM or field.field_type == FieldType.OPTIONS:
                        # Create a unique name for the enum based on message and field name
                        enum_name = f"{message.name}_{field.name}_{field.field_type.name}"
                        # Check if this enum has already been generated (can happen with inherited fields)
                        if enum_name not in enums_generated:
                            # Create a temporary Enum object for generation
                            temp_enum = Enum(
                                name=enum_name,
                                values=field.enum_values,
                                is_open=field.field_type == FieldType.OPTIONS, # Options are open enums
                                source_file=message.source_file, # Associate with the message's source file
                                namespace=None # Global namespace
                            )
                            global_message_field_enums.append(temp_enum)
                            enums_generated.add(enum_name)


        # Write message field enums for global scope
        for enum in global_message_field_enums:
            f.write(f"    // Enum for field {enum.name}\n")
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

        # Write message field enums for namespaced scope
        for namespace_name, enums in message_field_enums.items():
            f.write(f"    namespace {namespace_name} {{\n")
            for enum in enums:
                f.write(f"        // Enum for field {enum.name}\n")
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
            f.write(f"    }} // namespace {namespace_name}\n\n")


    def _write_serialization_utils(self, f: TextIO) -> None:
        """
        Write serialization utility functions.

        Args:
            f: The file to write to
        """
        f.write("namespace MessageSerialization {\n\n")

        f.write("    // Function to register message types (implementation not shown here)\n")
        f.write("    // This would typically involve mapping message type strings to factory functions\n")
        f.write("    // or reflection information.\n")
        f.write("    inline void RegisterMessageTypes() {\n")
        f.write("        // TODO: Implement message type registration\n")
        f.write("    }\n\n")

        f.write("    // Function to serialize a message to a JSON string with message type\n")
        f.write("    // This assumes messages have a ToJson() method.\n")
        f.write("    template<typename T>\n")
        f.write("    inline FString SerializeMessage(const T& message) {\n")
        f.write("        TSharedPtr<FJsonObject> JsonObject = message.ToJson();\n")
        f.write("        JsonObject->SetStringField(TEXT(\"messageType\"), T::StaticStruct()->GetName());\n")
        f.write("        FString OutputString;\n")
        f.write("        TSharedRef<TJsonWriter<TCHAR>> Writer = TJsonWriterFactory<TCHAR>::Create(&OutputString);\n")
        f.write("        FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);\n")
        f.write("        return OutputString;\n")
        f.write("    }\n\n")

        f.write("    // Function to deserialize a JSON string to a message object\n")
        f.write("    // This assumes a mechanism to create message objects by type string.\n")
        f.write("    // The implementation would typically involve looking up the message type\n")
        f.write("    // and calling the appropriate FromJson() method.\n")
        f.write("    inline TSharedPtr<FJsonObject> DeserializeMessage(const FString& JsonString) {\n")
        f.write("        TSharedPtr<FJsonObject> JsonObject;\n")
        f.write("        TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<TCHAR>::Create(JsonString);\n")
        f.write("        if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid()) {\n")
        f.write("            return JsonObject;\n")
        f.write("        }\n")
        f.write("        return nullptr;\n")
        f.write("    }\n\n")

        f.write("} // namespace MessageSerialization\n\n")


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
            if message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                namespaced_messages[message.namespace].append(message)
            else:
                global_messages.append(message)

        # Write global messages
        for message in global_messages:
            self._write_struct(f, message, "    ", "") # Pass empty string for global namespace

        # Write namespaced messages
        for namespace_name, messages in namespaced_messages.items():
            f.write(f"    namespace {namespace_name} {{\n")
            for message in messages:
                self._write_struct(f, message, "        ", namespace_name) # Pass namespace_name
            f.write(f"    }} // namespace {namespace_name}\n\n")


    def _write_struct(self, f: TextIO, message: Message, indent: str, namespace: str) -> None:
        """
        Write a single struct definition.

        Args:
            f: The file to write to
            message: The message to generate the struct for
            indent: The current indentation string
            namespace: The namespace the message belongs to (or empty string for global)
        """
        parent_inheritance = ""
        if message.parent:
            # If the parent has a namespace and it's different from the current message's namespace,
            # we need to use the fully qualified name or an alias.
            parent_message = self.model.get_message(message.parent)
            if parent_message and parent_message.namespace and parent_message.namespace != namespace:
                 # Check if there's an alias for the parent's namespace
                 # This requires access to the aliases created in _write_file_includes
                 # For now, we'll assume direct namespace access or a simple alias
                 # A more robust solution might involve passing the alias map or
                 # generating aliases in a shared context.
                 # For simplicity, let's assume direct namespace access for now.
                 parent_name = f"{parent_message.namespace}::{parent_message.name}"
            else:
                parent_name = message.parent

            parent_inheritance = f" : public {parent_name}"

        f.write(f"{indent}USTRUCT(BlueprintType)\n")
        f.write(f"{indent}struct F{message.name}{parent_inheritance}\n")
        f.write(f"{indent}{{\n")
        f.write(f"{indent}    GENERATED_BODY()\n\n")

        # Write fields
        for field in message.fields:
            self._write_field(f, message.name, field, f"{indent}    ")

        f.write(f"{indent}    // JSON Serialization/Deserialization\n")
        f.write(f"{indent}    TSharedPtr<FJsonObject> ToJson() const\n")
        f.write(f"{indent}    {{\n")
        f.write(f"{indent}        TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());\n")
        if message.parent:
             f.write(f"{indent}        // Serialize parent fields\n")
             f.write(f"{indent}        TSharedPtr<FJsonObject> ParentJsonObject = {parent_name}::ToJson();\n")
             f.write(f"{indent}        for (auto& Pair : ParentJsonObject->Values)\n")
             f.write(f"{indent}        {{\n")
             f.write(f"{indent}            JsonObject->SetField(Pair.Key, Pair.Value);\n")
             f.write(f"{indent}        }}\n")

        # Write field serialization
        for field in message.fields:
            self._write_field_serialization(f, message.name, field, f"{indent}        ")

        f.write(f"{indent}        return JsonObject;\n")
        f.write(f"{indent}    }}\n\n")

        f.write(f"{indent}    void FromJson(const TSharedPtr<FJsonObject>& JsonObject)\n")
        f.write(f"{indent}    {{\n")
        if message.parent:
             f.write(f"{indent}        // Deserialize parent fields\n")
             f.write(f"{indent}        {parent_name}::FromJson(JsonObject);\n")

        # Write field deserialization
        for field in message.fields:
            self._write_field_deserialization(f, message.name, field, f"{indent}        ")

        f.write(f"{indent}    }}\n")
        f.write(f"{indent}}};\n\n")


    def _get_field_type_description(self, field: Field, message_name: str) -> str:
        """
        Get the C++ type string for a field.

        Args:
            field: The field to get the type for
            message_name: The name of the message containing the field (for enum naming)

        Returns:
            str: The C++ type string
        """
        if field.field_type == FieldType.INT32:
            return "int32"
        elif field.field_type == FieldType.FLOAT:
            return "float"
        elif field.field_type == FieldType.STRING:
            return "FString"
        elif field.field_type == FieldType.BOOL:
            return "bool"
        elif field.field_type == FieldType.UINT8:
            return "uint8"
        elif field.field_type == FieldType.ENUM:
            if field.enum_reference:
                # Handle namespaced enum references
                if "::" in field.enum_reference:
                    return field.enum_reference
                else:
                    # Assume global or current namespace for now
                    # A more robust solution would check for aliases or current namespace
                    return field.enum_reference
            else:
                return f"{message_name}_{field.name}_ENUM"
        elif field.field_type == FieldType.OPTIONS:
            if field.enum_reference:
                 # Handle namespaced options references
                 if "::" in field.enum_reference:
                     return field.enum_reference
                 else:
                     # Assume global or current namespace for now
                     return field.enum_reference
            else:
                return f"{message_name}_{field.name}_OPTIONS"
        elif field.field_type == FieldType.COMPOUND:
            # For compound types, we need to generate an anonymous struct
            # This method is only for getting the type description, not generating the struct
            # The struct generation happens in _write_field
            return "/* Compound Type */" # Placeholder
        elif field.field_type == FieldType.MESSAGE:
            # Handle namespaced message references
            if "::" in field.message_reference:
                return f"F{field.message_reference}"
            else:
                # Assume global or current namespace for now
                return f"F{field.message_reference}"
        else:
            raise ValueError(f"Unknown field type: {field.field_type}")


    def _write_field(self, f: TextIO, message_name: str, field: Field, indent: str) -> None:
        """
        Write a single field definition.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field (for enum naming)
            field: The field to write
            indent: The current indentation string
        """
        # Add comment for optional fields
        if field.optional:
            f.write(f"{indent}// Optional\n")

        if field.field_type == FieldType.COMPOUND:
            f.write(f"{indent}struct\n")
            f.write(f"{indent}{{\n")
            for component in field.components:
                # Determine the C++ type for the component
                component_type = self._get_field_type_description(component, message_name)
                # Write the component field
                f.write(f"{indent}    {component_type} {component.name};\n")
            f.write(f"{indent}}} {field.name};\n")
        else:
            field_type = self._get_field_type_description(field, message_name)
            default_value = ""
            if field.default_value is not None:
                if field.field_type == FieldType.STRING:
                    default_value = f' = TEXT("{field.default_value}")'
                elif field.field_type == FieldType.BOOL:
                    default_value = f' = {"true" if field.default_value else "false"}'
                elif field.field_type == FieldType.ENUM:
                    # For enums, the default value is the enum value name
                    # We need to find the full enum value name, including the enum type
                    if field.enum_reference:
                        # If it's a reference, use the reference name
                        default_value = f" = {field.enum_reference}::{field.default_value}"
                    else:
                        # If it's an inline enum, use the generated enum name
                        default_value = f" = {message_name}_{field.name}_ENUM::{field.default_value}"
                elif field.field_type == FieldType.OPTIONS:
                    # For options, the default value can be a single option or a combination
                    if field.enum_reference:
                        # If it's a reference, use the reference name
                        default_value = f" = {field.enum_reference}::{field.default_value}"
                    else:
                        # If it's an inline options, use the generated options name
                        default_value = f" = {message_name}_{field.name}_OPTIONS::{field.default_value}"
                else:
                    default_value = f" = {field.default_value}"

            f.write(f"{indent}{field_type} {field.name}{default_value};\n")


    def _write_field_serialization(self, f: TextIO, message_name: str, field: Field, indent: str) -> None:
        """
        Write the JSON serialization code for a single field.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field (for enum naming)
            field: The field to write serialization for
            indent: The current indentation string
        """
        if field.field_type == FieldType.INT32:
            f.write(f"{indent}JsonObject->SetNumberField(TEXT(\"{field.name}\"), {field.name});\n")
        elif field.field_type == FieldType.FLOAT:
            f.write(f"{indent}JsonObject->SetNumberField(TEXT(\"{field.name}\"), {field.name});\n")
        elif field.field_type == FieldType.STRING:
            f.write(f"{indent}JsonObject->SetStringField(TEXT(\"{field.name}\"), {field.name});\n")
        elif field.field_type == FieldType.BOOL:
            f.write(f"{indent}JsonObject->SetBoolField(TEXT(\"{field.name}\"), {field.name});\n")
        elif field.field_type == FieldType.UINT8:
            f.write(f"{indent}JsonObject->SetNumberField(TEXT(\"{field.name}\"), {field.name});\n")
        elif field.field_type == FieldType.ENUM:
            f.write(f"{indent}JsonObject->SetNumberField(TEXT(\"{field.name}\"), static_cast<int32>({field.name}));\n")
        elif field.field_type == FieldType.OPTIONS:
            f.write(f"{indent}JsonObject->SetNumberField(TEXT(\"{field.name}\"), static_cast<int32>({field.name}));\n")
        elif field.field_type == FieldType.COMPOUND:
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    TSharedPtr<FJsonObject> CompoundObject = MakeShareable(new FJsonObject());\n")
            for component in field.components:
                # Assuming components are basic types for now
                if component.field_type == FieldType.INT32:
                    f.write(f"{indent}    CompoundObject->SetNumberField(TEXT(\"{component.name}\"), {field.name}.{component.name});\n")
                elif component.field_type == FieldType.FLOAT:
                    f.write(f"{indent}    CompoundObject->SetNumberField(TEXT(\"{component.name}\"), {field.name}.{component.name});\n")
                elif component.field_type == FieldType.STRING:
                    f.write(f"{indent}    CompoundObject->SetStringField(TEXT(\"{component.name}\"), {field.name}.{component.name});\n")
                elif component.field_type == FieldType.BOOL:
                    f.write(f"{indent}    CompoundObject->SetBoolField(TEXT(\"{component.name}\"), {field.name}.{component.name});\n")
                elif component.field_type == FieldType.UINT8:
                    f.write(f"{indent}    CompoundObject->SetNumberField(TEXT(\"{component.name}\"), {field.name}.{component.name});\n")
                # Add other basic types as needed
            f.write(f"{indent}    JsonObject->SetObjectField(TEXT(\"{field.name}\"), CompoundObject);\n")
            f.write(f"{indent}}}\n")
        elif field.field_type == FieldType.MESSAGE:
            f.write(f"{indent}JsonObject->SetObjectField(TEXT(\"{field.name}\"), {field.name}.ToJson());\n")
        else:
            raise ValueError(f"Unknown field type for serialization: {field.field_type}")


    def _write_field_deserialization(self, f: TextIO, message_name: str, field: Field, indent: str) -> None:
        """
        Write the JSON deserialization code for a single field.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field (for enum naming)
            field: The field to write deserialization for
            indent: The current indentation string
        """
        # Handle optional fields
        if field.optional:
            f.write(f"{indent}if (JsonObject->HasField(TEXT(\"{field.name}\")))\n")
            f.write(f"{indent}{{\n")
            indent += "    " # Increase indent for the if block

        if field.field_type == FieldType.INT32:
            f.write(f"{indent}{field.name} = JsonObject->GetIntegerField(TEXT(\"{field.name}\"));\n")
        elif field.field_type == FieldType.FLOAT:
            f.write(f"{indent}{field.name} = JsonObject->GetNumberField(TEXT(\"{field.name}\"));\n")
        elif field.field_type == FieldType.STRING:
            f.write(f"{indent}{field.name} = JsonObject->GetStringField(TEXT(\"{field.name}\"));\n")
        elif field.field_type == FieldType.BOOL:
            f.write(f"{indent}{field.name} = JsonObject->GetBoolField(TEXT(\"{field.name}\"));\n")
        elif field.field_type == FieldType.UINT8:
            f.write(f"{indent}{field.name} = static_cast<uint8>(JsonObject->GetIntegerField(TEXT(\"{field.name}\")));\n")
        elif field.field_type == FieldType.ENUM:
            f.write(f"{indent}{field.name} = static_cast<{self._get_field_type_description(field, message_name)}>(JsonObject->GetIntegerField(TEXT(\"{field.name}\")));\n")
        elif field.field_type == FieldType.OPTIONS:
            f.write(f"{indent}{field.name} = static_cast<{self._get_field_type_description(field, message_name)}>(JsonObject->GetIntegerField(TEXT(\"{field.name}\")));\n")
        elif field.field_type == FieldType.COMPOUND:
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    TSharedPtr<FJsonObject> CompoundObject = JsonObject->GetObjectField(TEXT(\"{field.name}\"));\n")
            f.write(f"{indent}    if (CompoundObject.IsValid())\n")
            f.write(f"{indent}    {{\n")
            for component in field.components:
                # Assuming components are basic types for now
                if component.field_type == FieldType.INT32:
                    f.write(f"{indent}        {field.name}.{component.name} = CompoundObject->GetIntegerField(TEXT(\"{component.name}\"));\n")
                elif component.field_type == FieldType.FLOAT:
                    f.write(f"{indent}        {field.name}.{component.name} = CompoundObject->GetNumberField(TEXT(\"{component.name}\"));\n")
                elif component.field_type == FieldType.STRING:
                    f.write(f"{indent}        {field.name}.{component.name} = CompoundObject->GetStringField(TEXT(\"{component.name}\"));\n")
                elif component.field_type == FieldType.BOOL:
                    f.write(f"{indent}        {field.name}.{component.name} = CompoundObject->GetBoolField(TEXT(\"{component.name}\"));\n")
                elif component.field_type == FieldType.UINT8:
                    f.write(f"{indent}        {field.name}.{component.name} = static_cast<uint8>(CompoundObject->GetIntegerField(TEXT(\"{component.name}\")));\n")
                # Add other basic types as needed
            f.write(f"{indent}    }}\n")
            f.write(f"{indent}}}\n")
        elif field.field_type == FieldType.MESSAGE:
            f.write(f"{indent}{{\n")
            f.write(f"{indent}    TSharedPtr<FJsonObject> MessageObject = JsonObject->GetObjectField(TEXT(\"{field.name}\"));\n")
            f.write(f"{indent}    if (MessageObject.IsValid())\n")
            f.write(f"{indent}    {{\n")
            f.write(f"{indent}        {field.name}.FromJson(MessageObject);\n")
            f.write(f"{indent}    }}\n")
            f.write(f"{indent}}}\n")
        else:
            raise ValueError(f"Unknown field type for deserialization: {field.field_type}")

        # Close the if block for optional fields
        if field.optional:
            indent = indent[:-4] # Decrease indent
            f.write(f"{indent}}}\n")