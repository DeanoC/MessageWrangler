"""
Python 3 generator for MessageModel.
Outputs Python dataclasses with type annotations and Enum classes for all messages and enums.
"""
from typing import Any, Dict, List, Optional
from message_model import MessageModel, FieldType

BASIC_TYPE_TO_PY = {
    FieldType.STRING: "str",
    FieldType.INT: "int",
    FieldType.FLOAT: "float",
    FieldType.BOOL: "bool",
    FieldType.BYTE: "int",  # Could use custom type for 0-255
}

def generate_python_code(model: MessageModel, module_name: str = "messages", import_modules=None):
    # List of Python built-in type names and reserved words to avoid as field names
    PYTHON_RESERVED_NAMES = {
        'dict', 'list', 'set', 'tuple', 'int', 'float', 'str', 'bool', 'bytes', 'object', 'type', 'field', 'class', 'def', 'from', 'import', 'as', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'lambda', 'return', 'yield', 'del', 'pass', 'break', 'continue', 'assert', 'raise', 'global', 'nonlocal', 'not', 'and', 'or', 'is', 'in', 'None', 'True', 'False', 'async', 'await', 'print', 'super', 'self', 'property', 'staticmethod', 'classmethod', 'open', 'input', 'id', 'sum', 'min', 'max', 'abs', 'all', 'any', 'bin', 'hex', 'oct', 'len', 'map', 'filter', 'zip', 'range', 'enumerate', 'reversed', 'sorted', 'slice', 'next', 'iter', 'eval', 'exec', 'compile', 'format', 'vars', 'locals', 'globals', 'hasattr', 'setattr', 'getattr', 'delattr', 'isinstance', 'issubclass', 'callable', 'dir', 'help', 'memoryview', 'object', 'repr', 'staticmethod', 'type', 'vars', 'Exception', 'BaseException', 'Warning', 'UserWarning', 'DeprecationWarning', 'SyntaxWarning', 'RuntimeWarning', 'FutureWarning', 'PendingDeprecationWarning', 'ImportWarning', 'UnicodeWarning', 'BytesWarning', 'ResourceWarning',
    }

    def safe_field_name(name):
        return name + '_' if name in PYTHON_RESERVED_NAMES else name
    lines = []
    # We'll add Any to the import only if needed
    typing_imports = {"List", "Dict", "Optional"}
    needs_any = False
    if import_modules is None:
        import_modules = []
    # --- Recursive generation bookkeeping removed: not needed in single-file-per-def mode ---
    # --- Collect types defined in this file ---
    defined_types = set(enum.name for enum in model.enums.values())
    defined_types.update(msg.name for msg in model.messages.values())
    # --- Collect compound types to generate ---
    compound_types = set()
    defined_compound_types = set()
    # --- Collect referenced types ---
    referenced_types = set()
    referenced_type_to_module = dict()
    # Helper to convert C++-style or namespaced names to valid Python identifiers
    def py_identifier(name):
        # Convert namespaced names (e.g., Base::Command) to valid Python identifiers (Base_Command)
        if not name:
            return ''
        if isinstance(name, str):
            return ''.join([c if c.isalnum() or c == '_' else '_' for c in name.replace('::', '_')])
        return str(name)

    # Helper to check if a type is a basic type (by FieldType or mapped Python type or value string)
    def is_basic_type(type_name):
        if type_name in BASIC_TYPE_TO_PY:
            return True
        if type_name in BASIC_TYPE_TO_PY.values():
            return True
        # Also check for FieldType values (e.g., 'string', 'int', etc.)
        if type_name in {ft.value for ft in BASIC_TYPE_TO_PY.keys()}:
            return True
        return False

    # Collect parent classes
    for msg in model.messages.values():
        parent_name = msg.parent
        if parent_name and parent_name not in defined_types and not is_basic_type(parent_name):
            # Only add if it's a user-defined type
            if parent_name in model.enums or parent_name in model.messages:
                referenced_types.add(parent_name)
                referenced_type_to_module[parent_name] = parent_name

    # Collect field types and compound types
    for msg in model.messages.values():
        for field in msg.fields:
            # Enums
            if field.field_type == FieldType.ENUM and field.enum_type and field.enum_type not in defined_types and not is_basic_type(field.enum_type):
                if field.enum_type in model.enums:
                    referenced_types.add(field.enum_type)
                    referenced_type_to_module[field.enum_type] = field.enum_type
            # Message references
            if field.field_type == FieldType.MESSAGE_REFERENCE and field.message_reference and field.message_reference not in defined_types and not is_basic_type(field.message_reference):
                if field.message_reference in model.messages:
                    referenced_types.add(field.message_reference)
                    referenced_type_to_module[field.message_reference] = field.message_reference
            # Compounds (reference to another message)
            if field.field_type == FieldType.COMPOUND and field.compound_reference and field.compound_reference not in defined_types and not is_basic_type(field.compound_reference):
                if field.compound_reference in model.messages:
                    referenced_types.add(field.compound_reference)
                    referenced_type_to_module[field.compound_reference] = field.compound_reference
            # Compound fields (inline compound dataclasses)
            if field.field_type == FieldType.COMPOUND:
                cname = f"{msg.name}_{field.name}_Compound"
                compound_types.add((msg.name, field.name, cname, field))
                defined_compound_types.add(cname)
            # Maps
            if field.field_type == FieldType.MAP:
                t = getattr(field, 'map_value_type', None)
                # If it's a user type (not a basic type), add
                t_name = None
                if isinstance(t, FieldType):
                    t_name = t.value
                elif isinstance(t, str):
                    t_name = t
                if t_name and not is_basic_type(t_name) and t_name not in defined_types:
                    # Only add if it's a user-defined type
                    if t_name in model.enums or t_name in model.messages:
                        referenced_types.add(t_name)
                        referenced_type_to_module[t_name] = t_name

    # --- Collect referenced compound types used in fields (for cross-file imports) ---
    referenced_compound_types = set()
    for msg in model.messages.values():
        for field in msg.fields:
            if field.field_type == FieldType.COMPOUND:
                cname = f"{msg.name}_{field.name}_Compound"
                # If this compound type is not defined in this file, it must be imported
                if cname not in defined_compound_types:
                    referenced_compound_types.add(cname)

    # No recursive file generation: only generate code for the current model/module_name
    # Check if any field uses Any
    for msg in model.messages.values():
        for field in msg.fields:
            if python_type_for_field(field, model, msg.name, check_any=True) == "Any":
                needs_any = True
    # Always emit future annotations import for forward references
    lines.append("from __future__ import annotations\n")
    typing_line = "from typing import " + ", ".join(sorted(list(typing_imports) + (["Any"] if needs_any else [])))
    lines.append(f"from dataclasses import dataclass, field\nfrom enum import Enum\n{typing_line}\n")
    # --- Emit Python imports for imported modules ---
    # Map parent class references to their import modules
    parent_imports = set()
    parent_class_to_module = {}
    # For each message, if it has a parent, determine if the parent is from an import
    for msg in model.messages.values():
        if msg.parent:
            # Parent may be namespaced, e.g., Base::Command
            parent = msg.parent
            # If parent is namespaced, the first part is the import alias
            if '::' in parent:
                import_alias, parent_type = parent.split('::', 1)
                # Find the import module for this alias
                for import_mod in import_modules:
                    # Match alias to import_mod (by convention, import_mod is the filename without extension)
                    if import_mod.lower() == import_alias.lower():
                        parent_imports.add(import_mod)
                        parent_class_to_module[parent] = import_mod
            else:
                # Parent is local or from another import
                pass
    # Emit import for parent modules
    for import_mod in import_modules:
        lines.append(f"from .{import_mod} import *")
    # Emit import for referenced compound types from other modules
    # For each referenced compound type, try to import it from any import module
    for cname in referenced_compound_types:
        # Try to find which import module defines this compound type
        for import_mod in import_modules:
            # By convention, compound types are defined in the module if the .def file defines the message/field
            # We can't know for sure here, but we can import * from all modules, or import the class directly
            # For now, import the class directly from the module
            lines.append(f"from .{import_mod} import {cname}")
    if import_modules or referenced_compound_types:
        lines.append("")

    # --- Emit enums (including inline/field-level enums) ---
    # Collect inline/field-level enums
    inline_enums = []
    for msg in model.messages.values():
        for field in msg.fields:
            if field.field_type == FieldType.ENUM and hasattr(field, 'enum_values') and field.enum_values:
                # Inline/field-level enum
                enum_class_name = f"{msg.name}_{field.name}_Enum" if not hasattr(field, 'enum_type') or not field.enum_type else field.enum_type.replace('::', '_')
                inline_enums.append((enum_class_name, field.enum_values, getattr(field, 'description', None)))
    # Emit top-level enums
    for enum in model.enums.values():
        if getattr(enum, 'description', None):
            # Emit enum doc comment as Python comment
            for line in enum.description.strip().splitlines():
                lines.append(f"# {line}")
        lines.append(f"class {enum.name}(Enum):")
        for value in enum.values:
            if getattr(value, 'description', None):
                for line in value.description.strip().splitlines():
                    lines.append(f"    # {line}")
            lines.append(f"    {value.name} = {value.value}")
        lines.append("")
    # Emit inline/field-level enums
    for enum_class_name, enum_values, description in inline_enums:
        if description:
            for line in description.strip().splitlines():
                lines.append(f"# {line}")
        lines.append(f"class {enum_class_name}(Enum):")
        for value in enum_values:
            lines.append(f"    {value.name} = {value.value}")
        lines.append("")

    # --- Emit messages ---
    # Build a set of all possible parent class identifiers that should be available in this module
    parent_identifiers = set()
    for msg in model.messages.values():
        if msg.parent:
            parent_identifiers.add(py_identifier(msg.parent))

    def parent_class_name(parent):
        # For parent references like Base::BaseMessage, return 'BaseMessage' if it's a message, else ''
        if not parent:
            return ''
        # If parent is namespaced, get the type name (last part after all '::')
        if isinstance(parent, str) and '::' in parent:
            type_name = parent.split('::')[-1]
        else:
            type_name = parent
        # Only emit inheritance if parent is a message/class, not an enum
        if type_name in model.messages:
            return type_name
        # If parent is not a message (could be an enum or not found), do not emit inheritance
        return ''

    for msg in model.messages.values():
        if getattr(msg, 'description', None):
            for line in msg.description.strip().splitlines():
                lines.append(f"# {line}")
        parent_cls = parent_class_name(msg.parent)
        parent_str = f"({parent_cls})" if parent_cls else ""
        lines.append(f"@dataclass")
        lines.append(f"class {py_identifier(msg.name)}{parent_str}:")
        if not msg.fields:
            lines.append(f"    pass")
        for field in msg.fields:
            # Field description as comment
            if getattr(field, 'description', None):
                for line in field.description.strip().splitlines():
                    lines.append(f"    # {line}")
            # Field type
            type_str = python_type_for_field(field, model, msg.name)
            # If type_str is a namespaced type, use only the type name (not py_identifier)
            def type_name_from_ref(ref):
                if not ref:
                    return ''
                if isinstance(ref, str) and '::' in ref:
                    return ref.split('::', 1)[1]
                return ref
            if isinstance(type_str, str) and '::' in type_str:
                type_str = type_name_from_ref(type_str)
            default_str = python_default_for_field(field)
            lines.append(f"    {safe_field_name(field.name)}: {type_str}{default_str}")
        lines.append("")

    # Emit compound dataclasses for all compound_types
    for msg_name, field_name, cname, field in sorted(compound_types):
        lines.append(f"@dataclass")
        lines.append(f"class {cname}:")
        if not getattr(field, 'compound_components', None):
            lines.append(f"    pass")
        else:
            for comp in field.compound_components:
                # Use the base type for all components
                base_type = BASIC_TYPE_TO_PY.get(field.compound_base_type, field.compound_base_type)
                lines.append(f"    {safe_field_name(comp)}: {base_type} = 0")
        lines.append("")

    return "\n".join(lines)
