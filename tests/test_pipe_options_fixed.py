"""
Test Pipe Options Fixed

This module contains tests for the pipe-separated options syntax with a fixed test file.
"""

import os
import pytest
from message_parser import MessageParser
from message_model import FieldType

def test_pipe_options_parsing_fixed():
    """Test parsing of pipe-separated options with a fixed test file."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_pipe_options_fixed.def")

    # Parse the file
    parser = MessageParser(test_file)
    model = parser.parse()

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

    # Check that the ChangeModeReply message exists
    change_mode_reply = model.get_message("ClientCommands::ChangeModeReply")
    assert change_mode_reply is not None, "ChangeModeReply message not found"

    # Check that ChangeModeReply has the correct parent
    assert change_mode_reply.parent == "BaseReply", f"ChangeModeReply has wrong parent: {change_mode_reply.parent}"

    # Check that the mode field exists and is of type ENUM
    mode_field = next((f for f in change_mode_reply.fields if f.name == "mode"), None)
    assert mode_field is not None, "mode field not found in ChangeModeReply message"
    assert mode_field.field_type == FieldType.ENUM, f"mode field is not of type ENUM, got {mode_field.field_type}"

    # Check that the enum values were correctly parsed
    assert len(mode_field.enum_values) == 3, f"Expected 3 enum values, got {len(mode_field.enum_values)}"
    mode_enum_names = [v.name for v in mode_field.enum_values]
    assert "Live" in mode_enum_names, "Live enum value not found"
    assert "Replay" in mode_enum_names, "Replay enum value not found"
    assert "Editor" in mode_enum_names, "Editor enum value not found"

    # Check that the ModesAvailable message exists
    modes_available = model.get_message("ClientCommands::ModesAvailable")
    assert modes_available is not None, "ModesAvailable message not found"

    # Check that ModesAvailable has the correct parent
    assert modes_available.parent == "BaseCommand", f"ModesAvailable has wrong parent: {modes_available.parent}"

    # Check that ModesAvailable doesn't have any fields (it's an empty message)
    assert len(modes_available.fields) == 0, f"Expected 0 fields, got {len(modes_available.fields)}"

    # Check that the ModesAvailableReply message exists
    message = model.get_message("ClientCommands::ModesAvailableReply")
    assert message is not None, "ModesAvailableReply message not found"

    # Check that ModesAvailableReply has the correct parent
    assert message.parent == "BaseReply", f"ModesAvailableReply has wrong parent: {message.parent}"

    # Check that the available field exists and is of type OPTIONS
    field = next((f for f in message.fields if f.name == "available"), None)
    assert field is not None, "available field not found in ModesAvailableReply message"
    assert field.field_type == FieldType.OPTIONS, f"available field is not of type OPTIONS, got {field.field_type}"

    # Check that the options values were correctly parsed
    assert len(field.enum_values) == 3, f"Expected 3 options values, got {len(field.enum_values)}"
    option_names = [v.name for v in field.enum_values]
    assert "Live" in option_names, "Live option not found"
    assert "Replay" in option_names, "Replay option not found"
    assert "Editor" in option_names, "Editor option not found"
