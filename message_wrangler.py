#!/usr/bin/env python3
"""
MessageWrangler

This script processes a specific format in a file and transforms it into formats
that C++, TypeScript, JSON, and Python can use. The purpose is to have a single source file
describe messages that will be passed over WebSocket between an Electron app and
Unreal Engine.

Usage:
    python message_wrangler.py --input <input_file> --output <output_dir> [--cpp] [--ts] [--json] [--py] [--language <lang>] [--cpp-type <type>] [--output-name <name>] [--help]

Arguments:
    --input, -i     : Path to the input file containing message definitions
    --output, -o    : Directory where output files will be generated
    --cpp           : Generate C++ output (default: True)
    --ts            : Generate TypeScript output (default: True)
    --json          : Generate JSON schema output (default: True)
    --py            : Generate Python output (default: False)
    --language, -l  : Output language format (cpp, typescript, json, python, or all)
                      Can provide multiple languages (e.g., --language cpp typescript)
                      Overrides individual --cpp, --ts, --json, and --py flags when specified
    --cpp-type      : C++ output type (unreal, standard, or both)
                      unreal: Generate Unreal Engine C++ code with Unreal types
                      standard: Generate standard C++ code with std types
                      both: Generate both Unreal and standard C++ code (default)
    --output-name, -n : Base name for output files without extension (default: input filename)
                      Unreal C++ files will be prefixed with 'ue_'
                      Standard C++ files will be prefixed with 'c_'
                      JSON schema files will have '_schema' suffix
    --help, -h      : Show this help message

Example:
    python message_wrangler.py --input messages.def --output ./generated --cpp --ts --json --py
    python message_wrangler.py --input messages.def --output ./generated --language all
    python message_wrangler.py --input messages.def --output ./generated --language cpp
    python message_wrangler.py --input messages.def --output ./generated --language json
    python message_wrangler.py --input messages.def --output ./generated --language python
    python message_wrangler.py --input messages.def --output ./generated --language cpp typescript python
    python message_wrangler.py --input messages.def --output ./generated --cpp-type standard
    python message_wrangler.py --input messages.def --output ./generated --output-name custom_name
"""

import argparse
import os
import sys
from typing import Dict, List, Any, Optional

from message_model import MessageModel
from message_parser import MessageParser
from cpp_generator import UnrealCppGenerator, StandardCppGenerator
from typescript_generator import TypeScriptGenerator
from json_generator import JsonGenerator
from python_generator import PythonGenerator


