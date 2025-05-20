"""
Tests for options_def and option values in build_model_from_lark_tree.
"""
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree

def test_options_def_basic():
    dsl = '''
    /// Options for color
    options ColorOptions {
        /// Red value
        RED = 1,
        GREEN = 2,
        /// Blue value
        BLUE = 3
    }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
    # Should be able to retrieve options by name
    opts = getattr(model, 'options', None)
    assert opts is not None
    color = opts.get("ColorOptions")
    assert color is not None
    assert color['description'].strip().startswith("/// Options for color")
    assert [v['name'] for v in color['values']] == ["RED", "GREEN", "BLUE"]
    assert [v['value'] for v in color['values']] == [1, 2, 3]
    assert color['values'][0]['description'].strip().startswith("/// Red value")
    assert color['values'][2]['description'].strip().startswith("/// Blue value")

def test_options_def_with_namespace():
    dsl = '''
    namespace Foo {
        options Bar {
            X = 1,
            Y = 2
        }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
    opts = getattr(model, 'options', None)
    assert opts is not None
    bar = opts.get("Foo::Bar")
    assert bar is not None
    assert [v['name'] for v in bar['values']] == ["X", "Y"]
