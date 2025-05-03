"""
Test Status class in sh4c_comms.def

This module contains tests for the Status class in sh4c_comms.def to ensure
it doesn't have a "Base::" prefix in the generated C++ code.
"""

import os
import pytest

from cpp_generator import StandardCppGenerator
from message_parser import MessageParser


def test_sh4c_status_no_base_prefix():
    """Test that the Status class in sh4c_base_msgs.h doesn't have a Base:: prefix."""
    # Get the paths to the .def files
    base_file_path = os.path.join(os.path.dirname(__file__), "sh4c_base.def")
    comms_file_path = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

    # Parse the comms file (which imports the base file)
    parser = MessageParser(comms_file_path)
    model = parser.parse()
    assert model is not None, "Failed to parse sh4c_comms.def"

    # Create a temporary directory for output
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate standard C++ code
        generator = StandardCppGenerator(model, temp_dir)
        result = generator.generate()
        assert result, "Failed to generate C++ code"

        # Find the generated base file
        base_file = os.path.join(temp_dir, "c_sh4c_base_msgs.h")
        assert os.path.exists(base_file), f"Generated base file not found: {base_file}"

        # Read the base file
        with open(base_file, 'r') as f:
            content = f.read()

        # Check that the Status class is defined correctly
        assert "struct Status : public Command" in content, "Status class not found or not inheriting from Command"
        assert "struct Status : public Base::Command" not in content, "Status class has incorrect Base:: prefix"

        # Check that the StatusReply class is defined correctly
        assert "struct StatusReply : public Reply" in content, "StatusReply class not found or not inheriting from Reply"
        assert "struct StatusReply : public Base::Reply" not in content, "StatusReply class has incorrect Base:: prefix"

        # Note: StandardCppGenerator doesn't generate FromJson methods
        # The issue is only with the struct inheritance declaration, which we've already checked above
