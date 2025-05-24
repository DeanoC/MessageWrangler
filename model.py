"""
model.py
Concrete, generator-ready representation of a parsed .def file. All references are resolved and all fields are concrete.
"""
from enum import Enum, auto
from typing import List, Dict, Optional, Union, Any

class ModelReference:
    """
    Reference to any entity in the Model (message, enum, namespace, etc.).
    Stores the QFN (qualified fully name) and the kind (e.g., 'message', 'enum', 'namespace').
    """
    def __init__(self, qfn: str, kind: str):
        self.qfn = qfn
        self.kind = kind
    def __repr__(self):
        return f"ModelReference(qfn={self.qfn!r}, kind={self.kind!r})"


class FieldModifier(Enum):
    OPTIONAL = "optional"
    REPEATED = "repeated"
    REQUIRED = "required"

class FieldType(Enum):
    INT = "int"
    STRING = "string"
    BOOL = "bool"
    FLOAT = "float"
    DOUBLE = "double"
    ENUM = "enum"
    MESSAGE = "message"
    COMPOUND = "compound"
    OPTIONS = "options"
    ARRAY = "array"
    MAP = "map"
    # Add more as needed to match all EarlyModel types

class ModelField:
    @property
    def type_ref(self):
        """
        Compatibility property for legacy code/tests expecting 'type_ref' on ModelField.
        Returns the first type_ref in type_refs, or None if empty.
        """
        return self.type_refs[0] if self.type_refs else None
    @property
    def type(self):
        """
        Compatibility property for legacy code/tests expecting 'type' on ModelField.
        Returns the first FieldType in field_types, or None if empty.
        """
        return self.field_types[0] if self.field_types else None
    def __init__(
        self,
        name: str,
        field_types: list,  # List[FieldType], always at least 1, up to 3 for maps
        type_refs: list = None,  # List[Optional[Any]], same length as field_types
        type_names: list = None,  # List[Optional[str]], for debugging
        modifiers: Optional[List[FieldModifier]] = None,
        default: Optional[Any] = None,
        doc: Optional[str] = None,
        comment: Optional[str] = None,
        inline_values: Optional[List['ModelEnumValue']] = None,  # For inline enums/options
        file: Optional[str] = None,
        line: Optional[int] = None,
        namespace: Optional[str] = None,
    ):
        self.name = name
        self.field_types = field_types
        self.type_refs = type_refs or [None] * len(field_types)
        self.type_names = type_names or [None] * len(field_types)
        self.modifiers = modifiers or []
        self.default = default
        self.doc = doc
        self.comment = comment
        self.inline_values = inline_values or []
        self.file = file
        self.line = line
        self.namespace = namespace

class ModelEnumValue:
    def __init__(self, name: str, value: int, doc: Optional[str] = None, comment: Optional[str] = None, file: Optional[str] = None, line: Optional[int] = None, namespace: Optional[str] = None):
        self.name = name
        self.value = value
        self.doc = doc
        self.comment = comment
        self.file = file
        self.line = line
        self.namespace = namespace

class ModelEnum:
    def __init__(self, name: str, values: List['ModelEnumValue'], is_open: bool = False, parent: Optional['ModelEnum'] = None, doc: Optional[str] = None, comment: Optional[str] = None, parent_raw: Optional[str] = None, file: Optional[str] = None, line: Optional[int] = None, namespace: Optional[str] = None):
        self.name = name
        self.values = values
        self.is_open = is_open
        self.parent = parent
        self.doc = doc
        self.comment = comment
        self.parent_raw = parent_raw
        self.file = file
        self.line = line
        self.namespace = namespace

class ModelMessage:
    def __init__(self, name: str, fields: List['ModelField'], parent: Optional['ModelReference'] = None, doc: Optional[str] = None, comment: Optional[str] = None, parent_raw: Optional[str] = None, file: Optional[str] = None, line: Optional[int] = None, namespace: Optional[str] = None):
        self.name = name
        self.fields = fields
        self.parent = parent  # ModelReference or None
        self.doc = doc
        self.comment = comment
        self.parent_raw = parent_raw  # Still keep the raw string for debugging
        self.file = file
        self.line = line
        self.namespace = namespace

