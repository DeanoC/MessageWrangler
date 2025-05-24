# def_file_loader.py
# Handles reading .def files and resolving imports recursively for MessageWrangler.
import os
from lark_parser import parse_message_dsl
from lark import Token, Tree
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyField, EarlyEnum, EarlyEnumValue

# Convenience function to load a .def file and return an EarlyModel

def load_def_file(def_file_path: str):
    with open(def_file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    file_namespace = os.path.splitext(os.path.basename(def_file_path))[0]
    tree = parse_message_dsl(text)
    return _build_early_model_from_lark_tree(tree, file_namespace, source_file=def_file_path)

def _build_early_model_from_lark_tree(tree, current_processing_file_namespace: str, source_file: str = None):
    # Top-level: scan for namespaces, messages, enums, options_def, compound_def, import_stmt
    namespaces = []
    free_messages = [] # Top-level messages
    free_enums = [] # Top-level enums
    options = [] # Top-level options_def
    compounds = [] # Top-level compound_def
    imports_raw = [] # List of (path, alias) tuples

    # DEBUG: Print tree for inspection
    print(f"[DEBUG] Parse tree: {tree}")

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
                        # Only set value if explicitly present, else use None
                        values.append(EarlyEnumValue(vname, vval, file, namespace, vline, comment=vcomment, doc=vdoc))
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
                    # Only set value if explicitly present, else use None
                    values.append(EarlyEnumValue(vname, vval, file, namespace, vline, comment=vcomment, doc=vdoc))

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
            # If this is a primitive type node, set raw_type to its string value
            if type_node.data in {'int', 'string', 'bool', 'float', 'double'}:
                info['raw_type'] = type_node.data
            if type_node.data == 'array_type':
                if type_node.children:
                    info['element_type_raw'] = _extract_raw_type_info(type_node.children[0]).get('raw_type')
            elif type_node.data == 'map_type':
                # Map type: Map < key , value >
                # Children: [map_key_type, map_value_type]
                # Defensive: flatten wrappers and handle missing children
                key_node = None
                value_node = None
                if len(type_node.children) > 1:
                    key_node = type_node.children[0]
                    value_node = type_node.children[1]
                elif len(type_node.children) == 1:
                    # Sometimes the parser may wrap both in a single child
                    if hasattr(type_node.children[0], 'children') and len(type_node.children[0].children) == 2:
                        key_node = type_node.children[0].children[0]
                        value_node = type_node.children[0].children[1]
                # Descend into map_key_type/map_value_type wrappers if present
                if key_node and hasattr(key_node, 'data') and key_node.data == 'map_key_type' and key_node.children:
                    key_node = key_node.children[0]
                if value_node and hasattr(value_node, 'data') and value_node.data == 'map_value_type' and value_node.children:
                    value_node = value_node.children[0]
                # Unwrap type_def for key_node if present
                if key_node and hasattr(key_node, 'data') and key_node.data == 'type_def' and key_node.children:
                    key_node = key_node.children[0]
                # Unwrap type_def for value_node if present
                if value_node and hasattr(value_node, 'data') and value_node.data == 'type_def' and value_node.children:
                    value_node = value_node.children[0]
                key_info = _extract_raw_type_info(key_node) if key_node else {'raw_type': '?', 'type_name': '?'}
                value_info = _extract_raw_type_info(value_node) if value_node else {'raw_type': '?', 'type_name': '?'}
                # Prefer raw_type if set and not '?', else type_name
                info['map_key_type_raw'] = key_info.get('raw_type') if key_info.get('raw_type') not in (None, '?') else key_info.get('type_name') or '?'
                info['map_value_type_raw'] = value_info.get('raw_type') if value_info.get('raw_type') not in (None, '?') else value_info.get('type_name') or '?'
                # Set the type_name for the map itself
                key_type_str = info.get('map_key_type_raw', '?')
                value_type_str = info.get('map_value_type_raw', '?')
                info['type_name'] = f"Map<{key_type_str}, {value_type_str}>"
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
        # (Debug output removed)
        value_node_name = 'enum_value' if kind == 'enum' else 'option_value'
        def flatten_nodes(nodes, out):
            for node in nodes:
                if isinstance(node, Tree) and getattr(node, 'data', None) in (
                    'option_value_or_comment_list',
                    'option_value_or_comment_seq',
                    'option_value_or_comment_item',
                    'enum_value_or_comment_list',
                    'enum_value_or_comment_seq',
                    'enum_value_or_comment_item',
                    'option_value_or_comment_sep',
                    'enum_value_or_comment_sep',
                ):
                    flatten_nodes(node.children, out)
                elif isinstance(node, Tree) and getattr(node, 'data', None) == value_node_name:
                    out.append(('value', node))
                elif isinstance(node, Tree) and getattr(node, 'data', None) == 'comment':
                    for c in node.children:
                        if isinstance(c, Token) and c.type == 'DOC_COMMENT':
                            out.append(('doc', str(c).strip()))
                elif isinstance(node, Token) and node.type == 'DOC_COMMENT':
                    out.append(('doc', str(node).strip()))
                # Ignore other nodes (LOCAL_COMMENT, C_COMMENT, etc.)
        """Generic raw value list parser for enums/options. Returns list of raw value dicts."""
        raw_values = []
        if values_tree is None:
            return raw_values

        value_node_name = 'enum_value' if kind == 'enum' else 'option_value'

        # Flatten the tree into a sequence of ('doc', docstring) and ('value', value_node) pairs
        def flatten_nodes(nodes, out):
            for node in nodes:
                if isinstance(node, Tree) and getattr(node, 'data', None) in (
                    'option_value_or_comment_list',
                    'option_value_or_comment_seq',
                    'option_value_or_comment_item',
                    'enum_value_or_comment_list',
                    'enum_value_or_comment_seq',
                    'enum_value_or_comment_item',
                    'option_value_or_comment_sep',
                    'enum_value_or_comment_sep',
                ):
                    flatten_nodes(node.children, out)
                elif isinstance(node, Tree) and getattr(node, 'data', None) == value_node_name:
                    out.append(('value', node))
                elif isinstance(node, Tree) and getattr(node, 'data', None) == 'comment':
                    for c in node.children:
                        if isinstance(c, Token) and c.type == 'DOC_COMMENT':
                            out.append(('doc', str(c).strip()))
                elif isinstance(node, Token) and node.type == 'DOC_COMMENT':
                    out.append(('doc', str(node).strip()))
                # Ignore other nodes (LOCAL_COMMENT, C_COMMENT, etc.)

        flat_seq = []
        if hasattr(values_tree, 'children'):
            flatten_nodes(values_tree.children, flat_seq)

        # Robust doc association: attach all preceding DOCs to a value, and also attach an inline DOC if it immediately follows
        doc_buffer = []
        i = 0
        n = len(flat_seq)
        while i < n:
            typ, item = flat_seq[i]
            if typ == 'doc':
                doc_buffer.append(item)
                i += 1
            elif typ == 'value':
                vname = None
                vval = None
                child_doc_strings = []
                for child_token in item.children:
                    if isinstance(child_token, Token) and child_token.type == 'DOC_COMMENT':
                        child_doc_strings.append(str(child_token).strip())
                    elif isinstance(child_token, Token) and child_token.type == 'NAME':
                        vname = str(child_token)
                    elif isinstance(child_token, Token) and child_token.type == 'NUMBER':
                        vval = int(str(child_token))
                doc_strings = []
                # Preceding doc comments (buffer) or child doc comments
                if doc_buffer:
                    doc_strings.extend(doc_buffer)
                elif child_doc_strings:
                    doc_strings.extend(child_doc_strings)
                # If neither, look for inline doc comment (immediately after value)
                elif i + 1 < n and flat_seq[i + 1][0] == 'doc':
                    doc_strings.append(flat_seq[i + 1][1])
                    i += 1  # Skip the inline doc for the next value
                vdoc_str = "\n".join([d.strip() for d in doc_strings])
                vcomment_str = vdoc_str
                if vname is not None:
                    raw_values.append({
                        'name': vname,
                        'value': vval, # Can be None if no explicit value
                        'doc': vdoc_str,
                        'comment': vcomment_str
                    })
                doc_buffer.clear()
                i += 1
            else:
                i += 1
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

        # Set type_type for map/array/compound/enum/options
        if type_info.get('map_key_type_raw') is not None or type_info.get('map_value_type_raw') is not None:
            type_type = 'map_type'
        elif type_info.get('element_type_raw') is not None:
            type_type = 'array_type'
        elif type_info.get('compound_base_type_raw') and type_info.get('compound_components_raw'):
            type_type = 'compound'
        elif type_info.get('is_inline_enum', False):
            type_type = 'enum_type'
        elif type_info.get('is_inline_options', False):
            type_type = 'options_type'
        else:
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
        # Robust doc extraction: check both preceding siblings and direct children for DOC_COMMENT
        doc, comment = _extract_comments(options_node, parent_children, node_index)
        # If doc is empty, check for DOC_COMMENT tokens as direct children
        if not doc:
            doc_comments = []
            for child in options_node.children:
                if isinstance(child, Token) and child.type == 'DOC_COMMENT':
                    doc_comments.append(str(child).strip())
            if doc_comments:
                doc = "\n".join(doc_comments)
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