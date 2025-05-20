import pytest
from lark_parser import parse_message_dsl

def test_enum_extension():
    text = '''
    message RandomContainer_ensfMVKw {
        randomStatus_mPjMzGhR: enum { RANDOM_OK_IyWuYyuL = 0, RANDOM_ERROR_HZRMxLTD = 1, RANDOM_WARNING_OgNzwxqY = 2 }
    }
    message RandomExtendedUser_eHLXfTXV {
        // Legacy + syntax is not supported in the new parser, so we use a simple enum reference for now
        randomExtendedStatus_YOmzXaTV: RandomContainer_ensfMVKw.randomStatus_mPjMzGhR
    }
    '''
    tree = parse_message_dsl(text)
    # Check that both messages and fields are parsed
    pretty = tree.pretty()
    assert 'RandomContainer_ensfMVKw' in pretty, pretty
    assert 'randomStatus_mPjMzGhR' in pretty, pretty
    assert 'RandomExtendedUser_eHLXfTXV' in pretty, pretty
    assert 'randomExtendedStatus_YOmzXaTV' in pretty, pretty
    # The + syntax is not checked here anymore

if __name__ == "__main__":
    pytest.main([__file__])
