import os
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel
from model_transforms.assign_enum_values_transform import AssignEnumValuesTransform

def test_enum_value_names_are_unique_after_merging():
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

    # Ensure all value names are unique
    names = [v.name for v in command_enum.values]
    assert len(names) == len(set(names)), f"Enum value names are not unique: {names}"

def test_child_enum_illegal_duplicate_name():
    # Create a parent and child enum with duplicate value name
    from model import ModelEnum, ModelEnumValue, ModelNamespace, Model
    parent_enum = ModelEnum(
        name="Parent",
        values=[ModelEnumValue("Status", None)],
        is_open=False,
        parent=None
    )
    child_enum = ModelEnum(
        name="Child",
        values=[ModelEnumValue("Status", None)],
        is_open=False,
        parent=parent_enum
    )
    ns = ModelNamespace(name="TestNS", messages=[], enums=[child_enum], namespaces=[])
    model = Model(file="fake.def", namespaces=[ns])
    from model_transforms.assign_enum_values_transform import AssignEnumValuesTransform
    try:
        AssignEnumValuesTransform().transform(model)
    except ValueError as e:
        assert "illegally redefines value 'Status'" in str(e)
    else:
        assert False, "Expected ValueError for duplicate enum value name in child"
