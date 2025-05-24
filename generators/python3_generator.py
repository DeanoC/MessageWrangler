"""
Python 3 generator for Model (new system).
Outputs Python dataclasses and Enum classes for all messages and enums in the Model.
"""
from model import Model
from typing import List, Callable

from model_transforms.flatten_imports_transform import FlattenImportsTransform

from model_transforms.assign_unique_names_transform import AssignUniqueNamesTransform
from model_transforms.flatten_enums_transform import FlattenEnumsTransform


def generate_python3_code(model: Model, module_name: str = "messages", transforms: List[Callable] = None):
    # Apply enum value assignment and enum flattening so all enums/messages have a flat, unique name and values are set
    from model_transforms.assign_enum_values_transform import AssignEnumValuesTransform
    model = AssignEnumValuesTransform().transform(model)
    model = FlattenEnumsTransform().transform(model)
    # DEBUG: Print all enums and their parent/file info
    import sys
    print("[PYGEN DEBUG] ENUMS AND PARENTS:", file=sys.stderr)
    def debug_print_enum_parents(ns, indent=""):
        for enum in getattr(ns, 'enums', []):
            parent = getattr(enum, 'parent', None)
            parent_file = getattr(parent, 'file', None) if parent else None
            print(f"{indent}Enum {enum.name}: parent={getattr(parent, 'name', None)}, parent_file={parent_file}, file={getattr(enum, 'file', None)}", file=sys.stderr)
        for nested in getattr(ns, 'namespaces', []):
            debug_print_enum_parents(nested, indent + "  ")
    for ns in getattr(model, 'namespaces', []):
        debug_print_enum_parents(ns)

    # --- Collect imports for referenced base enums/messages (robust, post-model-build) ---
    import_lines = ["from enum import Enum", "from dataclasses import dataclass"]
    referenced_imports = set()

    def get_file_level_ns_for_obj(obj):
        file_attr = getattr(obj, 'file', None)
        if file_attr:
            import os
            return os.path.splitext(os.path.basename(file_attr))[0]
        return None

    def collect_referenced_imports_ns(ns):
        # Enums: check parent
        for enum in getattr(ns, 'enums', []):
            if enum.parent is not None:
                parent_mod = get_file_level_ns_for_obj(enum.parent)
                this_mod = get_file_level_ns_for_obj(model)
                if parent_mod and parent_mod != this_mod:
                    referenced_imports.add(parent_mod)
        # Messages: check parent (if inheritance is supported)
        for msg in getattr(ns, 'messages', []):
            if hasattr(msg, 'parent') and msg.parent is not None:
                # parent is a ModelReference or ModelMessage
                parent_obj = msg.parent
                parent_mod = get_file_level_ns_for_obj(parent_obj)
                this_mod = get_file_level_ns_for_obj(model)
                if parent_mod and parent_mod != this_mod:
                    referenced_imports.add(parent_mod)
            # Fields: check type_refs for referenced enums/messages from other files
            for field in getattr(msg, 'fields', []):
                for tref in getattr(field, 'type_refs', []):
                    if tref is not None and hasattr(tref, 'file'):
                        tref_mod = get_file_level_ns_for_obj(tref)
                        this_mod = get_file_level_ns_for_obj(model)
                        if tref_mod and tref_mod != this_mod:
                            referenced_imports.add(tref_mod)
        # Nested namespaces
        for nested in getattr(ns, 'namespaces', []):
            collect_referenced_imports_ns(nested)

    for ns in getattr(model, 'namespaces', []):
        collect_referenced_imports_ns(ns)
    # Emit import lines for referenced imports (using file-level namespace/module name)
    for imp in sorted(referenced_imports):
        import_lines.append(f"from .{imp} import *")
    lines = import_lines + [""]


    def get_qualified_name(obj):
        # Use the unique_name if present, else fallback to name
        return getattr(obj, 'name', obj.name)

    def emit_enum(enum, indent=""):
        # Handle enum inheritance
        base = "Enum"
        parent_comment = None
        if enum.parent is not None:
            parent_name = getattr(enum.parent, 'name', enum.parent.name)
            parent_file = getattr(enum.parent, 'file', None)
            parent_mod = None
            if parent_file:
                import os
                parent_mod = os.path.splitext(os.path.basename(parent_file))[0]
            if parent_mod:
                fq_flat_name = f"{parent_mod}_{parent_name}"
            else:
                fq_flat_name = parent_name
            import sys
            print(f"[PYGEN DEBUG] emit_enum: {enum.name} parent={fq_flat_name}", file=sys.stderr)
            parent_comment = f"# NOTE: Intended to inherit from {fq_flat_name} (from {parent_mod}), but Python Enum does not support Enum subclassing."

        if enum.doc:
            for line in (enum.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        if parent_comment:
            lines.append(f"{indent}{parent_comment}")
        lines.append(f"{indent}class {get_qualified_name(enum)}({base}):")

        # Emit all values, including inherited, in order, with child values overriding parent values
        # Use get_all_values() if available, else fallback to enum.values
        if hasattr(enum, 'get_all_values'):
            all_values = enum.get_all_values()
        else:
            all_values = enum.values

        # Build a map of explicit values for child values (overrides)
        child_explicit = {v.name: v.value for v in enum.values if v.value is not None}

        # To ensure correct auto-increment, assign values in the merged (parent+child) order, updating last_value after each assignment.
        assigned = {}
        last_value = None
        for idx, value in enumerate(all_values):
            # Prefer explicit value from child, then explicit value from value, else auto-increment
            if value.name in child_explicit:
                val = child_explicit[value.name]
            elif value.value is not None:
                val = value.value
            else:
                if last_value is not None:
                    val = last_value + 1
                else:
                    val = 0
            assigned[value.name] = val
            last_value = val
            # Debug output for enum value assignment
            import sys
            print(f"[PYGEN ENUM DEBUG] Assign {value.name} = {val} (idx={idx}, explicit_child={value.name in child_explicit}, explicit_any={value.value is not None})", file=sys.stderr)

        emitted = set()
        for value in all_values:
            if value.name in emitted:
                continue
            emitted.add(value.name)
            if value.doc:
                for line in (value.doc or '').strip().splitlines():
                    lines.append(f"{indent}    # {line}")
            lines.append(f"{indent}    {value.name} = {assigned[value.name]}")
        lines.append("")

    def emit_message(msg, indent=""):
        if msg.doc:
            for line in (msg.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        lines.append(f"{indent}@dataclass")
        lines.append(f"{indent}class {get_qualified_name(msg)}:")
        if not msg.fields:
            lines.append(f"{indent}    pass")
        else:
            for field in msg.fields:
                # For now, use type 'int' for all fields (stub, to be improved)
                lines.append(f"{indent}    {field.name}: int")
        lines.append("")

    def emit_namespace_flat(ns):
        # Emit all enums and messages at the module level, recursively
        for enum in getattr(ns, 'enums', []):
            emit_enum(enum, "")
        for msg in getattr(ns, 'messages', []):
            emit_message(msg, "")
        for nested in getattr(ns, 'namespaces', []):
            emit_namespace_flat(nested)

    # Top-level: emit all enums, messages, and namespaces at module level
    for ns in getattr(model, 'namespaces', []):
        emit_namespace_flat(ns)
    return "\n".join(lines)



def write_python3_file(model: Model, out_path):
    code = generate_python3_code(model)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)

def get_file_level_namespace_name(model: Model) -> str:
    """Get the file-level namespace name for a Model (usually the .def filename without extension)."""
    if hasattr(model, 'file') and model.file:
        import os
        return os.path.splitext(os.path.basename(model.file))[0]
    # fallback
    return "unknown"

def write_python3_files_for_model_and_imports(model: Model, out_dir: str, written=None):
    """Recursively write .py files for the model and all its imports."""
    import os
    if written is None:
        written = set()
    ns_name = get_file_level_namespace_name(model)
    out_path = os.path.join(out_dir, f"{ns_name}.py")
    if out_path in written:
        return
    os.makedirs(out_dir, exist_ok=True)
    code = generate_python3_code(model, module_name=ns_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    written.add(out_path)
    # Recurse for imports
    for imported in getattr(model, 'imports', {}).values():
        write_python3_files_for_model_and_imports(imported, out_dir, written)
