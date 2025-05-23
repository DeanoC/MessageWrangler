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
    import_lines = ["from __future__ import annotations", "from enum import Enum", "from dataclasses import dataclass"]
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

    # If there are no namespaces, still return the imports and a pass statement
    if not getattr(model, 'namespaces', []):
        lines.append("pass\n")
        return "\n".join(lines)

    # --- Helper functions (define only once, not nested) ---
    def get_local_name(name, parent_ns=None):
        # Always remove file-level namespace prefix if present
        if module_name and name.startswith(module_name + "_"):
            name = name[len(module_name) + 1:]
        # For nested namespaces, remove parent_ns prefix if present
        if parent_ns and name.startswith(parent_ns + "_"):
            name = name[len(parent_ns) + 1:]
        return name

    def get_qualified_name(obj, parent_ns=None):
        # Always use only the local name for nested classes
        name = getattr(obj, 'name', obj.name)
        return get_local_name(name, parent_ns)

    def emit_enum_inner(enum, indent="", parent_ns=None):
        base = "Enum"
        parent_comment = None
        if enum.parent is not None:
            parent_name = getattr(enum.parent, 'name', enum.parent.name)
            parent_mod = getattr(enum.parent, 'namespace', None)
            fq_flat_name = parent_name
            import sys
            print(f"[PYGEN DEBUG] emit_enum: {enum.name} parent={fq_flat_name}", file=sys.stderr)
            parent_file_ns = None
            if hasattr(enum.parent, 'file') and enum.parent.file:
                import os
                parent_file_ns = os.path.splitext(os.path.basename(enum.parent.file))[0]
            parent_flat_name = getattr(enum.parent, 'name', parent_name)
            # Emit the flat name with underscore for the inheritance comment to match test expectation
            if parent_file_ns:
                parent_full_flat = f"{parent_file_ns}_{parent_flat_name}"
            else:
                parent_full_flat = parent_flat_name
            parent_comment = f"# NOTE: Intended to inherit from {parent_full_flat} (from {parent_mod}), but Python Enum does not support Enum subclassing."
        if enum.doc:
            for line in (enum.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        if parent_comment:
            lines.append(f"{indent}{parent_comment}")
        # Always use local name for class emission (strip file-level prefix)
        enum_name = get_local_name(enum.name, parent_ns)
        lines.append(f"{indent}class {enum_name}({base}):")
        enum_body_lines = []
        if hasattr(enum, 'get_all_values'):
            all_values = enum.get_all_values()
        else:
            all_values = enum.values
        child_explicit = {v.name: v.value for v in enum.values if v.value is not None}
        assigned = {}
        last_value = None
        for idx, value in enumerate(all_values):
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
        emitted = set()
        for value in all_values:
            if value.name in emitted:
                continue
            emitted.add(value.name)
            if value.doc:
                for line in (value.doc or '').strip().splitlines():
                    enum_body_lines.append(f"{indent}    # {line}")
            enum_body_lines.append(f"{indent}    {value.name} = {assigned[value.name]}")
        if enum_body_lines:
            lines.extend(enum_body_lines)
        else:
            lines.append(f"{indent}    pass")
        lines.append("")
        return enum_name

    def emit_message(msg, indent="", parent_ns=None):
        if msg.doc:
            for line in (msg.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        lines.append(f"{indent}@dataclass")
        # Always use local name for class emission (strip file-level prefix)
        msg_class_name = get_local_name(msg.name, parent_ns)
        lines.append(f"{indent}class {msg_class_name}:")
        if not msg.fields:
            lines.append(f"{indent}    pass")
        else:
            for field in msg.fields:
                def py_type(field):
                    from model import FieldType
                    ftypes = field.field_types
                    trefs = field.type_refs
                    if ftypes[0] == FieldType.MAP:
                        key_py = py_type_helper(ftypes[1], trefs[1])
                        val_py = py_type_helper(ftypes[2], trefs[2])
                        return f"dict[{key_py}, {val_py}]"
                    if ftypes[0] == FieldType.ARRAY:
                        elem_py = py_type_helper(ftypes[1], trefs[1])
                        return f"list[{elem_py}]"
                    return py_type_helper(ftypes[0], trefs[0])
                def py_type_helper(ftype, tref):
                    from model import FieldType, ModelReference
                    def get_enum_type_name(enum_ref):
                        if enum_ref is None:
                            return "str"  # fallback for unresolved enum
                        ns_chain = []
                        ns = getattr(enum_ref, 'parent_namespace', None)
                        while ns is not None:
                            ns_chain.insert(0, ns.name)
                            ns = getattr(ns, 'parent_namespace', None)
                        file_ns = module_name
                        if ns_chain and ns_chain[0] != file_ns:
                            ns_chain.insert(0, file_ns)
                        elif not ns_chain:
                            ns_chain = [file_ns]
                        enum_name = getattr(enum_ref, 'name', str(enum_ref))
                        ns_prefix = '_'.join(ns_chain)
                        if enum_name.startswith(ns_prefix + '_'):
                            enum_name = enum_name[len(ns_prefix) + 1:]
                        # Use only the local name for type hints
                        return enum_name
                    def find_message_in_namespaces(local_name, namespaces, parent_path=None):
                        if parent_path is None:
                            parent_path = []
                        for ns in namespaces:
                            msg_dict = getattr(ns, 'messages', [])
                            if isinstance(msg_dict, dict):
                                if local_name in msg_dict:
                                    if parent_path:
                                        path = parent_path + [ns.name, local_name]
                                        if path and path[0] == module_name:
                                            path = path[1:]
                                        return '.'.join(path)
                                    else:
                                        return local_name
                            elif isinstance(msg_dict, list):
                                msg_names = {getattr(m, 'name', None) for m in msg_dict}
                                if local_name in msg_names:
                                    if parent_path:
                                        path = parent_path + [ns.name, local_name]
                                        if path and path[0] == module_name:
                                            path = path[1:]
                                        return '.'.join(path)
                                    else:
                                        return local_name
                            nested_namespaces = getattr(ns, 'namespaces', [])
                            new_parent_path = parent_path + [ns.name] if ns.name else parent_path
                            found = find_message_in_namespaces(local_name, nested_namespaces, new_parent_path)
                            if found:
                                return found
                        return None
                    if ftype == FieldType.INT:
                        return "int"
                    if ftype == FieldType.STRING:
                        return "str"
                    if ftype == FieldType.BOOL:
                        return "bool"
                    if ftype == FieldType.FLOAT or ftype == FieldType.DOUBLE:
                        return "float"
                    if ftype == FieldType.ENUM:
                        if tref is None:
                            return "str"  # fallback for unresolved enum
                        name = get_enum_type_name(tref)
                        if name == "Any":
                            return "str"
                        # Always use fully qualified name for file-level namespace types
                        file_ns = module_name
                        ns_chain = []
                        ns = getattr(tref, 'parent_namespace', None)
                        while ns is not None:
                            ns_chain.insert(0, ns.name)
                            ns = getattr(ns, 'parent_namespace', None)
                        if not ns_chain or (len(ns_chain) == 1 and ns_chain[0] == file_ns):
                            return f"{file_ns}.{get_local_name(getattr(tref, 'name', ''))}"
                        return name
                    if ftype == FieldType.MESSAGE:
                        if tref is None:
                            return "str"  # fallback for unresolved message
                        if hasattr(tref, 'name'):
                            file_ns = module_name
                            msg_ns = getattr(tref, 'parent_namespace', None)
                            if msg_ns is None or (getattr(msg_ns, 'name', None) == file_ns):
                                return f"{file_ns}.{get_local_name(getattr(tref, 'name', ''))}"
                            return get_local_name(getattr(tref, 'name', ''))
                        if hasattr(tref, 'qfn'):
                            qfn = getattr(tref, 'qfn')
                            local_name = qfn.split('::')[-1]
                            found = find_message_in_namespaces(local_name, getattr(model, 'namespaces', []))
                            if found:
                                return found
                        if isinstance(tref, str):
                            found = find_message_in_namespaces(tref, getattr(model, 'namespaces', []))
                            if found:
                                return found
                        return "str"  # fallback for unresolved message
                    if ftype == FieldType.COMPOUND:
                        compound_name = f"{get_local_name(getattr(msg, 'name', '?'))}_{get_local_name(getattr(field, 'name', '?'))}_Compound"
                        return compound_name
                    return "str"  # fallback for unresolved/unknown type
                lines.append(f"{indent}    {field.name}: {py_type(field)}")
        lines.append("")

    def emit_namespace_flat(ns, indent="", class_path=None, file_level_aliases=None, file_level_full_aliases=None):
        if class_path is None:
            class_path = []
        if file_level_aliases is None:
            file_level_aliases = {}
        if file_level_full_aliases is None:
            file_level_full_aliases = {}
        if ns.name:
            lines.append(f"{indent}class {ns.name}:")
            subindent = indent + "    "
            this_class_path = class_path + [ns.name]
        else:
            subindent = indent
            this_class_path = class_path[:]
        start_len = len(lines)
        enum_names = []
        msg_names = []
        enum_local_names = []
        msg_local_names = []
        # Collect all enums/messages for file-level aliasing if referenced by fields
        referenced_types = set()
        for msg in getattr(ns, 'messages', []):
            for field in getattr(msg, 'fields', []):
                # Only consider enums and messages
                tref = None
                if hasattr(field, 'type_refs') and field.type_refs:
                    tref = field.type_refs[0]
                if tref is not None and hasattr(tref, 'name'):
                    referenced_types.add(tref.name)
        # Emit enums as nested classes and assign as class attributes (inside class body)
        for enum in getattr(ns, 'enums', []):
            enum_name = emit_enum_inner(enum, subindent, ns.name)
            if enum_name:
                enum_names.append(enum_name)
                local_name = get_local_name(enum.name, ns.name)
                # Always emit alias if local_name differs from enum_name and local_name is not empty
                if local_name and local_name != enum_name:
                    enum_local_names.append((local_name, enum_name))
                # If this enum is referenced by a field, add to file-level aliases
                if enum.name in referenced_types or local_name in referenced_types:
                    file_level_aliases[local_name] = enum_name
                    # Also emit the fully-prefixed name as an alias (for test compatibility)
                    if enum.name != local_name:
                        file_level_full_aliases[enum.name] = enum_name
        # Emit messages as nested classes and assign as class attributes (inside class body)
        for msg in getattr(ns, 'messages', []):
            emit_message(msg, subindent, ns.name)
            msg_name = get_qualified_name(msg, ns.name)
            msg_names.append(msg_name)
            local_name = get_local_name(msg.name, ns.name)
            if local_name and local_name != msg_name:
                msg_local_names.append((local_name, msg_name))
            # If this message is referenced by a field, add to file-level aliases
            if msg.name in referenced_types or local_name in referenced_types:
                file_level_aliases[local_name] = msg_name
                if msg.name != local_name:
                    file_level_full_aliases[msg.name] = msg_name
        for nested in getattr(ns, 'namespaces', []):
            emit_namespace_flat(nested, subindent, this_class_path, file_level_aliases, file_level_full_aliases)
        # For file-level namespace, emit assignments for all top-level enums/messages
        if not class_path and ns.name:
            for enum_name in enum_names:
                lines.append(f"{subindent}{enum_name} = {enum_name}")
            for msg_name in msg_names:
                lines.append(f"{subindent}{msg_name} = {msg_name}")
            # Emit file-level aliases for referenced types (e.g., inline enums) as class attributes
            for local_name, class_name in file_level_aliases.items():
                if local_name != class_name:
                    lines.append(f"{subindent}{local_name} = {class_name}")
            for full_name, class_name in file_level_full_aliases.items():
                if full_name != class_name:
                    lines.append(f"{subindent}{full_name} = {class_name}")
        # Also emit these aliases at the module level for direct import (after the class definition)
        if not class_path and ns.name:
            module_level_aliases = []
            for local_name, class_name in file_level_aliases.items():
                if local_name != class_name:
                    module_level_aliases.append((local_name, f"{ns.name}.{class_name}"))
            for full_name, class_name in file_level_full_aliases.items():
                if full_name != class_name:
                    module_level_aliases.append((full_name, f"{ns.name}.{class_name}"))
            if module_level_aliases:
                lines.append("")
                for alias, target in module_level_aliases:
                    lines.append(f"{alias} = {target}")
        # For nested namespaces, always emit local name assignments inside the class
        if class_path and ns.name:
            for enum in getattr(ns, 'enums', []):
                local_name = get_local_name(enum.name, ns.name)
                class_name = get_qualified_name(enum, ns.name)
                lines.append(f"{subindent}{local_name} = {class_name}")
            for msg in getattr(ns, 'messages', []):
                local_name = get_local_name(msg.name, ns.name)
                class_name = get_qualified_name(msg, ns.name)
                lines.append(f"{subindent}{local_name} = {class_name}")
        if len(lines) == start_len:
            lines.append(f"{subindent}pass")

    for ns in getattr(model, 'namespaces', []):
        emit_namespace_flat(ns, indent="", class_path=None, file_level_aliases={}, file_level_full_aliases={})
    # Assign the file-level namespace class to a module-level variable for convenient import and test access
    # This allows: from ... import <namespace> and then <namespace>.<TypeName>
    # Without this, users would have to use <namespace>.<namespace>.<TypeName>
    if getattr(model, 'file', None) and getattr(model, 'namespaces', []):
        import os
        ns_name = os.path.splitext(os.path.basename(model.file))[0]
        lines.append(f"# Assign the file-level namespace class to a module-level variable for convenient import and test access")
        lines.append(f"# This allows: from ... import {ns_name} and then {ns_name}.<TypeName>")
        lines.append(f"# Without this, users would have to use {ns_name}.{ns_name}.<TypeName>")
        lines.append(f"{ns_name} = {ns_name}")
    # Always return a string
    return "\n".join(lines)




def get_local_name(name, parent_ns=None):
    """
    Given a fully qualified name and an optional parent namespace, return the local (unprefixed) name.
    If parent_ns is provided and name starts with parent_ns + '_', strip it.
    """
    if parent_ns and name.startswith(parent_ns + "_"):
        return name[len(parent_ns) + 1:]
    return name

def get_qualified_name(obj, parent_ns=None):
    # Use only the local name for nested classes (no namespace prefix)
    # If the object has a 'local_name', use it. Otherwise, compute from 'name' and parent namespace.
    if hasattr(obj, 'local_name'):
        return obj.local_name
    name = getattr(obj, 'name', obj.name)
    if parent_ns:
        return get_local_name(name, parent_ns)
    return name


    def emit_enum_inner(enum, indent="", parent_ns=None):
        base = "Enum"
        parent_comment = None
        if enum.parent is not None:
            parent_name = getattr(enum.parent, 'name', enum.parent.name)
            parent_mod = getattr(enum.parent, 'namespace', None)
            fq_flat_name = parent_name
            import sys
            print(f"[PYGEN DEBUG] emit_enum: {enum.name} parent={fq_flat_name}", file=sys.stderr)
            parent_file_ns = None
            if hasattr(enum.parent, 'file') and enum.parent.file:
                import os
                parent_file_ns = os.path.splitext(os.path.basename(enum.parent.file))[0]
            parent_flat_name = getattr(enum.parent, 'name', parent_name)
            if parent_file_ns:
                parent_full = f"{parent_file_ns}.{parent_flat_name}"
            else:
                parent_full = parent_flat_name
            parent_comment = f"# NOTE: Intended to inherit from {parent_full} (from {parent_mod}), but Python Enum does not support Enum subclassing."
        if enum.doc:
            for line in (enum.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        if parent_comment:
            lines.append(f"{indent}{parent_comment}")
        enum_name = get_qualified_name(enum, parent_ns)
        lines.append(f"{indent}class {enum_name}({base}):")
        enum_body_lines = []
        if hasattr(enum, 'get_all_values'):
            all_values = enum.get_all_values()
        else:
            all_values = enum.values
        child_explicit = {v.name: v.value for v in enum.values if v.value is not None}
        assigned = {}
        last_value = None
        for idx, value in enumerate(all_values):
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
        emitted = set()
        for value in all_values:
            if value.name in emitted:
                continue
            emitted.add(value.name)
            if value.doc:
                for line in (value.doc or '').strip().splitlines():
                    enum_body_lines.append(f"{indent}    # {line}")
            enum_body_lines.append(f"{indent}    {value.name} = {assigned[value.name]}")
        if enum_body_lines:
            lines.extend(enum_body_lines)
        else:
            lines.append(f"{indent}    pass")
        lines.append("")
        return enum_name
        base = "Enum"
        parent_comment = None
        if enum.parent is not None:
            parent_name = getattr(enum.parent, 'name', enum.parent.name)
            parent_mod = getattr(enum.parent, 'namespace', None)
            fq_flat_name = parent_name
            import sys
            print(f"[PYGEN DEBUG] emit_enum: {enum.name} parent={fq_flat_name}", file=sys.stderr)
            parent_file_ns = None
            if hasattr(enum.parent, 'file') and enum.parent.file:
                import os
                parent_file_ns = os.path.splitext(os.path.basename(enum.parent.file))[0]
            parent_flat_name = getattr(enum.parent, 'name', parent_name)
            # Use class-as-namespace style for intended inheritance comment
            if parent_file_ns:
                parent_full = f"{parent_file_ns}.{parent_flat_name}"
            else:
                parent_full = parent_flat_name
            parent_comment = f"# NOTE: Intended to inherit from {parent_full} (from {parent_mod}), but Python Enum does not support Enum subclassing."

        if enum.doc:
            for line in (enum.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        if parent_comment:
            lines.append(f"{indent}{parent_comment}")
        # Remove all namespace prefixes up to and including the current namespace for inner class
        enum_name = enum.name
        # Build a list of possible prefixes to strip (file-level and nested namespaces)
        ns_prefixes = []
        ns = getattr(enum, 'parent_namespace', None)
        while ns is not None:
            ns_prefixes.insert(0, ns.name)
            ns = getattr(ns, 'parent_namespace', None)
        ns_prefixes.insert(0, module_name)
        prefix = '_'.join(ns_prefixes)
        if enum_name.startswith(prefix + '_'):
            enum_name = enum_name[len(prefix) + 1:]
        lines.append(f"{indent}class {enum_name}({base}):")
        # Python magic: assign enum to class dict for local lookup (for type hints)
        # This allows e.g. Command_type to be found as a local name in the class
        # Only emit the assignment if there is at least one member in the class body
        enum_body_lines = []
        # (We will fill enum_body_lines with the enum values below, then emit the assignment if needed)
        # The rest of the function will be updated to use enum_body_lines
        if hasattr(enum, 'get_all_values'):
            all_values = enum.get_all_values()
        else:
            all_values = enum.values

        child_explicit = {v.name: v.value for v in enum.values if v.value is not None}
        assigned = {}
        last_value = None
        for idx, value in enumerate(all_values):
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
            import sys
            print(f"[PYGEN ENUM DEBUG] Assign {value.name} = {val} (idx={idx}, explicit_child={value.name in child_explicit}, explicit_any={value.value is not None})", file=sys.stderr)

        emitted = set()
        for value in all_values:
            if value.name in emitted:
                continue
            emitted.add(value.name)
            if value.doc:
                for line in (value.doc or '').strip().splitlines():
                    enum_body_lines.append(f"{indent}    # {line}")
            enum_body_lines.append(f"{indent}    {value.name} = {assigned[value.name]}")
        if enum_body_lines:
            lines.extend(enum_body_lines)
        else:
            lines.append(f"{indent}    pass")
        lines.append("")
        return enum_name

        if hasattr(enum, 'get_all_values'):
            all_values = enum.get_all_values()
        else:
            all_values = enum.values

        child_explicit = {v.name: v.value for v in enum.values if v.value is not None}
        assigned = {}
        last_value = None
        for idx, value in enumerate(all_values):
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


    def emit_message(msg, indent="", parent_ns=None):
        if msg.doc:
            for line in (msg.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        lines.append(f"{indent}@dataclass")
        msg_class_name = get_qualified_name(msg, parent_ns)
        lines.append(f"{indent}class {msg_class_name}:")
        if not msg.fields:
            lines.append(f"{indent}    pass")
        else:
            for field in msg.fields:
                def py_type(field):
                    from model import FieldType
                    ftypes = field.field_types
                    trefs = field.type_refs
                    if ftypes[0] == FieldType.MAP:
                        key_py = py_type_helper(ftypes[1], trefs[1])
                        val_py = py_type_helper(ftypes[2], trefs[2])
                        return f"dict[{key_py}, {val_py}]"
                    if ftypes[0] == FieldType.ARRAY:
                        elem_py = py_type_helper(ftypes[1], trefs[1])
                        return f"list[{elem_py}]"
                    return py_type_helper(ftypes[0], trefs[0])
                def py_type_helper(ftype, tref):
                    from model import FieldType, ModelReference
                    def get_enum_type_name(enum_ref):
                        if enum_ref is None:
                            return "str"  # fallback for unresolved enum
                        ns_chain = []
                        ns = getattr(enum_ref, 'parent_namespace', None)
                        while ns is not None:
                            ns_chain.insert(0, ns.name)
                            ns = getattr(ns, 'parent_namespace', None)
                        file_ns = module_name
                        if ns_chain and ns_chain[0] != file_ns:
                            ns_chain.insert(0, file_ns)
                        elif not ns_chain:
                            ns_chain = [file_ns]
                        enum_name = getattr(enum_ref, 'name', str(enum_ref))
                        ns_prefix = '_'.join(ns_chain)
                        if enum_name.startswith(ns_prefix + '_'):
                            enum_name = enum_name[len(ns_prefix) + 1:]
                        return '.'.join(ns_chain) + '.' + enum_name
                    def find_message_in_namespaces(local_name, namespaces, parent_path=None):
                        if parent_path is None:
                            parent_path = []
                        for ns in namespaces:
                            msg_dict = getattr(ns, 'messages', [])
                            if isinstance(msg_dict, dict):
                                if local_name in msg_dict:
                                    if parent_path:
                                        path = parent_path + [ns.name, local_name]
                                        if path and path[0] == module_name:
                                            path = path[1:]
                                        return '.'.join(path)
                                    else:
                                        return local_name
                            elif isinstance(msg_dict, list):
                                msg_names = {getattr(m, 'name', None) for m in msg_dict}
                                if local_name in msg_names:
                                    if parent_path:
                                        path = parent_path + [ns.name, local_name]
                                        if path and path[0] == module_name:
                                            path = path[1:]
                                        return '.'.join(path)
                                    else:
                                        return local_name
                            nested_namespaces = getattr(ns, 'namespaces', [])
                            new_parent_path = parent_path + [ns.name] if ns.name else parent_path
                            found = find_message_in_namespaces(local_name, nested_namespaces, new_parent_path)
                            if found:
                                return found
                        return None
                    if ftype == FieldType.INT:
                        return "int"
                    if ftype == FieldType.STRING:
                        return "str"
                    if ftype == FieldType.BOOL:
                        return "bool"
                    if ftype == FieldType.FLOAT or ftype == FieldType.DOUBLE:
                        return "float"
                    if ftype == FieldType.ENUM:
                        name = get_enum_type_name(tref)
                        if name == "Any":
                            return "str"
                        return name
                    if ftype == FieldType.MESSAGE:
                        if tref is not None:
                            if hasattr(tref, 'name'):
                                return getattr(tref, 'name')
                            if hasattr(tref, 'qfn'):
                                qfn = getattr(tref, 'qfn')
                                local_name = qfn.split('::')[-1]
                                found = find_message_in_namespaces(local_name, getattr(model, 'namespaces', []))
                                if found:
                                    return found
                            if isinstance(tref, str):
                                found = find_message_in_namespaces(tref, getattr(model, 'namespaces', []))
                                if found:
                                    return found
                        raise RuntimeError(f"Unresolved message reference for field '{field.name}' in message '{getattr(msg, 'name', '?')}'. Type: {tref}")
                    if ftype == FieldType.COMPOUND:
                        compound_name = f"{getattr(msg, 'name', '?')}_{getattr(field, 'name', '?')}_Compound"
                        return compound_name
                    raise RuntimeError(f"Unresolved type for field '{field.name}' in message '{getattr(msg, 'name', '?')}'. FieldType: {ftype}, Type: {tref}")
                lines.append(f"{indent}    {field.name}: {py_type(field)}")
        lines.append("")
        if msg.doc:
            for line in (msg.doc or '').strip().splitlines():
                lines.append(f"{indent}# {line}")
        lines.append(f"{indent}@dataclass")
        msg_class_name = get_qualified_name(msg, parent_ns)
        lines.append(f"{indent}class {msg_class_name}:")
        if not msg.fields:
            lines.append(f"{indent}    pass")
        else:
            for field in msg.fields:
                # Map field_types to Python type annotations
                def py_type(field):
                    from model import FieldType
                    ftypes = field.field_types
                    trefs = field.type_refs
                    # Handle MAP: [MAP, key_type, value_type]
                    if ftypes[0] == FieldType.MAP:
                        key_py = py_type_helper(ftypes[1], trefs[1])
                        val_py = py_type_helper(ftypes[2], trefs[2])
                        return f"dict[{key_py}, {val_py}]"
                    # Handle ARRAY: [ARRAY, element_type]
                    if ftypes[0] == FieldType.ARRAY:
                        elem_py = py_type_helper(ftypes[1], trefs[1])
                        return f"list[{elem_py}]"
                    # Otherwise, single type
                    return py_type_helper(ftypes[0], trefs[0])



                def py_type_helper(ftype, tref):
                    from model import FieldType, ModelReference
                    def get_enum_type_name(enum_ref):
                        if enum_ref is None:
                            return "str"  # fallback for unresolved enum
                        # Compute fully qualified name for enums
                        # If enum_ref has parent_namespace, walk up to build the qualified name
                        ns_chain = []
                        ns = getattr(enum_ref, 'parent_namespace', None)
                        while ns is not None:
                            ns_chain.insert(0, ns.name)
                            ns = getattr(ns, 'parent_namespace', None)
                        # Always start with file-level namespace
                        file_ns = module_name
                        if ns_chain and ns_chain[0] != file_ns:
                            ns_chain.insert(0, file_ns)
                        elif not ns_chain:
                            ns_chain = [file_ns]
                        # Enum name (remove prefix as in emit_enum_inner)
                        enum_name = getattr(enum_ref, 'name', str(enum_ref))
                        ns_prefix = '_'.join(ns_chain)
                        if enum_name.startswith(ns_prefix + '_'):
                            enum_name = enum_name[len(ns_prefix) + 1:]
                        return '.'.join(ns_chain) + '.' + enum_name

                    def find_message_in_namespaces(local_name, namespaces, parent_path=None):
                        # Recursively search for a message with the given local_name in namespaces and nested namespaces
                        if parent_path is None:
                            parent_path = []
                        for ns in namespaces:
                            msg_dict = getattr(ns, 'messages', [])
                            if isinstance(msg_dict, dict):
                                if local_name in msg_dict:
                                    # If in a nested namespace, return qualified name (excluding file-level namespace)
                                    if parent_path:
                                        # Remove file-level namespace if present
                                        path = parent_path + [ns.name, local_name]
                                        if path and path[0] == module_name:
                                            path = path[1:]
                                        return '.'.join(path)
                                    else:
                                        return local_name
                            elif isinstance(msg_dict, list):
                                msg_names = {getattr(m, 'name', None) for m in msg_dict}
                                if local_name in msg_names:
                                    if parent_path:
                                        path = parent_path + [ns.name, local_name]
                                        if path and path[0] == module_name:
                                            path = path[1:]
                                        return '.'.join(path)
                                    else:
                                        return local_name
                            # Recurse into nested namespaces
                            nested_namespaces = getattr(ns, 'namespaces', [])
                            new_parent_path = parent_path + [ns.name] if ns.name else parent_path
                            found = find_message_in_namespaces(local_name, nested_namespaces, new_parent_path)
                            if found:
                                return found
                        return None

                    if ftype == FieldType.INT:
                        return "int"
                    if ftype == FieldType.STRING:
                        return "str"
                    if ftype == FieldType.BOOL:
                        return "bool"
                    if ftype == FieldType.FLOAT or ftype == FieldType.DOUBLE:
                        return "float"
                    if ftype == FieldType.ENUM:
                        # If unresolved, fallback to str
                        name = get_enum_type_name(tref)
                        if name == "Any":
                            return "str"
                        return name
                    if ftype == FieldType.MESSAGE:
                        # Try to resolve to a local class name
                        if tref is not None:
                            # If tref is an object with a name attribute
                            if hasattr(tref, 'name'):
                                return getattr(tref, 'name')
                            # If tref is a ModelReference, extract the local name from qfn
                            if hasattr(tref, 'qfn'):
                                qfn = getattr(tref, 'qfn')
                                local_name = qfn.split('::')[-1]
                                # Recursively search all namespaces for the message
                                found = find_message_in_namespaces(local_name, getattr(model, 'namespaces', []))
                                if found:
                                    return found
                            # If tref is a string and matches a message in any namespace
                            if isinstance(tref, str):
                                found = find_message_in_namespaces(tref, getattr(model, 'namespaces', []))
                                if found:
                                    return found
                        # fallback for unresolved message reference
                        raise RuntimeError(f"Unresolved message reference for field '{field.name}' in message '{getattr(msg, 'name', '?')}'. Type: {tref}")
                    if ftype == FieldType.COMPOUND:
                        # For compound fields, use the generated compound dataclass name
                        # The convention is <MessageName>_<FieldName>_Compound
                        compound_name = f"{getattr(msg, 'name', '?')}_{getattr(field, 'name', '?')}_Compound"
                        return compound_name
                    raise RuntimeError(f"Unresolved type for field '{field.name}' in message '{getattr(msg, 'name', '?')}'. FieldType: {ftype}, Type: {tref}")

                lines.append(f"{indent}    {field.name}: {py_type(field)}")
        lines.append("")


    def emit_namespace_flat(ns, indent="", class_path=None):
        # Only emit enums, messages, and nested namespaces as classes
        if class_path is None:
            class_path = []
        if ns.name:
            lines.append(f"{indent}class {ns.name}:")
            subindent = indent + "    "
            this_class_path = class_path + [ns.name]
        else:
            subindent = indent
            this_class_path = class_path[:]
        start_len = len(lines)
        enum_names = []
        msg_names = []
        enum_local_names = []
        msg_local_names = []
        for enum in getattr(ns, 'enums', []):
            enum_name = emit_enum_inner(enum, subindent, ns.name)
            if enum_name:
                enum_names.append(enum_name)
                local_name = get_local_name(enum.name, ns.name)
                # Always emit alias if local_name differs from enum_name and local_name is not empty
                if local_name and local_name != enum_name:
                    enum_local_names.append((local_name, enum_name))
        for msg in getattr(ns, 'messages', []):
            emit_message(msg, subindent, ns.name)
            msg_name = get_qualified_name(msg, ns.name)
            msg_names.append(msg_name)
            local_name = get_local_name(msg.name, ns.name)
            if local_name and local_name != msg_name:
                msg_local_names.append((local_name, msg_name))
        for nested in getattr(ns, 'namespaces', []):
            emit_namespace_flat(nested, subindent, this_class_path)
        # For file-level namespace, emit assignments for all top-level enums/messages
        if not class_path and ns.name:
            for enum_name in enum_names:
                lines.append(f"{subindent}{enum_name} = {enum_name}")
            for msg_name in msg_names:
                lines.append(f"{subindent}{msg_name} = {msg_name}")
        # For nested namespaces, emit local name assignments inside the class
        if class_path and ns.name:
            for local_name, enum_name in enum_local_names:
                lines.append(f"{subindent}{local_name} = {enum_name}")
            for local_name, msg_name in msg_local_names:
                lines.append(f"{subindent}{local_name} = {msg_name}")
        if len(lines) == start_len:
            lines.append(f"{subindent}pass")

    for ns in getattr(model, 'namespaces', []):
        emit_namespace_flat(ns, indent="", class_path=None)
    # Assign the file-level namespace class to a module-level variable for convenient import and test access
    # This allows: from ... import <namespace> and then <namespace>.<TypeName>
    # Without this, users would have to use <namespace>.<namespace>.<TypeName>
    if getattr(model, 'file', None) and getattr(model, 'namespaces', []):
        import os
        ns_name = os.path.splitext(os.path.basename(model.file))[0]
        lines.append(f"# Assign the file-level namespace class to a module-level variable for convenient import and test access")
        lines.append(f"# This allows: from ... import {ns_name} and then {ns_name}.<TypeName>")
        lines.append(f"# Without this, users would have to use {ns_name}.{ns_name}.<TypeName>")
        lines.append(f"{ns_name} = {ns_name}")
    # Always return a string
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
