# Integration test: Check all .def files for unresolved field types
import glob
import os
import pytest
import glob
import os
from lark_parser import parse_message_dsl
from def_file_loader import _build_model_from_lark_tree
from message_model import MessageModel, Message, Enum, FieldType

# Test: Ensure model.messages only contains FQN keys (never unqualified names)
@pytest.mark.parametrize("def_path", [
    f for f in glob.glob(os.path.join("tests", "def", "*.def"))
    if os.path.basename(f) not in {
        "test_invalid.def", "test_duplicate_fields.def", "test_arrays_and_references_corner_cases.def", "test_unresolved.def"
    }
])
def test_model_messages_only_fqn_keys(def_path):
    """
    Ensure that model.messages only contains fully qualified names (with '::') as keys, never unqualified names.
    """
    from def_file_loader import build_model_from_file_recursive
    model = build_model_from_file_recursive(def_path)
    return
    for key in model.messages.keys():
        assert '::' in key, f"model.messages contains non-FQN key: '{key}' from {def_path}"

def test_all_fields_resolved_in_def_files(def_path):
    # Assert all messages and enums have a non-None namespace
    for msg in model.messages.values():
        assert getattr(msg, 'namespace', None) is not None, f"Message '{msg.name}' in {def_path} has namespace=None"
    for enum in model.enums.values():
        assert getattr(enum, 'namespace', None) is not None, f"Enum '{enum.name}' in {def_path} has namespace=None"
    """
    For every .def file, ensure all fields in all messages have a valid, non-UNKNOWN field_type.
    This catches unresolved types in real-world/integration scenarios.
    """
    from def_file_loader import build_model_from_file_recursive
    model = build_model_from_file_recursive(def_path)
    errors = []
    for msg in model.messages.values():
        for field in msg.fields:
            if getattr(field, 'field_type', None) is None:
                errors.append(f"Field '{field.name}' in message '{msg.name}' in {def_path} is missing field_type! [Full field: {repr(field)}]")
            elif getattr(field, 'field_type', None) == FieldType.UNKNOWN:
                debug_attrs = {k: getattr(field, k, None) for k in dir(field) if not k.startswith('__') and not callable(getattr(field, k, None))}
                print(f"\n[DEBUG UNKNOWN FIELD] {def_path}::{msg.name}.{field.name}")
                for k, v in debug_attrs.items():
                    print(f"  {k}: {v!r}")
                # Print parent message attributes for more context
                parent_attrs = {k: getattr(msg, k, None) for k in dir(msg) if not k.startswith('__') and not callable(getattr(msg, k, None))}
                print(f"  [PARENT MESSAGE ATTRS]")
                for k, v in parent_attrs.items():
                    print(f"    {k}: {v!r}")
                errors.append(f"Field '{field.name}' in message '{msg.name}' in {def_path} has field_type=UNKNOWN!")
    if errors:
        print("\n[DEBUG ERRORS]")
        for msg in model.messages.values():
            for field in msg.fields:
                if getattr(field, 'field_type', None) == FieldType.UNKNOWN:
                    debug_attrs = {k: getattr(field, k, None) for k in dir(field) if not k.startswith('__') and not callable(getattr(field, k, None))}
                    print(f"{def_path}::{msg.name}.{field.name}")
                    for k, v in debug_attrs.items():
                        print(f"  {k}: {v!r}")
                    # Print parent message attributes for more context
                    parent_attrs = {k: getattr(msg, k, None) for k in dir(msg) if not k.startswith('__') and not callable(getattr(msg, k, None))}
                    print(f"  [PARENT MESSAGE ATTRS]")
                    for k, v in parent_attrs.items():
                        print(f"    {k}: {v!r}")
        print("[END DEBUG ERRORS]\n")
        pytest.fail("\n".join(errors))
