"""
PromoteInlineEnumsTransform: Promotes all inline enums in EarlyModel to top-level enums in the correct namespace, assigns unique names, and updates all references.
After this transform, there are no inline enums left in fields; all enums are normal enums.
"""
from early_model import EarlyModel, EarlyEnum, EarlyEnumValue
import copy

def promote_inline_enums(early_model: EarlyModel):
    """
    Promotes all inline enums in EarlyModel to top-level enums in the correct namespace, assigns unique names, and updates all references.
    """
    def walk_namespace(ns):
        # Collect new enums to add
        new_enums = []
        for msg in getattr(ns, 'messages', []):
            for field in getattr(msg, 'fields', []):
                if getattr(field, 'is_inline_enum', False) and getattr(field, 'inline_values_raw', None):
                    # Create a new EarlyEnum
                    enum_name = f"{msg.name}_{field.name}"
                    values = [EarlyEnumValue(
                        v.get('name', '?'), v.get('value', None), field.file, field.namespace, field.line, comment=v.get('comment', None), doc=v.get('doc', None)
                    ) for v in field.inline_values_raw]
                    new_enum = EarlyEnum(
                        name=enum_name,
                        values=values,
                        file=field.file,
                        namespace=field.namespace,
                        line=field.line,
                        parent_raw=None,
                        is_open_raw=False,
                        comment=field.comment,
                        doc=field.doc
                    )
                    new_enums.append(new_enum)
                    # Update the field to reference the new enum
                    field.is_inline_enum = False
                    field.inline_values_raw = None
                    field.type_name = enum_name
                    field.type_type = 'enum_type'
        # Add new enums to the namespace
        ns.enums.extend(new_enums)
        # Recurse into nested namespaces
        for nested in getattr(ns, 'namespaces', []):
            walk_namespace(nested)
    for ns in getattr(early_model, 'namespaces', []):
        walk_namespace(ns)
    return early_model

class PromoteInlineEnumsTransform:
    def transform(self, early_model: EarlyModel) -> EarlyModel:
        return promote_inline_enums(early_model)
