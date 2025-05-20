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
from message_parser_core import MessageParser
from tests.test_utils import generate_random_name

def test_duplicate_enum_values():
    """Test that duplicate enum values are detected and reported as errors."""
    # Generate random names
    message_name = f"TestDuplicateEnumValues_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"
    ok_value = f"RANDOM_OK_{generate_random_name()}"
    error_value = f"RANDOM_ERROR_{generate_random_name()}"
    warning_value = f"RANDOM_WARNING_{generate_random_name()}"

    # Create a temporary file with an enum that has duplicate values
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        message {message_name} {{
            field {status_field}: enum {{
                {ok_value} = 0,
                {error_value} = 1,
                {warning_value} = 1  // Duplicate value
            }}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about duplicate enum values
        assert any("Duplicate enum value" in error for error in parser.errors), \
            "No error about duplicate enum values was reported"
        # Additionally, check that the model is None because of the error
        assert model is None, "Model should be None when parsing fails due to duplicate enum values"

    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_duplicate_enum_values_auto_increment():
    """Test that duplicate enum values are detected when using auto-increment."""
    # Generate random names
    message_name = f"TestDuplicateEnumValuesAutoIncrement_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"
    ok_value = f"RANDOM_OK_{generate_random_name()}"
    error_value = f"RANDOM_ERROR_{generate_random_name()}"
    critical_value = f"RANDOM_CRITICAL_{generate_random_name()}"

    # Create a temporary file with an enum that has duplicate values due to auto-increment
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        message {message_name} {{
            field {status_field}: enum {{
                {ok_value} = 0,
                {error_value} = 1,
                {critical_value} = 0  // Duplicate value with {ok_value}
            }}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()


        # Check that there is an error about duplicate enum values
        assert any("Duplicate enum value" in error for error in parser.errors), \
            "No error about duplicate enum values was reported"
        # Additionally, check that the model is None because of the error
        assert model is None, "Model should be None when parsing fails due to duplicate enum values"

    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_duplicate_enum_values_extended_enum():
    """Test that duplicate enum values are detected in extended enums."""
    # Generate random names
    enum_container = f"RandomContainer_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"
    ok_value = f"RANDOM_OK_{generate_random_name()}"
    error_value = f"RANDOM_ERROR_{generate_random_name()}"
    warning_value = f"RANDOM_WARNING_{generate_random_name()}"
    extended_enum_user = f"RandomExtendedUser_{generate_random_name()}"
    extended_status = f"randomExtendedStatus_{generate_random_name()}"
    critical_value = f"RANDOM_CRITICAL_{generate_random_name()}"
    unknown_value = f"RANDOM_UNKNOWN_{generate_random_name()}"

    # Create a temporary file with an extended enum that has duplicate values
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        message {enum_container} {{
            field {status_field}: enum {{
                {ok_value} = 0,
                {error_value} = 1,
                {warning_value} = 2
            }}
        }}

        message {extended_enum_user} {{
            field {extended_status}: {enum_container}.{status_field} + {{ {critical_value} = 100, {unknown_value} = 1 }}  // {unknown_value} has duplicate value with {error_value}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        print(f"DEBUG: Errors after parsing: {parser.errors}") # Add this line

         # Check that there is an error about duplicate enum values
        expected_error_substring = f"Duplicate enum value '1' in inline enum for field '{extended_status}'"
        assert any(expected_error_substring in error for error in parser.errors), \
            f"Expected error '{expected_error_substring}' not found in parser errors: {parser.errors}"
        # Additionally, check that the model is None because of the error
        assert model is None, "Model should be None when parsing fails due to duplicate enum values"

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
