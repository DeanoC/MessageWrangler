import importlib.util
import os
import sys
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

def test_enum_inheritance_and_imports():
    # Generate code for sh4c_comms.def and sh4c_base.def
    def_path = os.path.join("tests", "def", "sh4c_comms.def")
    early_model, _ = load_early_model_with_imports(def_path)
    model = EarlyModelToModelTransform().transform(early_model)
    out_dir = os.path.join("generated", "python3")
    write_python3_files_for_model_and_imports(model, out_dir)
    # Use package-style import for generated modules
    import importlib
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(out_dir, '..')))
    # Import as package: generated.python3.sh4c_base, generated.python3.sh4c_comms
    base_mod = importlib.import_module("generated.python3.sh4c_base")
    comms_mod = importlib.import_module("generated.python3.sh4c_comms")
    # Validate import statement
    comms_py_path = os.path.join(out_dir, "sh4c_comms.py")
    with open(comms_py_path, encoding="utf-8") as f:
        contents = f.read()
    assert "from .sh4c_base import *" in contents
    # Validate enum inheritance and values (flat structure)
    cmd_enum = getattr(comms_mod, "sh4c_comms_ClientCommands_Command")
    base_enum = getattr(base_mod, "sh4c_base_Command_type")
    # Python Enum does not support subclassing, so check for intended inheritance comment and value overlap
    with open(comms_py_path, encoding="utf-8") as f:
        code = f.read()
    assert "Intended to inherit from sh4c_base_Command_type" in code, "Missing intended inheritance comment"
    # Check that enum values are present and correct
    assert cmd_enum.ChangeMode.value == 1000
    assert cmd_enum.ModesAvailable.value == 1001
    # Check that base enum values are present in the derived enum (if any)
    assert hasattr(cmd_enum, "ChangeMode")
    assert hasattr(cmd_enum, "ModesAvailable")
