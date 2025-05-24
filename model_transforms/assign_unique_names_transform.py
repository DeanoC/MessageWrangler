"""
AssignUniqueNamesTransform: Assigns a unique, context-aware name to every enum (and optionally message) in the Model.
This is useful for generators that need a flat, unique name for inline enums (e.g., Message_Field for inline enums).
The unique name is stored as the 'unique_name' attribute on ModelEnum/ModelMessage.
"""
from model import Model, ModelEnum, ModelMessage, ModelNamespace

def assign_unique_names(model: Model, enum_prefix: str = "", message_prefix: str = ""):
    """
    Traverses the model and assigns a unique_name attribute to every enum and message.
    For inline enums, the name will be <MessageName>_<FieldName>.
    For top-level enums, the name will be just the enum name (optionally prefixed).
    """
    def walk_namespace(ns: ModelNamespace, prefix: str = ""):
        import sys
        # Flatten namespace chain for unique_name
        new_prefix = f"{prefix}{ns.name}_" if ns.name else prefix
        for enum in getattr(ns, 'enums', []):
            parent = getattr(enum, 'parent_container', None)
            if parent and isinstance(parent, ModelMessage):
                unique_name = f"{new_prefix}{parent.name}_{enum.name}"
            else:
                unique_name = f"{new_prefix}{enum.name}"
            setattr(enum, 'unique_name', unique_name)
            print(f"[DEBUG] AssignUniqueNames: enum {enum.name} assigned unique_name={unique_name}", file=sys.stderr)
        for msg in getattr(ns, 'messages', []):
            unique_name = f"{new_prefix}{msg.name}"
            setattr(msg, 'unique_name', unique_name)
        for nested in getattr(ns, 'namespaces', []):
            walk_namespace(nested, new_prefix)
    for ns in getattr(model, 'namespaces', []):
        walk_namespace(ns, enum_prefix)
    return model

class AssignUniqueNamesTransform:
    def __init__(self, enum_prefix: str = "", message_prefix: str = ""):
        self.enum_prefix = enum_prefix
        self.message_prefix = message_prefix
    def transform(self, model: Model) -> Model:
        return assign_unique_names(model, self.enum_prefix, self.message_prefix)
