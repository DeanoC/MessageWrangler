"""
Test Enum Single Value

This script tests parsing a message with an enum field that has a single value.
It uses randomized names to ensure the test isn't passing due to hardcoded special cases.
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser_core import MessageParser
from tests.test_utils import randomize_def_file, cleanup_temp_dir

def main():
    """Parse a randomized version of test_enum_single_value.def and print the results."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_enum_single_value.def")

    # Create a randomized version of the file
    temp_dir, random_file_path, name_mapping = randomize_def_file(original_file)

    try:
        # Get the directory and filename of the random file
        random_file_dir = os.path.dirname(random_file_path)
        random_file_name = os.path.basename(random_file_path)

        # Change to the directory containing the random file
        original_dir = os.getcwd()
        os.chdir(random_file_dir)

        # Parse the randomized file
        parser = MessageParser(random_file_name)

        # Print errors and warnings before parsing
        print("Errors and warnings before parsing:")
        print(f"  Errors: {parser.errors}")
        print(f"  Warnings: {parser.warnings}")

        model = parser.parse()

        # Print errors and warnings after parsing
        print("\nErrors and warnings after parsing:")
        if parser.errors:
            print("\nErrors:")
            for error in parser.errors:
                print(f"  {error}")
        else:
            print("  Errors: []")

        if parser.warnings:
            print("\nWarnings:")
            for warning in parser.warnings:
                print(f"  {warning}")
        else:
            print("  Warnings: []")

        if model is None:
            print(f"Failed to parse {random_file_name}")
            return

        print("\nMessages in model:")
        for msg_name, msg in model.messages.items():
            print(f"  {msg_name} (namespace: {msg.namespace}, parent: {msg.parent})")
            print(f"    Fields: {len(msg.fields)}")
            for field in msg.fields:
                print(f"      {field.name}: {field.field_type.value}")
                if field.field_type == FieldType.ENUM:
                    print(f"        Enum values: {[v.name for v in field.enum_values]}")

        # Print the name mapping for reference
        print("\nName mapping:")
        for original_name, random_name in name_mapping.items():
            print(f"  {original_name} -> {random_name}")

        # Change back to the original directory
        os.chdir(original_dir)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)

if __name__ == "__main__":
    main()