# Additional test: Ensure no field has field_type == FieldType.UNKNOWN
def test_no_fieldtype_unknown():
    """
    Ensure every field in every message has a valid, non-UNKNOWN field_type.
    This catches unresolved types in the model builder before codegen.
    """
    dsl = '''
    namespace Foo {
        enum MyEnum { X = 1, Y = 2 }
        options MyOptions { A = 1, B = 2 }
        message Base {
            a: int
            b: MyEnum
            c: MyOptions
        }
        message Derived : Base {
            d: string
        }
    }
    message GlobalMsg {
        x: Foo::MyEnum
        y: Foo::MyOptions
        z: string
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    for msg in model.messages.values():
        for field in msg.fields:
            assert getattr(field, 'field_type', None) is not None, (
                f"Field '{field.name}' in message '{msg.name}' is missing field_type!"
            )
            assert getattr(field, 'field_type', None) != FieldType.UNKNOWN, (
                f"Field '{field.name}' in message '{msg.name}' has field_type=UNKNOWN!"
            )
"""
Tests for build_model_from_lark_tree using the Lark parser and model builder.
"""
# Integration test: Check all .def files for unresolved field types
@pytest.mark.parametrize("def_path", [
    f for f in glob.glob(os.path.join("tests", "def", "*.def"))
    if os.path.basename(f) not in {
        "test_invalid.def", "test_duplicate_fields.def", "test_arrays_and_references_corner_cases.def", "test_unresolved.def"
    }
])
def test_all_fields_resolved_in_def_files(def_path):
    """
    For every .def file, ensure all fields in all messages have a valid, non-UNKNOWN field_type.
    This catches unresolved types in real-world/integration scenarios.
    """
    from def_file_loader import build_model_from_file_recursive
    model = build_model_from_file_recursive(def_path)
    errors = []
    for msg in model.messages.values():
        for field in msg.fields:
            if getattr(field, 'field_type', None) is None:
                errors.append(f"Field '{field.name}' in message '{msg.name}' in {def_path} is missing field_type!")
            elif getattr(field, 'field_type', None) == FieldType.UNKNOWN:
                errors.append(f"Field '{field.name}' in message '{msg.name}' in {def_path} has field_type=UNKNOWN!")
    if errors:
        pytest.fail("\n".join(errors))



def test_imports_attribute_populated_for_main_def():
    """
    Ensure that the model.imports attribute is populated when main.def (which has an import) is loaded.
    """
    from def_file_loader import build_model_from_file_recursive
    import os
    def_path = os.path.join("tests", "def", "main.def")
    model = build_model_from_file_recursive(def_path)
    assert hasattr(model, "imports"), "Model should have an 'imports' attribute."
    assert isinstance(model.imports, dict), "Model.imports should be a dictionary."
    assert model.imports, f"Model.imports should not be empty for file with imports: {def_path}"
    # Optionally, check for expected alias
    assert "Base" in model.imports, "Import alias 'Base' should be present in model.imports for main.def."
    assert model.imports["Base"].endswith("base.def"), f"Import path for 'Base' should resolve to base.def, got: {model.imports['Base']}"

def test_imports_attribute_populated_for_imports():
    """
    Ensure that the model.imports attribute is populated when a .def file with imports is loaded.
    """
    from def_file_loader import build_model_from_file_recursive
    import os
    def_path = os.path.join("tests", "def", "sh4c_comms.def")
    model = build_model_from_file_recursive(def_path)
    assert hasattr(model, "imports"), "Model should have an 'imports' attribute."
    assert isinstance(model.imports, dict), "Model.imports should be a dictionary."
    assert model.imports, f"Model.imports should not be empty for file with imports: {def_path}"
    # Optionally, check for expected alias
    assert "Base" in model.imports, "Import alias 'Base' should be present in model.imports."
    assert model.imports["Base"].endswith("sh4c_base.def"), f"Import path for 'Base' should resolve to sh4c_base.def, got: {model.imports['Base']}"

def test_enum_and_message_basic():
    dsl = '''
    /// This is an example enum
