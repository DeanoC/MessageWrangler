"""
Test Enum Duplicate Values

This script tests that duplicate enum values are detected and reported as errors.
"""

import os
import sys
import pytest
import tempfile

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser

def test_duplicate_enum_values():
    """Test that duplicate enum values are detected and reported as errors."""
    # Create a temporary file with an enum that has duplicate values
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        message TestDuplicateEnumValues {
            field status: enum {
                OK = 0,
                ERROR = 1,
                WARNING = 1  // Duplicate value
            }
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about duplicate enum values
        assert any("Duplicate enum value" in error for error in parser.errors), \
            "No error about duplicate enum values was reported"

    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_duplicate_enum_values_auto_increment():
    """Test that duplicate enum values are detected when using auto-increment."""
    # Create a temporary file with an enum that has duplicate values due to auto-increment
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        message TestDuplicateEnumValuesAutoIncrement {
            field status: enum {
                OK = 0,
                ERROR = 1,
                CRITICAL = 0  // Duplicate value with OK
            }
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about duplicate enum values
        assert any("Duplicate enum value" in error for error in parser.errors), \
            "No error about duplicate enum values was reported"

    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_duplicate_enum_values_extended_enum():
    """Test that duplicate enum values are detected in extended enums."""
    # Create a temporary file with an extended enum that has duplicate values
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        message EnumContainer {
            field status: enum {
                OK = 0,
                ERROR = 1,
                WARNING = 2
            }
        }

        message ExtendedEnumUser {
            field extendedStatus: EnumContainer.status + { CRITICAL = 100, UNKNOWN = 1 }  // UNKNOWN has duplicate value with ERROR
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about duplicate enum values
        assert any("Duplicate enum value" in error for error in parser.errors), \
            "No error about duplicate enum values was reported"

    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def main():
    """Run the tests manually."""
    try:
        test_duplicate_enum_values()
        print("test_duplicate_enum_values passed!")

        test_duplicate_enum_values_auto_increment()
        print("test_duplicate_enum_values_auto_increment passed!")

        test_duplicate_enum_values_extended_enum()
        print("test_duplicate_enum_values_extended_enum passed!")

        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    main()
