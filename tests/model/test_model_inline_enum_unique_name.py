from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel
from model_transforms.assign_unique_names_transform import AssignUniqueNamesTransform
import os

def test_inline_enum_unique_name():
    # Use sh4c_base.def which has an inline enum in Command.type
    base_path = os.path.join(os.path.dirname(__file__), "../def", "sh4c_base.def")
    early_model, _ = load_early_model_with_imports(base_path)
    model = EarlyModelToModel().process(early_model)
    model = AssignUniqueNamesTransform().transform(model)
    # Find the Command_type enum
    def find_enum_by_unique_name(model, unique_name):
        for ns in model.namespaces:
            for enum in ns.enums:
                if getattr(enum, 'unique_name', None) == unique_name:
                    return enum
        return None
    # The unique_name will be prefixed with the file-level namespace (e.g., sh4c_base_Command_type)
    expected_unique_name = "sh4c_base_Command_type"
    enum = find_enum_by_unique_name(model, expected_unique_name)
    assert enum is not None, f"Inline enum Command_type should be present as a top-level enum with unique_name {expected_unique_name}"
    assert enum.name == "Command_type", f"Enum name should be Command_type, got {enum.name}"
    assert hasattr(enum, 'unique_name') and enum.unique_name == expected_unique_name