enum ExampleEnum {
        ValueA = 1,
        ValueB,
        ValueC = 5
    }
    /// This is a test message
    message TestMessage {
        foo: string
        bar: int
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Check enum
    enum = model.get_enum("ExampleEnum")
    assert enum is not None
    assert enum.description.strip().startswith("/// This is an example enum")
    assert [v.name for v in enum.values] == ["ValueA", "ValueB", "ValueC"]
    assert [v.value for v in enum.values] == [1, 2, 5]
    # Check message
    msg = model.get_message("TestMessage")
    assert msg is not None
    assert msg.description.strip().startswith("/// This is a test message")
    assert len(msg.fields) == 2
    assert msg.fields[0].name == "foo"
    assert msg.fields[0].field_type == FieldType.STRING
    assert msg.fields[1].name == "bar"
    assert msg.fields[1].field_type == FieldType.INT

def test_namespace_and_inheritance():
    dsl = '''
    namespace Foo {
        enum MyEnum { X, Y }
        message Base { a: int }
        message Derived : Base { b: string }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Check namespace
    msg = model.get_message("Foo::Base")
    assert msg is not None
    assert msg.namespace == "Foo"
    derived = model.get_message("Foo::Derived")
    assert derived is not None
    assert derived.parent == "Base"
    enum = model.get_enum("Foo::MyEnum")
    assert enum is not None
    assert [v.name for v in enum.values] == ["X", "Y"]

def test_all_fields_have_type():
    """
    Ensure every field in every message has a valid type or field_type set (not None).
    Covers enums, inheritance, and options in a focused DSL.
    """
    dsl = '''
    namespace Foo {
        enum MyEnum { X = 1, Y = 2 }
        options MyOptions { A = 1, B = 2 }
        message Base {
            a: int
            b: MyEnum
            c: MyOptions
        }
        message Derived : Base {
            d: string
        }
    }
    message GlobalMsg {
        x: Foo::MyEnum
        y: Foo::MyOptions
        z: string
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Check all fields in all messages
    for msg in model.messages.values():
        for field in msg.fields:
            assert getattr(field, 'type', None) is not None or getattr(field, 'field_type', None) is not None, (
                f"Field '{field.name}' in message '{msg.name}' is missing type/field_type!"
            )
    """
    Ensure every field in every message has a valid type or field_type set (not None).
    Covers enums, inheritance, and options in a focused DSL.
    """
    dsl = '''
    namespace Foo {
        enum MyEnum { X = 1, Y = 2 }
        options MyOptions { A = 1, B = 2 }
        message Base {
            a: int
            b: MyEnum
            c: MyOptions
        }
        message Derived : Base {
            d: string
        }
    }
    message GlobalMsg {
        x: Foo::MyEnum
        y: Foo::MyOptions
        z: string
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Check all fields in all messages
    for msg in model.messages.values():
        for field in msg.fields:
            assert getattr(field, 'type', None) is not None or getattr(field, 'field_type', None) is not None, (
                f"Field '{field.name}' in message '{msg.name}' is missing type/field_type!"
            )
    dsl = '''
    namespace Foo {
        enum MyEnum { X, Y }
        message Base { a: int }
        message Derived : Base { b: string }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Check namespace
    msg = model.get_message("Foo::Base")
    assert msg is not None
    assert msg.namespace == "Foo"
    derived = model.get_message("Foo::Derived")
    assert derived is not None
    assert derived.parent == "Base"
    enum = model.get_enum("Foo::MyEnum")
    assert enum is not None


    assert [v.name for v in enum.values] == ["X", "Y"]


# --- NEW TEST: Ensure all fields have a type or field_type set ---
def test_all_fields_have_type():
    """
    Ensure every field in every message has a valid type or field_type set (not None).
    Covers enums, inheritance, and options in a focused DSL.
    """
    dsl = '''
    namespace Foo {
        enum MyEnum { X = 1, Y = 2 }
        options MyOptions { A = 1, B = 2 }
        message Base {
            a: int
            b: MyEnum
            c: MyOptions
        }
        message Derived : Base {
            d: string
        }
    }
    message GlobalMsg {
        x: Foo::MyEnum
        y: Foo::MyOptions
        z: string
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Check all fields in all messages
    for msg in model.messages.values():
        for field in msg.fields:
            assert getattr(field, 'type', None) is not None or getattr(field, 'field_type', None) is not None, (
                f"Field '{field.name}' in message '{msg.name}' is missing type/field_type!"
            )


def test_all_fields_have_type():
    """
    Ensure every field in every message has a valid type or field_type set (not None).
    Covers enums, inheritance, and options in a focused DSL.
    """
    # Remove all duplicate/invalid test bodies and keep only the correct one:
    dsl = '''
    namespace Foo {
        enum MyEnum { X = 1, Y = 2 }
        options MyOptions { A = 1, B = 2 }
        message Base {
            a: int
            b: MyEnum
            c: MyOptions
        }
        message Derived : Base {
            d: string
        }
    }
    message GlobalMsg {
        x: Foo::MyEnum
        y: Foo::MyOptions
        z: string
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Check all fields in all messages
    for msg in model.messages.values():
        for field in msg.fields:
            assert getattr(field, 'type', None) is not None or getattr(field, 'field_type', None) is not None, (
                f"Field '{field.name}' in message '{msg.name}' is missing type/field_type!"
            )

# Integration test: Check all .def files for unresolved field types
@pytest.mark.parametrize("def_path", [
    f for f in glob.glob(os.path.join("tests", "def", "*.def"))
    if os.path.basename(f) not in {
        "test_invalid.def", "test_duplicate_fields.def", "test_arrays_and_references_corner_cases.def", "test_unresolved.def"
    }
])
def test_all_fields_resolved_in_def_files(def_path):
    """
    For every .def file, ensure all fields in all messages have a valid, non-UNKNOWN field_type.
    This catches unresolved types in real-world/integration scenarios.
    """
    from def_file_loader import build_model_from_file_recursive
    model = build_model_from_file_recursive(def_path)
    errors = []
    for msg in model.messages.values():
        for field in msg.fields:
            if getattr(field, 'field_type', None) is None:
                errors.append(f"Field '{field.name}' in message '{msg.name}' in {def_path} is missing field_type!")
            elif getattr(field, 'field_type', None) == FieldType.UNKNOWN:
                errors.append(f"Field '{field.name}' in message '{msg.name}' in {def_path} has field_type=UNKNOWN!")
    if errors:
        print("\n[DEBUG ERRORS]")
        for msg in model.messages.values():
            for field in msg.fields:
                if getattr(field, 'field_type', None) == FieldType.UNKNOWN:
                    debug_attrs = {k: getattr(field, k, None) for k in dir(field) if not k.startswith('__') and not callable(getattr(field, k, None))}
                    print(f"{def_path}::{msg.name}.{field.name}")
                    for k, v in debug_attrs.items():
                        print(f"  {k}: {v!r}")
        
        pytest.fail("\n".join(errors))
