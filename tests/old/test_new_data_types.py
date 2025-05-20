"""
Test New Data Types

This module contains tests for the new data types: Boolean, Byte, and Options.
It uses randomized names to ensure the tests aren't passing due to hardcoded special cases.
"""

import os
import pytest
from tempfile import NamedTemporaryFile

from message_model import FieldType, Message, MessageModel
from message_parser_core import MessageParser
from tests.test_utils import generate_random_name


@pytest.fixture
def boolean_message_file():
    """Create a file with a message containing a boolean field for testing."""
    # Generate random names
    message_name = f"RandomBoolean_{generate_random_name()}"
    enabled_field = f"randomEnabled_{generate_random_name()}"
    disabled_field = f"randomDisabled_{generate_random_name()}"
    active_field = f"randomActive_{generate_random_name()}"

    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(f"""
message {message_name} {{
    field {enabled_field}: bool
    field {disabled_field}: bool default(false)
    field {active_field}: bool default(true)
}}
        """)
        temp_file = f.name

    # Return both the file path and the name mapping
    yield temp_file, {
        "message_name": message_name,
        "enabled_field": enabled_field,
        "disabled_field": disabled_field,
        "active_field": active_field
    }
    os.unlink(temp_file)


@pytest.fixture
def byte_message_file():
    """Create a file with a message containing a byte field for testing."""
    # Generate random names
    message_name = f"RandomByte_{generate_random_name()}"
    value_field = f"randomValue_{generate_random_name()}"
    default_value_field = f"randomDefaultValue_{generate_random_name()}"

    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(f"""
message {message_name} {{
    field {value_field}: byte
    field {default_value_field}: byte default(42)
}}
        """)
        temp_file = f.name

    # Return both the file path and the name mapping
    yield temp_file, {
        "message_name": message_name,
        "value_field": value_field,
        "default_value_field": default_value_field
    }
    os.unlink(temp_file)


@pytest.fixture
def options_message_file():
    """Create a file with a message containing options fields for testing."""
    # Generate random names
    message_name = f"RandomOptions_{generate_random_name()}"
    single_option_field = f"randomSingleOption_{generate_random_name()}"
    combined_options_field = f"randomCombinedOptions_{generate_random_name()}"
    optional_options_field = f"randomOptionalOptions_{generate_random_name()}"

    option_a = f"RANDOM_OPTION_A_{generate_random_name()}"
    option_b = f"RANDOM_OPTION_B_{generate_random_name()}"
    option_c = f"RANDOM_OPTION_C_{generate_random_name()}"

    option_x = f"RANDOM_OPTION_X_{generate_random_name()}"
    option_y = f"RANDOM_OPTION_Y_{generate_random_name()}"
    option_z = f"RANDOM_OPTION_Z_{generate_random_name()}"

    option_1 = f"RANDOM_OPTION_1_{generate_random_name()}"
    option_2 = f"RANDOM_OPTION_2_{generate_random_name()}"
    option_3 = f"RANDOM_OPTION_3_{generate_random_name()}"

    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(f"""
message {message_name} {{
    field {single_option_field}: options {{ {option_a}, {option_b}, {option_c} }} default({option_a})
    field {combined_options_field}: options {{ {option_x}, {option_y}, {option_z} }} default({option_x} & {option_z})
    field {optional_options_field}: options {{ {option_1}, {option_2}, {option_3} }} optional
}}
        """)
        temp_file = f.name

    # Return both the file path and the name mapping
    yield temp_file, {
        "message_name": message_name,
        "single_option_field": single_option_field,
        "combined_options_field": combined_options_field,
        "optional_options_field": optional_options_field,
        "option_a": option_a,
        "option_b": option_b,
        "option_c": option_c,
        "option_x": option_x,
        "option_y": option_y,
        "option_z": option_z,
        "option_1": option_1,
        "option_2": option_2,
        "option_3": option_3
    }
    os.unlink(temp_file)


