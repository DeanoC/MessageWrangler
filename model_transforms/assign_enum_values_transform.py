"""
Model Transform: AssignEnumValuesTransform
Assigns values to all ModelEnum values, including inherited and auto-incremented values, so generators do not need to handle value assignment logic.
"""
from typing import Optional
from model import Model, ModelEnum, ModelEnumValue, ModelNamespace

class AssignEnumValuesTransform:
    def transform(self, model: Model) -> Model:
        for ns in getattr(model, 'namespaces', []):
            self._process_namespace(ns)
        return model

    def _process_namespace(self, ns: ModelNamespace):
        for enum in getattr(ns, 'enums', []):
            self._assign_enum_values(enum)
        for nested in getattr(ns, 'namespaces', []):
            self._process_namespace(nested)

    def _assign_enum_values(self, enum: ModelEnum):
        # Recursively assign values to parent first
        parent_values = []
        if enum.parent is not None:
            self._assign_enum_values(enum.parent)
            parent_values = enum.parent.values
        # Build merged value list: parent values (in order), overridden by child values (by name)
        child_value_map = {v.name: v for v in enum.values}
        merged = []
        used_names = set()
        # Build merged list: parent values (in order), overridden by child if present (child order wins)
        merged = []
        parent_names = set()
        for pval in parent_values:
            merged.append(ModelEnumValue(
                name=pval.name,
                value=pval.value,  # Use parent's assigned value
                doc=pval.doc,
                comment=pval.comment,
                file=pval.file,
                line=pval.line,
                namespace=pval.namespace
            ))
            parent_names.add(pval.name)
        # Remove parent values if overridden by child, then append child values in order
        for cval in enum.values:
            if cval.name in parent_names:
                raise ValueError(f"Child enum '{enum.name}' illegally redefines value '{cval.name}' from parent enum.")
            merged = [v for v in merged if v.name != cval.name]
            merged.append(cval)
        # Debug: print merged list before value assignment
        print(f"[DEBUG] Enum '{enum.name}' merged values before assignment:")
        for v in merged:
            print(f"    name={v.name!r}, value={v.value!r}")

        # Assign values in order, auto-incrementing and resetting after explicit assignments
        last_value = 0
        for idx, v in enumerate(merged):
            if v.value is not None:
                last_value = v.value
            else:
                v.value = last_value
            last_value += 1

        # Debug: print merged list after value assignment
        print(f"[DEBUG] Enum '{enum.name}' merged values after assignment:")
        for v in merged:
            print(f"    name={v.name!r}, value={v.value!r}")

        enum.values = merged
