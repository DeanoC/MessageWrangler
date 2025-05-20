"""
Test compound field extraction in build_model_from_lark_tree with a minimal inline DSL.
"""
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from message_model import FieldType

def test_compound_field_minimal():
    dsl = '''
    /// Message with a compound field
    message Vec3Test {
        /// Position in 3D
        pos: float { x, y, z }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
    msg = model.get_message("Vec3Test")
    assert msg is not None
    field = next((f for f in msg.fields if f.name == "pos"), None)
    assert field is not None
    assert field.field_type == FieldType.COMPOUND
    assert field.compound_base_type == "float"
    assert field.compound_components == ["x", "y", "z"]

def test_compound_field_with_different_base():
    dsl = '''
    message ColorTest {
        color: int { r, g, b, a }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
    msg = model.get_message("ColorTest")
    assert msg is not None
    field = next((f for f in msg.fields if f.name == "color"), None)
    assert field is not None
    assert field.field_type == FieldType.COMPOUND
    assert field.compound_base_type == "int"
    assert field.compound_components == ["r", "g", "b", "a"]

def test_multiple_compound_fields():
    dsl = '''
    message MultiCompound {
        a: float { x, y }
        b: int { r, g, b }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
    msg = model.get_message("MultiCompound")
    assert msg is not None
    a = next((f for f in msg.fields if f.name == "a"), None)
    b = next((f for f in msg.fields if f.name == "b"), None)
    assert a is not None and b is not None
    assert a.field_type == FieldType.COMPOUND
    assert a.compound_base_type == "float"
    assert a.compound_components == ["x", "y"]
    assert b.field_type == FieldType.COMPOUND
    assert b.compound_base_type == "int"
    assert b.compound_components == ["r", "g", "b"]
