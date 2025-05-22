import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree

@pytest.mark.parametrize("dsl,expected_modifiers", [
    # Single modifier
    ("""
    message Foo {
        optional a: int32
        repeated b: string
        required c: float
    }
    """, [
        ["optional"],
        ["repeated"],
        ["required"]
    ]),
    # Multiple modifiers (if grammar allows, e.g. 'optional repeated')
    ("""
    message Bar {
        optional repeated a: int32
        repeated optional b: string
    }
    """, [
        ["optional", "repeated"],
        ["repeated", "optional"]
    ]),
    # No modifier
    ("""
    message Baz {
        a: int32
        b: string
    }
    """, [
        [],
        []
    ]),
    # Edge: modifier with doc comment
    ("""
    message Qux {
        /// This is a doc comment
        optional a: int32
    }
    """, [
        ["optional"]
    ]),
])
def test_field_modifiers(dsl, expected_modifiers):
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree, "test")
    # Get the first message in the model
    msg = next(iter(model.messages.values()))
    for field, expected in zip(msg.fields, expected_modifiers):
        assert field.modifiers == expected, f"Expected {expected} for field {field.name}, got {field.modifiers}"
