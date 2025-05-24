import os
import pytest
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from model import ModelReference

def test_model_enum_inheritance_inline_cross_file():
    # Load sh4c_comms.def and all its imports using the correct pipeline
    comms_path = os.path.join(os.path.dirname(__file__), "../def", "sh4c_comms.def")
    early_comms, all_early_models = load_early_model_with_imports(comms_path)
    model_comms = EarlyModelToModelTransform().transform(early_comms)

    # Recursively find ClientCommands namespace
    def find_namespace(ns_list, target):
        for ns in ns_list:
            if ns.name == target:
                return ns
            found = find_namespace(getattr(ns, 'namespaces', []), target)
            if found:
                return found
        return None
    client_ns = find_namespace(model_comms.namespaces, "ClientCommands")
    assert client_ns is not None, "ClientCommands namespace not found in sh4c_comms.def model"

    # Find Command enum in ClientCommands
    command_enum = None
    for enum in client_ns.enums:
        if enum.name == "Command":
            command_enum = enum
    assert command_enum is not None, "Command enum not found in ClientCommands namespace"
    # The parent should be resolved and come from sh4c_base.def (inline enum in Command message)
    assert command_enum.parent is not None, "Command enum should have a parent (inherited from base)"
    parent_enum = command_enum.parent
    # The parent enum should have a file attribute pointing to sh4c_base.def
    assert parent_enum.file and parent_enum.file.endswith("sh4c_base.def"), \
        f"Parent enum file is {parent_enum.file}, expected to end with sh4c_base.def"
    # The parent enum (promoted from inline field 'type' in message 'Command')
    # should now have a name like 'Command_type' (or similar, depending on promotion naming).
    assert parent_enum.name == "Command_type", f"Parent enum name is '{parent_enum.name}', expected 'Command_type' after promotion."
    # The parent enum should have at least one value (Status)
    assert any(v.name == "Status" for v in parent_enum.values), "Parent enum should have value 'Status'"
    # The child enum should inherit values from the parent
    child_value_names = [v.name for v in command_enum.values]
    assert "ChangeMode" in child_value_names and "ModesAvailable" in child_value_names, "Child enum missing expected values"
