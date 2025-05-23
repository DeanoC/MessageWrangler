"""
Corner case tests for options_def and option values in build_model_from_lark_tree.
"""
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_model_from_lark_tree
from def_file_loader import build_model_from_file_recursive

def test_options_def_empty():
    dsl = '''
    options EmptyOptions { }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    opts = getattr(model, 'options', None)
    assert opts is not None
    # Always use the fully qualified name for options (global: just name, namespaced: Namespace::Name)
    empty = opts.get("EmptyOptions")  # Global options: no namespace
    assert empty is not None
    assert empty['values'] == []

def test_options_def_with_comments_only():
    dsl = '''
    /// Option set with only comments
    options OnlyComments {
        /// This is a comment
        // Another comment
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    opts = getattr(model, 'options', None)
    assert opts is not None
    only = opts.get("OnlyComments")  # Global options: no namespace
    assert only is not None
    assert only['values'] == []
    assert only['description'].strip().startswith("/// Option set with only comments")

def test_options_def_with_trailing_comma():
    dsl = '''
    options TrailingComma {
        X = 1,
        Y = 2,
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    opts = getattr(model, 'options', None)
    assert opts is not None
    trailing = opts.get("TrailingComma")  # Global options: no namespace
    assert trailing is not None
    assert [v['name'] for v in trailing['values']] == ["X", "Y"]
    assert [v['value'] for v in trailing['values']] == [1, 2]

def test_options_def_with_interleaved_comments():
    dsl = '''
    options Interleaved {
        /// First value
        A = 10,
        // Inline comment
        /// Second value
        B = 20
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    opts = getattr(model, 'options', None)
    assert opts is not None
    inter = opts.get("Interleaved")  # Global options: no namespace
    assert inter is not None
    assert [v['name'] for v in inter['values']] == ["A", "B"]
    assert [v['value'] for v in inter['values']] == [10, 20]
    assert inter['values'][0]['description'].strip().startswith("/// First value")
    assert inter['values'][1]['description'].strip().startswith("/// Second value")

def test_options_def_with_namespace_and_comments():
    dsl = '''
    namespace Edge {
        /// Options with namespace and comments
        options NSOptions {
            /// X value
            X = 1,
            // Y comment
            Y = 2
        }
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    opts = getattr(model, 'options', None)
    assert opts is not None
    nsopts = opts.get("Edge::NSOptions")  # Namespaced options: Namespace::Name
    assert nsopts is not None
    assert [v['name'] for v in nsopts['values']] == ["X", "Y"]
    assert [v['value'] for v in nsopts['values']] == [1, 2]
    assert nsopts['values'][0]['description'].strip().startswith("/// X value")
    assert nsopts['description'].strip().startswith("/// Options with namespace and comments")
