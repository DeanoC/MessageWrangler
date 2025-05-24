"""
Shared utilities for code generators (Python, TypeScript, etc).
Handles type mapping, name resolution, and import/reference collection.
"""
from typing import Any, Optional

# --- Type Mapping ---
PY_TO_TS_TYPE = {
    'int': 'number',
    'float': 'number',
    'double': 'number',
    'bool': 'boolean',
    'str': 'string',
    'bytes': 'Uint8Array',
    'Any': 'any',
}

PY_TO_PY_TYPE = {
    'int': 'int',
    'float': 'float',
    'double': 'float',
    'bool': 'bool',
    'str': 'str',
    'bytes': 'bytes',
    'Any': 'Any',
}

def get_typescript_type(field: Any) -> str:
    """Map a model field to a TypeScript type string."""
    base_type = getattr(field, 'field_type', None)
    if hasattr(base_type, 'value'):
        base_type = base_type.value
    if base_type in PY_TO_TS_TYPE:
        ts_type = PY_TO_TS_TYPE[base_type]
    elif hasattr(field, 'enum_reference') and field.enum_reference:
        ts_type = field.enum_reference
    elif hasattr(field, 'compound_reference') and field.compound_reference:
        ts_type = field.compound_reference
    else:
        ts_type = 'any'
    if getattr(field, 'is_array', False):
        ts_type += '[]'
    if getattr(field, 'optional', False):
        ts_type += ' | undefined'
    return ts_type

def get_python_type(field: Any) -> str:
    """Map a model field to a Python type string."""
    base_type = getattr(field, 'field_type', None)
    if hasattr(base_type, 'value'):
        base_type = base_type.value
    if base_type in PY_TO_PY_TYPE:
        py_type = PY_TO_PY_TYPE[base_type]
    elif hasattr(field, 'enum_reference') and field.enum_reference:
        py_type = field.enum_reference
    elif hasattr(field, 'compound_reference') and field.compound_reference:
        py_type = field.compound_reference
    else:
        py_type = 'Any'
    if getattr(field, 'is_array', False):
        py_type = f'list[{py_type}]'
    if getattr(field, 'is_map', False):
        py_type = f'dict[str, {py_type}]'
    return py_type

# --- Name Resolution ---
def get_local_name(name: str, parent_ns: Optional[str] = None, module_name: Optional[str] = None) -> str:
    if module_name and name.startswith(module_name + "_"):
        name = name[len(module_name) + 1:]
    if parent_ns and name.startswith(parent_ns + "_"):
        name = name[len(parent_ns) + 1:]
    return name

def get_qualified_name(obj: Any, parent_ns: Optional[str] = None, module_name: Optional[str] = None) -> str:
    name = getattr(obj, 'name', None)
    return get_local_name(name, parent_ns, module_name)

# --- Import/Reference Collection ---
def collect_referenced_imports(model: Any) -> set:
    """Collect referenced imports for a model (for cross-file references)."""
    referenced_imports = set()
    def get_file_level_ns_for_obj(obj):
        file_attr = getattr(obj, 'file', None)
        if file_attr:
            import os
            return os.path.splitext(os.path.basename(file_attr))[0]
        return None
    def walk_ns(ns):
        for enum in getattr(ns, 'enums', []):
            if enum.parent is not None:
                parent_mod = get_file_level_ns_for_obj(enum.parent)
                this_mod = get_file_level_ns_for_obj(model)
                if parent_mod and parent_mod != this_mod:
                    referenced_imports.add(parent_mod)
        for msg in getattr(ns, 'messages', []):
            if hasattr(msg, 'parent') and msg.parent is not None:
                parent_obj = msg.parent
                parent_mod = get_file_level_ns_for_obj(parent_obj)
                this_mod = get_file_level_ns_for_obj(model)
                if parent_mod and parent_mod != this_mod:
                    referenced_imports.add(parent_mod)
            for field in getattr(msg, 'fields', []):
                for tref in getattr(field, 'type_refs', []):
                    if tref is not None and hasattr(tref, 'file'):
                        tref_mod = get_file_level_ns_for_obj(tref)
                        this_mod = get_file_level_ns_for_obj(model)
                        if tref_mod and tref_mod != this_mod:
                            referenced_imports.add(tref_mod)
        for nested in getattr(ns, 'namespaces', []):
            walk_ns(nested)
    for ns in getattr(model, 'namespaces', []):
        walk_ns(ns)
    return referenced_imports
