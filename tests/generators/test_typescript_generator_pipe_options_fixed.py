import os
import re
import pytest
from generators.typescript_generator import generate_typescript_code
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel

def test_typescript_generator_outputs_dummy_enum_for_options():
    """
    Ensure that for test_pipe_options_fixed.def, the generated TypeScript includes
    a dummy enum for ModesAvailableReplyAvailable and the field uses it as type.
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
    # Check for the dummy enum declaration
    assert "export enum ModesAvailableReplyAvailable { /* AUTO-GENERATED DUMMY */ }" in ts_out, "Dummy enum ModesAvailableReplyAvailable not found in output."
    # Check that the ModesAvailableReply interface uses the dummy enum as the type for 'available'
    interface_match = re.search(r"export interface ModesAvailableReply \{([^}]*)\}", ts_out, re.DOTALL)
    assert interface_match, "ModesAvailableReply interface not found."
    interface_body = interface_match.group(1)
    assert "available: ModesAvailableReplyAvailable;" in interface_body, "Field 'available' does not use ModesAvailableReplyAvailable as type."
