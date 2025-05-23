"""
model_debug.py
Pretty-print and debug dump utilities for MessageWrangler models.
"""
import os
import json
from typing import Any

from early_model import EarlyModel

def pretty_print_model(model: Any, file_path: str = None, out_dir: str = "./generated/model_builder"):
    """
    Pretty-print the model to a file (as JSON) for inspection by AI and user.
    If file_path is not given, use out_dir/model_debug_dump.json.
    """
    if file_path is None:
        file_path = os.path.join(out_dir, "model_debug_dump.json")
    else:
        file_path = os.path.join(out_dir, file_path)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Use a custom encoder to handle non-serializable objects
    def default_encoder(obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, default=default_encoder)
    print(f"[DEBUG] Model pretty-printed to {file_path}")

def _print_early_field(field, indent_level, add_line_func):
    ind = '  ' * indent_level
    # Assuming EarlyField constructor assigns name and type_name to self.name and self.type_name
    # If not, getattr will gracefully return '?'
    field_name = getattr(field, 'name', '?')
    field_type_name = getattr(field, 'type_name', '?')

    details = [
        f"type_name='{field_type_name}'",
        f"type_type='{getattr(field, 'type_type', '?')}'",
        f"raw_type='{getattr(field, 'raw_type', '?')}'"
    ]

    if getattr(field, 'modifiers_raw', None): details.append(f"modifiers={getattr(field, 'modifiers_raw')}")
    if getattr(field, 'default_value_raw', None) is not None: details.append(f"default='{getattr(field, 'default_value_raw')}'")
    if getattr(field, 'options_raw', None): details.append(f"options_raw={getattr(field, 'options_raw')}")

    if getattr(field, 'element_type_raw', None): details.append(f"element_type_raw='{getattr(field, 'element_type_raw')}'")
    if getattr(field, 'map_key_type_raw', None): details.append(f"map_key_type_raw='{getattr(field, 'map_key_type_raw')}'")
    if getattr(field, 'map_value_type_raw', None): details.append(f"map_value_type_raw='{getattr(field, 'map_value_type_raw')}'")
    if getattr(field, 'compound_base_type_raw', None): details.append(f"compound_base_raw='{getattr(field, 'compound_base_type_raw')}'")
    if getattr(field, 'compound_components_raw', None): details.append(f"compound_components_raw={getattr(field, 'compound_components_raw')}")
    if getattr(field, 'referenced_name_raw', None): details.append(f"ref_name_raw='{getattr(field, 'referenced_name_raw')}'")

    if getattr(field, 'is_inline_enum', False): details.append(f"is_inline_enum=True")
    if getattr(field, 'is_inline_options', False): details.append(f"is_inline_options=True")
    if getattr(field, 'inline_values_raw', None): details.append(f"inline_values_raw={getattr(field, 'inline_values_raw')}")

    doc_str = getattr(field, 'doc', '')
    comment_str = getattr(field, 'comment', '')
    if doc_str: details.append(f"doc='{doc_str[:30].replace('\n', ' ')}{'...' if len(doc_str) > 30 else ''}'")
    if comment_str and comment_str != doc_str: details.append(f"comment='{comment_str[:30].replace('\n', ' ')}{'...' if len(comment_str) > 30 else ''}'")

    # Field's own file/line/namespace (namespace is of its container)
    add_line_func(f"{ind}Field: {field_name} ({', '.join(details)}) (file='{getattr(field, 'file', '?')}', line={getattr(field, 'line', '?')}, ns='{getattr(field, 'namespace', '?')}')")

def _print_early_enum_value(val, indent_level, add_line_func):
    ind = '  ' * indent_level
    details = [
        f"value={getattr(val, 'value', '?')}"
    ]
    doc_str = getattr(val, 'doc', '')
    comment_str = getattr(val, 'comment', '')
    if doc_str: details.append(f"doc='{doc_str[:20].replace('\n', ' ')}{'...' if len(doc_str) > 20 else ''}'")
    if comment_str and comment_str != doc_str: details.append(f"comment='{comment_str[:20].replace('\n', ' ')}{'...' if len(comment_str) > 20 else ''}'")
    
    # EnumValue's file/line/namespace (namespace is of its parent enum)
    add_line_func(f"{ind}Value: {getattr(val, 'name', '?')} ({', '.join(details)}) (file='{getattr(val, 'file', '?')}', line={getattr(val, 'line', '?')}, ns='{getattr(val, 'namespace', '?')}')")

