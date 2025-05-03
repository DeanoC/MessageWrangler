import os
import pytest
import tempfile

from message_parser import MessageParser

def test_invalid_enum_reference_field():
    """Test that referencing a non-existent enum field generates an error."""
    # Create a temporary file with an invalid enum reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        message Base::Command {
            field type: enum { Status }
        }

        message CommCommand : Base::Command {
            field typeX: enum Command.Type + enum { ChangeMode }
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid enum reference
        assert any("Message 'Command' referenced by enum reference" in error for error in parser.errors), \
            f"Expected error about non-existent message, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_invalid_enum_reference_field_in_namespace():
    """Test that referencing a non-existent enum field in a namespace generates an error."""
    # Create a temporary file with an invalid enum reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        namespace Base {
            message Command {
                field type: enum { Status }
            }
        }

        message CommCommand : Base::Command {
            field typeX: enum Base::Command.NonExistentField + enum { ChangeMode }
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid enum reference
        assert any("Enum 'NonExistentField' not found in message 'Base::Command'" in error for error in parser.errors), \
            f"Expected error about non-existent enum field, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
