import os
import pytest
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from model import ModelReference

def test_model_reference_resolution_across_files():
    # Load main.def and all its imports using the correct pipeline
    main_path = os.path.join(os.path.dirname(__file__), "def", "main.def")
    early_main, all_early_models = load_early_model_with_imports(main_path)


    # Assert that after full EarlyModel transformation, all aliases are set in early_main.imports
    print("[DEBUG] Aliases and imports in EarlyModel before Model conversion:")
    for import_path, alias in early_main.imports_raw:
        key = alias if alias else import_path
        assert key in early_main.imports, f"Missing import for key: {key}"
        imported_em = early_main.imports[key]
        print(f"    import key: {key}, namespaces: {[ns.name for ns in imported_em.namespaces]}")
        # The imported namespace should be as defined in the imported file (not the alias)
        imported_ns_name = imported_em.namespaces[0].name
        print(f"    [DEBUG] Imported file's top-level namespace: {imported_ns_name}")
        # The alias should be used for reference resolution, not for renaming the namespace
        if alias:
            # Simulate what Model.resolve_reference will do: substitute alias for real namespace
            # e.g., Base::AnotherBaseMessage should resolve to base::AnotherBaseMessage
            ref_qfn = f"{alias}::AnotherBaseMessage"
            real_qfn = f"{imported_ns_name}::AnotherBaseMessage"
            assert imported_ns_name != alias, (
                f"Imported namespace should not be renamed to alias. Got: {imported_ns_name}, alias: {alias}"
            )
            print(f"    [DEBUG] Reference using alias: {ref_qfn} should resolve to: {real_qfn}")

    from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
    model_main = EarlyModelToModelTransform().transform(early_main)

    # Debug: print the imports attached to the model
    print(f"[DEBUG] model_main.imports: {list(model_main.imports.keys())}")
    for k, v in model_main.imports.items():
        print(f"    import key: {k}, namespaces: {[ns.name for ns in v.namespaces]}")

    # Find DerivedMessage in main.def and resolve its parent reference
    derived = None
    for ns in model_main.namespaces:
        for msg in ns.messages:
            if msg.name == "DerivedMessage":
                derived = msg
    assert derived is not None, "DerivedMessage not found in main.def model"
    assert derived.parent is not None, "DerivedMessage should have a parent reference"
    # The parent reference should resolve to AnotherBaseMessage in base.def
    resolved = model_main.resolve_reference(derived.parent)
    assert resolved is not None, "Failed to resolve parent reference across files"
    assert getattr(resolved, "name", None) == "AnotherBaseMessage"
    # Also check that a non-existent reference returns None
    bad_ref = ModelReference(qfn="NonexistentNS::Nope", kind="message")
    assert model_main.resolve_reference(bad_ref) is None
