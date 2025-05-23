"""
early_transform_pipeline.py
Defines a pipeline for transforming EarlyModel objects using a sequence of EarlyTransform objects.
"""
from typing import List, Protocol
from early_model import EarlyModel

class EarlyTransform(Protocol):
    def transform(self, model: EarlyModel) -> EarlyModel:
        ...

def run_early_transform_pipeline(
    model: EarlyModel, 
    transforms: List[EarlyTransform]
) -> EarlyModel:
    """
    Applies a sequence of EarlyTransform objects to an EarlyModel.
    Each transform takes an EarlyModel and returns a new EarlyModel.
    """
    for transform in transforms:
        model = transform.transform(model)
    return model
