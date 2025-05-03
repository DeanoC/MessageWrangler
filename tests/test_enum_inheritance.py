import os
import pytest
import tempfile
import re

from cpp_generator import StandardCppGenerator
from message_parser import MessageParser

def test_enum_inheritance():
    """Test that extended enum references include the original enum values in C++ code."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_enum_inheritance.def")

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

        # Check that the CommCommand_typeX_Enum enum includes all values
        enum_pattern = r"enum class CommCommand_typeX_Enum.*?{(.*?)}"
        enum_match = re.search(enum_pattern, content, re.DOTALL)
        assert enum_match, "CommCommand_typeX_Enum not found in generated code"

        enum_content = enum_match.group(1)
        print(f"Enum content: {enum_content}")

        # Check that the enum includes the original value from Base::Command.type
        assert "Status = 0" in enum_content, "Original enum value Status not found in extended enum"

        # Check that the enum includes the additional value
        assert "ChangeMode" in enum_content, "Additional enum value ChangeMode not found in extended enum"