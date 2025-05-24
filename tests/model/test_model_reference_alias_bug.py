import os
import pytest
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from model import ModelReference

def test_model_reference_alias_bug():
    # Load sh4c_comms.def and all its imports using the correct pipeline
    comms_path = os.path.join(os.path.dirname(__file__), "../def", "sh4c_comms.def")
    early_comms, all_early_models = load_early_model_with_imports(comms_path)
    # Convert all EarlyModels to ModelNamespaces and merge
    from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
    all_namespaces = []
    merged_alias_map = {}
    merged_imports = {}
    for em in all_early_models.values():
        model = EarlyModelToModelTransform().transform(em)
        all_namespaces.extend(model.namespaces)
        # Merge alias_map and imports from each model
        if hasattr(model, 'alias_map') and model.alias_map:
            merged_alias_map.update(model.alias_map)
        if hasattr(model, 'imports') and model.imports:
            merged_imports.update(model.imports)
    # Build a Model with all namespaces and merged alias_map/imports
    from model import Model
    model_comms = Model(file=comms_path, namespaces=all_namespaces, alias_map=merged_alias_map, imports=merged_imports)

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
    comm_command = None
    for msg in client_ns.messages:
        if msg.name == "CommCommand":
            comm_command = msg
    assert comm_command is not None, "CommCommand not found in sh4c_comms.def model"
    assert comm_command.parent is not None, "CommCommand should have a parent reference"
    # The parent reference should resolve to Command in sh4c_base.def (after fix)
    resolved = model_comms.resolve_reference(comm_command.parent)
    assert resolved is not None, "BUG: resolve_reference should resolve alias QFN to the imported message!"
    assert getattr(resolved, "name", None) == "Command"
