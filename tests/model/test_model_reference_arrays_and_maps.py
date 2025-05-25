import os
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform
from earlymodel_to_model import EarlyModelToModel
from model import FieldType, ModelReference

def test_model_reference_arrays_and_maps():
    def_file = os.path.join(os.path.dirname(__file__), "../def", "test_arrays_and_references.def")
    with open(def_file, 'r', encoding='utf-8') as f:
        text = f.read()
    file_namespace = os.path.splitext(os.path.basename(def_file))[0]
    tree = parse_message_dsl(text)
    early_model = _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file)
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModel().process(early_model)

    # Find WithMap message
    with_map = None
    for ns in model.namespaces:
        for msg in ns.messages:
            if msg.name == "WithMap":
                with_map = msg
    assert with_map is not None, "WithMap message not found"
    dict_field = next(f for f in with_map.fields if f.name == "dict")
    obj_map_field = next(f for f in with_map.fields if f.name == "objMap")

    # Check dict field: should be [MAP, STRING, INT]
    assert dict_field.field_types[0] == FieldType.MAP, f"dict type[0] should be MAP, got {dict_field.field_types[0]}"
    assert dict_field.field_types[1] == FieldType.STRING, f"dict type[1] should be STRING, got {dict_field.field_types[1]}"
    assert dict_field.field_types[2] == FieldType.INT, f"dict type[2] should be INT, got {dict_field.field_types[2]}"

    # Check objMap field: should be [MAP, STRING, MESSAGE]
    assert obj_map_field.field_types[0] == FieldType.MAP, f"objMap type[0] should be MAP, got {obj_map_field.field_types[0]}"
    assert obj_map_field.field_types[1] == FieldType.STRING, f"objMap type[1] should be STRING, got {obj_map_field.field_types[1]}"
    assert obj_map_field.field_types[2] == FieldType.MESSAGE, f"objMap type[2] should be MESSAGE, got {obj_map_field.field_types[2]}"
    assert isinstance(obj_map_field.type_refs[2], ModelReference), f"objMap type[2] should be ModelReference, got {type(obj_map_field.type_refs[2])}"
    assert obj_map_field.type_refs[2].qfn.endswith("Vec3"), f"objMap type[2] qfn should end with Vec3, got {obj_map_field.type_refs[2].qfn}"
    assert obj_map_field.type_refs[2].kind == "message"

if __name__ == "__main__":
    test_model_reference_arrays_and_maps()
    print("Model reference arrays and maps test passed.")
