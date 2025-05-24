from def_file_loader import load_def_file
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
import os

def test_map_type_preservation():
    base_path = os.path.join(os.path.dirname(__file__), "../def", "test_arrays_and_references.def")
    early_model = load_def_file(base_path)
    early_model = AddFileLevelNamespaceTransform().transform(early_model)
    # Find WithMap message
    found = False
    for ns in early_model.namespaces:
        for msg in ns.messages:
            if msg.name == "WithMap":
                for field in msg.fields:
                    if field.name == "dict":
                        found = True
                        assert field.raw_type == "map_type" or field.type_type == "map_type", f"dict field raw_type/type_type: {field.raw_type}/{getattr(field, 'type_type', None)}"
                        assert field.map_key_type_raw == "string", f"dict field map_key_type_raw: {field.map_key_type_raw}"
                        assert field.map_value_type_raw == "int", f"dict field map_value_type_raw: {field.map_value_type_raw}"
                    if field.name == "objMap":
                        found = True
                        assert field.raw_type == "map_type" or field.type_type == "map_type", f"objMap field raw_type/type_type: {field.raw_type}/{getattr(field, 'type_type', None)}"
                        assert field.map_key_type_raw == "string", f"objMap field map_key_type_raw: {field.map_key_type_raw}"
                        assert field.map_value_type_raw == "Vec3", f"objMap field map_value_type_raw: {field.map_value_type_raw}"
    assert found, "WithMap message and its map fields should be found in EarlyModel"
