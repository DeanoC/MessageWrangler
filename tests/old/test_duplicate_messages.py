'''
Test Duplicate Messages

This module contains tests for the duplicate message detection.
It uses randomized names to ensure the test isn't passing due to hardcoded special cases.
'''

import os
import tempfile
import pytest
from message_parser_core import MessageParser
from tests.test_utils import generate_random_name

def test_duplicate_message_detection():
    '''Test detection of duplicate message definitions.'''
    # Generate random names for messages, fields, namespaces, and enum values
    base_command = f"RandomBaseCommand_{generate_random_name()}"
    base_reply = f"RandomBaseReply_{generate_random_name()}"
    client_commands = f"RandomClientCommands_{generate_random_name()}"
    change_mode = f"RandomChangeMode_{generate_random_name()}"

    type_field = f"randomType_{generate_random_name()}"
    key_field = f"randomKey_{generate_random_name()}"
    status_field = f"randomStatus_{generate_random_name()}"
    mode_field = f"randomMode_{generate_random_name()}"

    status_value = f"RANDOM_STATUS_{generate_random_name()}"
    success_value = f"RANDOM_SUCCESS_{generate_random_name()}"
    failure_value = f"RANDOM_FAILURE_{generate_random_name()}"
    pending_value = f"RANDOM_PENDING_{generate_random_name()}"
    live_value = f"RANDOM_LIVE_{generate_random_name()}"
    replay_value = f"RANDOM_REPLAY_{generate_random_name()}"
    editor_value = f"RANDOM_EDITOR_{generate_random_name()}"

    # Create a temporary file with randomized message definitions
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.def')
    temp_file_path = temp_file.name

    with open(temp_file_path, "w") as f:
        f.write(f"""/// Test file for duplicate message detection

/// Base message for all commands
message {base_command} {{
    /// The type of command
    field {type_field}: enum {{
        {status_value}
    }}
    field {key_field}: string
}}

/// Base message for all replies
message {base_reply} {{
    /// The status of the command execution
    field {status_field}: enum {{
        {success_value},
        {failure_value},
        {pending_value}
    }}
    field {key_field}: string
}}

/// Command the client can send to the server
namespace {client_commands} {{
    /// Client to server messages
    message {change_mode} : {base_command} {{
        field {mode_field}: enum {{
            /// Connect to the Unreal target through the server
            {live_value},
            /// Replay an previous Unreal session recorded by the server
            {replay_value},
            /// Connect to the Unreal Editor through the server
            {editor_value}
        }}
    }}

    /// Duplicate message definition in the same namespace
    message {change_mode} : {base_command} {{
        field {mode_field}: enum {{
            /// Connect to the Unreal target through the server
            {live_value},
            /// Replay an previous Unreal session recorded by the server
            {replay_value},
            /// Connect to the Unreal Editor through the server
            {editor_value}
        }}
    }}
}}
""")
    temp_file.close()

    try:
        # Parse the file
        parser = MessageParser(temp_file_path)
        model = parser.parse()

        # Check that there are errors
        assert parser.errors, "Expected parser errors for duplicate message definitions"

        # Check that the error message contains the expected text
        error_found = False
        expected_error = f"Duplicate message definition '{client_commands}::{change_mode}'"
        for error in parser.errors:
            if expected_error in error:
                error_found = True
                break

        assert error_found, f"Expected error message '{expected_error}' not found"

        # The model should be None because parsing failed
        assert model is None, "Expected model to be None when parsing fails"
    finally:
        # Clean up the temporary file
        os.remove(temp_file_path)
