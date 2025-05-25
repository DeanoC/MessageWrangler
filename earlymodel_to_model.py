"""
Transform: Converts a fully-resolved EarlyModel into a concrete Model for code generation.
"""
import sys
from early_model import EarlyModel
from model import Model, ModelNamespace, ModelMessage, ModelEnum, ModelField, ModelEnumValue, FieldType, FieldModifier
from model import ModelReference

class EarlyModelToModel:
    def __init__(self):
        # Mapping from QFN to ModelEnum for all enums (local and imported)
        self.model_enum_by_qfn = {}
    def process(self, early_model: EarlyModel) -> Model:
        """
        Convert a fully-resolved EarlyModel to a concrete Model.
        All references must be QFN and resolvable.
        """
        # First, build a lookup of all enums and messages by QFN for reference resolution
        enum_lookup = {}
        msg_lookup = {}
        print("[DEBUG] Building enum/message lookup", file=sys.stderr)
        def build_lookup_ns(ns, prefix):
            ns_qfn = '::'.join(prefix + [ns.name]) if ns.name else '::'.join(prefix)
            for enum in ns.enums:
                qfn = ns_qfn + '::' + enum.name if ns_qfn else enum.name
                enum_lookup[qfn] = enum
            for msg in ns.messages:
                qfn = ns_qfn + '::' + msg.name if ns_qfn else msg.name
                msg_lookup[qfn] = msg
            for nested in ns.namespaces:
                build_lookup_ns(nested, prefix + [ns.name] if ns.name else prefix)

        # Register enums and inline enums from the current model
        for ns in early_model.namespaces:
            build_lookup_ns(ns, [])

        # Register enums and inline enums from all imported models (recursively)
        if hasattr(early_model, 'imports') and early_model.imports:
            for imported_model in early_model.imports.values():
                for ns in getattr(imported_model, 'namespaces', []):
                    build_lookup_ns(ns, [])

        print(f"[DEBUG] enum_lookup keys: {list(enum_lookup.keys())}", file=sys.stderr)

        # Helper to map raw type to FieldType enum
        def map_field_type(field):
            # Accepts either an EarlyField or a dict with 'type_name' and 'type_type'
            if isinstance(field, dict):
                type_name = field.get('type_name', None)
                type_type = field.get('type_type', None)
            else:
                type_name = getattr(field, 'type_name', None)
                type_type = getattr(field, 'type_type', None)
            # Map EarlyModel type_type to FieldType
            primitives = {
                'int': FieldType.INT,
                'string': FieldType.STRING,
                'bool': FieldType.BOOL,
                'float': FieldType.FLOAT,
                'double': FieldType.DOUBLE,
            }
            # Debug: print type_name and type_type for map_field_type
            print(f"[MAP_FIELD_TYPE DEBUG] type_name={type_name}, type_type={type_type}")
            # Use EarlyModel's type_type directly: if primitive, always map to FieldType
            if type_type == 'primitive':
                return primitives.get(type_name, FieldType.STRING), type_name
            # (Legacy fallback: treat ref_type with a primitive type_name as a primitive, for robustness)
            if type_type == 'ref_type' and type_name in primitives:
                return primitives.get(type_name, FieldType.STRING), type_name
            # PATCH: treat any type_name that matches an enum QFN as FieldType.ENUM, even if type_type is not 'enum_type'
            # Try direct match
            if type_name in enum_lookup:
                return FieldType.ENUM, type_name
            # Try alias mapping (e.g., Base::Command::type -> sh4c_base::Command_type)
            if isinstance(type_name, str) and '::' in type_name and alias_map:
                first = type_name.split('::', 1)[0]
                if first in alias_map:
                    mapped_type_name = alias_map[first] + '::' + type_name.split('::', 1)[1]
                    # Also try promoted inline enum QFN (Namespace::Message::fieldName -> Namespace::Message_fieldName)
                    if mapped_type_name in enum_lookup:
                        return FieldType.ENUM, mapped_type_name
                    # Try promoted QFN
                    parts = mapped_type_name.split('::')
                    if len(parts) >= 2:
                        promoted_qfn = '::'.join(parts[:-1]) + '_' + parts[-1]
                        if promoted_qfn in enum_lookup:
                            return FieldType.ENUM, promoted_qfn
            elif type_type == 'enum_type':
                if getattr(field, 'is_inline_enum', False):
                    return FieldType.ENUM, None
                return FieldType.ENUM, type_name
            elif type_type == 'message_type':
                # Try direct match
                if type_name in msg_lookup:
                    return FieldType.MESSAGE, type_name
                # Try to match by suffix (unqualified name)
                for qfn in msg_lookup.keys():
                    if qfn.endswith(f'::{type_name}') or qfn == type_name:
                        return FieldType.MESSAGE, qfn
                return FieldType.MESSAGE, type_name
            elif type_type in ('compound', 'compound_type'):
                return FieldType.COMPOUND, type_name
            elif type_type == 'options_type':
                return FieldType.OPTIONS, type_name
            elif type_type == 'array_type':
                return FieldType.ARRAY, type_name
            elif type_type == 'map_type':
                # Only return FieldType.MAP if this is the top-level field (not for key/value)
                # If the type_name is 'string', 'int', etc., treat as primitive
                if type_name in primitives:
                    return primitives.get(type_name, FieldType.STRING), type_name
                return FieldType.MAP, type_name
            # fallback
            return FieldType.STRING, type_name

        # Build alias map and imports dict from imports_raw
        alias_map = {}
        imports_dict = {}
        def build_ns_qfn(ns, prefix=None):
            prefix = prefix or []
            return '::'.join(prefix + [ns.name]) if ns.name else '::'.join(prefix)

        if hasattr(early_model, 'imports_raw') and hasattr(early_model, 'imports'):
            print(f"[ALIAS DEBUG] early_model.file: {getattr(early_model, 'file', None)}")
            print(f"[ALIAS DEBUG] early_model.imports_raw: {getattr(early_model, 'imports_raw', None)}")
            print(f"[ALIAS DEBUG] early_model.imports keys: {list(getattr(early_model, 'imports', {}).keys())}")
            print(f"[ALIAS DEBUG] alias_map after construction: {alias_map}")
            for import_path, alias in getattr(early_model, 'imports_raw', []):
                key = alias if alias else import_path
                imported_model = early_model.imports.get(key)
                if imported_model:
                    # Use the same transform instance for imports to share model_enum_by_qfn
                    imported_model_obj = self.process(imported_model)
                    imports_dict[key] = imported_model_obj
                    print(f"[ALIAS DEBUG] alias: {alias}, imported_model_obj: <Model object>, namespaces: {[ns.name for ns in getattr(imported_model_obj, 'namespaces', [])]}")
                    # Always map alias to the file-level namespace QFN (auto-generated or explicit)
                    if alias and imported_model_obj.namespaces:
                        file_ns = imported_model_obj.namespaces[0]
                        file_ns_qfn = build_ns_qfn(file_ns)
                        alias_map[alias] = file_ns_qfn
                    # Also, if the imported model has its own alias_map, merge it in (for transitive aliases)
                    if hasattr(imported_model_obj, 'alias_map') and imported_model_obj.alias_map:
                        for k, v in imported_model_obj.alias_map.items():
                            if k not in alias_map:
                                alias_map[k] = v

        # Convert enums
        enum_model_lookup = {}
        def convert_enum(enum, parent=None):
            # Resolve parent if not provided
            resolved_parent = parent
            parent_raw = getattr(enum, 'parent_raw', None)
            print(f"[DEBUG] convert_enum: enum.name={getattr(enum, 'name', None)}, parent_raw={parent_raw}", file=sys.stderr)
            # Map parent_raw using alias_map if it starts with an alias
            mapped_parent_raw = parent_raw
            if parent_raw and isinstance(parent_raw, str) and '::' in parent_raw and alias_map:
                first = parent_raw.split('::', 1)[0]
                if first in alias_map:
                    mapped_parent_raw = alias_map[first] + '::' + parent_raw.split('::', 1)[1]
                    print(f"[DEBUG] Mapped parent_raw '{parent_raw}' to '{mapped_parent_raw}' using alias_map", file=sys.stderr)
            else:
                mapped_parent_raw = parent_raw
            if mapped_parent_raw and parent is None:
                print(f"[ENUM PARENT DEBUG] Trying to resolve parent_raw='{mapped_parent_raw}'", file=sys.stderr)

                # Try to resolve in the main enum_lookup (contains EarlyEnums from current and imported models)
                target_qfn = mapped_parent_raw

                # Check if the reference looks like a promoted inline enum (Namespace::Message::fieldName)
                # and convert it to the promoted name format (Namespace::Message_fieldName)
                if '::' in target_qfn:
                    parts = target_qfn.split('::')
                    if len(parts) >= 2:
                        # Assuming the format is Namespace::Message::fieldName
                        # The promoted name would be Namespace::Message_fieldName
                        potential_promoted_qfn = '::'.join(parts[:-1]) + '_' + parts[-1]
                        # Check if this potential promoted QFN exists in the enum_lookup
                        if potential_promoted_qfn in enum_lookup:
                            target_qfn = potential_promoted_qfn
                            print(f"[ENUM PARENT DEBUG] Mapped inline enum reference '{mapped_parent_raw}' to promoted QFN '{target_qfn}'", file=sys.stderr)


                # Try to resolve in the main enum_lookup (contains EarlyEnums from current and imported models)
                if target_qfn in enum_lookup:
                    candidate_early_enum = enum_lookup[target_qfn]
                    # Now find the corresponding ModelEnum. It could be in the current model's lookup
                    # or in an imported model's lookup.
                    resolved_parent = enum_model_lookup.get(candidate_early_enum)

                    if resolved_parent:
                        print(f"[ENUM PARENT DEBUG] Resolved enum parent for '{mapped_parent_raw}' (looked up as '{target_qfn}') via local enum_model_lookup", file=sys.stderr)
                    else:
                        # If not found in the current model's lookup, search in imported models' lookups
                        print(f"[ENUM PARENT DEBUG] Parent '{mapped_parent_raw}' (looked up as '{target_qfn}') not found in local enum_model_lookup. Searching imported models.", file=sys.stderr)
                        for imported_model_obj in imports_dict.values():
                            # Access the enum_model_lookup of the imported model
                            # Note: Model objects don't directly expose enum_model_lookup,
                            # so we need to search its namespaces.
                            def find_enum_in_model(model, target_qfn):
                                def search_ns(ns_list, current_qfn_parts):
                                    for ns in ns_list:
                                        ns_name = ns.name if ns.name else ""
                                        current_ns_qfn = '::'.join(current_qfn_parts + [ns_name]) if ns_name else '::'.join(current_qfn_parts)
                                        # Check enums in the current namespace
                                        for enum in getattr(ns, 'enums', []):
                                            enum_qfn = current_ns_qfn + '::' + enum.name if current_ns_qfn else enum.name
                                            if enum_qfn == target_qfn:
                                                return enum
                                        # Recurse into nested namespaces
                                        found_in_nested = search_ns(getattr(ns, 'namespaces', []), current_qfn_parts + [ns_name] if ns_name else current_qfn_parts)
                                        if found_in_nested:
                                            return found_in_nested
                                    return None
                                # Start search from the top-level namespaces of the imported model
                                return search_ns(getattr(model, 'namespaces', []), [])

                            resolved_parent = find_enum_in_model(imported_model_obj, target_qfn)
                            if resolved_parent:
                                print(f"[ENUM PARENT DEBUG] Resolved imported enum parent '{mapped_parent_raw}' (looked up as '{target_qfn}') in imported model.", file=sys.stderr)
                                break # Found the parent, no need to search other imported models

                if resolved_parent:
                    print(f"[ENUM PARENT DEBUG] Final resolved parent for '{getattr(enum, 'name', None)}': {getattr(resolved_parent, 'name', None)}", file=sys.stderr)
                else:
                    print(f"[ENUM PARENT DEBUG] Could not resolve parent for '{getattr(enum, 'name', None)}' (raw: {parent_raw}, looked up as: {target_qfn})", file=sys.stderr)

            # ... rest of the function ...
            values = [
                ModelEnumValue(
                    v.name,
                    v.value,
                    doc=getattr(v, 'doc', None),
                    comment=getattr(v, 'comment', None),
                    file=getattr(v, 'file', None),
                    line=getattr(v, 'line', None),
                    namespace=getattr(v, 'namespace', None)
                ) for v in getattr(enum, 'values', [])
            ]
            model_enum = ModelEnum(
                name=enum.name,
                values=values,
                is_open=getattr(enum, 'is_open_raw', False),
                parent=resolved_parent,
                doc=getattr(enum, 'doc', None),
                comment=getattr(enum, 'comment', None),
                parent_raw=getattr(enum, 'parent_raw', None),
                file=getattr(enum, 'file', None),
                line=getattr(enum, 'line', None),
                namespace=getattr(enum, 'namespace', None)
            )
            # Find QFN for this enum
            qfn = None
            for k, v in enum_lookup.items():
                if v is enum:
                    qfn = k
                    break
            if qfn:
                self.model_enum_by_qfn[qfn] = model_enum
            enum_model_lookup[enum] = model_enum
            return model_enum

        # Convert messages
        msg_model_lookup = {}
        # Set file-level namespace for use in enum QFN resolution
        filelevelns = None
        if hasattr(early_model, 'namespaces') and early_model.namespaces:
            filelevelns = early_model.namespaces[0].name

        def convert_message(msg, parent=None):
            fields = []
            # To add inline enums to the containing namespace
            containing_ns = getattr(msg, 'parent_container', None)
            ns_for_inline = containing_ns if containing_ns else ns  # fallback to current ns
            for field in getattr(msg, 'fields', []):
                # Initialize ftype and ref_qfn to avoid UnboundLocalError
                ftype = None
                ref_qfn = None
                # DEBUG: Print type_name, candidate_msgs, and candidate_enum_qfn for enum reference fields
                type_name = getattr(field, 'type_name', None)
                if type_name and ('.' in type_name or '::' in type_name):
                    print(f"[DEBUG ENUM RESOLVE] Field '{getattr(field, 'name', None)}' type_name='{type_name}'", file=sys.stderr)
                    msg_name = None
                    enum_field = None
                    if '.' in type_name:
                        msg_path, enum_field = type_name.rsplit('.', 1)
                    else:
                        msg_path, enum_field = type_name.rsplit('::', 1)
                    msg_name = msg_path.split('::')[-1]
                    candidate_msgs = [qfn for qfn in msg_lookup.keys() if qfn.split('::')[-1] == msg_name]
                    print(f"[DEBUG ENUM RESOLVE] candidate_msgs for msg_name '{msg_name}': {candidate_msgs}", file=sys.stderr)
                    for msg_qfn in candidate_msgs:
                        candidate_enum_qfn = f"{msg_qfn}::{enum_field}"
                        print(f"[DEBUG ENUM RESOLVE] Trying candidate_enum_qfn: {candidate_enum_qfn}", file=sys.stderr)
                        if candidate_enum_qfn in enum_lookup:
                            print(f"[DEBUG ENUM RESOLVE] SUCCESS: Found enum QFN '{candidate_enum_qfn}' in enum_lookup", file=sys.stderr)
                            # PATCH: If found, set ftype and ref_qfn immediately
                            ftype = FieldType.ENUM
                            ref_qfn = candidate_enum_qfn
                        # PATCH: Also try promoted QFN form (Namespace::Message_field)
                        candidate_enum_qfn_promoted = f"{msg_qfn}_{enum_field}"
                        print(f"[DEBUG ENUM RESOLVE] Trying candidate_enum_qfn_promoted: {candidate_enum_qfn_promoted}", file=sys.stderr)
                        if candidate_enum_qfn_promoted in enum_lookup:
                            print(f"[DEBUG ENUM RESOLVE] SUCCESS: Found promoted enum QFN '{candidate_enum_qfn_promoted}' in enum_lookup", file=sys.stderr)
                            # PATCH: If found, set ftype and ref_qfn immediately
                            ftype = FieldType.ENUM
                            ref_qfn = candidate_enum_qfn_promoted
                            type_type = 'enum_type'
                            type_name = candidate_enum_qfn_promoted.split('::')[-1]
                # Build the field_types, type_refs, and type_names arrays
                field_types = []
                type_refs = []
                type_names = []
                inline_values = []

                # --- PATCH: If enum QFN was resolved above (including promoted), always set arrays to ENUM/ModelReference/QFN ---
                # This ensures that fields like 'containerStatus' and 'testLevel' are not left as string
                if ftype == FieldType.ENUM and ref_qfn and (ref_qfn in enum_lookup or ref_qfn in self.model_enum_by_qfn):
                    # Find the enum object
                    enum_obj = enum_lookup.get(ref_qfn) or self.model_enum_by_qfn.get(ref_qfn)
                    type_ref = ModelReference(ref_qfn, kind='enum')
                    if enum_obj is not None:
                        type_ref.name = getattr(enum_obj, 'name', None)
                        type_ref.file = getattr(enum_obj, 'file', None)
                        type_ref.namespace = getattr(enum_obj, 'namespace', None)
                    field_types.clear()
                    type_refs.clear()
                    type_names.clear()
                    field_types.append(FieldType.ENUM)
                    type_refs.append(type_ref)
                    type_names.append(ref_qfn)
                # Infer type_type for the top-level field
                def infer_type_type(type_name, type_type=None):
                    primitives = {'int', 'string', 'bool', 'float', 'double'}
                    if type_name in primitives:
                        return 'primitive'
                    if type_name in enum_lookup:
                        return 'enum_type'
                    # If type_type is 'ref_type' but type_name matches a message, treat as message_type
                    if (type_type == 'ref_type' or type_type is None):
                        if type_name in msg_lookup:
                            return 'message_type'
                        for qfn in msg_lookup.keys():
                            if qfn.endswith(f'::{type_name}') or qfn == type_name:
                                return 'message_type'
                    return None
                type_name = getattr(field, 'type_name', None)
                type_type = getattr(field, 'type_type', None)
                # --- PATCH: robust fallback for missing/unknown type_name ---
                if (type_name == '?' or type_name is None):
                    # Defensive: ensure ftype and ref_qfn are initialized
                    if 'ftype' not in locals():
                        ftype = None
                    if 'ref_qfn' not in locals():
                        ref_qfn = None
                    raw_type = getattr(field, 'raw_type', None)
                    referenced_name_raw = getattr(field, 'referenced_name_raw', None)
                    print(f"[MODEL PATCH DEBUG] Field '{getattr(field, 'name', '?')}' in message '{msg.name}' has type_name='?'. raw_type='{raw_type}', referenced_name_raw='{referenced_name_raw}'", file=sys.stderr)
                    print(f"[MODEL PATCH DEBUG] enum_lookup keys: {list(enum_lookup.keys())}", file=sys.stderr)
                    fallback_type = raw_type or referenced_name_raw
                    field_name = getattr(field, 'name', None)
                    found_enum_qfn = None
                    qfn_suffix_attempts = []
                    parent_msg_name = getattr(msg, 'name', None)
                    parent_msg_qfn = None
                    if hasattr(msg, 'namespace') and msg.namespace:
                        parent_msg_qfn = f"{msg.namespace}::{parent_msg_name}" if parent_msg_name else None

                    # --- PATCH: Promote parent's inline enum for derived field if needed ---
                    # If this field is in a derived message, and the parent message has a field with the same name and that field is an inline enum, promote it here
                    parent_ref = getattr(msg, 'parent', None)
                    parent_msg = None
                    if parent_ref and hasattr(parent_ref, 'qfn') and parent_ref.qfn in msg_lookup:
                        parent_msg = msg_lookup[parent_ref.qfn]
                    if parent_msg:
                        for parent_field in getattr(parent_msg, 'fields', []):
                            if parent_field.name == field_name and getattr(parent_field, 'is_inline_enum', False) and getattr(parent_field, 'inline_values_raw', None):
                                # Promote parent's inline enum to this message's namespace with the derived field name
                                promoted_enum_name = f"{parent_msg_name}_{field_name}"
                                # Avoid duplicate promotion
                                if not any(e.name == promoted_enum_name for e in ns_for_inline.enums):
                                    enum_values = [
                                        ModelEnumValue(
                                            v.get('name', '?'),
                                            v.get('value', None),
                                            doc=v.get('doc', None),
                                            comment=v.get('comment', None),
                                            file=v.get('file', None),
                                            line=v.get('line', None),
                                            namespace=v.get('namespace', None)
                                        ) for v in parent_field.inline_values_raw
                                    ]
                                    promoted_enum = ModelEnum(
                                        name=promoted_enum_name,
                                        values=enum_values,
                                        is_open=False,
                                        parent=None,
                                        doc=None,
                                        comment=None,
                                        parent_raw=None,
                                        file=getattr(field, 'file', None),
                                        line=getattr(field, 'line', None),
                                        namespace=getattr(field, 'namespace', None)
                                    )
                                    ns_for_inline.enums.append(promoted_enum)
                                    # Also add to enum_lookup for QFN search
                                    # Build QFN for this promoted enum
                                    ns_qfn = getattr(field, 'namespace', None)
                                    if ns_qfn:
                                        promoted_enum_qfn = f"{ns_qfn}::{promoted_enum_name}"
                                    else:
                                        promoted_enum_qfn = promoted_enum_name
                                    enum_lookup[promoted_enum_qfn] = promoted_enum
                                    print(f"[MODEL PATCH] Promoted parent's inline enum for derived field: {promoted_enum_qfn}", file=sys.stderr)
                    # Try to resolve by QFN suffix (field name)
                    for qfn in enum_lookup.keys():
                        # Direct field name
                        if qfn.endswith(f'::{field_name}') or qfn.split('::')[-1] == field_name:
                            found_enum_qfn = qfn
                            qfn_suffix_attempts.append(qfn)
                            break
                        # Promoted: Message_fieldName (search all namespaces, including current file)
                        if parent_msg_name and (qfn.endswith(f'{parent_msg_name}_{field_name}') or qfn.split('::')[-1] == f'{parent_msg_name}_{field_name}'):
                            found_enum_qfn = qfn
                            qfn_suffix_attempts.append(qfn)
                            break
                        # Promoted: Namespace::Message_fieldName (search all namespaces, including current file)
                        if parent_msg_qfn and (qfn.endswith(f'{parent_msg_qfn}_{field_name}') or qfn == f'{parent_msg_qfn}_{field_name}'):
                            found_enum_qfn = qfn
                            qfn_suffix_attempts.append(qfn)
                            break
                        # Promoted: Message_type (for fields like typeX, try Message_type in current file's namespace)
                        if parent_msg_name and field_name.lower().startswith('type'):
                            if qfn.endswith(f'{parent_msg_name}_type') or qfn.split('::')[-1] == f'{parent_msg_name}_type':
                                found_enum_qfn = qfn
                                qfn_suffix_attempts.append(qfn)
                                break
                        qfn_suffix_attempts.append(qfn)
                    if not found_enum_qfn:
                        print(f"[MODEL PATCH DEBUG] QFN suffix search for field '{field_name}' in message '{msg.name}' tried: {qfn_suffix_attempts}", file=sys.stderr)
                        print(f"[MODEL PATCH DEBUG] QFN suffix search did NOT find a match for '{field_name}', '{parent_msg_name}_{field_name}', '{parent_msg_qfn}_{field_name}', or '{parent_msg_name}_type' in any namespace", file=sys.stderr)
                    # Try to resolve by message parent chain (for inherited fields), recursively
                    def resolve_enum_from_parent_chain(msg_obj, fname):
                        visited = set()
                        parent_chain_attempts = []
                        while msg_obj and hasattr(msg_obj, 'fields'):
                            for parent_field in getattr(msg_obj, 'fields', []):
                                if parent_field.name == fname:
                                    parent_type_name = getattr(parent_field, 'type_name', None)
                                    # Try direct type_name
                                    if parent_type_name and parent_type_name != '?':
                                        for qfn in enum_lookup.keys():
                                            if qfn.endswith(f'::{parent_type_name}') or qfn.split('::')[-1] == parent_type_name:
                                                print(f"[DEBUG] Parent chain: matched direct type_name '{parent_type_name}' to QFN '{qfn}'", file=sys.stderr)
                                                parent_chain_attempts.append(qfn)
                                                return qfn, 'direct_type_name', parent_chain_attempts
                                            else:
                                                parent_chain_attempts.append(qfn)
                                    # Try _patch_enum_qfn_hint
                                    if hasattr(parent_field, '_patch_enum_qfn_hint'):
                                        qfn_hint = getattr(parent_field, '_patch_enum_qfn_hint')
                                        print(f"[DEBUG] Parent chain: using _patch_enum_qfn_hint '{qfn_hint}'", file=sys.stderr)
                                        parent_chain_attempts.append(qfn_hint)
                                        return qfn_hint, '_patch_enum_qfn_hint', parent_chain_attempts
                                    # Try promoted QFN: Namespace::Message_field
                                    parent_msg_name = getattr(msg_obj, 'name', None)
                                    ns = getattr(msg_obj, 'namespace', None)
                                    possible_qfns = []
                                    if ns and parent_msg_name:
                                        possible_qfns.append(f"{ns}::{parent_msg_name}_{fname}")
                                    if parent_msg_name:
                                        possible_qfns.append(f"{parent_msg_name}_{fname}")
                                    # Brute-force: try any QFN ending with _{fname} or ::{parent_msg_name}_{fname}
                                    for enum_qfn in enum_lookup.keys():
                                        if enum_qfn.endswith(f'_{fname}'):
                                            print(f"[DEBUG] Parent chain: brute-force matched QFN ending with _{fname}: '{enum_qfn}'", file=sys.stderr)
                                            parent_chain_attempts.append(enum_qfn)
                                            return enum_qfn, 'brute_force_underscore', parent_chain_attempts
                                        if parent_msg_name and enum_qfn.endswith(f'::{parent_msg_name}_{fname}'):
                                            print(f"[DEBUG] Parent chain: brute-force matched QFN ending with ::{parent_msg_name}_{fname}: '{enum_qfn}'", file=sys.stderr)
                                            parent_chain_attempts.append(enum_qfn)
                                            return enum_qfn, 'brute_force_colon', parent_chain_attempts
                                        parent_chain_attempts.append(enum_qfn)
                                    for qfn in possible_qfns:
                                        for enum_qfn in enum_lookup.keys():
                                            if enum_qfn.endswith(qfn):
                                                print(f"[DEBUG] Parent chain: matched possible_qfn '{qfn}' to QFN '{enum_qfn}'", file=sys.stderr)
                                                parent_chain_attempts.append(enum_qfn)
                                                return enum_qfn, 'possible_qfn', parent_chain_attempts
                                            else:
                                                parent_chain_attempts.append(enum_qfn)
                                    # Otherwise, try to resolve recursively up the parent chain
                                    parent_ref = getattr(msg_obj, 'parent', None)
                                    if parent_ref and hasattr(parent_ref, 'qfn') and parent_ref.qfn in msg_lookup:
                                        next_msg = msg_lookup[parent_ref.qfn]
                                        if id(next_msg) not in visited:
                                            visited.add(id(next_msg))
                                            return resolve_enum_from_parent_chain(next_msg, fname)
                            # If no field found, try up the parent chain
                            parent_ref = getattr(msg_obj, 'parent', None)
                            if parent_ref and hasattr(parent_ref, 'qfn') and parent_ref.qfn in msg_lookup:
                                next_msg = msg_lookup[parent_ref.qfn]
                                if id(next_msg) not in visited:
                                    visited.add(id(next_msg))
                                    msg_obj = next_msg
                                    continue
                            break
                        print(f"[DEBUG] Parent chain: no QFN match found for field '{fname}' in parent chain. enum_lookup keys: {list(enum_lookup.keys())}", file=sys.stderr)
                        print(f"[DEBUG] Parent chain: attempted QFNs: {parent_chain_attempts}", file=sys.stderr)
                        return None, None, parent_chain_attempts
                    if not found_enum_qfn and hasattr(msg, 'parent') and msg.parent:
                        parent_ref = msg.parent
                        parent_msg = None
                        if hasattr(parent_ref, 'qfn') and parent_ref.qfn in msg_lookup:
                            parent_msg = msg_lookup[parent_ref.qfn]
                        if parent_msg:
                            found_enum_qfn, match_type, parent_chain_attempts = resolve_enum_from_parent_chain(parent_msg, field_name)
                            if found_enum_qfn:
                                print(f"[MODEL PATCH] Field '{field_name}' in message '{msg.name}' resolved type_name by QFN suffix or parent: '{found_enum_qfn}' (match_type={match_type})", file=sys.stderr)
                                type_name = found_enum_qfn.split('::')[-1]
                                ref_qfn = found_enum_qfn
                                setattr(field, '_patch_enum_qfn_hint', found_enum_qfn)
                                type_type = 'enum_type'
                            else:
                                print(f"[MODEL PATCH DEBUG] Parent chain search for field '{field_name}' in message '{msg.name}' attempted QFNs: {parent_chain_attempts}", file=sys.stderr)
                    if found_enum_qfn:
                        # Ensure type_type and ftype are set for enum
                        type_type = 'enum_type'
                        ftype = FieldType.ENUM
                        print(f"[MODEL PATCH] Field '{field_name}' in message '{msg.name}' FINAL PATCH: type_name='{type_name}', ref_qfn='{ref_qfn}', type_type='{type_type}', ftype='{ftype}'", file=sys.stderr)
                    if found_enum_qfn:
                        print(f"[MODEL PATCH] Field '{field_name}' in message '{msg.name}' resolved type_name by QFN suffix or parent: '{found_enum_qfn}'", file=sys.stderr)
                        type_name = found_enum_qfn.split('::')[-1]
                        ref_qfn = found_enum_qfn
                        setattr(field, '_patch_enum_qfn_hint', found_enum_qfn)
                        type_type = 'enum_type'
                    elif fallback_type and fallback_type != '?':
                        print(f"[MODEL PATCH] Field '{getattr(field, 'name', '?')}' in message '{msg.name}' has type_name='?'. Using fallback_type='{fallback_type}'", file=sys.stderr)
                        type_name = fallback_type
                # Special handling for map_type: always treat as map, even if type_name is '?'
                if (type_type == 'map_type' or getattr(field, 'raw_type', None) == 'map_type'):
                    ftype = FieldType.MAP  # Ensure ftype is always set for map_type fields
                    ktype_raw = getattr(field, 'map_key_type_raw', None)
                    vtype_raw = getattr(field, 'map_value_type_raw', None)
                    primitives = {'int', 'string', 'bool', 'float', 'double'}
                    # Key type
                    if ktype_raw is not None:
                        if ktype_raw in primitives:
                            ktype_type = 'primitive'
                        else:
                            ktype_type = infer_type_type(ktype_raw)
                        if not ktype_type and ktype_raw in primitives:
                            ktype_type = 'primitive'
                        if ktype_type == 'map_type' and ktype_raw in primitives:
                            ktype_type = 'primitive'
                        ktype, ktype_ref_qfn = map_field_type({'type_name': ktype_raw, 'type_type': ktype_type})
                    else:
                        ktype, ktype_ref_qfn = None, None
                    # Value type
                    if vtype_raw is not None:
                        if vtype_raw in primitives:
                            vtype_type = 'primitive'
                        else:
                            vtype_type = infer_type_type(vtype_raw)
                        if not vtype_type and vtype_raw in primitives:
                            vtype_type = 'primitive'
                        if vtype_type == 'map_type' and vtype_raw in primitives:
                            vtype_type = 'primitive'
                        vtype, vtype_ref_qfn = map_field_type({'type_name': vtype_raw, 'type_type': vtype_type})
                    else:
                        vtype, vtype_ref_qfn = None, None
                    field_types.append(FieldType.MAP)
                    field_types.append(ktype)
                    field_types.append(vtype)
                    type_names.append('MAP')
                    type_names.append(ktype_raw)
                    type_names.append(vtype_raw)
                    map_key_type_ref = None
                    map_value_type_ref = None
                    if ktype == FieldType.ENUM and ktype_ref_qfn:
                        map_key_type_ref = enum_model_lookup.get(enum_lookup[ktype_ref_qfn])
                    if vtype == FieldType.ENUM and vtype_ref_qfn:
                        map_value_type_ref = enum_model_lookup.get(enum_lookup[vtype_ref_qfn])
                    elif vtype == FieldType.MESSAGE and vtype_ref_qfn:
                        # Set ModelReference and attach name/file for generator
                        map_value_type_ref = ModelReference(vtype_ref_qfn, kind='message')
                        msg_obj = msg_lookup.get(vtype_ref_qfn)
                        if msg_obj is not None:
                            if hasattr(msg_obj, 'name'):
                                map_value_type_ref.name = getattr(msg_obj, 'name', None)
                            if hasattr(msg_obj, 'file'):
                                map_value_type_ref.file = getattr(msg_obj, 'file', None)
                    type_refs.append(None)  # MAP itself has no ref
                    type_refs.append(map_key_type_ref)
                    type_refs.append(map_value_type_ref)
                else:
                    # Defensive: If type_name is '?' or None, try to patch using QFN suffix logic above
                    if type_name == '?' or type_name is None:
                        # If ref_qfn was set by the QFN patch above, use it
                        if hasattr(field, '_patch_enum_qfn_hint'):
                            patched_qfn = getattr(field, '_patch_enum_qfn_hint')
                            print(f"[MODEL PATCH] For field '{getattr(field, 'name', '?')}' using patched QFN '{patched_qfn}' for enum resolution.", file=sys.stderr)
                            type_name = patched_qfn.split('::')[-1]
                            ref_qfn = patched_qfn
                            type_type = 'enum_type'
                            ftype = FieldType.ENUM
                        else:
                            print(f"[MODEL ERROR] Field '{getattr(field, 'name', '?')}' in message '{msg.name}' has invalid type_name ('?'). Skipping enum/message resolution.")
                            if ftype is None:
                                ftype = FieldType.STRING
                            if ref_qfn is None:
                                ref_qfn = type_name
                    else:
                        # Debug: print type_name and type_type before inference
                        print(f"[MODEL DEBUG] Field '{getattr(field, 'name', '?')}' initial type_name='{type_name}', type_type='{type_type}'")
                        # Always infer type_type if not set or is '?' or is 'ref_type'
                        if not type_type or type_type == '?' or type_type == 'ref_type':
                            type_type = infer_type_type(type_name, type_type)
                        print(f"[MODEL DEBUG] Field '{getattr(field, 'name', '?')}' after inference type_name='{type_name}', type_type='{type_type}'")
                        ftype, ref_qfn = map_field_type({'type_name': type_name, 'type_type': type_type})
                        print(f"[MODEL DEBUG] Field '{getattr(field, 'name', '?')}' resolved ftype={ftype}, ref_qfn={ref_qfn}")
                    # Only append the top-level ftype for non-MAP fields
                    if ftype != FieldType.MAP:
                        field_types.append(ftype)
                type_ref = None
                # ENUM
                if ftype == FieldType.ENUM:
                    # PATCH: Robustly resolve enum references like EnumContainer.status or Test::NamespacedEnum.level
                    if (not ref_qfn or ref_qfn not in enum_lookup) and type_name and ('.' in type_name or '::' in type_name):
                        # Try all possible QFN forms: 'A::B::field', 'A_B_field', etc.
                        parts = type_name.replace('.', '::').split('::')
                        if len(parts) >= 2:
                            # Try 'A::B::field', 'A_B_field', 'A::B_field'
                            candidate_qfn1 = '::'.join(parts)
                            candidate_qfn2 = '_'.join(parts)
                            candidate_qfn3 = '::'.join(parts[:-2] + [parts[-2] + '_' + parts[-1]]) if len(parts) > 2 else None
                            tried = []
                            print(f"[DEBUG ENUM PATCH] enum_lookup keys: {list(enum_lookup.keys())}", file=sys.stderr)
                            print(f"[DEBUG ENUM PATCH] Attempting QFNs for type_name '{type_name}': {[candidate_qfn1, candidate_qfn2, candidate_qfn3]}", file=sys.stderr)
                            candidates = [candidate_qfn1, candidate_qfn2, candidate_qfn3]
                            # Try file-level namespace prefix if available
                            if filelevelns:
                                candidates += [f"{filelevelns}::{qfn}" for qfn in [candidate_qfn1, candidate_qfn2, candidate_qfn3] if qfn]
                            print(f"[DEBUG ENUM PATCH] Candidates for '{type_name}': {candidates}", file=sys.stderr)
                            print(f"[DEBUG ENUM PATCH] enum_lookup keys: {list(enum_lookup.keys())}", file=sys.stderr)
                            for candidate_qfn in candidates:
                                if candidate_qfn and candidate_qfn in enum_lookup:
                                    ref_qfn = candidate_qfn
                                    ftype = FieldType.ENUM  # PATCH: ensure field type is set to ENUM
                                    print(f"[PATCH] Resolved enum reference '{type_name}' to QFN '{candidate_qfn}' (set ftype=ENUM)", file=sys.stderr)
                                    break
                                tried.append(candidate_qfn)
                            else:
                                # Try all QFNs ending with the field name
                                field_part = parts[-1]
                                for qfn in enum_lookup.keys():
                                    if qfn.endswith(f'::{field_part}') or qfn.endswith(f'_{field_part}'):
                                        ref_qfn = qfn
                                        print(f"[PATCH] Fallback resolved enum reference '{type_name}' to QFN '{qfn}'", file=sys.stderr)
                                        break
                            print(f"[DEBUG ENUM PATCH] Final ref_qfn for '{type_name}': {ref_qfn}", file=sys.stderr)
                    # If still not found, try MessageName::fieldName for all messages (legacy fallback)
                    if (not ref_qfn or ref_qfn not in enum_lookup) and type_name and '.' not in type_name and '.' not in ref_qfn if ref_qfn else True:
                        for msg_qfn in msg_lookup.keys():
                            candidate_qfn = f"{msg_qfn}::{type_name.split('.')[-1]}"
                            if candidate_qfn in enum_lookup:
                                ref_qfn = candidate_qfn
                                print(f"[PATCH] Fallback resolved enum reference '{type_name}' to QFN '{candidate_qfn}'", file=sys.stderr)
                                break
                    # Always promote inline enums to the containing namespace and set type_ref
                    resolved_enum = None
                    resolved_qfn = ref_qfn
                    # If this is an inline enum, always use the promoted enum
                    if getattr(field, 'is_inline_enum', False) and getattr(field, 'inline_values_raw', None):
                        promoted_name = f"{msg.name}_{field.name}"
                        promoted_enum = next((e for e in ns_for_inline.enums if e.name == promoted_name), None)
                        if not promoted_enum:
                            # Create and add the promoted enum if not present
                            enum_values = [
                                ModelEnumValue(
                                    v.get('name', '?'),
                                    v.get('value', None),
                                    doc=v.get('doc', None),
                                    comment=v.get('comment', None),
                                    file=v.get('file', None),
                                    line=v.get('line', None),
                                    namespace=v.get('namespace', None)
                                ) for v in field.inline_values_raw
                            ]
                            promoted_enum = ModelEnum(
                                name=promoted_name,
                                values=enum_values,
                                is_open=False,
                                parent=None,
                                doc=None,
                                comment=None,
                                parent_raw=None,
                                file=getattr(field, 'file', None),
                                line=getattr(field, 'line', None),
                                namespace=getattr(field, 'namespace', None)
                            )
                            ns_for_inline.enums.append(promoted_enum)
                        resolved_enum = promoted_enum
                        # Always set type_ref to a ModelReference for promoted enums
                        promoted_enum_qfn = None
                        for k, v in enum_lookup.items():
                            if v is promoted_enum:
                                promoted_enum_qfn = k
                                break
                        if promoted_enum_qfn:
                            type_ref = ModelReference(promoted_enum_qfn, kind='enum')
                            type_ref.name = promoted_enum.name
                            type_ref.file = getattr(promoted_enum, 'file', None)
                            type_ref.namespace = getattr(promoted_enum, 'namespace', None)
                        else:
                            type_ref = promoted_enum
                        type_names.append(promoted_name)
                    # --- PATCH: use _patch_enum_qfn_hint if present ---
                    if not resolved_enum and hasattr(field, '_patch_enum_qfn_hint'):
                        qfn_hint = getattr(field, '_patch_enum_qfn_hint')
                        if qfn_hint in self.model_enum_by_qfn:
                            resolved_enum = self.model_enum_by_qfn[qfn_hint]
                            ref_qfn = qfn_hint  # PATCH: update ref_qfn so type_refs[0] is set correctly
                            # Overwrite type_names to ensure the correct enum name is used
                            type_names.clear()
                            type_names.append(qfn_hint.split('::')[-1])
                            # Always set type_ref to a ModelReference for resolved enums
                            type_ref = ModelReference(qfn_hint, kind='enum')
                            type_ref.name = resolved_enum.name
                            type_ref.file = getattr(resolved_enum, 'file', None)
                            type_ref.namespace = getattr(resolved_enum, 'namespace', None)
                    # Otherwise, try normal enum resolution
                    if not resolved_enum:
                        # Try direct QFN
                        if ref_qfn and ref_qfn in self.model_enum_by_qfn:
                            resolved_enum = self.model_enum_by_qfn[ref_qfn]
                            type_names.append(ref_qfn)
                            type_ref = ModelReference(ref_qfn, kind='enum')
                            type_ref.name = resolved_enum.name
                            type_ref.file = getattr(resolved_enum, 'file', None)
                            type_ref.namespace = getattr(resolved_enum, 'namespace', None)
                        # Try alias mapping if not found
                        elif ref_qfn and alias_map:
                            parts = ref_qfn.split('::')
                            if parts and parts[0] in alias_map:
                                mapped_qfn = alias_map[parts[0]] + '::' + '::'.join(parts[1:])
                                # Try promoted QFN (Namespace::Message::fieldName -> Namespace::Message_fieldName)
                                if mapped_qfn in self.model_enum_by_qfn:
                                    resolved_enum = self.model_enum_by_qfn[mapped_qfn]
                                    ref_qfn = mapped_qfn
                                    type_names.append(mapped_qfn)
                                    type_ref = ModelReference(mapped_qfn, kind='enum')
                                    type_ref.name = resolved_enum.name
                                    type_ref.file = getattr(resolved_enum, 'file', None)
                                    type_ref.namespace = getattr(resolved_enum, 'namespace', None)
                                else:
                                    mapped_parts = mapped_qfn.split('::')
                                    if len(mapped_parts) >= 2:
                                        promoted_qfn = '::'.join(mapped_parts[:-1]) + '_' + mapped_parts[-1]
                                        if promoted_qfn in self.model_enum_by_qfn:
                                            resolved_enum = self.model_enum_by_qfn[promoted_qfn]
                                            ref_qfn = promoted_qfn
                                            type_names.append(promoted_qfn)
                                            type_ref = ModelReference(promoted_qfn, kind='enum')
                                            type_ref.name = resolved_enum.name
                                            type_ref.file = getattr(resolved_enum, 'file', None)
                                            type_ref.namespace = getattr(resolved_enum, 'namespace', None)
                                mapped_qfn = alias_map[parts[0]] + ('::' + '::'.join(parts[1:]) if len(parts) > 1 else '')
                                if mapped_qfn in enum_lookup:
                                    resolved_enum = enum_model_lookup.get(enum_lookup[mapped_qfn])
                                    resolved_qfn = mapped_qfn
                                    type_names.append(mapped_qfn)
                                    type_ref = ModelReference(mapped_qfn, kind='enum')
                                    type_ref.name = resolved_enum.name if resolved_enum else None
                                    type_ref.file = getattr(resolved_enum, 'file', None) if resolved_enum else None
                                    type_ref.namespace = getattr(resolved_enum, 'namespace', None) if resolved_enum else None
                        # Try to resolve by searching all enums by suffix (unqualified name)
                        if not resolved_enum and ref_qfn:
                            for qfn, early_enum in enum_lookup.items():
                                if qfn.endswith(f'::{ref_qfn}') or qfn == ref_qfn or qfn.split('::')[-1] == ref_qfn:
                                    resolved_enum = enum_model_lookup.get(early_enum)
                                    if resolved_enum:
                                        type_names.append(qfn)
                                        type_ref = ModelReference(qfn, kind='enum')
                                        type_ref.name = resolved_enum.name
                                        type_ref.file = getattr(resolved_enum, 'file', None)
                                        type_ref.namespace = getattr(resolved_enum, 'namespace', None)
                                        break
                        # Try to resolve by searching all enums by field type_name (if ref_qfn is None)
                        if not resolved_enum and type_name and type_name != '?':
                            for qfn, early_enum in enum_lookup.items():
                                if qfn.endswith(f'::{type_name}') or qfn == type_name or qfn.split('::')[-1] == type_name:
                                    resolved_enum = enum_model_lookup.get(early_enum)
                                    if resolved_enum:
                                        type_names.append(qfn)
                                        type_ref = ModelReference(qfn, kind='enum')
                                        type_ref.name = resolved_enum.name
                                        type_ref.file = getattr(resolved_enum, 'file', None)
                                        type_ref.namespace = getattr(resolved_enum, 'namespace', None)
                                        break
                    # Extra: Try to resolve by searching enums in the current namespace if still not found
                    if not resolved_enum and type_name and type_name != '?':
                        for enum in getattr(ns_for_inline, 'enums', []):
                            if enum.name == type_name:
                                resolved_enum = enum
                                if type_name not in type_names:
                                    type_names.append(type_name)
                                # Set type_ref to a ModelReference for this enum
                                for k, v in enum_lookup.items():
                                    if v is enum:
                                        type_ref = ModelReference(k, kind='enum')
                                        type_ref.name = enum.name
                                        type_ref.file = getattr(enum, 'file', None)
                                        type_ref.namespace = getattr(enum, 'namespace', None)
                                        break
                                break
                    if not resolved_enum:
                        print(f"[MODEL ERROR] Field '{getattr(field, 'name', '?')}' in message '{msg.name}' references unknown enum '{ref_qfn}'. Skipping type_ref.", file=sys.stderr)
                        print(f"[MODEL ERROR]   type_name: {type_name}", file=sys.stderr)
                        print(f"[MODEL ERROR]   enum_lookup keys: {list(enum_lookup.keys())}", file=sys.stderr)
                        # Try promoted inline QFN forms: e.g., EnumContainer.status -> EnumContainer_status, EnumContainer::status
                        promoted_qfn1 = type_name.replace('.', '_').replace('::', '_')
                        promoted_qfn2 = type_name.replace('.', '::')
                        # Try with file-level namespace prefix
                        file_ns = None
                        if hasattr(ns_for_inline, 'name') and ns_for_inline.name:
                            file_ns = ns_for_inline.name
                        promoted_qfn1_ns = f"{file_ns}::{promoted_qfn1}" if file_ns else promoted_qfn1
                        promoted_qfn2_ns = f"{file_ns}::{promoted_qfn2}" if file_ns else promoted_qfn2
                        found_promoted = False
                        for candidate in [promoted_qfn1, promoted_qfn2, promoted_qfn1_ns, promoted_qfn2_ns]:
                            if candidate in enum_lookup:
                                enum_obj = enum_lookup[candidate]
                                type_ref = ModelReference(candidate, kind='enum')
                                type_ref.name = getattr(enum_obj, 'name', None)
                                type_ref.file = getattr(enum_obj, 'file', None)
                                type_ref.namespace = getattr(enum_obj, 'namespace', None)
                                print(f"[PATCH] Promoted fallback: matched enum for field '{getattr(field, 'name', None)}' to QFN '{candidate}'", file=sys.stderr)
                                found_promoted = True
                                break
                        if not found_promoted:
                            type_names.append(type_name)
                            type_ref = None
                    # PATCH: Always set type_ref to a ModelReference for resolved enums (not just promoted/inline)
                    if type_ref is None:
                        # Try direct QFN
                        if ref_qfn and ref_qfn in enum_lookup:
                            enum_obj = enum_lookup[ref_qfn]
                            type_ref = ModelReference(ref_qfn, kind='enum')
                            type_ref.name = getattr(enum_obj, 'name', None)
                            type_ref.file = getattr(enum_obj, 'file', None)
                            type_ref.namespace = getattr(enum_obj, 'namespace', None)
                        else:
                            # Enhanced fallback: handle references like MessageName.field or Namespace::MessageName.field
                            if type_name and ('.' in type_name or '::' in type_name):
                                if '.' in type_name:
                                    msg_path, enum_field = type_name.rsplit('.', 1)
                                else:
                                    msg_path, enum_field = type_name.rsplit('::', 1)
                                msg_name = msg_path.split('::')[-1]
                                candidate_msgs = [qfn for qfn in msg_lookup.keys() if qfn == msg_path or qfn.endswith(f'::{msg_name}')]
                                for msg_qfn in candidate_msgs:
                                    candidate_enum_qfn = f"{msg_qfn}::{enum_field}"
                                    if candidate_enum_qfn in enum_lookup:
                                        enum_obj = enum_lookup[candidate_enum_qfn]
                                        type_ref = ModelReference(candidate_enum_qfn, kind='enum')
                                        type_ref.name = getattr(enum_obj, 'name', None)
                                        type_ref.file = getattr(enum_obj, 'file', None)
                                        type_ref.namespace = getattr(enum_obj, 'namespace', None)
                                        break
                            # Fallback: search all enums for a match by field name and parent message/namespace
                            if type_ref is None:
                                field_name = getattr(field, 'name', None)
                                for qfn, enum_obj in enum_lookup.items():
                                    if qfn.split('::')[-1] == field_name:
                                        type_ref = ModelReference(qfn, kind='enum')
                                        type_ref.name = getattr(enum_obj, 'name', None)
                                        type_ref.file = getattr(enum_obj, 'file', None)
                                        type_ref.namespace = getattr(enum_obj, 'namespace', None)
                                        print(f"[PATCH] Fallback: matched enum for field '{field_name}' to QFN '{qfn}'", file=sys.stderr)
                                        break
                    # --- PATCH: Ensure enum fields have aligned field_types/type_refs/type_names ---
                    # Always set the first entry to the resolved enum type, reference, and name
                    field_types.clear()
                    type_refs.clear()
                    type_names.clear()
                    field_types.append(FieldType.ENUM)
                    if type_ref is not None:
                        type_refs.append(type_ref)
                        # Use QFN if available, else enum name
                        if hasattr(type_ref, 'qfn') and type_ref.qfn:
                            type_names.append(type_ref.qfn)
                        elif hasattr(type_ref, 'name') and type_ref.name:
                            type_names.append(type_ref.name)
                        else:
                            type_names.append(type_name)
                    else:
                        type_refs.append(None)
                        type_names.append(type_name)
                # MESSAGE
                elif ftype == FieldType.MESSAGE:
                    # Always try to resolve the message reference for type_ref
                    resolved_ref_qfn = ref_qfn
                    if not resolved_ref_qfn and type_name and type_name != '?':
                        # Try to resolve by suffix (unqualified name)
                        for qfn in msg_lookup.keys():
                            if qfn.endswith(f'::{type_name}') or qfn == type_name:
                                resolved_ref_qfn = qfn
                                break
                    if resolved_ref_qfn and resolved_ref_qfn in msg_lookup:
                        msg_obj = msg_lookup[resolved_ref_qfn]
                        type_ref = ModelReference(resolved_ref_qfn, kind='message')
                        # Attach name, file, and namespace for generator
                        if hasattr(msg_obj, 'name'):
                            type_ref.name = getattr(msg_obj, 'name', None)
                        if hasattr(msg_obj, 'file'):
                            type_ref.file = getattr(msg_obj, 'file', None)
                        if hasattr(msg_obj, 'namespace'):
                            type_ref.namespace = getattr(msg_obj, 'namespace', None)
                        type_names.append(resolved_ref_qfn)
                    else:
                        type_names.append(type_name)
                        type_ref = None
                    type_refs.append(type_ref)
                # ARRAY
                elif ftype == FieldType.ARRAY:
                    etype_raw = getattr(field, 'element_type_raw', None)
                    etype_type = infer_type_type(etype_raw) if etype_raw else None
                    etype, etype_ref_qfn = map_field_type({'type_name': etype_raw, 'type_type': etype_type}) if etype_raw else (None, None)
                    field_types.append(etype)
                    element_type_ref = None
                    if etype == FieldType.ENUM and etype_ref_qfn:
                        element_type_ref = enum_model_lookup.get(enum_lookup[etype_ref_qfn])
                        type_names.append(etype_ref_qfn)
                    elif etype == FieldType.MESSAGE:
                        resolved_ref_qfn = etype_ref_qfn
                        if not resolved_ref_qfn and etype_raw and etype_raw != '?':
                            for qfn in msg_lookup.keys():
                                if qfn.endswith(f'::{etype_raw}') or qfn == etype_raw:
                                    resolved_ref_qfn = qfn
                                    break
                        if resolved_ref_qfn and resolved_ref_qfn in msg_lookup:
                            msg_obj = msg_lookup[resolved_ref_qfn]
                            element_type_ref = ModelReference(resolved_ref_qfn, kind='message')
                            # Attach name, file, and namespace for generator
                            if hasattr(msg_obj, 'name'):
                                element_type_ref.name = getattr(msg_obj, 'name', None)
                            if hasattr(msg_obj, 'file'):
                                element_type_ref.file = getattr(msg_obj, 'file', None)
                            if hasattr(msg_obj, 'namespace'):
                                element_type_ref.namespace = getattr(msg_obj, 'namespace', None)
                            type_names.append(resolved_ref_qfn)
                        else:
                            type_names.append(etype_raw)
                    else:
                        type_names.append(etype_raw)
                    type_refs.append(None)  # ARRAY itself has no ref
                    type_refs.append(element_type_ref)
                # MAP
                elif ftype == FieldType.MAP:
                    ktype_raw = getattr(field, 'map_key_type_raw', None)
                    vtype_raw = getattr(field, 'map_value_type_raw', None)
                    primitives = {'int', 'string', 'bool', 'float', 'double'}
                    print(f"[MAP DEBUG] dict_field: ktype_raw={ktype_raw}, vtype_raw={vtype_raw}")
                    # Key type
                    if ktype_raw is not None:
                        # Always treat primitives as 'primitive', never 'map_type' for keys
                        if ktype_raw in primitives:
                            ktype_type = 'primitive'
                        else:
                            ktype_type = infer_type_type(ktype_raw)
                        # Defensive: if ktype_type is None, but ktype_raw is primitive, force to 'primitive'
                        if not ktype_type and ktype_raw in primitives:
                            ktype_type = 'primitive'
                        # Defensive: if ktype_type is 'map_type', but ktype_raw is primitive, force to 'primitive'
                        if ktype_type == 'map_type' and ktype_raw in primitives:
                            ktype_type = 'primitive'
                        print(f"[MAP DEBUG] dict_field: after infer, ktype_type={ktype_type}")
                        print(f"[MAP DEBUG] ktype_raw={ktype_raw}, ktype_type={ktype_type}")
                        ktype, ktype_ref_qfn = map_field_type({'type_name': ktype_raw, 'type_type': ktype_type})
                        print(f"[MAP DEBUG] ktype result: ktype={ktype}, ktype_ref_qfn={ktype_ref_qfn}")
                    else:
                        ktype, ktype_ref_qfn = None, None
                    # Value type
                    if vtype_raw is not None:
                        if vtype_raw in primitives:
                            vtype_type = 'primitive'
                        else:
                            vtype_type = infer_type_type(vtype_raw)
                        if not vtype_type and vtype_raw in primitives:
                            vtype_type = 'primitive'
                        if vtype_type == 'map_type' and vtype_raw in primitives:
                            vtype_type = 'primitive'
                        print(f"[MAP DEBUG] dict_field: after infer, vtype_type={vtype_type}")
                        print(f"[MAP DEBUG] vtype_raw={vtype_raw}, vtype_type={vtype_type}")
                        vtype, vtype_ref_qfn = map_field_type({'type_name': vtype_raw, 'type_type': vtype_type})
                        print(f"[MAP DEBUG] vtype result: vtype={vtype}, vtype_ref_qfn={vtype_ref_qfn}")
                    else:
                        vtype, vtype_ref_qfn = None, None
                    # Only three entries: [MAP, key_type, value_type]
                    field_types.append(FieldType.MAP)
                    field_types.append(ktype)
                    field_types.append(vtype)
                    type_names.append('MAP')
                    type_names.append(ktype_raw)
                    type_names.append(vtype_raw)
                    map_key_type_ref = None
                    map_value_type_ref = None
                    if ktype == FieldType.ENUM and ktype_ref_qfn:
                        map_key_type_ref = enum_model_lookup.get(enum_lookup[ktype_ref_qfn])
                    elif ktype == FieldType.MESSAGE and ktype_ref_qfn:
                        # Set ModelReference and attach name, file, and namespace for generator
                        map_key_type_ref = ModelReference(ktype_ref_qfn, kind='message')
                        msg_obj = msg_lookup.get(ktype_ref_qfn)
                        if msg_obj is not None:
                            if hasattr(msg_obj, 'name'):
                                map_key_type_ref.name = getattr(msg_obj, 'name', None)
                            if hasattr(msg_obj, 'file'):
                                map_key_type_ref.file = getattr(msg_obj, 'file', None)
                            if hasattr(msg_obj, 'namespace'):
                                map_key_type_ref.namespace = getattr(msg_obj, 'namespace', None)
                    if vtype == FieldType.ENUM and vtype_ref_qfn:
                        map_value_type_ref = enum_model_lookup.get(enum_lookup[vtype_ref_qfn])
                    elif vtype == FieldType.MESSAGE and vtype_ref_qfn:
                        map_value_type_ref = ModelReference(vtype_ref_qfn, kind='message')
                        msg_obj = msg_lookup.get(vtype_ref_qfn)
                        if msg_obj is not None:
                            if hasattr(msg_obj, 'name'):
                                map_value_type_ref.name = getattr(msg_obj, 'name', None)
                            if hasattr(msg_obj, 'file'):
                                map_value_type_ref.file = getattr(msg_obj, 'file', None)
                            if hasattr(msg_obj, 'namespace'):
                                map_value_type_ref.namespace = getattr(msg_obj, 'namespace', None)
                    type_refs.append(None)  # MAP itself has no ref
                    type_refs.append(map_key_type_ref)
                    type_refs.append(map_value_type_ref)
                else:
                    # Base types, compounds, options, etc.
                    type_refs.append(None)
                    type_names.append(type_name)
                # Promote inline enums/options to top-level enums in the containing namespace
                if getattr(field, 'is_inline_enum', False) and getattr(field, 'inline_values_raw', None):
                    enum_name = f"{msg.name}_{field.name}"
                    enum_values = [
                        ModelEnumValue(
                            v.get('name', '?'),
                            v.get('value', None),
                            doc=v.get('doc', None),
                            comment=v.get('comment', None),
                            file=v.get('file', None),
                            line=v.get('line', None),
                            namespace=v.get('namespace', None)
                        ) for v in field.inline_values_raw
                    ]
                    model_enum = ModelEnum(
                        name=enum_name,
                        values=enum_values,
                        is_open=False,
                        parent=None,
                        doc=None,
                        comment=None,
                        parent_raw=None,
                        file=getattr(field, 'file', None),
                        line=getattr(field, 'line', None),
                        namespace=getattr(field, 'namespace', None)
                    )
                    # Add to containing namespace's enums if not already present
                    if not any(e.name == enum_name for e in ns_for_inline.enums):
                        ns_for_inline.enums.append(model_enum)
                    # Set type_ref to this enum
                    type_ref = model_enum
                    type_names.append(enum_name)
                # Map modifiers_raw (list of str) to FieldModifier enum values
                modifiers_raw = getattr(field, 'modifiers_raw', [])
                modifiers = []
                for m in modifiers_raw:
                    try:
                        modifiers.append(FieldModifier(m.upper()))
                    except Exception:
                        # fallback: try by value
                        for mod in FieldModifier:
                            if mod.value == m:
                                modifiers.append(mod)
                                break
                # If this is a compound field, pass base type and components
                compound_base_type = None
                compound_components = None
                if (ftype == FieldType.COMPOUND or type_type in ('compound', 'compound_type')):
                    compound_base_type = getattr(field, 'compound_base_type_raw', None)
                    compound_components = getattr(field, 'compound_components_raw', None)
                model_field = ModelField(
                    name=field.name,
                    field_types=field_types,
                    type_refs=type_refs,
                    type_names=type_names,
                    modifiers=modifiers,
                    default=getattr(field, 'default_value_raw', None),
                    doc=getattr(field, 'doc', None),
                    comment=getattr(field, 'comment', None),
                    inline_values=[],  # Inline enums are now promoted
                    file=getattr(field, 'file', None),
                    line=getattr(field, 'line', None),
                    namespace=getattr(field, 'namespace', None),
                    compound_base_type=compound_base_type,
                    compound_components=compound_components
                )
                fields.append(model_field)
                # DEBUG: Print ModelField construction for enum fields
                try:
                    if any((hasattr(ftype, 'name') and ftype.name == 'ENUM') or ftype == FieldType.ENUM for ftype in field_types):
                        print(f"[DEBUG MODELFIELD] name={field.name} field_types={field_types} type_refs={type_refs} type_names={type_names}", file=sys.stderr)
                except Exception as e:
                    pass            # Convert parent_raw to ModelReference if present
            parent_ref = None
            parent_raw = getattr(msg, 'parent_raw', None)
            if parent_raw:
                # Map parent_raw using alias_map if it starts with an alias (like Base::)
                mapped_parent_raw = parent_raw
                if parent_raw and isinstance(parent_raw, str) and '::' in parent_raw and alias_map:
                    first = parent_raw.split('::', 1)[0]
                    if first in alias_map:
                        mapped_parent_raw = alias_map[first] + '::' + parent_raw.split('::', 1)[1]
                # Try to resolve the mapped_parent_raw QFN to set name and file for generator import logic
                resolved_parent_qfn = mapped_parent_raw
                if resolved_parent_qfn not in msg_lookup and mapped_parent_raw and mapped_parent_raw != '?':
                    for qfn in msg_lookup.keys():
                        if qfn.endswith(f'::{mapped_parent_raw}') or qfn == mapped_parent_raw:
                            resolved_parent_qfn = qfn
                            break
                parent_ref = ModelReference(resolved_parent_qfn, kind='message')
                parent_msg_obj = msg_lookup.get(resolved_parent_qfn)
                if parent_msg_obj is not None:
                    if hasattr(parent_msg_obj, 'name'):
                        parent_ref.name = getattr(parent_msg_obj, 'name', None)
                    if hasattr(parent_msg_obj, 'file'):
                        parent_ref.file = getattr(parent_msg_obj, 'file', None)
                    if hasattr(parent_msg_obj, 'namespace'):
                        parent_ref.namespace = getattr(parent_msg_obj, 'namespace', None)
            model_msg = ModelMessage(
                name=msg.name,
                fields=fields,
                parent=parent_ref,
                doc=getattr(msg, 'doc', None),
                comment=getattr(msg, 'comment', None),
                parent_raw=parent_raw,
                file=getattr(msg, 'file', None),
                line=getattr(msg, 'line', None),
                namespace=getattr(msg, 'namespace', None)
            )
            # Set parent reference on all fields
            for field in fields:
                field.parent = model_msg
            msg_model_lookup[msg] = model_msg
            return model_msg

        # Convert namespaces recursively
        def convert_namespace(ns):
            print(f"[DEBUG] Model transform: enums in namespace '{ns.name}': {[e.name for e in ns.enums]}", file=sys.stderr)
            enums = [convert_enum(e) for e in getattr(ns, 'enums', [])]
            messages = [convert_message(m) for m in getattr(ns, 'messages', [])]
            namespaces = [convert_namespace(n) for n in getattr(ns, 'namespaces', [])]
            model_ns = ModelNamespace(
                name=ns.name,
                messages=messages,
                enums=enums,
                namespaces=namespaces,
                doc=getattr(ns, 'doc', None),
                comment=getattr(ns, 'comment', None),
                options=getattr(ns, 'options', []),
                compounds=getattr(ns, 'compounds', []),
                file=getattr(ns, 'file', None),
                line=getattr(ns, 'line', None),
                parent_namespace=getattr(ns, 'parent_namespace', None)
            )
            return model_ns

        model_namespaces = [convert_namespace(ns) for ns in early_model.namespaces]
        # Collect and convert all options from all namespaces recursively
        def collect_options_from_namespaces(namespaces):
            result = []
            for ns in namespaces:
                for opt in getattr(ns, 'options', []):
                    values = [
                        ModelEnumValue(
                            v.get('name', '?'),
                            v.get('value', None),
                            doc=v.get('doc', None),
                            comment=v.get('comment', None),
                            file=v.get('file', None),
                            line=v.get('line', None),
                            namespace=v.get('namespace', None)
                        ) for v in opt.get('values_raw', [])
                    ]
                    opt_name = opt.get('name', '?')
                    ns_name = ns.name if ns.name and ns.name != '?' else None
                    if ns_name:
                        opt_name = f"{ns_name}::{opt_name}"
                    model_enum = ModelEnum(
                        name=opt_name,
                        values=values,
                        is_open=False,
                        parent=None,
                        doc=opt.get('doc', None),
                        comment=opt.get('comment', None),
                        parent_raw=None,
                        file=opt.get('file', None),
                        line=opt.get('line', None),
                        namespace=ns_name
                    )
                    result.append(model_enum)
                # Recurse into nested namespaces
                result.extend(collect_options_from_namespaces(getattr(ns, 'namespaces', [])))
            return result

        options = collect_options_from_namespaces(getattr(early_model, 'namespaces', []))
        compounds = getattr(early_model, 'compounds', [])
        return Model(
            file=early_model.file,
            namespaces=model_namespaces,
            options=options,
            compounds=compounds,
            alias_map=alias_map,
            imports=imports_dict
        )
