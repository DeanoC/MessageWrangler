import os
from tests.test_utils import load_early_model_with_imports
import pytest

def test_imported_file_level_namespace_present():
    """
    Ensure that every imported EarlyModel has a file-level namespace present, even if the imported file declares no explicit namespace.
    This is critical for alias mapping and QFN resolution in downstream transforms.
    """
    def_path = os.path.join(os.path.dirname(__file__), "../def", "sh4c_comms.def")
    early_model, all_models = load_early_model_with_imports(def_path)
    # Check all imports
    for key, imported in early_model.imports.items():
        assert imported is not None, f"Import {key} not attached"
        assert hasattr(imported, "namespaces"), f"Imported model {key} missing namespaces"
        assert len(imported.namespaces) > 0, f"Imported model {key} has no namespaces (should have file-level namespace)"
        # The file-level namespace name should match the file stem
        file_stem = os.path.splitext(os.path.basename(imported.file))[0]
        file_ns = imported.namespaces[0]
        assert file_ns.name == file_stem, f"Imported model {key} file-level namespace name '{file_ns.name}' does not match file stem '{file_stem}'"

if __name__ == "__main__":
    test_imported_file_level_namespace_present()
    print("EarlyModel import file-level namespace test passed.")
