"""
Test C++ Generator

This module contains tests for the C++ generator.
"""

import os
import pytest
import tempfile

from cpp_generator.unreal_cpp_generator import UnrealCppGenerator
from cpp_generator.standard_cpp_generator import StandardCppGenerator
from message_parser_core import MessageParser


def test_unreal_generator(test_model, temp_dir):
    """Test generating Unreal Engine C++ code."""
    generator = UnrealCppGenerator(test_model, temp_dir)
    result = generator.generate()
    assert result

    # Check that the output file exists
    output_file = os.path.join(temp_dir, f"ue_{generator.output_name}_msgs.h")
    assert os.path.exists(output_file)

    # Read the output file
    with open(output_file, 'r') as f:
        content = f.read()

    # Check that the content contains expected elements
    assert "namespace ue_Messages" in content
    assert "struct SimpleMessage" in content
    assert "struct BaseMessage" in content
    assert "struct DerivedMessage : public BaseMessage" in content
    assert "FString stringField" in content
    assert "int32 intField" in content
    assert "float floatField" in content
    assert "SimpleMessage_status_Enum status" in content
    assert "enum class SimpleMessage_status_Enum" in content
    assert "OK = 0" in content
    assert "ERROR = 1" in content
    assert "PENDING = 2" in content
    assert "struct {" in content
    assert "float x" in content
    assert "float y" in content
    assert "float z" in content
    assert "} position" in content

    # Check for Unreal-specific elements
    assert "CoreMinimal.h" in content
    assert "Auto-generated message definitions for Unreal Engine C++" in content


def test_standard_generator(test_model, temp_dir):
    """Test generating standard C++ code."""
    generator = StandardCppGenerator(test_model, temp_dir)
    result = generator.generate()
    assert result

    # Check that the output file exists
    output_file = os.path.join(temp_dir, f"c_{generator.output_name}_msgs.h")
    assert os.path.exists(output_file)

    # Read the output file
    with open(output_file, 'r') as f:
        content = f.read()

    # Check that the content contains expected elements
    assert "namespace c_Messages" in content
    assert "struct SimpleMessage" in content
    assert "struct BaseMessage" in content
    assert "struct DerivedMessage : public BaseMessage" in content
    assert "std::string stringField" in content
    assert "int32_t intField" in content
    assert "float floatField" in content
    assert "SimpleMessage_status_Enum status" in content
    assert "enum class SimpleMessage_status_Enum" in content
    assert "OK = 0" in content
    assert "ERROR = 1" in content
    assert "PENDING = 2" in content
    assert "struct {" in content
    assert "float x" in content
    assert "float y" in content
    assert "float z" in content
    assert "} position" in content

    # Check for standard C++-specific elements
    assert "#include <string>" in content
    assert "#include <cstdint>" in content
    assert "Auto-generated message definitions for standard C++" in content
    assert "uint8_t" in content


