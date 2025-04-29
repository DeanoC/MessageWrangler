"""
Test empty message TypeScript generation

This module tests that empty messages that inherit from a parent are generated correctly
and don't trigger ESLint warnings.
"""

import os
import pytest
from message_model import Message, MessageModel, Field, FieldType
from typescript_generator import TypeScriptGenerator

def test_empty_message_generation(temp_dir):
    """Test generating TypeScript code for an empty message that inherits from a parent."""
    # Create a simple model with a parent message and an empty child message
    model = MessageModel()

    # Add a parent message
    parent_message = Message("BaseCommand")
    # Create a string field and add it to the parent message
    type_field = Field("type", FieldType.STRING, "The type of command")
    parent_message.fields.append(type_field)
    model.add_message(parent_message)

    # Add an empty child message that inherits from the parent
    child_message = Message("Status")
    child_message.parent = "BaseCommand"
    model.add_message(child_message)

    # Generate TypeScript code
    generator = TypeScriptGenerator(model, temp_dir, "test_empty_message")
    result = generator.generate()
    assert result

    # Check that the output file exists
    output_file = os.path.join(temp_dir, "test_empty_message_msgs.ts")
    assert os.path.exists(output_file)

    # Read the output file
    with open(output_file, 'r') as f:
        content = f.read()

    # Check that the content contains the expected elements
    assert "export interface BaseCommand" in content

    # Check that the empty message is defined as a type alias instead of an interface
    assert "export type Status = BaseCommand;" in content

    # Make sure the old interface syntax is not used
    assert "export interface Status extends BaseCommand" not in content
