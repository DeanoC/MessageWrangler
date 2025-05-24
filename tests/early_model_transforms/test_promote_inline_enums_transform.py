from early_model import EarlyModel
from early_model_transforms.promote_inline_enums_transform import PromoteInlineEnumsTransform
from tests.test_utils import load_early_model_with_imports
import os
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform

def test_promote_inline_enums_removes_all_inline_enums():
    # Use sh4c_base.def which has an inline enum in Command.type
    base_path = os.path.join(os.path.dirname(__file__), "../def", "sh4c_base.def")
    from def_file_loader import load_def_file
    # Load the raw EarlyModel (no transforms)
    early_model = load_def_file(base_path)
    # Apply the file-level namespace transform
    early_model = AddFileLevelNamespaceTransform().transform(early_model)
    # Sanity check: there is at least one inline enum after file-level namespace transform
    found_inline = False
    for ns in early_model.namespaces:
        for msg in ns.messages:
            for field in msg.fields:
                if getattr(field, 'is_inline_enum', False):
                    found_inline = True
    assert found_inline, "Should have at least one inline enum before transform"
    # Apply transform
    early_model = PromoteInlineEnumsTransform().transform(early_model)
    # After transform, there should be no inline enums
    for ns in early_model.namespaces:
        for msg in ns.messages:
            for field in msg.fields:
                assert not getattr(field, 'is_inline_enum', False), f"Field {field.name} in {msg.name} should not be inline enum after transform"
                assert not getattr(field, 'inline_values_raw', None), f"Field {field.name} in {msg.name} should not have inline_values_raw after transform"
    # The promoted enum should exist in the namespace
    found_promoted = False
    for ns in early_model.namespaces:
        for enum in ns.enums:
            if enum.name == "Command_type":
                found_promoted = True
    assert found_promoted, "Promoted inline enum Command_type should exist as a top-level enum"
