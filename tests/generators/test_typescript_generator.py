import os
import glob
import pytest
from generators.typescript_generator import generate_typescript_code
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform

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
    early_model, all_early_models = load_early_model_with_imports(def_path)
    model = EarlyModelToModelTransform().transform(early_model)
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
            assert "{" in line and "}" in line, f"Import statement does not import types: {line} in {output_path}"

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
