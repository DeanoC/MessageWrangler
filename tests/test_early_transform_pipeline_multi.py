from early_model import EarlyModel
from early_model_transforms.attach_imported_models_transform import AttachImportedModelsTransform
from early_transform_pipeline_multi import run_early_transform_pipeline_multi, EarlyTransform

def make_model(name, imports_raw):
    return EarlyModel(namespaces=[], enums=[], messages=[], standalone_options=[], standalone_compounds=[], imports_raw=imports_raw, file=name)

class DummyTransform(EarlyTransform):
    def __init__(self):
        self.touched = set()
    def transform(self, model):
        self.touched.add(model.file)
        return model

def test_pipeline_multi_order():
    a = make_model('a', [('b', None)])
    b = make_model('b', [])
    models = {'a': a, 'b': b}
    dummy = DummyTransform()
    out = run_early_transform_pipeline_multi(models, [dummy])
    # b must be processed before a
    assert out.index(b) < out.index(a)
    assert dummy.touched == {'a', 'b'}
