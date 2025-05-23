"""
Transform: Converts a fully-resolved EarlyModel into a concrete Model for code generation.
"""
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
        for ns in early_model.namespaces:
            build_lookup_ns(ns, [])

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
                if type_name in msg_lookup:
                    return FieldType.MESSAGE, type_name
                return FieldType.MESSAGE, type_name
            elif type_type == 'compound_type':
                return FieldType.COMPOUND, type_name
            elif type_type == 'options_type':
                return FieldType.OPTIONS, type_name
            elif type_type == 'array_type':
                return FieldType.ARRAY, type_name
            elif type_type == 'map_type':
                return FieldType.MAP, type_name
            # fallback
            return FieldType.STRING, type_name

        # Convert enums
        enum_model_lookup = {}
        def convert_enum(enum, parent=None):
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
                parent=parent,
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
            for field in getattr(msg, 'fields', []):
                # Build the field_types, type_refs, and type_names arrays
                field_types = []
                type_refs = []
                type_names = []
                inline_values = []
                # Infer type_type for the top-level field
                def infer_type_type(type_name):
                    primitives = {'int', 'string', 'bool', 'float', 'double'}
                    if type_name in primitives:
                        return 'primitive'
                    if type_name in enum_lookup:
                        return 'enum_type'
                    elif type_name in msg_lookup:
                        return 'message_type'
                    return None
                type_name = getattr(field, 'type_name', None)
                type_type = getattr(field, 'type_type', None) or infer_type_type(type_name)
                ftype, ref_qfn = map_field_type({'type_name': type_name, 'type_type': type_type})
                # Base type
                field_types.append(ftype)
                type_ref = None
                # ENUM
                if ftype == FieldType.ENUM:
                    if getattr(field, 'is_inline_enum', False):
                        inline_enum_name = f"{msg.name}_{field.name}_InlineEnum"
                        inline_enum_values = [
                            ModelEnumValue(
                                v.get('name', '?'),
                                v.get('value', None),
                                doc=v.get('doc', None),
                                comment=v.get('comment', None),
                                file=v.get('file', None),
                                line=v.get('line', None),
                                namespace=v.get('namespace', None)
                            ) for v in getattr(field, 'inline_values_raw', [])
                        ]
                        inline_enum = ModelEnum(
                            name=inline_enum_name,
                            values=inline_enum_values,
                            is_open=False,
                            parent=None,
                            doc=getattr(field, 'doc', None),
                            comment=getattr(field, 'comment', None),
                            parent_raw=None,
                            file=getattr(field, 'file', None),
                            line=getattr(field, 'line', None),
                            namespace=getattr(field, 'namespace', None)
                        )
                        type_ref = inline_enum
                        type_names.append(inline_enum_name)
                        if not hasattr(msg, '_inline_enums'):
                            msg._inline_enums = []
                        msg._inline_enums.append(inline_enum)
                    elif ref_qfn:
                        type_ref = enum_model_lookup.get(enum_lookup[ref_qfn])
                        type_names.append(ref_qfn)
                    else:
                        type_names.append(type_name)
                    type_refs.append(type_ref)
                # MESSAGE
                elif ftype == FieldType.MESSAGE:
                    if ref_qfn:
                        type_ref = msg_model_lookup.get(msg_lookup[ref_qfn])
                        type_names.append(ref_qfn)
                    else:
                        type_names.append(type_name)
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
                        element_type_ref = msg_model_lookup.get(msg_lookup[etype_ref_qfn])
                        type_names.append(etype_ref_qfn)
                    else:
                        type_names.append(etype_raw)
                    type_refs.append(None)  # ARRAY itself has no ref
                    type_refs.append(element_type_ref)
                # MAP
                elif ftype == FieldType.MAP:
                    ktype_raw = getattr(field, 'map_key_type_raw', None)
                    vtype_raw = getattr(field, 'map_value_type_raw', None)
                    ktype_type = infer_type_type(ktype_raw) if ktype_raw else None
                    vtype_type = infer_type_type(vtype_raw) if vtype_raw else None
                    ktype, ktype_ref_qfn = map_field_type({'type_name': ktype_raw, 'type_type': ktype_type}) if ktype_raw else (None, None)
                    vtype, vtype_ref_qfn = map_field_type({'type_name': vtype_raw, 'type_type': vtype_type}) if vtype_raw else (None, None)
                    field_types.extend([ktype, vtype])
                    map_key_type_ref = None
                    map_value_type_ref = None
                    if ktype == FieldType.ENUM and ktype_ref_qfn:
                        map_key_type_ref = enum_model_lookup.get(enum_lookup[ktype_ref_qfn])
                        type_names.append(ktype_ref_qfn)
                    elif ktype == FieldType.MESSAGE and ktype_ref_qfn:
                        map_key_type_ref = msg_model_lookup.get(msg_lookup[ktype_ref_qfn])
                        type_names.append(ktype_ref_qfn)
                    else:
                        type_names.append(ktype_raw)
                    if vtype == FieldType.ENUM and vtype_ref_qfn:
                        map_value_type_ref = enum_model_lookup.get(enum_lookup[vtype_ref_qfn])
                        type_names.append(vtype_ref_qfn)
                    elif vtype == FieldType.MESSAGE and vtype_ref_qfn:
                        map_value_type_ref = msg_model_lookup.get(msg_lookup[vtype_ref_qfn])
                        type_names.append(vtype_ref_qfn)
                    else:
                        type_names.append(vtype_raw)
                    type_refs.append(None)  # MAP itself has no ref
                    type_refs.append(map_key_type_ref)
                    type_refs.append(map_value_type_ref)
                else:
                    # Base types, compounds, options, etc.
                    type_refs.append(None)
                    type_names.append(type_name)
                # Handle inline enums/options for the field
                if getattr(field, 'inline_values_raw', None):
                    for v in field.inline_values_raw:
                        inline_values.append(
                            ModelEnumValue(
                                v.get('name', '?'),
                                v.get('value', None),
                                doc=v.get('doc', None),
                                comment=v.get('comment', None),
                                file=v.get('file', None),
                                line=v.get('line', None),
                                namespace=v.get('namespace', None)
                            )
                        )
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
                model_field = ModelField(
                    name=field.name,
                    field_types=field_types,
                    type_refs=type_refs,
                    type_names=type_names,
                    modifiers=modifiers,
                    default=getattr(field, 'default_value_raw', None),
                    doc=getattr(field, 'doc', None),
                    comment=getattr(field, 'comment', None),
                    inline_values=inline_values,
                    file=getattr(field, 'file', None),
                    line=getattr(field, 'line', None),
                    namespace=getattr(field, 'namespace', None)
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
        # Carry over options/compounds from EarlyModel
        options = getattr(early_model, 'options', [])
        compounds = getattr(early_model, 'compounds', [])
        # Build alias map and imports dict from imports_raw
        alias_map = {}
        imports_dict = {}
        if hasattr(early_model, 'imports_raw') and hasattr(early_model, 'imports'):
            for import_path, alias in getattr(early_model, 'imports_raw', []):
                key = alias if alias else import_path
                imported_model = early_model.imports.get(key)
                if imported_model:
                    imports_dict[key] = EarlyModelToModelTransform().transform(imported_model)
                if alias and imported_model and imported_model.namespaces:
                    file_ns = imported_model.namespaces[0]
                    alias_map[alias] = file_ns.name
        return Model(
            file=early_model.file,
            namespaces=model_namespaces,
            options=options,
            compounds=compounds,
            alias_map=alias_map,
            imports=imports_dict
        )
