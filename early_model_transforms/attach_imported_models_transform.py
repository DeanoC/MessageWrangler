"""
AttachImportedModelsTransform: For each import in imports_raw, attaches the corresponding EarlyModel to the 'imports' field.
"""
from early_model import EarlyModel
from early_transform_pipeline import EarlyTransform
from typing import Dict

class AttachImportedModelsTransform(EarlyTransform):
    def __init__(self, import_models: Dict[str, EarlyModel]):
        self.import_models = import_models

    def transform(self, model: EarlyModel) -> EarlyModel:
        # For each import in imports_raw, attach the corresponding EarlyModel if available
        for import_path, alias in model.imports_raw:
            key = alias if alias else import_path
            if key in self.import_models:
                model.imports[key] = self.import_models[key]
        return model
