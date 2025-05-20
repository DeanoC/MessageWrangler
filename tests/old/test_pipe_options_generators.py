"""
Test Pipe Options Generators

This module contains tests for the output generators with pipe-separated options syntax.
"""

import os
import sys
import pytest
import json
import tempfile
import shutil

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_parser_core import MessageParser
from python_generator import PythonGenerator
from typescript_generator import TypeScriptGenerator
from cpp_generator import UnrealCppGenerator, StandardCppGenerator
from json_generator import JsonGenerator
from tests.test_utils import randomize_def_file, cleanup_temp_dir


def test_python_generator_options():
    """Test that the Python generator correctly handles options fields."""
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

        # Get the randomized names
        client_commands = name_mapping.get("ClientCommands", "ClientCommands")
        change_mode = name_mapping.get("ChangeMode", "ChangeMode")
        change_mode_reply = name_mapping.get("ChangeModeReply", "ChangeModeReply")
        modes_available_reply = name_mapping.get("ModesAvailableReply", "ModesAvailableReply")
        available_field = name_mapping.get("available", "available")
        live_value = name_mapping.get("Live", "Live")
        replay_value = name_mapping.get("Replay", "Replay")
        editor_value = name_mapping.get("Editor", "Editor")

        # Generate Python code
        output_dir = tempfile.mkdtemp()
        try:
            # Create a unique output name
            output_name = f"test_pipe_options_{random_file_name.replace('.def', '')}"
            generator = PythonGenerator(model, output_dir, output_name)
            result = generator.generate()
            assert result

            # Check that the output file exists
            output_file = os.path.join(output_dir, f"{output_name}_msgs.py")
            assert os.path.exists(output_file)

            # Read the output file
            with open(output_file, 'r') as f:
                content = f.read()

            # Python generator converts names to lowercase for class names
            client_commands_lower = client_commands.lower()
            modes_available_reply_lower = modes_available_reply.lower()
            available_field_lower = available_field.lower()
            change_mode_lower = change_mode.lower()
            change_mode_reply_lower = change_mode_reply.lower()

            # Check that the content contains expected elements for options
            options_class_name = f"class {client_commands_lower}{modes_available_reply_lower}{available_field_lower.capitalize()}Options(IntFlag):"
            assert options_class_name in content, f"Options class not found: {options_class_name}"
            assert f"{live_value} = 1" in content, f"{live_value} = 1 not found in content"
            assert f"{replay_value} = 2" in content, f"{replay_value} = 2 not found in content"
            assert f"{editor_value} = 4" in content, f"{editor_value} = 4 not found in content"

            # Check that the field is correctly defined in the message class
            field_definition = f"{available_field_lower}: {client_commands_lower}{modes_available_reply_lower}{available_field_lower.capitalize()}Options = 0"
            assert field_definition in content, f"Field definition not found: {field_definition}"

            # Check that the serialization methods handle options correctly
            serialization = f"\"{available_field_lower}\": int(self.{available_field_lower})"
            assert serialization in content, f"Serialization not found: {serialization}"

            deserialization = f"instance.{available_field_lower} = {client_commands_lower}{modes_available_reply_lower}{available_field_lower.capitalize()}Options(data[\"{available_field_lower}\"])"
            assert deserialization in content, f"Deserialization not found: {deserialization}"

            # Check that all comment lines in both ChangeMode and ChangeModeReply classes have the # prefix
            # This test will fail if any comment line is missing the # prefix
            with open(output_file, 'r') as f:
                content = f.read()
                lines = content.splitlines()

            # Check both classes for the issue
            classes_to_check = [f"{client_commands_lower}{change_mode_lower}", f"{client_commands_lower}{change_mode_reply_lower}"]

            for class_name in classes_to_check:
                # Find the class - look for @dataclass followed by the class definition
                class_start_idx = -1
                for i, line in enumerate(lines):
                    if i > 0 and "@dataclass" in lines[i-1] and f"class {class_name}" in line:
                        class_start_idx = i
                        break

                assert class_start_idx != -1, f"{class_name} class not found"

                # Print a few lines after the class definition for debugging
                print(f"\nChecking {class_name} class starting at line {class_start_idx}:")
                for i in range(class_start_idx, class_start_idx + 15):
                    if i < len(lines):
                        print(f"Line {i+1}: {lines[i]}")

                # Skip the general check and focus on the specific problematic lines
                # We need to track if we're inside a docstring
                in_docstring = False

                for i in range(class_start_idx, class_start_idx + 20):  # Check a reasonable number of lines
                    if i >= len(lines):
                        break
                    line = lines[i].strip()

                    # Track if we're inside a docstring
                    if line.startswith('"""') or line.endswith('"""'):
                        in_docstring = not in_docstring
                        continue

                    # Skip docstring content
                    if in_docstring:
                        continue

                    # Check specifically for the problematic lines
                    if "Replay an previous Unreal session recorded by the server" in line:
                        assert line.startswith("#"), f"In {class_name}, line {i+1} containing 'Replay an previous Unreal session' is missing # prefix: '{line}'"

                    if "Connect to the Unreal Editor through the server" in line and not live_value in line:
                        assert line.startswith("#"), f"In {class_name}, line {i+1} containing 'Connect to the Unreal Editor' is missing # prefix: '{line}'"

                # Make sure we found both problematic lines
                replay_line_found = False
                editor_line_found = False

                for i in range(class_start_idx, class_start_idx + 20):  # Check a reasonable number of lines
                    if i >= len(lines):
                        break
                    line = lines[i].strip()

                    # Skip docstring content
                    if line.startswith('"""') or line.endswith('"""') or in_docstring:
                        continue

                    if "Replay an previous Unreal session recorded by the server" in line:
                        replay_line_found = True

                    if "Connect to the Unreal Editor through the server" in line and not live_value in line:
                        editor_line_found = True

                assert replay_line_found, f"In {class_name}, did not find the line containing 'Replay an previous Unreal session'"
                assert editor_line_found, f"In {class_name}, did not find the line containing 'Connect to the Unreal Editor'"
        finally:
            # Clean up the output directory
            shutil.rmtree(output_dir)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)


