import os
import glob
import pytest
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from model_transforms.reserved_keyword_rename_transform import ReservedKeywordRenameTransform

def get_valid_def_files():
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]

@pytest.mark.parametrize("def_path", get_valid_def_files())
def test_reserved_keyword_rename_transform_on_defs(def_path):
    # Use a reserved set that will hit common names, e.g., 'base', 'main', 'class', 'def', 'return'
    reserved = {"base", "main", "class", "def", "return"}
    prefix = "gen_"
    early_model, _ = load_early_model_with_imports(def_path)
    model = EarlyModelToModelTransform().transform(early_model)
    transform = ReservedKeywordRenameTransform(reserved, prefix)
    model = transform.transform(model)
    # Check all namespaces, messages, enums, and fields for renamed reserved keywords
    for ns in model.namespaces:
        # Namespace name
        if ns.name in reserved:
            assert ns.name.startswith(prefix)
        # Messages
        for msg in getattr(ns, 'messages', []):
            if msg.name in reserved:
                assert msg.name.startswith(prefix)
            for field in getattr(msg, 'fields', []):
                if field.name in reserved:
                    assert field.name.startswith(prefix)
        # Enums
        for enum in getattr(ns, 'enums', []):
            if enum.name in reserved:
                assert enum.name.startswith(prefix)
            for value in getattr(enum, 'values', []):
                if value.name in reserved:
                    assert value.name.startswith(prefix)
