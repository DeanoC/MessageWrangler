import pytest
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum, EarlyField
from early_model_transforms.canonicalize_colons_transform import CanonicalizeColonsTransform

def make_field(type_name):
    return EarlyField(name='f', type_name=type_name, file='', namespace='', line=1, raw_type=type_name)

def test_canonicalize_colons_in_fields():
    msg = EarlyMessage(name='M', fields=[make_field('foo.bar.Baz'), make_field('foo::bar.Baz')], file='', namespace='', line=1)
    ns = EarlyNamespace(name='ns', messages=[msg], enums=[], file='', line=1)
    model = EarlyModel(namespaces=[ns], enums=[], messages=[], standalone_options=[], standalone_compounds=[], imports_raw=[], file='')
    CanonicalizeColonsTransform().transform(model)
    assert msg.fields[0].type_name == 'foo::bar::Baz'
    assert msg.fields[1].type_name == 'foo::bar::Baz'

def test_canonicalize_colons_in_enum_parent():
    enum = EarlyEnum(name='E', values=[], file='', namespace='', line=1, parent_raw='foo.bar.Baz')
    ns = EarlyNamespace(name='ns', messages=[], enums=[enum], file='', line=1)
    model = EarlyModel(namespaces=[ns], enums=[], messages=[], standalone_options=[], standalone_compounds=[], imports_raw=[], file='')
    CanonicalizeColonsTransform().transform(model)
    assert enum.parent_raw == 'foo::bar::Baz'
