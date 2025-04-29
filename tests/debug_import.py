"""
Debug Import Command

This script parses the main.def file and prints the results.
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser

def main():
    """Parse the main.def file and print the results."""
    parser = MessageParser("tests/main.def")

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
        print("Failed to parse main.def")
        return

    print("\nMessages in model:")
    for msg_name, msg in model.messages.items():
        print(f"  {msg_name} (namespace: {msg.namespace}, parent: {msg.parent})")
        print(f"    Fields: {len(msg.fields)}")
        for field in msg.fields:
            print(f"      {field.name}: {field.field_type.value}")

    # Check if DerivedMessage is in the model
    derived_message = None
    for msg_name, msg in model.messages.items():
        if msg.name == "DerivedMessage":
            derived_message = msg
            print(f"\nFound DerivedMessage: {msg_name} (namespace: {msg.namespace}, parent: {msg.parent})")
            break

    if derived_message is None:
        print("\nDerivedMessage not found in model")

    # Check if MainMessage has the expected fields
    main_message = model.get_message("MainMessage")
    if main_message is not None:
        print(f"\nMainMessage has {len(main_message.fields)} fields:")
        for field in main_message.fields:
            print(f"  {field.name}: {field.field_type.value}")
    else:
        print("\nMainMessage not found in model")

if __name__ == "__main__":
    main()
