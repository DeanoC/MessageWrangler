from model_debug import debug_print_model
import os
import sys
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from model import Model

def_dir = os.path.join(os.path.dirname(__file__), "../def")
def get_def_files():
    # Exclude known validation-failure files (like test_duplicate_fields.def)
    # Exclude known validation-failure files (like test_duplicate_fields.def, test_duplicate_messages.def)
    return [os.path.join(def_dir, f) for f in os.listdir(def_dir)
            if f.endswith(".def") and "invalid" not in f and "corner_case" not in f and "duplicate_fields" not in f and "duplicate_messages" not in f]

def extract_model_names(model: Model):
    names = set()
    def walk_ns(ns, prefix):
        ns_qfn = '::'.join(prefix + [ns.name]) if ns.name else '::'.join(prefix)
        for msg in ns.messages:
            names.add(ns_qfn + '::' + msg.name if ns_qfn else msg.name)
        for enum in ns.enums:
            names.add(ns_qfn + '::' + enum.name if ns_qfn else enum.name)
        for nested in ns.namespaces:
            walk_ns(nested, prefix + [ns.name] if ns.name else prefix)
    for ns in model.namespaces:
        walk_ns(ns, [])
    return names

def check_model_references_resolved(model: Model, names):
    # Additional validation: check for duplicate names in each namespace
    def check_duplicates(ns):
        seen = set()
        for msg in ns.messages:
            assert msg.name not in seen, f"Duplicate message name {msg.name} in namespace {ns.name}"
            seen.add(msg.name)
        for enum in ns.enums:
            assert enum.name not in seen, f"Duplicate enum name {enum.name} in namespace {ns.name}"
            seen.add(enum.name)
        for nested in ns.namespaces:
            check_duplicates(nested)
    for ns in model.namespaces:
        check_duplicates(ns)

    # Check that all enums have at least one value
    def check_enum_values(ns):
        for enum in ns.enums:
            assert enum.values, f"Enum {enum.name} in namespace {ns.name} has no values"
        for nested in ns.namespaces:
            check_enum_values(nested)
    for ns in model.namespaces:
        check_enum_values(ns)
    def check_fields(fields):
        for field in fields:
            if field.type.name in ('ENUM', 'MESSAGE'):
                assert field.type_ref is not None, f"Field {field.name} of type {field.type.name} missing type_ref"
    def walk_ns(ns):
        for msg in ns.messages:
            check_fields(msg.fields)
        for nested in ns.namespaces:
            walk_ns(nested)
    for ns in model.namespaces:
        walk_ns(ns)

def test_model_on_defs():
    out_dir = os.path.join('generated', 'model')
    os.makedirs(out_dir, exist_ok=True)
    for def_file in get_def_files():
        with open(def_file, 'r', encoding='utf-8') as f:
            text = f.read()
        file_namespace = os.path.splitext(os.path.basename(def_file))[0]
        tree = parse_message_dsl(text)
        early_model = _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file)
        AddFileLevelNamespaceTransform().transform(early_model)
        QfnReferenceTransform().transform(early_model)
        model = EarlyModelToModelTransform().transform(early_model)
        names = extract_model_names(model)
        check_model_references_resolved(model, names)
        # Print model for inspection
        out_path = os.path.join(out_dir, os.path.basename(def_file) + '.model.txt')
        debug_print_model(model, file_path=out_path, out_dir=out_dir)
