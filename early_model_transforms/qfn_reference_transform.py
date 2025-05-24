"""
QfnReferenceTransform: Adds fully qualified names (QFN) to all references in an EarlyModel, following the namespace resolution hierarchy.
"""
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum, EarlyField
from early_transform_pipeline import EarlyTransform
from typing import Dict, List, Optional
import re

def _is_qualified(name: str) -> bool:
    return '::' in name

class QfnReferenceTransform(EarlyTransform):
    def transform(self, model: EarlyModel) -> EarlyModel:
        # Require at least one namespace (file-level) for QFN transform; fail otherwise
        if not getattr(model, 'namespaces', None) or not model.namespaces:
            raise ValueError("QfnReferenceTransform requires at least one file-level namespace. Run AddFileLevelNamespaceTransform first.")
        # Build QFN lookup for this file (file-level namespace is always present)
        file_ns = model.namespaces[0]  # AddFileLevelNamespaceTransform guarantees this
        file_ns_name = file_ns.name

        def build_lookup(ns: EarlyNamespace, prefix: List[str], lookup: Dict[str, str]):
            ns_qfn = '::'.join(prefix + [ns.name]) if ns.name else '::'.join(prefix)
            ns.qfn = ns_qfn if ns_qfn else ns.name  # Assign qfn to namespace
            for msg in ns.messages:
                msg.qfn = ns_qfn + '::' + msg.name if ns_qfn else msg.name
                lookup[msg.name] = msg.qfn
            for enum in ns.enums:
                enum.qfn = ns_qfn + '::' + enum.name if ns_qfn else enum.name
                lookup[enum.name] = enum.qfn
            for nested in ns.namespaces:
                build_lookup(nested, prefix + [ns.name] if ns.name else prefix, lookup)

        # Build lookup for this file
        local_lookup = {}
        build_lookup(file_ns, [], local_lookup)

        # Build lookups for non-aliased imports (file-level namespace only)
        import_lookups = {}
        for import_path, alias in model.imports_raw:
            if alias:
                continue  # Aliased imports only accessible via alias
            imported_model = model.imports.get(import_path)
            if imported_model and imported_model.namespaces:
                import_ns = imported_model.namespaces[0]
                import_ns_name = import_ns.name
                import_lookup = {}
                build_lookup(import_ns, [], import_lookup)
                # DEBUG: Print the file-level namespace and QFN keys for each import
                print(f"[DEBUG] QfnReferenceTransform: Import '{import_path}' file-level namespace: '{import_ns_name}' QFN keys: {list(import_lookup.keys())}")
                import_lookups[import_ns_name] = import_lookup

        # Build lookups for aliased imports (file-level namespace only, must use alias)
        alias_lookups = {}
        for import_path, alias in model.imports_raw:
            if not alias:
                continue
            imported_model = model.imports.get(alias)
            if imported_model and imported_model.namespaces:
                import_ns = imported_model.namespaces[0]
                # Build a local QFN lookup rooted at the alias, without mutating the imported model
                def build_lookup_with_alias(ns, prefix, lookup):
                    # Replace the file-level namespace with the alias at the root
                    if not prefix:
                        ns_qfn = alias
                    else:
                        ns_qfn = '::'.join(prefix + [ns.name]) if ns.name else '::'.join(prefix)
                    for msg in ns.messages:
                        msg_qfn = ns_qfn + '::' + msg.name if ns_qfn else msg.name
                        lookup[msg.name] = msg_qfn
                    for enum in ns.enums:
                        enum_qfn = ns_qfn + '::' + enum.name if ns_qfn else enum.name
                        lookup[enum.name] = enum_qfn
                    for nested in ns.namespaces:
                        build_lookup_with_alias(nested, prefix + [ns_qfn] if ns_qfn else prefix, lookup)
                import_lookup = {}
                build_lookup_with_alias(import_ns, [], import_lookup)
                alias_lookups[alias] = import_lookup

        def resolve_unqualified(name: str, ns_stack: List[EarlyNamespace]) -> Optional[str]:
            # 1. Current namespace, then parent namespaces
            for ns in reversed(ns_stack):
                if name in local_lookup:
                    # Only match if QFN starts with this namespace
                    qfn = local_lookup[name]
                    ns_qfn = '::'.join([file_ns_name] + [n.name for n in ns_stack[1:]])
                    if qfn.startswith(ns_qfn):
                        return qfn
            # 2. File-level namespace
            if name in local_lookup:
                return local_lookup[name]
            # 3. Non-aliased imports (file-level namespace only)
            for import_ns_name, lookup in import_lookups.items():
                if name in lookup:
                    return lookup[name]
            return None

        def resolve_qualified(name: str) -> Optional[str]:
            # Try local lookup
            if name in local_lookup.values():
                return name
            # Try aliased imports
            m = re.match(r'^(\w+)::(.+)$', name)
            if m:
                alias, rest = m.group(1), m.group(2)
                if alias in alias_lookups and rest in alias_lookups[alias]:
                    return alias_lookups[alias][rest]
            return None

        def update_fields(fields, ns_stack):
            primitives = {"int", "string", "bool", "float", "double"}
            for field in fields:
                # Main type_name
                if hasattr(field, 'type_name') and field.type_name:
                    # Special case: if type_name is '?' and element_type_raw is a primitive, set type_name to element_type_raw
                    if field.type_name == '?' and hasattr(field, 'element_type_raw') and field.element_type_raw in primitives:
                        field.type_name = field.element_type_raw
                    elif field.type_name not in primitives:
                        if _is_qualified(field.type_name):
                            qfn = resolve_qualified(field.type_name)
                        else:
                            qfn = resolve_unqualified(field.type_name, ns_stack)
                        if qfn:
                            field.type_name = qfn
                # Debug: print the type_name after possible QFN rewrite
                print(f"[QFN DEBUG] After QFN transform: field '{getattr(field, 'name', '?')}' type_name = '{getattr(field, 'type_name', None)}'")
                # Array element type
                if hasattr(field, 'element_type_raw') and field.element_type_raw:
                    if field.element_type_raw not in primitives:
                        if _is_qualified(field.element_type_raw):
                            qfn = resolve_qualified(field.element_type_raw)
                        else:
                            qfn = resolve_unqualified(field.element_type_raw, ns_stack)
                        if qfn:
                            field.element_type_raw = qfn
                    # For arrays of non-primitives, always set type_name to element_type_raw (now QFN)
                    if field.element_type_raw not in primitives and hasattr(field, 'type_name'):
                        field.type_name = field.element_type_raw
                # Map key type
                if hasattr(field, 'map_key_type_raw') and field.map_key_type_raw:
                    if field.map_key_type_raw not in primitives:
                        if _is_qualified(field.map_key_type_raw):
                            qfn = resolve_qualified(field.map_key_type_raw)
                        else:
                            qfn = resolve_unqualified(field.map_key_type_raw, ns_stack)
                        if qfn:
                            field.map_key_type_raw = qfn
                # Map value type
                if hasattr(field, 'map_value_type_raw') and field.map_value_type_raw:
                    if field.map_value_type_raw not in primitives:
                        if _is_qualified(field.map_value_type_raw):
                            qfn = resolve_qualified(field.map_value_type_raw)
                        else:
                            qfn = resolve_unqualified(field.map_value_type_raw, ns_stack)
                        if qfn:
                            field.map_value_type_raw = qfn

        def update_enums(enums, ns_stack):
            for enum in enums:
                if hasattr(enum, 'parent_raw') and enum.parent_raw:
                    if _is_qualified(enum.parent_raw):
                        qfn = resolve_qualified(enum.parent_raw)
                    else:
                        qfn = resolve_unqualified(enum.parent_raw, ns_stack)
                    if qfn:
                        enum.parent_raw = qfn

        def update_ns(ns: EarlyNamespace, ns_stack: List[EarlyNamespace]):
            for msg in ns.messages:
                update_fields(msg.fields, ns_stack + [ns])
            update_enums(ns.enums, ns_stack + [ns])
            for nested in ns.namespaces:
                update_ns(nested, ns_stack + [ns])

        update_ns(file_ns, [])
        return model
