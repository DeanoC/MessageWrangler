import pytest
import os
import sys
from tempfile import TemporaryDirectory

# Add the parent directory to sys.path to allow importing from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_model import FieldType, EnumValue, Field, Message, MessageModel

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with TemporaryDirectory() as dir_path:
        yield dir_path

@pytest.fixture
def test_model():
    """Create a test message model with various message types and fields."""
    model = MessageModel()

    # Create a simple message
    simple_message = Message(
        name="SimpleMessage",
        description="A simple message"
    )

    # Add fields to the simple message
    simple_message.fields.append(
        Field(
            name="stringField",
            field_type=FieldType.STRING,
            description="A string field"
        )
    )

    simple_message.fields.append(
        Field(
            name="intField",
            field_type=FieldType.INT,
            description="An int field"
        )
    )

    simple_message.fields.append(
        Field(
            name="floatField",
            field_type=FieldType.FLOAT,
            description="A float field"
        )
    )

    # Add boolean field
    simple_message.fields.append(
        Field(
            name="boolField",
            field_type=FieldType.BOOLEAN,
            description="A boolean field",
            default_value=True
        )
    )

    # Add byte field
    simple_message.fields.append(
        Field(
            name="byteField",
            field_type=FieldType.BYTE,
            description="A byte field",
            default_value=42
        )
    )

    # Create an enum field
    enum_field = Field(
        name="status",
        field_type=FieldType.ENUM,
        description="A status enum"
    )
    enum_field.enum_values = [
        EnumValue(name="OK", value=0),
        EnumValue(name="ERROR", value=1),
        EnumValue(name="PENDING", value=2)
    ]
    simple_message.fields.append(enum_field)

    # Create a compound field
    compound_field = Field(
        name="position",
        field_type=FieldType.COMPOUND,
        description="A position field"
    )
    compound_field.compound_base_type = "float"
    compound_field.compound_components = ["x", "y", "z"]
    simple_message.fields.append(compound_field)

    # Add the simple message to the model
    model.add_message(simple_message)

    # Create a base message
    base_message = Message(
        name="BaseMessage",
        description="A base message"
    )
    base_message.fields.append(
        Field(
            name="baseField",
            field_type=FieldType.STRING,
            description="A base field"
        )
    )
    model.add_message(base_message)

    # Create a derived message
    derived_message = Message(
        name="DerivedMessage",
        parent="BaseMessage",
        description="A derived message"
    )
    derived_message.fields.append(
        Field(
            name="derivedField",
            field_type=FieldType.INT,
            description="A derived field"
        )
    )
    model.add_message(derived_message)

    # Create a message with options fields
    options_message = Message(
        name="OptionsMessage",
        description="A message with options fields"
    )

    # Add single option field
    single_option_field = Field(
        name="singleOption",
        field_type=FieldType.OPTIONS,
        description="A single option field",
        default_value=1  # OptionA
    )
    single_option_field.default_value_str = "OptionA"
    single_option_field.enum_values = [
        EnumValue(name="OptionA", value=1),
        EnumValue(name="OptionB", value=2),
        EnumValue(name="OptionC", value=4)
    ]
    options_message.fields.append(single_option_field)

    # Add combined options field
    combined_options_field = Field(
        name="combinedOptions",
        field_type=FieldType.OPTIONS,
        description="A combined options field",
        default_value=5  # OptionX | OptionZ
    )
    combined_options_field.default_value_str = "OptionX & OptionZ"
    combined_options_field.enum_values = [
        EnumValue(name="OptionX", value=1),
        EnumValue(name="OptionY", value=2),
        EnumValue(name="OptionZ", value=4)
    ]
    options_message.fields.append(combined_options_field)

    # Add optional options field
    optional_options_field = Field(
        name="optionalOptions",
        field_type=FieldType.OPTIONS,
        description="An optional options field",
        optional=True
    )
    optional_options_field.enum_values = [
        EnumValue(name="Option1", value=1),
        EnumValue(name="Option2", value=2),
        EnumValue(name="Option3", value=4)
    ]
    options_message.fields.append(optional_options_field)

    model.add_message(options_message)

    return model
