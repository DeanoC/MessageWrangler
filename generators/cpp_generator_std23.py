"""
C++23-compliant code generator for MessageWrangler message definitions.
Implements the C++23 variant using the shared CppGeneratorBase.
"""
import os
import re

from generators.cpp_generator import CppGeneratorBase

class CppGeneratorStd23(CppGeneratorBase):
    def _find_type_in_imports(self, type_name, import_map=None, already_visited=None):
        """
        Recursively search imported models for a type (message or enum) by name.
        Returns (namespace, type_kind) if found, else (None, None).
        type_kind is 'message' or 'enum'.
        """
        if already_visited is None:
            already_visited = set()
        model = getattr(self, 'model', None)
        if not model or not hasattr(model, 'imports') or not model.imports:
            return (None, None)
        import_map = import_map or {}
        from def_file_loader import build_model_from_file_recursive
        for imported_ns, imported_path in model.imports.items():
            imported_base = os.path.splitext(os.path.basename(imported_path))[0]
            if imported_path in already_visited:
                continue
            already_visited.add(imported_path)
            try:
                imported_model = build_model_from_file_recursive(imported_path)
                # Check messages
                if hasattr(imported_model, 'messages') and type_name in imported_model.messages:
                    ns = getattr(imported_model.messages[type_name], 'namespace', None)
                    return (ns, 'message')
                # Check enums
                if hasattr(imported_model, 'enums') and type_name in imported_model.enums:
                    ns = getattr(imported_model.enums[type_name], 'namespace', None)
                    return (ns, 'enum')
                # Recurse into further imports
                sub_gen = CppGeneratorStd23([imported_model], model=imported_model)
                ns, kind = sub_gen._find_type_in_imports(type_name, import_map, already_visited)
                if ns:
                    return (ns, kind)
            except Exception:
                continue
        return (None, None)
    def __init__(self, namespaces, options=None, model=None):
        super().__init__(namespaces, options)
        # Store the model if provided, so we can always find all enums/messages for a namespace
        self.model = model

    # DEBUG: Print model and namespace structure for diagnosis
    def debug_model_structure(self):
        model = getattr(self, 'model', None)
        if model:
            print("[DEBUG] Model namespaces:", list(getattr(model, 'namespaces', {}).keys()))
            for ns_name_dbg, ns_obj in getattr(model, 'namespaces', {}).items():
                print(f"[DEBUG] Namespace '{ns_name_dbg}': messages={list(getattr(ns_obj, 'messages', {}).keys())} enums={list(getattr(ns_obj, 'enums', {}).keys())}")
            print("[DEBUG] Top-level messages in model:", list(getattr(model, 'messages', {}).keys()))
            print("[DEBUG] Top-level enums in model:", list(getattr(model, 'enums', {}).keys()))
    def _cpp_base_class_name(self, parent, ns_name=None):
        """
        Given a parent reference (possibly with namespace, e.g., Base::Command),
        return the correct C++ type name for use as a base class (e.g., Base::Command).
        """
        if not parent:
            return None
        # If parent is already a C++-style identifier (no '::'), just sanitize
        if '::' not in parent:
            return self._sanitize_identifier(parent)
        # If parent is namespaced (e.g., Base::Command), use C++ namespace separator
        parts = parent.split('::')
        return '::'.join(self._sanitize_identifier(p) for p in parts)
    def _generate_namespace_decls_only(self, ns, def_path=None, header_filename=None, base_filename=None, import_map=None, root_namespace=None, emitted_enum_names=None, emitted_struct_names=None, fully_qualify=False, ns_prefix=None):
        # --- Collect inline enums from message fields and emit as top-level enums ---
        # Map: (msg_cpp_name, field_name) -> enum_obj
        inline_enums_to_emit = []
        from message_model import FieldType
        for msg in messages:
            msg_cpp_name = self._sanitize_identifier(msg.name)
            for field in getattr(msg, 'fields', []):
                if (getattr(field, 'field_type', None) == FieldType.INLINE_ENUM or getattr(field, 'inline_enum', None)) and hasattr(field, 'inline_enum') and field.inline_enum is not None:
                    enum_obj = field.inline_enum
                    enum_cpp_name = f"{msg_cpp_name}_{self._sanitize_identifier(field.name)}_Enum"
                    fq_enum_name = f"{ns_name}::{enum_cpp_name}"
                    if fq_enum_name not in emitted_enum_names:
                        inline_enums_to_emit.append((enum_cpp_name, enum_obj, fq_enum_name))

        """
        Generate only the declarations (structs, enums, etc.) for a namespace, without includes, pragma once, or namespace wrapper.
        Used to avoid duplicate wrappers in the file-level namespace.
        """
        current_ns_name_raw = ns.name if hasattr(ns, 'name') else None
        ns_name_raw = ns.name if hasattr(ns, 'name') else 'messages'
        if root_namespace is not None:
            ns_name = root_namespace
        else:
            ns_name = self._sanitize_identifier(ns_name_raw)
        decls = []
        # Do NOT reset deduplication sets if provided
        assert emitted_enum_names is not None and emitted_struct_names is not None, "Deduplication sets must be provided from generate_header."
        model = getattr(self, 'model', None)
        enums = []
        messages = []
        if model:
            seen_enum_fqnames = set()
            seen_msg_fqnames = set()
            def fq_msg_name(msg):
                ns = getattr(msg, 'namespace', None)
                ns = ns if ns is not None else ns_name_raw
                return f"{self._sanitize_identifier(ns)}::{self._sanitize_identifier(msg.name)}"
            def fq_enum_name(enum):
                ns = getattr(enum, 'namespace', None)
                ns = ns if ns is not None else ns_name_raw
                cpp_name = self._sanitize_identifier(enum.name if not hasattr(enum, 'cpp_name') else enum.cpp_name)
                cpp_name = cpp_name.split('::')[-1]
                if not cpp_name.endswith('_Enum'):
                    cpp_name += '_Enum'
                return f"{self._sanitize_identifier(ns)}::{cpp_name}"
            def collect_message_recursive(msg):
                fqname = fq_msg_name(msg)
                if fqname in seen_msg_fqnames:
                    return
                messages.append(msg)
                seen_msg_fqnames.add(fqname)
                parent_name = getattr(msg, 'parent', None)
                if parent_name and parent_name in model.messages:
                    collect_message_recursive(model.messages[parent_name])
                for field in getattr(msg, 'fields', []):
                    ref = getattr(field, 'message_reference', None)
                    if ref and ref in model.messages:
                        collect_message_recursive(model.messages[ref])
            def collect_enum_recursive(enum):
                fqname = fq_enum_name(enum)
                if fqname in seen_enum_fqnames:
                    return
                enums.append(enum)
                seen_enum_fqnames.add(fqname)
                parent_name = getattr(enum, 'parent', None)
                if parent_name and parent_name in model.enums:
                    collect_enum_recursive(model.enums[parent_name])
            # Use sanitized namespace for comparison
            sanitized_ns_name_raw = self._sanitize_identifier(ns_name_raw)
            def msg_ns_sanitized(msg):
                ns = getattr(msg, 'namespace', None)
                return self._sanitize_identifier(ns) if ns is not None else None
            def enum_ns_sanitized(enum):
                ns = getattr(enum, 'namespace', None)
                return self._sanitize_identifier(ns) if ns is not None else None

            # --- NEW LOGIC: Collect all enums referenced by fields in this namespace ---
            # First, collect all enums defined in this namespace as before
            # Then, for all messages in this namespace, collect enums referenced by their fields
            # This ensures that enums used as field types are always emitted
            # (even if not top-level in the namespace)
            #
            # 1. Collect all enums defined in this namespace (as before)
            # 2. For each message in this namespace, for each field, if the field references an enum, collect it
            #
            # Step 1: as before (done below in roots/enum_roots)
            # Step 2: after roots/enum_roots, traverse all fields

            # We'll collect additional enums to emit here
            additional_enums = set()
            # Find all messages in this namespace
            all_msgs = [msg for msg in model.messages.values() if msg_ns_sanitized(msg) == sanitized_ns_name_raw]
            for msg in all_msgs:
                for field in getattr(msg, 'fields', []):
                    # Check for enum_reference or enum_type
                    enum_ref = getattr(field, 'enum_reference', None)
                    enum_type = getattr(field, 'enum_type', None)
                    # Check for type string that matches an enum
                    type_name = getattr(field, 'type', None)
                    if enum_ref and enum_ref in model.enums:
                        additional_enums.add(model.enums[enum_ref])
                    elif enum_type and enum_type in model.enums:
                        additional_enums.add(model.enums[enum_type])
                    elif type_name and isinstance(type_name, str) and type_name in model.enums:
                        additional_enums.add(model.enums[type_name])
            # Add these to enum_roots for emission
            # (enum_roots is used below to collect and emit enums)
            # We'll add any not already present
            enum_roots = [enum for enum in model.enums.values() if enum_ns_sanitized(enum) == sanitized_ns_name_raw]
            for enum in additional_enums:
                if enum not in enum_roots:
                    enum_roots.append(enum)
        print(f"[DEBUG] _generate_namespace_decls_only: ns_name_raw={ns_name_raw}, ns_name={ns_name}, sanitized_ns_name_raw={sanitized_ns_name_raw}")
        print(f"[DEBUG] Model messages: {[ (m.name, getattr(m, 'namespace', None)) for m in model.messages.values() ]}")
        print(f"[DEBUG] Model enums: {[ (e.name, getattr(e, 'namespace', None)) for e in model.enums.values() ]}")
        roots = [msg for msg in model.messages.values() if msg_ns_sanitized(msg) == sanitized_ns_name_raw]
        enum_roots = [enum for enum in model.enums.values() if enum_ns_sanitized(enum) == sanitized_ns_name_raw]
        print(f"[DEBUG] Roots for ns '{sanitized_ns_name_raw}': {[m.name for m in roots]}")
        print(f"[DEBUG] Enum roots for ns '{sanitized_ns_name_raw}': {[e.name for e in enum_roots]}")
        for msg in roots:
            collect_message_recursive(msg)
        for enum in enum_roots:
            collect_enum_recursive(enum)

        # Condition to determine if we are generating for the file-level namespace
        # or for a specific named namespace that might be embedded or standalone.
        is_file_level_context = ns_name == getattr(self, 'file_namespace', None)

        if is_file_level_context:
            # PATCH: For file-level header, emit all messages/enums from the main namespace (if any), else fallback to previous logic
            main_ns_obj = None
            if model and hasattr(model, 'namespaces') and model.namespaces:
                # Prefer a namespace matching the sanitized_ns, else use the first
                for ns_candidate in model.namespaces.values():
                    ns_name_candidate = getattr(ns_candidate, 'name', None)
                    if self._sanitize_identifier(ns_name_candidate, for_namespace=True) == ns_name:
                        main_ns_obj = ns_candidate
                        break
                if not main_ns_obj:
                    # Fallback: just use the first namespace
                    main_ns_obj = next(iter(model.namespaces.values()))
            if main_ns_obj:
                # Only emit messages/enums defined in this namespace (not imported)
                ns_name_actual = getattr(main_ns_obj, 'name', None)
                messages_in_ns = [m for m in getattr(main_ns_obj, 'messages', {}).values()
                                  if getattr(m, 'namespace', None) == ns_name_actual]
                enums_in_ns = [e for e in getattr(main_ns_obj, 'enums', {}).values()
                               if getattr(e, 'namespace', None) == ns_name_actual]
            else:
                # Fallback: previous logic (global messages)
                target_sanitized_ns = self._sanitize_identifier(ns_name_raw)
                seen_msg_names = set()
                messages_in_ns = []
                for m in model.messages.values():
                    if self._sanitize_identifier(getattr(m, 'namespace', None)) == target_sanitized_ns:
                        msg_name = self._sanitize_identifier(m.name)
                        if msg_name not in seen_msg_names:
                            messages_in_ns.append(m)
                            seen_msg_names.add(msg_name)
                seen_enum_names = set()
                enums_in_ns = []
                for e in model.enums.values():
                    if self._sanitize_identifier(getattr(e, 'namespace', None)) == target_sanitized_ns:
                        enum_name = self._sanitize_identifier(e.name)
                        if enum_name not in seen_enum_names:
                            enums_in_ns.append(e)
                            seen_enum_names.add(enum_name)
            # Topologically sort messages so base classes come before derived classes
            def topo_sort_messages(msgs):
                name_to_msg = {self._sanitize_identifier(m.name): m for m in msgs}
                visited = set()
                result = []
                def visit(m):
                    name = self._sanitize_identifier(m.name)
                    if name in visited:
                        return
                    parent_name = getattr(m, 'parent', None)
                    if parent_name and parent_name in name_to_msg:
                        visit(name_to_msg[parent_name])
                    visited.add(name)
                    result.append(m)
                for m in msgs:
                    visit(m)
                return result
            messages_in_ns = topo_sort_messages(messages_in_ns)
            # Compound structs
            compound_map = self._collect_compound_fields(messages_in_ns)
            for struct_name, (field, parent_msg) in compound_map.items():
                fq_struct_name = f"{ns_name}::{struct_name}"
                if fq_struct_name not in emitted_struct_names:
                    decls.append(self._generate_compound_struct(struct_name, field, parent_msg, indent="    ", fully_qualify=False, ns_prefix=None))
                    emitted_struct_names.add(fq_struct_name)

            # --- Emit all enums first (from enum_roots) ---
            for enum in enum_roots:
                enum_cpp_name = self._sanitize_identifier(enum.name if not hasattr(enum, 'cpp_name') else enum.cpp_name)
                enum_cpp_name = enum_cpp_name.split('::')[-1]
                if not enum_cpp_name.endswith('_Enum'):
                    enum_cpp_name += '_Enum'
                fq_enum_name = f"{ns_name}::{enum_cpp_name}"
                if fq_enum_name not in emitted_enum_names:
                    decls.append(self._generate_enum_full(enum, indent="    ", fully_qualify=False, ns_prefix=None))
                    emitted_enum_names.add(fq_enum_name)

            # Emit all inline enums as top-level enums (with correct names)
            for enum_cpp_name, enum_obj, fq_enum_name in inline_enums_to_emit:
                if fq_enum_name not in emitted_enum_names:
                    decls.append(self._generate_enum_full(enum_obj, indent="    ", fully_qualify=False, ns_prefix=None, cpp_name_override=enum_cpp_name))
                    emitted_enum_names.add(fq_enum_name)

            # Emit messages
            for msg in messages_in_ns:
                msg_cpp_name = self._sanitize_identifier(msg.name)
                fq_msg_name = f"{ns_name}::{msg_cpp_name}"
                if fq_msg_name not in emitted_struct_names:
                    decls.append(self._generate_message_struct(msg, ns_name, indent="    ", effective_ns=ns_name, fully_qualify=False, ns_prefix=None))
                    emitted_struct_names.add(fq_msg_name)
            return '\n\n'.join(decls)
        else:
            # Namespace-level context: emit messages/enums for this specific namespace (ns_name_raw)
            # This branch is hit when generating a dedicated header for a namespace (e.g. Main_std23.h)
            # or when embedding a namespace's content into the file-level header (e.g. Main's content into mw_main_std23.h)
            
            # Always collect all messages from the model whose namespace matches the current namespace (raw or sanitized)
            if model:
                target_sanitized_ns = self._sanitize_identifier(ns_name_raw)
                messages_in_ns = [m for m in model.messages.values()
                                  if self._sanitize_identifier(getattr(m, 'namespace', None)) == target_sanitized_ns
                                  and getattr(m, 'namespace', None) == ns_name_raw]
                enums_in_ns = [e for e in enums
                               if self._sanitize_identifier(getattr(e, 'namespace', None)) == target_sanitized_ns
                               and getattr(e, 'namespace', None) == ns_name_raw]
            else:
                messages_in_ns = []
                enums_in_ns = []

            # Topologically sort messages so base classes come before derived classes
            def topo_sort_messages(msgs):
                name_to_msg = {fq_msg_name(m): m for m in msgs}
                visited = set()
                result = []
                def visit(m):
                    fqname = fq_msg_name(m)
                    if fqname in visited:
                        return
                    parent_name = getattr(m, 'parent', None)
                    if parent_name:
                        for candidate in name_to_msg.values():
                            if candidate.name == parent_name:
                                visit(candidate)
                    visited.add(fqname)
                    result.append(m)
                for m in msgs:
                    visit(m)
                return result
            messages_in_ns = topo_sort_messages(messages_in_ns)
            compound_map = self._collect_compound_fields(messages_in_ns)
            for struct_name, (field, parent_msg) in compound_map.items():
                fq_struct_name = f"{ns_name}::{struct_name}"
                if fq_struct_name not in emitted_struct_names:
                    decls.append(self._generate_compound_struct(struct_name, field, parent_msg, indent="    "))
                    emitted_struct_names.add(fq_struct_name)
            enums_in_ns = [e for e in enums if enum_ns_sanitized(e) == sanitized_ns_name_raw]
            for enum in enums_in_ns:
                enum_cpp_name = self._sanitize_identifier(enum.name if not hasattr(enum, 'cpp_name') else enum.cpp_name)
                enum_cpp_name = enum_cpp_name.split('::')[-1]
                if not enum_cpp_name.endswith('_Enum'):
                    enum_cpp_name += '_Enum'
                fq_enum_name = f"{ns_name}::{enum_cpp_name}"
                if fq_enum_name not in emitted_enum_names:
                    decls.append(self._generate_enum_full(enum, indent="    "))
                    emitted_enum_names.add(fq_enum_name)
            print(f"[DEBUG] Emitting messages_in_ns for ns '{ns_name}': {[m.name for m in messages_in_ns]}")
            for msg in messages_in_ns:
                msg_cpp_name = self._sanitize_identifier(msg.name)
                msg_ns = self._sanitize_identifier(getattr(msg, 'namespace', None))
                fq_msg_name = f"{msg_ns}::{msg_cpp_name}"
                print(f"[DEBUG] Considering emission: {fq_msg_name}")
                if fq_msg_name not in emitted_struct_names:
                    # Pass import_map as an attribute for use in struct emission
                    self.import_map = import_map
                    print(f"[DEBUG] Emitting struct for: {fq_msg_name}")
                    decls.append(self._generate_message_struct(msg, msg_ns, indent="    ", effective_ns=msg_ns))
                    emitted_struct_names.add(fq_msg_name)
            return '\n\n'.join(decls)
    def _generate_message_struct(self, msg, ns_name, nested_enums=None, indent="    ", effective_ns=None, fully_qualify=False, ns_prefix=None):
        """
        Compatibility wrapper for test and generator code expecting _generate_message_struct.
        Calls _generate_message_struct_with_nested_enums with default empty list for nested_enums if not provided.
        Adds logic to avoid struct/namespace name collision (C++ C2757).
        """
        if nested_enums is None:
            nested_enums = []
        # Check for struct/namespace name collision
        struct_name = self._sanitize_identifier(getattr(msg, 'name', 'Message'))
        ns_name_sanitized = self._sanitize_identifier(ns_name, for_namespace=True)
        # If struct name matches namespace, prefix struct name
        if struct_name == ns_name_sanitized:
            struct_name = f"mw_{struct_name}"
            # Patch the msg object for this emission only, so downstream code uses the new name
            import copy
            msg = copy.copy(msg)
            msg.name = struct_name
        result = self._generate_message_struct_with_nested_enums(
            msg, ns_name, nested_enums, indent=indent, effective_ns=effective_ns,
            fully_qualify=fully_qualify, ns_prefix=ns_prefix
        )
        return result if result is not None else ""
    def _cpp_type(self, field) -> str:
        """
        Enhanced C++ type mapping for C++23 generator.
        Handles enums, references, compound types, arrays, and built-in types, with full namespace/type resolution.
        For arrays, returns std::vector<type>. For optional fields, returns std::optional<type>.
        """
        base_type = getattr(field, 'type', None)
        field_type = getattr(field, 'field_type', None)
        is_array = getattr(field, 'is_array', False)
        is_optional = getattr(field, 'is_optional', False)
        parent_msg = getattr(field, 'parent_message', getattr(field, 'parent', None))
        # Always use the file-level namespace for all generated types
        file_ns = None
        if hasattr(self, 'file_namespace'):
            file_ns = self.file_namespace
        elif hasattr(self, 'model') and hasattr(self.model, 'file_namespace'):
            file_ns = self.model.file_namespace
        # Compound fields: always use the generated struct name, qualified with file-level namespace
        if field_type in ('compound',) or str(field_type) in ('FieldType.COMPOUND', 'compound'):
            msg_name = self._sanitize_identifier(getattr(parent_msg, 'name', parent_msg) if parent_msg else 'Message')
            field_name = self._sanitize_identifier(getattr(field, 'name', 'field'))
            cpp_type = f"{msg_name}_{field_name}_Compound"
            if file_ns:
                cpp_type = f"{file_ns}::{cpp_type}"
        # Enum fields: if field has an 'enum' attribute, use the generated enum type, qualified with file-level namespace
        elif hasattr(field, 'enum') and getattr(field, 'enum', None):
            msg_name = self._sanitize_identifier(getattr(parent_msg, 'name', parent_msg) if parent_msg else 'Message')
            field_name = self._sanitize_identifier(getattr(field, 'name', 'field'))
            cpp_type = f"{msg_name}_{field_name}_Enum"
            if file_ns:
                cpp_type = f"{file_ns}::{cpp_type}"
        # Reference fields: use the referenced type, resolved via _cpp_type_for_type_name, always qualify with file-level namespace if not built-in
        elif field_type in ('reference',) or str(field_type) in ('FieldType.REFERENCE', 'reference'):
            ref_type = getattr(field, 'reference_type', None) or base_type
            cpp_type = self._cpp_type_for_type_name(ref_type, field=field, parent_msg=parent_msg)
            # Only qualify if not a built-in type
            builtins = {"std::string", "int32_t", "float", "bool", "uint8_t", "uint32_t", "int8_t", "uint16_t", "int16_t", "int64_t", "uint64_t", "double"}
            if file_ns and cpp_type not in builtins and '::' not in cpp_type:
                cpp_type = f"{file_ns}::{cpp_type}"
        # All other types: resolve via _cpp_type_for_type_name (handles enums, messages, built-ins, cross-namespace)
        else:
            cpp_type = self._cpp_type_for_type_name(base_type, field=field, parent_msg=parent_msg)
            builtins = {"std::string", "int32_t", "float", "bool", "uint8_t", "uint32_t", "int8_t", "uint16_t", "int16_t", "int64_t", "uint64_t", "double"}
            if file_ns and cpp_type not in builtins and '::' not in cpp_type:
                cpp_type = f"{file_ns}::{cpp_type}"
        # Array handling: use std::vector<type>
        if is_array:
            cpp_type = f"std::vector<{cpp_type}>"
        # Optional handling: use std::optional<type> (C++17+)
        if is_optional:
            cpp_type = f"std::optional<{cpp_type}>"
        return cpp_type
    def _doc_comment(self, comment, indent="    "):
        """
        Format a comment or description as a Doxygen-style C++ comment block.
        Handles multi-line comments and empty/null cases.
        """
        if not comment:
            return ""
        lines = str(comment).strip().splitlines()
        if len(lines) == 1:
            return f"{indent}/** {lines[0].strip()} */"
        doc = [f"{indent}/**"]
        for line in lines:
            doc.append(f"{indent} * {line.rstrip()}")
        doc.append(f"{indent} */")
        return "\n".join(doc)

    def _generate_message_struct_with_nested_enums(self, msg, ns_name, nested_enums, indent="    ", effective_ns=None, fully_qualify=False, ns_prefix=None):
        """
        Generate a C++ struct for a message, including nested enums and doc comments.
        """
        msg_name = getattr(msg, 'name', 'Message')
        doc_comment = getattr(msg, 'comment', None) or getattr(msg, 'description', None)
        doc = self._doc_comment(doc_comment, indent)
        extra_doc_lines = []
        if isinstance(doc_comment, str):
            for line in doc_comment.strip().splitlines():
                if line.strip().startswith('///'):
                    extra_doc_lines.append(f"{indent}{line.strip()}")
        if extra_doc_lines:
            doc = doc + "\n" + "\n".join(extra_doc_lines)
        parent = getattr(msg, 'parent', None)
        base = ""
        if parent:
            model = getattr(self, 'model', None)
            parent_obj = None
            parent_ns = None
            # Try to resolve parent with namespace if not found
            if model and hasattr(model, 'messages') and parent in model.messages:
                parent_obj = model.messages[parent]
                parent_ns = getattr(parent_obj, 'namespace', None)
            elif '::' in parent:
                ns_alias, unqualified = parent.split('::', 1)
                if model and hasattr(model, 'namespaces') and ns_alias in model.namespaces:
                    ns_obj = model.namespaces[ns_alias]
                    if hasattr(ns_obj, 'messages') and unqualified in ns_obj.messages:
                        parent_obj = ns_obj.messages[unqualified]
                        parent_ns = ns_alias
            # Always fully qualify base class if it is cross-namespace or imported
            if parent_obj:
                # If the parent is in a different namespace, always qualify using the import alias if available
                if getattr(parent_obj, 'namespace', None) and getattr(parent_obj, 'namespace', None) != ns_name:
                    import_map = getattr(self, 'import_map', None)
                    ns_alias = None
                    if import_map:
                        # Prefer alias if present, else use sanitized namespace name
                        for alias, imported_base in import_map.items():
                            if self._sanitize_identifier(imported_base) == self._sanitize_identifier(parent_obj.namespace):
                                ns_alias = self._sanitize_identifier(alias)
                                break
                    if ns_alias:
                        base = f" : public {ns_alias}::{self._sanitize_identifier(parent_obj.name)}"
                    else:
                        base = f" : public {self._sanitize_identifier(parent_obj.namespace)}::{self._sanitize_identifier(parent_obj.name)}"
                else:
                    base = f" : public {self._sanitize_identifier(parent_obj.name)}"
            elif parent and '::' in parent:
                ns_alias, unqualified = parent.split('::', 1)
                import_map = getattr(self, 'import_map', None)
                ns_alias_sanitized = None
                if import_map and ns_alias in import_map:
                    ns_alias_sanitized = self._sanitize_identifier(ns_alias)
                else:
                    ns_alias_sanitized = self._sanitize_identifier(ns_alias)
                base = f" : public {ns_alias_sanitized}::{self._sanitize_identifier(unqualified)}"
            else:
                base = f" : public {self._sanitize_identifier(parent)}"
        struct_name = self._sanitize_identifier(msg_name)
        # Always use unqualified name for struct declaration inside the namespace
        struct_lines = [f"{doc}\n{indent}struct {struct_name}{base}\n{indent}{{"]
        has_fields = False
        for field in getattr(msg, 'fields', []):
            has_fields = True
            field_comment = getattr(field, 'comment', None) or getattr(field, 'description', None)
            field_doc = self._doc_comment(field_comment, indent + "    ")
            extra_field_doc_lines = []
            if isinstance(field_comment, str):
                for line in field_comment.strip().splitlines():
                    if line.strip().startswith('///'):
                        extra_field_doc_lines.append(f"{indent}    {line.strip()}")
            if extra_field_doc_lines:
                field_doc = field_doc + "\n" + "\n".join(extra_field_doc_lines)
            field_type = self._cpp_field_type(field, msg, effective_ns=ns_prefix if fully_qualify and ns_prefix else (effective_ns or ns_name))
            field_name = self._sanitize_identifier(getattr(field, 'name', 'field'))
            struct_lines.append(f"{field_doc}\n{indent}    {field_type} {field_name};")
        for enum in nested_enums:
            struct_lines.append(self._generate_enum_full(enum, indent=indent + "    ", fully_qualify=fully_qualify, ns_prefix=ns_prefix))
        if not has_fields and not nested_enums:
            struct_lines.append(f"{indent}    // (no fields)")
        struct_lines.append(f"{indent}}};")
        return "\n".join([line for line in struct_lines if line.strip()])
    def _collect_compound_fields(self, messages):
        """
        Collect all unique compound fields from all messages.
        Returns a dict mapping compound struct name to (field, parent_msg).
        """
        compounds = {}
        for msg in messages:
            for field in getattr(msg, 'fields', []):
                if getattr(field, 'field_type', None) in ('compound',) or str(getattr(field, 'field_type', None)) in ('FieldType.COMPOUND', 'compound'):
                    msg_name = getattr(msg, 'name', 'Message')
                    field_name = getattr(field, 'name', 'field')
                    struct_name = f"{self._sanitize_identifier(msg_name)}_{self._sanitize_identifier(field_name)}_Compound"
                    compounds[struct_name] = (field, msg)
        return compounds

    def _generate_compound_struct(self, struct_name, field, parent_msg, indent="    ", fully_qualify=False, ns_prefix=None):
        """
        Generate a C++ struct for a compound field.
        """
        doc = self._doc_comment(getattr(field, 'comment', None) or getattr(field, 'description', None), indent)
        # Compound components: field.compound_components, field.compound_base_type
        base_type = getattr(field, 'compound_base_type', 'float')
        components = getattr(field, 'compound_components', [])
        # Map base_type to C++ type
        cpp_type = {
            'float': 'float',
            'int': 'int32_t',
            'uint': 'uint32_t',
            'bool': 'bool',
            'byte': 'uint8_t',
            'string': 'std::string',
        }.get(base_type, base_type)
        fields = []
        for comp in components:
            fields.append(f"{indent}    {cpp_type} {self._sanitize_identifier(comp)};")
        fields_str = '\n'.join(fields)
        # Always use unqualified name for struct declaration inside the namespace
        name = struct_name
        result = f"{doc}\n{indent}struct {name}\n{indent}{{\n{fields_str}\n{indent}}};"
        return result if result is not None else ""
    def __init__(self, namespaces, options=None, model=None):
        super().__init__(namespaces, options)
        # Store the model if provided, so we can always find all enums/messages for a namespace
        self.model = model


    def generate_header(self, root_namespace=None, write_to_disk=True, _already_loaded=None):
        """
        Recursively generate C++23 headers for the main model and all imported models.
        Returns a dict mapping header filenames to their content.
        """
        if _already_loaded is None:
            _already_loaded = set()
        model = getattr(self, 'model', None)
        def_path = getattr(model, 'main_file_path', None) if model else None
        headers = {}
        if model is not None:
            model_id = id(model)
            if model_id in _already_loaded:
                return {}
            _already_loaded.add(model_id)

        # --- RECURSIVELY GENERATE IMPORTED HEADERS FIRST ---
        import_map = {}
        if model and hasattr(model, 'imports') and model.imports:
            import os
            from def_file_loader import build_model_from_file_recursive
            for imported_ns, imported_path in model.imports.items():
                imported_base = os.path.splitext(os.path.basename(imported_path))[0]
                import_map[imported_ns] = imported_base
                imported_model = build_model_from_file_recursive(imported_path)
                imported_model.main_file_path = imported_path
                imported_gen = CppGeneratorStd23([imported_model], model=imported_model)
                imported_headers = imported_gen.generate_header(_already_loaded=_already_loaded)
                headers.update(imported_headers)

        # --- GENERATE ONE HEADER PER NAMESPACE ---
        emitted_enum_names = set()
        emitted_struct_names = set()
        cpp_reserved = {"main", "namespace", "class", "struct", "enum", "union", "template", "typename", "public", "private", "protected", "virtual", "inline", "static", "const", "volatile", "mutable", "explicit", "friend", "operator", "this", "true", "false", "nullptr", "new", "delete", "default", "override", "final", "import", "export", "module", "requires", "co_await", "co_return", "co_yield"}
        includes = "#include <string>\n#include <vector>\n#include <map>\n#include <memory>\n#include <cstdint>"

        if model and hasattr(model, 'namespaces') and model.namespaces:
            import os
            # Use the .def file base name for the header filename
            if def_path:
                file_base = os.path.splitext(os.path.basename(def_path))[0]
                file_sanitized = self._sanitize_identifier(file_base, for_namespace=True)
                ns_filename = f"{file_sanitized}_std23.h"
                # If there is only one namespace, use it; otherwise, merge all into one header, each wrapped in its own namespace
                ns_content = ""
                for ns in model.namespaces.values():
                    ns_name = self._sanitize_identifier(getattr(ns, 'name', None), for_namespace=True)
                    inner_content = self._generate_namespace_header_full(
                        ns,
                        def_path=def_path,
                        header_filename=ns_filename,
                        base_filename=file_sanitized,
                        import_map=import_map,
                        root_namespace=getattr(ns, 'name', None),
                        emitted_enum_names=emitted_enum_names,
                        emitted_struct_names=emitted_struct_names
                    )
                    # Only emit the namespace block if it is non-empty (not just whitespace)
                    if inner_content and inner_content.strip():
                        ns_content += f"namespace {ns_name} {{\n" + inner_content + f"\n}} // namespace {ns_name}\n"
                if ns_content.strip():
                    include_directives = ""
                    alias_directives = ""
                    already_included = set()
                    if import_map:
                        for alias, imported_base in import_map.items():
                            inc = f"{imported_base}_std23.h"
                            if inc not in already_included:
                                include_directives += f"#include \"{inc}\"\n"
                                already_included.add(inc)
                    for inc in sorted(getattr(self, '_last_needed_headers', set())):
                        if inc not in already_included:
                            include_directives += f"#include \"{inc}\"\n"
                            already_included.add(inc)
                    if import_map:
                        for alias, imported_base in import_map.items():
                            imported_ns = self._sanitize_identifier(imported_base)
                            alias_ns = self._sanitize_identifier(alias)
                            if imported_ns in cpp_reserved:
                                imported_ns = f"ns_{imported_ns}"
                            if alias_ns != imported_ns:
                                alias_directives += f"namespace {alias_ns} = {imported_ns};\n"
                        if alias_directives:
                            include_directives += alias_directives + "\n"
                    def_comment = f"// Source .def file: {def_path}" if def_path else "// Source .def file: (unknown)"
                    header = f"// Auto-generated C++23 header for file {file_sanitized}\n{def_comment}\n#pragma once\n\n{includes}\n\n{include_directives}"
                    content = header + ns_content
                    headers[ns_filename] = content

        # Assert that no generated header is named messages_*.h (indicates lost filename)
        for header_name in headers:
            assert not header_name.startswith("messages_") and not header_name == "messages_std23.h", (
                f"Invalid generated header filename: {header_name}. This indicates the filename was lost. "
                f"All generated headers must be named after the .def file or imported namespace.")
        return headers

    def _strip_namespace_wrapper(self, content, ns_name):
        """
        Remove the outermost namespace {ns_name} {{ ... }} wrapper from content, preserving inner content.
        """
        import re
        if not content:
            return ""
        if not ns_name:
            return content
        # Match 'namespace ns_name { ... }' and extract the body
        pattern = re.compile(rf"namespace\s+{re.escape(str(ns_name))}\s*\{{(.*)\}}\s*//\s*namespace\s+{re.escape(str(ns_name))}\s*", re.DOTALL)
        m = pattern.search(content)
        if m:
            return m.group(1).strip()
        # Fallback: try to find the first opening and last closing brace
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            return content[start+1:end].strip()
        return content

    def generate_source(self, root_namespace=None):
        """
        Generate C++23 source (.cpp) files for all namespaces in the model.
        For C++23, since we're using header-only implementation, this method returns an empty dict.
        """
        return {}  # Empty dict since C++23 implementation is header-only

    def _generate_namespace_header_full(self, ns, def_path=None, header_filename=None, base_filename=None, import_map=None, root_namespace=None, emitted_enum_names=None, emitted_struct_names=None) -> str:
        assert emitted_enum_names is not None and emitted_struct_names is not None, "Deduplication sets must be provided from generate_header."
        ns_name = root_namespace if root_namespace is not None else self._sanitize_identifier(getattr(ns, 'name', None))
        decls = []
        ns_doc = getattr(ns, 'comment', None) or getattr(ns, 'description', None)
        if ns_doc:
            decls.append(self._doc_comment(ns_doc, indent=""))

        # Only emit messages/enums defined in the current model's .def file (not imported)
        model = getattr(self, 'model', None)
        model_file = getattr(model, 'main_file_path', None) if model else None
        def is_defined_here(obj):
            obj_file = getattr(obj, 'source_file', None)
            # Normalize paths for comparison (case-insensitive, absolute, slashes)
            if obj_file and model_file:
                obj_file_norm = os.path.normcase(os.path.abspath(obj_file))
                model_file_norm = os.path.normcase(os.path.abspath(model_file))
                return obj_file_norm == model_file_norm
            return obj_file == model_file

        # Recursively collect all enums and messages defined in this .def file from this namespace and all sub-namespaces
        def collect_defined_enums(ns):
            enums = []
            if hasattr(ns, 'enums'):
                enums.extend([e for e in ns.enums.values() if is_defined_here(e)])
            if hasattr(ns, 'namespaces'):
                for subns in ns.namespaces.values():
                    enums.extend(collect_defined_enums(subns))
            return enums

        def collect_defined_messages(ns):
            messages = []
            if hasattr(ns, 'messages'):
                messages.extend([m for m in ns.messages.values() if is_defined_here(m)])
            if hasattr(ns, 'namespaces'):
                for subns in ns.namespaces.values():
                    messages.extend(collect_defined_messages(subns))
            return messages

        enums = collect_defined_enums(ns)
        messages = collect_defined_messages(ns)

        # Sort for deterministic output
        enums.sort(key=lambda e: e.name)
        messages.sort(key=lambda m: m.name)


        # Emit enums defined in this namespace
        for enum in enums:
            enum_cpp_name = self._sanitize_identifier(enum.name if not hasattr(enum, 'cpp_name') else enum.cpp_name)
            enum_cpp_name = enum_cpp_name.split('::')[-1]
            if not enum_cpp_name.endswith('_Enum'):
                enum_cpp_name += '_Enum'
            fq_enum_name = f"{ns_name}::{enum_cpp_name}"
            if fq_enum_name not in emitted_enum_names:
                decls.append(self._generate_enum_full(enum, indent="    ", fully_qualify=True, ns_prefix=ns_name))
                emitted_enum_names.add(fq_enum_name)

        # --- Emit enums referenced by message fields (even if not top-level in ns.enums) ---
        # Collect all enums referenced by fields in this namespace's messages
        referenced_enums = set()
        def collect_field_enums(msg):
            for field in getattr(msg, 'fields', []):
                # If the field has an enum reference, add it
                enum_obj = getattr(field, 'enum', None)
                if enum_obj is not None:
                    referenced_enums.add(enum_obj)
        for msg in messages:
            collect_field_enums(msg)
        # Emit any referenced enums not already emitted
        for enum in referenced_enums:
            enum_cpp_name = self._sanitize_identifier(enum.name if not hasattr(enum, 'cpp_name') else enum.cpp_name)
            enum_cpp_name = enum_cpp_name.split('::')[-1]
            if not enum_cpp_name.endswith('_Enum'):
                enum_cpp_name += '_Enum'
            fq_enum_name = f"{ns_name}::{enum_cpp_name}"
            if fq_enum_name not in emitted_enum_names:
                decls.append(self._generate_enum_full(enum, indent="    ", fully_qualify=True, ns_prefix=ns_name))
                emitted_enum_names.add(fq_enum_name)

        # Topologically sort messages so base classes come before derived classes
        def topo_sort_messages(msgs):
            name_to_msg = {self._sanitize_identifier(m.name): m for m in msgs}
            visited = set()
            result = []
            def visit(m):
                name = self._sanitize_identifier(m.name)
                if name in visited:
                    return
                parent_name = getattr(m, 'parent', None)
                if parent_name and parent_name in name_to_msg:
                    visit(name_to_msg[parent_name])
                visited.add(name)
                result.append(m)
            for m in msgs:
                visit(m)
            return result
        messages_sorted = topo_sort_messages(messages)
        for msg in messages_sorted:
            msg_cpp_name = self._sanitize_identifier(msg.name)
            msg_ns = self._sanitize_identifier(getattr(msg, 'namespace', None))
            fq_msg_name = f"{msg_ns}::{msg_cpp_name}"
            if fq_msg_name not in emitted_struct_names:
                self.import_map = import_map
                decls.append(self._generate_message_struct(msg, ns_name, indent="    ", effective_ns=ns_name, fully_qualify=True, ns_prefix=ns_name))
                emitted_struct_names.add(fq_msg_name)

        return "\n\n".join(decls)

    def _is_imported_message(self, msg, import_map, ns_name_raw, ns_name):
        """
        Return True if the message is from an imported namespace (not the current one).
        """
        msg_ns = getattr(msg, 'namespace', None)
        if not msg_ns:
            return False
        # If the namespace is not the current one, and is in import_map or is a sanitized import, it's imported
        if msg_ns != ns_name_raw and self._sanitize_identifier(msg_ns) != ns_name:
            if import_map:
                for alias, imported_base in import_map.items():
                    if self._sanitize_identifier(imported_base) == self._sanitize_identifier(msg_ns) or self._sanitize_identifier(alias) == self._sanitize_identifier(msg_ns):
                        return True
            return True
        return False

        # Topologically sort messages so base classes come before derived classes
        def topo_sort_messages(msgs):
            # Use fully qualified name for deduplication
            name_to_msg = {fq_msg_name(m): m for m in msgs}
            visited = set()
            result = []
            def visit(m):
                fqname = fq_msg_name(m)
                if fqname in visited:
                    return
                parent_name = getattr(m, 'parent', None)
                if parent_name:
                    # Try to find parent by unqualified name
                    for candidate_fqname, candidate in name_to_msg.items():
                        if candidate.name == parent_name:
                            visit(candidate)
                visited.add(fqname)
                result.append(m)
            for fqname, m in name_to_msg.items():
                visit(m)
            return result
        messages_in_ns = topo_sort_messages(messages_in_ns)

        # DEBUG: Print collected messages and enums
        print(f"[DEBUG GENERATOR] Emitting messages for {ns_name}: {[m.name for m in messages_in_ns]}")
        print(f"[DEBUG GENERATOR] Emitting enums for {ns_name}: {[e.name for e in enums]}")
        for m in messages_in_ns:
            print(f"[DEBUG GENERATOR] Message in ns: name={m.name}, namespace={getattr(m, 'namespace', None)}, parent={getattr(m, 'parent', None)}")



        # --- Emit includes for explicit imports and for all header dependencies (base classes, field types) ---
        needed_headers = set()
        # 1. Explicit imports (as before)
        if import_map:
            for alias, imported_base in import_map.items():
                inc = f"{imported_base}_std23.h"
                needed_headers.add(inc)
        # 2. Scan all messages for base classes and field types that require includes (always include for cross-namespace references)
        def header_for_ns(ns):
            if not ns:
                return None
            sanitized = self._sanitize_identifier(ns)
            return f"{sanitized}_std23.h"

        # Collect all valid namespaces for which we can generate headers
        valid_namespaces = set()
        if model and hasattr(model, 'namespaces'):
            valid_namespaces.update(self._sanitize_identifier(n) for n in model.namespaces.keys())
        # Also add imported namespaces (aliases)
        if import_map:
            valid_namespaces.update(self._sanitize_identifier(alias) for alias in import_map.keys())
            valid_namespaces.update(self._sanitize_identifier(base) for base in import_map.values())
        # Never emit includes for these built-in or standard namespaces
        builtin_namespaces = {"std", "cstdint", "string", "vector", "map", "memory", "int32_t", "uint8_t", "uint32_t", "int8_t", "uint16_t", "int16_t", "int64_t", "uint64_t", "double", "float", "bool"}

        for msg in messages_in_ns:
            # Base class
            parent = getattr(msg, 'parent', None)
            if parent:
                parent_ns = None
                if '::' in parent:
                    parent_ns = parent.split('::')[0]
                else:
                    if model and hasattr(model, 'messages') and parent in model.messages:
                        parent_obj = model.messages[parent]
                        parent_ns = getattr(parent_obj, 'namespace', None)
                # Always include if parent_ns is different and valid
                if parent_ns and parent_ns != ns_name:
                    sanitized_parent_ns = self._sanitize_identifier(parent_ns)
                    if sanitized_parent_ns in valid_namespaces and sanitized_parent_ns not in builtin_namespaces:
                        inc = header_for_ns(parent_ns)
                        if inc and inc != header_filename:
                            needed_headers.add(inc)
            # Field types
            for field in getattr(msg, 'fields', []):
                t = self._cpp_field_type(field, msg, effective_ns=ns_name)
                if '::' in t:
                    ns_part = t.split('::')[0]
                    sanitized_ns_part = self._sanitize_identifier(ns_part)
                    if sanitized_ns_part != ns_name and sanitized_ns_part in valid_namespaces and sanitized_ns_part not in builtin_namespaces:
                        inc = header_for_ns(ns_part)
                        if inc and inc != header_filename:
                            needed_headers.add(inc)
        # Remove self-include
        if header_filename:
            needed_headers.discard(header_filename)
        self._last_needed_headers = needed_headers


        # Emit compound structs first (for messages in this namespace or global)
        compound_map = self._collect_compound_fields(messages_in_ns)
        for struct_name, (field, parent_msg) in compound_map.items():
            fq_struct_name = f"{ns_name}::{struct_name}"
            if fq_struct_name not in emitted_struct_names:
                decls.append(self._generate_compound_struct(struct_name, field, parent_msg, indent="    "))
                emitted_struct_names.add(fq_struct_name)
                
        # Then enums (all enums in the model for this namespace or global)
        # PATCH: Define is_file_level based on context
        is_file_level = ns_name_raw is None or ns_name_raw.lower() in ("messages", "global", "") or ns_name.startswith("mw_")
        if is_file_level:
            enums_in_ns = [e for e in enums if not getattr(e, 'namespace', None) or getattr(e, 'namespace', None) == ns_name or getattr(e, 'namespace', None) == sanitized_ns]
        else:
            enums_in_ns = [e for e in enums if getattr(e, 'namespace', None) == ns_name_raw or getattr(e, 'namespace', None) == ns_name]
        for enum in enums_in_ns:
            enum_cpp_name = self._sanitize_identifier(enum.name if not hasattr(enum, 'cpp_name') else enum.cpp_name)
            enum_cpp_name = enum_cpp_name.split('::')[-1]
            if not enum_cpp_name.endswith('_Enum'):
                enum_cpp_name += '_Enum'
            fq_enum_name = f"{ns_name}::{enum_cpp_name}"
            if fq_enum_name not in emitted_enum_names:
                decls.append(self._generate_enum_full(enum, indent="    "))
                emitted_enum_names.add(fq_enum_name)
                
        # Then messages (all messages in this namespace or global)
        for msg in messages_in_ns:
            msg_cpp_name = self._sanitize_identifier(msg.name)
            msg_ns = self._sanitize_identifier(getattr(msg, 'namespace', None))
            fq_msg_name = f"{msg_ns}::{msg_cpp_name}"
            if fq_msg_name not in emitted_struct_names:
                # Pass import_map as an attribute for use in struct emission
                self.import_map = import_map
                decls.append(self._generate_message_struct(msg, msg_ns, indent="    ", effective_ns=msg_ns))
                emitted_struct_names.add(fq_msg_name)
                
        # Ensure messages_in_ns and enums_in_ns are always defined for comments/footer
        if 'messages_in_ns' not in locals():
            messages_in_ns = []
        if 'enums_in_ns' not in locals():
            enums_in_ns = []
        decls_str = '\n\n'.join(decls)
        msg_comment = f"// Messages: {', '.join(sorted([m.name for m in messages_in_ns]))}" if messages_in_ns else "// Messages: (none)"
        enum_comment = f"// Enums: {', '.join(sorted([e.name for e in enums_in_ns]))}" if enums_in_ns else "// Enums: (none)"
        def_comment = f"// Source .def file: {def_path}" if def_path else "// Source .def file: (unknown)"
        # Patch: define includes as in generate_header
        includes = "#include <string>\n#include <vector>\n#include <map>\n#include <memory>\n#include <cstdint>"
        if hasattr(self, '_last_needed_headers') and self._last_needed_headers:
            for inc in sorted(self._last_needed_headers):
                includes += f"\n#include \"{inc}\""
        return f"// Auto-generated C++23 header for namespace {ns_name}\n{def_comment}\n#pragma once\n\n{includes}\n\nnamespace {ns_name} {{\n{decls_str}\n}} // namespace {ns_name}\n"

    def _generate_namespace_source(self, ns, def_path=None):
        ns_name_raw = ns.name if hasattr(ns, 'name') else 'messages'
        ns_name = self._sanitize_identifier(ns_name_raw)
        model = getattr(self, 'model', None)
        enums = []
        messages = []
        if model:
            seen_enum_names = set()
            seen_msg_names = set()

            def collect_message_recursive(msg):
                if msg.name in seen_msg_names:
                    return
                messages.append(msg)
                seen_msg_names.add(msg.name)
                parent_name = getattr(msg, 'parent', None)
                if parent_name and parent_name in model.messages:
                    collect_message_recursive(model.messages[parent_name])
                for field in getattr(msg, 'fields', []):
                    ref = getattr(field, 'message_reference', None)
                    if ref and ref in model.messages:
                        collect_message_recursive(model.messages[ref])
                    enum_ref = getattr(field, 'enum_reference', None)
                    if enum_ref and enum_ref in model.enums:
                        collect_enum_recursive(model.enums[enum_ref])

            def collect_enum_recursive(enum):
                if enum.name in seen_enum_names:
                    return
                enums.append(enum)
                seen_enum_names.add(enum.name)
                parent_name = getattr(enum, 'parent', None)
                if parent_name and parent_name in model.enums:
                    collect_enum_recursive(model.enums[parent_name])

            # Phase 1: collect all roots in this namespace
            roots = [msg for msg in model.messages.values() if getattr(msg, 'namespace', None) == ns_name_raw]
            enum_roots = [enum for enum in model.enums.values() if getattr(enum, 'namespace', None) == ns_name_raw]

            # Phase 2: recursively collect all reachable messages/enums
            for msg in roots:
                collect_message_recursive(msg)
            for enum in enum_roots:
                collect_enum_recursive(enum)

            # Also add any directly attached to the namespace object (for compatibility)
            for enum in getattr(ns, 'enums', {}).values():
                if enum.name not in {e.name for e in enums}:
                    enums.append(enum)
            for msg in getattr(ns, 'messages', {}).values():
                if msg.name not in {m.name for m in messages}:
                    messages.append(msg)

        # DEBUG OUTPUT: Print what will be emitted for this namespace
        print(f"[GENERATOR DEBUG] Namespace: {ns_name}")
        print(f"[GENERATOR DEBUG] Enums: {[e.name for e in enums]}")
        print(f"[GENERATOR DEBUG] Messages: {[m.name for m in messages]}")
        for msg in messages:
            print(f"[GENERATOR DEBUG] Message '{msg.name}' doc: {getattr(msg, 'comment', None) or getattr(msg, 'description', None)}")
            for field in getattr(msg, 'fields', []):
                print(f"[GENERATOR DEBUG]   Field '{field.name}' doc: {getattr(field, 'comment', None) or getattr(field, 'description', None)}")
        for enum in enums:
            print(f"[GENERATOR DEBUG] Enum '{enum.name}' doc: {getattr(enum, 'comment', None) or getattr(enum, 'description', None)}")

        # Sort by name for deterministic output
        enums.sort(key=lambda e: e.name)
        messages.sort(key=lambda m: m.name)

        # Emit all enums/messages for this namespace: include both recursively collected and directly attached
        # (Move emission block after messages_in_ns is defined and sorted)
        decls = []
        target_sanitized_ns = self._sanitize_identifier(ns_name)
        # Enums: union of enums_in_ns and ns.enums.values()
        enums_in_ns = [e for e in enums if self._sanitize_identifier(getattr(e, 'namespace', None)) == target_sanitized_ns]
        direct_enums = [e for e in getattr(ns, 'enums', {}).values() if self._sanitize_identifier(getattr(e, 'namespace', None)) == target_sanitized_ns]
        all_enums_to_emit = {e.name: e for e in enums_in_ns + direct_enums}.values()

        # Messages: union of messages_in_ns and ns.messages.values()
        messages_in_ns = [m for m in messages if self._sanitize_identifier(getattr(m, 'namespace', None)) == target_sanitized_ns]
        direct_msgs = [m for m in getattr(ns, 'messages', {}).values() if self._sanitize_identifier(getattr(m, 'namespace', None)) == target_sanitized_ns]
        all_msgs_to_emit = {m.name: m for m in list(messages_in_ns) + direct_msgs}.values()
        for enum in all_enums_to_emit:
            decls.append(self._generate_enum_full(enum, indent="    "))
        for msg in all_msgs_to_emit:
            decls.append(self._generate_message_struct(msg, ns_name, indent="    "))
        decls_str = '\n\n'.join(decls)

        msg_comment = f"// Messages: {', '.join(sorted([m.name for m in all_msgs_to_emit]))}" if all_msgs_to_emit else "// Messages: (none)"
        enum_comment = f"// Enums: {', '.join(sorted([e.name for e in all_enums_to_emit]))}" if all_enums_to_emit else "// Enums: (none)"
        def_comment = f"// Source .def file: {def_path}" if def_path else "// Source .def file: (unknown)"
        return f"// Auto-generated C++23 header for namespace {ns_name}\n{def_comment}\n#pragma once\n\nnamespace {ns_name} {{\n{decls_str}\n}} // namespace {ns_name}\n"

    def _cpp_field_type(self, field, parent_msg, effective_ns=None):
        """
        Generate the C++ type for a field in a message, with correct enum field naming.
        This handles nested enum references correctly, ensuring we don't duplicate the _Enum suffix.
        """
        model = getattr(self, 'model', None)
        
        # Handle arrays
        if getattr(field, 'is_array', False):
            import copy
            elem_field = copy.copy(field)
            elem_field.is_array = False
            elem_type = self._cpp_field_type(elem_field, parent_msg, effective_ns=effective_ns)
            return f"std::vector<{elem_type}>"
        
        # Handle maps
        if getattr(field, 'is_map', False):
            key_type = 'std::string'
            value_type = 'int32_t'
            
            if hasattr(field, 'map_key_type') and field.map_key_type is not None:
                # map_key_type may be a Field or a type string
                if isinstance(field.map_key_type, str):
                    key_type = self._cpp_type_for_type_name(field.map_key_type)
                else:
                    key_type = self._cpp_field_type(field.map_key_type, parent_msg, effective_ns=effective_ns)
                    
            if hasattr(field, 'map_value_type') and field.map_value_type is not None:
                if isinstance(field.map_value_type, str):
                    value_type = self._cpp_type_for_type_name(field.map_value_type)
                else:
                    value_type = self._cpp_field_type(field.map_value_type, parent_msg, effective_ns=effective_ns)
                    
            return f"std::map<{key_type}, {value_type}>"
        
        # Handle compound fields
        if getattr(field, 'field_type', None) in ('compound',) or str(getattr(field, 'field_type', None)) in ('FieldType.COMPOUND', 'compound'):
            # Always use the message name where the field is defined (parent_msg)
            msg_name = getattr(parent_msg, 'name', 'Message')
            field_name = getattr(field, 'name', 'field')
            return f"{self._sanitize_identifier(msg_name)}_{self._sanitize_identifier(field_name)}_Compound"
        
        # Handle enums (inline or reference):
        if getattr(field, 'field_type', None) in ('enum',) or str(getattr(field, 'field_type', None)) in ('FieldType.ENUM', 'enum') or getattr(field, 'enum_reference', None):
            # If this is a reference to an enum in another message, use that message's name
            enum_type = getattr(field, 'enum_type', None) or getattr(field, 'enum_reference', None)
            if enum_type and ('::' in enum_type or '.' in enum_type):
                # enum_type is like 'EnumContainer::status_Enum' or 'EnumContainer.status_Enum'
                # Accept both separators
                for sep in ('::', '.'):  # prefer '::' if present
                    if sep in enum_type:
                        parts = enum_type.split(sep)
                        msg_name = parts[0]
                        field_part = sep.join(parts[1:])
                        # Remove trailing _Enum if present in field_part
                        if field_part.endswith('_Enum'):
                            field_part = field_part[:-5]
                        return f"{self._sanitize_identifier(msg_name)}_{self._sanitize_identifier(field_part)}_Enum"
            # Otherwise, use parent_msg (inline enum)
            msg_name = getattr(parent_msg, 'name', 'Message')
            field_name = getattr(field, 'name', 'field')
            return f"{self._sanitize_identifier(msg_name)}_{self._sanitize_identifier(field_name)}_Enum"
        
        # Handle options fields (always uint32_t)
        if getattr(field, 'field_type', None) in ('options',) or str(getattr(field, 'field_type', None)) in ('FieldType.OPTIONS', 'options') or getattr(field, 'is_options', False):
            return 'uint32_t'
        
        # Handle message references
        if getattr(field, 'field_type', None) in ('message_reference',) or str(getattr(field, 'field_type', None)) in ('FieldType.MESSAGE_REFERENCE', 'message_reference') or getattr(field, 'message_reference', None):
            msg_ref = getattr(field, 'message_reference', None)
            if msg_ref and model and hasattr(model, 'messages'):
                msg_obj = model.messages.get(msg_ref)
                if msg_obj:
                    msg_ns = getattr(msg_obj, 'namespace', None)
                    # Use unqualified name if in the same namespace as the parent message, else qualified
                    current_ns = getattr(parent_msg, 'namespace', None) if parent_msg and hasattr(parent_msg, 'namespace') else getattr(field, 'namespace', None)
                    msg_name = self._sanitize_identifier(msg_obj.name)
                    # Use effective_ns for all qualified names in this header
                    if effective_ns is not None:
                        if msg_ns == effective_ns or msg_ns == current_ns:
                            return msg_name
                        else:
                            return f"{self._sanitize_identifier(msg_ns)}::{msg_name}"
                    else:
                        if msg_ns == current_ns:
                            return msg_name
                        else:
                            return f"{self._sanitize_identifier(msg_ns)}::{msg_name}" if msg_ns else msg_name
            
            # Fallback: use type name
            if getattr(field, 'type', None):
                return self._sanitize_identifier(str(field.type))
                
            return 'unknown_type'  # fallback
        
        # Handle all basic types
        field_type = getattr(field, 'field_type', None)
        if hasattr(field_type, 'value'):
            field_type_str = field_type.value
        else:
            field_type_str = str(field_type) if field_type else None
            
        fieldtype_to_cpp = {
            'string': 'std::string',
            'int': 'int32_t',
            'float': 'float',
            'bool': 'bool',
            'boolean': 'bool',
            'byte': 'uint8_t',
        }
        
        if field_type_str in fieldtype_to_cpp:
            return fieldtype_to_cpp[field_type_str]
        
        # Try to resolve user-defined types by name (for enums, options, messages)
        type_name = getattr(field, 'type', None)
        if isinstance(type_name, str):
            # Check enums
            if model and hasattr(model, 'enums') and type_name in model.enums:
                enum_obj = model.enums[type_name]
                enum_ns = getattr(enum_obj, 'namespace', None)
                current_ns = getattr(parent_msg, 'namespace', None) if parent_msg and hasattr(parent_msg, 'namespace') else getattr(field, 'namespace', None)
                
                raw_name = enum_obj.name
                sanitized_name = self._sanitize_identifier(raw_name)
                # Avoid duplicating the _Enum suffix
                enum_name = sanitized_name if sanitized_name.endswith("_Enum") else sanitized_name + "_Enum"
                
                if effective_ns is not None:
                    if enum_ns == effective_ns or enum_ns == current_ns:
                        return enum_name
                    else:
                        return f"{self._sanitize_identifier(enum_ns)}::{enum_name}" if enum_ns else enum_name
                else:
                    return enum_name
                
            # Check messages
            if model and hasattr(model, 'messages') and type_name in model.messages:
                msg_obj = model.messages[type_name]
                msg_ns = getattr(msg_obj, 'namespace', None)
                msg_name = self._sanitize_identifier(msg_obj.name)
                if effective_ns is not None:
                    if msg_ns == effective_ns or msg_ns == current_ns:
                        return msg_name
                    else:
                        return f"{self._sanitize_identifier(msg_ns)}::{msg_name}" if msg_ns else msg_name
                else:
                    return msg_name
            # Check options
            if model and hasattr(model, 'options') and type_name in model.options:
                return 'uint32_t'
        
        # Fallback: in a closed type system, this should never happen
        raise RuntimeError(f"[CppGeneratorStd23] Could not resolve C++ type for field '{getattr(field, 'name', None)}' in message '{getattr(parent_msg, 'name', None)}' (type='{getattr(field, 'type', None)}', field_type='{getattr(field, 'field_type', None)}')")

    def _cpp_type_for_type_name(self, type_name, field=None, parent_msg=None, effective_ns=None):
        # Handle map/dict fields if field_type or is_map is set
        if field is not None:
            field_type = getattr(field, 'field_type', None)
            if getattr(field, 'is_map', False) or field_type in ('dict', 'map') or str(field_type).lower() in ('fieldtype.dict', 'fieldtype.map', 'dict', 'map'):
                key_type = 'std::string'
                value_type = 'int32_t'
                if hasattr(field, 'map_key_type') and field.map_key_type is not None:
                    if isinstance(field.map_key_type, str):
                        key_type = self._cpp_type_for_type_name(field.map_key_type)
                    else:
                        key_type = self._cpp_type_for_type_name(None, field=field.map_key_type)
                if hasattr(field, 'map_value_type') and field.map_value_type is not None:
                    if isinstance(field.map_value_type, str):
                        value_type = self._cpp_type_for_type_name(field.map_value_type)
                    else:
                        value_type = self._cpp_type_for_type_name(None, field=field.map_value_type)
                return f"std::map<{key_type}, {value_type}>"
        """
        Helper to map a type name string to a valid C++ type, with namespace/model lookup.
        Handles enums, messages, cross-namespace, and built-in types. Never emits 'unknown_type'.
        """
        # Built-in types
        mapping = {
            'string': 'std::string',
            'int': 'int32_t',
            'float': 'float',
            'bool': 'bool',
            'boolean': 'bool',
            'byte': 'uint8_t',
            'uint': 'uint32_t',
            'int8': 'int8_t',
            'uint8': 'uint8_t',
            'int16': 'int16_t',
            'uint16': 'uint16_t',
            'int32': 'int32_t',
            'uint32': 'uint32_t',
            'int64': 'int64_t',
            'uint64': 'uint64_t',
            'double': 'double',
        }
        if type_name in mapping:
            return mapping[type_name]

        model = getattr(self, 'model', None)
        # Try to resolve enums (top-level and nested)
        if model:
            enums = getattr(model, 'enums', {})
            messages = getattr(model, 'messages', {})
            # Try direct lookup
            if type_name in enums:
                enum_obj = enums[type_name]
                enum_ns = getattr(enum_obj, 'namespace', None)
                sanitized_name = self._sanitize_identifier(enum_obj.name)
                enum_name = sanitized_name if sanitized_name.endswith("_Enum") else sanitized_name + "_Enum"
                if effective_ns is not None:
                    if enum_ns == effective_ns:
                        return enum_name
                    else:
                        return f"{self._sanitize_identifier(enum_ns)}::{enum_name}" if enum_ns else enum_name
                else:
                    return enum_name
            if type_name in messages:
                msg_obj = messages[type_name]
                msg_ns = getattr(msg_obj, 'namespace', None)
                msg_name = self._sanitize_identifier(msg_obj.name)
                if effective_ns is not None:
                    if msg_ns == effective_ns:
                        return msg_name
                    else:
                        return f"{self._sanitize_identifier(msg_ns)}::{msg_name}" if msg_ns else msg_name
                else:
                    return msg_name
            # Try lookup by short name (for messages/enums defined at top level or in current namespace)
            for key, msg_obj in messages.items():
                if getattr(msg_obj, 'name', None) == type_name:
                    msg_ns = getattr(msg_obj, 'namespace', None)
                    msg_name = self._sanitize_identifier(msg_obj.name)
                    if effective_ns is not None:
                        if msg_ns == effective_ns:
                            return msg_name
                        else:
                            return f"{self._sanitize_identifier(msg_ns)}::{msg_name}" if msg_ns else msg_name
                    else:
                        return msg_name
            for key, enum_obj in enums.items():
                if getattr(enum_obj, 'name', None) == type_name:
                    enum_ns = getattr(enum_obj, 'namespace', None)
                    sanitized_name = self._sanitize_identifier(enum_obj.name)
                    enum_name = sanitized_name if sanitized_name.endswith("_Enum") else sanitized_name + "_Enum"
                    if effective_ns is not None:
                        if enum_ns == effective_ns:
                            return enum_name
                        else:
                            return f"{self._sanitize_identifier(enum_ns)}::{enum_name}" if enum_ns else enum_name
                    else:
                        return enum_name
            # Namespaced enums/messages (Namespace.Type or Namespace::Type)
            if ('.' in str(type_name)) or ('::' in str(type_name)):
                if '.' in str(type_name):
                    ns_part, type_part = str(type_name).rsplit('.', 1)
                else:
                    ns_part, type_part = str(type_name).rsplit('::', 1)
                ns_obj = getattr(model, 'namespaces', {}).get(ns_part, None)
                if ns_obj:
                    ns_enums = getattr(ns_obj, 'enums', {})
                    if type_part in ns_enums:
                        sanitized_name = self._sanitize_identifier(type_part)
                        enum_name = sanitized_name if sanitized_name.endswith("_Enum") else sanitized_name + "_Enum"
                        return f"{self._sanitize_identifier(ns_part)}::{enum_name}"
                    ns_msgs = getattr(ns_obj, 'messages', {})
                    if type_part in ns_msgs:
                        return f"{self._sanitize_identifier(ns_part)}::{self._sanitize_identifier(type_part)}"
            # Try to resolve in imports if not found in current model
            import_map = getattr(self, 'import_map', None)
            ns, kind = self._find_type_in_imports(type_name, import_map)
            if ns:
                sanitized_ns = self._sanitize_identifier(ns)
                sanitized_name = self._sanitize_identifier(type_name)
                if kind == 'enum':
                    enum_name = sanitized_name if sanitized_name.endswith("_Enum") else sanitized_name + "_Enum"
                    return f"{sanitized_ns}::{enum_name}"
                else:
                    return f"{sanitized_ns}::{sanitized_name}"
            # Nested enums (field enums)
            if field is not None and hasattr(field, 'enum') and getattr(field, 'enum', None):
                msg_name = self._sanitize_identifier(getattr(parent_msg, 'name', parent_msg) if parent_msg else 'Message')
                field_name = self._sanitize_identifier(getattr(field, 'name', 'field'))
                return f"{msg_name}_{field_name}_Enum"
            # Nested/field compound types
            if field is not None and (getattr(field, 'field_type', None) in ('compound',) or str(getattr(field, 'field_type', None)) in ('FieldType.COMPOUND', 'compound')):
                msg_name = self._sanitize_identifier(getattr(parent_msg, 'name', parent_msg) if parent_msg else 'Message')
                field_name = self._sanitize_identifier(getattr(field, 'name', 'field'))
                return f"{msg_name}_{field_name}_Compound"
            # Options
            options = getattr(model, 'options', {})
            if type_name in options:
                return 'uint32_t'
        # If type_name is None, try to resolve from field metadata (enum/options/compound/message_reference/basic types)
        if field is not None:
            field_type = getattr(field, 'field_type', None)
            # Enum field: use generated enum type name
            if field_type in ('enum',) or str(field_type) in ('FieldType.ENUM', 'enum') or getattr(field, 'enum_reference', None) or getattr(field, 'enum', None):
                msg_name = self._sanitize_identifier(getattr(parent_msg, 'name', parent_msg) if parent_msg else 'Message')
                field_name = self._sanitize_identifier(getattr(field, 'name', 'field'))
                return f"{msg_name}_{field_name}_Enum"
            # Options field: always uint32_t
            if field_type in ('options',) or str(field_type) in ('FieldType.OPTIONS', 'options') or getattr(field, 'is_options', False):
                return 'uint32_t'
            # Compound field: use generated struct name
            if field_type in ('compound',) or str(field_type) in ('FieldType.COMPOUND', 'compound'):
                msg_name = self._sanitize_identifier(getattr(parent_msg, 'name', parent_msg) if parent_msg else 'Message')
                field_name = self._sanitize_identifier(getattr(field, 'name', 'field'))
                return f"{msg_name}_{field_name}_Compound"
            # Message reference: use referenced message type
            if field_type in ('message_reference',) or str(field_type) in ('FieldType.MESSAGE_REFERENCE', 'message_reference') or getattr(field, 'message_reference', None):
                msg_ref = getattr(field, 'message_reference', None)
                if msg_ref and model and hasattr(model, 'messages') and msg_ref in model.messages:
                    msg_obj = model.messages[msg_ref]
                    msg_ns = getattr(msg_obj, 'namespace', None)
                    msg_name = self._sanitize_identifier(msg_obj.name)
                    current_ns = getattr(parent_msg, 'namespace', None) if parent_msg and hasattr(parent_msg, 'namespace') else getattr(field, 'namespace', None)
                    if effective_ns is not None:
                        if msg_ns == effective_ns or msg_ns == current_ns:
                            return msg_name
                        else:
                            return f"{self._sanitize_identifier(msg_ns)}::{msg_name}" if msg_ns else msg_name
                    else:
                        if msg_ns == current_ns:
                            return msg_name
                        else:
                            return f"{self._sanitize_identifier(msg_ns)}::{msg_name}" if msg_ns else msg_name
            # Basic types: map field_type to C++ type
            # Accept both string and enum representations
            fieldtype_to_cpp = {
                'string': 'std::string',
                'int': 'int32_t',
                'float': 'float',
                'bool': 'bool',
                'boolean': 'bool',
                'byte': 'uint8_t',
                'uint': 'uint32_t',
                'int8': 'int8_t',
                'uint8': 'uint8_t',
                'int16': 'int16_t',
                'uint16': 'uint16_t',
                'int32': 'int32_t',
                'uint32': 'uint32_t',
                'int64': 'int64_t',
                'uint64': 'uint64_t',
                'double': 'double',
            }
            # Try to get string value if field_type is an enum
            field_type_str = field_type.value if hasattr(field_type, 'value') else str(field_type) if field_type else None
            if field_type_str in fieldtype_to_cpp:
                return fieldtype_to_cpp[field_type_str]
        # Fallback: in a closed type system, this should never happen
        raise RuntimeError(f"[CppGeneratorStd23] Could not resolve C++ type for type_name '{type_name}' (field='{getattr(field, 'name', None)}', parent_msg='{getattr(parent_msg, 'name', None)}')")

    def _doc_comment(self, comment, indent="    "):
        """Generate a formatted Doxygen-style comment from the provided comment text."""
        if not comment:
            return ""
        
        # If the comment is already a Doxygen comment (starts with ///), use it as is
        if isinstance(comment, str) and comment.strip().startswith("///"):
            # Clean up the comment text - remove leading/trailing whitespace and handle multi-line comments
            lines = comment.strip().splitlines()
            # Handle an empty line if it slipped through
            if not lines:
                return ""
            # Convert to Doxygen format with proper indentation, preserving the /// prefix
            return "\n".join(f"{indent}{line}" for line in lines)
        
        # Otherwise, clean up the comment text and add /// prefix
        if isinstance(comment, str):
            lines = comment.strip().splitlines()
            # Handle an empty line if it slipped through
            if not lines:
                return ""
            # Convert to Doxygen format with proper indentation
            if len(lines) == 1:
                # Single line comment
                return f"{indent}/// {lines[0].strip()}"
            else:
                # Multi-line comment - format as a multi-line comment
                return "\n".join(f"{indent}/// {line.strip()}" for line in lines)
        
        return ""

    def _generate_enum_full(self, enum, indent="    ", nested=False, fully_qualify=False, ns_prefix=None):
        """
        Generate a C++ enum definition, handling field enums, nested enums, and enum inheritance.
        For nested enums (nested=True), use a simpler name without qualification.
        """
        # Collapse enum inheritance: flatten all parent values into a single enum definition
        def collect_all_enum_values(e, seen=None):
            if seen is None:
                seen = set()
            values = []
            # Recursively collect parent values first
            parent_name = getattr(e, 'parent', None)
            model = getattr(self, 'model', None)
            if parent_name and model and hasattr(model, 'enums') and parent_name in model.enums:
                parent_enum = model.enums[parent_name]
                values.extend(collect_all_enum_values(parent_enum, seen))
            # Add this enum's values, skipping duplicates
            for v in getattr(e, 'values', []):
                if v.name not in seen:
                    values.append(v)
                    seen.add(v.name)
            return values

        # If this is a field enum (e.g., Command_type_Enum), flatten and sanitize
        # Remove any '::' and flatten to Message_Field_Enum pattern
        raw_name = enum.name
        if '::' in raw_name:
            parts = raw_name.split('::')
            # If the pattern is Message::field_Enum, flatten to Message_field_Enum
            flat_name = '_'.join(parts)
            # For nested enums, use only the field name
            if nested and len(parts) == 2:
                flat_name = self._sanitize_identifier(parts[1])
        else:
            flat_name = raw_name
        
        # Append '_Enum' to the C++ enum name to avoid name clashes with structs
        # But don't append it if the name already ends with '_Enum'
        sanitized_name = self._sanitize_identifier(flat_name)
        name = sanitized_name if sanitized_name.endswith("_Enum") else sanitized_name + "_Enum"
        # Always use unqualified name for enum declaration inside the namespace
        # (do not prefix with namespace)
        
        # Get both comment and description for the enum
        enum_description = getattr(enum, 'description', None)
        enum_comment = getattr(enum, 'comment', None)
        # Use description if available, fall back to comment
        doc_text = enum_description if enum_description else enum_comment
        doc = self._doc_comment(doc_text, indent)
        
        # Determine the minimum bit size needed to represent all enum values
        size_bits = 32  # Default to 32 bits
        if hasattr(enum, 'get_min_size_bits'):
            size_bits = enum.get_min_size_bits()
        elif hasattr(enum, 'values') and enum.values:
            max_value = max([v.value for v in enum.values if hasattr(v, 'value')])
            if max_value < 256:
                size_bits = 8
            elif max_value < 65536:
                size_bits = 16
            else:
                size_bits = 32
        
        # Use enum or enum class based on whether the enum is open or closed
        enum_type = "enum" if getattr(enum, 'is_open', False) else "enum class"
        
        # No inheritance in C++: always use underlying type
        parent = f" : uint{size_bits}_t"
        
        # Collect all values, including from parent enums
        all_values = collect_all_enum_values(enum)
        
        values = []
        for v in all_values:
            # Add documentation for enum values if available
            enum_value_description = getattr(v, 'description', None)
            enum_value_comment = getattr(v, 'comment', None)
            
            # If we have a comment for the enum value, add it as a doc comment
            if enum_value_description or enum_value_comment:
                value_doc_text = enum_value_description if enum_value_description else enum_value_comment
                value_doc = self._doc_comment(value_doc_text, indent + "    ")
                values.append(f"{value_doc}")
            
            # Add each enum value with its numeric value
            values.append(f"{indent}    {self._sanitize_identifier(v.name)} = {v.value},")
        values_str = '\n'.join(values)
        
        # Generate the complete enum definition with doc comment
        result = f"{doc}\n{indent}{enum_type} {name}{parent}\n{indent}{{\n{values_str}\n{indent}}};"
        return result if result is not None else ""
