"""
Model transform to insert dummy enums for missing options types in the correct namespace.
This ensures all required enums for options fields are present before code generation.
"""
from model import Model

class AssignDummyOptionEnumsTransform:
    def transform(self, model: Model):
        def get_local_name(name):
            # CamelCase, no underscores
            parts = name.replace('::', '').split('_')
            return ''.join(part[:1].upper() + part[1:] for part in parts if part)

        def walk_namespaces(namespaces, parent_ns=None):
            for ns in namespaces:
                enums_by_name = {get_local_name(e.name): e for e in getattr(ns, 'enums', [])}
                # Scan all messages for options fields
                for msg in getattr(ns, 'messages', []):
                    for field in getattr(msg, 'fields', []):
                        ftypes = getattr(field, 'field_types', [])
                        if ftypes and ftypes[0].name == 'OPTIONS':
                            # Determine the expected enum name
                            type_name = None
                            trefs = getattr(field, 'type_refs', [])
                            if trefs and hasattr(trefs[0], 'name') and trefs[0].name:
                                type_name = get_local_name(trefs[0].name)
                            elif hasattr(field, 'type_names') and field.type_names:
                                for tname in field.type_names:
                                    if tname and tname.lower() not in ("int", "string", "bool", "float", "double", "map", "array", "options", "compound"):
                                        type_name = get_local_name(tname)
                                        break
                            # Only add a dummy if no enum with this name exists, or if the existing one has no values and is not a real enum
                            if type_name and (
                                type_name not in enums_by_name or
                                (hasattr(enums_by_name[type_name], 'values') and not enums_by_name[type_name].values and getattr(enums_by_name[type_name], 'is_dummy', False))
                            ):
                                # Insert dummy enum as a real ModelEnum-like object
                                class DummyEnum:
                                    def __init__(self, name):
                                        self.name = name
                                        self.values = []
                                        self.doc = None
                                        self.is_dummy = True
                                        self.parent = None
                                # Only add if not already present as a dummy
                                if type_name not in enums_by_name:
                                    ns.enums.append(DummyEnum(type_name))
                walk_namespaces(getattr(ns, 'namespaces', []), ns)
        walk_namespaces(getattr(model, 'namespaces', []))
        return model
