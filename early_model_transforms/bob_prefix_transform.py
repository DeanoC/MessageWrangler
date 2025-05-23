"""
BobPrefixTransform: Adds 'BOB_' prefix to all names in the EarlyModel.
"""
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum, EarlyField
from early_transform_pipeline import EarlyTransform

class BobPrefixTransform(EarlyTransform):
    def transform(self, model: EarlyModel) -> EarlyModel:
        def prefix_name(obj):
            if hasattr(obj, 'name') and not obj.name.startswith('BOB_'):
                obj.name = 'BOB_' + obj.name
        def walk_ns(ns: EarlyNamespace):
            prefix_name(ns)
            for msg in ns.messages:
                prefix_name(msg)
                for field in msg.fields:
                    prefix_name(field)
            for enum in ns.enums:
                prefix_name(enum)
                for value in enum.values:
                    prefix_name(value)
            for nested in ns.namespaces:
                walk_ns(nested)
        for ns in model.namespaces:
            walk_ns(ns)
        for msg in model.messages:
            prefix_name(msg)
            for field in msg.fields:
                prefix_name(field)
        for enum in model.enums:
            prefix_name(enum)
            for value in enum.values:
                prefix_name(value)
        return model