def _print_early_enum(enum_obj, indent_level, add_line_func):
    ind = '  ' * indent_level
    details = []
    parent_raw = getattr(enum_obj, 'parent_raw', None)
    if parent_raw:
        details.append(f"parent_raw='{parent_raw}'")
    if getattr(enum_obj, 'is_open_raw', False):
        details.append(f"is_open_raw=True")

    doc_str = getattr(enum_obj, 'doc', '')
    comment_str = getattr(enum_obj, 'comment', '')
    if doc_str:
        details.append(f"doc='{doc_str[:30].replace('\n', ' ')}{'...' if len(doc_str) > 30 else ''}'")
    if comment_str and comment_str != doc_str:
        details.append(f"comment='{comment_str[:30].replace('\n', ' ')}{'...' if len(comment_str) > 30 else ''}'")

    # Print open/closed and inheritance info explicitly
    extra_info = []
    if getattr(enum_obj, 'is_open_raw', False):
        extra_info.append('open')
    else:
        extra_info.append('closed')
    if parent_raw:
        extra_info.append(f'inherits {parent_raw}')
    extra_info_str = f" [{' | '.join(extra_info)}]" if extra_info else ""

    details_str = f" ({', '.join(details)})" if details else ""
    add_line_func(f"{ind}Enum: {getattr(enum_obj, 'name', '?')}{extra_info_str}{details_str} (file='{getattr(enum_obj, 'file', '?')}', line={getattr(enum_obj, 'line', '?')}, ns='{getattr(enum_obj, 'namespace', 'GLOBAL')}')")
    for val in getattr(enum_obj, 'values', []):
        _print_early_enum_value(val, indent_level + 1, add_line_func)

def _print_early_message(msg_obj, indent_level, add_line_func):
    ind = '  ' * indent_level
    details = []
    if getattr(msg_obj, 'parent_raw', None): details.append(f"parent_raw='{getattr(msg_obj, 'parent_raw')}'")

    doc_str = getattr(msg_obj, 'doc', '')
    comment_str = getattr(msg_obj, 'comment', '')
    if doc_str: details.append(f"doc='{doc_str[:30].replace('\n', ' ')}{'...' if len(doc_str) > 30 else ''}'")
    if comment_str and comment_str != doc_str: details.append(f"comment='{comment_str[:30].replace('\n', ' ')}{'...' if len(comment_str) > 30 else ''}'")

    details_str = f" ({', '.join(details)})" if details else ""
    add_line_func(f"{ind}Message: {getattr(msg_obj, 'name', '?')}{details_str} (file='{getattr(msg_obj, 'file', '?')}', line={getattr(msg_obj, 'line', '?')}, ns='{getattr(msg_obj, 'namespace', 'GLOBAL')}')")
    for field in getattr(msg_obj, 'fields', []):
        _print_early_field(field, indent_level + 1, add_line_func)

def _print_options_list(options_list, indent_level, add_line_func, context_label="Options"):
    ind = '  ' * indent_level
    if not options_list: return
    add_line_func(f"{ind}{context_label}:")
    item_ind = '  ' * (indent_level + 1)
    value_ind = '  ' * (indent_level + 2)
    for opts_item in options_list:
        details = [f"doc='{opts_item.get('doc', '')[:20].replace('\n', ' ')}{'...' if len(opts_item.get('doc', '')) > 20 else ''}'"] if opts_item.get('doc') else []
        if opts_item.get('comment') and opts_item.get('comment') != opts_item.get('doc'):
            details.append(f"comment='{opts_item.get('comment', '')[:20].replace('\n', ' ')}{'...' if len(opts_item.get('comment', '')) > 20 else ''}'")
        details_str = f" ({', '.join(details)})" if details else ""
        add_line_func(f"{item_ind}OptionsDef: {opts_item.get('name', '?')}{details_str} (file='{opts_item.get('file', '?')}', line={opts_item.get('line', '?')}, ns='{opts_item.get('namespace', 'GLOBAL')}')")
        for val_raw in opts_item.get('values_raw', []):
            val_details = [f"doc='{val_raw.get('doc', '')[:15].replace('\n', ' ')}{'...' if len(val_raw.get('doc', '')) > 15 else ''}'"] if val_raw.get('doc') else []
            if val_raw.get('comment') and val_raw.get('comment') != val_raw.get('doc'):
                val_details.append(f"comment='{val_raw.get('comment', '')[:15].replace('\n', ' ')}{'...' if len(val_raw.get('comment', '')) > 15 else ''}'")
            val_details_str = f" ({', '.join(val_details)})" if val_details else ""
            add_line_func(f"{value_ind}Value: {val_raw.get('name', '?')} = {val_raw.get('value', 'AUTO')}{val_details_str}")

