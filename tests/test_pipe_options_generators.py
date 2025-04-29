"""
Test Pipe Options Generators

This module contains tests for the output generators with pipe-separated options syntax.
"""

import os
import pytest
import json

from message_parser import MessageParser
from python_generator import PythonGenerator
from typescript_generator import TypeScriptGenerator
from cpp_generator import UnrealCppGenerator, StandardCppGenerator
from json_generator import JsonGenerator


def test_python_generator_options():
    """Test that the Python generator correctly handles options fields."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_pipe_options_fixed.def")

    # Parse the file
    parser = MessageParser(test_file)
    model = parser.parse()

    # Check that there are no errors
    assert not parser.errors, f"Parser errors: {parser.errors}"

    # Generate Python code
    temp_dir = os.path.join(os.path.dirname(__file__), "..", "generated")
    generator = PythonGenerator(model, temp_dir, "test_pipe_options")
    result = generator.generate()
    assert result

    # Check that the output file exists
    output_file = os.path.join(temp_dir, "test_pipe_options_msgs.py")
    assert os.path.exists(output_file)

    # Read the output file
    with open(output_file, 'r') as f:
        content = f.read()

    # Check that the content contains expected elements for options
    assert "class ClientcommandsModesavailablereplyAvailableOptions(IntFlag):" in content
    assert "Live = 1" in content
    assert "Replay = 2" in content
    assert "Editor = 4" in content

    # Check that the field is correctly defined in the message class
    assert "available: ClientcommandsModesavailablereplyAvailableOptions = 0" in content

    # Check that the serialization methods handle options correctly
    assert "\"available\": int(self.available)" in content
    assert "instance.available = ClientcommandsModesavailablereplyAvailableOptions(data[\"available\"])" in content

    # Check that all comment lines in both ChangeMode and ChangeModeReply classes have the # prefix
    # This test will fail if any comment line is missing the # prefix
    with open(output_file, 'r') as f:
        content = f.read()
        lines = content.splitlines()

    # Check both classes for the issue
    classes_to_check = ["ClientcommandsChangemode", "ClientcommandsChangemodereply"]

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

            if "Connect to the Unreal Editor through the server" in line and not "Live" in line:
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

            if "Connect to the Unreal Editor through the server" in line and not "Live" in line:
                editor_line_found = True

        assert replay_line_found, f"In {class_name}, did not find the line containing 'Replay an previous Unreal session'"
        assert editor_line_found, f"In {class_name}, did not find the line containing 'Connect to the Unreal Editor'"


def test_typescript_generator_options():
    """Test that the TypeScript generator correctly handles options fields."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_pipe_options_fixed.def")

    # Parse the file
    parser = MessageParser(test_file)
    model = parser.parse()

    # Check that there are no errors
    assert not parser.errors, f"Parser errors: {parser.errors}"

    # Generate TypeScript code
    temp_dir = os.path.join(os.path.dirname(__file__), "..", "generated")
    generator = TypeScriptGenerator(model, temp_dir, "test_pipe_options")
    result = generator.generate()
    assert result

    # Check that the output file exists
    output_file = os.path.join(temp_dir, "test_pipe_options_msgs.ts")
    assert os.path.exists(output_file)

    # Read the output file
    with open(output_file, 'r') as f:
        content = f.read()

    # Check that the content contains expected elements for options
    assert "export enum ClientCommands_ModesAvailableReply_available_Options {" in content
    assert "Live = 1," in content
    assert "Replay = 2," in content
    assert "Editor = 4," in content

    # Check that the field is correctly defined in the interface
    assert "available: number;" in content

    # Check that the type guard function is generated
    assert "export function isClientCommands_ModesAvailableReply(obj: unknown): obj is ClientCommands_ModesAvailableReply {" in content


def test_cpp_generator_options():
    """Test that the C++ generators correctly handle options fields."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_pipe_options_fixed.def")

    # Parse the file
    parser = MessageParser(test_file)
    model = parser.parse()

    # Check that there are no errors
    assert not parser.errors, f"Parser errors: {parser.errors}"

    # Generate Unreal C++ code
    temp_dir = os.path.join(os.path.dirname(__file__), "..", "generated")

    # Test Unreal C++ generator
    unreal_generator = UnrealCppGenerator(model, temp_dir, "ue_test_pipe_options")
    result = unreal_generator.generate()
    assert result

    # Check that the output file exists
    unreal_output_file = os.path.join(temp_dir, "ue_test_pipe_options_msgs.h")
    assert os.path.exists(unreal_output_file)

    # Read the output file
    with open(unreal_output_file, 'r') as f:
        unreal_content = f.read()

    # Check that the content contains expected elements for options
    assert "enum class ModesAvailableReply_available_Options : uint32" in unreal_content
    assert "Live = 1," in unreal_content
    assert "Replay = 2," in unreal_content
    assert "Editor = 4," in unreal_content

    # Check that the field is correctly defined in the struct
    assert "uint32 available = 0;" in unreal_content

    # Test Standard C++ generator
    standard_generator = StandardCppGenerator(model, temp_dir, "c_test_pipe_options")
    result = standard_generator.generate()
    assert result

    # Check that the output file exists
    standard_output_file = os.path.join(temp_dir, "c_test_pipe_options_msgs.h")
    assert os.path.exists(standard_output_file)

    # Read the output file
    with open(standard_output_file, 'r') as f:
        standard_content = f.read()

    # Check that the content contains expected elements for options
    assert "enum class ModesAvailableReply_available_Options : uint32_t" in standard_content
    assert "Live = 1," in standard_content
    assert "Replay = 2," in standard_content
    assert "Editor = 4," in standard_content

    # Check that the field is correctly defined in the struct
    assert "uint32_t available = 0;" in standard_content


def test_json_generator_options():
    """Test that the JSON generator correctly handles options fields."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_pipe_options_fixed.def")

    # Parse the file
    parser = MessageParser(test_file)
    model = parser.parse()

    # Check that there are no errors
    assert not parser.errors, f"Parser errors: {parser.errors}"

    # Generate JSON schema
    temp_dir = os.path.join(os.path.dirname(__file__), "..", "generated")
    generator = JsonGenerator(model, temp_dir, "test_pipe_options_msgs_schema")
    result = generator.generate()
    assert result

    # Check that the output file exists
    output_file = os.path.join(temp_dir, "test_pipe_options_msgs_schema.json")
    assert os.path.exists(output_file)

    # Read and parse the JSON output file
    with open(output_file, 'r') as f:
        json_content = json.load(f)

    # Check that the content contains expected elements for options
    assert "definitions" in json_content
    assert "ClientCommands::ModesAvailableReply" in json_content["definitions"]

    # Get the ModesAvailableReply definition
    reply_def = json_content["definitions"]["ClientCommands::ModesAvailableReply"]

    # Check that it has properties
    assert "properties" in reply_def
    assert "available" in reply_def["properties"]

    # Check the available property
    available_prop = reply_def["properties"]["available"]
    assert available_prop["type"] == "integer"
    assert "options" in available_prop

    # The options are defined as an array of objects with name and value properties
    options = available_prop["options"]
    assert isinstance(options, list)
    assert len(options) == 3

    # Check that the options have the expected values
    option_names = [opt["name"] for opt in options]
    option_values = [opt["value"] for opt in options]

    assert "Live" in option_names
    assert "Replay" in option_names
    assert "Editor" in option_names

    assert 1 in option_values
    assert 2 in option_values
    assert 4 in option_values
