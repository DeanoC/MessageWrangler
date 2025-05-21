
import os
import sys
import glob
import pytest
import tempfile
import subprocess
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from generators.typescript_generator import generate_typescript_code

# Ensure npm global bin is in PATH for tsc detection (especially in venv/IDE)
if sys.platform.startswith("win"):
    npm_global_bin = os.path.expandvars(r"%APPDATA%\\npm")
    if npm_global_bin not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + npm_global_bin
elif sys.platform.startswith("linux") or sys.platform == "darwin":
    # Typical npm global bin for Unix
    npm_global_bin = os.path.expanduser("~/.npm-global/bin")
    if npm_global_bin not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + npm_global_bin

def get_def_files():
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]

def is_tsc_available():
    # Try tsc, tsc.cmd, npx tsc in order
    candidates = [
        ["tsc", "--version"],
        ["tsc.cmd", "--version"],
        ["npx", "tsc", "--version"],
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return cmd[:-1]  # Return the working command (without --version)
        except FileNotFoundError:
            pass
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
    tsc_cmd = is_tsc_available()
    if not tsc_cmd:
        pytest.skip(
            "TypeScript compiler (tsc) is not installed or not in PATH for this Python environment. "
            + tsc_install_instructions()
            + "\n[DEBUG] See above for PATH and tsc debug output."
        )
    with open(def_path, "r", encoding="utf-8") as f:
        dsl = f.read()
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
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
            # Run tsc --noEmit on the generated file using the detected command
            result = subprocess.run(tsc_cmd + ["--noEmit", ts_file], capture_output=True, text=True)
            assert result.returncode == 0, f"TypeScript syntax/type error in {filename} generated from {def_path}:\n{result.stderr}"


# Additional test: ensure tsc emits errors for invalid TypeScript
def test_typescript_generator_tsc_invalid():
    tsc_cmd = is_tsc_available()
    if not tsc_cmd:
        pytest.skip(
            "TypeScript compiler (tsc) is not installed or not in PATH for this Python environment. "
            + tsc_install_instructions()
        )
    # Intentionally invalid TypeScript code
    invalid_code = """
    export interface Foo {
        bar: string
        baz: number
    }
    // The following line is invalid: 'let x: NotAType = 123;'
    let x: NotAType = 123;
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ts_file = os.path.join(tmpdir, "invalid_test.ts")
        with open(ts_file, "w", encoding="utf-8") as f:
            f.write(invalid_code)
        result = subprocess.run(tsc_cmd + ["--noEmit", ts_file], capture_output=True, text=True)
        assert result.returncode != 0, "tsc did not report an error for intentionally invalid TypeScript code!\nSTDOUT:\n{}\nSTDERR:\n{}".format(result.stdout, result.stderr)
