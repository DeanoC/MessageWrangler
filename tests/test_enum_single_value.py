"""
Test Enum Single Value

This script tests parsing a message with an enum field that has a single value.
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser

def main():
    """Parse the test_enum_single_value.def file and print the results."""
    parser = MessageParser("tests/test_enum_single_value.def")

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
        print("Failed to parse test_enum_single_value.def")
        return

    print("\nMessages in model:")
    for msg_name, msg in model.messages.items():
        print(f"  {msg_name} (namespace: {msg.namespace}, parent: {msg.parent})")
        print(f"    Fields: {len(msg.fields)}")
        for field in msg.fields:
            print(f"      {field.name}: {field.field_type.value}")
            if field.field_type == FieldType.ENUM:
                print(f"        Enum values: {[v.name for v in field.enum_values]}")

if __name__ == "__main__":
    main()