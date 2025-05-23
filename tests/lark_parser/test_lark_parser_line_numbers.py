from lark_parser import parse_message_dsl

def test_field_line_numbers():
    dsl = '''
    message Foo {
        a: int
        b: string
    }
    '''
    tree = parse_message_dsl(dsl)
    # Find all field nodes and check their line numbers
    def find_fields(t):
        fields = []
        if hasattr(t, 'data') and t.data == 'field':
            fields.append(t)
        for child in getattr(t, 'children', []):
            if hasattr(child, 'data') or hasattr(child, 'children'):
                fields.extend(find_fields(child))
        return fields
    fields = find_fields(tree)
    assert fields, 'No fields found in tree!'
    for f in fields:
        assert hasattr(f, 'line'), f'Field node missing line attribute: {f}'
        assert isinstance(f.line, int) and f.line > 0, f'Field node has invalid line number: {f.line}'
