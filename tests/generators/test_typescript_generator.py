def test_typescript_generator_nested_namespace_qualification():
    """
    Ensure that fields referencing nested namespace types (e.g., TestNS.Nested) are correctly qualified in the generated TypeScript.
    """
    def_path = os.path.join("tests", "def", "test_arrays_and_references.def")
    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    ts_code = generate_typescript_code(model)
    # Write the generated TypeScript code to generated/typescript/
    output_dir = os.path.join("generated", "typescript")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "test_arrays_and_references.ts")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_code)

    # Read the generated TypeScript output
    with open(output_path, "r", encoding="utf-8") as f:
        ts_out = f.read()

    # Check that WithNamespaceRef fields are correctly qualified
    # Should be: nested: TestNS.Nested; nestedArray: TestNS.Nested[];
    found_nested = False
    found_nested_array = False
    for line in ts_out.splitlines():
        if "WithNamespaceRef" in line:
            # Start of the interface block
            continue
        if "nested:" in line:
            found_nested = True
            assert ": TestNS.Nested" in line, f"Field 'nested' should be qualified as 'TestNS.Nested' in WithNamespaceRef, got: {line}"
        if "nestedArray:" in line:
            found_nested_array = True
            assert ": TestNS.Nested[]" in line, f"Field 'nestedArray' should be qualified as 'TestNS.Nested[]' in WithNamespaceRef, got: {line}"
    assert found_nested, "Field 'nested' not found in WithNamespaceRef interface in generated TypeScript."
    assert found_nested_array, "Field 'nestedArray' not found in WithNamespaceRef interface in generated TypeScript."
import os
import glob
import pytest
from generators.typescript_generator import generate_typescript_code
from tests.test_utils import load_early_model_with_imports
from earlymodel_to_model import EarlyModelToModel

def get_def_files():
    # Only include .def files that are expected to be valid for code generation
    # Exclude known invalid/negative test files
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]

