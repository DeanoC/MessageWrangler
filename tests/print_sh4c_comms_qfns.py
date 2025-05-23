from def_file_loader import load_def_file
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
import os

def print_model_qfns(def_path):
    early = load_def_file(def_path)
    early = AddFileLevelNamespaceTransform().transform(early)
    early = QfnReferenceTransform().transform(early)
    model = EarlyModelToModelTransform().transform(early)
    print(f"QFNs for {def_path}:")
    def walk_ns(ns, prefix):
        ns_qfn = '::'.join(prefix + [ns.name]) if ns.name else '::'.join(prefix)
        for msg in ns.messages:
            print(f"  MSG: {ns_qfn + '::' + msg.name if ns_qfn else msg.name}")
        for enum in ns.enums:
            print(f"  ENUM: {ns_qfn + '::' + enum.name if ns_qfn else enum.name}")
        for nested in ns.namespaces:
            walk_ns(nested, prefix + [ns.name] if ns.name else prefix)
    for ns in model.namespaces:
        walk_ns(ns, [])

if __name__ == "__main__":
    base_path = os.path.join(os.path.dirname(__file__), "def", "sh4c_base.def")
    comms_path = os.path.join(os.path.dirname(__file__), "def", "sh4c_comms.def")
    print_model_qfns(base_path)
    print_model_qfns(comms_path)
