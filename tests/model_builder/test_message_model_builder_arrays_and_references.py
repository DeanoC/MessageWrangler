from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from message_model import FieldType

def test_model_arrays_and_references():
    dsl = '''
    message Vec3 {
        x: float
        y: float
        z: float
    }
    message WithArrays {
        tags: string[]
        points: Vec3[]
        ids: int[]
    }
    message RefTest {
        ref: Vec3
        refArray: Vec3[]
    }
    namespace TestNS {
        message Nested {
            value: int
        }
    }
    message WithNamespaceRef {
        nested: TestNS::Nested
        nestedArray: TestNS::Nested[]
    }
    message WithMap {
        dict: Map<string, int>
        objMap: Map<string, Vec3>
    }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
    # Check array fields
    arr_msg = model.get_message("WithArrays")
    assert arr_msg is not None
    tags = next(f for f in arr_msg.fields if f.name == "tags")
    points = next(f for f in arr_msg.fields if f.name == "points")
    ids = next(f for f in arr_msg.fields if f.name == "ids")
    assert tags.is_array and tags.field_type == FieldType.STRING
    assert points.is_array and points.field_type == FieldType.MESSAGE_REFERENCE and points.message_reference == "Vec3"
    assert ids.is_array and ids.field_type == FieldType.INT
    # Check message reference
    ref_msg = model.get_message("RefTest")
    ref = next(f for f in ref_msg.fields if f.name == "ref")
    ref_array = next(f for f in ref_msg.fields if f.name == "refArray")
    assert ref.field_type == FieldType.MESSAGE_REFERENCE and ref.message_reference == "Vec3"
    assert ref_array.is_array and ref_array.field_type == FieldType.MESSAGE_REFERENCE and ref_array.message_reference == "Vec3"
    # Check namespace reference
    ns_msg = model.get_message("WithNamespaceRef")
    nested = next(f for f in ns_msg.fields if f.name == "nested")
    nested_array = next(f for f in ns_msg.fields if f.name == "nestedArray")
    assert nested.field_type == FieldType.MESSAGE_REFERENCE and nested.message_reference == "TestNS::Nested"
    assert nested_array.is_array and nested_array.field_type == FieldType.MESSAGE_REFERENCE and nested_array.message_reference == "TestNS::Nested"
    # Check map fields
    map_msg = model.get_message("WithMap")
    dict_field = next(f for f in map_msg.fields if f.name == "dict")
    obj_map_field = next(f for f in map_msg.fields if f.name == "objMap")
    assert dict_field.is_map and dict_field.map_key_type == "string"
    assert obj_map_field.is_map and obj_map_field.map_key_type == "string"

if __name__ == "__main__":
    test_model_arrays_and_references()
    print("Model test passed.")
