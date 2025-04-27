#!/usr/bin/env python3
"""
MessageWrangler

This script processes a specific format in a file and transforms it into formats
that both C++ and TypeScript can use. The purpose is to have a single source file
describe messages that will be passed over WebSocket between an Electron app and
Unreal Engine.

Usage:
    python message_wrangler.py --input <input_file> --output <output_dir> [--cpp] [--ts] [--language <lang>] [--help]

Arguments:
    --input, -i     : Path to the input file containing message definitions
    --output, -o    : Directory where output files will be generated
    --cpp           : Generate C++ output (default: True)
    --ts            : Generate TypeScript output (default: True)
    --language, -l  : Output language format (cpp, typescript, or all)
                      Overrides individual --cpp and --ts flags when specified
    --help, -h      : Show this help message

Example:
    python message_wrangler.py --input messages.def --output ./generated --cpp --ts
    python message_wrangler.py --input messages.def --output ./generated --language all
    python message_wrangler.py --input messages.def --output ./generated --language cpp
"""

import argparse
import os
import sys
from typing import Dict, List, Any, Optional

from message_model import MessageModel
from message_parser import MessageParser
from cpp_generator import CppGenerator
from typescript_generator import TypeScriptGenerator


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
        self.model = None

    def parse_input_file(self) -> bool:
        """
        Parse the input file containing message definitions.

        Returns:
            bool: True if parsing was successful, False otherwise
        """
        parser = MessageParser(self.input_file)
        self.model = parser.parse()
        return self.model is not None

    def generate_cpp_output(self) -> bool:
        """
        Generate C++ output files from the parsed message definitions.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not self.model:
            print("Error: No message model available. Parse input file first.")
            return False

        generator = CppGenerator(self.model, self.output_dir)
        return generator.generate()

    def generate_typescript_output(self) -> bool:
        """
        Generate TypeScript output files from the parsed message definitions.

        Returns:
            bool: True if generation was successful, False otherwise
        """
        if not self.model:
            print("Error: No message model available. Parse input file first.")
            return False

        generator = TypeScriptGenerator(self.model, self.output_dir)
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
