"""
flatten_imports_transform.py
A ModelTransform that flattens all imported namespaces, messages, and enums into the root model, for single-file output (e.g., JSON Schema).
"""
from model import Model, ModelNamespace, ModelMessage, ModelEnum
from typing import Set

class FlattenImportsTransform:
    def transform(self, model: Model) -> Model:
        """Flatten all imported namespaces, messages, and enums into the root model."""
        # Collect all namespaces, messages, and enums from imports recursively
        seen_models: Set[int] = set()
        def collect_ns_from_model(m: Model):
            if id(m) in seen_models:
                return []
            seen_models.add(id(m))
            result = []
            for ns in getattr(m, 'namespaces', []):
                result.append(ns)
            for imported in getattr(m, 'imports', {}).values():
                result.extend(collect_ns_from_model(imported))
            return result
        # Flatten all namespaces from self and imports
        all_namespaces = collect_ns_from_model(model)
        # Remove duplicates by QFN (namespace name path)
        seen_ns = set()
        flat_namespaces = []
        for ns in all_namespaces:
            ns_key = ns.name
            if ns_key not in seen_ns:
                flat_namespaces.append(ns)
                seen_ns.add(ns_key)
        # Create a new model with all namespaces flattened
        model.namespaces = flat_namespaces
        model.imports = {}  # Remove imports
        return model

    def __call__(self, model: Model) -> Model:
        return self.transform(model)
        # Collect all namespaces, messages, and enums from imports recursively
        seen_models: Set[int] = set()
        def collect_ns_from_model(m: Model):
            if id(m) in seen_models:
                return []
            seen_models.add(id(m))
            result = []
            for ns in getattr(m, 'namespaces', []):
                result.append(ns)
            for imported in getattr(m, 'imports', {}).values():
                result.extend(collect_ns_from_model(imported))
            return result
        # Flatten all namespaces from self and imports
        all_namespaces = collect_ns_from_model(model)
        # Remove duplicates by QFN (namespace name path)
        seen_ns = set()
        flat_namespaces = []
        for ns in all_namespaces:
            ns_key = ns.name
            if ns_key not in seen_ns:
                flat_namespaces.append(ns)
                seen_ns.add(ns_key)
        # Create a new model with all namespaces flattened
        model.namespaces = flat_namespaces
        model.imports = {}  # Remove imports
        return model