def test_parse_boolean_field(boolean_message_file):
    """Test parsing a message with boolean fields."""
    # Unpack the file path and name mapping
    file_path, names = boolean_message_file

    parser = MessageParser(file_path)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message(names["message_name"])
    assert message is not None
    assert len(message.fields) == 3

    # Check boolean fields
    enabled_field = message.fields[0]
    assert enabled_field.name == names["enabled_field"]
    assert enabled_field.field_type == FieldType.BOOLEAN
    assert enabled_field.default_value is None
    assert not enabled_field.optional

    disabled_field = message.fields[1]
    assert disabled_field.name == names["disabled_field"]
    assert disabled_field.field_type == FieldType.BOOLEAN
    assert disabled_field.default_value is False
    assert not disabled_field.optional

    active_field = message.fields[2]
    assert active_field.name == names["active_field"]
    assert active_field.field_type == FieldType.BOOLEAN
    assert active_field.default_value is True
    assert not active_field.optional


def test_parse_byte_field(byte_message_file):
    """Test parsing a message with byte fields."""
    # Unpack the file path and name mapping
    file_path, names = byte_message_file

    parser = MessageParser(file_path)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message(names["message_name"])
    assert message is not None
    assert len(message.fields) == 2

    # Check byte fields
    value_field = message.fields[0]
    assert value_field.name == names["value_field"]
    assert value_field.field_type == FieldType.BYTE
    assert value_field.default_value is None
    assert not value_field.optional

    default_value_field = message.fields[1]
    assert default_value_field.name == names["default_value_field"]
    assert default_value_field.field_type == FieldType.BYTE
    assert default_value_field.default_value == 42
    assert not default_value_field.optional


def test_parse_options_field(options_message_file):
    """Test parsing a message with options fields."""
    # Unpack the file path and name mapping
    file_path, names = options_message_file

    parser = MessageParser(file_path)
    model = parser.parse()
    assert model is not None

    # Check message
    message = model.get_message(names["message_name"])
    assert message is not None
    assert len(message.fields) == 3

    # Check single option field
    single_option_field = message.fields[0]
    assert single_option_field.name == names["single_option_field"]
    assert single_option_field.field_type == FieldType.OPTIONS
    assert single_option_field.default_value_str == names["option_a"]
    assert len(single_option_field.enum_values) == 3
    assert single_option_field.enum_values[0].name == names["option_a"]
    assert single_option_field.enum_values[0].value == 1  # 2^0
    assert single_option_field.enum_values[1].name == names["option_b"]
    assert single_option_field.enum_values[1].value == 2  # 2^1
    assert single_option_field.enum_values[2].name == names["option_c"]
    assert single_option_field.enum_values[2].value == 4  # 2^2
    assert not single_option_field.optional

    # Check combined options field
    combined_options_field = message.fields[1]
    assert combined_options_field.name == names["combined_options_field"]
    assert combined_options_field.field_type == FieldType.OPTIONS
    assert combined_options_field.default_value_str == f"{names['option_x']} & {names['option_z']}"
    assert combined_options_field.default_value == 5  # 1 (option_x) | 4 (option_z)
    assert len(combined_options_field.enum_values) == 3
    assert combined_options_field.enum_values[0].name == names["option_x"]
    assert combined_options_field.enum_values[0].value == 1  # 2^0
    assert combined_options_field.enum_values[1].name == names["option_y"]
    assert combined_options_field.enum_values[1].value == 2  # 2^1
    assert combined_options_field.enum_values[2].name == names["option_z"]
    assert combined_options_field.enum_values[2].value == 4  # 2^2
    assert not combined_options_field.optional

    # Check optional options field
    optional_options_field = message.fields[2]
    assert optional_options_field.name == names["optional_options_field"]
    assert optional_options_field.field_type == FieldType.OPTIONS
    assert optional_options_field.default_value is None
    assert len(optional_options_field.enum_values) == 3
    assert optional_options_field.enum_values[0].name == names["option_1"]
    assert optional_options_field.enum_values[0].value == 1  # 2^0
    assert optional_options_field.enum_values[1].name == names["option_2"]
    assert optional_options_field.enum_values[1].value == 2  # 2^1
    assert optional_options_field.enum_values[2].name == names["option_3"]
    assert optional_options_field.enum_values[2].value == 4  # 2^2
    assert optional_options_field.optional
