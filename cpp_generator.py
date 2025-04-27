"""
C++ Generator

This module provides functionality for generating C++ code from the
intermediate representation defined in message_model.py.
It supports both Unreal Engine C++ and standard C++ code generation.
"""

import os
from typing import List, Set, TextIO

from message_model import (
    FieldType,
    Field,
    Message,
    MessageModel
)


class BaseCppGenerator:
    """
    Base generator for C++ code from the intermediate representation.
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

    def _write_namespace_start(self, f: TextIO) -> None:
        """
        Write the start of the namespace.

        Args:
            f: The file to write to
        """
        f.write("namespace Messages {\n\n")

    def _write_namespace_end(self, f: TextIO) -> None:
        """
        Write the end of the namespace.

        Args:
            f: The file to write to
        """
        f.write("} // namespace Messages\n")

    def _write_forward_declarations(self, f: TextIO) -> None:
        """
        Write forward declarations for all structs.

        Args:
            f: The file to write to
        """
        for message_name in self.model.messages:
            f.write(f"    struct {message_name};\n")
        f.write("\n")


class UnrealCppGenerator(BaseCppGenerator):
    """
    Generator for Unreal Engine C++ code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
        """
        super().__init__(model, output_dir)


class UnrealCppGenerator(BaseCppGenerator):
    """
    Generator for Unreal Engine C++ code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
        """
        super().__init__(model, output_dir)

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

            # Generate header file
            header_file = os.path.join(self.output_dir, "Messages.h")
            with open(header_file, 'w') as f:
                self._write_header(f)
                self._write_namespace_start(f)
                self._write_enums(f)
                self._write_forward_declarations(f)
                self._write_structs(f)
                self._write_serialization_utils(f)
                self._write_namespace_end(f)

            print(f"Generated Unreal C++ header file: {header_file}")
            return True

        except Exception as e:
            print(f"Error generating Unreal C++ output: {str(e)}")
            return False

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
        f.write("// Each message is defined as a C++ struct within the Messages namespace.\n")
        f.write("//\n")
        f.write("// Message Structure:\n")
        f.write("// - Messages are defined as structs with specific fields\n")
        f.write("// - Messages can inherit from other messages using standard C++ inheritance\n")
        f.write("// - Fields can be of the following types:\n")
        f.write("//   * Basic types: int32 (integer), float, FString (string)\n")
        f.write("//   * Enum types: defined as enum class with uint8 underlying type\n")
        f.write("//   * Compound types: struct with named components\n")
        f.write("//\n")
        f.write("// Enum Naming Convention:\n")
        f.write("// - Enums are named as MessageName_fieldName_Enum\n")
        f.write("//\n")
        f.write("// Compound Field Structure:\n")
        f.write("// - Compound fields are defined as anonymous structs within the message\n")
        f.write("// - Each component is a named field within the anonymous struct\n")
        f.write("//\n")
        f.write("// JSON Serialization:\n")
        f.write("// ================\n")
        f.write("// Each message struct includes ToJson() and FromJson() methods for serialization and deserialization.\n")
        f.write("// - ToJson(): Converts the message to a JSON object\n")
        f.write("// - FromJson(): Populates the message from a JSON object\n")
        f.write("//\n")
        f.write("// The MessageSerialization namespace provides utility functions for working with messages:\n")
        f.write("// - SerializeMessage(): Serializes a message to a JSON string with message type\n")
        f.write("// - DeserializeMessage(): Deserializes a JSON string to a message object\n")
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
                        f.write(f"    enum class {enum_name} : uint8\n")
                        f.write("    {\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    };\n\n")
                        enums_generated.add(enum_name)

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

    def _write_structs(self, f: TextIO) -> None:
        """
        Write struct definitions with JSON serialization methods.

        Args:
            f: The file to write to
        """
        for message_name, message in self.model.messages.items():
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
                f.write(f"    struct {message_name} : public {message.parent}\n")
            else:
                f.write(f"    struct {message_name}\n")

            f.write("    {\n")

            # Generate fields
            for field in message.fields:
                self._write_field(f, message_name, field)

            # Add ToJson method
            f.write("\n        /**\n")
            f.write("         * Convert this message to a JSON object\n")
            f.write("         * @return JSON object representation of this message\n")
            f.write("         */\n")
            f.write("        TSharedPtr<FJsonObject> ToJson() const {\n")
            f.write("            TSharedPtr<FJsonObject> JsonObj = MakeShared<FJsonObject>();\n")

            # If this message inherits from another, call the parent's ToJson method
            if message.parent:
                f.write("            // Call parent class serialization\n")
                f.write(f"            TSharedPtr<FJsonObject> ParentJson = {message.parent}::ToJson();\n")
                f.write("            for (const auto& Pair : ParentJson->Values) {\n")
                f.write("                JsonObj->SetField(Pair.Key, Pair.Value);\n")
                f.write("            }\n\n")

            # Serialize each field
            for field in message.fields:
                self._write_field_serialization(f, message_name, field)

            f.write("            return JsonObj;\n")
            f.write("        }\n\n")

            # Add FromJson method
            f.write("        /**\n")
            f.write("         * Populate this message from a JSON object\n")
            f.write("         * @param JsonObject JSON object to parse\n")
            f.write("         * @param OutMessage Message to populate\n")
            f.write("         * @return True if parsing was successful, false otherwise\n")
            f.write("         */\n")
            f.write(f"        static bool FromJson(const TSharedPtr<FJsonObject>& JsonObject, {message_name}& OutMessage) {{\n")

            # If this message inherits from another, call the parent's FromJson method
            if message.parent:
                f.write("            // Call parent class deserialization\n")
                f.write(f"            if (!{message.parent}::FromJson(JsonObject, OutMessage)) {{\n")
                f.write("                return false;\n")
                f.write("            }\n\n")

            # Deserialize each field
            for field in message.fields:
                self._write_field_deserialization(f, message_name, field)

            f.write("            return true;\n")
            f.write("        }\n")

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
        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            return f"Enum ({enum_name})"

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                components = ", ".join(field.compound_components)
                return f"Compound ({components})"
            else:
                return f"Compound ({field.compound_base_type})"

        elif field.field_type == FieldType.STRING:
            return "String (FString)"

        elif field.field_type == FieldType.INT:
            return "Integer (int32)"

        elif field.field_type == FieldType.FLOAT:
            return "Float (float)"

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
        # Add documentation comment for the field
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
            f.write(f"        /** {field_type_desc} field */\n")

        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            f.write(f"        {enum_name} {field.name};\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"        struct {{\n")
                for component in field.compound_components:
                    f.write(f"            /** {component} component of {field.name} */\n")
                    f.write(f"            float {component};\n")
                f.write(f"        }} {field.name};\n")
            else:
                # Handle other compound types if needed
                f.write(f"        // Unsupported compound type: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"        FString {field.name};\n")

        elif field.field_type == FieldType.INT:
            f.write(f"        int32 {field.name};\n")

        elif field.field_type == FieldType.FLOAT:
            f.write(f"        float {field.name};\n")

        else:
            f.write(f"        // Unsupported type: {field.field_type}\n")

    def _write_field_serialization(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write code to serialize a field to JSON.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to serialize
        """
        if field.field_type == FieldType.ENUM:
            f.write(f"            JsonObj->SetNumberField(\"{field.name}\", static_cast<int32>({field.name}));\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"            TSharedPtr<FJsonObject> {field.name}Obj = MakeShared<FJsonObject>();\n")
                for component in field.compound_components:
                    f.write(f"            {field.name}Obj->SetNumberField(\"{component}\", {field.name}.{component});\n")
                f.write(f"            JsonObj->SetObjectField(\"{field.name}\", {field.name}Obj);\n")
            else:
                # Handle other compound types if needed
                f.write(f"            // Unsupported compound type serialization: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"            JsonObj->SetStringField(\"{field.name}\", {field.name});\n")

        elif field.field_type == FieldType.INT:
            f.write(f"            JsonObj->SetNumberField(\"{field.name}\", {field.name});\n")

        elif field.field_type == FieldType.FLOAT:
            f.write(f"            JsonObj->SetNumberField(\"{field.name}\", {field.name});\n")

        else:
            f.write(f"            // Unsupported type serialization: {field.field_type}\n")

    def _write_field_deserialization(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write code to deserialize a field from JSON.

        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to deserialize
        """
        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            f.write(f"            int32 {field.name}Value;\n")
            f.write(f"            if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"            {{\n")
            f.write(f"                OutMessage.{field.name} = static_cast<{enum_name}>({field.name}Value);\n")
            f.write(f"            }}\n")
            f.write(f"            else\n")
            f.write(f"            {{\n")
            f.write(f"                return false;\n")
            f.write(f"            }}\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"            const TSharedPtr<FJsonObject>* {field.name}Obj;\n")
                f.write(f"            if (JsonObject->TryGetObjectField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Obj))\n")
                f.write(f"            {{\n")
                for component in field.compound_components:
                    f.write(f"                double {component}Value;\n")
                    f.write(f"                if ((*{field.name}Obj)->TryGetNumberField(StringCast<TCHAR>(\"{component}\").Get(), {component}Value))\n")
                    f.write(f"                {{\n")
                    f.write(f"                    OutMessage.{field.name}.{component} = static_cast<float>({component}Value);\n")
                    f.write(f"                }}\n")
                    f.write(f"                else\n")
                    f.write(f"                {{\n")
                    f.write(f"                    return false;\n")
                    f.write(f"                }}\n")
                f.write(f"            }}\n")
                f.write(f"            else\n")
                f.write(f"            {{\n")
                f.write(f"                return false;\n")
                f.write(f"            }}\n")
            else:
                # Handle other compound types if needed
                f.write(f"            // Unsupported compound type deserialization: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"            FString {field.name}Value;\n")
            f.write(f"            if (JsonObject->TryGetStringField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"            {{\n")
            f.write(f"                OutMessage.{field.name} = {field.name}Value;\n")
            f.write(f"            }}\n")
            f.write(f"            else\n")
            f.write(f"            {{\n")
            f.write(f"                return false;\n")
            f.write(f"            }}\n")

        elif field.field_type == FieldType.INT:
            f.write(f"            int32 {field.name}Value;\n")
            f.write(f"            if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"            {{\n")
            f.write(f"                OutMessage.{field.name} = {field.name}Value;\n")
            f.write(f"            }}\n")
            f.write(f"            else\n")
            f.write(f"            {{\n")
            f.write(f"                return false;\n")
            f.write(f"            }}\n")

        elif field.field_type == FieldType.FLOAT:
            f.write(f"            double {field.name}Value;\n")
            f.write(f"            if (JsonObject->TryGetNumberField(StringCast<TCHAR>(\"{field.name}\").Get(), {field.name}Value))\n")
            f.write(f"            {{\n")
            f.write(f"                OutMessage.{field.name} = static_cast<float>({field.name}Value);\n")
            f.write(f"            }}\n")
            f.write(f"            else\n")
            f.write(f"            {{\n")
            f.write(f"                return false;\n")
            f.write(f"            }}\n")

        else:
            f.write(f"            // Unsupported type deserialization: {field.field_type}\n")


class StandardCppGenerator(BaseCppGenerator):
    """
    Generator for standard C++ code from the intermediate representation.
    Uses standard C++ types and includes instead of Unreal Engine specific ones.
    """

    def __init__(self, model: MessageModel, output_dir: str):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
        """
        super().__init__(model, output_dir)

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

            # Generate header file
            header_file = os.path.join(self.output_dir, "StandardMessages.h")
            with open(header_file, 'w') as f:
                self._write_header(f)
                self._write_namespace_start(f)
                self._write_enums(f)
                self._write_forward_declarations(f)
                self._write_structs(f)
                self._write_namespace_end(f)

            print(f"Generated standard C++ header file: {header_file}")
            return True

        except Exception as e:
            print(f"Error generating standard C++ output: {str(e)}")
            return False

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
        f.write("// Each message is defined as a C++ struct within the Messages namespace.\n")
        f.write("//\n")
        f.write("// Message Structure:\n")
        f.write("// - Messages are defined as structs with specific fields\n")
        f.write("// - Messages can inherit from other messages using standard C++ inheritance\n")
        f.write("// - Fields can be of the following types:\n")
        f.write("//   * Basic types: int32_t (integer), float, std::string (string)\n")
        f.write("//   * Enum types: defined as enum class with uint8_t underlying type\n")
        f.write("//   * Compound types: struct with named components\n")
        f.write("//\n")
        f.write("// Enum Naming Convention:\n")
        f.write("// - Enums are named as MessageName_fieldName_Enum\n")
        f.write("//\n")
        f.write("// Compound Field Structure:\n")
        f.write("// - Compound fields are defined as anonymous structs within the message\n")
        f.write("// - Each component is a named field within the anonymous struct\n")
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
                        f.write(f"    enum class {enum_name} : uint8_t\n")
                        f.write("    {\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    };\n\n")
                        enums_generated.add(enum_name)

    def _write_structs(self, f: TextIO) -> None:
        """
        Write struct definitions.

        Args:
            f: The file to write to
        """
        for message_name, message in self.model.messages.items():
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
                f.write(f"    struct {message_name} : public {message.parent}\n")
            else:
                f.write(f"    struct {message_name}\n")

            f.write("    {\n")

            # Generate fields
            for field in message.fields:
                self._write_field(f, message_name, field)

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
        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            return f"Enum ({enum_name})"

        elif field.field_type == FieldType.COMPOUND:
            if field.compound_base_type == "float":
                components = ", ".join(field.compound_components)
                return f"Compound ({components})"
            else:
                return f"Compound ({field.compound_base_type})"

        elif field.field_type == FieldType.STRING:
            return "String (std::string)"

        elif field.field_type == FieldType.INT:
            return "Integer (int32_t)"

        elif field.field_type == FieldType.FLOAT:
            return "Float (float)"

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
        # Add documentation comment for the field
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
            f.write(f"        /** {field_type_desc} field */\n")

        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            f.write(f"        {enum_name} {field.name};\n")

        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"        struct {{\n")
                for component in field.compound_components:
                    f.write(f"            /** {component} component of {field.name} */\n")
                    f.write(f"            float {component};\n")
                f.write(f"        }} {field.name};\n")
            else:
                # Handle other compound types if needed
                f.write(f"        // Unsupported compound type: {field.compound_base_type}\n")

        elif field.field_type == FieldType.STRING:
            f.write(f"        std::string {field.name};\n")

        elif field.field_type == FieldType.INT:
            f.write(f"        int32_t {field.name};\n")

        elif field.field_type == FieldType.FLOAT:
            f.write(f"        float {field.name};\n")

        else:
            f.write(f"        // Unsupported type: {field.field_type}\n")
