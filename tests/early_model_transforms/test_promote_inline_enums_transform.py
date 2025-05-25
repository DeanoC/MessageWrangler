def test_promote_inline_enums_promotes_inline_options():
    """
    Ensure that PromoteInlineEnumsTransform promotes inline options fields to top-level enums.
    """
    def_path = os.path.join(os.path.dirname(__file__), "..", "def", "test_pipe_options_fixed.def")
    from def_file_loader import load_def_file
    early_model = load_def_file(def_path)
    from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
    early_model = AddFileLevelNamespaceTransform().transform(early_model)
    # DEBUG: Print ModesAvailableReply.available field attributes before promotion
    def find_namespace(ns_list, target):
        for ns in ns_list:
            if ns.name == target:
                return ns
            nested = find_namespace(getattr(ns, 'namespaces', []), target)
            if nested:
                return nested
        return None
    client_ns_dbg = find_namespace(early_model.namespaces, "ClientCommands")
    if client_ns_dbg:
        modes_reply_dbg = None
        for msg in client_ns_dbg.messages:
            if msg.name == "ModesAvailableReply":
                modes_reply_dbg = msg
                break
        if modes_reply_dbg:
            for field in modes_reply_dbg.fields:
                if field.name == "available":
                    print(f"[DEBUG] Before promotion: available field is_inline_options={getattr(field, 'is_inline_options', None)}, inline_values_raw={getattr(field, 'inline_values_raw', None)}")
    early_model = PromoteInlineEnumsTransform().transform(early_model)
    # Find the ClientCommands namespace (search recursively)
    def find_namespace(ns_list, target):
        for ns in ns_list:
            if ns.name == target:
                return ns
            nested = find_namespace(getattr(ns, 'namespaces', []), target)
            if nested:
                return nested
        return None
    client_ns = find_namespace(early_model.namespaces, "ClientCommands")
    assert client_ns is not None, "ClientCommands namespace not found"
    # Look for promoted enum for ModesAvailableReply.available
    found = False
    for enum in getattr(client_ns, 'enums', []):
        if enum.name == "ModesAvailableReplyAvailable":
            found = True
            # Should have values Live, Replay, Editor
            value_names = [v.name for v in enum.values]
            assert set(value_names) == {"Live", "Replay", "Editor"}, f"Enum values: {value_names}"
    assert found, "Promoted enum ModesAvailableReplyAvailable not found in ClientCommands namespace"
    # Check that the ModesAvailableReply.available field type_name is set to the promoted enum
    modes_reply = None
    for msg in client_ns.messages:
        if msg.name == "ModesAvailableReply":
            modes_reply = msg
            break
    assert modes_reply is not None, "ModesAvailableReply message not found"
    available_field = None
    for field in modes_reply.fields:
        if field.name == "available":
            available_field = field
            break
    assert available_field is not None, "Field 'available' not found in ModesAvailableReply"
    assert available_field.type_name == "ModesAvailableReplyAvailable", f"Field type_name: {available_field.type_name}"
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