class MessageFormatConverter:
    """
    Handles the conversion of message definitions from a source format
    to C++, TypeScript, JSON schema, and Python formats.
    """

    def __init__(self, input_file: str, output_dir: str, cpp_type: str = "both", output_name: str = None, verbose: bool = False):
        """
        Initialize the converter with input file and output directory.

        Args:
            input_file: Path to the input file containing message definitions
            output_dir: Directory where output files will be generated
            cpp_type: Type of C++ output to generate (unreal, standard, or both)
            output_name: Base name for output files without extension (default: input filename)
            verbose: Whether to print debug information (default: False)
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.cpp_type = cpp_type
        self.model = None
        self.verbose = verbose

        # If output_name is not provided, use the input filename without extension
        if output_name is None:
            self.output_name = os.path.splitext(os.path.basename(input_file))[0]
        else:
            self.output_name = output_name

    def parse_input_file(self) -> bool:
        """
        Parse the input file containing message definitions.

        Returns:
            bool: True if parsing was successful, False otherwise
        """
        parser = MessageParser(self.input_file, self.verbose)
        self.model = parser.parse()

        # If parsing failed, the errors will have been reported by the parser
        if self.model is None:
            return False

        return True

    def generate_cpp_output(self) -> bool:
        """
        Generate C++ output files from the parsed message definitions.
        The type of C++ output is determined by the cpp_type attribute.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not self.model:
            print("Error: No message model available. Parse input file first.")
            return False

        success = True

        if self.cpp_type in ["unreal", "both"]:
            # Use ue_ prefix for Unreal C++ files
            unreal_output_name = f"ue_{self.output_name}"
            generator = UnrealCppGenerator(self.model, self.output_dir, unreal_output_name)
            if not generator.generate():
                success = False
                print("Error generating Unreal C++ output.")

        if self.cpp_type in ["standard", "both"]:
            # Use c_ prefix for standard C++ files
            standard_output_name = f"c_{self.output_name}"
            generator = StandardCppGenerator(self.model, self.output_dir, standard_output_name)
            if not generator.generate():
                success = False
                print("Error generating standard C++ output.")

        return success

    def generate_typescript_output(self) -> bool:
        """
        Generate TypeScript output files from the parsed message definitions.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not self.model:
            print("Error: No message model available. Parse input file first.")
            return False

        generator = TypeScriptGenerator(self.model, self.output_dir, self.output_name)
        return generator.generate()

    def generate_json_output(self) -> bool:
        """
        Generate JSON schema output files from the parsed message definitions.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not self.model:
            print("Error: No message model available. Parse input file first.")
            return False

        # Add _msgs before _schema suffix for JSON schema files
        json_output_name = f"{self.output_name}_msgs_schema"
        generator = JsonGenerator(self.model, self.output_dir, json_output_name)
        return generator.generate()

    def generate_python_output(self) -> bool:
        """
        Generate Python output files from the parsed message definitions.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not self.model:
            print("Error: No message model available. Parse input file first.")
            return False

        generator = PythonGenerator(self.model, self.output_dir, self.output_name)
        return generator.generate()


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
    parser.add_argument('--json', action='store_true', help='Generate JSON schema output')
    parser.add_argument('--py', action='store_true', help='Generate Python output')
    parser.add_argument('--language', '-l', nargs='+', 
                        help='Output language format (cpp, typescript, json, python, or all)')
    parser.add_argument('--cpp-type', choices=['unreal', 'standard', 'both'], default='both',
                        help='C++ output type (unreal, standard, or both)')
    parser.add_argument('--output-name', '-n', help='Base name for output files without extension (default: input filename)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output for debugging')

    args = parser.parse_args()

    # Handle the relationship between --language and --cpp/--ts/--json flags
    if args.language:
        # Process language arguments to handle comma-separated values
        processed_languages = []
        for lang_arg in args.language:
            # Split by comma if it contains commas
            if ',' in lang_arg:
                split_langs = [l.strip() for l in lang_arg.split(',')]
                processed_languages.extend(split_langs)
            else:
                processed_languages.append(lang_arg)

        # Validate each language value
        valid_choices = ['cpp', 'typescript', 'json', 'python', 'all']
        for lang in processed_languages:
            if lang not in valid_choices:
                parser.error(f"argument --language/-l: invalid choice: '{lang}' (choose from 'cpp', 'typescript', 'json', 'python', 'all')")

        # Replace the original list with processed list
        args.language = processed_languages

        # Reset all flags first
        args.cpp = False
        args.ts = False
        args.json = False
        args.py = False

        # If --language is specified, it overrides individual flags
        for lang in args.language:
            if lang == 'cpp':
                args.cpp = True
            elif lang == 'typescript':
                args.ts = True
            elif lang == 'json':
                args.json = True
            elif lang == 'python':
                args.py = True
            elif lang == 'all':
                args.cpp = True
                args.ts = True
                args.json = True
                args.py = True
    else:
        # If no language specified but individual flags are set
        if args.cpp and not args.ts and not args.json and not args.py:
            args.language = 'cpp'
        elif args.ts and not args.cpp and not args.json and not args.py:
            args.language = 'typescript'
        elif args.json and not args.cpp and not args.ts and not args.py:
            args.language = 'json'
        elif args.py and not args.cpp and not args.ts and not args.json:
            args.language = 'python'
        else:
            # Default: generate all except Python
            args.cpp = True
            args.ts = True
            args.json = True
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
    cpp_type = os.environ.get('MW_CPP_TYPE', args.cpp_type)
    output_name = os.environ.get('MW_OUTPUT_NAME', args.output_name)

    # Handle environment variable for language preference
    if 'MW_LANGUAGE' in os.environ:
        # Reset all flags first
        args.cpp = False
        args.ts = False
        args.json = False
        args.py = False

        # Split the environment variable by spaces or commas to get a list of languages
        env_languages = [lang.strip().lower() for lang in os.environ['MW_LANGUAGE'].replace(',', ' ').split()]

        for env_language in env_languages:
            if env_language == 'cpp':
                args.cpp = True
            elif env_language == 'typescript':
                args.ts = True
            elif env_language == 'json':
                args.json = True
            elif env_language == 'python':
                args.py = True
            elif env_language == 'all' or env_language == 'both':  # Support both for backward compatibility
                args.cpp = True
                args.ts = True
                args.json = True
                args.py = True

    # Create converter instance
    verbose = os.environ.get('MW_VERBOSE', args.verbose)
    converter = MessageFormatConverter(input_file, output_dir, cpp_type, output_name, verbose)

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

    if args.json:
        if not converter.generate_json_output():
            success = False

    if args.py:
        if not converter.generate_python_output():
            success = False

    if success:
        print("Message format conversion completed successfully.")
    else:
        print("Message format conversion completed with errors.")
        sys.exit(1)


if __name__ == '__main__':
    main()
