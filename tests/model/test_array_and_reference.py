import os
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform
from earlymodel_to_model import EarlyModelToModel
from model import FieldType, ModelReference

def test_array_and_reference():
    def_file = os.path.join(os.path.dirname(__file__), "../def", "test_arrays_and_references.def")
    with open(def_file, 'r', encoding='utf-8') as f:
        text = f.read()
    file_namespace = os.path.splitext(os.path.basename(def_file))[0]
    tree = parse_message_dsl(text)
    early_model = _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file)
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModel().process(early_model)

    # Test RefTest message
    ref_test = None
    for ns in model.namespaces:
        for msg in ns.messages:
            if msg.name == "RefTest":
                ref_test = msg
    assert ref_test is not None, "RefTest message not found"
    ref_field = next(f for f in ref_test.fields if f.name == "ref")
    ref_array_field = next(f for f in ref_test.fields if f.name == "refArray")

    # ref should be a MESSAGE with ModelReference
    assert ref_field.field_types[0] == FieldType.MESSAGE, f"ref type should be MESSAGE, got {ref_field.field_types[0]}"
    assert isinstance(ref_field.type_refs[0], ModelReference), f"ref type_ref should be ModelReference, got {type(ref_field.type_refs[0])}"
    assert ref_field.type_refs[0].qfn.endswith("Vec3"), f"ref type_ref qfn should end with Vec3, got {ref_field.type_refs[0].qfn}"
    assert ref_field.type_refs[0].kind == "message"

    # refArray should be ARRAY of MESSAGE with ModelReference
    assert ref_array_field.field_types[0] == FieldType.ARRAY, f"refArray type[0] should be ARRAY, got {ref_array_field.field_types[0]}"
    assert ref_array_field.field_types[1] == FieldType.MESSAGE, f"refArray type[1] should be MESSAGE, got {ref_array_field.field_types[1]}"
    assert isinstance(ref_array_field.type_refs[1], ModelReference), f"refArray type_ref[1] should be ModelReference, got {type(ref_array_field.type_refs[1])}"
    assert ref_array_field.type_refs[1].qfn.endswith("Vec3"), f"refArray type_ref[1] qfn should end with Vec3, got {ref_array_field.type_refs[1].qfn}"
    assert ref_array_field.type_refs[1].kind == "message"

if __name__ == "__main__":
    test_array_and_reference()
    print("Array and reference test passed.")
