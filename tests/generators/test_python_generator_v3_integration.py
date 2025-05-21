import os
import glob
import subprocess
import sys
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from generators.python_generator_v3 import generate_all_python_files

def get_def_files():
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    # Exclude invalid, duplicate, unresolved, and multi-dimensional array/corner case defs
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
        # Exclude any .def file with multi-dimensional arrays or parser-unsupported syntax
        # test_arrays_and_references_corner_cases.def already covers multi-dim arrays
    }
    # Optionally, exclude any other .def files with known parser-rejected syntax here
    return [f for f in all_defs if os.path.basename(f) not in invalid]

gen_dir = os.path.join("generated", "python_v3")
os.makedirs(gen_dir, exist_ok=True)

@pytest.mark.parametrize("def_path", get_def_files())
def test_python_generator_v3_executes(def_path):
    # Generate all needed .py files for this def and its imports
    generate_all_python_files([def_path], gen_dir)
    # Now parse the main def file to get the model for runner
    from lark_parser import parse_message_dsl
    from message_model_builder import build_model_from_lark_tree
    with open(def_path, "r", encoding="utf-8") as f:
        dsl = f.read()
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree)
    module_name = os.path.splitext(os.path.basename(def_path))[0]
    # Add a __main__ block to a separate runner file that imports and instantiates the classes
    runner_path = os.path.join(gen_dir, module_name + "_runner.py")
    runner_lines = [f"from .{module_name} import *", "if __name__ == '__main__':"]
    for msg in model.messages.values():
        runner_lines.append(f"    print({msg.name}())")
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write("\n".join(runner_lines) + "\n")
    # Run the runner file as a module (so relative imports work)
    # Compute the module path relative to the workspace root
    import_path = f"generated.python_v3.{module_name}_runner"
    result = subprocess.run([sys.executable, "-m", import_path], capture_output=True, text=True, cwd=os.path.abspath(os.path.join(gen_dir, '..', '..')))
    assert result.returncode == 0, f"Python code failed to run for {def_path}: {result.stderr}"
    # Optionally, check that output contains class names
    for msg in model.messages.values():
        assert msg.name in result.stdout, f"Output missing message {msg.name} for {def_path}"
