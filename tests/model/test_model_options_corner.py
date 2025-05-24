def get_option(model, name):
    for opt in getattr(model, 'options', []):
        if opt.name == name:
            return opt
    return None
"""
Ported corner case tests for options_def and option values in build_model_from_lark_tree.
"""
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform

def test_options_def_empty():
    dsl = '''
    options EmptyOptions { }
    '''
    tree = parse_message_dsl(dsl)
    early_model = _build_early_model_from_lark_tree(tree, "test")
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModelTransform().transform(early_model)
    opts = getattr(model, 'options', None)
    assert opts is not None
    empty = get_option(model, "EmptyOptions")
    assert empty is not None
    assert empty.values == []

def test_options_def_with_comments_only():
    dsl = '''
    /// Option set with only comments
    options OnlyComments {
        /// This is a comment
        // Another comment
    }
    '''
    tree = parse_message_dsl(dsl)
    early_model = _build_early_model_from_lark_tree(tree, "test")
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModelTransform().transform(early_model)
    opts = getattr(model, 'options', None)
    assert opts is not None
    only = get_option(model, "OnlyComments")
    assert only is not None
    assert only.values == []
    assert (only.doc or "").strip().startswith("/// Option set with only comments")

def test_options_def_with_trailing_comma():
    dsl = '''
    options TrailingComma {
        X = 1,
        Y = 2,
    }
    '''
    tree = parse_message_dsl(dsl)
    early_model = _build_early_model_from_lark_tree(tree, "test")
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModelTransform().transform(early_model)
    opts = getattr(model, 'options', None)
    assert opts is not None
    trailing = get_option(model, "TrailingComma")
    assert trailing is not None
    assert [v.name for v in trailing.values] == ["X", "Y"]
    assert [v.value for v in trailing.values] == [1, 2]

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
    early_model = _build_early_model_from_lark_tree(tree, "test")
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModelTransform().transform(early_model)
    opts = getattr(model, 'options', None)
    assert opts is not None
    inter = get_option(model, "Interleaved")
    assert inter is not None
    assert [v.name for v in inter.values] == ["A", "B"]
    assert [v.value for v in inter.values] == [10, 20]
    assert (inter.values[0].doc or "").strip().startswith("/// First value")
    assert (inter.values[1].doc or "").strip().startswith("/// Second value")

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
    early_model = _build_early_model_from_lark_tree(tree, "test")
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModelTransform().transform(early_model)
    opts = getattr(model, 'options', None)
    assert opts is not None
    nsopts = get_option(model, "Edge::NSOptions")
    assert nsopts is not None
    assert [v.name for v in nsopts.values] == ["X", "Y"]
    assert [v.value for v in nsopts.values] == [1, 2]
    assert (nsopts.values[0].doc or "").strip().startswith("/// X value")
    assert (nsopts.doc or "").strip().startswith("/// Options with namespace and comments")
