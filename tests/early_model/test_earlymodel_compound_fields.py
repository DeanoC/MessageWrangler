import os
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree

def test_earlymodel_multiline_compound():
    text = '''
    message MultiLineCompoundTest {
        position: float {
            x,
            y,
            z
        };
        color: int {
            r,
            g,
            b,
            a
        };
    }
    '''
    tree = parse_message_dsl(text)
    early_model = _build_early_model_from_lark_tree(tree, "test_multiline_compound", source_file="test_multiline_compound.def")
    # Find the message
    msg = None
    for m in early_model.messages:
        if m.name == "MultiLineCompoundTest":
            msg = m
            break
    assert msg is not None, "MultiLineCompoundTest not found"
    # Check fields
    pos_field = next((f for f in msg.fields if f.name == "position"), None)
    color_field = next((f for f in msg.fields if f.name == "color"), None)
    assert pos_field is not None, "position field not found"
    assert color_field is not None, "color field not found"
    # Check compound base type and components
    assert getattr(pos_field, 'compound_base_type_raw', None) == 'float', f"Expected base type 'float', got {getattr(pos_field, 'compound_base_type_raw', None)}"
    assert getattr(color_field, 'compound_base_type_raw', None) == 'int', f"Expected base type 'int', got {getattr(color_field, 'compound_base_type_raw', None)}"
    assert getattr(pos_field, 'compound_components_raw', None) == ['x', 'y', 'z'], f"Expected components ['x','y','z'], got {getattr(pos_field, 'compound_components_raw', None)}"
    assert getattr(color_field, 'compound_components_raw', None) == ['r', 'g', 'b', 'a'], f"Expected components ['r','g','b','a'], got {getattr(color_field, 'compound_components_raw', None)}"

if __name__ == "__main__":
    pytest.main([__file__])
