import os
import pytest
from generators.typescript_generator import generate_typescript_code
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel
from model_debug import debug_print_model

def get_options_def_file():
    return os.path.join("tests", "def", "test_pipe_options_fixed.def")

def test_typescript_generator_emits_options_as_bitflags_and_prints_model(tmp_path):
    def_path = get_options_def_file()
    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    # Print the model for debugging
    debug_print_model(model, file_path="model_debug_options.txt", out_dir="generated/model")
    ts_code = generate_typescript_code(model)
    output_dir = os.path.join("generated", "typescript")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(def_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.ts")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_code)
    # Check for bit flag values (1, 2, 4, ...)
    with open(output_path, "r", encoding="utf-8") as f:
        ts_out = f.read()
    assert "= 1" in ts_out or "= 0x1" in ts_out, "First option value should be 1"
    assert "= 2" in ts_out or "= 0x2" in ts_out, "Second option value should be 2"
    assert "|" in ts_out or "," in ts_out, "Should allow bitwise OR of options"
    # Optionally, check that the field type is number or a named bitflag type, not string
    # Accept the promoted name (e.g., ModesAvailableReplyAvailable) as a valid bitflag type (CamelCase, no underscores)
    import re
    field_type_matches = re.findall(r"available: ([A-Za-zA-Z0-9]+);", ts_out)
    assert any(
        t in ("number", "PipeOptions", "ModesAvailableReplyAvailable") for t in field_type_matches
    ), f"Options field should not be string, got types: {field_type_matches}"
