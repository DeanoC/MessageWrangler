"""
Test Status class in sh4c_comms.def

This module contains tests for the Status class in sh4c_comms.def to ensure
it doesn't have a "Base::" prefix in the generated C++ code.
"""

import os
import sys
import pytest
import tempfile
import shutil

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cpp_generator import StandardCppGenerator
from message_parser_core import MessageParser
from tests.test_utils import randomize_def_file, cleanup_temp_dir


def test_sh4c_status_no_base_prefix():
    """Test that the Status class in sh4c_base_msgs.h doesn't have a Base:: prefix."""
    # Get the paths to the original files
    base_file_path = os.path.join(os.path.dirname(__file__), "sh4c_base.def")
    comms_file_path = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

    # Create a randomized version of the comms file
    temp_dir, random_comms_path, name_mapping = randomize_def_file(comms_file_path)

    try:
        # Get the directory and filename of the random file
        random_file_dir = os.path.dirname(random_comms_path)
        random_file_name = os.path.basename(random_comms_path)

        # Store the original directory
        original_dir = os.getcwd()

        # Change to the directory containing the random file
        os.chdir(random_file_dir)

        # Parse the randomized file
        parser = MessageParser(random_file_name)
        model = parser.parse()

        # Change back to the original directory
        os.chdir(original_dir)

        # Check that the model was created
        assert model is not None, f"Failed to parse {random_file_name}"

        # Create a temporary directory for output
        output_dir = tempfile.mkdtemp()

        try:
            # Generate standard C++ code
            generator = StandardCppGenerator(model, output_dir)
            result = generator.generate()
            assert result, "Failed to generate C++ code"

            # Get the randomized names
            base_namespace = name_mapping.get("Base", "Base")
            status = name_mapping.get("Status", "Status")
            command = name_mapping.get("Command", "Command")
            status_reply = name_mapping.get("StatusReply", "StatusReply")
            reply = name_mapping.get("Reply", "Reply")

            # Find the generated base file
            base_file_pattern = f"c_{base_namespace.lower()}_"
            base_files = [f for f in os.listdir(output_dir) if f.startswith(base_file_pattern) and f.endswith("_msgs.h")]
            assert len(base_files) > 0, f"No base files found in {output_dir} matching pattern {base_file_pattern}"
            base_file = os.path.join(output_dir, base_files[0])

            # Read the base file
            with open(base_file, 'r') as f:
                content = f.read()

            # Check that the Status class is defined correctly
            assert f"struct {status} : public {command}" in content, f"{status} class not found or not inheriting from {command}"
            assert f"struct {status} : public {base_namespace}::{command}" not in content, f"{status} class has incorrect {base_namespace}:: prefix"

            # Check that the StatusReply class is defined correctly
            assert f"struct {status_reply} : public {reply}" in content, f"{status_reply} class not found or not inheriting from {reply}"
            assert f"struct {status_reply} : public {base_namespace}::{reply}" not in content, f"{status_reply} class has incorrect {base_namespace}:: prefix"

            # Note: StandardCppGenerator doesn't generate FromJson methods
            # The issue is only with the struct inheritance declaration, which we've already checked above
        finally:
            # Clean up the output directory
            shutil.rmtree(output_dir)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)
