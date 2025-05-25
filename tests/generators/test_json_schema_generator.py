
import os
import glob
import pytest
from generators.json_schema_generator import generate_json_schema
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel


try:
    import jsonschema
except ImportError:
    jsonschema = None

def get_def_files():
    # Only include .def files that are expected to be valid for schema generation
    # Exclude known invalid/negative test files
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema package not installed")
@pytest.mark.parametrize("def_path", get_def_files())
def test_json_schema_generation_and_validation(def_path):
    # Step 1: Load and resolve EarlyModel (with imports)
    early_model, _ = load_early_model_with_imports(def_path)
    # Step 2: Convert to generator-ready Model
    model = EarlyModelToModel().process(early_model)
    # Step 3: Generate JSON schema
    schema = generate_json_schema(model)
    # Step 4: Validate the generated schema itself
    jsonschema.Draft7Validator.check_schema(schema)
    # Step 5: Check that all message and enum definitions are present in the schema
    # Messages
    for ns in model.namespaces:
        for msg in getattr(ns, 'messages', []):
            assert msg.name in schema["definitions"], f"Message {msg.name} missing in schema for {def_path}"
        for enum in getattr(ns, 'enums', []):
            assert enum.name in schema["definitions"], f"Enum {enum.name} missing in schema for {def_path}"

    # Write schema to generated/json_schema for visual inspection
    import json
    import os
    out_dir = os.path.join("generated", "json_schema")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(def_path))[0]
    out_path = os.path.join(out_dir, f"{base}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
