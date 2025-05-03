import os
import pytest
import tempfile
import re

from cpp_generator import UnrealCppGenerator, StandardCppGenerator
from message_parser import MessageParser


def test_extended_enum_cpp():
    """Test that extended enum references include the original enum values in C++ code."""
    # Create a temporary file with an extended enum reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        // Define a message with an enum
        message EnumContainer {
            field status: enum { OK = 0, ERROR = 1, WARNING = 2 }
        }

        // Define a message that references the enum and adds additional values
        message ExtendedEnumUser {
            field extendedStatus: EnumContainer.status + { CRITICAL = 100, UNKNOWN = 101 }
        }
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

            # Check that the ExtendedEnumUser_extendedStatus_Enum enum includes all values
            enum_pattern = r"enum class ExtendedEnumUser_extendedStatus_Enum.*?{(.*?)}"
            enum_match = re.search(enum_pattern, content, re.DOTALL)
            assert enum_match, "ExtendedEnumUser_extendedStatus_Enum not found in generated code"

            enum_content = enum_match.group(1)
            print(f"Enum content: {enum_content}")

            # Check that the enum includes the original values
            assert "OK = 0" in enum_content, "Original enum value OK not found in extended enum"
            assert "ERROR = 1" in enum_content, "Original enum value ERROR not found in extended enum"
            assert "WARNING = 2" in enum_content, "Original enum value WARNING not found in extended enum"

            # Check that the enum includes the additional values
            assert "CRITICAL = 100" in enum_content, "Additional enum value CRITICAL not found in extended enum"
            assert "UNKNOWN = 101" in enum_content, "Additional enum value UNKNOWN not found in extended enum"

    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
