import os
import pytest
from message_parser import MessageParser
from message_model import FieldType

def test_enum_references():
    """Test parsing and validation of enum references."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_enum_references.def")

    # Parse the test file
    parser = MessageParser(test_file, verbose=True)
    model = parser.parse()

    # Check that there are no errors
    assert not parser.errors, f"Parsing errors: {parser.errors}"

    # Check that the model was created
    assert model is not None, "Model is None"

    # Check that all messages were parsed
    assert "EnumContainer" in model.messages
    assert "EnumUser" in model.messages
    assert "Test::NamespacedEnum" in model.messages
    assert "NamespacedEnumUser" in model.messages
    assert "MultipleEnums" in model.messages
    assert "MultipleEnumUser" in model.messages

    # Check that enum references were resolved correctly

    # Check EnumUser.containerStatus
    enum_user = model.messages["EnumUser"]
    assert len(enum_user.fields) == 1
    container_status = enum_user.fields[0]
    assert container_status.name == "containerStatus"
    assert container_status.field_type == FieldType.ENUM
    assert container_status.enum_reference == "EnumContainer.status"

    # Check that the enum values were copied from EnumContainer.status
    enum_container = model.messages["EnumContainer"]
    status_field = enum_container.fields[0]
    assert status_field.name == "status"
    assert status_field.field_type == FieldType.ENUM

    # Compare enum values
    assert len(container_status.enum_values) == len(status_field.enum_values)
    for i, enum_value in enumerate(status_field.enum_values):
        assert container_status.enum_values[i].name == enum_value.name
        assert container_status.enum_values[i].value == enum_value.value

    # Check NamespacedEnumUser.testLevel
    namespaced_enum_user = model.messages["NamespacedEnumUser"]
    assert len(namespaced_enum_user.fields) == 1
    test_level = namespaced_enum_user.fields[0]
    assert test_level.name == "testLevel"
    assert test_level.field_type == FieldType.ENUM
    assert test_level.enum_reference == "Test::NamespacedEnum.level"

    # Check that the enum values were copied from Test::NamespacedEnum.level
    namespaced_enum = model.messages["Test::NamespacedEnum"]
    level_field = namespaced_enum.fields[0]
    assert level_field.name == "level"
    assert level_field.field_type == FieldType.ENUM

    # Compare enum values
    assert len(test_level.enum_values) == len(level_field.enum_values)
    for i, enum_value in enumerate(level_field.enum_values):
        assert test_level.enum_values[i].name == enum_value.name
        assert test_level.enum_values[i].value == enum_value.value

    # Check MultipleEnumUser.multiType and MultipleEnumUser.multiState
    multiple_enum_user = model.messages["MultipleEnumUser"]
    assert len(multiple_enum_user.fields) == 2

    multi_type = multiple_enum_user.fields[0]
    assert multi_type.name == "multiType"
    assert multi_type.field_type == FieldType.ENUM
    assert multi_type.enum_reference == "MultipleEnums.type"

    multi_state = multiple_enum_user.fields[1]
    assert multi_state.name == "multiState"
    assert multi_state.field_type == FieldType.ENUM
    assert multi_state.enum_reference == "MultipleEnums.state"

    # Check that the enum values were copied from MultipleEnums.type and MultipleEnums.state
    multiple_enums = model.messages["MultipleEnums"]
    type_field = multiple_enums.fields[0]
    state_field = multiple_enums.fields[1]

    # Compare enum values for type
    assert len(multi_type.enum_values) == len(type_field.enum_values)
    for i, enum_value in enumerate(type_field.enum_values):
        assert multi_type.enum_values[i].name == enum_value.name
        assert multi_type.enum_values[i].value == enum_value.value

    # Compare enum values for state
    assert len(multi_state.enum_values) == len(state_field.enum_values)
    for i, enum_value in enumerate(state_field.enum_values):
        assert multi_state.enum_values[i].name == enum_value.name
        assert multi_state.enum_values[i].value == enum_value.value

def test_invalid_enum_reference():
    """Test that invalid enum references are detected."""
    # Create a temporary file with an invalid enum reference
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        message EnumContainer {
            field status: enum { OK = 0, ERROR = 1 }
        }

        message InvalidEnumUser {
            field invalidStatus: EnumContainer.nonexistent
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid enum reference
        assert any("Enum 'nonexistent' not found in message 'EnumContainer'" in error for error in parser.errors), \
            f"Expected error about nonexistent enum, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_invalid_message_reference():
    """Test that invalid message references in enum references are detected."""
    # Create a temporary file with an invalid message reference
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        message InvalidEnumUser {
            field invalidStatus: NonexistentMessage.status
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid message reference
        assert any("Message 'NonexistentMessage' referenced by enum reference 'NonexistentMessage.status'" in error for error in parser.errors), \
            f"Expected error about nonexistent message, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_extended_enum_references():
    """Test parsing and validation of extended enum references."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_enum_references.def")

    # Parse the test file
    parser = MessageParser(test_file, verbose=True)
    model = parser.parse()

    # Check that there are no errors
    assert not parser.errors, f"Parsing errors: {parser.errors}"

    # Check that the model was created
    assert model is not None, "Model is None"

    # Check that all messages were parsed
    assert "ExtendedEnumUser" in model.messages
    assert "ExtendedNamespacedEnumUser" in model.messages
    assert "ExtendedMultipleEnumUser" in model.messages

    # Check ExtendedEnumUser.extendedStatus
    extended_enum_user = model.messages["ExtendedEnumUser"]
    assert len(extended_enum_user.fields) == 1
    extended_status = extended_enum_user.fields[0]
    assert extended_status.name == "extendedStatus"
    assert extended_status.field_type == FieldType.ENUM
    assert extended_status.enum_reference == "EnumContainer.status"

    # Check that the enum values were copied from EnumContainer.status and additional values were added
    enum_container = model.messages["EnumContainer"]
    status_field = enum_container.fields[0]

    # The extended enum should have all the values from the original enum plus the additional values
    assert len(extended_status.enum_values) == len(status_field.enum_values) + 2

    # Check that the original enum values are present
    original_enum_values = {ev.name: ev.value for ev in status_field.enum_values}
    for name, value in original_enum_values.items():
        assert any(ev.name == name and ev.value == value for ev in extended_status.enum_values)

    # Check that the additional enum values are present
    assert any(ev.name == "CRITICAL" and ev.value == 100 for ev in extended_status.enum_values)
    assert any(ev.name == "UNKNOWN" and ev.value == 101 for ev in extended_status.enum_values)

    # Check ExtendedNamespacedEnumUser.extendedLevel
    extended_namespaced_enum_user = model.messages["ExtendedNamespacedEnumUser"]
    assert len(extended_namespaced_enum_user.fields) == 1
    extended_level = extended_namespaced_enum_user.fields[0]
    assert extended_level.name == "extendedLevel"
    assert extended_level.field_type == FieldType.ENUM
    assert extended_level.enum_reference == "Test::NamespacedEnum.level"

    # Check that the enum values were copied from Test::NamespacedEnum.level and additional values were added
    namespaced_enum = model.messages["Test::NamespacedEnum"]
    level_field = namespaced_enum.fields[0]

    # The extended enum should have all the values from the original enum plus the additional values
    assert len(extended_level.enum_values) == len(level_field.enum_values) + 2

    # Check that the original enum values are present
    original_enum_values = {ev.name: ev.value for ev in level_field.enum_values}
    for name, value in original_enum_values.items():
        assert any(ev.name == name and ev.value == value for ev in extended_level.enum_values)

    # Check that the additional enum values are present
    assert any(ev.name == "EXTREME" and ev.value == 100 for ev in extended_level.enum_values)
    assert any(ev.name == "UNKNOWN" and ev.value == 101 for ev in extended_level.enum_values)

    # Check ExtendedMultipleEnumUser.extendedType and ExtendedMultipleEnumUser.extendedState
    extended_multiple_enum_user = model.messages["ExtendedMultipleEnumUser"]
    assert len(extended_multiple_enum_user.fields) == 2

    extended_type = extended_multiple_enum_user.fields[0]
    assert extended_type.name == "extendedType"
    assert extended_type.field_type == FieldType.ENUM
    assert extended_type.enum_reference == "MultipleEnums.type"

    extended_state = extended_multiple_enum_user.fields[1]
    assert extended_state.name == "extendedState"
    assert extended_state.field_type == FieldType.ENUM
    assert extended_state.enum_reference == "MultipleEnums.state"

    # Check that the enum values were copied from MultipleEnums.type and MultipleEnums.state and additional values were added
    multiple_enums = model.messages["MultipleEnums"]
    type_field = multiple_enums.fields[0]
    state_field = multiple_enums.fields[1]

    # The extended type enum should have all the values from the original enum plus the additional values
    assert len(extended_type.enum_values) == len(type_field.enum_values) + 2

    # Check that the original enum values are present
    original_enum_values = {ev.name: ev.value for ev in type_field.enum_values}
    for name, value in original_enum_values.items():
        assert any(ev.name == name and ev.value == value for ev in extended_type.enum_values)

    # Check that the additional enum values are present
    assert any(ev.name == "TYPE_C" and ev.value == 100 for ev in extended_type.enum_values)
    assert any(ev.name == "TYPE_D" and ev.value == 101 for ev in extended_type.enum_values)

    # The extended state enum should have all the values from the original enum plus the additional value
    assert len(extended_state.enum_values) == len(state_field.enum_values) + 1

    # Check that the original enum values are present
    original_enum_values = {ev.name: ev.value for ev in state_field.enum_values}
    for name, value in original_enum_values.items():
        assert any(ev.name == name and ev.value == value for ev in extended_state.enum_values)

    # Check that the additional enum value is present
    assert any(ev.name == "PENDING" and ev.value == 100 for ev in extended_state.enum_values)

def test_duplicate_enum_value_in_extension():
    """Test that duplicate enum value names in extended enum references are detected."""
    # Create a temporary file with a duplicate enum value name in an extended enum reference
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write("""
        message EnumContainer {
            field status: enum { OK = 0, ERROR = 1 }
        }

        message DuplicateEnumUser {
            field duplicateStatus: EnumContainer.status + { OK = 100 }
        }
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the duplicate enum value name
        assert any("Duplicate enum value name 'OK' in extended enum reference 'EnumContainer.status'" in error for error in parser.errors), \
            f"Expected error about duplicate enum value name, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
