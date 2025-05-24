import importlib.util
import os
import sys
import types
import pytest
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from generators.python3_generator import write_python3_files_for_model_and_imports, get_file_level_namespace_name

def import_generated_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def test_message_and_namespace_generation():
    def_path = os.path.join("tests", "def", "test_enum_numbering.def")
    early_model, _ = load_early_model_with_imports(def_path)
    model = EarlyModelToModelTransform().transform(early_model)
    out_dir = os.path.join("generated", "python3")
    write_python3_files_for_model_and_imports(model, out_dir)
    ns_name = get_file_level_namespace_name(model)
    py_path = os.path.join(out_dir, f"{ns_name}.py")
    assert os.path.exists(py_path)
    mod = import_generated_module(py_path, ns_name)
    # The top-level message should be a class in the module (not in a namespace)
    # But with the current generator, it will be inside a class named after the file-level namespace
    ns_class = getattr(mod, ns_name, None)
    assert ns_class is not None, f"Expected namespace class {ns_name}"
    # The message should be inside the namespace class
    msg_class = getattr(ns_class, "TestEnumNumbering", None)
    assert msg_class is not None, "TestEnumNumbering message class not found"
    # It should be a dataclass
    from dataclasses import is_dataclass
    assert is_dataclass(msg_class)
    # It should have the expected fields
    field_names = set(f.name for f in msg_class.__dataclass_fields__.values())
    expected_fields = {"explicitValues", "autoIncrement", "mixedAssignments", "negativeValues"}
    assert field_names == expected_fields, f"Fields: {field_names}"
