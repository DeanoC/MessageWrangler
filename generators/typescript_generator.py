"""
TypeScript code generator for MessageWrangler message definitions.
Mirrors the structure and features of the Python v3 generator.
"""

from typing import List, Dict, Set, Optional
from message_model import MessageModel, Field, Enum, CompoundField, Namespace, Message

PY_TO_TS_TYPE = {
    'int': 'number',
    'float': 'number',
    'double': 'number',
    'bool': 'boolean',
    'str': 'string',
    'bytes': 'Uint8Array',
    'Any': 'any',
}

def map_type(field: Field, imports: Set[str], current_ns: str) -> str:
    """Map a Field to a TypeScript type, handling arrays, optionals, and cross-namespace refs."""
    base_type = field.field_type.value if hasattr(field.field_type, 'value') else field.field_type
    if base_type in PY_TO_TS_TYPE:
        ts_type = PY_TO_TS_TYPE[base_type]
    elif getattr(field, 'enum_values', None):
        ts_type = field.enum_reference or base_type
    elif getattr(field, 'compound_base_type', None):
        ts_type = field.compound_reference or base_type
    else:
        ts_type = 'any'
    if getattr(field, 'is_array', False):
        ts_type += '[]'
    if getattr(field, 'optional', False):
        ts_type += ' | undefined'
    return ts_type

def generate_enum(enum: Enum) -> str:
    lines = [f"export enum {enum.name} {{"]
    for value in enum.values:
        lines.append(f"    {value.name} = {value.value},")
    lines.append("}")
    return '\n'.join(lines)

def generate_compound(comp: CompoundField, imports: Set[str], current_ns: str) -> str:
    lines = [f"export interface {comp.name} {{"]
    for component in comp.components:
        # Each component is just a name, type is the base_type
        ts_type = PY_TO_TS_TYPE.get(comp.base_type, 'any')
        lines.append(f"    {component}: {ts_type};")
    lines.append("}")
    return '\n'.join(lines)

def generate_message(msg: Message, imports: Set[str], current_ns: str) -> str:
    base = f" extends {msg.parent}" if getattr(msg, 'parent', None) else ""
    lines = [f"export interface {msg.name}{base} {{"]
    for field in getattr(msg, 'fields', []):
        ts_type = map_type(field, imports, current_ns)
        lines.append(f"    {field.name}: {ts_type};")
    lines.append("}")
    return '\n'.join(lines)

def generate_namespace(ns: Namespace) -> str:
    imports: Set[str] = set()
    body: List[str] = []
    for enum in getattr(ns, 'enums', {}).values() if hasattr(ns, 'enums') else []:
        body.append(generate_enum(enum))
        body.append("")
    for comp in getattr(ns, 'compounds', {}).values() if hasattr(ns, 'compounds') else []:
        body.append(generate_compound(comp, imports, ns.name))
        body.append("")
    for msg in getattr(ns, 'messages', {}).values() if hasattr(ns, 'messages') else []:
        body.append(generate_message(msg, imports, ns.name))
        body.append("")
    import_lines = []
    for imp in sorted(imports):
        if imp != ns.name:
            import_lines.append(f"import * as {imp} from './{imp}';")
    return '\n'.join(import_lines + [f"export namespace {ns.name} {{"] + ["    " + line if line else "" for line in body] + ["}"])

def generate_typescript_code(namespaces: List[Namespace]) -> Dict[str, str]:
    """
    Generate TypeScript code for all namespaces.
    Returns a dict: {filename: code}
    """
    result = {}
    for ns in namespaces:
        code = generate_namespace(ns)
        result[f"{ns.name}.ts"] = code
    return result
