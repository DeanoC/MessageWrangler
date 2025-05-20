import os
import sys
import pytest
import tempfile
import re

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cpp_generator import UnrealCppGenerator, StandardCppGenerator
from message_parser_core import MessageParser
from tests.test_utils import generate_random_name


def test_extended_enum_cpp():
    """Test that extended enum references include the original enum values in C++ code."""
    # Generate random names for messages, fields, and enum values
    enum_container = f"RandomContainer_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"
    ok_value = f"RANDOM_OK_{generate_random_name()}"
    error_value = f"RANDOM_ERROR_{generate_random_name()}"
    warning_value = f"RANDOM_WARNING_{generate_random_name()}"
    extended_enum_user = f"RandomExtendedUser_{generate_random_name()}"
    extended_status = f"randomExtendedStatus_{generate_random_name()}"
    critical_value = f"RANDOM_CRITICAL_{generate_random_name()}"
    unknown_value = f"RANDOM_UNKNOWN_{generate_random_name()}"

    # Create a temporary file with an extended enum reference using random names
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        // Define a message with an enum
        message {enum_container} {{
            field {status_field}: enum {{ {ok_value} = 0, {error_value} = 1, {warning_value} = 2 }}
        }}

        // Define a message that references the enum and adds additional values
        message {extended_enum_user} {{
            field {extended_status}: {enum_container}.{status_field} + {{ {critical_value} = 100, {unknown_value} = 101 }}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there are no errors
        assert not parser.errors, f"Parsing errors: {parser.errors}"

        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate standard C++ code
            generator = StandardCppGenerator(model, temp_dir)
            result = generator.generate()
            assert result, "Failed to generate C++ code"

            # Find the generated C++ file
            cpp_files = [f for f in os.listdir(temp_dir) if f.startswith("c_") and f.endswith("_msgs.h")]
            assert len(cpp_files) > 0, f"No C++ files found in {temp_dir}"
            output_file = os.path.join(temp_dir, cpp_files[0])

            # Read the output file
            with open(output_file, 'r') as f:
                content = f.read()

            # Check that the extended enum includes all values
            enum_pattern = rf"enum class {extended_enum_user}_{extended_status}_Enum.*?{{(.*?)}}"
            enum_match = re.search(enum_pattern, content, re.DOTALL)
            assert enum_match, f"{extended_enum_user}_{extended_status}_Enum not found in generated code"

            enum_content = enum_match.group(1)
            print(f"Enum content: {enum_content}")

            # Check that the enum includes the original values
            assert f"{ok_value} = 0" in enum_content, f"Original enum value {ok_value} not found in extended enum"
            assert f"{error_value} = 1" in enum_content, f"Original enum value {error_value} not found in extended enum"
            assert f"{warning_value} = 2" in enum_content, f"Original enum value {warning_value} not found in extended enum"

            # Check that the enum includes the additional values
            assert f"{critical_value} = 100" in enum_content, f"Additional enum value {critical_value} not found in extended enum"
            assert f"{unknown_value} = 101" in enum_content, f"Additional enum value {unknown_value} not found in extended enum"

    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
