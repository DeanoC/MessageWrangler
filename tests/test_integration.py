"""
Integration Tests

This module contains integration tests for the message wrangler.
"""

import os
import pytest
import json

from message_wrangler import MessageFormatConverter


@pytest.mark.integration
def test_end_to_end(temp_dir):
    """Test the end-to-end process."""
    # Create a converter instance with path to test_messages.def in tests directory
    converter = MessageFormatConverter(os.path.join(os.path.dirname(__file__), "test_messages.def"), temp_dir)

    # Parse input file
    result = converter.parse_input_file()
    assert result

    # Generate C++ output
    result = converter.generate_cpp_output()
    assert result

    # Check that the C++ output file exists
    unreal_cpp_file = os.path.join(temp_dir, f"ue_{converter.output_name}_msgs.h")
    assert os.path.exists(unreal_cpp_file)

    # Generate TypeScript output
    result = converter.generate_typescript_output()
    assert result

    # Check that the TypeScript output file exists
    ts_file = os.path.join(temp_dir, f"{converter.output_name}_msgs.ts")
    assert os.path.exists(ts_file)

    # Generate JSON output
    result = converter.generate_json_output()
    assert result

    # Check that the JSON output file exists
    json_file = os.path.join(temp_dir, f"{converter.output_name}_msgs_schema.json")
    assert os.path.exists(json_file)

    # Read the C++ output file
    with open(unreal_cpp_file, 'r') as f:
        cpp_content = f.read()

    # Check C++ content more specifically
    # For Unreal C++ files, the namespace includes the ue_ prefix
    assert f"namespace ue_{converter.output_name}" in cpp_content
    # ToolToUnrealCmd
    assert "struct ToolToUnrealCmd" in cpp_content
    # Check for the multi-line enum definition
    assert "enum class ToolToUnrealCmd_command_Enum : uint8" in cpp_content
    assert "Ping = 0," in cpp_content
    assert "Position = 1," in cpp_content
    assert "ToolToUnrealCmd_command_Enum command;" in cpp_content
    assert "FString verb;" in cpp_content
    assert "FString actor;" in cpp_content
    # UnrealToToolCmdReply
    assert "struct UnrealToToolCmdReply" in cpp_content
    # Check for the multi-line enum definition
    assert "enum class UnrealToToolCmdReply_status_Enum : uint8" in cpp_content
    assert "OK = 0," in cpp_content
    assert "FAIL = 1," in cpp_content
    assert "UnrealToToolCmdReply_status_Enum status;" in cpp_content
    # UnrealToToolCmdUpdateReply
    assert "struct UnrealToToolCmdUpdateReply : public UnrealToToolCmdReply" in cpp_content
    # Check for the multi-line struct definition
    assert "struct {" in cpp_content  # Check for opening brace
    assert "float x;" in cpp_content  # Check for x component
    assert "float y;" in cpp_content  # Check for y component
    assert "float z;" in cpp_content  # Check for z component
    assert "} position;" in cpp_content  # Check for closing brace and name

    # Read the TypeScript output file
    with open(ts_file, 'r') as f:
        ts_content = f.read()

    # Check TypeScript content more specifically
    # The TypeScript generator might use either namespace or direct exports
    assert (f"export namespace {converter.output_name}" in ts_content or "export interface" in ts_content)
    # ToolToUnrealCmd
    # Check for multi-line enum definition
    assert "export enum ToolToUnrealCmd_command_Enum {" in ts_content
    assert "Ping = 0," in ts_content
    assert "Position = 1," in ts_content
    assert "}" in ts_content  # Closing brace for enum
    assert "export interface ToolToUnrealCmd" in ts_content
    assert "command: ToolToUnrealCmd_command_Enum;" in ts_content
    assert "verb: string;" in ts_content
    assert "actor: string;" in ts_content
    # UnrealToToolCmdReply
    # Check for multi-line enum definition
    assert "export enum UnrealToToolCmdReply_status_Enum {" in ts_content
    assert "OK = 0," in ts_content
    assert "FAIL = 1," in ts_content
    assert "}" in ts_content  # Closing brace for enum
    assert "export interface UnrealToToolCmdReply" in ts_content
    assert "status: UnrealToToolCmdReply_status_Enum;" in ts_content
    # UnrealToToolCmdUpdateReply
    assert "export interface UnrealToToolCmdUpdateReply extends UnrealToToolCmdReply" in ts_content
    # Check for multi-line compound type definition
    assert "position: {" in ts_content  # Check for opening brace
    assert "x: number;" in ts_content  # Check for x component
    assert "y: number;" in ts_content  # Check for y component
    assert "z: number;" in ts_content  # Check for z component
    assert "};" in ts_content  # Check for closing brace and semicolon
    # Type guards - they might have different formats in different versions
    assert "isToolToUnrealCmd" in ts_content
    assert "isUnrealToToolCmdReply" in ts_content
    assert "isUnrealToToolCmdUpdateReply" in ts_content

    # Read and parse the JSON output file
    with open(json_file, 'r') as f:
        json_content = json.load(f)

    # Check JSON content
    assert "$schema" in json_content  # Check it's a JSON schema
    assert "definitions" in json_content
    definitions = json_content["definitions"]
    assert len(definitions) == 3
    assert "ToolToUnrealCmd" in definitions
    assert "UnrealToToolCmdReply" in definitions
    assert "UnrealToToolCmdUpdateReply" in definitions

    # Check ToolToUnrealCmd in JSON Schema definitions
    msg1 = definitions["ToolToUnrealCmd"]
    assert msg1["type"] == "object"
    assert msg1["description"] == "This message is sent from the tool to Unreal Engine to issue a command."
    assert "properties" in msg1
    props1 = msg1["properties"]
    assert len(props1) == 3
    assert props1["command"]["description"] == "The type of command to execute."
    assert props1["command"]["type"] == "integer"  # Enum maps to integer in JSON schema
    assert props1["command"]["enum"] == [0, 1]
    assert props1["command"]["enumNames"] == ["Ping", "Position"]
    assert props1["verb"]["description"] == "The verb describing the action to perform."
    assert props1["verb"]["type"] == "string"
    assert props1["actor"]["description"] == "The actor on which to perform the action."
    assert props1["actor"]["type"] == "string"
    assert msg1["required"] == ["command", "verb", "actor"]

    # Check UnrealToToolCmdReply in JSON Schema definitions
    msg2 = definitions["UnrealToToolCmdReply"]
    assert msg2["type"] == "object"
    assert msg2["description"] == "This message is sent from Unreal Engine to the tool as a reply to a command."
    assert "properties" in msg2
    props2 = msg2["properties"]
    assert len(props2) == 1
    assert props2["status"]["description"] == "The status of the command execution."
    assert props2["status"]["type"] == "integer"
    assert props2["status"]["enum"] == [0, 1]
    assert props2["status"]["enumNames"] == ["OK", "FAIL"]
    assert msg2["required"] == ["status"]

    # Check UnrealToToolCmdUpdateReply in JSON Schema definitions
    msg3 = definitions["UnrealToToolCmdUpdateReply"]
    assert msg3["type"] == "object"
    # Description might have newline, check start only
    assert msg3["description"].startswith("This message is sent from Unreal Engine to the tool as a reply to a command")
    assert "properties" in msg3
    props3 = msg3["properties"]
    assert len(props3) == 1  # Only own properties listed here
    assert props3["position"]["description"] == "The position in 3D space."
    assert props3["position"]["type"] == "object"
    pos_props = props3["position"]["properties"]
    assert pos_props["x"]["type"] == "number"
    assert pos_props["y"]["type"] == "number"
    assert pos_props["z"]["type"] == "number"
    assert props3["position"]["required"] == ["x", "y", "z"]
    assert msg3["required"] == ["position"]
    assert "allOf" in msg3
    assert msg3["allOf"] == [{"$ref": "#/definitions/UnrealToToolCmdReply"}]
