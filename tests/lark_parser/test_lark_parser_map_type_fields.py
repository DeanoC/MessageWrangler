from lark_parser import parse_message_dsl
from lark import Tree

def find_message(tree: Tree, name: str):
    # Recursively search for a message node with the given name
    if tree.data == 'message':
        for child in tree.children:
            if isinstance(child, str) and child == name:
                return tree
    for child in tree.children:
        if isinstance(child, Tree):
            result = find_message(child, name)
            if result:
                return result
    return None

def find_field(tree: Tree, field_name: str):
    # Recursively search for a field node with the given name
    if tree.data == 'field':
        for child in tree.children:
            if isinstance(child, str) and child == field_name:
                return tree
    for child in tree.children:
        if isinstance(child, Tree):
            result = find_field(child, field_name)
            if result:
                return result
    return None

def test_map_type_fields_parsed_correctly():
    dsl = '''
    message WithMap {
        dict: Map<string, int>
        objMap: Map<string, Vec3>
    }
    message Vec3 {
        x: float
        y: float
        z: float
    }
    '''
    tree = parse_message_dsl(dsl)
    msg = find_message(tree, 'WithMap')
    assert msg is not None, "WithMap message not found"
    dict_field = find_field(msg, 'dict')
    objmap_field = find_field(msg, 'objMap')
    assert dict_field is not None, "dict field not found"
    assert objmap_field is not None, "objMap field not found"
    # Check that the type_def child is a map_type and print its children for debugging
    def extract_map_types(field_tree):
        from lark import Tree
        for child in field_tree.children:
            if isinstance(child, Tree) and child.data == 'type_def':
                for t in child.children:
                    if isinstance(t, Tree) and t.data == 'map_type':
                        # map_type.children: [map_key_type, map_value_type]
                        key_type_node = t.children[0].children[0]  # map_key_type -> basic_type
                        value_type_node = t.children[1].children[0].children[0]  # map_value_type -> type_def -> (basic_type|ref_type)
                        return key_type_node, value_type_node
        return None, None
    dict_key, dict_value = extract_map_types(dict_field)
    objmap_key, objmap_value = extract_map_types(objmap_field)
    assert dict_key is not None and dict_value is not None, "dict map_type not parsed"
    assert objmap_key is not None and objmap_value is not None, "objMap map_type not parsed"
    # Check key and value types
    from lark import Token
    assert getattr(dict_key, 'data', None) == 'basic_type', f"dict key type not basic_type: {dict_key}"
    assert dict_key.children[0] == Token('BASIC_TYPE', 'string'), f"dict key type not string: {dict_key.children[0]}"
    assert getattr(dict_value, 'data', None) == 'ref_type' or getattr(dict_value, 'data', None) == 'basic_type', f"dict value type not basic_type or ref_type: {dict_value}"
    # For dict, value should be int
    if getattr(dict_value, 'data', None) == 'ref_type':
        # Should be qualified_name_with_dot -> int
        assert dict_value.children[0].children[0] == Token('NAME', 'int'), f"dict value type not int: {dict_value.children[0].children[0]}"
    else:
        assert dict_value.children[0] == Token('BASIC_TYPE', 'int'), f"dict value type not int: {dict_value.children[0]}"
    assert getattr(objmap_key, 'data', None) == 'basic_type', f"objMap key type not basic_type: {objmap_key}"
    assert objmap_key.children[0] == Token('BASIC_TYPE', 'string'), f"objMap key type not string: {objmap_key.children[0]}"
    assert getattr(objmap_value, 'data', None) == 'ref_type', f"objMap value type not ref_type: {objmap_value}"
    # objMap value type should be Vec3
    assert objmap_value.children[0].children[0] == Token('NAME', 'Vec3'), f"objMap value type not Vec3: {objmap_value.children[0].children[0]}"
