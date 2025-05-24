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

def test_enum_generation_and_validation():
    def_path = os.path.join("tests", "def", "test_standalone_enum.def")
    early_model, _ = load_early_model_with_imports(def_path)
    model = EarlyModelToModelTransform().transform(early_model)
    out_dir = os.path.join("generated", "python3")
    write_python3_files_for_model_and_imports(model, out_dir)
    ns_name = get_file_level_namespace_name(model)
    py_path = os.path.join(out_dir, f"{ns_name}.py")
    assert os.path.exists(py_path)
    mod = import_generated_module(py_path, ns_name)
    # Validate enums
    # The enum name is now flattened: test_standalone_enum_TestEnum
    # Flat names for all enums
    assert hasattr(mod, "test_standalone_enum_TestEnum")
    enum_flat = getattr(mod, "test_standalone_enum_TestEnum")
    assert enum_flat.Zero.value == 0
    assert enum_flat.One.value == 1
    assert enum_flat.Two.value == 2
    assert hasattr(mod, "test_standalone_enum_TestOpenEnum")
    open_enum_flat = getattr(mod, "test_standalone_enum_TestOpenEnum")
    assert open_enum_flat.Zero.value == 0
    assert open_enum_flat.One.value == 1
    assert open_enum_flat.Two.value == 2
    assert hasattr(mod, "test_standalone_enum_TestEnumWithInheritance")
    inh_enum_flat = getattr(mod, "test_standalone_enum_TestEnumWithInheritance")
    assert inh_enum_flat.Three.value == 3
    assert inh_enum_flat.Four.value == 4
    assert hasattr(mod, "test_standalone_enum_TestMessage_enumField")
    msg_enum_flat = getattr(mod, "test_standalone_enum_TestMessage_enumField")
    assert msg_enum_flat.Zero.value == 0
    assert msg_enum_flat.One.value == 1
    assert msg_enum_flat.Two.value == 2
    assert hasattr(mod, "test_standalone_enum_TestNamespace_NamespacedEnum")
    ns_enum_flat = getattr(mod, "test_standalone_enum_TestNamespace_NamespacedEnum")
    assert ns_enum_flat.Zero.value == 0
    assert ns_enum_flat.One.value == 1
    assert ns_enum_flat.Two.value == 2
    # If NamespacedEnum is in a namespace class, check there
    if hasattr(mod, "TestNamespace"):
        ns = getattr(mod, "TestNamespace")
        assert hasattr(ns, "NamespacedEnum")
        assert ns.NamespacedEnum.Zero.value == 0
        assert ns.NamespacedEnum.One.value == 1
        assert ns.NamespacedEnum.Two.value == 2
    else:
        assert mod.NamespacedEnum.Zero.value == 0
        assert mod.NamespacedEnum.One.value == 1
        assert mod.NamespacedEnum.Two.value == 2
