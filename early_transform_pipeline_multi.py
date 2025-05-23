"""
Multi-model transform pipeline for EarlyModels, processing in dependency order.
"""
from typing import List, Dict
from early_model import EarlyModel
from early_model_transforms.dependency_sort import topological_sort_earlymodels

class EarlyTransform:
    def transform(self, model: EarlyModel) -> EarlyModel:
        raise NotImplementedError

def run_early_transform_pipeline_multi(
    models: Dict[str, EarlyModel],
    transforms: List[EarlyTransform]
) -> List[EarlyModel]:
    """
    Applies a sequence of EarlyTransform objects to each EarlyModel in dependency order.
    Returns the list of transformed EarlyModels in dependency order.
    """
    sorted_models = topological_sort_earlymodels(models)
    for model in sorted_models:
        for transform in transforms:
            transform.transform(model)
    return sorted_models
