"""
Test Message Reference

This script tests that using a message directly as a field type generates an error.
It uses randomized names to ensure the test isn't passing due to hardcoded special cases.
"""

import os
import sys
import tempfile

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser_core import MessageParser
from tests.test_utils import generate_random_name

def main():
    """Create a temporary file with a message that uses another message directly as a field type, and parse it."""
    # Generate random names for messages and fields
    base_message = f"RandomBase_{generate_random_name()}"
    base_field = f"randomBaseField_{generate_random_name()}"
    main_message = f"RandomMain_{generate_random_name()}"
    base_message_field = f"randomBaseMessage_{generate_random_name()}"
    main_field = f"randomMainField_{generate_random_name()}"

    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.def')
    temp_file_path = temp_file.name

    with open(temp_file_path, "w") as f:
        f.write(f"""
message {base_message} {{
    field {base_field}: string;
}}

message {main_message} {{
    field {base_message_field}: {base_message};
    field {main_field}: string;
}}
        """)

    # Print the content of the file
    print("Content of the file:")
    with open(temp_file_path, "r") as f:
        print(f.read())

    # Parse the file
    parser = MessageParser(temp_file_path)

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
    os.remove(temp_file_path)

if __name__ == "__main__":
    main()
