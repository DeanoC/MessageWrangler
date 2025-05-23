"""
namespace_resolver.py
Namespace and FQN resolution logic for MessageWrangler, following the documented hierarchy.
"""
import os

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
            imported_model = None
            try:
                from def_file_loader import build_model_from_file_recursive
                imported_model = build_model_from_file_recursive(import_path, set())
            except Exception:
                continue
            if imported_model:
                imported_file_ns = os.path.splitext(os.path.basename(import_path))[0]
                fq_imported = f"{imported_file_ns}::{ref_name}"
                if fq_imported in imported_model.messages or fq_imported in imported_model.enums or (hasattr(imported_model, 'options') and fq_imported in imported_model.options):
                    return fq_imported
    # 5. Aliased imports: only if explicitly qualified (already handled above)
    return None
