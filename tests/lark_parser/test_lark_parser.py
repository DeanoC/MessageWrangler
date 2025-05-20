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

if __name__ == "__main__":
    pytest.main([__file__])