def test_namespace_matches_filename():
    """Test that the namespace alias is correctly defined for imported files."""
    # Create a base file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.def') as base_file:
        base_file.write("""
namespace Base {
    message Command {
        field type: string
    }
}
        """)
        base_file_path = base_file.name
        base_file_name = os.path.basename(base_file_path)
        # Get the base name without extension for expected namespace
        base_name_without_ext = os.path.splitext(base_file_name)[0]

    # Create a main file that imports the base file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.def') as main_file:
        main_file.write(f"""
import "{base_file_name}" as Base

namespace ClientCommands {{
    message ChangeMode : Base::Command {{
        field mode: string
    }}
}}
        """)
        main_file_path = main_file.name
        main_file_name = os.path.basename(main_file_path)

    try:
        # Parse the main file
        parser = MessageParser(main_file_path)
        model = parser.parse()
        assert model is not None, "Failed to parse file with import command"

        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate Unreal C++ code
            # Use the base name without extension as the output name
            unreal_generator = UnrealCppGenerator(model, temp_dir, base_name_without_ext)
            result = unreal_generator.generate()
            assert result, "Failed to generate Unreal C++ code"

            # Find all generated Unreal C++ files
            unreal_files = [f for f in os.listdir(temp_dir) if f.startswith("ue_") and f.endswith("_msgs.h")]
            assert len(unreal_files) >= 2, f"Expected at least 2 Unreal C++ files, found {len(unreal_files)}"

            # Check each file for correct namespace
            for file_name in unreal_files:
                # Extract the expected namespace name from the file name
                expected_namespace = file_name[3:-7]  # Remove "ue_" and "_msgs.h"

                # Read the file
                with open(os.path.join(temp_dir, file_name), 'r') as f:
                    content = f.read()

                # If this is the main file (contains ClientCommands namespace), check for namespace alias
                if "ClientCommands" in content:
                    # The namespace alias should map "Base" to the base file's namespace with the ue_ prefix
                    expected_alias = f"namespace Base = ue_{base_name_without_ext};"
                    assert expected_alias in content, f"Namespace alias not correctly defined in {file_name}. Expected: {expected_alias}"

                    # Verify that the parent reference is correctly defined
                    assert "public Base::Command" in content, f"Parent reference not correctly defined in {file_name}"

                    # Print the content for debugging
                    print(f"Content of {file_name}:")
                    print(content[:500])  # Print first 500 chars to avoid too much output

                # If this is the base file, check that the namespace matches the base file name
                elif "namespace Base" in content and "message Command" in content:
                    # The namespace in the base file should match the base file name (without extension)
                    assert f"namespace {expected_namespace}" in content, f"Namespace in base file does not match file name in {file_name}. Expected: namespace {expected_namespace}"

            # Generate standard C++ code
            # Use the base name without extension as the output name
            standard_generator = StandardCppGenerator(model, temp_dir, base_name_without_ext)
            result = standard_generator.generate()
            assert result, "Failed to generate standard C++ code"

            # Find all generated standard C++ files
            standard_files = [f for f in os.listdir(temp_dir) if f.startswith("c_") and f.endswith("_msgs.h")]
            assert len(standard_files) >= 2, f"Expected at least 2 standard C++ files, found {len(standard_files)}"

            # Check each file for correct namespace
            for file_name in standard_files:
                # Extract the expected namespace name from the file name
                expected_namespace = file_name[2:-7]  # Remove "c_" and "_msgs.h"

                # Read the file
                with open(os.path.join(temp_dir, file_name), 'r') as f:
                    content = f.read()

                # If this is the main file (contains ClientCommands namespace), check for namespace alias
                if "ClientCommands" in content:
                    # The namespace alias should map "Base" to the base file's namespace with the c_ prefix
                    expected_alias = f"namespace Base = c_{base_name_without_ext};"
                    assert expected_alias in content, f"Namespace alias not correctly defined in {file_name}. Expected: {expected_alias}"

                    # Verify that the parent reference is correctly defined
                    assert "public Base::Command" in content, f"Parent reference not correctly defined in {file_name}"

                    # Print the content for debugging
                    print(f"Content of {file_name}:")
                    print(content[:500])  # Print first 500 chars to avoid too much output

                # If this is the base file, check that the namespace matches the base file name
                elif "namespace Base" in content and "message Command" in content:
                    # The namespace in the base file should match the base file name (without extension)
                    assert f"namespace {expected_namespace}" in content, f"Namespace in base file does not match file name in {file_name}. Expected: namespace {expected_namespace}"

    finally:
        # Clean up temporary files
        os.unlink(base_file_path)
        os.unlink(main_file_path)


