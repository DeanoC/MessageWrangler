import os
import json
import glob
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import _build_model_from_lark_tree
from generators.json_generator import generate_json_schema

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
    with open(def_path, "r", encoding="utf-8") as f:
        dsl = f.read()
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree)
    schema = generate_json_schema(model)
    # Validate the generated schema itself
    jsonschema.Draft7Validator.check_schema(schema)
    # Optionally, check that all message definitions are present in the schema
    for msg in model.messages.values():
        assert msg.name in schema["definitions"], f"Message {msg.name} missing in schema for {def_path}"
    # Optionally, check that all enums are present
    for enum in model.enums.values():
        assert enum.name in schema["definitions"], f"Enum {enum.name} missing in schema for {def_path}"
