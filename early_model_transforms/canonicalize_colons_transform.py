"""
CanonicalizeColonsTransform: Ensures all name specifiers use '::' instead of '.' in an EarlyModel.
"""
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum, EarlyField
from early_transform_pipeline import EarlyTransform
from typing import List

class CanonicalizeColonsTransform(EarlyTransform):
    def transform(self, model: EarlyModel) -> EarlyModel:
        def canonicalize(name: str) -> str:
            return name.replace('.', '::') if name else name

        def update_fields(fields: List[EarlyField]):
            for field in fields:
                if hasattr(field, 'type_name') and field.type_name:
                    field.type_name = canonicalize(field.type_name)
                if hasattr(field, 'referenced_name_raw') and field.referenced_name_raw:
                    field.referenced_name_raw = canonicalize(field.referenced_name_raw)
                if hasattr(field, 'element_type_raw') and field.element_type_raw:
                    field.element_type_raw = canonicalize(field.element_type_raw)
                if hasattr(field, 'map_key_type_raw') and field.map_key_type_raw:
                    field.map_key_type_raw = canonicalize(field.map_key_type_raw)
                if hasattr(field, 'map_value_type_raw') and field.map_value_type_raw:
                    field.map_value_type_raw = canonicalize(field.map_value_type_raw)
                if hasattr(field, 'compound_base_type_raw') and field.compound_base_type_raw:
                    field.compound_base_type_raw = canonicalize(field.compound_base_type_raw)
                if hasattr(field, 'compound_components_raw') and field.compound_components_raw:
                    field.compound_components_raw = [canonicalize(c) for c in field.compound_components_raw]

        def update_enums(enums: List[EarlyEnum]):
            for enum in enums:
                if hasattr(enum, 'parent_raw') and enum.parent_raw:
                    enum.parent_raw = canonicalize(enum.parent_raw)

        def update_ns(ns: EarlyNamespace):
            for msg in ns.messages:
                update_fields(msg.fields)
            update_enums(ns.enums)
            for nested in ns.namespaces:
                update_ns(nested)

        for ns in model.namespaces:
            update_ns(ns)
        for msg in model.messages:
            update_fields(msg.fields)
        update_enums(model.enums)
        return model
