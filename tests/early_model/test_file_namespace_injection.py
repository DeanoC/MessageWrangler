import os
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model import EarlyNamespace

def test_file_namespace_injection():
    def_file = os.path.join(os.path.dirname(__file__), "../def", "test_arrays_and_references.def")
    with open(def_file, 'r', encoding='utf-8') as f:
        text = f.read()
    file_namespace = os.path.splitext(os.path.basename(def_file))[0]
    tree = parse_message_dsl(text)
    early_model = _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file)
    AddFileLevelNamespaceTransform().transform(early_model)
    # There should be exactly one file-level namespace
    assert len(early_model.namespaces) == 1, f"Expected 1 file-level namespace, got {len(early_model.namespaces)}"
    file_ns = early_model.namespaces[0]
    # The file-level namespace should be named after the file
    assert file_ns.name == file_namespace, f"File-level namespace name should be '{file_namespace}', got '{file_ns.name}'"
    # All top-level messages should be inside the file-level namespace
    assert not early_model.messages, "Top-level messages should be moved into the file-level namespace"
    # All nested namespaces should be children of the file-level namespace
    for ns in file_ns.namespaces:
        assert isinstance(ns, EarlyNamespace), "Nested namespaces should be EarlyNamespace instances"
    print("File namespace injection test passed.")

if __name__ == "__main__":
    test_file_namespace_injection()
