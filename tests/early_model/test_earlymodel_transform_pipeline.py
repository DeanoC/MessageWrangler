import os
from tests.test_utils import load_early_model_with_imports
import pytest

def test_transformed_earlymodel_qfns_and_imports():
    """
    Validate that after the full transform pipeline, the EarlyModel has correct QFNs and imports.
    """
    # Use the main.def and sh4c_comms.def as cross-file test cases
    test_cases = [
        ("main.def", "DerivedMessage", "AnotherBaseMessage"),
        ("sh4c_comms.def", "CommCommand", "Command"),
    ]
    for def_file, child_name, parent_name in test_cases:
        def_path = os.path.join(os.path.dirname(__file__), "../def", def_file)
        early_model, all_models = load_early_model_with_imports(def_path)

        # Check that all namespaces and messages have QFNs assigned
        def check_ns(ns, seen):
            assert hasattr(ns, "qfn"), f"Namespace {ns.name} missing qfn"
            seen.add(ns.qfn)
            for msg in getattr(ns, "messages", []):
                assert hasattr(msg, "qfn"), f"Message {msg.name} missing qfn"
                seen.add(msg.qfn)
            for nested in getattr(ns, "namespaces", []):
                check_ns(nested, seen)
        seen_qfns = set()
        for ns in early_model.namespaces:
            check_ns(ns, seen_qfns)
        # QFNs should be unique
        assert len(seen_qfns) == len(set(seen_qfns)), "QFNs are not unique in EarlyModel"

        # Check that imports are attached and correct
        for key, imported in early_model.imports.items():
            assert imported is not None, f"Import {key} not attached"
            # Optionally, check that imported EarlyModel has namespaces/messages
            assert hasattr(imported, "namespaces"), f"Imported model {key} missing namespaces"

        # Check that the child message has a parent reference string that matches the expected parent QFN
        def find_message(ns, name):
            for msg in getattr(ns, "messages", []):
                if msg.name == name:
                    return msg
            for nested in getattr(ns, "namespaces", []):
                found = find_message(nested, name)
                if found:
                    return found
            return None
        child_msg = None
        for ns in early_model.namespaces:
            child_msg = find_message(ns, child_name)
            if child_msg:
                break
        assert child_msg is not None, f"{child_name} not found in EarlyModel"
        assert hasattr(child_msg, "parent_raw"), f"{child_name} missing parent_raw"
        assert parent_name in child_msg.parent_raw, f"{child_name} parent_raw does not reference {parent_name}"

        # Optionally, check that all attached imports are also fully transformed
        for key, imported in early_model.imports.items():
            for ns in imported.namespaces:
                check_ns(ns, set())

if __name__ == "__main__":
    pytest.main([__file__])