# Helper function to generate all .py files for a set of .def files and their imports
import os
import re
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree

def generate_all_python_files(def_files, output_dir):
    """
    For each .def file, generate a .py file with all its types, and for each import, generate the corresponding .py file if not already present.
    def_files: list of paths to .def files to process (main files)
    output_dir: directory to write generated .py files
    """
    generated = set()
    def parse_imports(def_path):
        imports = []
        with open(def_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r'\s*import\s+"([^"]+)"\s+as\s+(\w+)', line)
                if m:
                    import_path, import_mod = m.group(1), m.group(2)
                    # Normalize path
                    import_path = os.path.normpath(os.path.join(os.path.dirname(def_path), import_path))
                    imports.append((import_path, import_mod))
        return imports

    def process_def(def_path):
        if def_path in generated:
            return
        imports = parse_imports(def_path)
        import_mods = []
        for import_path, import_mod in imports:
            process_def(import_path)
            import_mods.append(os.path.splitext(os.path.basename(import_path))[0])
        # Parse and build model
        with open(def_path, encoding="utf-8") as f:
            dsl = f.read()
        tree = parse_message_dsl(dsl)
        model = build_model_from_lark_tree(tree)
        module_name = os.path.splitext(os.path.basename(def_path))[0]
        code = generate_python_code(model, module_name, import_mods)
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{module_name}.py")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(code)
        generated.add(def_path)

    for def_path in def_files:
        process_def(def_path)

