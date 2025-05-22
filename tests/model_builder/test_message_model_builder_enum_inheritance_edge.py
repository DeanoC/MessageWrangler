"""
Edge case tests for enum inheritance in build_model_from_lark_tree.
"""
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import _build_model_from_lark_tree

def test_enum_inheritance_chain():
    dsl = '''
    enum A { X = 1 }
    enum B : A { Y = 2 }
    enum C : B { Z = 3 }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    a = model.get_enum("A")
    b = model.get_enum("B")
    c = model.get_enum("C")
    assert a is not None and b is not None and c is not None
    assert b.parent == "A"
    assert c.parent == "B"
    assert [v.name for v in a.values] == ["X"]
    assert [v.name for v in b.values] == ["Y"]
    assert [v.name for v in c.values] == ["Z"]

def test_enum_inheritance_with_qualified_parent():
    dsl = '''
    namespace Foo {
        enum Base { A }
    }
    enum Child : Foo::Base { B }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    base = model.get_enum("Foo::Base")
    child = model.get_enum("Child")
    assert base is not None and child is not None
    assert child.parent == "Foo::Base"
    assert [v.name for v in base.values] == ["A"]
    assert [v.name for v in child.values] == ["B"]

def test_enum_inheritance_with_dot_qualified_parent():
    dsl = '''
    enum Outer { A }
    enum Inner : Outer.Base { B }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    outer = model.get_enum("Outer")
    inner = model.get_enum("Inner")
    assert outer is not None and inner is not None
    assert inner.parent == "Outer::Base"
    assert [v.name for v in outer.values] == ["A"]
    assert [v.name for v in inner.values] == ["B"]
