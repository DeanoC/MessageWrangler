"""
Test New Data Types

This module contains tests for the new data types: Boolean, Byte, and Options.
"""

import os
import pytest
from tempfile import NamedTemporaryFile

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser


@pytest.fixture
def boolean_message_file():
    """Create a file with a message containing a boolean field for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message BooleanMessage {
    field enabled: bool
    field disabled: bool default(false)
    field active: bool default(true)
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def byte_message_file():
    """Create a file with a message containing a byte field for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message ByteMessage {
    field value: byte
    field defaultValue: byte default(42)
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def options_message_file():
    """Create a file with a message containing options fields for testing."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message OptionsMessage {
    field singleOption: options { OptionA, OptionB, OptionC } default(OptionA)
    field combinedOptions: options { OptionX, OptionY, OptionZ } default(OptionX & OptionZ)
    field optionalOptions: options { Option1, Option2, Option3 } optional
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


def test_parse_boolean_field(boolean_message_file):
    """Test parsing a message with boolean fields."""
    parser = MessageParser(boolean_message_file)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message("BooleanMessage")
    assert message is not None
    assert len(message.fields) == 3

    # Check boolean fields
    enabled_field = message.fields[0]
    assert enabled_field.name == "enabled"
    assert enabled_field.field_type == FieldType.BOOLEAN
    assert enabled_field.default_value is None
    assert not enabled_field.optional

    disabled_field = message.fields[1]
    assert disabled_field.name == "disabled"
    assert disabled_field.field_type == FieldType.BOOLEAN
    assert disabled_field.default_value is False
    assert not disabled_field.optional

    active_field = message.fields[2]
    assert active_field.name == "active"
    assert active_field.field_type == FieldType.BOOLEAN
    assert active_field.default_value is True
    assert not active_field.optional


def test_parse_byte_field(byte_message_file):
    """Test parsing a message with byte fields."""
    parser = MessageParser(byte_message_file)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message("ByteMessage")
    assert message is not None
    assert len(message.fields) == 2

    # Check byte fields
    value_field = message.fields[0]
    assert value_field.name == "value"
    assert value_field.field_type == FieldType.BYTE
    assert value_field.default_value is None
    assert not value_field.optional

    default_value_field = message.fields[1]
    assert default_value_field.name == "defaultValue"
    assert default_value_field.field_type == FieldType.BYTE
    assert default_value_field.default_value == 42
    assert not default_value_field.optional


def test_parse_options_field(options_message_file):
    """Test parsing a message with options fields."""
    parser = MessageParser(options_message_file)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message("OptionsMessage")
    assert message is not None
    assert len(message.fields) == 3

    # Check single option field
    single_option_field = message.fields[0]
    assert single_option_field.name == "singleOption"
    assert single_option_field.field_type == FieldType.OPTIONS
    assert single_option_field.default_value_str == "OptionA"
    assert len(single_option_field.enum_values) == 3
    assert single_option_field.enum_values[0].name == "OptionA"
    assert single_option_field.enum_values[0].value == 1  # 2^0
    assert single_option_field.enum_values[1].name == "OptionB"
    assert single_option_field.enum_values[1].value == 2  # 2^1
    assert single_option_field.enum_values[2].name == "OptionC"
    assert single_option_field.enum_values[2].value == 4  # 2^2
    assert not single_option_field.optional

    # Check combined options field
    combined_options_field = message.fields[1]
    assert combined_options_field.name == "combinedOptions"
    assert combined_options_field.field_type == FieldType.OPTIONS
    assert combined_options_field.default_value_str == "OptionX & OptionZ"
    assert combined_options_field.default_value == 5  # 1 (OptionX) | 4 (OptionZ)
    assert len(combined_options_field.enum_values) == 3
    assert combined_options_field.enum_values[0].name == "OptionX"
    assert combined_options_field.enum_values[0].value == 1  # 2^0
    assert combined_options_field.enum_values[1].name == "OptionY"
    assert combined_options_field.enum_values[1].value == 2  # 2^1
    assert combined_options_field.enum_values[2].name == "OptionZ"
    assert combined_options_field.enum_values[2].value == 4  # 2^2
    assert not combined_options_field.optional

    # Check optional options field
    optional_options_field = message.fields[2]
    assert optional_options_field.name == "optionalOptions"
    assert optional_options_field.field_type == FieldType.OPTIONS
    assert optional_options_field.default_value is None
    assert len(optional_options_field.enum_values) == 3
    assert optional_options_field.enum_values[0].name == "Option1"
    assert optional_options_field.enum_values[0].value == 1  # 2^0
    assert optional_options_field.enum_values[1].name == "Option2"
    assert optional_options_field.enum_values[1].value == 2  # 2^1
    assert optional_options_field.enum_values[2].name == "Option3"
    assert optional_options_field.enum_values[2].value == 4  # 2^2
    assert optional_options_field.optional