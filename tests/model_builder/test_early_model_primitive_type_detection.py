import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree

def test_early_model_detects_primitive_type():
    dsl = '''
    message Vec3 {
        x: float
        y: float
        z: float
    }
    '''
    tree = parse_message_dsl(dsl)
    early_model = _build_early_model_from_lark_tree(tree, "test_primitive_type")
    # Search both namespaces and top-level messages for Vec3
    vec3 = None
    for ns in early_model.namespaces:
        for msg in ns.messages:
            if msg.name == "Vec3":
                vec3 = msg
                break
    if not vec3:
        for msg in getattr(early_model, 'messages', []):
            if msg.name == "Vec3":
                vec3 = msg
                break
    assert vec3 is not None, "Vec3 message not found in EarlyModel"
    for field in vec3.fields:
        assert field.type_name == "float"
        # This should be 'primitive' or 'float', not 'ref_type'
        assert getattr(field, 'type_type', None) == 'primitive', f"Expected type_type='primitive' for float, got {getattr(field, 'type_type', None)}"
