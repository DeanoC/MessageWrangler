"""
Transform: Converts a fully-resolved EarlyModel into a concrete Model for code generation.
"""
import sys
from early_model import EarlyModel
from model import Model, ModelNamespace, ModelMessage, ModelEnum, ModelField, ModelEnumValue, FieldType, FieldModifier
from model import ModelReference

class EarlyModelToModelTransform:
    def transform(self, early_model: EarlyModel) -> Model:
        """
        Convert a fully-resolved EarlyModel to a concrete Model.
        All references must be QFN and resolvable.
        """
        # First, build a lookup of all enums and messages by QFN for reference resolution
        enum_lookup = {}
        msg_lookup = {}
        import sys
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
            elif type_type == 'enum_type':
                if getattr(field, 'is_inline_enum', False):
                    return FieldType.ENUM, None
                if type_name in enum_lookup:
                    return FieldType.ENUM, type_name
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
                    imported_model_obj = EarlyModelToModelTransform().transform(imported_model)
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
            import sys
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
                import sys
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
            enum_model_lookup[enum] = model_enum
            return model_enum

        # Convert messages
        msg_model_lookup = {}
        def convert_message(msg, parent=None):
            fields = []
            # To add inline enums to the containing namespace
            containing_ns = getattr(msg, 'parent_container', None)
            ns_for_inline = containing_ns if containing_ns else ns  # fallback to current ns
            for field in getattr(msg, 'fields', []):
                # Build the field_types, type_refs, and type_names arrays
                field_types = []
                type_refs = []
                type_names = []
                inline_values = []
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
                        map_value_type_ref = ModelReference(vtype_ref_qfn, kind='message')
                    type_refs.append(None)  # MAP itself has no ref
                    type_refs.append(map_key_type_ref)
                    type_refs.append(map_value_type_ref)
                else:
                    # Defensive: If type_name is '?' or None, treat as invalid and skip enum/message resolution
                    if type_name == '?' or type_name is None:
                        print(f"[MODEL ERROR] Field '{getattr(field, 'name', '?')}' in message '{msg.name}' has invalid type_name ('?'). Skipping enum/message resolution.")
                        ftype, ref_qfn = FieldType.STRING, type_name
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
                    # Inline enums are promoted, so this field should always reference a top-level enum.
                    if ref_qfn and ref_qfn in enum_lookup:
                        type_ref = enum_model_lookup.get(enum_lookup[ref_qfn])
                        type_names.append(ref_qfn)
                    else:
                        # Try to find a promoted inline enum by name pattern
                        promoted_name = f"{msg.name}_{field.name}"
                        promoted_enum = next((e for e in ns_for_inline.enums if e.name == promoted_name), None)
                        if promoted_enum:
                            type_ref = promoted_enum
                            type_names.append(promoted_name)
                        else:
                            print(f"[MODEL ERROR] Field '{getattr(field, 'name', '?')}' in message '{msg.name}' references unknown enum '{ref_qfn}'. Skipping type_ref.")
                            type_names.append(type_name)
                            type_ref = None
                    type_refs.append(type_ref)
                # MESSAGE
                elif ftype == FieldType.MESSAGE:
                    if ref_qfn:
                        # Use ModelReference for message fields
                        type_ref = ModelReference(ref_qfn, kind='message')
                        type_names.append(ref_qfn)
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
                    elif etype == FieldType.MESSAGE and etype_ref_qfn:
                        # Use ModelReference for array element if message
                        element_type_ref = ModelReference(etype_ref_qfn, kind='message')
                        type_names.append(etype_ref_qfn)
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
                        map_key_type_ref = msg_model_lookup.get(msg_lookup[ktype_ref_qfn])
                    if vtype == FieldType.ENUM and vtype_ref_qfn:
                        map_value_type_ref = enum_model_lookup.get(enum_lookup[vtype_ref_qfn])
                    elif vtype == FieldType.MESSAGE and vtype_ref_qfn:
                        map_value_type_ref = ModelReference(vtype_ref_qfn, kind='message')
                    type_refs.append(None)  # MAP itself has no ref
                    type_refs.append(map_key_type_ref)
                    type_refs.append(map_value_type_ref)
                else:
                    # Base types, compounds, options, etc.
                    type_refs.append(None)
                    type_names.append(type_name)
                # Promote inline enums/options to top-level enums in the containing namespace
                if getattr(field, 'inline_values_raw', None):
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
            # Convert parent_raw to ModelReference if present
            parent_ref = None
            parent_raw = getattr(msg, 'parent_raw', None)
            if parent_raw:
                parent_ref = ModelReference(parent_raw, kind='message')
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
