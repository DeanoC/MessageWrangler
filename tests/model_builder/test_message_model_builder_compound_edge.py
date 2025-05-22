import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree

# Edge case: compound field with no components (should error or handle gracefully)
def test_compound_field_no_components():
    dsl = """
    message Test {
        empty: float { } // Invalid: no components
    }
    """
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree, "test")
    msg = model.get_message("Test")
    field = msg.fields[0]
    assert field.field_type.name == "COMPOUND"
    assert field.compound_base_type == "float"
    assert field.compound_components == []

# Edge case: compound field with duplicate component names
def test_compound_field_duplicate_components():
    dsl = """
    message Test {
        pos: float { x, y, x }
    }
    """
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree, "test")
    msg = model.get_message("Test")
    field = msg.fields[0]
    assert field.field_type.name == "COMPOUND"
    assert field.compound_base_type == "float"
    assert field.compound_components == ["x", "y", "x"]

# Edge case: compound field with unusual base type (should be UNKNOWN or error)
def test_compound_field_unusual_base_type():
    dsl = """
    message Test {
        weird: notatype { a, b }
    }
    """
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree, "test")
    msg = model.get_message("Test")
    field = msg.fields[0]
    assert field.field_type.name == "COMPOUND"
    # Should be UNKNOWN or 'notatype' depending on grammar
    assert field.compound_base_type in ("notatype", "UNKNOWN")
    assert field.compound_components == ["a", "b"]

# Edge case: compound field with whitespace and comments in components
def test_compound_field_with_comments_and_whitespace():
    dsl = """
    message Test {
        pos: float { x, /* comment */ y, z } // should ignore comments
    }
    """
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree, "test")
    msg = model.get_message("Test")
    field = msg.fields[0]
    assert field.field_type.name == "COMPOUND"
    assert field.compound_base_type == "float"
    assert "x" in field.compound_components and "y" in field.compound_components and "z" in field.compound_components
    assert len(field.compound_components) == 3
