# def_file_loader.py
# Handles reading .def files and resolving imports recursively for MessageWrangler.
import os
import re
from message_model import MessageModel
from lark_parser import parse_message_dsl
from lark import Token, Tree
from message_model import MessageModel, Enum
from model_debug import debug_print_early_model, pretty_print_model
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyField, EarlyEnum, EarlyEnumValue

# Convenience function to load a .def file and return an EarlyModel

def load_def_file(def_file_path: str):
    with open(def_file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    file_namespace = os.path.splitext(os.path.basename(def_file_path))[0]
    tree = parse_message_dsl(text)
    return _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file_path)

def _build_early_model_from_lark_tree(tree, current_processing_file_namespace: str, source_file: str = None):

    """Build an EarlyModel from a Lark parse tree, capturing raw information."""

    file = source_file or "?"

    def _extract_comments(node, parent_children=None, node_index=None):
        """Extract doc comments (///) and other comments (//, /* */) associated with a node."""
        doc_comments = []
        other_comments = []

        # Look for preceding comments in parent_children
        if parent_children is not None and node_index is not None:
            i = node_index - 1
            while i >= 0:
                prev = parent_children[i]
                if isinstance(prev, Tree) and prev.data == "comment":
                    for c in prev.children:
                        if isinstance(c, Token):
                            if c.type == "DOC_COMMENT":
                                doc_comments.append(str(c).strip())
                            elif c.type in ("LOCAL_COMMENT", "C_COMMENT"):
                                other_comments.append(str(c).strip())
                    # Stop looking backwards after finding the first non-comment item
                    # or a comment block that isn't directly attached (simplification)
                    break
                # If the previous item is not a comment, stop looking backwards
                if not (isinstance(prev, Tree) and prev.data == "comment"):
                     break
                i -= 1

        doc = "\n".join(doc_comments)
        comment = "\n".join(doc_comments + other_comments) # 'comment' includes all types
        return doc, comment

    def get_line(node):
        return getattr(node, 'line', None) or getattr(node, 'line_no', None) or -1

    def parse_enum(enum_node, namespace, file, parent_children=None, node_index=None):
        name = "?"
        line = get_line(enum_node)
        values = []
        parent_raw = None
        is_open_raw = False

        # Grammar: enum_def: DOC_COMMENT* enum_kind NAME inheritance? "{" enum_value_or_comment_list "}"
        # Extract name, kind, parent, and values by iterating through children
        name_found = False
        # Look for enum_kind node and check its token child for 'enum' or 'open_enum'
        for child_node in enum_node.children:
            if isinstance(child_node, Tree) and child_node.data == 'enum_kind':
                if child_node.children and isinstance(child_node.children[0], Token):
                    kind_val = str(child_node.children[0]).strip()
                    is_open_raw = (kind_val == 'open_enum')
                    print(f"[DEBUG] parse_enum: name={name} enum_kind token: {kind_val}, is_open_raw: {is_open_raw}")
                else:
                    print(f"[DEBUG] parse_enum: name={name} enum_kind node: {child_node} (no token child)")
                break

        for child_node in enum_node.children:
            if not name_found and isinstance(child_node, Token) and child_node.type == 'NAME':
                name = str(child_node)
                name_found = True
            elif isinstance(child_node, Tree) and child_node.data == 'inheritance':
                # Handle both qualified and unqualified parent enum names
                if child_node.children:
                    first_child = child_node.children[0]
                    if isinstance(first_child, Tree) and first_child.data == 'qualified_name_with_dot':
                        parent_raw = _extract_raw_type_info(first_child).get('referenced_name_raw')
                        print(f"[DEBUG] parse_enum: name={name} parent_raw={parent_raw}")
                    elif isinstance(first_child, Token) and first_child.type == 'NAME':
                        parent_raw = str(first_child)
                        print(f"[DEBUG] parse_enum: name={name} parent_raw={parent_raw} (unqualified)")
            elif isinstance(child_node, Tree) and child_node.data in ('enum_value_or_comment_list', 'enum_value_or_comment_seq'):
                # Iterate for 'enum_value' subtrees to extract values
                for v_node in (n for n in child_node.iter_subtrees() if getattr(n, 'data', None) == 'enum_value'):
                    vname, vval = None, None
                    vline = get_line(v_node)
                    v_doc_strings = []
                    # DOC_COMMENT* are children of enum_value node as per grammar: enum_value: DOC_COMMENT* NAME ...
                    for v_child_token in v_node.children:
                        if isinstance(v_child_token, Token) and v_child_token.type == 'DOC_COMMENT':
                            v_doc_strings.append(str(v_child_token).strip())
                        elif isinstance(v_child_token, Token) and v_child_token.type == 'NAME':
                            vname = str(v_child_token)
                        elif isinstance(v_child_token, Token) and v_child_token.type == 'NUMBER':
                            vval = int(str(v_child_token))
                    vdoc = "\n".join(v_doc_strings)
                    vcomment = vdoc
                    if vname is not None:
                        values.append(EarlyEnumValue(vname, vval if vval is not None else 0, file, namespace, vline, comment=vcomment, doc=vdoc))
            elif isinstance(child_node, Tree) and child_node.data == 'enum_value': # Direct enum_value child (less common if list is used)
                v_node = child_node
                vname, vval = None, None
                vline = get_line(v_node)
                v_doc_strings = []
                for v_child_token in v_node.children:
                    if isinstance(v_child_token, Token) and v_child_token.type == 'DOC_COMMENT':
                        v_doc_strings.append(str(v_child_token).strip())
                    elif isinstance(v_child_token, Token) and v_child_token.type == 'NAME':
                        vname = str(v_child_token)
                    elif isinstance(v_child_token, Token) and v_child_token.type == 'NUMBER':
                        vval = int(str(v_child_token))
                vdoc = "\n".join(v_doc_strings)
                vcomment = vdoc # Simplification for EarlyModel
                if vname is not None:
                    values.append(EarlyEnumValue(vname, vval if vval is not None else 0, file, namespace, vline, comment=vcomment, doc=vdoc))

        doc, comment = _extract_comments(enum_node, parent_children, node_index) # For the enum_def itself

        return EarlyEnum(name, values, file, namespace, line, parent_raw=parent_raw, is_open_raw=is_open_raw, comment=comment, doc=doc)

    def _extract_raw_type_info(type_node):
        """Extract raw type details from a type_def subtree."""
        info = {
            'type_name': getattr(type_node, 'data', '?'),
            'raw_type': '?',
            'element_type_raw': None,
            'map_key_type_raw': None,
            'map_value_type_raw': None,
            'compound_base_type_raw': None,
            'compound_components_raw': [],
            'referenced_name_raw': None,
            'is_inline_enum': False,
            'is_inline_options': False,
            'inline_values_raw': []
        }

        if isinstance(type_node, Token):
            info['raw_type'] = str(type_node)
        elif isinstance(type_node, Tree):
            info['type_name'] = type_node.data
            if type_node.data == 'array_type':
                if type_node.children:
                    info['element_type_raw'] = _extract_raw_type_info(type_node.children[0]).get('raw_type')
            elif type_node.data == 'map_type':
                # Map type: Map < key , value >
                # Children: [map_key_type, map_value_type]
                print(f"[DEBUG] _extract_raw_type_info: map_type children: {[str(child) + ' (' + getattr(child, 'data', str(type(child))) + ')' for child in type_node.children]}")
                if len(type_node.children) > 1:
                    key_node = type_node.children[0]
                    value_node = type_node.children[1]
                    # Descend into map_key_type/map_value_type wrappers if present
                    if hasattr(key_node, 'data') and key_node.data == 'map_key_type' and key_node.children:
                        key_node = key_node.children[0]
                    if hasattr(value_node, 'data') and value_node.data == 'map_value_type' and value_node.children:
                        value_node = value_node.children[0]
                    # Unwrap type_def for value_node if present
                    if hasattr(value_node, 'data') and value_node.data == 'type_def' and value_node.children:
                        value_node = value_node.children[0]
                    key_info = _extract_raw_type_info(key_node)
                    value_info = _extract_raw_type_info(value_node)
                    print(f"[DEBUG] _extract_raw_type_info: key_info={key_info}, value_info={value_info}")
                    info['map_key_type_raw'] = key_info.get('raw_type') or key_info.get('type_name') or '?'
                    info['map_value_type_raw'] = value_info.get('raw_type') or value_info.get('type_name') or '?'
            elif type_node.data == 'compound_type':
                if type_node.children:
                    base_type_node = type_node.children[0]
                    if isinstance(base_type_node, Tree) and base_type_node.data == 'basic_type' and base_type_node.children:
                        info['compound_base_type_raw'] = str(base_type_node.children[0])
                        info['raw_type'] = str(base_type_node.children[0])
                    elif isinstance(base_type_node, Token) and base_type_node.type == 'NAME':
                        info['compound_base_type_raw'] = str(base_type_node)
                        info['raw_type'] = str(base_type_node)
                    else:
                        info['compound_base_type_raw'] = 'UNKNOWN'

                    for child in type_node.children:
                        if isinstance(child, Tree) and child.data == 'compound_component_seq':
                            for comp_item in (n for n in child.iter_subtrees() if getattr(n, 'data', None) == 'compound_component_item'):
                                for name_token in comp_item.children:
                                    if isinstance(name_token, Token) and name_token.type == 'NAME':
                                        info['compound_components_raw'].append(str(name_token))
                            break

            elif type_node.data == 'ref_type':
                # Handle qualified_name_with_dot (usual case)
                if type_node.children and isinstance(type_node.children[0], Tree) and type_node.children[0].data == 'qualified_name_with_dot':
                    names = []
                    for c in type_node.children[0].children:
                        if isinstance(c, Token) and c.type == 'NAME':
                            names.append(str(c))
                    # Patch: handle single-name qualified_name_with_dot as well
                    if names:
                        val = '::'.join(names)
                        info['referenced_name_raw'] = val
                        info['raw_type'] = val
                # Handle direct Token (for basic types parsed as ref_type)
                elif type_node.children and isinstance(type_node.children[0], Token):
                    val = str(type_node.children[0])
                    info['referenced_name_raw'] = val
                    info['raw_type'] = val
            # Patch: handle qualified_name_with_dot anywhere (for enum inheritance, etc.)
            elif type_node.data == 'qualified_name_with_dot':
                names = []
                for c in type_node.children:
                    if isinstance(c, Token) and c.type == 'NAME':
                        names.append(str(c))
                if names:
                    val = '::'.join(names)
                    info['referenced_name_raw'] = val
                    info['raw_type'] = val
            elif type_node.data == 'basic_type':
                if type_node.children and isinstance(type_node.children[0], Token):
                    info['raw_type'] = str(type_node.children[0])
            elif type_node.data == 'enum_type':
                info['is_inline_enum'] = True
                for child in type_node.children:
                    if isinstance(child, Tree) and child.data == 'enum_value_or_comment_list':
                        info['inline_values_raw'] = _parse_value_list_raw(child, kind='enum')
                        break
            elif type_node.data == 'options_type':
                info['is_inline_options'] = True
                for child in type_node.children:
                    if isinstance(child, Tree) and child.data == 'option_value_or_comment_list':
                        info['inline_values_raw'] = _parse_value_list_raw(child, kind='option')
                        break
            else:
                for child in type_node.children:
                    if isinstance(child, Token) and child.type == 'NAME':
                        info['raw_type'] = str(child)
                        break

        return info

    def _parse_value_list_raw(values_tree, kind):
        """Generic raw value list parser for enums/options. Returns list of raw value dicts."""
        raw_values = []
        if values_tree is None:
            return raw_values

        value_node_name = 'enum_value' if kind == 'enum' else 'option_value'

        # Manual filter for Lark compatibility: iterate all subtrees and select those with .data == value_node_name
        for value_node in values_tree.iter_subtrees():
            if not (isinstance(value_node, Tree) and getattr(value_node, 'data', None) == value_node_name):
                continue
            vname = None
            vval = None
            # Grammar for enum_value/option_value: DOC_COMMENT* NAME ...
            # DOC_COMMENT tokens are direct children of value_node.
            doc_strings = []
            for child_token in value_node.children:
                if isinstance(child_token, Token) and child_token.type == 'DOC_COMMENT':
                    doc_strings.append(str(child_token).strip())
                elif isinstance(child_token, Token) and child_token.type == 'NAME':
                    vname = str(child_token)
                elif isinstance(child_token, Token) and child_token.type == 'NUMBER':
                    vval = int(str(child_token))
            vdoc_str = "\n".join(doc_strings)
            # For EarlyModel's raw values, 'comment' can be the same as 'doc'.
            # More sophisticated comment association (like preceding general comments)
            # is harder with iter_subtrees without parent context.
            vcomment_str = vdoc_str

            if vname is not None:
                raw_values.append({
                    'name': vname,
                    'value': vval, # Can be None if no explicit value
                    'doc': vdoc_str,
                    'comment': vcomment_str
                })
        return raw_values

    def parse_field(field_node, namespace, file, parent_children=None, node_index=None):
        name = "?"
        line = get_line(field_node)
        doc, comment = _extract_comments(field_node, parent_children, node_index)

        modifiers_raw = []
        type_def_node = None
        default_value_raw = None
        options_raw = {}

        for child in field_node.children:
            if isinstance(child, Tree) and child.data == 'field_modifier':
                for mod_token in child.children:
                    if isinstance(mod_token, Token):
                        modifiers_raw.append(str(mod_token))
            elif isinstance(child, Token) and child.type == 'NAME':
                name = str(child)
            elif isinstance(child, Tree) and child.data == 'type_def':
                type_def_node = child
            elif isinstance(child, Tree) and child.data == 'field_default':
                if child.children:
                    # default_expr is a regex token or a Token/Tree
                    val = child.children[0]
                    # If it's a Token, get its value
                    if isinstance(val, Token):
                        # Remove quotes for strings
                        if val.type == 'STRING':
                            default_value_raw = val.value[1:-1]
                        else:
                            default_value_raw = val.value.strip()
                    elif isinstance(val, Tree):
                        # If it's a Tree, try to extract the first token
                        if val.children:
                            tok = val.children[0]
                            if isinstance(tok, Token):
                                if tok.type == 'STRING':
                                    default_value_raw = tok.value[1:-1]
                                else:
                                    default_value_raw = tok.value.strip()
                            else:
                                default_value_raw = str(tok).strip()
                        else:
                            default_value_raw = str(val).strip()
                    else:
                        default_value_raw = str(val).strip()
            elif isinstance(child, Tree) and child.data == 'field_options':
                 # field_options: [ option_assignments ]
                 for opt_assign_node in child.iter_subtrees('option_assignment'):
                     opt_name = None
                     opt_value = None
                     for opt_part in opt_assign_node.children: # Corrected variable name
                         if isinstance(opt_part, Token) and opt_part.type == 'NAME':
                             opt_name = str(opt_part)
                         elif isinstance(opt_part, Token) and opt_part.type in ('NUMBER', 'STRING'): # Handle simple tokens
                             opt_value = str(opt_part)
                         elif isinstance(opt_part, Tree) and opt_part.data == 'default_expr': # Handle default_expr tree
                             if opt_part.children:
                                 opt_value = str(opt_part.children[0]).strip()
                     if opt_name:
                         options_raw[opt_name] = opt_value

        # Extract raw type info from type_def
        type_info = _extract_raw_type_info(type_def_node.children[0] if type_def_node and type_def_node.children else None)


        # Patch: type_name is the type string (prefer referenced_name_raw, then raw_type, then type_type)
        type_name = type_info.get('referenced_name_raw') or type_info.get('raw_type') or type_info.get('type_name', '?')
        # If type_name is a primitive, set type_type to 'primitive', else use the current logic
        primitives = {'int', 'float', 'string', 'bool', 'double'}
        if type_name in primitives:
            type_type = 'primitive'
        else:
            type_type = type_info.get('type_name', '?')

        field = EarlyField(
            name=name,
            type_name=type_name,
            file=file,
            namespace=namespace,
            line=line,
            raw_type=type_info.get('raw_type', '?'),
            options=options_raw,
            comment=comment,
            doc=doc
        )
        field.type_type = type_type
        field.modifiers_raw = modifiers_raw
        field.default_value_raw = default_value_raw
        field.element_type_raw = type_info.get('element_type_raw')
        field.map_key_type_raw = type_info.get('map_key_type_raw')
        field.map_value_type_raw = type_info.get('map_value_type_raw')
        field.compound_base_type_raw = type_info.get('compound_base_type_raw')
        field.compound_components_raw = type_info.get('compound_components_raw', [])
        field.referenced_name_raw = type_info.get('referenced_name_raw')
        field.is_inline_enum = type_info.get('is_inline_enum', False)
        field.is_inline_options = type_info.get('is_inline_options', False)
        field.inline_values_raw = type_info.get('inline_values_raw', [])

        return field

    def parse_message(msg_node, namespace, file, parent_children=None, node_index=None):
        name = "?"
        line = get_line(msg_node)
        doc, comment = _extract_comments(msg_node, parent_children, node_index)
        fields = []
        parent_raw = None

        for child in msg_node.children:
            if isinstance(child, Token) and child.type == 'NAME':
                name = str(child)
            elif isinstance(child, Tree) and child.data == 'inheritance':
                if child.children and isinstance(child.children[0], Tree) and child.children[0].data == 'qualified_name_with_dot':
                    parent_raw = _extract_raw_type_info(child.children[0]).get('referenced_name_raw')
            elif isinstance(child, Tree) and child.data == 'message_body':
                for f_idx, f in enumerate(child.children):
                    if isinstance(f, Tree) and f.data == 'field':
                        fields.append(parse_field(f, namespace, file, child.children, f_idx))
            elif isinstance(child, Tree) and child.data == 'field': # Handle fields directly under message
                 fields.append(parse_field(child, namespace, file, msg_node.children, msg_node.children.index(child)))

        return EarlyMessage(name, fields, file, namespace, line, parent_raw=parent_raw, comment=comment, doc=doc)

    def parse_namespace(ns_node, file, parent_children=None, node_index=None):
        name = "?"
        line = get_line(ns_node)
        doc, comment = _extract_comments(ns_node, parent_children, node_index)
        messages, enums, options, compounds, namespaces = [], [], [], [], []

        if ns_node.children:
             name_token = ns_node.children[0]
             if isinstance(name_token, Token) and name_token.type == 'NAME':
                 name = str(name_token)

        # Iterate through items within the namespace body
        # Assuming grammar: "namespace" NAME "{" item* "}"
        # Items are children after NAME and '{' up to '}'
        # The loop should start from index 1 (after NAME)
        print(f"[DEBUG] parse_namespace: ns='{name}' children after NAME: {[getattr(c, 'data', type(c)) for c in ns_node.children[1:]]}")
        def flatten_namespace_items(nodes):
            result = []
            for n in nodes:
                if not isinstance(n, Tree):
                    continue
                if hasattr(n, 'data') and n.data in ('block', 'item'):
                    result.extend(flatten_namespace_items(n.children))
                else:
                    result.append(n)
            return result

        flat_nodes = flatten_namespace_items(ns_node.children[1:])
        for child_idx, subnode in enumerate(flat_nodes):
            if not isinstance(subnode, Tree):
                continue
            print(f"[DEBUG] parse_namespace: ns='{name}' subnode data: {getattr(subnode, 'data', type(subnode))}")
            if subnode.data == 'namespace':
                namespaces.append(parse_namespace(subnode, file, flat_nodes, child_idx + 1))
            elif subnode.data == 'message':
                messages.append(parse_message(subnode, name, file, ns_node.children, child_idx + 1))
            elif subnode.data == 'enum_def':
                enums.append(parse_enum(subnode, name, file, ns_node.children, child_idx + 1))
            elif subnode.data == 'options_def':
                options.append(_parse_options_def(subnode, name, file, ns_node.children, child_idx + 1))
            elif subnode.data == 'compound_def':
                compounds.append(_parse_compound_def(subnode, name, file, ns_node.children, child_idx + 1))
            # Ignore 'comment' and 'import_stmt' at this level if they appear (grammar might prevent imports)

        # Determine parent namespace name (None if root)
        parent_ns = None
        if parent_children is not None and node_index is not None:
            # Find the parent namespace node if any
            for i in range(node_index - 1, -1, -1):
                prev = parent_children[i]
                if isinstance(prev, Tree) and getattr(prev, 'data', None) == 'namespace':
                    if prev.children and isinstance(prev.children[0], Token) and prev.children[0].type == 'NAME':
                        parent_ns = str(prev.children[0])
                    break

        return EarlyNamespace(name, messages, enums, file, line, options=options, compounds=compounds, comment=comment, doc=doc, namespaces=namespaces, parent_namespace=parent_ns)

    def _parse_options_def(options_node, namespace, file, parent_children=None, node_index=None):
        name = "?"
        line = get_line(options_node)
        doc, comment = _extract_comments(options_node, parent_children, node_index)
        values_tree = None

        for child in options_node.children:
            if isinstance(child, Token) and child.type == 'NAME':
                name = str(child)
            elif isinstance(child, Tree) and child.data == 'option_value_or_comment_list':
                values_tree = child

        values_raw = _parse_value_list_raw(values_tree, kind='option')

        return {
            'name': name,
            'namespace': namespace,
            'file': file,
            'line': line,
            'doc': doc,
            'comment': comment,
            'values_raw': values_raw
        }

    def _parse_compound_def(compound_node, namespace, file, parent_children=None, node_index=None):
        name = "?"
        line = get_line(compound_node)
        doc, comment = _extract_comments(compound_node, parent_children, node_index)
        base_type_raw = None
        components_raw = []

        for child in compound_node.children:
            if isinstance(child, Tree) and child.data == 'basic_type':
                if child.children and isinstance(child.children[0], Token):
                    base_type_raw = str(child.children[0])
            elif isinstance(child, Token) and child.type == 'NAME':
                # The first NAME after basic_type is the compound definition name
                if name == "?":
                    name = str(child)
                else: # Subsequent NAME tokens are components
                    components_raw.append(str(child))
            elif isinstance(child, Tree) and child.data == 'compound_component_seq':
                 # This rule seems to be for inline compounds, but grammar uses it for standalone too
                 for comp_item in child.iter_subtrees('compound_component_item'):
                     for name_token in comp_item.children:
                         if isinstance(name_token, Token) and name_token.type == 'NAME':
                             components_raw.append(str(name_token))

        return {
            'name': name,
            'namespace': namespace,
            'file': file,
            'line': line,
            'doc': doc,
            'comment': comment,
            'base_type_raw': base_type_raw,
            'components_raw': components_raw
        }

    namespaces = []
    free_messages = [] # Top-level messages
    free_enums = [] # Top-level enums
    options = [] # Top-level options_def
    compounds = [] # Top-level compound_def
    imports_raw = [] # List of (path, alias) tuples

    # Top-level: scan for namespaces, messages, enums, options_def, compound_def, import_stmt
    for idx, node in enumerate(tree.children):
      if not isinstance(node, Tree):
          continue
      # Flat logic: if this is an 'item', process its children as if they were top-level
      nodes_to_check = [node]
      if node.data == 'item':
          nodes_to_check = node.children
      for subnode in nodes_to_check:
          if not isinstance(subnode, Tree):
              continue
          if subnode.data == 'namespace':
              namespaces.append(parse_namespace(subnode, file, tree.children, idx))
          elif subnode.data == 'message':
              ns_name = current_processing_file_namespace
              free_messages.append(parse_message(subnode, ns_name, file, tree.children, idx))
          elif subnode.data == 'enum_def':
              ns_name = current_processing_file_namespace
              free_enums.append(parse_enum(subnode, ns_name, file, tree.children, idx))
          elif subnode.data == 'options_def':
              ns_name = current_processing_file_namespace
              options.append(_parse_options_def(subnode, ns_name, file, tree.children, idx))
          elif subnode.data == 'compound_def':
              ns_name = current_processing_file_namespace
              compounds.append(_parse_compound_def(subnode, ns_name, file, tree.children, idx))
          elif subnode.data == 'import_stmt':
              path = None
              alias = None
              for child in subnode.children:
                  if isinstance(child, Token) and child.type == 'STRING':
                      path = str(child).strip('"')
                  elif isinstance(child, Token) and child.type == 'NAME':
                      alias = str(child)
              if path:
                  imports_raw.append((path, alias))
          # Ignore 'comment' at this level

    # The EarlyModel constructor needs to be updated to accept the new lists
    return EarlyModel(namespaces, free_enums, free_messages, options, compounds, imports_raw, file)


