import os
import pytest
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum, EarlyField
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform
from early_model_transforms.attach_imported_models_transform import AttachImportedModelsTransform
from early_model_transforms.qfn_reference_transform import QfnReferenceTransform

def make_field(type_name):
    return EarlyField(name='f', type_name=type_name, file='', namespace='', line=1, raw_type=type_name)

def make_model(file, messages=None, enums=None, namespaces=None, imports_raw=None, imports=None):
    return EarlyModel(
        namespaces=namespaces or [],
        enums=enums or [],
        messages=messages or [],
        standalone_options=[],
        standalone_compounds=[],
        imports_raw=imports_raw or [],
        file=file,
        imports=imports or {}
    )

def run_pipeline(model, import_models=None):
    AddFileLevelNamespaceTransform().transform(model)
    if import_models:
        AttachImportedModelsTransform(import_models).transform(model)
    QfnReferenceTransform().transform(model)
    return model

def test_simple_intra_file():
    msg = EarlyMessage(name='A', fields=[make_field('A')], file='foo.def', namespace='', line=1)
    model = make_model('foo.def', messages=[msg])
    run_pipeline(model)
    assert msg.fields[0].type_name == 'foo::A'

def test_nested_namespace():
    inner = EarlyNamespace(name='Bar', messages=[EarlyMessage('B', [make_field('B')], 'foo.def', '', 1)], enums=[], file='foo.def', line=1)
    model = make_model('foo.def', namespaces=[inner])
    run_pipeline(model)
    b_msg = model.namespaces[0].namespaces[0].messages[0]
    assert b_msg.fields[0].type_name == 'foo::Bar::B'

def test_cross_file_import():
    imported = make_model('x.def', messages=[EarlyMessage('AA', [], 'x.def', '', 1)])
    main = make_model('y.def', messages=[EarlyMessage('BB', [make_field('AA')], 'y.def', '', 1)], imports_raw=[('x.def', None)])
    run_pipeline(imported)
    run_pipeline(main, {'x.def': imported})
    bb = main.namespaces[0].messages[0]
    assert bb.fields[0].type_name == 'x::AA'

def test_cross_file_aliased_import():
    imported = make_model('x.def', messages=[EarlyMessage('AA', [], 'x.def', '', 1)])
    main = make_model('y.def', messages=[EarlyMessage('BB', [make_field('L::AA')], 'y.def', '', 1)], imports_raw=[('x.def', 'L')])
    run_pipeline(imported)
    run_pipeline(main, {'L': imported})
    bb = main.namespaces[0].messages[0]
    assert bb.fields[0].type_name == 'L::AA'

def test_cross_file_aliased_import_unqualified_fails():
    imported = make_model('x.def', messages=[EarlyMessage('AA', [], 'x.def', '', 1)])
    main = make_model('y.def', messages=[EarlyMessage('BB', [make_field('AA')], 'y.def', '', 1)], imports_raw=[('x.def', 'L')])
    run_pipeline(imported)
    run_pipeline(main, {'L': imported})
    bb = main.namespaces[0].messages[0]
    # Unqualified AA should not resolve to L::AA
    assert bb.fields[0].type_name == 'AA'

def test_shadowing_and_parent_resolution():
    # foo.def: namespace N { message A {} message B : A {} } message A {}
    inner = EarlyNamespace(name='N', messages=[EarlyMessage('A', [], 'foo.def', '', 1), EarlyMessage('B', [make_field('A')], 'foo.def', '', 1)], enums=[], file='foo.def', line=1)
    outer = EarlyMessage('A', [], 'foo.def', '', 1)
    model = make_model('foo.def', namespaces=[inner], messages=[outer])
    run_pipeline(model)
    # N::B's field A should resolve to foo::N::A, not foo::A
    b_msg = model.namespaces[0].namespaces[0].messages[1]
    assert b_msg.fields[0].type_name == 'foo::N::A'

def test_import_resolution_order():
    # y.def imports x.def, both define AA
    imported = make_model('x.def', messages=[EarlyMessage('AA', [], 'x.def', '', 1)])
    main = make_model('y.def', messages=[EarlyMessage('AA', [], 'y.def', '', 1), EarlyMessage('BB', [make_field('AA')], 'y.def', '', 1)], imports_raw=[('x.def', None)])
    run_pipeline(imported)
    run_pipeline(main, {'x.def': imported})
    bb = main.namespaces[0].messages[1]
    # Should resolve to y::AA, not x::AA
    assert bb.fields[0].type_name == 'y::AA'

def test_enum_parent_crossfile():
    imported = make_model('x.def', enums=[EarlyEnum('E', [], 'x.def', '', 1)])
    main = make_model('y.def', enums=[EarlyEnum('F', [], 'y.def', '', 1, parent_raw='E')], imports_raw=[('x.def', None)])
    run_pipeline(imported)
    run_pipeline(main, {'x.def': imported})
    f_enum = main.namespaces[0].enums[0]
    assert f_enum.parent_raw == 'x::E'

def test_enum_parent_aliased():
    imported = make_model('x.def', enums=[EarlyEnum('E', [], 'x.def', '', 1)])
    main = make_model('y.def', enums=[EarlyEnum('F', [], 'y.def', '', 1, parent_raw='L::E')], imports_raw=[('x.def', 'L')])
    run_pipeline(imported)
    run_pipeline(main, {'L': imported})
    f_enum = main.namespaces[0].enums[0]
    assert f_enum.parent_raw == 'L::E'

def test_enum_parent_aliased_unqualified_fails():
    imported = make_model('x.def', enums=[EarlyEnum('E', [], 'x.def', '', 1)])
    main = make_model('y.def', enums=[EarlyEnum('F', [], 'y.def', '', 1, parent_raw='E')], imports_raw=[('x.def', 'L')])
    run_pipeline(imported)
    run_pipeline(main, {'L': imported})
    f_enum = main.namespaces[0].enums[0]
    # Unqualified E should not resolve to L::E
    assert f_enum.parent_raw == 'E'
