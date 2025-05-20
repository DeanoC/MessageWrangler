"""
Test script for multi-line support in message parser.
It uses randomized names to ensure the test isn't passing due to hardcoded special cases.
"""

import os
import pytest
from message_parser_core import MessageParser
from tests.test_utils import randomize_def_file, cleanup_temp_dir


def test_parse_multiline_def():
    """Test parsing of test_multiline.def file with randomized names."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_multiline.def")

    # Create a randomized version of the file
    temp_dir, random_file_path, name_mapping = randomize_def_file(original_file)

    try:
        # Get the directory and filename of the random file
        random_file_dir = os.path.dirname(random_file_path)
        random_file_name = os.path.basename(random_file_path)

        # Store the original directory
        original_dir = os.getcwd()

        # Change to the directory containing the random file
        os.chdir(random_file_dir)

        # Parse the randomized file
        parser = MessageParser(random_file_name)
        model = parser.parse()

        # Change back to the original directory
        os.chdir(original_dir)

        # Check that the model was created successfully
        assert model is not None, f"Failed to parse {random_file_name}"
        assert len(model.messages) > 0, "No messages were parsed"

        # Verify details of each message
        for message_name, message in model.messages.items():
            assert message.description is not None
            assert len(message.fields) > 0, f"Message {message_name} should have fields"

            for field in message.fields:
                assert field.name, f"Field in {message_name} should have a name"
                assert field.field_type, f"Field {field.name} should have a type"

                # Check enum fields
                if field.field_type.value == "enum":
                    assert len(field.enum_values) > 0, f"Enum field {field.name} should have values"

                # Check compound fields
                if field.field_type.value == "compound":
                    assert field.compound_base_type, f"Compound field {field.name} should have a base type"
                    assert field.compound_components, f"Compound field {field.name} should have components"
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)
