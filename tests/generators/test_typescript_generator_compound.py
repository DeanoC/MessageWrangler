import os
import glob
import pytest
from generators.typescript_generator import generate_typescript_code
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel

def get_compound_def_files():
    # Only include .def files that are expected to contain compound fields
    # This can be expanded as needed
    return [
        os.path.join("tests", "def", "test_multiline.def"),
        os.path.join("tests", "def", "test_multiline_root.def"),
        os.path.join("tests", "def", "test_optional.def"),
        os.path.join("tests", "def", "test_namespaces.def"),
        os.path.join("tests", "def", "test_messages.def"),
    ]

@pytest.mark.parametrize("def_path", get_compound_def_files())
def test_typescript_generator_no_any_for_compound(def_path):
    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    ts_code = generate_typescript_code(model)
    output_dir = os.path.join("generated", "typescript")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(def_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.ts")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_code)
    # Check for any usage of 'any' or 'any[]' in the output
    with open(output_path, "r", encoding="utf-8") as f:
        ts_out = f.read()
    for line in ts_out.splitlines():
        assert ": any" not in line and ": any[]" not in line, f"Type 'any' found in generated TypeScript: {line} in {output_path}. Compound types must be explicit."
    # Check that all compound fields are present and have a concrete type (not 'any')
    for line in ts_out.splitlines():
        if '{' in line and 'Compound' in line:
            assert 'any' not in line, f"Compound type field uses 'any': {line} in {output_path}"
