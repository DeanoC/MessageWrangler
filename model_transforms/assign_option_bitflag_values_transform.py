"""
Model Transform: AssignOptionBitflagValuesTransform
Assigns bitflag (1, 2, 4, ...) values to all enums used as options in the Model.
This ensures that all options enums (including those promoted from inline options) have correct bitflag values before code generation.
"""
from model import Model, ModelEnum, ModelEnumValue, ModelNamespace

class AssignOptionBitflagValuesTransform:
    def transform(self, model: Model) -> Model:
        # Collect all enums used as options
        option_enum_names = set()
        def collect_option_enums(ns: ModelNamespace):
            for msg in getattr(ns, 'messages', []):
                for field in getattr(msg, 'fields', []):
                    ftypes = getattr(field, 'field_types', [])
                    if ftypes and ftypes[0].name == 'OPTIONS':
                        # The type name for the enum used by this options field
                        trefs = getattr(field, 'type_refs', [])
                        if trefs and hasattr(trefs[0], 'name') and trefs[0].name:
                            option_enum_names.add(trefs[0].name)
                        elif hasattr(field, 'type_names') and field.type_names:
                            for tname in field.type_names:
                                if tname:
                                    option_enum_names.add(tname)
                        else:
                            # Fallback: promoted inline options, use CamelCase
                            camel = lambda s: ''.join([p[:1].upper() + p[1:] for p in s.replace('::','').split('_') if p])
                            option_enum_names.add(camel(f"{msg.name}_{field.name}"))
            for nested in getattr(ns, 'namespaces', []):
                collect_option_enums(nested)
        for ns in getattr(model, 'namespaces', []):
            collect_option_enums(ns)
        # Assign bitflag values to all enums whose name matches
        def assign_bitflags(ns: ModelNamespace):
            for enum in getattr(ns, 'enums', []):
                # Match by CamelCase name
                camel = lambda s: ''.join([p[:1].upper() + p[1:] for p in s.replace('::','').split('_') if p])
                print(f"[BITFLAG] Enum: {enum.name} (Camel: {camel(enum.name)})")
                print(f"[BITFLAG] option_enum_names: {option_enum_names}")
                if enum.name in option_enum_names or camel(enum.name) in option_enum_names:
                    print(f"[BITFLAG] Assigning bitflags to enum: {enum.name}")
                    val = 1
                    for v in enum.values:
                        v.value = None  # Clear any existing value
                    for v in enum.values:
                        v.value = val
                        val <<= 1
            for nested in getattr(ns, 'namespaces', []):
                assign_bitflags(nested)
        for ns in getattr(model, 'namespaces', []):
            assign_bitflags(ns)
        return model
