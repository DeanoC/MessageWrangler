#!/usr/bin/env python3
"""
MessageWrangler

This script processes a specific format in a file and transforms it into formats
that both C++ and TypeScript can use. The purpose is to have a single source file
describe messages that will be passed over WebSocket between an Electron app and
Unreal Engine.

Usage:
    python message_wrangler.py --input <input_file> --output <output_dir> [--cpp] [--ts] [--help]

Arguments:
    --input, -i     : Path to the input file containing message definitions
    --output, -o    : Directory where output files will be generated
    --cpp           : Generate C++ output (default: True)
    --ts            : Generate TypeScript output (default: True)
    --help, -h      : Show this help message

Example:
    python message_wrangler.py --input messages.def --output ./generated --cpp --ts
"""

import argparse
import os
import sys
import json
from typing import Dict, List, Any, Optional


class MessageFormatConverter:
    """
    Handles the conversion of message definitions from a source format
    to C++ and TypeScript formats.
    """

    def __init__(self, input_file: str, output_dir: str):
        """
        Initialize the converter with input file and output directory.

        Args:
            input_file: Path to the input file containing message definitions
            output_dir: Directory where output files will be generated
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.messages = {}

    def parse_input_file(self) -> bool:
        """
        Parse the input file containing message definitions.

        Returns:
            bool: True if parsing was successful, False otherwise
        """
        try:
            print(f"Parsing input file: {self.input_file}")

            # Check if the file exists
            if not os.path.exists(self.input_file):
                print(f"Error: Input file '{self.input_file}' does not exist.")
                return False

            # Reset messages dictionary
            self.messages = {}

            # Read the file content
            with open(self.input_file, 'r') as f:
                content = f.read()

            # Parse the content
            current_message = None
            current_message_name = None
            parent_message = None

            # Split content into lines and process each line
            lines = content.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Skip empty lines
                if not line:
                    i += 1
                    continue

                # Parse message definition
                if line.startswith('message '):
                    # Extract message name and parent if exists
                    message_def = line[len('message '):].strip()
                    if '{' in message_def:
                        message_def = message_def[:message_def.find('{')].strip()

                    # Check for inheritance
                    if ':' in message_def:
                        parts = message_def.split(':')
                        current_message_name = parts[0].strip()
                        parent_message = parts[1].strip()
                    else:
                        current_message_name = message_def
                        parent_message = None

                    # Create new message entry
                    current_message = {
                        "fields": [],
                        "parent": parent_message,
                        "description": f"{current_message_name} message"
                    }
                    self.messages[current_message_name] = current_message

                # Parse field definition
                elif line.startswith('field ') and current_message is not None:
                    # Extract field name and type
                    field_def = line[len('field '):].strip()
                    if ':' in field_def:
                        name, type_def = field_def.split(':', 1)
                        name = name.strip()
                        type_def = type_def.strip()

                        # Handle enum type
                        if type_def.startswith('enum'):
                            enum_values = []
                            if '{' in type_def and '}' in type_def:
                                enum_str = type_def[type_def.find('{')+1:type_def.find('}')].strip()
                                enum_values = [v.strip() for v in enum_str.split(',')]

                            field = {
                                "name": name,
                                "type": "enum",
                                "enum_values": enum_values,
                                "description": f"{name} enum field"
                            }
                            current_message["fields"].append(field)

                        # Handle compound type (like float { x, y, z })
                        elif '{' in type_def and '}' in type_def:
                            base_type = type_def[:type_def.find('{')].strip()
                            components_str = type_def[type_def.find('{')+1:type_def.find('}')].strip()
                            components = [c.strip() for c in components_str.split(',')]

                            field = {
                                "name": name,
                                "type": "compound",
                                "base_type": base_type,
                                "components": components,
                                "description": f"{name} compound field"
                            }
                            current_message["fields"].append(field)

                        # Handle simple type
                        else:
                            field = {
                                "name": name,
                                "type": type_def,
                                "description": f"{name} field"
                            }
                            current_message["fields"].append(field)

                # Check for closing brace of message definition
                elif line == '}':
                    current_message = None
                    current_message_name = None

                i += 1

            print(f"Successfully parsed {len(self.messages)} message definitions.")
            return True

        except Exception as e:
            print(f"Error parsing input file: {str(e)}")
            return False

    def generate_cpp_output(self) -> bool:
        """
        Generate C++ output files from the parsed message definitions.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating C++ output in: {self.output_dir}")

            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)

            # Generate header file
            header_file = os.path.join(self.output_dir, "Messages.h")
            with open(header_file, 'w') as f:
                f.write("// Auto-generated message definitions for C++\n")
                f.write("#pragma once\n\n")
                f.write("#include \"CoreMinimal.h\"\n\n")

                f.write("namespace Messages {\n\n")

                # Generate enum definitions
                enums_generated = set()
                for message_name, message in self.messages.items():
                    for field in message["fields"]:
                        if field["type"] == "enum":
                            enum_name = f"{message_name}_{field['name']}_Enum"
                            if enum_name not in enums_generated:
                                f.write(f"    // Enum for {message_name}.{field['name']}\n")
                                f.write(f"    enum class {enum_name} : uint8\n")
                                f.write("    {\n")
                                for i, value in enumerate(field["enum_values"]):
                                    f.write(f"        {value} = {i},\n")
                                f.write("    };\n\n")
                                enums_generated.add(enum_name)

                # First pass: forward declare all structs
                for message_name in self.messages:
                    f.write(f"    struct {message_name};\n")
                f.write("\n")

                # Second pass: generate struct definitions
                for message_name, message in self.messages.items():
                    f.write(f"    // {message['description']}\n")

                    # Handle inheritance
                    if message["parent"]:
                        f.write(f"    struct {message_name} : public {message['parent']}\n")
                    else:
                        f.write(f"    struct {message_name}\n")

                    f.write("    {\n")

                    # Generate fields
                    for field in message["fields"]:
                        if field["type"] == "enum":
                            enum_name = f"{message_name}_{field['name']}_Enum"
                            f.write(f"        {enum_name} {field['name']};\n")
                        elif field["type"] == "compound":
                            # For compound fields like position with x, y, z
                            if field["base_type"] == "float":
                                f.write(f"        struct {{\n")
                                for component in field["components"]:
                                    f.write(f"            float {component};\n")
                                f.write(f"        }} {field['name']};\n")
                            else:
                                # Handle other compound types if needed
                                f.write(f"        // Unsupported compound type: {field['base_type']}\n")
                        elif field["type"] == "string":
                            f.write(f"        FString {field['name']};\n")
                        elif field["type"] == "int":
                            f.write(f"        int32 {field['name']};\n")
                        elif field["type"] == "float":
                            f.write(f"        float {field['name']};\n")
                        else:
                            f.write(f"        // Unsupported type: {field['type']}\n")

                    f.write("    };\n\n")

                f.write("} // namespace Messages\n")

            print(f"Generated C++ header file: {header_file}")
            return True

        except Exception as e:
            print(f"Error generating C++ output: {str(e)}")
            return False

    def generate_typescript_output(self) -> bool:
        """
        Generate TypeScript output files from the parsed message definitions.

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
                f.write("// Auto-generated message definitions for TypeScript\n\n")
                f.write("export namespace Messages {\n\n")

                # Generate enum definitions
                enums_generated = set()
                for message_name, message in self.messages.items():
                    for field in message["fields"]:
                        if field["type"] == "enum":
                            enum_name = f"{message_name}_{field['name']}_Enum"
                            if enum_name not in enums_generated:
                                f.write(f"    // Enum for {message_name}.{field['name']}\n")
                                f.write(f"    export enum {enum_name} {{\n")
                                for i, value in enumerate(field["enum_values"]):
                                    f.write(f"        {value} = {i},\n")
                                f.write("    }\n\n")
                                enums_generated.add(enum_name)

                # Generate interface definitions
                for message_name, message in self.messages.items():
                    f.write(f"    // {message['description']}\n")

                    # Handle inheritance
                    if message["parent"]:
                        f.write(f"    export interface {message_name} extends {message['parent']} {{\n")
                    else:
                        f.write(f"    export interface {message_name} {{\n")

                    # Generate fields
                    for field in message["fields"]:
                        if field["type"] == "enum":
                            enum_name = f"{message_name}_{field['name']}_Enum"
                            f.write(f"        {field['name']}: {enum_name};\n")
                        elif field["type"] == "compound":
                            # For compound fields like position with x, y, z
                            if field["base_type"] == "float":
                                f.write(f"        {field['name']}: {{\n")
                                for component in field["components"]:
                                    f.write(f"            {component}: number;\n")
                                f.write("        };\n")
                            else:
                                # Handle other compound types if needed
                                f.write(f"        // Unsupported compound type: {field['base_type']}\n")
                        elif field["type"] == "string":
                            f.write(f"        {field['name']}: string;\n")
                        elif field["type"] == "int":
                            f.write(f"        {field['name']}: number;\n")
                        elif field["type"] == "float":
                            f.write(f"        {field['name']}: number;\n")
                        else:
                            f.write(f"        // Unsupported type: {field['type']}\n")

                    f.write("    }\n\n")

                f.write("} // namespace Messages\n")

            print(f"Generated TypeScript file: {ts_file}")
            return True

        except Exception as e:
            print(f"Error generating TypeScript output: {str(e)}")
            return False


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert message definitions to C++ and TypeScript formats",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('--input', '-i', required=True, help='Path to the input file containing message definitions')
    parser.add_argument('--output', '-o', required=True, help='Directory where output files will be generated')
    parser.add_argument('--cpp', action='store_true', help='Generate C++ output')
    parser.add_argument('--ts', action='store_true', help='Generate TypeScript output')
    parser.add_argument('--language', '-l', choices=['cpp', 'typescript', 'all'], 
                        help='Output language format (cpp, typescript, or all)')
    
    args = parser.parse_args()
    
    # Handle the relationship between --language and --cpp/--ts flags
    if args.language:
        # If --language is specified, it overrides individual flags
        if args.language == 'cpp':
            args.cpp = True
            args.ts = False
        elif args.language == 'typescript':
            args.cpp = False
            args.ts = True
        elif args.language == 'all':
            args.cpp = True
            args.ts = True
    else:
        # If no language specified but individual flags are set
        if args.cpp and not args.ts:
            args.language = 'cpp'
        elif args.ts and not args.cpp:
            args.language = 'typescript'
        else:
            # Default: generate all
            args.cpp = True
            args.ts = True
            args.language = 'all'
            
    return args


def main():
    """
    Main entry point of the script.
    """
    args = parse_arguments()

    # Override with environment variables if set
    input_file = os.environ.get('MW_INPUT_FILE', args.input)
    output_dir = os.environ.get('MW_OUTPUT_DIR', args.output)
    
    # Handle environment variable for language preference
    if 'MW_LANGUAGE' in os.environ:
        env_language = os.environ['MW_LANGUAGE'].lower()
        if env_language == 'cpp':
            args.cpp = True
            args.ts = False
        elif env_language == 'typescript':
            args.cpp = False
            args.ts = True
        elif env_language == 'all' or env_language == 'both':  # Support both for backward compatibility
            args.cpp = True
            args.ts = True

    # Create converter instance
    converter = MessageFormatConverter(input_file, output_dir)

    # Parse input file
    if not converter.parse_input_file():
        sys.exit(1)

    # Generate outputs based on command line arguments
    success = True

    if args.cpp:
        if not converter.generate_cpp_output():
            success = False

    if args.ts:
        if not converter.generate_typescript_output():
            success = False

    if success:
        print("Message format conversion completed successfully.")
    else:
        print("Message format conversion completed with errors.")
        sys.exit(1)


if __name__ == '__main__':
    main()
