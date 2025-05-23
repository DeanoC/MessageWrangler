import os
import glob
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_model_from_lark_tree
from generators.python_generator_v3 import generate_python_code

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
def test_python_generator_v3_output(def_path):
    with open(def_path, "r", encoding="utf-8") as f:
        dsl = f.read()
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree)
    code = generate_python_code(model)
    if 'WithMap' in code:
        print("\n[DEBUG] Full generated code for WithMap test:\n" + code)
    # Basic asserts: code is not empty, contains all message and enum class names
    assert code.strip(), f"No code generated for {def_path}"
    for msg in model.messages.values():
        assert f'class {msg.name}' in code, f"Missing class for message {msg.name} in {def_path}"
    for enum in model.enums.values():
        assert f'class {enum.name}(Enum)' in code, f"Missing Enum for {enum.name} in {def_path}"
    # Optionally, check for @dataclass usage
    assert '@dataclass' in code, f"No @dataclass found in output for {def_path}"

    # Additional: check that all field types in generated code are valid Python types
    import re
    # Map FieldType to expected Python type string
    from message_model import FieldType
    BASIC_TYPE_TO_PY = {
        FieldType.STRING: "str",
        FieldType.INT: "int",
        FieldType.FLOAT: "float",
        FieldType.BOOL: "bool",
        FieldType.BYTE: "int",
    }
    # Find all class definitions and their fields
    class_blocks = re.findall(r'class (\w+)[^:]*:\n((?:    .+\n)+)', code)
    for class_name, body in class_blocks:
        # Find all fields: lines like '    field_name: type'
        for line in body.splitlines():
            m = re.match(r'\s+(\w+): ([^=]+)', line)
            if m:
                field_name, type_str = m.groups()
                type_str = type_str.strip()
                # Acceptable types: str, int, float, bool, Any, Dict[str, Any], List[Any], or class/enum names
                valid_basic = {"str", "int", "float", "bool", "Any"}
                valid_container = re.compile(r"^(List\[.*\]|Dict\[str, .+\])$")
                # Accept also any class or enum name in this code
                valid_names = {c for c, _ in class_blocks} | {e.name for e in model.enums.values()}
                # Accept compound class names
                # Accept references to other files (e.g., namespaced or cross-file types)
                valid_reference = re.compile(r"^[A-Z]\w*(::[A-Z]\w*)*(_[A-Za-z0-9]+)?$")
                if (
                    type_str not in valid_basic
                    and not valid_container.match(type_str)
                    and type_str not in valid_names
                    and not type_str.endswith("_Compound")
                    and not valid_reference.match(type_str)
                ):
                    raise AssertionError(f"Field '{field_name}' in class '{class_name}' has invalid type '{type_str}' in generated code for {def_path}")