def _print_compounds_list(compounds_list, indent_level, add_line_func, context_label="Compounds"):
    ind = '  ' * indent_level
    if not compounds_list: return
    add_line_func(f"{ind}{context_label}:")
    item_ind = '  ' * (indent_level + 1)
    for comp_item in compounds_list:
        details = [f"base_type='{comp_item.get('base_type_raw', '?')}'", f"components={comp_item.get('components_raw', [])}"]
        if comp_item.get('doc'): details.append(f"doc='{comp_item.get('doc', '')[:20].replace('\n', ' ')}{'...' if len(comp_item.get('doc', '')) > 20 else ''}'")
        if comp_item.get('comment') and comp_item.get('comment') != comp_item.get('doc'):
            details.append(f"comment='{comp_item.get('comment', '')[:20].replace('\n', ' ')}{'...' if len(comp_item.get('comment', '')) > 20 else ''}'")
        add_line_func(f"{item_ind}CompoundDef: {comp_item.get('name', '?')} ({', '.join(details)}) (file='{comp_item.get('file', '?')}', line={comp_item.get('line', '?')}, ns='{comp_item.get('namespace', 'GLOBAL')}')")

def debug_print_early_model(early_model: EarlyModel, indent=0, file_path=None, out_dir="./generated/model_builder"):
  """
  Print a language-neutral, hierarchical view of an EarlyModel (from early_model.py).
  If file_path is given, write output to that file (in out_dir if relative), else print to stdout.
  """
  lines = []
  def add_line(s):
    lines.append(s)

  ind = '  ' * indent
  add_line(f"{ind}EarlyModel (Main File: {getattr(early_model, 'file', '?')})")
  imports_raw = getattr(early_model, 'imports_raw', [])
  if imports_raw:
    add_line(f"{ind}  Imports Raw: {imports_raw}")

  imports = getattr(early_model, 'imports', None)
  if imports:
    add_line(f"{ind}  Imports (resolved):")
    for k, v in imports.items():
      v_file = getattr(v, 'file', '?')
      v_namespaces = getattr(v, 'namespaces', [])
      ns_names = [getattr(ns, 'name', '?') for ns in v_namespaces]
      add_line(f"{ind}    {k}: file='{v_file}', namespaces={ns_names}")

  _print_options_list(getattr(early_model, 'options', []), indent + 1, add_line, "Top-Level Options")
  _print_compounds_list(getattr(early_model, 'compounds', []), indent + 1, add_line, "Top-Level Compounds")

  top_level_enums = getattr(early_model, 'enums', [])
  if top_level_enums:
    add_line(f"{ind}  Top-Level Enums:")
    for enum_obj in top_level_enums:
      _print_early_enum(enum_obj, indent + 2, add_line)

  top_level_messages = getattr(early_model, 'messages', [])
  if top_level_messages:
    add_line(f"{ind}  Top-Level Messages:")
    for msg_obj in top_level_messages:
      _print_early_message(msg_obj, indent + 2, add_line)


  def _print_namespace(ns_obj, indent_level):
    ns_ind = '  ' * indent_level
    ns_details = []
    doc_str = getattr(ns_obj, 'doc', '')
    comment_str = getattr(ns_obj, 'comment', '')
    if doc_str:
      ns_details.append(f"doc='{doc_str[:30].replace('\n', ' ')}{'...' if len(doc_str) > 30 else ''}'")
    if comment_str and comment_str != doc_str:
      ns_details.append(f"comment='{comment_str[:30].replace('\n', ' ')}{'...' if len(comment_str) > 30 else ''}'")
    parent_ns = getattr(ns_obj, 'parent_namespace', None)
    ns_details_str = f" ({', '.join(ns_details)})" if ns_details else ""
    add_line(f"{ns_ind}Namespace: {getattr(ns_obj, 'name', '?')}{ns_details_str} (file='{getattr(ns_obj, 'file', '?')}', line={getattr(ns_obj, 'line', '?')}, parent_namespace={repr(parent_ns)})")

    _print_options_list(getattr(ns_obj, 'standalone_options', []), indent_level + 1, add_line)
    _print_compounds_list(getattr(ns_obj, 'standalone_compounds', []), indent_level + 1, add_line)

    ns_enums = getattr(ns_obj, 'enums', [])
    add_line(f"{ns_ind}    [DEBUG] enums count: {len(ns_enums)}")
    if ns_enums:
      add_line(f"{ns_ind}  Enums (in namespace):")
      for enum_obj in ns_enums:
        _print_early_enum(enum_obj, indent_level + 2, add_line)

    ns_messages = getattr(ns_obj, 'messages', [])
    add_line(f"{ns_ind}    [DEBUG] messages count: {len(ns_messages)}")
    if ns_messages:
      add_line(f"{ns_ind}  Messages (in namespace):")
      for msg_obj in ns_messages:
        _print_early_message(msg_obj, indent_level + 2, add_line)

    # Recursively print nested namespaces if present
    nested_namespaces = getattr(ns_obj, 'namespaces', [])
    if nested_namespaces:
      add_line(f"{ns_ind}  Nested Namespaces:")
      for nested_ns in nested_namespaces:
        _print_namespace(nested_ns, indent_level + 2)

  namespaces = getattr(early_model, 'namespaces', [])
  if namespaces:
    add_line(f"{ind}  Namespaces:")
    for ns_obj in namespaces:
      _print_namespace(ns_obj, indent + 1)

  output = "\n".join(lines)
  if file_path is not None:
    if not os.path.isabs(file_path):
      file_path = os.path.join(out_dir, file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
      f.write(output)
    print(f"[DEBUG] EarlyModel pretty-printed to {file_path}")
  else:
    print(output)

def debug_print_model(model, indent=0, file_path=None, out_dir="./generated/model_builder"):
    """
    Pretty-print a Model (concrete, generator-ready) for inspection.
    """
    lines = []
    def add_line(s):
        lines.append(s)

    ind = '  ' * indent
    add_line(f"{ind}Model (Main File: {getattr(model, 'file', '?')})")

    # Print imports if present
    imports = getattr(model, 'imports', None)
    if imports:
        add_line(f"{ind}  Imports (resolved):")
        for k, v in imports.items():
            v_file = getattr(v, 'file', '?')
            v_namespaces = getattr(v, 'namespaces', [])
            ns_names = [getattr(ns, 'name', '?') for ns in v_namespaces]
            add_line(f"{ind}    {k}: file='{v_file}', namespaces={ns_names}")

    # Print top-level options/compounds
    options = getattr(model, 'options', [])
    if options:
        add_line(f"{ind}  Top-Level Options:")
        for opt in options:
            add_line(f"{ind}    {opt}")
    compounds = getattr(model, 'compounds', [])
    if compounds:
        add_line(f"{ind}  Top-Level Compounds:")
        for comp in compounds:
            add_line(f"{ind}    {comp}")

    # Print top-level enums/messages if present
    top_level_enums = getattr(model, 'enums', [])
    if top_level_enums:
        add_line(f"{ind}  Top-Level Enums:")
        for enum_obj in top_level_enums:
            add_line(f"{ind}    Enum: {getattr(enum_obj, 'name', '?')}")
    top_level_messages = getattr(model, 'messages', [])
    if top_level_messages:
        add_line(f"{ind}  Top-Level Messages:")
        for msg_obj in top_level_messages:
            add_line(f"{ind}    Message: {getattr(msg_obj, 'name', '?')}")

    def print_enum(enum, level):
        enum_ind = '  ' * level
        details = []
        if enum.parent_raw:
            details.append(f"parent_raw='{enum.parent_raw}'")
        details.append(f"is_open={enum.is_open}")
        if enum.doc:
            details.append(f"doc='{enum.doc[:30].replace('\n', ' ')}{'...' if len(enum.doc) > 30 else ''}'")
        if enum.comment:
            details.append(f"comment='{enum.comment[:30].replace('\n', ' ')}{'...' if len(enum.comment) > 30 else ''}'")
        add_line(f"{enum_ind}Enum: {enum.name} ({', '.join(details)}) (file='{enum.file}', line={enum.line}, ns='{enum.namespace}')")
        for val in enum.values:
            val_details = [f"value={val.value}"]
            if val.doc:
                val_details.append(f"doc='{val.doc[:20].replace('\n', ' ')}{'...' if len(val.doc) > 20 else ''}'")
            if val.comment:
                val_details.append(f"comment='{val.comment[:20].replace('\n', ' ')}{'...' if len(val.comment) > 20 else ''}'")
            add_line(f"{enum_ind}  Value: {val.name} ({', '.join(val_details)}) (file='{val.file}', line={val.line}, ns='{val.namespace}')")

    def print_message(msg, level):
        msg_ind = '  ' * level
        details = []
        # Print parent reference (ModelReference) if present
        if getattr(msg, 'parent', None):
            details.append(f"parent={repr(msg.parent)}")
        elif getattr(msg, 'parent_raw', None):
            details.append(f"parent_raw='{msg.parent_raw}'")
        if msg.doc:
            details.append(f"doc='{msg.doc[:30].replace('\n', ' ')}{'...' if len(msg.doc) > 30 else ''}'")
        if msg.comment:
            details.append(f"comment='{msg.comment[:30].replace('\n', ' ')}{'...' if len(msg.comment) > 30 else ''}'")
        add_line(f"{msg_ind}Message: {msg.name}{' (' + ', '.join(details) + ')' if details else ''} (file='{msg.file}', line={msg.line}, ns='{msg.namespace}')")
        for field in msg.fields:
            field_details = []
            for i, ftype in enumerate(field.field_types):
                ref = field.type_refs[i] if i < len(field.type_refs) else None
                tname = field.type_names[i] if i < len(field.type_names) else None
                s = f"type[{i}]={ftype.name}"
                if tname:
                    s += f" (name='{tname}')"
                if ref is not None:
                    s += f" (ref={getattr(ref, 'name', ref)})"
                field_details.append(s)
            if field.modifiers:
                field_details.append(f"modifiers={[m.name for m in field.modifiers]}")
            if field.default is not None:
                field_details.append(f"default={field.default}")
            if field.inline_values:
                field_details.append(f"inline_values=[{', '.join(f'{v.name}={v.value}' for v in field.inline_values)}]")
            if field.doc:
                field_details.append(f"doc='{field.doc[:30].replace('\n', ' ')}{'...' if len(field.doc) > 30 else ''}'")
            if field.comment:
                field_details.append(f"comment='{field.comment[:30].replace('\n', ' ')}{'...' if len(field.comment) > 30 else ''}'")
            add_line(f"{msg_ind}  Field: {field.name} ({', '.join(field_details)}) (file='{field.file}', line={field.line}, ns='{field.namespace}')")

    def print_namespace(ns, level):
        ns_ind = '  ' * level
        ns_details = []
        if ns.doc:
            ns_details.append(f"doc='{ns.doc[:30].replace('\n', ' ')}{'...' if len(ns.doc) > 30 else ''}'")
        if ns.comment:
            ns_details.append(f"comment='{ns.comment[:30].replace('\n', ' ')}{'...' if len(ns.comment) > 30 else ''}'")
        ns_details_str = f" ({', '.join(ns_details)})" if ns_details else ""
        add_line(f"{ns_ind}Namespace: {ns.name}{ns_details_str} (file='{ns.file}', line={ns.line}, parent_namespace={repr(ns.parent_namespace)})")

        if ns.options:
            add_line(f"{ns_ind}  Options:")
            for opt in ns.options:
                add_line(f"{ns_ind}    {opt}")
        if ns.compounds:
            add_line(f"{ns_ind}  Compounds:")
            for comp in ns.compounds:
                add_line(f"{ns_ind}    {comp}")

        if ns.enums:
            add_line(f"{ns_ind}  Enums:")
            for enum in ns.enums:
                print_enum(enum, level + 2)
        if ns.messages:
            add_line(f"{ns_ind}  Messages:")
            for msg in ns.messages:
                print_message(msg, level + 2)
        if ns.namespaces:
            add_line(f"{ns_ind}  Nested Namespaces:")
            for n in ns.namespaces:
                print_namespace(n, level + 1)

    namespaces = getattr(model, 'namespaces', [])
    if namespaces:
        add_line(f"{ind}  Namespaces:")
        for ns in namespaces:
            print_namespace(ns, indent + 1)

    output = "\n".join(lines)
    if file_path is not None:
        if not os.path.isabs(file_path):
            file_path = os.path.join(out_dir, file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[DEBUG] Model pretty-printed to {file_path}")
    else:
        print(output)
