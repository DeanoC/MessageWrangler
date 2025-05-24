
import pytest
from lark_parser import parse_message_dsl

def test_simple_enum():
    text = '''
    message Foo {
        status: enum { OK = 0, ERROR = 1 }
    }
    '''
    tree = parse_message_dsl(text)
    # Check that the parse tree contains expected nodes
    assert 'message' in tree.pretty(), tree.pretty()
    assert 'enum_type' in tree.pretty(), tree.pretty()
    assert 'enum_value' in tree.pretty(), tree.pretty()

def test_multiline_compound():
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
    # Check that the parse tree contains compound_type and component names
    assert 'compound_type' in tree.pretty(), tree.pretty()
    assert 'x' in tree.pretty(), tree.pretty()
    assert 'y' in tree.pretty(), tree.pretty()
    assert 'z' in tree.pretty(), tree.pretty()
    assert 'color' in tree.pretty(), tree.pretty()
    assert 'r' in tree.pretty(), tree.pretty()
    assert 'g' in tree.pretty(), tree.pretty()
    assert 'b' in tree.pretty(), tree.pretty()
    assert 'a' in tree.pretty(), tree.pretty()

if __name__ == "__main__":
    pytest.main([__file__])
