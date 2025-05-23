import os
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform

def test_add_file_level_namespace_moves_options_and_compounds():
    msg = EarlyMessage(name='M', fields=[], file='foo.def', namespace='', line=1)
    enum = EarlyEnum(name='E', values=[], file='foo.def', namespace='', line=1)
    ns = EarlyNamespace(name='Bar', messages=[], enums=[], file='foo.def', line=1)
    options = [{'name': 'opt1'}]
    compounds = [{'name': 'comp1'}]
    model = EarlyModel(namespaces=[ns], enums=[enum], messages=[msg], options=options, compounds=compounds, imports_raw=[], file='foo.def')
    AddFileLevelNamespaceTransform().transform(model)
    file_ns = os.path.splitext(os.path.basename(model.file))[0]
    assert len(model.namespaces) == 1
    ns = model.namespaces[0]
    assert ns.name == file_ns
    assert ns.options == options
    assert ns.compounds == compounds
    assert model.options == []
    assert model.compounds == []
