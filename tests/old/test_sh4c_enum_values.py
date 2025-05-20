import os
import sys
import pytest
import tempfile
import re

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cpp_generator import StandardCppGenerator
from message_parser_core import MessageParser
from tests.test_utils import randomize_def_file, cleanup_temp_dir

def test_sh4c_enum_values():
    """Test that enum values are preserved correctly in sh4c_comms.def."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

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
        assert not parser.errors, f"Parsing errors: {parser.errors}"

        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as output_dir:
            # Generate standard C++ code
            generator = StandardCppGenerator(model, output_dir)
            result = generator.generate()
            assert result, "Failed to generate C++ code"

            # Find the generated C++ file
            cpp_files = [f for f in os.listdir(output_dir) if f.startswith("c_") and f.endswith("_msgs.h")]
            assert len(cpp_files) > 0, f"No C++ files found in {output_dir}"

            # Get the randomized namespace name
            client_commands = name_mapping.get("ClientCommands", "ClientCommands")

            # Find the file that contains the randomized namespace
            namespace_file = None
            for file_name in cpp_files:
                with open(os.path.join(output_dir, file_name), 'r') as f:
                    content = f.read()
                    if f"namespace {client_commands}" in content:
                        namespace_file = file_name
                        break

            assert namespace_file, f"{client_commands} namespace not found in generated code"

            # Read the file with the namespace
            with open(os.path.join(output_dir, namespace_file), 'r') as f:
                content = f.read()

            # Get the randomized enum and value names
            command = name_mapping.get("Command", "Command")
            status = name_mapping.get("Status", "Status")
            change_mode = name_mapping.get("ChangeMode", "ChangeMode")
            modes_available = name_mapping.get("ModesAvailable", "ModesAvailable")

            # Check that the Command enum includes all values with correct values
            enum_pattern = rf"enum class {command}.*?{{(.*?)}}"
            enum_match = re.search(enum_pattern, content, re.DOTALL)
            assert enum_match, f"{command} enum not found in generated code"

            enum_content = enum_match.group(1)
            print(f"Enum content: {enum_content}")

            # Check that the enum includes the original value from Base::Command.type
            assert f"{status} = 0" in enum_content, f"Original enum value {status} not found in {command} enum"

            # Check that the enum includes the additional values with correct values
            assert f"{change_mode} = 1000" in enum_content, f"Enum value {change_mode} should be 1000 but was not found or had wrong value"
            assert f"{modes_available} = 1001" in enum_content, f"Enum value {modes_available} should be 1001 but was not found or had wrong value"
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)
