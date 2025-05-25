import os
import re
import pytest
from generators.typescript_generator import generate_typescript_code
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel

def test_typescript_generator_outputs_inline_enum_for_options():
    """
    Ensure that for test_pipe_options_fixed.def, the generated TypeScript includes
    a real enum for ModesAvailableReplyAvailable with bitflag values for inline options.
    """
    def_path = os.path.join("tests", "def", "test_pipe_options_fixed.def")
    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    ts_code = generate_typescript_code(model)
    # Write the generated TypeScript code to a temp file
    output_dir = os.path.join("generated", "typescript")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "test_pipe_options_fixed.ts")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_code)
    # Read the generated TypeScript output
    with open(output_path, "r", encoding="utf-8") as f:
        ts_out = f.read()
    # Check for the correct enum declaration with bitflag values
    enum_match = re.search(r"export enum ModesAvailableReplyAvailable \{([^}]*)\}", ts_out, re.DOTALL)
    assert enum_match, "ModesAvailableReplyAvailable enum not found."
    enum_body = enum_match.group(1)
    # Should contain bitflag values for Live, Replay, Editor
    assert "Live = 1" in enum_body, "Live bitflag missing in ModesAvailableReplyAvailable."
    assert "Replay = 2" in enum_body, "Replay bitflag missing in ModesAvailableReplyAvailable."
    assert "Editor = 4" in enum_body, "Editor bitflag missing in ModesAvailableReplyAvailable."
