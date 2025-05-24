"""
FlattenEnumsTransform: Flattens all enums in the Model so that each enum's name is unique and includes its namespace/message context (e.g., Namespace_Message_EnumName).
This is useful for generators that require flat, globally unique enum names (e.g., Python, C++).
"""
from model import Model, ModelEnum, ModelNamespace, ModelMessage
import copy

def flatten_enums(model: Model) -> Model:
    """
    Traverses the model and renames all enums to a flat, unique name that includes their namespace/message context.
    Updates all references to these enums in fields and parent relationships.
    """
    # Build a mapping from original enum object to new flat name
    enum_to_flat_name = {}
    # Helper to build flat name from namespace/message chain
    def build_flat_name(ns_chain, enum_name):
        return '_'.join(ns_chain + [enum_name])
    # First pass: assign flat names
    def walk_namespace(ns: ModelNamespace, ns_chain):
        for enum in getattr(ns, 'enums', []):
            flat_name = build_flat_name(ns_chain, enum.name)
            enum_to_flat_name[enum] = flat_name
        for msg in getattr(ns, 'messages', []):
            pass
        for nested in getattr(ns, 'namespaces', []):
            walk_namespace(nested, ns_chain + [nested.name] if nested.name else ns_chain)
    for ns in getattr(model, 'namespaces', []):
        walk_namespace(ns, [ns.name] if ns.name else [])
    # Second pass: update enum names and references
    def update_namespace(ns: ModelNamespace, ns_chain):
        for enum in getattr(ns, 'enums', []):
            flat_name = enum_to_flat_name[enum]
            enum.name = flat_name
            setattr(enum, 'unique_name', flat_name)
            # Update parent name to flat name if parent is in enum_to_flat_name
            if getattr(enum, 'parent', None) in enum_to_flat_name:
                enum.parent.name = enum_to_flat_name[enum.parent]
        for msg in getattr(ns, 'messages', []):
            for field in getattr(msg, 'fields', []):
                # Update enum type_refs in fields
                for i, tref in enumerate(getattr(field, 'type_refs', [])):
                    if tref in enum_to_flat_name:
                        tref.name = enum_to_flat_name[tref]
                # If the field itself is an enum, update type_names
                if hasattr(field, 'type_names'):
                    for i, tname in enumerate(field.type_names):
                        if tname in enum_to_flat_name.values():
                            field.type_names[i] = tname
        for nested in getattr(ns, 'namespaces', []):
            update_namespace(nested, ns_chain + [nested.name] if nested.name else ns_chain)
    for ns in getattr(model, 'namespaces', []):
        update_namespace(ns, [ns.name] if ns.name else [])
    # Update parent relationships for enums: ensure parent reference points to the correct (flattened) enum object
    enum_obj_map = {id(enum): enum for enum in enum_to_flat_name}
    for enum in enum_to_flat_name:
        parent = getattr(enum, 'parent', None)
        if parent in enum_to_flat_name:
            # Find the actual parent object in the flattened set (by id)
            for candidate in enum_to_flat_name:
                if candidate is parent or id(candidate) == id(parent):
                    enum.parent = candidate
                    enum.parent.name = enum_to_flat_name[candidate]
                    break
    return model

class FlattenEnumsTransform:
    def transform(self, model: Model) -> Model:
        return flatten_enums(model)
