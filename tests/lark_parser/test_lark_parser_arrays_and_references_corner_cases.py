import pytest
from lark.exceptions import UnexpectedCharacters
from lark_parser import parse_message_dsl

def test_nested_array_parse_error():
    dsl = '''
    message InvalidNestedArray {
        nestedArray: string[][]
    }
    '''
    with pytest.raises(UnexpectedCharacters):
        parse_message_dsl(dsl)
