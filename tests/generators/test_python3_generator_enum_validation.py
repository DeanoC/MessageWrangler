import importlib.util
import os
import sys
import types
import pytest
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel
from generators.python3_generator import write_python3_files_for_model_and_imports, get_file_level_namespace_name

def import_generated_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def test_enum_generation_and_validation():
    def_path = os.path.join("tests", "def", "test_standalone_enum.def")
    early_model, _ = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    out_dir = os.path.join("generated", "python3")
    write_python3_files_for_model_and_imports(model, out_dir)
    ns_name = get_file_level_namespace_name(model)
    py_path = os.path.join(out_dir, f"{ns_name}.py")
    assert os.path.exists(py_path)
    mod = import_generated_module(py_path, ns_name)
    # Validate enums
    # The enum name is now flattened: test_standalone_enum_TestEnum
    # Flat names for all enums
    # All enums/messages are now inside the file-level namespace class
    ns = getattr(mod, "test_standalone_enum")
    assert hasattr(ns, "TestEnum")
    enum_nested = getattr(ns, "TestEnum")
    assert enum_nested.Zero.value == 0
    assert enum_nested.One.value == 1
    assert enum_nested.Two.value == 2
    assert hasattr(ns, "TestOpenEnum")
    open_enum_nested = getattr(ns, "TestOpenEnum")
    assert open_enum_nested.Zero.value == 0
    assert open_enum_nested.One.value == 1
    assert open_enum_nested.Two.value == 2
    assert hasattr(ns, "TestEnumWithInheritance")
    inh_enum_nested = getattr(ns, "TestEnumWithInheritance")
    assert inh_enum_nested.Three.value == 3
    assert inh_enum_nested.Four.value == 4
    assert hasattr(ns, "TestMessage_enumField")
    msg_enum_nested = getattr(ns, "TestMessage_enumField")
    assert msg_enum_nested.Zero.value == 0
    assert msg_enum_nested.One.value == 1
    assert msg_enum_nested.Two.value == 2
    assert hasattr(ns, "TestNamespace")
    ns2 = getattr(ns, "TestNamespace")
    assert hasattr(ns2, "NamespacedEnum")
    assert ns2.NamespacedEnum.Zero.value == 0
    assert ns2.NamespacedEnum.One.value == 1
    assert ns2.NamespacedEnum.Two.value == 2