def python_type_for_field(field, model, msg_name, check_any=False):
    # Basic
    ft = field.field_type
    t = None
    # Only allow FieldType, never raw string
    assert isinstance(ft, FieldType), f"Field '{field.name}' in message '{msg_name}' has non-enum field_type: {repr(ft)}"
    if ft in BASIC_TYPE_TO_PY:
        t = BASIC_TYPE_TO_PY[ft]
        if field.is_array:
            return f"List[{t}]"
        if field.is_map:
            return f"Dict[str, {t}]"
        return t
    # Enum
    if field.field_type == FieldType.ENUM:
        t = field.enum_type or field.name
        t_py = t
        if isinstance(t, str) and '::' in t:
            t_py = ''.join([c if c.isalnum() or c == '_' else '_' for c in t.replace('::', '_')])
        if field.is_array:
            return f"List[{t_py}]"
        if field.is_map:
            return f"Dict[str, {t_py}]"
        return t_py
    # Message reference
    if field.field_type == FieldType.MESSAGE_REFERENCE:
        t = field.message_reference or field.name
        # If t is a basic type string (e.g., 'string', 'int'), map to Python type
        # t may be a string like 'string', 'int', etc., or a user-defined type
        # Try to map t to FieldType and then to BASIC_TYPE_TO_PY
        py_type = None
        if isinstance(t, str):
            # Try to match FieldType by value
            for ft, py in BASIC_TYPE_TO_PY.items():
                if t == ft.value:
                    py_type = py
                    break
        if py_type:
            if field.is_array:
                return f"List[{py_type}]"
            if field.is_map:
                return f"Dict[str, {py_type}]"
            return py_type
        # Otherwise, treat as user-defined type
        t_py = t
        if isinstance(t, str) and '::' in t:
            t_py = ''.join([c if c.isalnum() or c == '_' else '_' for c in t.replace('::', '_')])
        if field.is_array:
            return f"List[{t_py}]"
        if field.is_map:
            return f"Dict[str, {t_py}]"
        return t_py
    # Compound
    if field.field_type == FieldType.COMPOUND:
        cname = f"{msg_name}_{field.name}_Compound"
        cname_py = ''.join([c if c.isalnum() or c == '_' else '_' for c in cname.replace('::', '_')])
        if field.is_array:
            return f"List[{cname_py}]"
        if field.is_map:
            return f"Dict[str, {cname_py}]"
        return cname_py
    # Map fallback
    if field.field_type == FieldType.MAP:
        # Use map_value_type as the value type if available
        t = getattr(field, 'map_value_type', None)
        print(f"[DEBUG] python_type_for_field: field={field.name}, map_value_type={repr(t)} (type={type(t)})")
        # If t is a FieldType, use the mapping; if it's a string, try to resolve; else fallback to Any
        if isinstance(t, FieldType):
            t_str = BASIC_TYPE_TO_PY.get(t, t.value)
        elif isinstance(t, str):
            # Try to resolve as FieldType string
            try:
                t_enum = FieldType(t.lower())
                t_str = BASIC_TYPE_TO_PY.get(t_enum, t_enum.value)
            except Exception:
                t_str = t if t.strip() else "Any"
        else:
            t_str = "Any"
        # If t_str is a message or enum name, keep as is
        # If t_str is still not valid, fallback to Any
        if not t_str or not str(t_str).strip():
            t_str = "Any"
        print(f"[DEBUG] python_type_for_field: field={field.name}, resolved map value type={t_str}")
        return f"Dict[str, {t_str}]" if not check_any else "Any"
    return "Any"

