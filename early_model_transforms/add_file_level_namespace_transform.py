"""
AddFileLevelNamespaceTransform: Wraps all top-level items in a file-level namespace named after the file (without extension).
"""
import os
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum
from early_transform_pipeline import EarlyTransform
from typing import List

class AddFileLevelNamespaceTransform(EarlyTransform):
    def transform(self, model: EarlyModel) -> EarlyModel:
        print(f"[FILELEVELNS DEBUG] Running AddFileLevelNamespaceTransform on file: {model.file}")
        # Always create a file-level namespace named after the file (without extension)
        file_ns = os.path.splitext(os.path.basename(model.file))[0]
        # If the only namespace is already the file-level namespace and all top-level items are inside it, do nothing
        if (
            len(model.namespaces) == 1 and
            model.namespaces[0].name == file_ns and
            not model.messages and not model.enums and not model.options and not model.compounds
        ):
            print(f"[FILELEVELNS DEBUG] File-level namespace already present: {file_ns}")
            return model
        # Otherwise, wrap all top-level items (including namespaces) in the file-level namespace
        print(f"[FILELEVELNS DEBUG] Creating file-level namespace: {file_ns}")
        new_ns = EarlyNamespace(
            name=file_ns,
            messages=model.messages,
            enums=model.enums,
            file=model.file,
            line=1,
            namespaces=model.namespaces,
            options=model.options,
            compounds=model.compounds
        )
        model.namespaces = [new_ns]
        model.messages = []
        model.enums = []
        model.options = []
        model.compounds = []
        print(f"[FILELEVELNS DEBUG] Namespaces after transform: {[ns.name for ns in model.namespaces]}")
        return model
