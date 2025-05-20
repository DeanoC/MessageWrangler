from lark_parser import parse_message_dsl
import pytest

def test_enum_with_comments_and_trailing_comma():
    dsl = '''
    enum E {
        // comment before
        FIRST = 1, // comment after
        // another comment
        SECOND = 2, /* C-style comment */
    }
    '''
    tree = parse_message_dsl(dsl)
    assert tree is not None

def test_options_with_comments_and_trailing_comma():
    dsl = '''
    options Opt {
        // comment before
        FOO = 1, // comment after
        // another comment
        BAR = 2, /* C-style comment */
    }
    '''
    tree = parse_message_dsl(dsl)
    assert tree is not None

@pytest.mark.parametrize("dsl", [
    "enum E { /* comment */ FIRST = 1, SECOND = 2 }",
    "enum E { FIRST = 1 /* comment */, SECOND = 2 }",
    "enum E { FIRST = 1, /* comment */ SECOND = 2 }",
    "options O { /* comment */ FOO = 1, BAR = 2 }",
    "options O { FOO = 1 /* comment */, BAR = 2 }",
    "options O { FOO = 1, /* comment */ BAR = 2 }",
    "enum E { /* comment */ }",
    "options O { /* comment */ }",
])
def test_enum_option_comments_various(dsl):
    tree = parse_message_dsl(dsl)
    assert tree is not None