class ModelNamespace:
    def __init__(self, name: str, messages: List['ModelMessage'], enums: List['ModelEnum'], namespaces: Optional[List['ModelNamespace']] = None,
                 doc: Optional[str] = None, comment: Optional[str] = None, options: Optional[list] = None, compounds: Optional[list] = None, file: Optional[str] = None, line: Optional[int] = None, parent_namespace: Optional[str] = None):
        self.name = name
        self.messages = messages
        self.enums = enums
        self.namespaces = namespaces or []
        self.doc = doc
        self.comment = comment
        self.options = options or []
        self.compounds = compounds or []
        self.file = file
        self.line = line
        self.parent_namespace = parent_namespace

class Model:
    def __init__(self, file: str, namespaces: List['ModelNamespace'], options: Optional[list] = None, compounds: Optional[list] = None, alias_map: Optional[dict] = None, imports: Optional[dict] = None):
        self.file = file
        self.namespaces = namespaces
        self.options = options or []
        self.compounds = compounds or []
        self.alias_map = alias_map or {}
        self.imports = imports or {}  # key: alias or import path, value: Model
        self._qfn_lookup = self._build_qfn_lookup()

    def _build_qfn_lookup(self):
        lookup = {}
        def walk_ns(ns, prefix):
            ns_qfn = '::'.join(prefix + [ns.name]) if ns.name else '::'.join(prefix)
            for msg in getattr(ns, 'messages', []):
                msg_qfn = ns_qfn + '::' + msg.name if ns_qfn else msg.name
                lookup[(msg_qfn, 'message')] = msg
            for enum in getattr(ns, 'enums', []):
                enum_qfn = ns_qfn + '::' + enum.name if ns_qfn else enum.name
                lookup[(enum_qfn, 'enum')] = enum
            for nested in getattr(ns, 'namespaces', []):
                walk_ns(nested, prefix + [ns.name] if ns.name else prefix)
        for ns in getattr(self, 'namespaces', []):
            walk_ns(ns, [])
        return lookup

    def resolve_reference(self, ref: 'ModelReference') -> Optional[Any]:
        """
        Resolve a ModelReference to the actual object in the Model (message, enum, namespace, etc.).
        Returns None if not found. Handles import alias mapping and matches full QFN at any depth.
        """
        if not ref or not ref.qfn:
            return None
        qfn_target = ref.qfn
        kind = ref.kind
        # Debug: print the QFN lookup table and the target QFN
        print(f"[DEBUG] Model.resolve_reference: Looking for QFN '{qfn_target}' of kind '{kind}'")
        print(f"[DEBUG] Model.resolve_reference: QFN lookup keys:")
        for k in self._qfn_lookup.keys():
            print(f"    {k}")
        # Debug: print all aliases in alias_map
        if hasattr(self, 'alias_map') and self.alias_map:
            print(f"[DEBUG] Model.resolve_reference: Aliases in alias_map:")
            for alias, ns in self.alias_map.items():
                print(f"    alias '{alias}' -> '{ns}'")
        # Try direct QFN match
        found = self._qfn_lookup.get((qfn_target, kind))
        if found:
            print(f"[DEBUG] Model.resolve_reference: Found direct QFN match for {qfn_target}")
            return found
        # Try alias mapping: delegate to imported Model if alias is present
        if '::' in qfn_target and hasattr(self, 'alias_map') and self.alias_map:
            alias, rest = qfn_target.split('::', 1)
            if alias in self.imports and alias in self.alias_map:
                real_ns = self.alias_map[alias]
                # If real_ns is empty, just use rest as the QFN
                if real_ns:
                    rewritten_qfn = f"{real_ns}::{rest}"
                else:
                    rewritten_qfn = rest
                print(f"[DEBUG] Model.resolve_reference: Delegating lookup of '{rewritten_qfn}' of kind '{kind}' to import '{alias}' (alias for '{real_ns}')")
                imported_model = self.imports[alias]
                return imported_model.resolve_reference(ModelReference(qfn=rewritten_qfn, kind=kind))
        print(f"[DEBUG] Model.resolve_reference: No match found for {qfn_target}")
        return None