"""
Test TypeScript Imports

This module contains tests for the TypeScript generator's handling of imports.
"""

import os
import pytest
from tempfile import NamedTemporaryFile

from message_model import MessageModel, Message, Field, FieldType
from message_parser import MessageParser
from typescript_generator import TypeScriptGenerator


@pytest.fixture
def base_message_file():
    """Create a base file with messages to be imported."""
    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""
message BaseMessage {
    field baseField: string
}

message AnotherBaseMessage {
    field anotherField: int
}

message ChildMessage : BaseMessage {
    field childField: float
}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


@pytest.fixture
def import_message_file(base_message_file):
    """Create a file that imports the base message file."""
    # Get the relative path to the base file
    base_file_path = os.path.basename(base_message_file)

    with NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(f"""
import "{base_file_path}" as Base

message MainMessage : Base::BaseMessage {{
    field mainField: string
}}

message DerivedMessage : Base::AnotherBaseMessage {{
    field derivedField: int
}}
        """)
        temp_file = f.name

    yield temp_file
    os.unlink(temp_file)


def test_typescript_explicit_imports(import_message_file, tmp_path):
    """Test that the TypeScript generator correctly generates explicit imports."""
    parser = MessageParser(import_message_file)
    model = parser.parse()

    assert model is not None, "Failed to parse file with import command"
    assert not parser.errors, f"Parser errors: {parser.errors}"

    # Generate TypeScript code
    output_dir = str(tmp_path)
    generator = TypeScriptGenerator(model, output_dir)
    result = generator.generate()
    assert result, "Failed to generate TypeScript code"

    # Find the generated TypeScript files
    ts_files = [f for f in os.listdir(output_dir) if f.endswith("_msgs.ts")]
    assert len(ts_files) >= 2, f"Expected at least 2 TypeScript files, found {len(ts_files)}: {ts_files}"

    # The main file is the one that imports from the base file
    # The base file is the one that doesn't import from any other file
    main_file = None
    base_file = None

    for ts_file in ts_files:
        file_path = os.path.join(output_dir, ts_file)
        with open(file_path, 'r') as f:
            content = f.read()

        if "import {" in content:
            main_file = file_path
        else:
            base_file = file_path

    assert main_file is not None, "Main file not found"
    assert base_file is not None, "Base file not found"

    # Get the base module name from the base file path
    base_module = os.path.splitext(os.path.basename(base_file))[0]

    # Read the main file
    with open(main_file, 'r') as f:
        main_content = f.read()

    # Print the content of the main file for debugging
    print("\nMain file content:")
    print(main_content)

    # Print the content of the base file for debugging
    with open(base_file, 'r') as f:
        base_content = f.read()
    print("\nBase file content:")
    print(base_content)

    # Check if there are any import statements in the main file
    import_lines = [line for line in main_content.split('\n') if line.startswith('import')]
    print("\nImport lines in main file:")
    for line in import_lines:
        print(line)

    # Check that the main file contains explicit imports, not wildcard imports
    # The import statement should be something like: import { Base_BaseMessage, Base_AnotherBaseMessage, isBase_BaseMessage, isBase_AnotherBaseMessage } from './base_module';
    # But the exact format might vary, so we'll check for the presence of both types and their type guard functions in the import
    assert "Base_BaseMessage" in main_content, "Base_BaseMessage not found in main file"
    assert "Base_AnotherBaseMessage" in main_content, "Base_AnotherBaseMessage not found in main file"
    assert "isBase_BaseMessage" in main_content, "isBase_BaseMessage type guard not found in main file"
    assert "isBase_AnotherBaseMessage" in main_content, "isBase_AnotherBaseMessage type guard not found in main file"

    # Check that there's at least one import statement
    assert len(import_lines) > 0, "No import statements found in main file"

    # Check that the import statement is using explicit imports, not wildcard imports
    assert any("import {" in line for line in import_lines), "No explicit imports found in main file"
    assert not any(f"import * as {base_module}" in line for line in import_lines), "Wildcard imports found in main file"

    # Check that the interfaces are defined correctly
    assert "export interface MainMessage extends Base_BaseMessage {" in main_content, "MainMessage interface not defined correctly"
    assert "export interface DerivedMessage extends Base_AnotherBaseMessage {" in main_content, "DerivedMessage interface not defined correctly"
