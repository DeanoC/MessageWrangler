"""
Builds a MessageModel from a Lark parse tree.
"""
from typing import Any
from lark import Tree, Token
from message_model import MessageModel, Message, Field, Enum, EnumValue, Namespace, FieldType


def build_model_from_lark_tree(tree: Tree) -> MessageModel:
    model = MessageModel()
    if not hasattr(model, 'options'):
        model.options = {}

    def extract_doc_comment(children):
        comments = []
        for c in children:
            if isinstance(c, Token) and c.type == "DOC_COMMENT":
                comments.append(str(c).lstrip())
            elif isinstance(c, Tree):
                if hasattr(c, 'data') and c.data == "comment":
                    for t in c.children:
                        if isinstance(t, Token) and t.type == "DOC_COMMENT":
                            comments.append(str(t).lstrip())
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

    def extract_field_from_node(f, extract_type_name, parent_children=None, node_index=None, extract_doc_comment=None):
        # --- Enhanced Field Extraction: modifiers, options, doc comments ---
        # Extract doc comment for the field (preceding or inline)
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
        # Array type
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "array_type":
            element_type_node = actual_type_node.children[0]
            ref_name = extract_type_name(element_type_node)
            # print(f"[DEBUG] ARRAY FIELD: {fname}, element_type_node={element_type_node}, ref_name={ref_name}")
            if ref_name in ["string", "int", "float", "bool", "byte"]:
                field_type = FieldType[ref_name.upper()]
                return Field(
                    name=fname,
                    field_type=field_type,
                    is_array=True,
                    description=doc,
                    options=options,
                    modifiers=modifiers
                )
            else:
                # Message reference array (including namespaced)
                return Field(
                    name=fname,
                    field_type=FieldType.MESSAGE_REFERENCE,
                    message_reference=ref_name,
                    is_array=True,
                    description=doc,
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
                options=options,
                modifiers=modifiers
            )
        # Compound type
        compound_node = None
        base_type = None
        components = []
        if actual_type_node:
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
            else:
                base_type = "UNKNOWN"
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
                options=options,
                modifiers=modifiers
            )
        # Message reference or basic type
        if actual_type_node and isinstance(actual_type_node, Tree) and actual_type_node.data == "ref_type":
            ref_name = extract_type_name(actual_type_node)
            if ref_name in ["string", "int", "float", "bool", "byte"]:
                field_type = FieldType[ref_name.upper()]
                return Field(
                    name=fname,
                    field_type=field_type,
                    description=doc,
                    options=options,
                    modifiers=modifiers
                )
            else:
                return Field(
                    name=fname,
                    field_type=FieldType.MESSAGE_REFERENCE,
                    message_reference=ref_name,
                    description=doc,
                    options=options,
                    modifiers=modifiers
                )
            element_type_node = type_def_node.children[0]
            ref_name = extract_type_name(element_type_node)
            # Debug print
            print(f"[DEBUG] ARRAY FIELD: {fname}, element_type_node={element_type_node}, ref_name={ref_name}")
            if ref_name in ["string", "int", "float", "bool", "byte"]:
                field_type = FieldType[ref_name.upper()]
                return Field(
                    name=fname,
                    field_type=field_type,
                    is_array=True,
                    description=doc,
                    options=options,
                    modifiers=modifiers
                )
            else:
                # Message reference array (including namespaced)
                return Field(
                    name=fname,
                    field_type=FieldType.MESSAGE_REFERENCE,
                    message_reference=ref_name,
                    is_array=True,
                    description=doc,
                    options=options,
                    modifiers=modifiers
                )
        # Map type
        if type_def_node and isinstance(type_def_node, Tree) and type_def_node.data == "map_type":
            key_type_node = type_def_node.children[0]
            value_type_node = type_def_node.children[1]
            key_type = extract_type_name(key_type_node)
            value_type = extract_type_name(value_type_node)
            return Field(
                name=fname,
                field_type=FieldType.UNKNOWN,  # Could add MAP to FieldType if desired
                is_map=True,
                map_key_type=key_type,
                description=doc,
                options=options,
                modifiers=modifiers
            )
        # Compound type
        compound_node = None
        base_type = None
        components = []
        if type_def_node:
            for child in type_def_node.children:
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
            else:
                base_type = "UNKNOWN"
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
                options=options,
                modifiers=modifiers
            )
        # Message reference type
        if type_def_node and isinstance(type_def_node, Tree) and type_def_node.data == "ref_type":
            ref_name = extract_type_name(type_def_node)
            return Field(
                name=fname,
                field_type=FieldType.MESSAGE_REFERENCE,
                message_reference=ref_name,
                description=doc,
                options=options,
                modifiers=modifiers
            )
        # Not a compound or special field
        ftype = None
        try:
            ftype = extract_type_name(type_def_node) if type_def_node else None
        except Exception:
            ftype = None
        normalized_type = None
        if ftype:
            ftype_str = str(ftype).strip().lower()
            # Map aliases (e.g., boolean -> bool)
            if ftype_str == "boolean":
                ftype_str = "bool"
            # Only allow valid FieldType members
            for member in FieldType:
                if member.value == ftype_str:
                    normalized_type = member
                    break
        field_type = normalized_type if normalized_type is not None else FieldType.UNKNOWN
        # Diagnostic assertion: field_type must be a FieldType, never a string
        assert isinstance(field_type, FieldType), f"Invalid field_type for field '{fname}': got {repr(field_type)} from ftype={repr(ftype)}"
        return Field(
            name=fname,
            field_type=field_type,
            description=doc,
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

    def debug_print_tree(subtree, label="FULL TREE"):
        pass

    # debug_print_tree(tree)

    def process_node(node, parent_children=None, node_index=None, root_children=None, root_index=None, current_namespace=None):
        if node.data == "options_def":
            doc = find_preceding_doc_comment(node, root_children, root_index)
            idx = 0
            while idx < len(node.children) and (
                (isinstance(node.children[idx], Token) and node.children[idx].type == "DOC_COMMENT") or
                (isinstance(node.children[idx], Tree) and node.children[idx].data == "comment")
            ):
                idx += 1
            name = str(node.children[idx])
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
        if not isinstance(node, Tree):
            return
        # print(f"[DEBUG] Node: {getattr(node, 'data', None)}")
        if node.data == "item":
            for idx, child in enumerate(node.children):
                process_node(child, node.children, idx, root_children, root_index, current_namespace)
        elif node.data == "compound_def":
            # Compound type definition at root level (not a field, but a type definition)
            # For now, skip adding to model unless you want to support named compound types
            pass
        elif node.data == "enum_def":
            # print(f"[DEBUG] Enum children: {[str(c) for c in node.children]}")
            doc = find_preceding_doc_comment(node, root_children, root_index)
            idx = 0
            while idx < len(node.children) and (
                (isinstance(node.children[idx], Token) and node.children[idx].type == "DOC_COMMENT") or
                (isinstance(node.children[idx], Tree) and node.children[idx].data == "comment")
            ):
                idx += 1
            kind = str(node.children[idx])
            idx += 1
            name = str(node.children[idx])
            # print(f"[DEBUG] Registering enum: '{name}'")
            idx += 1
            parent = None
            if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "inheritance":
                inh = node.children[idx]
                if len(inh.children) > 0:
                    qn = inh.children[0]
                    if isinstance(qn, Tree) and getattr(qn, 'data', None) == "qualified_name_with_dot":
                        names = []
                        for t in qn.children:
                            if isinstance(t, Token) and t.type == "NAME":
                                names.append(str(t))
                        if len(qn.children) >= 3 and isinstance(qn.children[-2], Token) and qn.children[-2].type == "DOT":
                            parent = "::".join(names[:-1]) + "." + names[-1] if len(names) > 1 else names[-1]
                        else:
                            parent = "::".join(names)
                    else:
                        parent = str(qn)
                idx += 1
            values_tree = None
            while idx < len(node.children):
                if isinstance(node.children[idx], Tree) and node.children[idx].data == "enum_value_or_comment_list":
                    values_tree = node.children[idx]
                    break
                idx += 1
            values = parse_value_list(values_tree, kind="enum") if values_tree else []
            enum_obj = Enum(name=name, values=values, parent=parent, description=doc, namespace=current_namespace)
            model.add_enum(enum_obj)
        elif node.data == "message":
            # print(f"[DEBUG] (MESSAGE) root_index={root_index}, root_children={[(c.data if isinstance(c, Tree) else str(type(c))) for c in (root_children or [])]}")
            doc = find_preceding_doc_comment(node, root_children, root_index)
            idx = 0
            while idx < len(node.children) and (
                (isinstance(node.children[idx], Token) and node.children[idx].type == "DOC_COMMENT") or
                (isinstance(node.children[idx], Tree) and node.children[idx].data == "comment")
            ):
                idx += 1
            name = str(node.children[idx])
            idx += 1
            parent = None
            if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "inheritance":
                inh = node.children[idx]
                if len(inh.children) > 0:
                    qn = inh.children[0]
                    if isinstance(qn, Tree) and qn.data == "qualified_name_with_dot":
                        names = []
                        for t in qn.children:
                            if isinstance(t, Token) and t.type == "NAME":
                                names.append(str(t))
                        parent = "::".join(names)
                    else:
                        parent = str(qn)
            msg = Message(name=name, parent=parent, description=doc, namespace=current_namespace)
            for mb in node.children[idx:]:
                if isinstance(mb, Tree) and mb.data == "message_body":
                    for f_idx, f in enumerate(mb.children):
                        if isinstance(f, Tree) and f.data == "field":
                            field = extract_field_from_node(f, extract_type_name, mb.children, f_idx, extract_doc_comment)
                            msg.add_field(field)
            model.add_message(msg)
        elif node.data == "namespace":
            # print(f"[DEBUG] Registering namespace: '{str(node.children[0])}'")
            ns_name = str(node.children[0])
            ns = Namespace(name=ns_name)
            for ns_item in node.children[1:]:
                if isinstance(ns_item, Tree):
                    process_node(ns_item, node.children, None, node.children, None, ns_name)
            model.add_namespace(ns)
        # TODO: Add options_def, compound_def, etc. (compound_def handled above for fields)

    for idx, item in enumerate(tree.children):
        process_node(item, tree.children, idx, tree.children, idx, None)
    return model

# Usage example (not for production):
# from lark_parser import parse_message_dsl
# tree = parse_message_dsl(open("some.def").read())
# model = build_model_from_lark_tree(tree)
