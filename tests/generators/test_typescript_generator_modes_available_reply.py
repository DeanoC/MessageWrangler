import os
import re
import pytest

GENERATED_TS_PATH = os.path.join(
    os.path.dirname(__file__), '../../generated/typescript/test_pipe_options_fixed.ts'
)

def test_typescript_generator_modes_available_reply_defined():
    """
    This test checks that the TypeScript generator does not emit an undefined reference
    for ModesAvailableReply_available in the generated output.
    """
    assert os.path.exists(GENERATED_TS_PATH), f"Generated file not found: {GENERATED_TS_PATH}"
    with open(GENERATED_TS_PATH, encoding='utf-8') as f:
        ts_code = f.read()
    # Check that ModesAvailableReply_available is defined as an interface, type, or enum
    defined = re.search(r'(interface|type|enum)\s+ModesAvailableReply_available', ts_code)
    # Check for usage
    used = re.search(r'available:\s*ModesAvailableReply_available', ts_code)
    assert not (used and not defined), (
        "ModesAvailableReply_available is referenced but not defined in the generated TypeScript. "
        "The generator should not emit undefined types."
    )