# Place this at the end of the file, after all helper functions (including process_node)
def _build_model_from_lark_tree(tree, current_processing_file_namespace: str, source_file: str = None):
    """
    Build a MessageModel from a Lark parse tree.
    Always creates and populates the file-level (global) namespace for global messages/enums.

    Args:
        tree: The Lark parse tree.
        current_processing_file_namespace: The namespace to be used for top-level items in this tree.
    """
    from message_model import MessageModel, Message, Field, Enum, EnumValue, Namespace, FieldType
    model = MessageModel()
    # (Undo patch) Namespace creation does not set source_file
    model.options = {}
    model.imports = {}
    _file_namespace_for_this_tree = current_processing_file_namespace

    # Helper: get set of import aliases
    import_aliases = set(getattr(model, 'imports', {}).keys()) if hasattr(model, 'imports') else set()
    if not hasattr(model, 'options'):
        model.options = {}

    # Remove the old version of resolve_reference_hierarchically; only use the new one with full signature

    def extract_doc_comment(children):
        comments = []
        def add_doc_prefix(line):
            s = line.lstrip()
            if s.startswith('///'):
                return s
            return '/// ' + s if s else ''
        for c in children:
            if isinstance(c, Token) and c.type == "DOC_COMMENT":
                comments.append(add_doc_prefix(str(c)))
            elif isinstance(c, Tree):
                if hasattr(c, 'data') and c.data == "comment":
                    for t in c.children:
                        if isinstance(t, Token) and t.type == "DOC_COMMENT":
                            comments.append(add_doc_prefix(str(t)))
                else:
                    comments.extend(extract_doc_comment(c.children))
        return "\n".join(comments)

    def find_preceding_doc_comment(node, root_children, root_index):
        """Finds a doc comment preceding a node at the root level or as a child."""
        doc = ""
        found_doc = False
        if root_children is not None and root_index is not None:
            i = root_index - 1
            while i >= 0:
                prev = root_children[i]
                if isinstance(prev, Tree) and prev.data == "comment":
                    comment_doc = extract_doc_comment([prev])
                    if comment_doc:
                        doc = comment_doc
                        found_doc = True
                    break
                if isinstance(prev, Tree) and prev.data == "item" and len(prev.children) == 1:
                    only_child = prev.children[0]
                    if isinstance(only_child, Tree) and only_child.data == "comment":
                        comment_doc = extract_doc_comment([only_child])
                        if comment_doc:
                            doc = comment_doc
                            found_doc = True
                        break
                break
        if not found_doc:
            for c in node.children:
                if isinstance(c, Token) and c.type == "DOC_COMMENT":
                    doc = c.lstrip()
                    found_doc = True
                    break
                elif isinstance(c, Tree) and c.data == "comment":
                    for t in c.children:
                        if isinstance(t, Token) and t.type == "DOC_COMMENT":
                            doc = t.lstrip()
                            found_doc = True
                            break
                    if found_doc:
                        break
        return doc

    def parse_value_list(values_tree, kind):
        """Generic value list parser for enums/options. Returns list of value dicts or EnumValue objects."""
        def parse_enum(node, prev_comment="", current_value=0):
            results = []
            if isinstance(node, Tree):
                if node.data in ("enum_value_or_comment_list", "enum_value_or_comment_seq"):
                    for child in node.children:
                        vals, prev_comment, current_value = parse_enum(child, prev_comment, current_value)
                        results.extend(vals)
                    return results, prev_comment, current_value
                elif node.data == "enum_value_or_comment_item":
                    for child in node.children:
                        vals, prev_comment, current_value = parse_enum(child, prev_comment, current_value)
                        results.extend(vals)
                    return results, prev_comment, current_value
                elif node.data == "enum_value_or_comment":
                    for child in node.children:
                        if isinstance(child, Tree) and child.data == "comment":
                            prev_comment = extract_doc_comment(child.children)
                        elif isinstance(child, Tree) and child.data == "enum_value":
                            vdoc = prev_comment or extract_doc_comment(child.children)
                            vname = None
                            vval = None
                            for c in child.children:
                                if isinstance(c, Token) and c.type == "NAME":
                                    vname = str(c)
                                elif isinstance(c, Token) and c.type == "NUMBER":
                                    vval = int(str(c))
                            if vname is not None:
                                val = vval if vval is not None else current_value
                                results.append(EnumValue(name=vname, value=val, options={}))
                                current_value = (vval + 1) if vval is not None else (current_value + 1)
                            prev_comment = ""
                    return results, prev_comment, current_value
                elif node.data == "enum_value":
                    vdoc = prev_comment or extract_doc_comment(node.children)
                    vname = None
                    vval = None
                    for c in node.children:
                        if isinstance(c, Token) and c.type == "NAME":
                            vname = str(c)
                        elif isinstance(c, Token) and c.type == "NUMBER":
                            vval = int(str(c))
                    if vname is not None:
                        val = vval if vval is not None else current_value
                        results.append(EnumValue(name=vname, value=val, options={}))
                        current_value = (vval + 1) if vval is not None else (current_value + 1)
                    prev_comment = ""
                    return results, prev_comment, current_value
            return results, prev_comment, current_value

        def parse_option(node, prev_comment=""):
            results = []
            if isinstance(node, Tree):
                if node.data in ("option_value_or_comment_list", "option_value_or_comment_seq"):
                    for child in node.children:
                        vals, prev_comment = parse_option(child, prev_comment)
                        results.extend(vals)
                    return results, prev_comment
                elif node.data == "option_value_or_comment_item":
                    if len(node.children) == 1 and isinstance(node.children[0], Tree) and node.children[0].data == "comment":
                        prev_comment = extract_doc_comment(node.children[0].children)
                        return [], prev_comment
                    for child in node.children:
                        vals, prev_comment = parse_option(child, prev_comment)
                        results.extend(vals)
                    return results, prev_comment
                elif node.data == "option_value_or_comment":
                    for child in node.children:
                        if isinstance(child, Tree) and child.data == "comment":
                            prev_comment = extract_doc_comment(child.children)
                        elif isinstance(child, Tree) and child.data == "option_value":
                            vdoc = prev_comment or extract_doc_comment(child.children)
                            vname = None
                            vval = None
                            for c in child.children:
                                if isinstance(c, Token) and c.type == "NAME":
                                    vname = str(c)
                                elif isinstance(c, Token) and c.type == "NUMBER":
                                    vval = int(str(c))
                            if vname is not None:
                                results.append({"name": vname, "value": vval, "description": vdoc})
                            prev_comment = ""
                    return results, prev_comment
                elif node.data == "option_value":
                    vdoc = prev_comment or extract_doc_comment(node.children)
                    vname = None
                    vval = None
                    for c in node.children:
                        if isinstance(c, Token) and c.type == "NAME":
                            vname = str(c)
                        elif isinstance(c, Token) and c.type == "NUMBER":
                            vval = int(str(c))
                    if vname is not None:
                        results.append({"name": vname, "value": vval, "description": vdoc})
                    prev_comment = ""
                    return results, prev_comment
                elif node.data == "option_value_or_comment_sep":
                    for child in node.children:
                        if isinstance(child, Tree) and child.data == "comment":
                            prev_comment = extract_doc_comment(child.children)
                    return [], prev_comment
            return results, prev_comment

        if kind == "enum":
            values, _, _ = parse_enum(values_tree)
            return values
        elif kind == "option":
            values, _ = parse_option(values_tree)
            return values
        return []
    def resolve_reference_hierarchically(ref_name, current_namespace, model, file_namespace, import_aliases=None):
        """
        Resolve a reference name according to MessageWrangler's namespace hierarchy rules.
        - ref_name: the (possibly unqualified) name to resolve (e.g., 'AA')
        - current_namespace: the current namespace context (e.g., 'Y::D')
        - model: the MessageModel
        - file_namespace: the file-level namespace (e.g., 'Y')
        - import_aliases: set of import aliases (e.g., {'L', ...})
        Returns the fully qualified name if found, else None.
        """
        # 1. If ref_name is already qualified (contains '::'), check directly
        if '::' in ref_name:
            if ref_name in model.messages or ref_name in model.enums or (hasattr(model, 'options') and ref_name in model.options):
                return ref_name
            return None
        # 2. Search up the namespace hierarchy
        ns_parts = current_namespace.split('::') if current_namespace else []
        for i in range(len(ns_parts), -1, -1):
            ns_candidate = '::'.join(ns_parts[:i])
            fq_name = f"{ns_candidate}::{ref_name}" if ns_candidate else ref_name
            if fq_name in model.messages or fq_name in model.enums or (hasattr(model, 'options') and fq_name in model.options):
                return fq_name
        # 3. Search file-level namespace
        fq_file_ns = f"{file_namespace}::{ref_name}"
        if fq_file_ns in model.messages or fq_file_ns in model.enums or (hasattr(model, 'options') and fq_file_ns in model.options):
            return fq_file_ns
        # 4. Search non-aliased imports' file-level namespaces
        if hasattr(model, 'imports'):
            for alias, import_path in model.imports.items():
                # Only non-aliased imports (alias == imported file-level namespace)
                if import_aliases and alias in import_aliases:
                    continue
                # Try to resolve in the imported model's file-level namespace
                imported_model = None
                try:
                    imported_model = build_model_from_file_recursive(import_path, set()) # Pass empty set for already_loaded
                except Exception:
                    continue
                if imported_model: # Check if model was loaded
                    imported_file_ns = os.path.splitext(os.path.basename(import_path))[0]
                    fq_imported = f"{imported_file_ns}::{ref_name}"
                    if fq_imported in imported_model.messages or fq_imported in imported_model.enums or (hasattr(imported_model, 'options') and fq_imported in imported_model.options):
                        return fq_imported
        # 5. Aliased imports: only if explicitly qualified (already handled above)
        return None
    def extract_field_from_node(f, extract_type_name, parent_children=None, node_index=None, extract_doc_comment=None, current_namespace=None):
        # --- Extract doc comment for the field (preceding or inline) ---
        doc = ""
        if extract_doc_comment is not None:
            # Look for preceding comment node in parent_children (message_body) if available
            if parent_children is not None and node_index is not None:
                i = node_index - 1
                while i >= 0:
                    prev = parent_children[i]
                    if isinstance(prev, Tree) and prev.data == "comment":
                        comment_doc = extract_doc_comment([prev])
                        if comment_doc:
                            doc = comment_doc
                        break
                    if isinstance(prev, Tree) and prev.data == "item" and len(prev.children) == 1:
                        only_child = prev.children[0]
                        if isinstance(only_child, Tree) and only_child.data == "comment":
                            comment_doc = extract_doc_comment([only_child])
                            if comment_doc:
                                doc = comment_doc
                            break
                    break
            # Fallback: scan own children for DOC_COMMENT if not found in parent
            if not doc:
                for c in f.children:
                    if isinstance(c, Token) and c.type == "DOC_COMMENT":
                        doc = c.lstrip()
                        break
                    elif isinstance(c, Tree) and c.data == "comment":
                        for t in c.children:
                            if isinstance(t, Token) and t.type == "DOC_COMMENT":
                                doc = t.lstrip()
                                break
                        if doc:
                            break

        # Find field modifiers (e.g., optional, repeated, etc.)
        modifiers = []
        for c in f.children:
            if isinstance(c, Tree) and c.data == "field_modifier":
                # field_modifier: Token (OPTIONAL, REPEATED, REQUIRED, etc.)
                for mod in c.children:
                    if isinstance(mod, Token):
                        modifiers.append(str(mod).lower())
            elif isinstance(c, Token) and c.type in {"OPTIONAL", "REPEATED", "REQUIRED"}:
                # fallback for legacy/edge cases
                modifiers.append(str(c).lower())

        # Find the NAME token for the field name
        fname = None
        for c in f.children:
            if isinstance(c, Token) and c.type == "NAME":
                fname = str(c)
                break

        # Find the type_def subtree
        type_def_node = None
        for c in f.children:
            if isinstance(c, Tree) and c.data == "type_def":
                type_def_node = c
                break

        # Find field options (e.g., [default = 5])
        options = {}
        for c in f.children:
            if isinstance(c, Tree) and c.data == "field_options":
                # field_options: [ option_assignments ]
                for opt in c.children:
                    if isinstance(opt, Tree) and opt.data == "option_assignments":
                        for assign in opt.children:
                            if isinstance(assign, Tree) and assign.data == "option_assignment":
                                # option_assignment: NAME = value
                                opt_name = None
                                opt_value = None
                                for part in assign.children:
                                    if isinstance(part, Token) and part.type == "NAME":
                                        opt_name = str(part)
                                    elif isinstance(part, Token) and part.type in {"NUMBER", "STRING"}:
                                        opt_value = str(part)
                                if opt_name is not None:
                                    options[opt_name] = opt_value

        # Debug: print type_def_node for diagnosis
        # print(f"[DEBUG] FIELD {fname} type_def_node: {type_def_node}, data: {getattr(type_def_node, 'data', None)}")
        # Unwrap type_def node to get the actual type (array_type, ref_type, etc.)
        actual_type_node = type_def_node
        if type_def_node and isinstance(type_def_node, Tree) and type_def_node.data == "type_def" and type_def_node.children:
            actual_type_node = type_def_node.children[0]

        # --- PATCH: Handle inline enum_type as field type ---
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "enum_type":
            # Synthesize a name for the inline enum based on the parent message and field name
            parent_message_name = None
            if parent_children is not None:
                # Try to find the message name in the parent_children
                for p_node in parent_children: # Iterate through actual nodes
                    if isinstance(p_node, Tree) and p_node.data == "message": # Check if it's a message node
                        for child_of_msg in p_node.children:
                            if isinstance(child_of_msg, Token) and child_of_msg.type == "NAME":
                                parent_message_name = str(child_of_msg)
                                break
                        if parent_message_name:
                            break
            if not parent_message_name: # Fallback if not found in parent_children (e.g. if field is at top level of message_body)
                # This logic might need refinement based on how parent_message_name is expected to be found
                # For now, assume we are inside a message context if extract_field_from_node is called
                # A better way would be to pass the current message object or its name.
                # Let's assume current_namespace might hint at the message if it's deeply nested,
                # or we rely on a more direct passing of the message context.
                # For now, using a placeholder if truly unknown.
                # This part is tricky without knowing the exact call hierarchy for parent_message_name.
                # Let's assume the message name is part of current_namespace or passed differently.
                # The original code had a simple loop that might not always work.
                # A robust solution would be to pass the Message object currently being processed.
                # For now, let's assume `current_namespace` might be the message name if not a real namespace.
                # This is a simplification.
                if current_namespace and "::" not in current_namespace: # Simplistic check
                    parent_message_name = current_namespace
                else:
                    parent_message_name = "InlineMsg" # Fallback

            enum_name = f"{parent_message_name}_{fname}_Enum"
            # Find the enum_value_or_comment_list child
            values_tree = None
            for c in actual_type_node.children:
                if isinstance(c, Tree) and c.data == "enum_value_or_comment_list":
                    values_tree = c
                    break
            enum_values = parse_value_list(values_tree, kind="enum") if values_tree else []
            inline_enum = Enum(name=enum_name, values=enum_values, parent=None, description=doc, namespace=None, parent_message_name=parent_message_name)
            # Set enum_type to the synthesized name for inline enums
            field = Field(
                name=fname,
                field_type=FieldType.ENUM,
                inline_enum=inline_enum,
                description=doc,
                comment=doc,
                options=options,
                modifiers=modifiers
            )
            field.enum_type = enum_name
            return field
        # --- PATCH: Handle inline options_type as field type ---
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "options_type":
            parent_message_name = "InlineMsg" # Simplified, see notes for enum_type
            # This part needs similar robust logic for parent_message_name as above.
            if current_namespace and "::" not in current_namespace:
                 parent_message_name = current_namespace

            options_name = f"{parent_message_name}_{fname}_Options"
            # Find the option_value_or_comment_list child
            values_tree = None
            for c in actual_type_node.children:
                if isinstance(c, Tree) and c.data == "option_value_or_comment_list":
                    values_tree = c
                    break
            option_values_raw = parse_value_list(values_tree, kind="option") if values_tree else []
            # Convert raw option values (dicts) to EnumValue objects for consistency if needed by Field
            # Assuming Field.inline_options expects an Enum-like object or list of EnumValues
            option_enum_values = [EnumValue(name=ov['name'], value=ov['value'], options={'description': ov.get('description','')}) for ov in option_values_raw]

            from message_model import Enum # Local import
            inline_options_obj = Enum(name=options_name, values=option_enum_values, parent=None, description=doc, namespace=None)

            field = Field(
                name=fname,
                field_type=FieldType.OPTIONS if hasattr(FieldType, 'OPTIONS') else FieldType.ENUM,
                inline_options=inline_options_obj, # Pass the Enum-like object
                description=doc,
                comment=doc,
                options=options,
                modifiers=modifiers
            )
            field.options_type = options_name
            return field
        # PATCH: Print node info for ModesAvailableReply.available if unresolved
        if fname == "available":
            print(f"[DEBUG FIELD NODE] Field: {fname}, actual_type_node: {getattr(actual_type_node, 'data', None)}, children: {getattr(actual_type_node, 'children', None)}")
        # Array type
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "array_type":
            element_type_node = actual_type_node.children[0]
            ref_name = extract_type_name(element_type_node)
            # If the reference is to a message in the file-level namespace, use the unqualified name
            msg_ref = ref_name
            if ref_name in model.messages:
                msg_obj = model.messages[ref_name]
                if getattr(msg_obj, 'namespace', None) == _file_namespace_for_this_tree:
                    msg_ref = msg_obj.name
            if ref_name in ["string", "int", "float", "bool", "byte"]:
                field_type = FieldType[ref_name.upper()]
                return Field(
                    name=fname,
                    field_type=field_type,
                    is_array=True,
                    description=doc,
                    comment=doc,
                    options=options,
                    modifiers=modifiers
                )
            else:
                # Message reference array (including namespaced)
                return Field(
                    name=fname,
                    field_type=FieldType.MESSAGE_REFERENCE,
                    message_reference=msg_ref,
                    is_array=True,
                    description=doc,
                    comment=doc,
                    options=options,
                    modifiers=modifiers
                )
        # Map type
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "map_type":
            key_type_node = actual_type_node.children[0]
            value_type_node = actual_type_node.children[1]
            key_type = extract_type_name(key_type_node)
            value_type = extract_type_name(value_type_node)
            if not value_type:
                value_type = "Any"
            return Field(
                name=fname,
                field_type=FieldType.MAP,
                is_map=True,
                map_key_type=key_type,
                map_value_type=value_type,
                description=doc,
                comment=doc,
                options=options,
                modifiers=modifiers
            )
        # Compound type
        compound_node = None
        base_type = None
        components = []
        # Check if actual_type_node itself is 'compound_type' or if it's a child
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "compound_type":
            compound_node = actual_type_node
        elif actual_type_node: # Original logic: look for compound_type as a child
             for child in actual_type_node.children:
                if isinstance(child, Tree) and child.data == "compound_type":
                    compound_node = child
                    break

        if compound_node:
            if len(compound_node.children) > 0 and isinstance(compound_node.children[0], Tree) and compound_node.children[0].data == "basic_type":
                basic_type_node = compound_node.children[0]
                if basic_type_node.children:
                    t = basic_type_node.children[0]
                    base_type = str(t)
                else:
                    base_type = getattr(basic_type_node, 'value', None) or "UNKNOWN"
            elif len(compound_node.children) > 0 and isinstance(compound_node.children[0], Token) and compound_node.children[0].type == "NAME": # Support NAME as base type
                base_type = str(compound_node.children[0])
            else:
                base_type = "UNKNOWN" # Default if no explicit base type found

            for child in compound_node.children:
                if isinstance(child, Tree) and child.data == "compound_component_seq":
                    for comp in child.children:
                        if isinstance(comp, Tree) and comp.data == "compound_component_item":
                            for sub in comp.children:
                                if isinstance(sub, Token) and sub.type == "NAME":
                                    components.append(str(sub))
            return Field(
                name=fname,
                field_type=FieldType.COMPOUND,
                compound_base_type=base_type,
                compound_components=components,
                description=doc,
                comment=doc,
                options=options,
                modifiers=modifiers
            )
        # Message reference, enum, or options reference, or basic type
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "ref_type":
            ref_name = extract_type_name(actual_type_node)
            # Try to resolve as enum, options, or message reference using hierarchical resolution
            resolved = resolve_reference_hierarchically(
                ref_name,
                current_namespace,
                model, # model object being built
                _file_namespace_for_this_tree, # file-level namespace for resolution in this tree
                import_aliases
            )
            if resolved:
                # Check what kind of symbol it is
                if resolved in model.enums:
                    field = Field(
                        name=fname,
                        field_type=FieldType.ENUM,
                        enum_reference=resolved,
                        description=doc,
                        comment=doc,
                        options=options,
                        modifiers=modifiers
                    )
                    field.enum_type = resolved
                    return field
                elif hasattr(model, 'options') and resolved in model.options:
                    field = Field(
                        name=fname,
                        field_type=FieldType.OPTIONS,
                        options_reference=resolved,
                        description=doc,
                        comment=doc,
                        options=options,
                        modifiers=modifiers
                    )
                    field.options_type = resolved
                    return field
                elif resolved in model.messages:
                    # If the resolved message is in the file-level namespace, use the unqualified name
                    msg_ref = resolved
                    msg_obj = model.messages[resolved]
                    if getattr(msg_obj, 'namespace', None) == _file_namespace_for_this_tree:
                        msg_ref = msg_obj.name
                    return Field(
                        name=fname,
                        field_type=FieldType.MESSAGE_REFERENCE,
                        message_reference=msg_ref,
                        description=doc,
                        comment=doc,
                        options=options,
                        modifiers=modifiers
                    )
            elif ref_name in ["string", "int", "float", "bool", "byte"]: # Basic types can also be ref_type if grammar allows
                field_type_val = FieldType[ref_name.upper()]
                return Field(
                    name=fname,
                    field_type=field_type_val,
                    description=doc,
                    comment=doc,
                    options=options,
                    modifiers=modifiers
                )
            else:
                # Unknown reference: store the original ref_name for post-processing
                field = Field(
                    name=fname,
                    field_type=FieldType.UNKNOWN,
                    description=doc,
                    comment=doc,
                    options=options,
                    modifiers=modifiers
                )
                field.type_name = ref_name
                return field

        # Basic type directly under type_def (not as ref_type)
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "basic_type":
            ftype_str = extract_type_name(actual_type_node)
            if ftype_str in ["string", "int", "float", "bool", "byte"]:
                field_type_val = FieldType[ftype_str.upper()]
                return Field(
                    name=fname,
                    field_type=field_type_val,
                    description=doc,
                    comment=doc,
                    options=options,
                    modifiers=modifiers
                )

        # Fallback for other cases or if type extraction failed
        ftype_str_fallback = extract_type_name(actual_type_node) if actual_type_node else None
        normalized_type = FieldType.UNKNOWN
        if ftype_str_fallback:
            ftype_str_lower = str(ftype_str_fallback).strip().lower()
            if ftype_str_lower == "boolean": ftype_str_lower = "bool"
            try:
                normalized_type = FieldType(ftype_str_lower)
            except ValueError: # Not a direct FieldType member value
                 # If it's not a basic type, it might be an unresolved reference
                if ftype_str_lower not in ["string", "int", "float", "bool", "byte"]:
                    field = Field(name=fname, field_type=FieldType.UNKNOWN, description=doc, comment=doc, options=options, modifiers=modifiers)
                    field.type_name = ftype_str_fallback # Store original name for later resolution
                    return field
                normalized_type = FieldType.UNKNOWN # Default to UNKNOWN if not a basic type and not resolved

        assert isinstance(normalized_type, FieldType), f"Invalid field_type for field '{fname}': got {repr(normalized_type)} from ftype={repr(ftype_str_fallback)}"
        return Field(
            name=fname,
            field_type=normalized_type,
            description=doc,
            comment=doc,
            options=options,
            modifiers=modifiers
        )

    def extract_type_name(type_node):
        if isinstance(type_node, Token) and type_node.type == "NAME":
            return str(type_node)
        if isinstance(type_node, Tree):
            # Handle qualified_name_with_dot (for message references and namespaces)
            if type_node.data == "qualified_name_with_dot":
                names = []
                for c in type_node.children:
                    if isinstance(c, Token) and c.type == "NAME":
                        names.append(str(c))
                return "::".join(names)
            # Handle basic_type
            if type_node.data == "basic_type":
                for c in type_node.children:
                    if isinstance(c, Token) and c.type == "BASIC_TYPE":
                        return str(c)
            # Fallback: recurse
            for child in type_node.children:
                t = extract_type_name(child)
                if t:
                    return t
        return None

    def process_node(node, parent_children=None, node_index=None, root_children=None, root_index=None, current_namespace=None):
        if not isinstance(node, Tree): # Skip tokens at this level
            return
        print(f"[DEBUG] Processing node: {getattr(node, 'data', 'Token')}, Namespace: {current_namespace}")

        if node.data == "options_def":
            doc = find_preceding_doc_comment(node, root_children, root_index)
            idx = 0
            while idx < len(node.children) and (
                (isinstance(node.children[idx], Token) and node.children[idx].type == "DOC_COMMENT") or
                (isinstance(node.children[idx], Tree) and node.children[idx].data == "comment")
            ):
                idx += 1
            name_token = node.children[idx]
            name = str(name_token) if isinstance(name_token, Token) else str(name_token.children[0]) # Handle NAME token or Tree(NAME)
            idx += 1
            values_tree = None
            while idx < len(node.children):
                if isinstance(node.children[idx], Tree) and node.children[idx].data == "option_value_or_comment_list":
                    values_tree = node.children[idx]
                    break
                idx += 1
            values = parse_value_list(values_tree, kind="option") if values_tree else []
            fqname = name
            if current_namespace:
                fqname = f"{current_namespace}::{name}"
            model.options[fqname] = {"name": name, "description": doc, "values": values}

        elif node.data == "item":
            for child_idx, child in enumerate(node.children): # Pass correct index for child
                process_node(child, node.children, child_idx, root_children, root_index, current_namespace)
        elif node.data == "compound_def":
            # Compound type definition at root level (not a field, but a type definition)
            # For now, skip adding to model unless you want to support named compound types
            pass
        elif node.data == "enum_def":
            doc = find_preceding_doc_comment(node, root_children, root_index)
            idx = 0
            # Skip doc comments and comment trees at the beginning of enum_def children
            while idx < len(node.children) and (
                (isinstance(node.children[idx], Token) and node.children[idx].type == "DOC_COMMENT") or
                (isinstance(node.children[idx], Tree) and node.children[idx].data == "comment")
            ):
                idx += 1

            kind_node = node.children[idx] # enum_kind
            # Defensive: handle empty enum_kind node (closed enum by default)
            is_open = False
            if isinstance(kind_node, Tree) and kind_node.data == "enum_kind":
                if kind_node.children and len(kind_node.children) > 0:
                    is_open = str(kind_node.children[0]) == "open_enum"
                else:
                    is_open = False
            elif isinstance(kind_node, Token):
                is_open = str(kind_node) == "open_enum"

            idx += 1
            name_node = node.children[idx] # NAME token for enum name
            name = str(name_node)
            idx += 1

            parent = None
            if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "inheritance":
                inh_node = node.children[idx]
                if inh_node.children and isinstance(inh_node.children[0], Tree) and inh_node.children[0].data == "qualified_name_with_dot":
                    parent = extract_type_name(inh_node.children[0])
                idx += 1

            values_tree = None
            # Find enum_value_or_comment_list
            while idx < len(node.children):
                if isinstance(node.children[idx], Tree) and node.children[idx].data == "enum_value_or_comment_list":
                    values_tree = node.children[idx]
                    break
                idx +=1

            values = parse_value_list(values_tree, kind="enum") if values_tree else []
            enum_obj = Enum(name=name, values=values, parent=parent, description=doc, namespace=current_namespace, is_open=is_open, source_file=source_file)
            model.add_enum(enum_obj)
            print(f"[DEBUG] Added enum to model.enums: {enum_obj.get_full_name()}")

        elif node.data == "message":
            doc = find_preceding_doc_comment(node, root_children, root_index)
            idx = 0
            # Skip doc comments and comment trees
            while idx < len(node.children) and (
                (isinstance(node.children[idx], Token) and node.children[idx].type == "DOC_COMMENT") or
                (isinstance(node.children[idx], Tree) and node.children[idx].data == "comment")
            ):
                idx += 1

            name_node = node.children[idx] # NAME token for message name
            name = str(name_node)
            idx += 1

            parent = None
            if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "inheritance":
                inh_node = node.children[idx]
                if inh_node.children and isinstance(inh_node.children[0], Tree) and inh_node.children[0].data == "qualified_name_with_dot":
                    parent = extract_type_name(inh_node.children[0])
                idx += 1

            # If not in a namespace, assign the file-level namespace
            msg_namespace = current_namespace if current_namespace is not None else _file_namespace_for_this_tree
            msg = Message(name=name, parent=parent, description=doc, comment=doc, namespace=msg_namespace, source_file=source_file)

            # Process message_body elements
            while idx < len(node.children):
                child_node = node.children[idx]
                if isinstance(child_node, Tree):
                    if child_node.data == "message_body":
                        for f_idx, f_node in enumerate(child_node.children):
                            if isinstance(f_node, Tree) and f_node.data == "field":
                                field = extract_field_from_node(f_node, extract_type_name, child_node.children, f_idx, extract_doc_comment, current_namespace=msg_namespace)
                                if field: msg.add_field(field)
                            elif isinstance(f_node, Tree) and f_node.data == "comment":
                                pass
                    elif child_node.data == "field":
                        field = extract_field_from_node(child_node, extract_type_name, node.children, idx, extract_doc_comment, current_namespace=msg_namespace)
                        if field: msg.add_field(field)
                    elif child_node.data == "comment":
                        pass
                idx += 1
            model.add_message(msg)

        elif node.data == "namespace":
            ns_name_token = node.children[0] # NAME token for namespace
            ns_name = str(ns_name_token)

            if ns_name in model.namespaces:
                ns = model.namespaces[ns_name]
            else:
                ns = Namespace(name=ns_name)
                model.add_namespace(ns)

            # Process items within the namespace
            # Children after name and '{' up to '}'
            # Assuming grammar: "namespace" NAME "{" item* "}"
            # Children are [NAME, Tree(item), Tree(item), ...] or [NAME, item, item, ...]
            # The loop should start from index 1 (after NAME)
            for child_idx, ns_item_node in enumerate(node.children[1:]): # Iterate over actual items
                 # Pass ns_item_node's parent (node.children) and its index relative to that parent
                process_node(ns_item_node, node.children, child_idx + 1, root_children, root_index, ns_name)

        elif node.data == "import_stmt":
            # Handled by build_model_from_file_recursive, but can extract info here if needed
            pass
        elif node.data == "comment":
            # Comments are generally handled by find_preceding_doc_comment
            pass


    def ensure_namespace(ns_name):
        if ns_name not in model.namespaces:
            model.namespaces[ns_name] = Namespace(ns_name)
        return model.namespaces[ns_name]


    for idx, item in enumerate(tree.children):
        process_node(item, tree.children, idx, tree.children, idx, None)

    # --- GLOBAL REGISTRATION OF INLINE ENUMS/OPTIONS --- (Moved after process_node loop)
    # Also register unqualified name for messages in file-level or imported namespaces
    # (if not already present)
    for msg in list(model.messages.values()):
        ns = getattr(msg, 'namespace', None)
        if ns == _file_namespace_for_this_tree or ns in model.imports or ns == ns.lower():
            if msg.name not in model.messages:
                model.messages[msg.name] = msg
    for msg in list(model.messages.values()):
        if hasattr(msg, 'fields'):
            for field in msg.fields:
                ns_prefix = f"{msg.namespace}::" if getattr(msg, 'namespace', None) else ""
                # Register with both legacy and qualified names for reference resolution
                synthetic_enum_name = f"{msg.name}_{field.name}_Enum"
                qualified_enum_name = f"{msg.name}.{field.name}"
                qualified_enum_name_colon = f"{msg.name}::{field.name}"
                ns_qualified_enum_name = f"{ns_prefix}{msg.name}.{field.name}" if ns_prefix else None
                ns_qualified_enum_name_colon = f"{ns_prefix}{msg.name}::{field.name}" if ns_prefix else None
                if hasattr(field, 'inline_enum') and field.inline_enum is not None:
                    field.inline_enum.name = synthetic_enum_name
                    model.enums[synthetic_enum_name] = field.inline_enum
                    print(f"[DEBUG] Registered inline enum with key: {synthetic_enum_name}")
                    model.enums[qualified_enum_name] = field.inline_enum
                    print(f"[DEBUG] Registered inline enum with key: {qualified_enum_name}")
                    model.enums[qualified_enum_name_colon] = field.inline_enum
                    print(f"[DEBUG] Registered inline enum with key: {qualified_enum_name_colon}")
                    if ns_qualified_enum_name:
                        model.enums[ns_qualified_enum_name] = field.inline_enum
                        print(f"[DEBUG] Registered inline enum with key: {ns_qualified_enum_name}")
                    if ns_qualified_enum_name_colon:
                        model.enums[ns_qualified_enum_name_colon] = field.inline_enum
                        print(f"[DEBUG] Registered inline enum with key: {ns_qualified_enum_name_colon}")
                if hasattr(field, 'inline_options') and field.inline_options is not None:
                    synthetic_options_name = f"{msg.name}::{field.name}_Options"
                    qualified_options_name = f"{msg.name}.{field.name}_Options"
                    qualified_options_name_colon = f"{msg.name}::{field.name}_Options"
                    ns_qualified_options_name = f"{ns_prefix}{msg.name}.{field.name}_Options" if ns_prefix else None
                    ns_qualified_options_name_colon = f"{ns_prefix}{msg.name}::{field.name}_Options" if ns_prefix else None
                    field.inline_options.name = synthetic_options_name
                    if hasattr(model, 'options') and isinstance(model.options, dict):
                        model.options[synthetic_options_name] = {
                            "name": synthetic_options_name,
                            "description": getattr(field.inline_options, 'description', ''),
                            "values": getattr(field.inline_options, 'values', [])
                        }
                        model.options[qualified_options_name] = model.options[synthetic_options_name]
                        model.options[qualified_options_name_colon] = model.options[synthetic_options_name]
                        if ns_qualified_options_name:
                            model.options[ns_qualified_options_name] = model.options[synthetic_options_name]
                        if ns_qualified_options_name_colon:
                            model.options[ns_qualified_options_name_colon] = model.options[synthetic_options_name]
    print(f"[DEBUG] model.enums keys after inline enum registration in _build_model_from_lark_tree: {list(model.enums.keys())}")
    # --- POST-PROCESS: Resolve UNKNOWN field types for inline enums/options --- (Moved after process_node loop)
    for msg in list(model.messages.values()):
        for field in msg.fields: # Ensure fields attribute exists
            if getattr(field, 'field_type', None) == FieldType.UNKNOWN:
                ref_name = getattr(field, 'type_name', None) or getattr(field, 'enum_reference', None) or getattr(field, 'options_reference', None)
                if not ref_name and hasattr(field, 'name'):
                    ref_name = field.name
                split_success = False
                msg_part = None
                field_part = None
                for sep in ('::', '.'):
                    if ref_name and sep in ref_name:
                        msg_part, field_part = ref_name.split(sep, 1)
                        break
                candidates = []
                if msg_part and field_part:
                    candidates.append(f"{msg_part}::{field_part}")
                    candidates.append(f"{msg_part}.{field_part}")
                if ref_name:
                    candidates.append(ref_name)
                for candidate in candidates:
                    # Try enums
                    if hasattr(model, 'enums') and candidate in model.enums:
                        field.field_type = FieldType.ENUM
                        field.enum_reference = candidate
                        split_success = True
                        break
                    # Try options
                    if hasattr(model, 'options') and candidate in model.options:
                        field.field_type = FieldType.OPTIONS
                        field.options_reference = candidate
                        field.options_type = candidate
                        split_success = True
                        break
                if split_success:
                    continue
       # Ensure the determined file-level namespace for this tree always exists in the model's namespaces.
    if _file_namespace_for_this_tree not in model.namespaces:
        model.namespaces[_file_namespace_for_this_tree] = Namespace(_file_namespace_for_this_tree)

    # Ensure all global messages are attached to the file-level namespace object
    file_ns_obj = model.namespaces[_file_namespace_for_this_tree]
    for msg in list(model.messages.values()):
        if getattr(msg, 'namespace', None) == _file_namespace_for_this_tree:
            file_ns_obj.messages[msg.name] = msg

    # DEBUG: Print all messages and their namespaces after all post-processing
    print("[DEBUG] model.messages:")
    for msg_name, msg in model.messages.items():
        print(f"  - {msg_name}: namespace={getattr(msg, 'namespace', None)}")
    print("[DEBUG] model.namespaces (after creation):")
    for ns_name, ns_obj in model.namespaces.items():
        print(f"  - {ns_name}: messages={list(getattr(ns_obj, 'messages', {}).keys())}")
    return model