def test_typescript_generator_options():
    """Test that the TypeScript generator correctly handles options fields."""
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

        # Get the randomized names
        client_commands = name_mapping.get("ClientCommands", "ClientCommands")
        modes_available_reply = name_mapping.get("ModesAvailableReply", "ModesAvailableReply")
        available_field = name_mapping.get("available", "available")
        live_value = name_mapping.get("Live", "Live")
        replay_value = name_mapping.get("Replay", "Replay")
        editor_value = name_mapping.get("Editor", "Editor")

        # Generate TypeScript code
        output_dir = tempfile.mkdtemp()
        try:
            # Create a unique output name
            output_name = f"test_pipe_options_{random_file_name.replace('.def', '')}"
            generator = TypeScriptGenerator(model, output_dir, output_name)
            result = generator.generate()
            assert result

            # Check that the output file exists
            output_file = os.path.join(output_dir, f"{output_name}_msgs.ts")
            assert os.path.exists(output_file)

            # Read the output file
            with open(output_file, 'r') as f:
                content = f.read()

            # Check that the content contains expected elements for options
            options_enum = f"export enum {client_commands}_{modes_available_reply}_{available_field}_Options"
            assert options_enum in content, f"Options enum not found: {options_enum}"
            assert f"{live_value} = 1," in content, f"{live_value} = 1, not found in content"
            assert f"{replay_value} = 2," in content, f"{replay_value} = 2, not found in content"
            assert f"{editor_value} = 4," in content, f"{editor_value} = 4, not found in content"

            # Check that the field is correctly defined in the interface
            field_definition = f"{available_field}: number;"
            assert field_definition in content, f"Field definition not found: {field_definition}"

            # Check that the type guard function is generated
            type_guard = f"export function is{client_commands}_{modes_available_reply}(obj: unknown): obj is {client_commands}_{modes_available_reply}"
            assert type_guard in content, f"Type guard function not found: {type_guard}"
        finally:
            # Clean up the output directory
            shutil.rmtree(output_dir)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)


