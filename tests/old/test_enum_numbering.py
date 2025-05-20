"""
Test Enum Numbering

This script tests parsing a message with enum fields that have explicit value assignments
and auto-increment from the last defined value.
It uses randomized names to ensure the test isn't passing due to hardcoded special cases.
"""

import os
import sys
import pytest
import tempfile
import shutil

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser_core import MessageParser
from tests.test_utils import randomize_def_file, cleanup_temp_dir

def test_enum_numbering():
    """Test parsing enum fields with explicit value assignments and auto-increment using randomized names."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_enum_numbering.def")

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
        parser = MessageParser(random_file_name, verbose=True)
        model = parser.parse()

        # Change back to the original directory
        os.chdir(original_dir)

        # Check that there are no errors
        assert not parser.errors, f"Parser errors: {parser.errors}"

        # Check that the model was created
        assert model is not None, f"Failed to parse {random_file_name}"

        # Get the randomized message name
        test_enum_numbering = name_mapping.get("TestEnumNumbering", "TestEnumNumbering")

        # Get the message
        message = model.get_message(test_enum_numbering)
        assert message is not None, f"{test_enum_numbering} message not found in model"

        # Check that the message has the expected fields
        assert len(message.fields) == 4, f"Expected 4 fields, got {len(message.fields)}"

        # Get the randomized field names
        explicit_values = name_mapping.get("explicitValues", "explicitValues")
        auto_increment = name_mapping.get("autoIncrement", "autoIncrement")
        mixed_assignments = name_mapping.get("mixedAssignments", "mixedAssignments")
        negative_values = name_mapping.get("negativeValues", "negativeValues")

        # Get the randomized enum value names
        zero = name_mapping.get("Zero", "Zero")
        one = name_mapping.get("One", "One")
        ten = name_mapping.get("Ten", "Ten")
        hundred = name_mapping.get("Hundred", "Hundred")
        start = name_mapping.get("Start", "Start")
        next_val = name_mapping.get("Next", "Next")
        another = name_mapping.get("Another", "Another")
        first = name_mapping.get("First", "First")
        second = name_mapping.get("Second", "Second")
        third = name_mapping.get("Third", "Third")
        fourth = name_mapping.get("Fourth", "Fourth")
        fifth = name_mapping.get("Fifth", "Fifth")
        negative = name_mapping.get("Negative", "Negative")
        next_negative = name_mapping.get("NextNegative", "NextNegative")
        positive = name_mapping.get("Positive", "Positive")

        # Check the explicitValues enum
        explicit_values_field = next((f for f in message.fields if f.name == explicit_values), None)
        assert explicit_values_field is not None, f"{explicit_values} field not found"
        assert explicit_values_field.field_type == FieldType.ENUM, f"{explicit_values} field is not an enum"

        # Check the enum values
        enum_values = {v.name: v.value for v in explicit_values_field.enum_values}
        expected_values = {zero: 0, one: 1, ten: 10, hundred: 100}
        assert enum_values == expected_values, f"Unexpected enum values: {enum_values}, expected: {expected_values}"

        # Check the autoIncrement enum
        auto_increment_field = next((f for f in message.fields if f.name == auto_increment), None)
        assert auto_increment_field is not None, f"{auto_increment} field not found"
        assert auto_increment_field.field_type == FieldType.ENUM, f"{auto_increment} field is not an enum"

        # Check the enum values
        enum_values = {v.name: v.value for v in auto_increment_field.enum_values}
        expected_values = {start: 5, next_val: 6, another: 7}
        assert enum_values == expected_values, f"Unexpected enum values: {enum_values}, expected: {expected_values}"

        # Check the mixedAssignments enum
        mixed_assignments_field = next((f for f in message.fields if f.name == mixed_assignments), None)
        assert mixed_assignments_field is not None, f"{mixed_assignments} field not found"
        assert mixed_assignments_field.field_type == FieldType.ENUM, f"{mixed_assignments} field is not an enum"

        # Check the enum values
        enum_values = {v.name: v.value for v in mixed_assignments_field.enum_values}
        expected_values = {first: 0, second: 2, third: 3, fourth: 10, fifth: 11}
        assert enum_values == expected_values, f"Unexpected enum values: {enum_values}, expected: {expected_values}"

        # Check the negativeValues enum
        negative_values_field = next((f for f in message.fields if f.name == negative_values), None)
        assert negative_values_field is not None, f"{negative_values} field not found"
        assert negative_values_field.field_type == FieldType.ENUM, f"{negative_values} field is not an enum"

        # Check the enum values
        enum_values = {v.name: v.value for v in negative_values_field.enum_values}
        expected_values = {negative: -10, next_negative: -9, zero: 0, positive: 1}
        assert enum_values == expected_values, f"Unexpected enum values: {enum_values}, expected: {expected_values}"
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)

def main():
    """Run the test manually."""
    try:
        test_enum_numbering()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    main()
