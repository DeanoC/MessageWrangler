import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree

@pytest.mark.parametrize("dsl, expected_docs", [
    # Simple case: doc comment directly before option value
    ("""
    options Opt {
        /// doc for FOO
        FOO = 1,
        /// doc for BAR
        BAR = 2
    }
    """, ["doc for FOO", "doc for BAR"]),
    # Interleaved comments: local and doc
    ("""
    options Opt {
        // local comment\n/// doc for FOO\nFOO = 1,
        /* c-style */
        /// doc for BAR
        BAR = 2
    }
    """, ["doc for FOO", "doc for BAR"]),
    # Doc comment as direct child (inline)
    ("""
    options Opt {
        FOO = 1, /// doc for FOO
        BAR = 2 /// doc for BAR
    }
    """, ["doc for FOO", "doc for BAR"]),
    # No doc comments
    ("""
    options Opt {
        FOO = 1,
        BAR = 2
    }
    """, ["", ""]),
])
def test_option_value_doc_extraction(dsl, expected_docs):
    tree = parse_message_dsl(dsl)
    print("[DEBUG] Parse tree:\n" + tree.pretty())
    early_model = _build_early_model_from_lark_tree(tree, current_processing_file_namespace="TestNS")
    # Find the options set
    opt = None
    for o in early_model.options:
        if o['name'] == "Opt":
            opt = o
            break
    assert opt is not None, "Options set 'Opt' not found"
    docs = [v['doc'].strip().replace("///", "").strip() if v.get('doc') else "" for v in opt['values_raw']]
    assert docs == expected_docs
