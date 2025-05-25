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
    # Helper: build a lookup of all messages by qualified name
    def build_message_lookup(ns, prefix=None, lookup=None):
        if lookup is None:
            lookup = {}
        ns_prefix = f"{prefix}::{ns.name}" if prefix else ns.name
        for msg in getattr(ns, 'messages', []):
            lookup[f"{ns_prefix}::{msg.name}"] = msg
        for nested in getattr(ns, 'namespaces', []):
            build_message_lookup(nested, ns_prefix, lookup)
        return lookup

    # Helper: for a message, get all fields with inline enums (name -> promoted enum name)
    def get_inline_enum_fields(msg):
        result = {}
        for field in getattr(msg, 'fields', []):
            if getattr(field, 'is_inline_enum', False) and getattr(field, 'inline_values_raw', None):
                result[field.name] = f"{msg.name}_{field.name}"
        return result


    # Recursively build a lookup of all messages in all namespaces of this model and all imported models
    def build_message_lookup_recursive(model, prefix=None, lookup=None, visited=None):
        if lookup is None:
            lookup = {}
        if visited is None:
            visited = set()
        # Avoid cycles
        model_id = id(model)
        if model_id in visited:
            return lookup
        visited.add(model_id)
        for ns in getattr(model, 'namespaces', []):
            build_message_lookup(ns, prefix, lookup)
        # Recurse into imports
        for imported_model in getattr(model, 'imports', {}).values():
            build_message_lookup_recursive(imported_model, None, lookup, visited)
        return lookup

    message_lookup = build_message_lookup_recursive(early_model)

    def walk_namespace(ns):
        # Collect new enums to add
        new_enums = []

        for msg in getattr(ns, 'messages', []):
            # Promote inline enums and inline options in this message
            for field in getattr(msg, 'fields', []):
                # 1. Normal inline enum promotion
                if getattr(field, 'is_inline_enum', False) and getattr(field, 'inline_values_raw', None):
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
                # 1b. Inline options promotion: promote to open enum with bitflag values and is_options_raw flag
                if getattr(field, 'is_inline_options', False) and getattr(field, 'inline_values_raw', None):
                    def camel_case(parts):
                        return ''.join(p[:1].upper() + p[1:] for p in parts if p)
                    enum_name = camel_case([msg.name, field.name])
                    print(f"[DEBUG] Promoting inline options: {enum_name} with values {[v.get('name', '?') for v in field.inline_values_raw]}")
                    # Assign bitflag values
                    values = []
                    for idx, v in enumerate(field.inline_values_raw):
                        values.append(EarlyEnumValue(
                            v.get('name', '?'), 1 << idx, field.file, field.namespace, field.line, comment=v.get('comment', None), doc=v.get('doc', None)
                        ))
                    new_enum = EarlyEnum(
                        name=enum_name,
                        values=values,
                        file=field.file,
                        namespace=field.namespace,
                        line=field.line,
                        parent_raw=None,
                        is_open_raw=True,
                        comment=field.comment,
                        doc=field.doc
                    )
                    # Mark as originally options
                    setattr(new_enum, 'is_options_raw', True)
                    new_enums.append(new_enum)
                    # Update the field to reference the new enum
                    field.is_inline_options = False
                    field.inline_values_raw = None
                    field.type_name = enum_name
                    field.type_type = 'enum_type'
            # 2. Patch derived fields that reference a parent's promoted enum (even if not inline)
            parent_raw = getattr(msg, 'parent_raw', None)
            if parent_raw:
                parent_msg = message_lookup.get(parent_raw)
                if parent_msg:
                    parent_enum_fields = get_inline_enum_fields(parent_msg)
                    for field in getattr(msg, 'fields', []):
                        # Patch if:
                        # - type_name is '?', or
                        # - is_inline_enum is True and no inline_values_raw, or
                        # - raw_type == 'enum' and type_name is '?' (parser fallback)
                        if (
                            getattr(field, 'type_name', None) in (None, '?', '')
                            and (getattr(field, 'is_inline_enum', False) or getattr(field, 'raw_type', None) == 'enum')
                        ):
                            for parent_field_name, promoted_enum_name in parent_enum_fields.items():
                                if field.name.startswith(parent_field_name):
                                    field.is_inline_enum = False
                                    field.inline_values_raw = None
                                    field.type_name = promoted_enum_name
                                    field.type_type = 'enum_type'
                                    break

            # Handle derived messages: promote enum for fields like 'typeX' if parent had 'type' as inline enum
            parent_raw = getattr(msg, 'parent_raw', None)
            if parent_raw:
                # Try to find the parent message in the lookup
                parent_msg = message_lookup.get(parent_raw)
                if parent_msg:
                    parent_enum_fields = get_inline_enum_fields(parent_msg)
                    for field in getattr(msg, 'fields', []):
                        # For each parent inline enum field, if this field's name starts with parent's field name and is not already an enum
                        for parent_field_name, promoted_enum_name in parent_enum_fields.items():
                            if field.name.startswith(parent_field_name) and not getattr(field, 'is_inline_enum', False):
                                # Only update if not already set to an enum type
                                if not (getattr(field, 'type_name', None) == promoted_enum_name and getattr(field, 'type_type', None) == 'enum_type'):
                                    field.type_name = promoted_enum_name
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
