"""
Test Enum Numbering

This script tests parsing a message with enum fields that have explicit value assignments
and auto-increment from the last defined value.
"""

import os
import sys
import pytest

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser

def test_enum_numbering():
    """Test parsing enum fields with explicit value assignments and auto-increment."""
    parser = MessageParser("tests/test_enum_numbering.def", verbose=True)
    model = parser.parse()

    # Check that there are no errors
    assert not parser.errors, f"Parser errors: {parser.errors}"

    # Check that the model was created
    assert model is not None, "Failed to parse test_enum_numbering.def"

    # Get the TestEnumNumbering message
    message = model.get_message("TestEnumNumbering")
    assert message is not None, "TestEnumNumbering message not found in model"

    # Check that the message has the expected fields
    assert len(message.fields) == 4, f"Expected 4 fields, got {len(message.fields)}"

    # Check the explicitValues enum
    explicit_values_field = next((f for f in message.fields if f.name == "explicitValues"), None)
    assert explicit_values_field is not None, "explicitValues field not found"
    assert explicit_values_field.field_type == FieldType.ENUM, "explicitValues field is not an enum"

    # Check the enum values
    enum_values = {v.name: v.value for v in explicit_values_field.enum_values}
    assert enum_values == {"Zero": 0, "One": 1, "Ten": 10, "Hundred": 100}, f"Unexpected enum values: {enum_values}"

    # Check the autoIncrement enum
    auto_increment_field = next((f for f in message.fields if f.name == "autoIncrement"), None)
    assert auto_increment_field is not None, "autoIncrement field not found"
    assert auto_increment_field.field_type == FieldType.ENUM, "autoIncrement field is not an enum"

    # Check the enum values
    enum_values = {v.name: v.value for v in auto_increment_field.enum_values}
    assert enum_values == {"Start": 5, "Next": 6, "Another": 7}, f"Unexpected enum values: {enum_values}"

    # Check the mixedAssignments enum
    mixed_assignments_field = next((f for f in message.fields if f.name == "mixedAssignments"), None)
    assert mixed_assignments_field is not None, "mixedAssignments field not found"
    assert mixed_assignments_field.field_type == FieldType.ENUM, "mixedAssignments field is not an enum"

    # Check the enum values
    enum_values = {v.name: v.value for v in mixed_assignments_field.enum_values}
    assert enum_values == {"First": 0, "Second": 2, "Third": 3, "Fourth": 10, "Fifth": 11}, f"Unexpected enum values: {enum_values}"

    # Check the negativeValues enum
    negative_values_field = next((f for f in message.fields if f.name == "negativeValues"), None)
    assert negative_values_field is not None, "negativeValues field not found"
    assert negative_values_field.field_type == FieldType.ENUM, "negativeValues field is not an enum"

    # Check the enum values
    enum_values = {v.name: v.value for v in negative_values_field.enum_values}
    assert enum_values == {"Negative": -10, "NextNegative": -9, "Zero": 0, "Positive": 1}, f"Unexpected enum values: {enum_values}"

def main():
    """Run the test manually."""
    try:
        test_enum_numbering()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    main()