def test_cpp_generator_options():
    """Test that the C++ generators correctly handle options fields."""
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

        # Get the randomized names
        modes_available_reply = name_mapping.get("ModesAvailableReply", "ModesAvailableReply")
        available_field = name_mapping.get("available", "available")
        live_value = name_mapping.get("Live", "Live")
        replay_value = name_mapping.get("Replay", "Replay")
        editor_value = name_mapping.get("Editor", "Editor")

        # Generate C++ code
        output_dir = tempfile.mkdtemp()
        try:
            # Create unique output names
            unreal_output_name = f"ue_test_pipe_options_{random_file_name.replace('.def', '')}"
            standard_output_name = f"c_test_pipe_options_{random_file_name.replace('.def', '')}"

            # Test Unreal C++ generator
            unreal_generator = UnrealCppGenerator(model, output_dir, unreal_output_name)
            result = unreal_generator.generate()
            assert result

            # Check that the output file exists
            unreal_output_file = os.path.join(output_dir, f"{unreal_output_name}_msgs.h")
            assert os.path.exists(unreal_output_file)

            # Read the output file
            with open(unreal_output_file, 'r') as f:
                unreal_content = f.read()

            # Check that the content contains expected elements for options
            unreal_options_enum = f"enum class {modes_available_reply}_{available_field}_Options : uint32"
            assert unreal_options_enum in unreal_content, f"Unreal options enum not found: {unreal_options_enum}"
            assert f"{live_value} = 1," in unreal_content, f"{live_value} = 1, not found in Unreal content"
            assert f"{replay_value} = 2," in unreal_content, f"{replay_value} = 2, not found in Unreal content"
            assert f"{editor_value} = 4," in unreal_content, f"{editor_value} = 4, not found in Unreal content"

            # Check that the field is correctly defined in the struct
            unreal_field_definition = f"uint32 {available_field} = 0;"
            assert unreal_field_definition in unreal_content, f"Unreal field definition not found: {unreal_field_definition}"

            # Test Standard C++ generator
            standard_generator = StandardCppGenerator(model, output_dir, standard_output_name)
            result = standard_generator.generate()
            assert result

            # Check that the output file exists
            standard_output_file = os.path.join(output_dir, f"{standard_output_name}_msgs.h")
            assert os.path.exists(standard_output_file)

            # Read the output file
            with open(standard_output_file, 'r') as f:
                standard_content = f.read()

            # Check that the content contains expected elements for options
            standard_options_enum = f"enum class {modes_available_reply}_{available_field}_Options : uint32_t"
            assert standard_options_enum in standard_content, f"Standard options enum not found: {standard_options_enum}"
            assert f"{live_value} = 1," in standard_content, f"{live_value} = 1, not found in Standard content"
            assert f"{replay_value} = 2," in standard_content, f"{replay_value} = 2, not found in Standard content"
            assert f"{editor_value} = 4," in standard_content, f"{editor_value} = 4, not found in Standard content"

            # Check that the field is correctly defined in the struct
            standard_field_definition = f"uint32_t {available_field} = 0;"
            assert standard_field_definition in standard_content, f"Standard field definition not found: {standard_field_definition}"
        finally:
            # Clean up the output directory
            shutil.rmtree(output_dir)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)


def test_json_generator_options():
    """Test that the JSON generator correctly handles options fields."""
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

        # Get the randomized names
        client_commands = name_mapping.get("ClientCommands", "ClientCommands")
        modes_available_reply = name_mapping.get("ModesAvailableReply", "ModesAvailableReply")
        available_field = name_mapping.get("available", "available")
        live_value = name_mapping.get("Live", "Live")
        replay_value = name_mapping.get("Replay", "Replay")
        editor_value = name_mapping.get("Editor", "Editor")

        # Generate JSON schema
        output_dir = tempfile.mkdtemp()
        try:
            # Create a unique output name
            output_name = f"test_pipe_options_{random_file_name.replace('.def', '')}_schema"
            generator = JsonGenerator(model, output_dir, output_name)
            result = generator.generate()
            assert result

            # Check that the output file exists
            output_file = os.path.join(output_dir, f"{output_name}.json")
            assert os.path.exists(output_file)

            # Read and parse the JSON output file
            with open(output_file, 'r') as f:
                json_content = json.load(f)

            # Check that the content contains expected elements for options
            assert "definitions" in json_content

            # The full message name with namespace
            full_message_name = f"{client_commands}::{modes_available_reply}"
            assert full_message_name in json_content["definitions"], f"Message definition not found: {full_message_name}"

            # Get the ModesAvailableReply definition
            reply_def = json_content["definitions"][full_message_name]

            # Check that it has properties
            assert "properties" in reply_def
            assert available_field in reply_def["properties"]

            # Check the available property
            available_prop = reply_def["properties"][available_field]
            assert available_prop["type"] == "integer"
            assert "options" in available_prop

            # The options are defined as an array of objects with name and value properties
            options = available_prop["options"]
            assert isinstance(options, list)
            assert len(options) == 3

            # Check that the options have the expected values
            option_names = [opt["name"] for opt in options]
            option_values = [opt["value"] for opt in options]

            assert live_value in option_names, f"{live_value} not found in option names: {option_names}"
            assert replay_value in option_names, f"{replay_value} not found in option names: {option_names}"
            assert editor_value in option_names, f"{editor_value} not found in option names: {option_names}"

            assert 1 in option_values, "Value 1 not found in option values"
            assert 2 in option_values, "Value 2 not found in option values"
            assert 4 in option_values, "Value 4 not found in option values"
        finally:
            # Clean up the output directory
            shutil.rmtree(output_dir)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)
