"""
AddFileLevelNamespaceTransform: Wraps all top-level items in a file-level namespace named after the file (without extension).
"""
import os
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum
from early_transform_pipeline import EarlyTransform
from typing import List

class AddFileLevelNamespaceTransform(EarlyTransform):
    def transform(self, model: EarlyModel) -> EarlyModel:
        # Get file-level namespace name (filename without extension, sanitized)
        file_ns = os.path.splitext(os.path.basename(model.file))[0]
        # Only add if not already present as the sole namespace
        if len(model.namespaces) == 1 and model.namespaces[0].name == file_ns:
            return model
        # Move all top-level messages/enums/namespaces into the file-level namespace
        new_ns = EarlyNamespace(
            name=file_ns,
            messages=model.messages,
            enums=model.enums,
            file=model.file,
            line=1,
            namespaces=model.namespaces
        )
        model.namespaces = [new_ns]
        model.messages = []
        model.enums = []
        return model
