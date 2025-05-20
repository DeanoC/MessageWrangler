"""
Test script to verify that existing functionality still works.
It uses randomized names to ensure the tests aren't passing due to hardcoded special cases.
"""

import os
import pytest
from message_parser_core import MessageParser
from tests.test_utils import randomize_def_file, cleanup_temp_dir


def test_parse_messages_def():
    """Test parsing of test_messages.def file with randomized names."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_messages.def")

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
        parser = MessageParser(random_file_name)
        model = parser.parse()

        # Change back to the original directory
        os.chdir(original_dir)

        # Check that the model was created successfully
        assert model is not None, f"Failed to parse {random_file_name}"
        assert len(model.messages) > 0, f"No messages were parsed from {random_file_name}"
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)


def test_parse_namespaces_def():
    """Test parsing of test_namespaces.def file with randomized names."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_namespaces.def")

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
        parser = MessageParser(random_file_name)
        model = parser.parse()

        # Change back to the original directory
        os.chdir(original_dir)

        # Check that the model was created successfully
        assert model is not None, f"Failed to parse {random_file_name}"
        assert len(model.messages) > 0, f"No messages were parsed from {random_file_name}"
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)
