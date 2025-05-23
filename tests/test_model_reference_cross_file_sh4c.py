import os
import pytest
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from model import ModelReference

def test_model_reference_resolution_sh4c():
    # Load sh4c_comms.def and all its imports using the correct pipeline
    comms_path = os.path.join(os.path.dirname(__file__), "def", "sh4c_comms.def")
    early_comms, all_early_models = load_early_model_with_imports(comms_path)

    # Assert that after full EarlyModel transformation, all aliases are set in early_comms.imports
    for import_path, alias in early_comms.imports_raw:
        key = alias if alias else import_path
        assert key in early_comms.imports, f"Missing import for key: {key}"
        imported_em = early_comms.imports[key]
        imported_ns_name = imported_em.namespaces[0].name
        # The imported namespace should be as defined in the imported file (not the alias)
        if alias:
            assert imported_ns_name != alias, (
                f"Imported namespace should not be renamed to alias. Got: {imported_ns_name}, alias: {alias}"
            )
            # Simulate what Model.resolve_reference will do: substitute alias for real namespace
            ref_qfn = f"{alias}::Command"
            real_qfn = f"{imported_ns_name}::Command"
            print(f"    [DEBUG] Reference using alias: {ref_qfn} should resolve to: {real_qfn}")

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
    comm_command = None
    for msg in client_ns.messages:
        if msg.name == "CommCommand":
            comm_command = msg
    assert comm_command is not None, "CommCommand not found in sh4c_comms.def model"
    assert comm_command.parent is not None, "CommCommand should have a parent reference"
    # The parent reference should resolve to Command in sh4c_base.def
    resolved = model_comms.resolve_reference(comm_command.parent)
    assert resolved is not None, "Failed to resolve parent reference across files (sh4c)"
    assert getattr(resolved, "name", None) == "Command"
    # Also check that a non-existent reference returns None
    bad_ref = ModelReference(qfn="NonexistentNS::Nope", kind="message")
    assert model_comms.resolve_reference(bad_ref) is None
