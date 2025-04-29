"""
Test Message Parser

This module contains tests for the message parser.
"""

import os
import pytest
from tempfile import NamedTemporaryFile

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser


@pytest.fixture
def empty_file():
    """Create an empty file for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("")
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def simple_message_file():
    """Create a file with a simple message for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message SimpleMessage {
    field stringField: string
    field intField: int
    field floatField: float
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def enum_message_file():
    """Create a file with a message containing an enum field for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message EnumMessage {
    field status: enum { OK, ERROR, PENDING }
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def compound_message_file():
    """Create a file with a message containing a compound field for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message CompoundMessage {
    field position: float { x, y, z }
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def inheritance_message_file():
    """Create a file with messages demonstrating inheritance for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message BaseMessage {
    field baseField: string
}

message DerivedMessage : BaseMessage {
    field derivedField: int
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def default_values_message_file():
    """Create a file with a message containing fields with default values for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message DefaultValuesMessage {
    field stringField: string default("hello")
    field intField: int default(42)
    field floatField: float default(3.14)
    field enumField: enum { RED, GREEN, BLUE } default(GREEN)
    field optionalWithDefault: string optional default("optional with default")
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


def test_parse_empty_file(empty_file):
    """Test parsing an empty file."""
    parser = MessageParser(empty_file)
    model = parser.parse()
    assert model is not None
    assert len(model.messages) == 0


def test_parse_simple_message(simple_message_file):
    """Test parsing a simple message with basic fields."""
    parser = MessageParser(simple_message_file)
    model = parser.parse()
    assert model is not None
    assert len(model.messages) == 1

    # Check message
    message = model.get_message("SimpleMessage")
    assert message is not None
    assert message.name == "SimpleMessage"
    assert message.parent is None
    assert len(message.fields) == 3

    # Check fields
    assert message.fields[0].name == "stringField"
    assert message.fields[0].field_type == FieldType.STRING

    assert message.fields[1].name == "intField"
    assert message.fields[1].field_type == FieldType.INT

    assert message.fields[2].name == "floatField"
    assert message.fields[2].field_type == FieldType.FLOAT


def test_parse_enum_field(enum_message_file):
    """Test parsing a message with an enum field."""
    parser = MessageParser(enum_message_file)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message("EnumMessage")
    assert message is not None
    assert len(message.fields) == 1

    # Check enum field
    field = message.fields[0]
    assert field.name == "status"
    assert field.field_type == FieldType.ENUM
    assert len(field.enum_values) == 3

    # Check enum values
    assert field.enum_values[0].name == "OK"
    assert field.enum_values[0].value == 0

    assert field.enum_values[1].name == "ERROR"
    assert field.enum_values[1].value == 1

    assert field.enum_values[2].name == "PENDING"
    assert field.enum_values[2].value == 2


def test_parse_compound_field(compound_message_file):
    """Test parsing a message with a compound field."""
    parser = MessageParser(compound_message_file)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message("CompoundMessage")
    assert message is not None
    assert len(message.fields) == 1

    # Check compound field
    field = message.fields[0]
    assert field.name == "position"
    assert field.field_type == FieldType.COMPOUND
    assert field.compound_base_type == "float"
    assert len(field.compound_components) == 3
    assert field.compound_components == ["x", "y", "z"]


def test_parse_inheritance(inheritance_message_file):
    """Test parsing messages with inheritance."""
    parser = MessageParser(inheritance_message_file)
    model = parser.parse()
    assert model is not None
    assert len(model.messages) == 2

    # Check base message
    base_message = model.get_message("BaseMessage")
    assert base_message is not None
    assert base_message.parent is None
    assert len(base_message.fields) == 1
    assert base_message.fields[0].name == "baseField"

    # Check derived message
    derived_message = model.get_message("DerivedMessage")
    assert derived_message is not None
    assert derived_message.parent == "BaseMessage"
    assert len(derived_message.fields) == 1
    assert derived_message.fields[0].name == "derivedField"


def test_parse_default_values(default_values_message_file):
    """Test parsing a message with fields that have default values."""
    parser = MessageParser(default_values_message_file)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message("DefaultValuesMessage")
    assert message is not None
    assert len(message.fields) == 5

    # Check string field with default value
    string_field = message.fields[0]
    assert string_field.name == "stringField"
    assert string_field.field_type == FieldType.STRING
    assert string_field.default_value == "hello"
    assert not string_field.optional

    # Check int field with default value
    int_field = message.fields[1]
    assert int_field.name == "intField"
    assert int_field.field_type == FieldType.INT
    assert int_field.default_value == 42
    assert not int_field.optional

    # Check float field with default value
    float_field = message.fields[2]
    assert float_field.name == "floatField"
    assert float_field.field_type == FieldType.FLOAT
    assert float_field.default_value == 3.14
    assert not float_field.optional

    # Check enum field with default value
    enum_field = message.fields[3]
    assert enum_field.name == "enumField"
    assert enum_field.field_type == FieldType.ENUM
    assert enum_field.default_value == "GREEN"
    assert not enum_field.optional
    assert len(enum_field.enum_values) == 3
    assert enum_field.enum_values[0].name == "RED"
    assert enum_field.enum_values[1].name == "GREEN"
    assert enum_field.enum_values[2].name == "BLUE"

    # Check optional field with default value
    optional_field = message.fields[4]
    assert optional_field.name == "optionalWithDefault"
    assert optional_field.field_type == FieldType.STRING
    assert optional_field.default_value is None  # Default values for optional fields are ignored
    assert optional_field.optional