def test_sh4c_namespace_and_inheritance():
    """Test that the namespace and inheritance are correctly defined for sh4c files."""
    # Create a temporary directory for our test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a base file (sh4c_base.def) with a fixed name
        base_file_path = os.path.join(temp_dir, "sh4c_base.def")
        with open(base_file_path, 'w') as base_file:
            base_file.write("""/// Base message for all commands
message Command {
    /// The type of command
    field type: enum {
        Status
    }
    field key: string
}
/// Base message for all replies
message Reply {
    /// The status of the command execution
    field status: enum {
        Success,
        Failure,
        Pending
    }
    field key: string
}

/// Status doesn't have a paremeter it just pings the other side
message Status : Command {}
/// StatusReplay return a message with name and version of this side
message StatusReply : Reply {
    field msg: string
}""")
        base_file_name = os.path.basename(base_file_path)
        # Validate that sh4c_base.def was created successfully
        assert os.path.exists(base_file_path), "sh4c_base.def was not created successfully."

        # Validate the content of sh4c_base.def
        with open(base_file_path, 'r') as base_file:
            base_content = base_file.read()
            assert "message Command" in base_content, "sh4c_base.def content is invalid: missing 'message Command'."
            assert "message Reply" in base_content, "sh4c_base.def content is invalid: missing 'message Reply'."

        # Get the base name without extension for expected namespace
        base_name_without_ext = os.path.splitext(base_file_name)[0]

        # Create a main file (sh4c_comms.def) that imports the base file
        main_file_path = os.path.join(temp_dir, "sh4c_comms.def")
        with open(main_file_path, 'w') as main_file:
            main_file.write(f"""/// Message file for communication between sh4 companion client and server


import "{base_file_name}" as Base

/// Command the client can send to the server
namespace ClientCommands {{
    /// Client to server messages
    message ChangeMode : Base::Command {{
        field mode: enum {{
            /// Connect to the Unreal target through the server
            Live,
            /// Replay an previous Unreal session recorded by the server
            Replay,
            /// Connect to the Unreal Editor through the server
            Editor
        }}
    }}
    /// reply with the mode that was set (can be different from the one requested)
    message ChangeModeReply : Base::Reply {{
        field mode: enum {{
            /// Connect to the Unreal target through the server
            Live,
            /// Replay an previous Unreal session recorded by the server
            Replay,
            /// Connect to the Unreal Editor through the server
            Editor
        }}
    }}

    /// Ask the server what modes are currently available
    message ModesAvailable : Base::Command {{}}
    /// reply with the modes that are currently available
    message ModesAvailableReply : Base::Reply {{
        field available: options {{ Live, Replay, Editor }}
    }}
}}""")
        main_file_name = os.path.basename(main_file_path)

        # Parse the main file
        parser = MessageParser(main_file_path)
        model = parser.parse()
        assert model is not None, "Failed to parse file with import command"

        # Create a directory for output (use a subdirectory of our temp_dir)
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Generate Unreal C++ code
        # Use the base name without extension as the output name
        unreal_generator = UnrealCppGenerator(model, output_dir, base_name_without_ext)
        result = unreal_generator.generate()
        assert result, "Failed to generate Unreal C++ code"

        # Find all generated Unreal C++ files
        unreal_files = [f for f in os.listdir(output_dir) if f.startswith("ue_") and f.endswith("_msgs.h")]
        assert len(unreal_files) >= 2, f"Expected at least 2 Unreal C++ files, found {len(unreal_files)}"

        # Check each file for correct namespace
        for file_name in unreal_files:
            # Read the file
            with open(os.path.join(output_dir, file_name), 'r') as f:
                content = f.read()
                print(f"Content of {file_name}:")
                print(content[:500])  # Print first 500 chars to avoid too much output

            # If this is the base file (contains Command and Reply messages)
            if "struct Command" in content or "struct Reply" in content:
                # The namespace should be ue_sh4c_base
                assert "namespace ue_sh4c_base" in content, f"Namespace in base file is incorrect in {file_name}. Expected: namespace ue_sh4c_base"
                # The namespace should not be nested inside another namespace
                assert "namespace ue_sh4c_comms" not in content, f"Namespace ue_sh4c_comms should not be in base file {file_name}"
                # The base file should not have a "Base" namespace
                assert "namespace Base {" not in content, f"Base namespace should not be in base file {file_name}"
                # The base file should not have a "ClientCommands" namespace
                assert "namespace ClientCommands" not in content, f"ClientCommands namespace should not be in base file {file_name}"

            # If this is the comms file (contains ClientCommands namespace)
            if "ClientCommands" in content:
                # The namespace alias should map "Base" to ue_sh4c_base
                assert "namespace Base = ue_sh4c_base;" in content, f"Namespace alias not correctly defined in {file_name}. Expected: namespace Base = ue_sh4c_base;"

                # Verify that the parent references are correctly defined
                assert "public Base::Command" in content, f"Parent reference to Command not correctly defined in {file_name}"
                assert "public Base::Reply" in content, f"Parent reference to Reply not correctly defined in {file_name}"
