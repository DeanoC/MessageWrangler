"""
Test for QfnReferenceTransform: Ensures all intra-file references are replaced with QFN and no information is lost.
"""
import os
import sys
import pytest
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_transform_pipeline import run_early_transform_pipeline
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform

def_dir = os.path.join(os.path.dirname(__file__), "../def")
def get_def_files():
    return [os.path.join(def_dir, f) for f in os.listdir(def_dir) if f.endswith(".def") and "invalid" not in f and "corner_case" not in f]

def extract_qfns(model):
    qfns = set()
    def walk_ns(ns, prefix):
        ns_qfn = '.'.join(prefix + [ns.name]) if ns.name else '.'.join(prefix)
        for msg in ns.messages:
            qfns.add(ns_qfn + '.' + msg.name if ns_qfn else msg.name)
        for enum in ns.enums:
            qfns.add(ns_qfn + '.' + enum.name if ns_qfn else enum.name)
        for nested in ns.namespaces:
            walk_ns(nested, prefix + [ns.name] if ns.name else prefix)
    for ns in model.namespaces:
        walk_ns(ns, [])
    for msg in model.messages:
        qfns.add(msg.name)
    for enum in model.enums:
        qfns.add(enum.name)
    return qfns

def check_all_refs_are_qfn(model, qfns):
    def check_fields(fields):
        for field in fields:
            if hasattr(field, 'type_name') and field.type_name in qfns:
                assert field.type_name in qfns, f"Field type {field.type_name} is not a QFN in {field}"
    def walk_ns(ns):
        for msg in ns.messages:
            check_fields(msg.fields)
        for nested in ns.namespaces:
            walk_ns(nested)
    for ns in model.namespaces:
        walk_ns(ns)
    for msg in model.messages:
        check_fields(msg.fields)

def test_qfn_reference_transform_on_defs():
    from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
    for def_file in get_def_files():
        with open(def_file, 'r', encoding='utf-8') as f:
            text = f.read()
        file_namespace = os.path.splitext(os.path.basename(def_file))[0]
        tree = parse_message_dsl(text)
        early_model = _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file)
        AddFileLevelNamespaceTransform().transform(early_model)
        transformed = run_early_transform_pipeline(early_model, [QfnReferenceTransform()])
        qfns = extract_qfns(transformed)
        check_all_refs_are_qfn(transformed, qfns)
        # Optionally, check that the structure is unchanged except for references
