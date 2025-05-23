"""
Tests for enum inheritance in build_model_from_lark_tree.
"""
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_model_from_lark_tree
from def_file_loader import build_model_from_file_recursive

def test_enum_inheritance_simple():
    dsl = '''
    enum BaseEnum {
        A = 1,
        B = 2
    }
    enum ChildEnum : BaseEnum {
        C = 3
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    base = model.get_enum("BaseEnum")
    child = model.get_enum("ChildEnum")
    assert base is not None
    assert child is not None
    assert child.parent == "BaseEnum"
    assert [v.name for v in base.values] == ["A", "B"]
    assert [v.name for v in child.values] == ["C"]

def test_enum_inheritance_with_namespace():
    dsl = '''
    namespace Foo {
        enum Parent { X, Y }
        enum Sub : Parent { Z }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    parent = model.get_enum("Foo::Parent")
    sub = model.get_enum("Foo::Sub")
    assert parent is not None
    assert sub is not None
    assert sub.parent == "Parent"
    assert [v.name for v in parent.values] == ["X", "Y"]
    assert [v.name for v in sub.values] == ["Z"]
