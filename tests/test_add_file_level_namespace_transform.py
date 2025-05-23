import os
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum
from early_model_transforms.add_file_level_namespace_transform import AddFileLevelNamespaceTransform

def test_add_file_level_namespace():
    msg = EarlyMessage(name='M', fields=[], file='foo.def', namespace='', line=1)
    enum = EarlyEnum(name='E', values=[], file='foo.def', namespace='', line=1)
    ns = EarlyNamespace(name='Bar', messages=[], enums=[], file='foo.def', line=1)
    model = EarlyModel(namespaces=[ns], enums=[enum], messages=[msg], standalone_options=[], standalone_compounds=[], imports_raw=[], file='foo.def')
    AddFileLevelNamespaceTransform().transform(model)
    file_ns = os.path.splitext(os.path.basename(model.file))[0]
    assert len(model.namespaces) == 1
    assert model.namespaces[0].name == file_ns
    assert model.namespaces[0].messages[0] is msg
    assert model.namespaces[0].enums[0] is enum
    assert model.namespaces[0].namespaces[0] is ns
    assert model.messages == []
    assert model.enums == []
