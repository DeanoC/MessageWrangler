import os
import pytest
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel
from model import FieldType

def test_enum_field_resolution_sh4c_comms():
    """
    This test ensures that fields like 'typeX' and 'mode' in sh4c_comms.def are resolved to the correct enum type
    in the Model, and not left as FieldType.STRING or with type_ref=None.
    """
    from model_debug import debug_print_early_model, debug_print_model
    comms_path = os.path.join(os.path.dirname(__file__), "../def", "sh4c_comms.def")
    early_comms, all_early_models = load_early_model_with_imports(comms_path)
    model_comms = EarlyModelToModel().process(early_comms)

    def find_namespace(ns_list, target):
        for ns in ns_list:
            if ns.name == target:
                return ns
            found = find_namespace(getattr(ns, 'namespaces', []), target)
            if found:
                return found
        return None
    try:
        client_ns = find_namespace(model_comms.namespaces, "ClientCommands")
        assert client_ns is not None, "ClientCommands namespace not found in sh4c_comms.def model"

        comm_command = None
        for msg in client_ns.messages:
            if msg.name == "CommCommand":
                comm_command = msg
        assert comm_command is not None, "CommCommand not found in sh4c_comms.def model"
        typex_field = next((f for f in comm_command.fields if f.name == "typeX"), None)
        assert typex_field is not None, "Field 'typeX' not found in CommCommand"
        assert typex_field.type == FieldType.ENUM, f"Field 'typeX' should be FieldType.ENUM, got {typex_field.type}"
        assert typex_field.type_ref is not None, "Field 'typeX' should have a resolved type_ref (ModelEnum)"
        assert hasattr(typex_field.type_ref, 'values') and typex_field.type_ref.values, "Enum for 'typeX' should have values"

        for msg_name in ["ChangeMode", "ChangeModeReply"]:
            msg = next((m for m in client_ns.messages if m.name == msg_name), None)
            assert msg is not None, f"Message '{msg_name}' not found in ClientCommands"
            mode_field = next((f for f in msg.fields if f.name == "mode"), None)
            assert mode_field is not None, f"Field 'mode' not found in {msg_name}"
            assert mode_field.type == FieldType.ENUM, f"Field 'mode' in {msg_name} should be FieldType.ENUM, got {mode_field.type}"
            assert mode_field.type_ref is not None, f"Field 'mode' in {msg_name} should have a resolved type_ref (ModelEnum)"
            assert hasattr(mode_field.type_ref, 'values') and mode_field.type_ref.values, f"Enum for 'mode' in {msg_name} should have values"
    except AssertionError as e:
        print("\n[DEBUG] Assertion failed in test_enum_field_resolution_sh4c_comms:", e)
        print("\n[DEBUG] --- EarlyModel dump ---")
        debug_print_early_model(early_comms)
        print("\n[DEBUG] --- Model dump ---")
        debug_print_model(model_comms)
        raise

    # Also check ChangeMode and ChangeModeReply for 'mode' field
    for msg_name in ["ChangeMode", "ChangeModeReply"]:
        msg = next((m for m in client_ns.messages if m.name == msg_name), None)
        assert msg is not None, f"Message '{msg_name}' not found in ClientCommands"
        mode_field = next((f for f in msg.fields if f.name == "mode"), None)
        assert mode_field is not None, f"Field 'mode' not found in {msg_name}"
        assert mode_field.type == FieldType.ENUM, f"Field 'mode' in {msg_name} should be FieldType.ENUM, got {mode_field.type}"
        assert mode_field.type_ref is not None, f"Field 'mode' in {msg_name} should have a resolved type_ref (ModelEnum)"
        assert hasattr(mode_field.type_ref, 'values') and mode_field.type_ref.values, f"Enum for 'mode' in {msg_name} should have values"

def test_enum_field_resolution_inheritance():
    """
    This test ensures that enum inheritance across files (test_enum_inheritance.def) resolves the field type correctly.
    """
    from model_debug import debug_print_early_model, debug_print_model
    def_path = os.path.join(os.path.dirname(__file__), "../def", "test_enum_inheritance.def")
    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    def find_namespace(ns_list, target):
        for ns in ns_list:
            if ns.name == target:
                return ns
            found = find_namespace(getattr(ns, 'namespaces', []), target)
            if found:
                return found
        return None
    try:
        client_ns = find_namespace(model.namespaces, "ClientCommands")
        assert client_ns is not None, "ClientCommands namespace not found in test_enum_inheritance.def model"
        comm_command = next((m for m in client_ns.messages if m.name == "CommCommand"), None)
        assert comm_command is not None, "CommCommand not found in ClientCommands"
        typex_field = next((f for f in comm_command.fields if f.name == "typeX"), None)
        assert typex_field is not None, "Field 'typeX' not found in CommCommand"
        assert typex_field.type == FieldType.ENUM, f"Field 'typeX' should be FieldType.ENUM, got {typex_field.type}"
        assert typex_field.type_ref is not None, "Field 'typeX' should have a resolved type_ref (ModelEnum)"
        assert hasattr(typex_field.type_ref, 'values') and typex_field.type_ref.values, "Enum for 'typeX' should have values"
    except AssertionError as e:
        print("\n[DEBUG] Assertion failed in test_enum_field_resolution_inheritance:", e)
        print("\n[DEBUG] --- EarlyModel dump ---")
        debug_print_early_model(early_model)
        print("\n[DEBUG] --- Model dump ---")
        debug_print_model(model)
        raise
