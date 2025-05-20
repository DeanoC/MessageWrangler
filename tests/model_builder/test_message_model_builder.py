"""
Tests for build_model_from_lark_tree using the Lark parser and model builder.
"""
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from message_model import MessageModel, Message, Enum, FieldType


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
    model = build_model_from_lark_tree(tree)
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
    model = build_model_from_lark_tree(tree)
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
