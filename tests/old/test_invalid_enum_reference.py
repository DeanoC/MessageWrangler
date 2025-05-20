import os
import sys
import pytest
import tempfile

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_parser_core import MessageParser
from tests.test_utils import generate_random_name

def test_invalid_enum_reference_field():
    """Test that referencing a non-existent enum field generates an error."""
    # Generate random names
    base_namespace = f"RandomBase_{generate_random_name()}"
    command_message = f"RandomCommand_{generate_random_name()}"
    type_field = f"randomType_{generate_random_name()}"
    status_value = f"RANDOM_STATUS_{generate_random_name()}"
    comm_command = f"RandomCommCommand_{generate_random_name()}"
    type_x_field = f"randomTypeX_{generate_random_name()}"
    change_mode = f"RANDOM_CHANGE_MODE_{generate_random_name()}"
    non_existent_message = f"RandomNonExistent_{generate_random_name()}"
    non_existent_field = f"randomNonExistent_{generate_random_name()}"

    # Create a temporary file with an invalid enum reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        message {base_namespace}::{command_message} {{
            field {type_field}: enum {{ {status_value} }}
        }}

        message {comm_command} : {base_namespace}::{command_message} {{
            field {type_x_field}: enum {non_existent_message}.{non_existent_field} + enum {{ {change_mode} }}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid enum reference
        assert any(f"Message '{non_existent_message}' referenced by enum reference" in error for error in parser.errors), \
            f"Expected error about non-existent message, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_invalid_enum_reference_field_in_namespace():
    """Test that referencing a non-existent enum field in a namespace generates an error."""
    # Generate random names
    base_namespace = f"RandomBase_{generate_random_name()}"
    command_message = f"RandomCommand_{generate_random_name()}"
    type_field = f"randomType_{generate_random_name()}"
    status_value = f"RANDOM_STATUS_{generate_random_name()}"
    comm_command = f"RandomCommCommand_{generate_random_name()}"
    type_x_field = f"randomTypeX_{generate_random_name()}"
    change_mode = f"RANDOM_CHANGE_MODE_{generate_random_name()}"
    non_existent_field = f"randomNonExistent_{generate_random_name()}"

    # Create a temporary file with an invalid enum reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        namespace {base_namespace} {{
            message {command_message} {{
                field {type_field}: enum {{ {status_value} }}
            }}
        }}

        message {comm_command} : {base_namespace}::{command_message} {{
            field {type_x_field}: enum {base_namespace}::{command_message}.{non_existent_field} + enum {{ {change_mode} }}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid enum reference
        assert any(f"Enum '{non_existent_field}' not found in message '{base_namespace}::{command_message}'" in error for error in parser.errors), \
            f"Expected error about non-existent enum field, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
