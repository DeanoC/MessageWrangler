"""
TypeScript generator for Model (new system).
Outputs TypeScript interfaces and enums for all messages and enums in the Model.
"""
from model import Model
from typing import List, Callable
import sys
from model_transforms.flatten_imports_transform import FlattenImportsTransform
from model_transforms.assign_unique_names_transform import AssignUniqueNamesTransform
from model_transforms.flatten_enums_transform import FlattenEnumsTransform

def generate_typescript_code(model: Model, module_name: str = "messages", transforms: List[Callable] = None):
    # --- Model transform: assign dummy enums for missing options types ---
    from model_transforms.assign_dummy_option_enums_transform import AssignDummyOptionEnumsTransform
    model = AssignDummyOptionEnumsTransform().transform(model)
    # --- Ensure all namespaces have correct parent pointers ---
    def set_namespace_parents(namespaces, parent=None):
        for ns in namespaces:
            setattr(ns, 'parent', parent)
            set_namespace_parents(getattr(ns, 'namespaces', []), ns)
    set_namespace_parents(getattr(model, 'namespaces', []))
    # Apply enum value prefixing transform for TypeScript to avoid enum value name collisions
    from model_transforms.prefix_enum_value_names_transform import PrefixEnumValueNamesTransform
    model = PrefixEnumValueNamesTransform().transform(model)
    # Track emitted inline enums to avoid duplicates
    emitted_inline_enums = set()

    # Apply unique name assignment, enum value assignment, and enum flattening
    from model_transforms.assign_enum_values_transform import AssignEnumValuesTransform
    model = AssignUniqueNamesTransform().transform(model)
    model = AssignEnumValuesTransform().transform(model)
    model = FlattenEnumsTransform().transform(model)

    lines = []

    # --- Collect external type references for imports using shared utility ---
    from generators.generator_utils import collect_referenced_imports
    import os
    current_file_base = None
    if hasattr(model, 'file') and model.file:
        current_file_base = os.path.splitext(os.path.basename(model.file))[0]

    # Map file_base to namespace name (assume top-level namespace name matches file_base)
    filebase_to_ns = {}
    for ns in getattr(model, 'imports', {}).values():
        if hasattr(ns, 'file') and hasattr(ns, 'namespaces'):
            ns_file_base = os.path.splitext(os.path.basename(ns.file))[0]
            if ns.namespaces:
                filebase_to_ns[ns_file_base] = ns.namespaces[0].name

    referenced_imports = collect_referenced_imports(model)
    for import_file in sorted(referenced_imports):
        ns_name = filebase_to_ns.get(import_file, import_file)
        lines.append(f"import * as {ns_name} from './{import_file}';")
    if referenced_imports:
        lines.append("")

    def get_local_name(name, parent_ns=None, keep_full_for_options=False):
        # For options and promoted types, use CamelCase with no underscores (new convention)
        if keep_full_for_options:
            name = name.replace('::', '')
            parts = name.split('_')
            # Use str[0].upper() + str[1:] to preserve original casing after the first letter
            def camel_part(part):
                return part[:1].upper() + part[1:] if part else ''
            name = ''.join(camel_part(part) for part in parts)
            return name
        # Default: return only the base name (after last '::' or '_'), no underscores allowed
        if '::' in name:
            name = name.split('::')[-1]
        if '_' in name:
            name = name.split('_')[-1]
        name = name.replace('_', '')
        return name

    def emit_enum(enum, indent="", parent_ns=None, is_options=False):
        enum_name = get_local_name(enum.name, parent_ns)
        if enum.doc:
            for line in (enum.doc or '').strip().splitlines():
                lines.append(f"{indent}// {line}")
        all_values = enum.get_all_values() if hasattr(enum, 'get_all_values') else enum.values
        assigned = {}
        if is_options:
            # Assign bit values: 1, 2, 4, 8, ...
            for idx, value in enumerate(all_values):
                if value.value is not None:
                    val = value.value
                else:
                    val = 1 << idx
                assigned[value.name] = val
            lines.append(f"{indent}export enum {enum_name} {{")
            for value in all_values:
                if value.doc:
                    for line in (value.doc or '').strip().splitlines():
                        lines.append(f"{indent}    // {line}")
                lines.append(f"{indent}    {value.name} = {assigned[value.name]},")
            lines.append(f"{indent}}}\n")
        elif getattr(enum, 'is_open', False):
            value_literals = [str(v.value) for v in all_values]
            type_union = " | ".join(value_literals + ["number"])
            lines.append(f"{indent}export type {enum_name} = {type_union};\n")
        else:
            lines.append(f"{indent}export enum {enum_name} {{")
            last_value = None
            for idx, value in enumerate(all_values):
                if value.value is not None:
                    val = value.value
                else:
                    val = last_value + 1 if last_value is not None else 0
                assigned[value.name] = val
                last_value = val
            for value in all_values:
                if value.doc:
                    for line in (value.doc or '').strip().splitlines():
                        lines.append(f"{indent}    // {line}")
                lines.append(f"{indent}    {value.name} = {assigned[value.name]},")
            lines.append(f"{indent}}}\n")

    # Track dummy enums needed per namespace
    pending_dummy_enums = {}
    def ts_type(field, parent_ns=None):
        ftypes = field.field_types
        trefs = field.type_refs
        # Map field types to TypeScript types
        if ftypes[0].name == "MAP":
            key_ts = ts_type_helper(ftypes[1], trefs[1], parent_ns, field)
            val_ts = ts_type_helper(ftypes[2], trefs[2], parent_ns, field)
            return f"Record<{key_ts}, {val_ts}>"
        if ftypes[0].name == "ARRAY":
            elem_ts = ts_type_helper(ftypes[1], trefs[1], parent_ns, field)
            return f"{elem_ts}[]"
        # Handle options type
        if ftypes[0].name == "OPTIONS":
            tref = trefs[0] if trefs and len(trefs) > 0 else None
            type_name = None
            if tref is not None:
                if hasattr(tref, 'name') and tref.name:
                    type_name = get_local_name(tref.name, parent_ns, keep_full_for_options=True)
                elif hasattr(tref, 'qfn') and tref.qfn:
                    type_name = get_local_name(tref.qfn.split('::')[-1], parent_ns, keep_full_for_options=True)
            if not type_name and hasattr(field, 'type_names') and field.type_names:
                for tname in field.type_names:
                    if tname and tname.lower() not in ("int", "string", "bool", "float", "double", "map", "array", "options", "compound"):
                        type_name = get_local_name(tname, parent_ns, keep_full_for_options=True)
                        break
            if type_name:
                all_emitted_types = set(emitted_inline_enums)
                for ns in getattr(model, 'namespaces', []):
                    for enum in getattr(ns, 'enums', []):
                        all_emitted_types.add(get_local_name(enum.name, ns.name, keep_full_for_options=True))
                fallback_type_name = get_local_name(type_name, parent_ns, keep_full_for_options=True)
                # Find the correct namespace key for this field
                # If the field is in a message, use the message's parent namespace (object), else use parent_ns
                ns_key = None
                # Always walk up the namespace chain from the field's parent.namespace, including the root
                ns_obj = None
                if hasattr(field, 'parent') and hasattr(field.parent, 'namespace') and field.parent.namespace:
                    ns_obj = field.parent.namespace
                elif parent_ns:
                    # Try to find the namespace object by name if only parent_ns is given
                    # Look up the root namespace in the model
                    ns_obj = None
                    for ns_candidate in getattr(model, 'namespaces', []):
                        if getattr(ns_candidate, 'name', None) == parent_ns:
                            ns_obj = ns_candidate
                            break
                ns_names = []
                while ns_obj is not None:
                    ns_names.append(getattr(ns_obj, 'name', str(ns_obj)))
                    ns_obj = getattr(ns_obj, 'parent', None)
                ns_names = [n for n in reversed(ns_names) if n]
                ns_key = '.'.join(ns_names) if ns_names else (parent_ns or "__root__")
                # Ensure ns_key is always rooted at the model's root namespace
                if hasattr(model, 'namespaces') and model.namespaces:
                    root_ns = getattr(model.namespaces[0], 'name', None)
                    if root_ns and ns_key and not ns_key.startswith(root_ns):
                        ns_key = f"{root_ns}.{ns_key}" if ns_key else root_ns
                # DEBUG: Print the ns_key and fallback_type_name for dummy enum collection
                # print(f"[DUMMY ENUM COLLECT] ns_key={ns_key} type={fallback_type_name}")
                if fallback_type_name not in all_emitted_types:
                    pending_dummy_enums.setdefault(ns_key, set()).add(fallback_type_name)
                return fallback_type_name
            return "number"
        return ts_type_helper(ftypes[0], trefs[0], parent_ns, field)

    def ts_type_helper(ftype, tref, parent_ns=None, field=None):
        # DEBUG: Print field info for enum fields
        # Map model FieldType to TypeScript types
        if ftype.name == "INT":
            return "number"
        if ftype.name == "STRING":
            return "string"
        if ftype.name == "BOOL":
            return "boolean"
        if ftype.name == "FLOAT" or ftype.name == "DOUBLE":
            return "number"
        if ftype.name == "ENUM":
            # Use namespace import only for external enums, otherwise use local name
            if tref is not None and hasattr(tref, 'name'):
                ref_file = getattr(tref, 'file', None)
                ref_ns = getattr(tref, 'namespace', None)
                if ref_file:
                    ref_file_base = os.path.splitext(os.path.basename(ref_file))[0]
                    if ref_file_base != current_file_base:
                        ns_name = filebase_to_ns.get(ref_file_base, ref_file_base)
                        # If the referenced enum is inside a namespace, qualify it fully: ns.ns.EnumName
                        if ref_ns:
                            return f"{ns_name}.{ref_ns}.{get_local_name(tref.name, parent_ns)}"
                        else:
                            return f"{ns_name}.{get_local_name(tref.name, parent_ns)}"
                # If the referenced enum is in a nested namespace, qualify it
                if ref_ns and ref_ns != parent_ns:
                    return f"{ref_ns}.{get_local_name(tref.name, parent_ns)}"
                return get_local_name(tref.name, parent_ns)
            # If inline enum, generate and emit the enum type
            if field is not None and getattr(field, 'inline_values', []):
                parent_name = get_local_name(field.parent.name, parent_ns) if hasattr(field, 'parent') and field.parent else "Parent"
                enum_type_name = f"{parent_name}_{get_local_name(field.name, parent_ns)}"
                if enum_type_name not in emitted_inline_enums:
                    emitted_inline_enums.add(enum_type_name)
                    lines.append(f"    export enum {enum_type_name} {{")
                    for v in field.inline_values:
                        lines.append(f"        {v.name} = {v.value},")
                    lines.append(f"    }}\n")
                return enum_type_name
            # Try to use type_names if available and not a primitive
            if field is not None and hasattr(field, 'type_names'):
                for tname in field.type_names:
                    if tname and tname.lower() not in ("int", "string", "bool", "float", "double", "map", "array", "options", "compound"):
                        # If tname looks like a QFN (e.g., 'Base::Command.type'), extract the last part
                        if '::' in tname:
                            last = tname.split('::')[-1]
                            # If it has a dot (e.g., Command.type), take the part before the dot
                            if '.' in last:
                                last = last.split('.')[0]
                            return get_local_name(last, parent_ns)
                        # If it has a dot (e.g., Command.type), take the part before the dot
                        if '.' in tname:
                            last = tname.split('.')[0]
                            return get_local_name(last, parent_ns)
                        return get_local_name(tname, parent_ns)
            # Fallback: use the field name if it matches an enum in the same namespace
            if field is not None and hasattr(field, 'parent') and hasattr(field.parent, 'enums'):
                for enum in getattr(field.parent, 'enums', []):
                    if enum.name == field.name or get_local_name(enum.name, parent_ns) == field.name:
                        return get_local_name(enum.name, parent_ns)
            # Fallback: emit error or 'never' for unresolved enum references
            if field is not None:
                print(f"[TSGEN ERROR] Unresolved enum type for field '{getattr(field, 'name', None)}' in parent '{getattr(field.parent, 'name', None) if field and hasattr(field, 'parent') else None}'. type_names={getattr(field, 'type_names', None)}", file=sys.stderr)
            return "never /* UNRESOLVED_ENUM */"
        if ftype.name == "MESSAGE":
            if tref is not None and hasattr(tref, 'name'):
                ref_file = getattr(tref, 'file', None)
                ref_ns = getattr(tref, 'namespace', None)
                model_ns = None
                if hasattr(model, 'file') and model.file:
                    model_ns = os.path.splitext(os.path.basename(model.file))[0]
                # If the referenced type is in a nested namespace, qualify it
                if ref_ns and ref_ns != parent_ns:
                    return f"{ref_ns}.{get_local_name(tref.name, parent_ns)}"
                return get_local_name(tref.name, parent_ns)
            # Fallback: use type_names if available and not a primitive
            if field is not None and hasattr(field, 'type_names'):
                for tname in field.type_names:
                    if tname and tname.lower() not in ("int", "string", "bool", "float", "double", "map", "array", "options", "compound"):
                        # If tname looks like a QFN (e.g., 'Base::Command.type'), extract the last part
                        if '::' in tname:
                            parts = tname.split('::')
                            if len(parts) > 1:
                                ns_part = parts[-2]
                                name_part = parts[-1]
                                return f"{ns_part}.{get_local_name(name_part, parent_ns)}"
                            else:
                                return get_local_name(parts[-1], parent_ns)
                        return get_local_name(tname, parent_ns)
            # Fallback: emit error or 'never' for unresolved message references
            if field is not None:
                print(f"[TSGEN ERROR] Unresolved message type for field '{getattr(field, 'name', None)}' in parent '{getattr(field.parent, 'name', None) if field and hasattr(field, 'parent') else None}'. type_names={getattr(field, 'type_names', None)}", file=sys.stderr)
            return "never /* UNRESOLVED_MESSAGE */"
        if ftype.name == "COMPOUND":
            if field is not None and hasattr(field, 'parent') and hasattr(field, 'name'):
                return f"{get_local_name(field.parent.name, parent_ns)}_{get_local_name(field.name, parent_ns)}_Compound"
            raise RuntimeError(f"Unresolved COMPOUND type for field '{getattr(field, 'name', None)}' in parent '{getattr(field.parent, 'name', None) if field and hasattr(field, 'parent') else None}'")
        raise RuntimeError(f"Unresolved or unknown type '{ftype.name}' for field '{getattr(field, 'name', None)}' in parent '{getattr(field.parent, 'name', None) if field and hasattr(field, 'parent') else None}'")

    def emit_message(msg, indent="", parent_ns=None):
        if msg.doc:
            for line in (msg.doc or '').strip().splitlines():
                lines.append(f"{indent}// {line}")
        msg_name = get_local_name(msg.name, parent_ns)
        lines.append(f"{indent}export interface {msg_name} {{")
        if not msg.fields:
            lines.append(f"{indent}    // No fields")
        else:
            for field in msg.fields:
                # If the field type emits a dummy enum/type, ensure it is emitted at the correct indent
                ts_type_str = ts_type(field, parent_ns)
                # If the last line is a dummy enum, fix its indent
                if lines and lines[-1].startswith("export enum ") and lines[-1].endswith("{ /* AUTO-GENERATED DUMMY */ }\n"):
                    # Move the dummy enum before the field declaration, and fix indent
                    dummy_enum = lines.pop()
                    lines.append(f"{indent}    {dummy_enum.strip()}")
                lines.append(f"{indent}    {field.name}: {ts_type_str};")
        lines.append(f"{indent}}}\n")

    def emit_namespace(ns, indent=""):
        # Build the full namespace path for this ns
        ns_obj = ns
        ns_names = []
        while ns_obj is not None:
            ns_names.append(getattr(ns_obj, 'name', str(ns_obj)))
            ns_obj = getattr(ns_obj, 'parent', None)
        ns_names = [n for n in reversed(ns_names) if n]
        ns_key = '.'.join(ns_names) if ns_names else (getattr(ns, 'name', None) or "__root__")
        ns_name = ns.name
        has_content = bool(ns.enums or ns.messages or ns.namespaces or getattr(ns, 'options', []))
        if ns_name:
            lines.append(f"{indent}export namespace {ns_name} {{")
            indent += "    "
        emitted_enum_names = set()
        # Emit options as enums with bit values
        for opts in getattr(ns, 'options', []):
            if opts.get('values_raw'):
                class OptEnum:
                    def __init__(self, name, values, doc=None):
                        self.name = name
                        self.values = values
                        self.doc = doc
                    def get_all_values(self):
                        return self.values
                class OptValue:
                    def __init__(self, name, value, doc=None):
                        self.name = name
                        self.value = value
                        self.doc = doc
                values = []
                for idx, v in enumerate(opts['values_raw']):
                    val = v.get('value')
                    if val is None:
                        val = 1 << idx
                    values.append(OptValue(v['name'], val, v.get('doc')))
                promoted_name = opts.get('promoted_name') or opts.get('name')
                opt_enum = OptEnum(promoted_name, values, opts.get('doc'))
                emit_enum(opt_enum, indent, ns_name, is_options=True)
        # Emit any pending dummy enums for this namespace
        # Build the full namespace path for this ns
        ns_obj = ns
        ns_names = []
        while ns_obj is not None:
            ns_names.append(getattr(ns_obj, 'name', str(ns_obj)))
            ns_obj = getattr(ns_obj, 'parent', None)
        ns_names = [n for n in reversed(ns_names) if n]  # filter out empty names
        ns_key = '.'.join(ns_names) if ns_names else (ns_name or "__root__")
        # DEBUG: Print the ns_key for dummy enum emission
        # print(f"[DUMMY ENUM EMIT] ns_key={ns_key} pending={pending_dummy_enums.get(ns_key, set())}")
        # Emit dummy enums for ModelTransform-inserted dummy enums (no values)
        for enum in getattr(ns, 'enums', []):
            if getattr(enum, 'is_dummy', False):
                lines.append(f"{indent}export enum {get_local_name(enum.name, ns_name)} {{ /* AUTO-GENERATED DUMMY */ }}\n")
        for dummy_enum in pending_dummy_enums.get(ns_key, set()):
            lines.append(f"{indent}export enum {dummy_enum} {{ /* AUTO-GENERATED DUMMY */ }}\n")
        for enum in getattr(ns, 'enums', []):
            enum_local_name = get_local_name(enum.name, ns_name)
            if enum_local_name in emitted_enum_names:
                continue  # Skip duplicate
            emit_enum(enum, indent, ns_name)
            emitted_enum_names.add(enum_local_name)
        for msg in getattr(ns, 'messages', []):
            emit_message(msg, indent, ns_name)
        for nested in getattr(ns, 'namespaces', []):
            emit_namespace(nested, indent)
        if ns_name:
            indent = indent[:-4]
            lines.append(f"{indent}}}\n")

    for ns in getattr(model, 'namespaces', []):
        emit_namespace(ns)

    return "\n".join(lines)

def write_typescript_file(model: Model, out_path):
    code = generate_typescript_code(model)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)

# TESTS
if __name__ == "__main__":
    import os
    from def_file_loader import load_early_model_with_imports
    from earlymodel_to_model import early_model_to_model

    def test_typescript_generator():
        test_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "def")
        for fname in os.listdir(test_dir):
            if not fname.endswith(".def") or "invalid" in fname or "unresolved" in fname:
                continue
            main_path = os.path.join(test_dir, fname)
            early_main, all_early_models = load_early_model_with_imports(main_path)
            model_main = early_model_to_model(early_main)
            ts_code = generate_typescript_code(model_main)
            assert ts_code.strip(), f"No TypeScript code generated for {fname}"
            print(f"[PASS] {fname}")
    test_typescript_generator()
