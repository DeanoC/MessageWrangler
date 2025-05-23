import os
from def_file_loader import load_def_file
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform

def main():
    comms_path = os.path.join(os.path.dirname(__file__), "def", "sh4c_comms.def")
    early_comms = load_def_file(comms_path)
    early_comms = AddFileLevelNamespaceTransform().transform(early_comms)
    early_comms = QfnReferenceTransform().transform(early_comms)
    print("imports_raw:", early_comms.imports_raw)
    print("imports keys:", list(early_comms.imports.keys()))
    for k, v in early_comms.imports.items():
        print(f"import key: {k}, file: {getattr(v, 'file', None)}")

if __name__ == "__main__":
    main()
