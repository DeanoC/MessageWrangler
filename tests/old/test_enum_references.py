import os
import pytest
import sys
import tempfile
import shutil

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_parser_core import MessageParser
from message_model import FieldType
from tests.test_utils import randomize_def_file, cleanup_temp_dir, generate_random_name

def test_enum_references():
    """Test parsing and validation of enum references."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_enum_references.def")

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
        parser = MessageParser(random_file_name, verbose=True)
        model = parser.parse()

        # Change back to the original directory
        os.chdir(original_dir)

        # Check that there are no errors
        assert not parser.errors, f"Parsing errors: {parser.errors}"

        # Check that the model was created
        assert model is not None, "Model is None"

        # Get the randomized message names
        enum_container = name_mapping.get("EnumContainer", "EnumContainer")
        enum_user = name_mapping.get("EnumUser", "EnumUser")
        test_namespace = name_mapping.get("Test", "Test")
        namespaced_enum = name_mapping.get("NamespacedEnum", "NamespacedEnum")
        namespaced_enum_user = name_mapping.get("NamespacedEnumUser", "NamespacedEnumUser")
        multiple_enums = name_mapping.get("MultipleEnums", "MultipleEnums")
        multiple_enum_user = name_mapping.get("MultipleEnumUser", "MultipleEnumUser")

        # Check that all messages were parsed
        assert enum_container in model.messages
        assert enum_user in model.messages
        assert f"{test_namespace}::{namespaced_enum}" in model.messages
        assert namespaced_enum_user in model.messages
        assert multiple_enums in model.messages
        assert multiple_enum_user in model.messages

        # Get the randomized field names
        status = name_mapping.get("status", "status")
        container_status = name_mapping.get("containerStatus", "containerStatus")
        level = name_mapping.get("level", "level")
        test_level = name_mapping.get("testLevel", "testLevel")
        type_field = name_mapping.get("type", "type")
        state = name_mapping.get("state", "state")
        multi_type = name_mapping.get("multiType", "multiType")
        multi_state = name_mapping.get("multiState", "multiState")

        # Check that enum references were resolved correctly

        # Check EnumUser.containerStatus
        enum_user_msg = model.messages[enum_user]
        assert len(enum_user_msg.fields) == 1
        container_status_field = enum_user_msg.fields[0]
        assert container_status_field.name == container_status
        assert container_status_field.field_type == FieldType.ENUM
        assert container_status_field.enum_reference == f"{enum_container}.{status}"

        # Check that the enum values were copied from EnumContainer.status
        enum_container_msg = model.messages[enum_container]
        status_field_obj = enum_container_msg.fields[0]
        assert status_field_obj.name == status
        assert status_field_obj.field_type == FieldType.ENUM

        # Compare enum values
        assert len(container_status_field.enum_values) == len(status_field_obj.enum_values)
        for i, enum_value in enumerate(status_field_obj.enum_values):
            assert container_status_field.enum_values[i].name == enum_value.name
            assert container_status_field.enum_values[i].value == enum_value.value

        # Check NamespacedEnumUser.testLevel
        namespaced_enum_user_msg = model.messages[namespaced_enum_user]
        assert len(namespaced_enum_user_msg.fields) == 1
        test_level_field = namespaced_enum_user_msg.fields[0]
        assert test_level_field.name == test_level
        assert test_level_field.field_type == FieldType.ENUM
        assert test_level_field.enum_reference == f"{test_namespace}::{namespaced_enum}.{level}"

        # Check that the enum values were copied from Test::NamespacedEnum.level
        namespaced_enum_msg = model.messages[f"{test_namespace}::{namespaced_enum}"]
        level_field_obj = namespaced_enum_msg.fields[0]
        assert level_field_obj.name == level
        assert level_field_obj.field_type == FieldType.ENUM

        # Compare enum values
        assert len(test_level_field.enum_values) == len(level_field_obj.enum_values)
        for i, enum_value in enumerate(level_field_obj.enum_values):
            assert test_level_field.enum_values[i].name == enum_value.name
            assert test_level_field.enum_values[i].value == enum_value.value

        # Check MultipleEnumUser.multiType and MultipleEnumUser.multiState
        multiple_enum_user_msg = model.messages[multiple_enum_user]
        assert len(multiple_enum_user_msg.fields) == 2

        multi_type_field = multiple_enum_user_msg.fields[0]
        assert multi_type_field.name == multi_type
        assert multi_type_field.field_type == FieldType.ENUM
        assert multi_type_field.enum_reference == f"{multiple_enums}.{type_field}"

        multi_state_field = multiple_enum_user_msg.fields[1]
        assert multi_state_field.name == multi_state
        assert multi_state_field.field_type == FieldType.ENUM
        assert multi_state_field.enum_reference == f"{multiple_enums}.{state}"

        # Check that the enum values were copied from MultipleEnums.type and MultipleEnums.state
        multiple_enums_msg = model.messages[multiple_enums]
        type_field_obj = multiple_enums_msg.fields[0]
        state_field_obj = multiple_enums_msg.fields[1]

        # Compare enum values for type
        assert len(multi_type_field.enum_values) == len(type_field_obj.enum_values)
        for i, enum_value in enumerate(type_field_obj.enum_values):
            assert multi_type_field.enum_values[i].name == enum_value.name
            assert multi_type_field.enum_values[i].value == enum_value.value

        # Compare enum values for state
        assert len(multi_state_field.enum_values) == len(state_field_obj.enum_values)
        for i, enum_value in enumerate(state_field_obj.enum_values):
            assert multi_state_field.enum_values[i].name == enum_value.name
            assert multi_state_field.enum_values[i].value == enum_value.value
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)

def test_invalid_enum_reference():
    """Test that invalid enum references are detected."""
    # Generate random names
    enum_container = f"RandomContainer_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"
    ok_value = f"RANDOM_OK_{generate_random_name()}"
    error_value = f"RANDOM_ERROR_{generate_random_name()}"
    invalid_enum_user = f"RandomInvalidUser_{generate_random_name()}"
    invalid_status = f"randomInvalidStatus_{generate_random_name()}"
    nonexistent = f"nonexistent_{generate_random_name()}"

    # Create a temporary file with an invalid enum reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        message {enum_container} {{
            field {status_field}: enum {{ {ok_value} = 0, {error_value} = 1 }}
        }}

        message {invalid_enum_user} {{
            field {invalid_status}: {enum_container}.{nonexistent}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid enum reference
        assert any(f"Enum '{nonexistent}' not found in message '{enum_container}'" in error for error in parser.errors), \
            f"Expected error about nonexistent enum, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_invalid_message_reference():
    """Test that invalid message references in enum references are detected."""
    # Generate random names
    invalid_enum_user = f"RandomInvalidUser_{generate_random_name()}"
    invalid_status = f"randomInvalidStatus_{generate_random_name()}"
    nonexistent_message = f"NonexistentMessage_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"

    # Create a temporary file with an invalid message reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        message {invalid_enum_user} {{
            field {invalid_status}: {nonexistent_message}.{status_field}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the invalid message reference
        assert any(f"Message '{nonexistent_message}' referenced by enum reference '{nonexistent_message}.{status_field}'" in error for error in parser.errors), \
            f"Expected error about nonexistent message, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_extended_enum_references():
    """Test parsing and validation of extended enum references."""
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "test_enum_references.def")

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
        parser = MessageParser(random_file_name, verbose=True)
        model = parser.parse()

        # Change back to the original directory
        os.chdir(original_dir)

        # Check that there are no errors
        assert not parser.errors, f"Parsing errors: {parser.errors}"

        # Check that the model was created
        assert model is not None, "Model is None"

        # Get the randomized message names
        enum_container = name_mapping.get("EnumContainer", "EnumContainer")
        test_namespace = name_mapping.get("Test", "Test")
        namespaced_enum = name_mapping.get("NamespacedEnum", "NamespacedEnum")
        multiple_enums = name_mapping.get("MultipleEnums", "MultipleEnums")
        extended_enum_user = name_mapping.get("ExtendedEnumUser", "ExtendedEnumUser")
        extended_namespaced_enum_user = name_mapping.get("ExtendedNamespacedEnumUser", "ExtendedNamespacedEnumUser")
        extended_multiple_enum_user = name_mapping.get("ExtendedMultipleEnumUser", "ExtendedMultipleEnumUser")

        # Get the randomized field names
        status = name_mapping.get("status", "status")
        extended_status = name_mapping.get("extendedStatus", "extendedStatus")
        level = name_mapping.get("level", "level")
        extended_level = name_mapping.get("extendedLevel", "extendedLevel")
        type_field = name_mapping.get("type", "type")
        state = name_mapping.get("state", "state")
        extended_type = name_mapping.get("extendedType", "extendedType")
        extended_state = name_mapping.get("extendedState", "extendedState")

        # Get the randomized enum value names
        ok = name_mapping.get("OK", "OK")
        error = name_mapping.get("ERROR", "ERROR")
        warning = name_mapping.get("WARNING", "WARNING")
        critical = name_mapping.get("CRITICAL", "CRITICAL")
        unknown = name_mapping.get("UNKNOWN", "UNKNOWN")
        low = name_mapping.get("LOW", "LOW")
        medium = name_mapping.get("MEDIUM", "MEDIUM")
        high = name_mapping.get("HIGH", "HIGH")
        extreme = name_mapping.get("EXTREME", "EXTREME")
        type_a = name_mapping.get("TYPE_A", "TYPE_A")
        type_b = name_mapping.get("TYPE_B", "TYPE_B")
        type_c = name_mapping.get("TYPE_C", "TYPE_C")
        type_d = name_mapping.get("TYPE_D", "TYPE_D")
        on = name_mapping.get("ON", "ON")
        off = name_mapping.get("OFF", "OFF")
        pending = name_mapping.get("PENDING", "PENDING")

        # Check that all messages were parsed
        assert extended_enum_user in model.messages
        assert extended_namespaced_enum_user in model.messages
        assert extended_multiple_enum_user in model.messages

        # Check ExtendedEnumUser.extendedStatus
        extended_enum_user_msg = model.messages[extended_enum_user]
        assert len(extended_enum_user_msg.fields) == 1
        extended_status_field = extended_enum_user_msg.fields[0]
        assert extended_status_field.name == extended_status
        assert extended_status_field.field_type == FieldType.ENUM
        assert extended_status_field.enum_reference == f"{enum_container}.{status}"

        # Check that the enum values were copied from EnumContainer.status and additional values were added
        enum_container_msg = model.messages[enum_container]
        status_field_obj = enum_container_msg.fields[0]

        # The extended enum should have all the values from the original enum plus the additional values
        assert len(extended_status_field.enum_values) == len(status_field_obj.enum_values) + 2

        # Check that the original enum values are present
        original_enum_values = {ev.name: ev.value for ev in status_field_obj.enum_values}
        for name, value in original_enum_values.items():
            assert any(ev.name == name and ev.value == value for ev in extended_status_field.enum_values)

        # Check that the additional enum values are present
        assert any(ev.name == critical and ev.value == 100 for ev in extended_status_field.enum_values)
        assert any(ev.name == unknown and ev.value == 101 for ev in extended_status_field.enum_values)

        # Check ExtendedNamespacedEnumUser.extendedLevel
        extended_namespaced_enum_user_msg = model.messages[extended_namespaced_enum_user]
        assert len(extended_namespaced_enum_user_msg.fields) == 1
        extended_level_field = extended_namespaced_enum_user_msg.fields[0]
        assert extended_level_field.name == extended_level
        assert extended_level_field.field_type == FieldType.ENUM
        assert extended_level_field.enum_reference == f"{test_namespace}::{namespaced_enum}.{level}"

        # Check that the enum values were copied from Test::NamespacedEnum.level and additional values were added
        namespaced_enum_msg = model.messages[f"{test_namespace}::{namespaced_enum}"]
        level_field_obj = namespaced_enum_msg.fields[0]

        # The extended enum should have all the values from the original enum plus the additional values
        assert len(extended_level_field.enum_values) == len(level_field_obj.enum_values) + 2

        # Check that the original enum values are present
        original_enum_values = {ev.name: ev.value for ev in level_field_obj.enum_values}
        for name, value in original_enum_values.items():
            assert any(ev.name == name and ev.value == value for ev in extended_level_field.enum_values)

        # Check that the additional enum values are present
        assert any(ev.name == extreme and ev.value == 100 for ev in extended_level_field.enum_values)
        assert any(ev.name == unknown and ev.value == 101 for ev in extended_level_field.enum_values)

        # Check ExtendedMultipleEnumUser.extendedType and ExtendedMultipleEnumUser.extendedState
        extended_multiple_enum_user_msg = model.messages[extended_multiple_enum_user]
        assert len(extended_multiple_enum_user_msg.fields) == 2

        extended_type_field = extended_multiple_enum_user_msg.fields[0]
        assert extended_type_field.name == extended_type
        assert extended_type_field.field_type == FieldType.ENUM
        assert extended_type_field.enum_reference == f"{multiple_enums}.{type_field}"

        extended_state_field = extended_multiple_enum_user_msg.fields[1]
        assert extended_state_field.name == extended_state
        assert extended_state_field.field_type == FieldType.ENUM
        assert extended_state_field.enum_reference == f"{multiple_enums}.{state}"

        # Check that the enum values were copied from MultipleEnums.type and MultipleEnums.state and additional values were added
        multiple_enums_msg = model.messages[multiple_enums]
        type_field_obj = multiple_enums_msg.fields[0]
        state_field_obj = multiple_enums_msg.fields[1]

        # The extended type enum should have all the values from the original enum plus the additional values
        assert len(extended_type_field.enum_values) == len(type_field_obj.enum_values) + 2

        # Check that the original enum values are present
        original_enum_values = {ev.name: ev.value for ev in type_field_obj.enum_values}
        for name, value in original_enum_values.items():
            assert any(ev.name == name and ev.value == value for ev in extended_type_field.enum_values)

        # Check that the additional enum values are present
        assert any(ev.name == type_c and ev.value == 100 for ev in extended_type_field.enum_values)
        assert any(ev.name == type_d and ev.value == 101 for ev in extended_type_field.enum_values)

        # The extended state enum should have all the values from the original enum plus the additional value
        assert len(extended_state_field.enum_values) == len(state_field_obj.enum_values) + 1

        # Check that the original enum values are present
        original_enum_values = {ev.name: ev.value for ev in state_field_obj.enum_values}
        for name, value in original_enum_values.items():
            assert any(ev.name == name and ev.value == value for ev in extended_state_field.enum_values)

        # Check that the additional enum value is present
        assert any(ev.name == pending and ev.value == 100 for ev in extended_state_field.enum_values)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)

def test_duplicate_enum_value_in_extension():
    """Test that duplicate enum value names in extended enum references are detected."""
    # Generate random names
    enum_container = f"RandomContainer_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"
    ok_value = f"RANDOM_OK_{generate_random_name()}"
    error_value = f"RANDOM_ERROR_{generate_random_name()}"
    duplicate_enum_user = f"RandomDuplicateUser_{generate_random_name()}"
    duplicate_status = f"randomDuplicateStatus_{generate_random_name()}"

    # Create a temporary file with a duplicate enum value name in an extended enum reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.def', delete=False) as f:
        f.write(f"""
        message {enum_container} {{
            field {status_field}: enum {{ {ok_value} = 0, {error_value} = 1 }}
        }}

        message {duplicate_enum_user} {{
            field {duplicate_status}: {enum_container}.{status_field} + {{ {ok_value} = 100 }}
        }}
        """)
        temp_file = f.name

    try:
        # Parse the temporary file
        parser = MessageParser(temp_file, verbose=True)
        model = parser.parse()

        # Check that there is an error about the duplicate enum value name
        assert any(f"Duplicate enum value name '{ok_value}' in extended enum reference '{enum_container}.{status_field}'" in error for error in parser.errors), \
            f"Expected error about duplicate enum value name, but got: {parser.errors}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
