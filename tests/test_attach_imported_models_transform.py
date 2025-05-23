from early_model import EarlyModel
from early_model_transforms.attach_imported_models_transform import AttachImportedModelsTransform

def make_model(name):
    return EarlyModel(namespaces=[], enums=[], messages=[], options=[], compounds=[], imports_raw=[], file=name)

def test_attach_imported_models():
    # Simulate two imported models
    imported1 = make_model('imported1.def')
    imported2 = make_model('imported2.def')
    # Main model imports both
    imports_raw = [('imported1.def', None), ('imported2.def', 'alias2')]
    model = EarlyModel(namespaces=[], enums=[], messages=[], options=[], compounds=[], imports_raw=imports_raw, file='main.def')
    # Provide mapping for both
    import_models = {'imported1.def': imported1, 'alias2': imported2}
    AttachImportedModelsTransform(import_models).transform(model)
    assert model.imports['imported1.def'] is imported1
    assert model.imports['alias2'] is imported2
