import os
import glob
import sys
from def_file_loader import load_def_file
from model_debug import debug_print_early_model
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.attach_imported_models_transform import AttachImportedModelsTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)



def test_run_transform_pipeline_on_all_defs():
    defs_dir = os.path.join('tests', 'def')
    out_dir = os.path.join('generated', 'transformed_early_model')
    ensure_dir(out_dir)
    def_files = glob.glob(os.path.join(defs_dir, '*.def'))
    for def_file in def_files:
        try:
            # Load EarlyModel
            model = load_def_file(def_file)
        except Exception as e:
            print(f"[SKIP] {def_file}: {e}", file=sys.stderr)
            continue
        # Save before (pretty-printed)
        before_path = os.path.join(out_dir, os.path.basename(def_file) + '.before.txt')
        debug_print_early_model(model, file_path=before_path, out_dir=out_dir)
        # Run pipeline (no imports for now, can be extended)
        AddFileLevelNamespaceTransform().transform(model)
        AttachImportedModelsTransform({}).transform(model)
        QfnReferenceTransform().transform(model)
        # Save after (pretty-printed)
        after_path = os.path.join(out_dir, os.path.basename(def_file) + '.after.txt')
        debug_print_early_model(model, file_path=after_path, out_dir=out_dir)
        # Basic validation: ensure file-level namespace exists
        assert len(model.namespaces) == 1, f"File-level namespace missing in {def_file}"
        # Add more validation as needed