def build_model_from_file_recursive(main_file_path: str, already_loaded=None) -> MessageModel:

    # moving to a flatten non recursive implementation
    if(already_loaded == None):
      files_needed = _get_all_imported_files(main_file_path, already_loaded)
      early_models = []
      for file_path in files_needed:
        with open(file_path, 'r', encoding='utf-8') as f:
          text = f.read()
        tree = parse_message_dsl(text)
        file_namespace = os.path.splitext(os.path.basename(file_path))[0]
        early_model = _build_early_model_from_lark_tree(tree, file_namespace, source_file=file_path)
        early_models.append(early_model)
        debug_print_early_model(early_model=early_model, file_path=file_namespace + ".txt")

    return None
    # Canonical implementation moved from def_file_loader.py
    if already_loaded is None:
        already_loaded = set()
    abs_path = os.path.abspath(main_file_path)
    if abs_path in already_loaded:
        raise RuntimeError(f"Circular import detected for file: {main_file_path}")
    already_loaded.add(abs_path)



    with open(main_file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    tree = parse_message_dsl(text)
    this_file_actual_namespace = os.path.splitext(os.path.basename(abs_path))[0]
    model = _build_model_from_lark_tree(tree, this_file_actual_namespace, source_file=abs_path)


    # --- FINAL PATCH: Ensure model.messages only contains FQN keys ---
    # Remove any non-FQN keys (i.e., keys without '::')
    fqn_messages = {}
    for msg in model.messages.values():
        fqn = msg.get_full_name()
        fqn_messages[fqn] = msg
    model.messages = fqn_messages

    # Find import statements in the file
    import_pattern = re.compile(r'^\s*import\s+"([^"]+)"\s+as\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
    base_dir = os.path.dirname(abs_path)
    for match in import_pattern.finditer(text):
        import_path, import_alias = match.groups()
        import_file = os.path.normpath(os.path.join(base_dir, import_path))
        imported_model = build_model_from_file_recursive(import_file, already_loaded)
        # --- PATCH: Track imports in the model ---
        if hasattr(model, 'imports'):
            model.imports[import_alias] = imported_model
        # Merge imported namespaces/messages into the main model under the alias
        for ns_name, ns_obj in imported_model.namespaces.items():
            # Always set the namespace of all messages/enums to the alias
            for msg in ns_obj.messages.values():
                msg.namespace = import_alias
            if hasattr(ns_obj, 'enums'):
                for enum in ns_obj.enums.values():
                    enum.namespace = import_alias
            ns_obj.name = import_alias
            if import_alias not in model.namespaces:
                import copy
                ns_copy = copy.deepcopy(ns_obj)
                ns_copy.name = import_alias
                # Also set all messages/enums in the copy to the alias
                for msg in ns_copy.messages.values():
                    msg.namespace = import_alias
                if hasattr(ns_copy, 'enums'):
                    for enum in ns_copy.enums.values():
                        enum.namespace = import_alias
                model.namespaces[import_alias] = ns_copy
            else:
                model.namespaces[import_alias].messages.update(ns_obj.messages)
                if hasattr(model.namespaces[import_alias], 'enums') and hasattr(ns_obj, 'enums'):
                    model.namespaces[import_alias].enums.update(ns_obj.enums)
        # Merge imported messages into the main model under the alias
        # Need to reconstruct the key for all imported messages
        for original_key, imported_msg in imported_model.messages.items():
            imported_msg.namespace = import_alias # Update the namespace to the alias
            # Construct the new key by prepending the import alias to the original key
            new_key = f"{import_alias}::{original_key}"
            model.messages[new_key] = imported_msg
        # Merge imported enums into the main model under the alias
        # Need to reconstruct the key for inline enums using the import alias and parent message name
        # Merge imported enums into the main model under the alias
        # Need to reconstruct the key for all imported enums (standalone and inline)
        for original_key, imported_enum in imported_model.enums.items():
            imported_enum.namespace = import_alias # Update the namespace to the alias
            # Construct the new key by prepending the import alias to the original key
            new_key = f"{import_alias}::{original_key}"
            model.enums[new_key] = imported_enum
        # Optionally, merge options, etc.
    # --- PATCH: Normalize namespaces for all messages/enums to file-level namespace if not set ---
    # This ensures all types are visible in the generated C++ namespace
    base_filename = os.path.splitext(os.path.basename(main_file_path))[0]
    file_namespace = base_filename
    for msg in model.messages.values():
        if not getattr(msg, 'namespace', None):
            msg.namespace = file_namespace
    for enum in model.enums.values():
        if not getattr(enum, 'namespace', None):
            enum.namespace = file_namespace
    # Ensure the model always knows its source file for correct header naming
    model.main_file_path = main_file_path

    # --- POST-PROCESS: Ensure all namespaces are present and populated ---
    # 1. Collect all unique namespaces from messages and enums
    all_ns = set()
    for msg in model.messages.values():
        if getattr(msg, 'namespace', None):
            all_ns.add(msg.namespace)
    for enum in model.enums.values():
        if getattr(enum, 'namespace', None):
            all_ns.add(enum.namespace)
    # 2. Ensure Namespace objects exist for all
    for ns in all_ns:
        if ns not in model.namespaces:
            from message_model import Namespace
            model.namespaces[ns] = Namespace(ns)
    # 3. Attach all messages/enums to their Namespace objects
    for msg in model.messages.values():
        ns = getattr(msg, 'namespace', None)
        if ns and ns in model.namespaces:
            model.namespaces[ns].messages[msg.name] = msg
    for enum in model.enums.values():
        ns = getattr(enum, 'namespace', None)
        if ns and ns in model.namespaces:
            if not hasattr(model.namespaces[ns], 'enums'):
                model.namespaces[ns].enums = {}
            model.namespaces[ns].enums[enum.name] = enum
    # --- POST-PROCESS: Validate enum inheritance parent references ---
    for enum in list(model.enums.values()):
        if enum.parent:
            parent_name = enum.parent
            candidates = [parent_name]
            if '::' not in parent_name and getattr(enum, 'namespace', None):
                candidates.insert(0, f"{enum.namespace}::{parent_name}")
            found = False
            for candidate in candidates:
                if candidate in model.enums:
                    found = True
                    break
            if not found:
                raise RuntimeError(f"Cannot resolve parent enum '{parent_name}' for enum '{enum.namespace + '::' if enum.namespace else ''}{enum.name}'")
    # --- POST-PROCESS: Validate message inheritance parent references ---
    for msg in list(model.messages.values()):
        if msg.parent:
            parent_name = msg.parent
            candidates = [parent_name]
            if '::' not in parent_name and getattr(msg, 'namespace', None):
                candidates.insert(0, f"{msg.namespace}::{parent_name}")
            found = False
            for candidate in candidates:
                if candidate in model.messages:
                    found = True
                    break
            if not found:
                raise RuntimeError(f"Cannot resolve parent message '{parent_name}' for message '{msg.namespace + '::' if msg.namespace else ''}{msg.name}'")

    json_path = os.path.splitext(os.path.basename(main_file_path))[0] + ".json"
    pretty_print_model(model, file_path=json_path)

    return model

def _get_all_imported_files(main_file_path: str, already_loaded=None) -> list:
    """
    Recursively collect all imported .def files (full absolute paths) starting from main_file_path.
    Returns a list of all unique imported file paths, including the main file itself.
    """
    if already_loaded is None:
        already_loaded = set()
    abs_path = os.path.abspath(main_file_path)
    if abs_path in already_loaded:
        return []
    already_loaded.add(abs_path)
    imported_files = [abs_path]
    with open(main_file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    import_pattern = re.compile(r'^\s*import\s+"([^"]+)"\s+as\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
    base_dir = os.path.dirname(abs_path)
    for match in import_pattern.finditer(text):
        import_path, _ = match.groups()
        import_file = os.path.normpath(os.path.join(base_dir, import_path))
        imported_files.extend(_get_all_imported_files(import_file, already_loaded))
    return list(dict.fromkeys(imported_files))  # Remove duplicates, preserve order
