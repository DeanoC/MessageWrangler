"""
Model transform to make enum value names unique by prefixing them with the enum name.
This is only intended for use in the TypeScript generator pipeline.
"""

class PrefixEnumValueNamesTransform:
    def transform(self, model):
        for ns in getattr(model, 'namespaces', []):
            for enum in getattr(ns, 'enums', []):
                enum_name = enum.name
                seen = set()
                for value in enum.values:
                    # Only prefix if not already prefixed
                    original_name = value.name
                    prefixed_name = f"{enum_name}_{original_name}" if not original_name.startswith(enum_name + "_") else original_name
                    # Avoid double prefixing
                    value.name = prefixed_name
                    if prefixed_name in seen:
                        raise ValueError(f"Duplicate enum value name after prefixing: {prefixed_name}")
                    seen.add(prefixed_name)
        return model