def python_default_for_field(field):
    # If a default value is specified in the model, use it
    if hasattr(field, 'default_value') and field.default_value is not None:
        # For strings, wrap in quotes; for bool, use True/False; for others, use as is
        v = field.default_value
        if isinstance(v, str):
            return f" = '{v}'"
        elif isinstance(v, bool):
            return f" = {str(v)}"
        elif v is None:
            return " = None"
        else:
            return f" = {v}"
    # Optional fields
    if hasattr(field, 'modifiers') and "optional" in field.modifiers:
        return " = None"
    # Array/Map default
    if getattr(field, 'is_array', False):
        return " = field(default_factory=list)"
    if getattr(field, 'is_map', False):
        return " = field(default_factory=dict)"
    # Type-based sensible defaults
    from message_model import FieldType
    if hasattr(field, 'field_type'):
        ft = field.field_type
        if ft == FieldType.STRING:
            return " = ''"
        if ft == FieldType.INT:
            return " = 0"
        if ft == FieldType.FLOAT:
            return " = 0.0"
        if ft == FieldType.BOOL:
            return " = False"
        if ft == FieldType.BYTE:
            return " = 0"
        # For enums, references, compounds, maps, etc., default to None
        if ft in (FieldType.ENUM, FieldType.MESSAGE_REFERENCE, FieldType.COMPOUND, FieldType.MAP):
            return " = None"
    # Fallback
    return " = None"
