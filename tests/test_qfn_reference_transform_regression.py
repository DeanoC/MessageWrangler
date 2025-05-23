"""
Regression test: QfnReferenceTransform should convert all field type references to QFN, including arrays, maps, and nested/namespace types.
"""
import os
import sys
import pytest
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform

def test_qfn_reference_transform_regression():
    dsl = '''
    message Vec3 {
        x: float
        y: float
        z: float
    }
    message WithArrays {
        tags: string[]
        points: Vec3[]
        ids: int[]
    }
    namespace TestNS {
        message Nested {
            value: int
        }
    }
    message WithNamespaceRef {
        nested: TestNS::Nested
        nestedArray: TestNS::Nested[]
    }
    '''
    file_namespace = "test_arrays_and_references"
    tree = parse_message_dsl(dsl)
    early_model = _build_early_model_from_lark_tree(tree, file_namespace)
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    # Check that all field type_names are QFN for references
    def check_fields(fields):
        for field in fields:
            # Only check non-primitives
            if field.type_name not in ("int", "string", "bool", "float", "double"):
                assert "::" in field.type_name or field.type_name.startswith(file_namespace), f"Field {field.name} type_name not QFN: {field.type_name}"
    for ns in early_model.namespaces:
        for msg in ns.messages:
            check_fields(msg.fields)
        for nested in ns.namespaces:
            for msg in nested.messages:
                check_fields(msg.fields)
