import pytest
from early_model import EarlyModel
from early_model_transforms.dependency_sort import topological_sort_earlymodels, DependencyCycleError

def make_model(name, imports_raw):
    return EarlyModel(namespaces=[], enums=[], messages=[], standalone_options=[], standalone_compounds=[], imports_raw=imports_raw, file=name)

def test_topological_sort_simple():
    a = make_model('a', [('b', None)])
    b = make_model('b', [])
    models = {'a': a, 'b': b}
    sorted_models = topological_sort_earlymodels(models)
    # b must come before a
    assert sorted_models.index(b) < sorted_models.index(a)

def test_topological_sort_cycle():
    a = make_model('a', [('b', None)])
    b = make_model('b', [('a', None)])
    models = {'a': a, 'b': b}
    with pytest.raises(DependencyCycleError):
        topological_sort_earlymodels(models)
