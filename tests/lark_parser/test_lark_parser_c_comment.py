from lark_parser import parse_message_dsl
import pytest

def test_c_comment_in_message():
    dsl = '''
    /// Message with C-style comment
    message Test {
        pos: float { x, /* comment */ y, z }
    }
    '''
    tree = parse_message_dsl(dsl)
    # Should parse without error and produce a tree with a message and a field
    assert tree is not None
    # Optionally, check that the tree contains the expected structure
    # (not required for this smoke test)

def test_c_comment_alone():
    dsl = '''
    /* This is a C-style comment */
    message Test {
        a: int
    }
    '''
    tree = parse_message_dsl(dsl)
    assert tree is not None

@pytest.mark.parametrize("dsl", [
    "/* comment */ message X { a: int }",
    "message X { /* comment */ a: int }",
    "message X { a: int /* comment */ }",
    "message X { a: float { x, /* comment */ y } }",
])
def test_c_comment_various_locations(dsl):
    tree = parse_message_dsl(dsl)
    assert tree is not None
