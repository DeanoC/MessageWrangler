"""
model_transform_pipeline.py
Defines a pipeline for transforming Model objects using a sequence of ModelTransform objects.
"""
from typing import List, Protocol
from model import Model

class ModelTransform(Protocol):
    def transform(self, model: Model) -> Model:
        ...

def run_model_transform_pipeline(
    model: Model,
    transforms: List[ModelTransform]
) -> Model:
    """
    Applies a sequence of ModelTransform objects to a Model.
    Each transform takes a Model and returns a new Model.
    """
    for transform in transforms:
        model = transform.transform(model)
    return model
