import os
import glob
import pytest
from generators.python3_generator import generate_python3_code, write_python3_files_for_model_and_imports, get_file_level_namespace_name
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel

GENERATED_DIR = os.path.join("generated", "python3")
os.makedirs(GENERATED_DIR, exist_ok=True)

def get_def_files():
    # Only include .def files that are expected to be valid for code generation
    # Exclude known invalid/negative test files
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]

import importlib.util
import sys

@pytest.mark.parametrize("def_path", get_def_files())
def test_python3_generator_writes_files_for_imports(def_path):
    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    # Write all files for the root model and its imports
    write_python3_files_for_model_and_imports(model, GENERATED_DIR)
    # Collect all expected .py files (for root and all imports)
    def collect_all_models(m, seen=None):
        if seen is None:
            seen = set()
        result = []
        if id(m) in seen:
            return result
        seen.add(id(m))
        result.append(m)
        for imported in getattr(m, 'imports', {}).values():
            result.extend(collect_all_models(imported, seen))
        return result
    all_models = collect_all_models(model)
    for m in all_models:
        ns_name = get_file_level_namespace_name(m)
        out_path = os.path.join(GENERATED_DIR, f"{ns_name}.py")
        assert os.path.exists(out_path), f"Expected file {out_path} not found"
        assert os.path.getsize(out_path) > 0, f"File {out_path} is empty"

        # Specific check for test_arrays_and_references.py
        if ns_name == "test_arrays_and_references":
            with open(out_path, "r", encoding="utf-8") as f_gen:
                generated_content = f_gen.read()
            assert "ModelReference(" not in generated_content, \
                f"Generated file {out_path} unexpectedly contains 'ModelReference(' placeholder."

            # Check for correct type resolution instead of 'object' for various fields
            expected_types_and_fields = {
                "ref: Vec3": "RefTest.ref",
                "refArray: list[Vec3]": "RefTest.refArray",
                "nested: TestNS.Nested": "WithNamespaceRef.nested",
                "nestedArray: list[TestNS.Nested]": "WithNamespaceRef.nestedArray",
                "points: list[Vec3]": "WithArrays.points", # Assuming points are Vec3
                "objMap: dict[str, Vec3]": "WithMap.objMap" # Assuming objMap values are Vec3
            }

            for type_str, field_desc in expected_types_and_fields.items():
                assert type_str in generated_content, \
                    f"Generated file {out_path} expected to contain '{type_str}' for {field_desc}, but was not found. Found 'object' or other incorrect type."

            # Additionally, ensure the problematic 'object' types are NOT present for these specific fields.
            # This is a bit more brittle if field names are not unique, but good for these specific cases.
            problematic_object_hints = [
                "ref: object",
                "refArray: list[object]",
                "nested: object",
                "nestedArray: list[object]",
                "points: list[object]",
                "objMap: dict[str, object]"
            ]
            for problematic_hint in problematic_object_hints:
                assert problematic_hint not in generated_content, \
                    f"Generated file {out_path} unexpectedly contains '{problematic_hint}'. Specific type expected."

    # Special validation for sh4c_comms/sh4c_base
    if os.path.basename(def_path) == "sh4c_comms.def":
        # Use package-style import for generated modules
        import importlib
        import sys
        sys.path.insert(0, os.path.abspath(os.path.join(GENERATED_DIR, '..')))
        # Import as package: generated.python3.sh4c_base, generated.python3.sh4c_comms
        base_mod = importlib.import_module("generated.python3.sh4c_base")
        print(f"Imported base module: {base_mod}")
        print("Members of base_mod:")
        for name in dir(base_mod):
            print(f"  {name}")
        comms_mod = importlib.import_module("generated.python3.sh4c_comms")
        # Validate import statement
        comms_py_path = os.path.join(GENERATED_DIR, "sh4c_comms.py")
        with open(comms_py_path, encoding="utf-8") as f:
            contents = f.read()
        assert "from .sh4c_base import *" in contents, "Missing import for sh4c_base"
        assert ": Any" not in contents, \
            f"Generated file {comms_py_path} unexpectedly contains ': Any', indicating a lost type."
        # Validate enum inheritance and values (Pythonic nested structure)
        # Access enums as nested classes in the namespace structure
        cmd_enum = comms_mod.sh4c_comms.ClientCommands.Command
        base_enum = base_mod.sh4c_base.Command_type
        # Python Enum does not support subclassing, so check for intended inheritance comment and value overlap
        with open(comms_py_path, encoding="utf-8") as f:
            code = f.read()
        assert "Intended to inherit from sh4c_base_Command_type" in code or "Intended to inherit from sh4c_base.Command_type" in code, "Missing intended inheritance comment"
        # Check that enum values are present and correct
        assert cmd_enum.ChangeMode.value == 1000, f"ChangeMode value is {cmd_enum.ChangeMode.value}, expected 1000"
        assert cmd_enum.ModesAvailable.value == 1001, f"ModesAvailable value is {cmd_enum.ModesAvailable.value}, expected 1001"
        # Check that base enum values are present in the derived enum
        assert hasattr(cmd_enum, "ChangeMode")
        assert hasattr(cmd_enum, "ModesAvailable")
