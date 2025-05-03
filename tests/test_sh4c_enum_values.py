import os
import sys
import pytest
import tempfile
import re

# Add the parent directory to the path so we can import the message_parser module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cpp_generator import StandardCppGenerator
from message_parser import MessageParser

def test_sh4c_enum_values():
    """Test that enum values are preserved correctly in sh4c_comms.def."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

    # Parse the test file
    parser = MessageParser(test_file, verbose=True)
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

        # Find the file that contains the ClientCommands namespace
        client_commands_file = None
        for file_name in cpp_files:
            with open(os.path.join(temp_dir, file_name), 'r') as f:
                content = f.read()
                if "namespace ClientCommands" in content:
                    client_commands_file = file_name
                    break

        assert client_commands_file, "ClientCommands namespace not found in generated code"

        # Read the file with the ClientCommands namespace
        with open(os.path.join(temp_dir, client_commands_file), 'r') as f:
            content = f.read()

        # Check that the Command enum includes all values with correct values
        enum_pattern = r"enum class Command.*?{(.*?)}"
        enum_match = re.search(enum_pattern, content, re.DOTALL)
        assert enum_match, "Command enum not found in generated code"

        enum_content = enum_match.group(1)
        print(f"Enum content: {enum_content}")

        # Check that the enum includes the original value from Base::Command.type
        assert "Status = 0" in enum_content, "Original enum value Status not found in Command enum"

        # Check that the enum includes the additional values with correct values
        assert "ChangeMode = 1000" in enum_content, "Enum value ChangeMode should be 1000 but was not found or had wrong value"
        assert "ModesAvailable = 1001" in enum_content, "Enum value ModesAvailable should be 1001 but was not found or had wrong value"
