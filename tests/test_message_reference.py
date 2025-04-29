"""
Test Message Reference

This script tests that using a message directly as a field type generates an error.
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser

def main():
    """Create a temporary file with a message that uses another message directly as a field type, and parse it."""
    # Create a temporary file
    with open("tests/temp_message_reference.def", "w") as f:
        f.write("""
message BaseMessage {
    field baseField: string;
}

message MainMessage {
    field baseMessage: BaseMessage;
    field mainField: string;
}
        """)

    # Print the content of the file
    print("Content of the file:")
    with open("tests/temp_message_reference.def", "r") as f:
        print(f.read())

    # Parse the file
    parser = MessageParser("tests/temp_message_reference.def")

    # Add a debug print to see if the parser is initialized correctly
    print("\nParser initialized with input file:", parser.input_file)
    print("Reserved keywords:", parser.reserved_keywords)

    # Parse the file
    model = parser.parse()

    # Print errors and warnings
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

    # Print the messages in the model
    if model:
        print("\nMessages in model:")
        for msg_name, msg in model.messages.items():
            print(f"  {msg_name} (namespace: {msg.namespace}, parent: {msg.parent})")
            print(f"    Fields: {len(msg.fields)}")
            for field in msg.fields:
                print(f"      {field.name}: {field.field_type.value}")

    # Clean up
    os.remove("tests/temp_message_reference.def")

if __name__ == "__main__":
    main()
