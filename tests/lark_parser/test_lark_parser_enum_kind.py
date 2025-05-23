import pytest
from lark_parser import parse_message_dsl

def test_enum_kind_node_contains_token():
    text = '''
    enum TestEnum {
        Zero = 0,
        One = 1
    }
    open_enum TestOpenEnum {
        Zero = 0,
        One = 1
    }
    '''
    tree = parse_message_dsl(text)
    # Find all enum_def nodes
    enum_defs = [n for n in tree.iter_subtrees() if getattr(n, 'data', None) == 'enum_def']
    assert enum_defs, 'No enum_def nodes found!'
    for enum_def in enum_defs:
        # Find the enum_kind child
        enum_kind_nodes = [c for c in enum_def.children if hasattr(c, 'data') and c.data == 'enum_kind']
        assert enum_kind_nodes, f'No enum_kind node in enum_def: {enum_def.pretty()}'
        for ek in enum_kind_nodes:
            # The enum_kind node should have a Token child with value 'enum' or 'open_enum'
            token_children = [c for c in ek.children if hasattr(c, 'type')]
            assert token_children, f'enum_kind node has no token children: {ek.pretty()}'
            assert any(str(t) in ('enum', 'open_enum') for t in token_children), f'enum_kind token child is not enum/open_enum: {[str(t) for t in token_children]}'

if __name__ == "__main__":
    pytest.main([__file__])