@pytest.mark.parametrize("def_path", get_def_files())
def test_typescript_generator_generates_code(def_path):
    # 6. Check 1-to-1 mapping from imports in the .def file to imports in the TypeScript output
    def parse_def_imports(def_path):
        import_lines = []
        with open(def_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('import '):
                    # Extract the file name (between quotes)
                    import_file = None
                    if '"' in line:
                        import_file = line.split('"')[1]
                    elif "'" in line:
                        import_file = line.split("'")[1]
                    if import_file:
                        # Remove leading ./ or .\\ if present
                        import_file = import_file.lstrip('./').lstrip('.\\')
                        import_file_base = os.path.splitext(os.path.basename(import_file))[0]
                        import_lines.append(import_file_base)
        return set(import_lines)

    def parse_ts_imports(ts_code):
        ts_imports = set()
        for line in ts_code.splitlines():
            line = line.strip()
            if line.startswith('import '):
                # Extract the file name (between './' and the next quote)
                if "from './" in line:
                    after_from = line.split("from './", 1)[1]
                    import_file = after_from.split("'", 1)[0]
                    import_file_base = os.path.splitext(os.path.basename(import_file))[0]
                    ts_imports.add(import_file_base)
        return ts_imports

    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModel().process(early_model)
    # DEBUG: Print ModelField for 'typeX' in CommCommand if present
    for ns in getattr(model, 'namespaces', []):
        if ns.name == 'ClientCommands' or True:  # Search all namespaces
            for msg in getattr(ns, 'messages', []):
                if msg.name == 'CommCommand':
                    for field in msg.fields:
                        if field.name == 'typeX':
                            print(f"[DEBUG] CommCommand.typeX: field_types={field.field_types}, type_refs={field.type_refs}, type_names={field.type_names}, inline_values={field.inline_values}")
    ts_code = generate_typescript_code(model)
    assert ts_code.strip(), f"No TypeScript code generated for {def_path}"
    # Optionally, check for some expected TypeScript keywords
    assert "export" in ts_code and ("interface" in ts_code or "enum" in ts_code), f"No TypeScript interface or enum in output for {def_path}"

    # Write the generated TypeScript code to generated/typescript/
    output_dir = os.path.join("generated", "typescript")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(def_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.ts")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_code)

    # --- Additional validation of imports and names ---
    with open(output_path, "r", encoding="utf-8") as f:
        ts_out = f.read()

    # 1. Validate that import statements exist for referenced external types
    if "import" in ts_out:
        import_lines = [line for line in ts_out.splitlines() if line.strip().startswith("import ")]
        for line in import_lines:
            assert "from './" in line, f"Import statement does not use relative path: {line} in {output_path}"
            # Accept both named and namespace imports
            assert ("{" in line and "}" in line) or ("* as" in line), f"Import statement does not import types or namespace: {line} in {output_path}"

    # 2. Validate that enums and interfaces do not have namespace-prefixed names
    for line in ts_out.splitlines():
        if line.strip().startswith("export enum ") or line.strip().startswith("export interface "):
            name = line.split()[2]
            assert "_" not in name, f"Type/interface/enum name '{name}' should not be namespace-prefixed in {output_path}"

    # 3. Validate that field types are not just 'string' if they should reference a type
    # Only check for enum if the model expects an enum for this field
    for ns in getattr(model, 'namespaces', []):
        for msg in getattr(ns, 'messages', []):
            for field in msg.fields:
                if field.name in ('typeX', 'mode'):
                    # Only assert if the model expects an enum
                    if hasattr(field, 'type') and str(field.type) == 'FieldType.ENUM':
                        if f'{field.name}:' in ts_out:
                            for l in ts_out.splitlines():
                                if f'{field.name}:' in l:
                                    assert ': string' not in l, f"Field '{field.name}' should not be 'string' if it is an enum in {output_path}"

    # 4. Validate that all fields from the Model are present in the generated TypeScript
    for ns in getattr(model, 'namespaces', []):
        for msg in getattr(ns, 'messages', []):
            msg_name = msg.name.split('::')[-1].split('_')[-1]  # match get_local_name logic
            # Find the interface for this message
            interface_header = f"export interface {msg_name} {{"
            if interface_header in ts_out:
                # Find the block of the interface
                start = ts_out.index(interface_header)
                end = ts_out.index('}', start)
                interface_block = ts_out[start:end]
                for field in msg.fields:
                    assert f"{field.name}:" in interface_block, f"Field '{field.name}' missing in TypeScript for message '{msg_name}' in {output_path}"
            else:
                # If not found, fail
                assert False, f"Interface for message '{msg_name}' not found in TypeScript output for {output_path}"

    # 5. Validate that imported types are present in import statements and used in fields
    # Collect all referenced external types from the model
    referenced_types = set()
    current_file_base = os.path.splitext(os.path.basename(def_path))[0]
    for ns in getattr(model, 'namespaces', []):
        for msg in getattr(ns, 'messages', []):
            for field in msg.fields:
                for ftype, tref in zip(getattr(field, 'field_types', []), getattr(field, 'type_refs', [])):
                    if ftype.name in ("ENUM", "MESSAGE") and tref is not None:
                        ref_file = getattr(tref, 'file', None)
                        ref_name = getattr(tref, 'name', None)
                        if ref_file and ref_name:
                            ref_file_base = os.path.splitext(os.path.basename(ref_file))[0]
                            if ref_file_base != current_file_base:
                                referenced_types.add((ref_file_base, ref_name))
    # Only check 1-to-1 mapping if TypeScript output was generated and read
    if 'ts_out' in locals():
        def_imports = parse_def_imports(def_path)
        ts_imports = parse_ts_imports(ts_out)
        assert def_imports == ts_imports, f"Mismatch between .def imports {def_imports} and TypeScript imports {ts_imports} in {output_path}"
 
    # 6. Validate that 'any' is never used as a type in the generated TypeScript code
    # This ensures all types are known and written into the generated file (closed system)
    if 'ts_out' in locals():
        for line in ts_out.splitlines():
            if ": any" in line or ": any[]" in line:
                assert False, f"Type 'any' found in generated TypeScript: {line} in {output_path}. All types should be known and explicit."


 
    # Now check that each referenced type is present in an import statement
    for ref_file_base, ref_name in referenced_types:
        found = False
        for line in ts_out.splitlines():
            if line.strip().startswith("import ") and ref_file_base in line and ref_name in line:
                found = True
                break
        assert found, f"Missing import for type '{ref_name}' from '{ref_file_base}' in {output_path}"
