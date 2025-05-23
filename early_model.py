"""
early_model.py
A raw representation of the parsed message model, capturing information directly from the parser (including file, namespace, line number, type, comments, modifiers, etc.). This is the raw model before any manipulations or semantic processing.
"""
from typing import List, Optional, Dict, Any, Tuple

class EarlyField:
    def __init__(self, name: str, type_name: str, file: str, namespace: str, line: int, raw_type: str, options: Optional[Dict[str, Any]] = None, comment: str = "", doc: str = ""):
        self.name: str = name
        self.type_name: str = type_name
        self.file: str = file
        self.namespace: str = namespace
        self.line: int = line
        self.raw_type: str = raw_type  # e.g. 'int', 'string', 'MyEnum', 'array_type', 'map_type', etc.
        self.options_raw: Dict[str, str] = options or {} # Raw options like [default=5]
        self.comment: str = comment # All comments (///, //, /* */)
        self.doc: str = doc # Only doc comments (///)

        # Raw type details for complex types
        self.element_type_raw: Optional[str] = None # For array_type
        self.map_key_type_raw: Optional[str] = None # For map_type
        self.map_value_type_raw: Optional[str] = None # For map_type
        self.compound_base_type_raw: Optional[str] = None # For compound_type
        self.compound_components_raw: List[str] = [] # For compound_type
        self.referenced_name_raw: Optional[str] = None # For ref_type
        self.is_inline_enum: bool = False # For inline enum_type
        self.is_inline_options: bool = False # For inline options_type
        self.inline_values_raw: List[Dict[str, Any]] = [] # Raw values for inline enums/options

        self.modifiers_raw: List[str] = [] # e.g., ['optional', 'repeated']
        self.default_value_raw: Optional[str] = None # Raw string from default_expr

class EarlyEnumValue:
    def __init__(self, name: str, value: int, file: str, namespace: str, line: int, comment: str = "", doc: str = ""):
        self.name = name
        self.value = value
        self.file = file
        self.namespace = namespace # Namespace of the parent enum/message
        self.line = line
        self.comment = comment
        self.doc = doc

class EarlyEnum:
    def __init__(self, name: str, values: List[EarlyEnumValue], file: str, namespace: str, line: int,
                 parent_raw: Optional[str] = None, is_open_raw: bool = False,
                 comment: str = "", doc: str = ""):
        self.name = name
        self.values = values
        self.file = file
        self.namespace = namespace
        self.line = line
        self.comment = comment
        self.doc = doc
        self.parent_raw = parent_raw
        self.is_open_raw = is_open_raw

class EarlyMessage:
    def __init__(self, name: str, fields: List[EarlyField], file: str, namespace: str, line: int, parent_raw: Optional[str] = None, comment: str = "", doc: str = ""):
        self.name = name
        self.fields = fields
        self.file = file
        self.namespace = namespace
        self.line = line
        self.comment = comment
        self.doc = doc
        self.parent_raw = parent_raw

class EarlyNamespace:
   def __init__(self, name: str, messages: List[EarlyMessage], enums: List[EarlyEnum], file: str, line: int,
                 standalone_options: List[Dict[str, Any]] = [], standalone_compounds: List[Dict[str, Any]] = [],
                 comment: str = "", doc: str = "", namespaces: List['EarlyNamespace'] = None, parent_namespace: str = None):
        self.name = name
        self.messages = messages
        self.enums = enums
        self.file = file
        self.line = line
        self.comment = comment
        self.doc = doc
        self.standalone_options = standalone_options
        self.standalone_compounds = standalone_compounds
        self.namespaces = namespaces if namespaces is not None else []
        self.parent_namespace = parent_namespace

class EarlyModel:
  def __init__(
    self,
    namespaces: List[EarlyNamespace],
    enums: List[EarlyEnum],
    messages: List[EarlyMessage], # Top-level messages
    standalone_options: List[Dict[str, Any]], # Top-level options
    standalone_compounds: List[Dict[str, Any]], # Top-level compounds
    imports_raw: List[Tuple[str, Optional[str]]], # List of (path, alias) tuples
    file: str, # The main file being parsed
    imports: dict = None # Mapping of import name to EarlyModel
  ):
    self.namespaces = namespaces
    self.enums = enums
    self.messages = messages
    self.file = file
    self.standalone_options = standalone_options
    self.standalone_compounds = standalone_compounds
    self.imports_raw = imports_raw
    self.imports = imports if imports is not None else {}
