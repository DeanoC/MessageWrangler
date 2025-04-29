"""
Test script for multi-line support in message parser.
"""

import os
import pytest
from message_parser import MessageParser


def test_parse_multiline_def():
    """Test parsing of test_multiline.def file."""
    # Use the file in the tests directory
    file_path = os.path.join(os.path.dirname(__file__), "test_multiline.def")
    parser = MessageParser(file_path)
    model = parser.parse()

    assert model is not None, "Failed to parse test_multiline.def"
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
