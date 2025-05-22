import os
import glob
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import _build_model_from_lark_tree
from generators.typescript_generator import generate_typescript_code

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
def test_typescript_generator_output(def_path):
    with open(def_path, "r", encoding="utf-8") as f:
        dsl = f.read()
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree)
    # The model may have multiple namespaces; generate code for all
    if hasattr(model, 'namespaces'):
        namespaces = list(model.namespaces.values())
    else:
        # Fallback: treat the model as a single namespace
        namespaces = [model]
    code_map = generate_typescript_code(namespaces)
    # Basic asserts: code is not empty, contains all message and enum/interface names
    for filename, code in code_map.items():
        assert code.strip(), f"No code generated for {def_path} in {filename}"
        for ns in namespaces:
            for msg in getattr(ns, 'messages', []):
                assert f"interface {msg.name}" in code, f"Missing interface for message {msg.name} in {def_path} ({filename})"
            for enum in getattr(ns, 'enums', []):
                assert f"enum {enum.name}" in code, f"Missing enum for {enum.name} in {def_path} ({filename})"
    # Optionally, check that all field types in generated code are valid TypeScript types
    import re
    VALID_TS_TYPES = {"string", "number", "boolean", "any", "Uint8Array"}
    for filename, code in code_map.items():
        # Find all interface definitions and their fields
        interface_blocks = re.findall(r'interface (\w+)[^{]*{([^}]*)}', code, re.MULTILINE)
        for interface_name, body in interface_blocks:
            for line in body.splitlines():
                m = re.match(r'\s*(\w+): ([^;]+);', line)
                if m:
                    field_name, type_str = m.groups()
                    type_str = type_str.strip().replace(' | undefined', '').replace('[]', '')
                    # Acceptable types: string, number, boolean, any, Uint8Array, or class/enum names
                    if (
                        type_str not in VALID_TS_TYPES
                        and not re.match(r"^[A-Z]\w*(\.[A-Z]\w*)*$", type_str)
                        and not re.match(r"^[A-Z]\w*_Enum$", type_str)
                        and not re.match(r"^[A-Z]\w*_Options$", type_str)
                    ):
                        raise AssertionError(f"Field '{field_name}' in interface '{interface_name}' has invalid type '{type_str}' in generated code for {def_path} ({filename})")


import sys
import tempfile
import subprocess

def is_tsc_available():
    try:
        result = subprocess.run(["tsc", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def tsc_install_instructions():
    if sys.platform.startswith("win"):
        return "To install TypeScript, run: npm install -g typescript (in Command Prompt or PowerShell)"
    elif sys.platform.startswith("linux"):
        return "To install TypeScript, run: npm install -g typescript (in your shell)"
    elif sys.platform == "darwin":
        return "To install TypeScript, run: npm install -g typescript (in Terminal)"
    else:
        return "To install TypeScript, run: npm install -g typescript (in your shell)"

@pytest.mark.parametrize("def_path", get_def_files())
def test_typescript_generator_tsc_syntax(def_path):
    if not is_tsc_available():
        pytest.skip("TypeScript compiler (tsc) is not installed. " + tsc_install_instructions())
    with open(def_path, "r", encoding="utf-8") as f:
        dsl = f.read()
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree)
    if hasattr(model, 'namespaces'):
        namespaces = list(model.namespaces.values())
    else:
        namespaces = [model]
    code_map = generate_typescript_code(namespaces)
    for filename, code in code_map.items():
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file = os.path.join(tmpdir, filename)
            with open(ts_file, "w", encoding="utf-8") as f:
                f.write(code)
            # Run tsc --noEmit on the generated file
            result = subprocess.run(["tsc", "--noEmit", ts_file], capture_output=True, text=True)
            assert result.returncode == 0, f"TypeScript syntax/type error in {filename} generated from {def_path}:\n{result.stderr}"
