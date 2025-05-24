import os
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
from model_debug import debug_print_model

def test_model_multiline_root_debug(capsys):
    def_file = os.path.join(os.path.dirname(__file__), 'def', 'test_multiline_root.def')
    with open(def_file, 'r', encoding='utf-8') as f:
        text = f.read()
    file_namespace = os.path.splitext(os.path.basename(def_file))[0]
    tree = parse_message_dsl(text)
    early_model = _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file)
    AddFileLevelNamespaceTransform().transform(early_model)
    QfnReferenceTransform().transform(early_model)
    model = EarlyModelToModelTransform().transform(early_model)
    debug_print_model(model)
    out = capsys.readouterr().out
    # Check that compound fields are present and correct
    assert 'Field: position (type[0]=COMPOUND' in out or 'Field: position (type[0]=compound' in out, out
    assert 'Field: color (type[0]=COMPOUND' in out or 'Field: color (type[0]=compound' in out, out
    assert 'Field: vector (type[0]=COMPOUND' in out or 'Field: vector (type[0]=compound' in out, out
    assert 'Field: transform (type[0]=COMPOUND' in out or 'Field: transform (type[0]=compound' in out, out
    # Optionally, check that the base type and components are present
    assert 'base_type=float' in out or "base_type='float'" in out, out
    assert 'components=[x, y, z]' in out or "components=['x', 'y', 'z']" in out or 'components=[x, y, z, rx, ry, rz, sx, sy, sz]' in out, out

if __name__ == "__main__":
    pytest.main([__file__])
