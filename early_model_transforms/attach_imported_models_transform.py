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
        print(f"[DEBUG] AttachImportedModelsTransform: model.file={getattr(model, 'file', None)}")
        print(f"[DEBUG]   model.imports_raw={model.imports_raw}")
        print(f"[DEBUG]   self.import_models keys={list(self.import_models.keys())}")
        for import_path, alias in model.imports_raw:
            key = alias if alias else import_path
            if key in self.import_models:
                print(f"[DEBUG]     Attaching import for key: {key}")
                model.imports[key] = self.import_models[key]
            else:
                print(f"[DEBUG]     No import found for key: {key}")
        print(f"[DEBUG]   model.imports keys after attach: {list(model.imports.keys())}")
        return model
