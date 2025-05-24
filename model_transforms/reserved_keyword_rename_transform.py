"""
reserved_keyword_rename_transform.py
A ModelTransform that renames any message, field, or enum name that matches a reserved keyword list, adding a generator-specific prefix.
"""
from typing import List, Set
from model import Model, ModelNamespace, ModelMessage, ModelEnum, ModelField

class ReservedKeywordRenameTransform:
    def __init__(self, reserved_keywords: Set[str], prefix: str):
        self.reserved_keywords = set(reserved_keywords)
        self.prefix = prefix

    def transform(self, model: Model) -> Model:
        # Build a mapping of old_name -> new_name for all namespaces, messages, enums
        rename_map = {}
        # First pass: collect all renames
        for ns in model.namespaces:
            self._collect_renames(ns, rename_map, parent_ns=None)
        # Second pass: apply renames and update references
        for ns in model.namespaces:
            self._apply_renames(ns, rename_map, parent_ns=None)
        return model

    def _collect_renames(self, ns: ModelNamespace, rename_map: dict, parent_ns: str = None):
        # Namespace
        ns_qfn = ns.name if not parent_ns else f"{parent_ns}::{ns.name}"
        if ns.name in self.reserved_keywords:
            rename_map[ns_qfn] = self.prefix + ns.name
        # Enums
        for enum in ns.enums:
            enum_qfn = f"{ns_qfn}::{enum.name}"
            if enum.name in self.reserved_keywords:
                rename_map[enum_qfn] = self.prefix + enum.name
        # Messages
        for msg in ns.messages:
            msg_qfn = f"{ns_qfn}::{msg.name}"
            if msg.name in self.reserved_keywords:
                rename_map[msg_qfn] = self.prefix + msg.name
        # Nested namespaces
        for child_ns in getattr(ns, 'namespaces', []):
            self._collect_renames(child_ns, rename_map, ns_qfn)

    def _apply_renames(self, ns: ModelNamespace, rename_map: dict, parent_ns: str = None):
        ns_qfn = ns.name if not parent_ns else f"{parent_ns}::{ns.name}"
        # Rename namespace if needed
        if ns_qfn in rename_map:
            ns.name = rename_map[ns_qfn]
            ns_qfn = ns.name if not parent_ns else f"{parent_ns}::{ns.name}"
        # Enums
        for enum in ns.enums:
            enum_qfn = f"{ns_qfn}::{enum.name}"
            if enum_qfn in rename_map:
                enum.name = rename_map[enum_qfn]
            # Enum values
            for value in enum.values:
                if value.name in self.reserved_keywords:
                    value.name = self.prefix + value.name
        # Messages
        for msg in ns.messages:
            msg_qfn = f"{ns_qfn}::{msg.name}"
            if msg_qfn in rename_map:
                msg.name = rename_map[msg_qfn]
            # Parent reference (inheritance)
            if hasattr(msg, 'parent') and msg.parent:
                # parent is a ModelReference or similar
                if hasattr(msg.parent, 'qfn') and msg.parent.qfn in rename_map:
                    msg.parent.qfn = rename_map[msg.parent.qfn]
                elif isinstance(msg.parent, str) and msg.parent in rename_map:
                    msg.parent = rename_map[msg.parent]
            # Fields
            for field in msg.fields:
                if field.name in self.reserved_keywords:
                    field.name = self.prefix + field.name
                # Field type references (type_names)
                if hasattr(field, 'type_names'):
                    for i, tname in enumerate(field.type_names):
                        if tname is not None:
                            # Try to match QFN or simple name
                            for k, v in rename_map.items():
                                if tname == k.split('::')[-1]:
                                    field.type_names[i] = v
                                elif tname == k:
                                    field.type_names[i] = v
                # Compound base type
                if hasattr(field, 'compound_base_type') and field.compound_base_type in self.reserved_keywords:
                    field.compound_base_type = self.prefix + field.compound_base_type
        # Nested namespaces
        for child_ns in getattr(ns, 'namespaces', []):
            self._apply_renames(child_ns, rename_map, ns_qfn)
