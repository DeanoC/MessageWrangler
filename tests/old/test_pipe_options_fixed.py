"""
Test Pipe Options Fixed

This module contains tests for the pipe-separated options syntax with a randomized test file.
"""

import os
import sys
import pytest
import tempfile
import shutil

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_parser_core import MessageParser
from message_model import FieldType
from tests.test_utils import randomize_def_file, cleanup_temp_dir

def test_pipe_options_parsing_fixed():
    """Test parsing of pipe-separated options with a randomized test file."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_pipe_options_fixed.def")

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

        # Check that there are no errors
        assert not parser.errors, f"Parser errors: {parser.errors}"

        # Print warnings
        if parser.warnings:
            print("Parser warnings:")
            for warning in parser.warnings:
                print(f"  {warning}")

        # Check that the model was created
        assert model is not None

        # Print all messages in the model
        print("Messages in the model:")
        for message_name in model.messages:
            print(f"  {message_name}")

        # Print all namespaces in the model
        print("Namespaces in the model:")
        for namespace_name in model.namespaces:
            print(f"  {namespace_name}")
            for message_name in model.namespaces[namespace_name].messages:
                print(f"    {message_name}")

        # Get the randomized names
        client_commands = name_mapping.get("ClientCommands", "ClientCommands")
        change_mode_reply = name_mapping.get("ChangeModeReply", "ChangeModeReply")
        base_reply = name_mapping.get("BaseReply", "BaseReply")
        mode_field = name_mapping.get("mode", "mode")
        live_value = name_mapping.get("Live", "Live")
        replay_value = name_mapping.get("Replay", "Replay")
        editor_value = name_mapping.get("Editor", "Editor")
        modes_available = name_mapping.get("ModesAvailable", "ModesAvailable")
        base_command = name_mapping.get("BaseCommand", "BaseCommand")
        modes_available_reply = name_mapping.get("ModesAvailableReply", "ModesAvailableReply")
        available_field = name_mapping.get("available", "available")

        # Check that the ChangeModeReply message exists
        change_mode_reply_msg = model.get_message(f"{client_commands}::{change_mode_reply}")
        assert change_mode_reply_msg is not None, f"{change_mode_reply} message not found"

        # Check that ChangeModeReply has the correct parent
        assert change_mode_reply_msg.parent == base_reply, f"{change_mode_reply} has wrong parent: {change_mode_reply_msg.parent}"

        # Check that the mode field exists and is of type ENUM
        mode_field_obj = next((f for f in change_mode_reply_msg.fields if f.name == mode_field), None)
        assert mode_field_obj is not None, f"{mode_field} field not found in {change_mode_reply} message"
        assert mode_field_obj.field_type == FieldType.ENUM, f"{mode_field} field is not of type ENUM, got {mode_field_obj.field_type}"

        # Check that the enum values were correctly parsed
        assert len(mode_field_obj.enum_values) == 3, f"Expected 3 enum values, got {len(mode_field_obj.enum_values)}"
        mode_enum_names = [v.name for v in mode_field_obj.enum_values]
        assert live_value in mode_enum_names, f"{live_value} enum value not found"
        assert replay_value in mode_enum_names, f"{replay_value} enum value not found"
        assert editor_value in mode_enum_names, f"{editor_value} enum value not found"

        # Check that the ModesAvailable message exists
        modes_available_msg = model.get_message(f"{client_commands}::{modes_available}")
        assert modes_available_msg is not None, f"{modes_available} message not found"

        # Check that ModesAvailable has the correct parent
        assert modes_available_msg.parent == base_command, f"{modes_available} has wrong parent: {modes_available_msg.parent}"

        # Check that ModesAvailable doesn't have any fields (it's an empty message)
        assert len(modes_available_msg.fields) == 0, f"Expected 0 fields, got {len(modes_available_msg.fields)}"

        # Check that the ModesAvailableReply message exists
        modes_available_reply_msg = model.get_message(f"{client_commands}::{modes_available_reply}")
        assert modes_available_reply_msg is not None, f"{modes_available_reply} message not found"

        # Check that ModesAvailableReply has the correct parent
        assert modes_available_reply_msg.parent == base_reply, f"{modes_available_reply} has wrong parent: {modes_available_reply_msg.parent}"

        # Check that the available field exists and is of type OPTIONS
        available_field_obj = next((f for f in modes_available_reply_msg.fields if f.name == available_field), None)
        assert available_field_obj is not None, f"{available_field} field not found in {modes_available_reply} message"
        assert available_field_obj.field_type == FieldType.OPTIONS, f"{available_field} field is not of type OPTIONS, got {available_field_obj.field_type}"

        # Check that the options values were correctly parsed
        assert len(available_field_obj.enum_values) == 3, f"Expected 3 options values, got {len(available_field_obj.enum_values)}"
        option_names = [v.name for v in available_field_obj.enum_values]
        assert live_value in option_names, f"{live_value} option not found"
        assert replay_value in option_names, f"{replay_value} option not found"
        assert editor_value in option_names, f"{editor_value} option not found"
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)
