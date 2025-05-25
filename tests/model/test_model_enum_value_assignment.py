import os
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel
from model_transforms.assign_enum_values_transform import AssignEnumValuesTransform

def test_enum_value_assignment_inheritance():
    # Use sh4c_comms.def which has enum inheritance and explicit/implicit values
    comms_path = os.path.join(os.path.dirname(__file__), "../def", "sh4c_comms.def")
    early_comms, all_early_models = load_early_model_with_imports(comms_path)
    model_comms = EarlyModelToModel().process(early_comms)
    model_comms = AssignEnumValuesTransform().transform(model_comms)

    # Find ClientCommands namespace
    def find_namespace(ns_list, target):
        for ns in ns_list:
            if ns.name == target:
                return ns
            found = find_namespace(getattr(ns, 'namespaces', []), target)
            if found:
                return found
        return None
    client_ns = find_namespace(model_comms.namespaces, "ClientCommands")
    assert client_ns is not None, "ClientCommands namespace not found"

    # Find Command enum in ClientCommands
    command_enum = None
    for enum in client_ns.enums:
        if enum.name == "Command":
            command_enum = enum
    assert command_enum is not None, "Command enum not found in ClientCommands namespace"

    # Check values and assignments
    value_map = {v.name: v.value for v in command_enum.values}
    assert value_map["ChangeMode"] == 1000, f"ChangeMode value is {value_map['ChangeMode']}, expected 1000"
    assert value_map["ModesAvailable"] == 1001, f"ModesAvailable value is {value_map['ModesAvailable']}, expected 1001"
    # Parent value should also be present
    assert "Status" in value_map, "Inherited value 'Status' missing from child enum"
    # Status should have value 0 (from parent)
    assert value_map["Status"] == 0, f"Status value is {value_map['Status']}, expected 0"
