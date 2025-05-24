import os
from generators.python3_generator import generate_python3_code
from tests.test_utils import load_early_model_with_imports
from early_model_transforms.earlymodel_to_model_transform import EarlyModelToModelTransform
import re
from generators.python3_generator import get_file_level_namespace_name

def test_python3_generator_primitives_mapping():
    def_path = os.path.join("tests", "def", "test_arrays_and_references.def")
    early_model, _ = load_early_model_with_imports(def_path)
    model = EarlyModelToModelTransform().transform(early_model)
    ns_name = get_file_level_namespace_name(model)
    code = generate_python3_code(model, module_name=ns_name)
    # Check file-level namespace class
    # Match class definition and capture its indented body, robust to \r\n or \n line endings
    # Match class definition and capture its indented body, robust to \r, \n, and possible trailing whitespace
    # Robust regex: match class definition, allow any number of blank lines, then capture all indented lines (namespace body)
    print(f"[DEBUG GENERATED CODE for namespace '{ns_name}']\n" + code)
    ns_match = re.search(rf'class\s+{re.escape(ns_name)}\s*:\s*(?:\r?\n|\s)*((?:    .*(?:\r?\n|$))+)', code, re.DOTALL)
    assert ns_match, "Expected file-level namespace class in generated Python code."
    ns_body = ns_match.group(1)

    # Helper to extract class bodies from the namespace
    def extract_class_body(class_name, body):
        # Match class definition and capture its indented body until the next class or end of string
        pattern = rf'@dataclass\n    class {class_name}:[\s\r\n]+((?:        .*(?:\r?\n|$))+)'  # greedy match
        match = re.search(pattern, body, re.MULTILINE)
        if not match:
            return None
        # Remove trailing blank lines
        lines = [line for line in match.group(1).splitlines() if line.strip()]
        return '\n'.join(lines)

    # Vec3
    assert re.search(r'@dataclass\n    class Vec3:', ns_body), "Expected Vec3 class in generated Python code under namespace."
    vec3_body = extract_class_body('Vec3', ns_body)
    assert vec3_body is not None, "Could not extract Vec3 class body."
    assert 'x: float' in vec3_body, f"Expected 'x: float' in Vec3, got:\n{vec3_body}"
    assert 'y: float' in vec3_body, f"Expected 'y: float' in Vec3, got:\n{vec3_body}"
    assert 'z: float' in vec3_body, f"Expected 'z: float' in Vec3, got:\n{vec3_body}"

    # WithMap
    assert re.search(r'@dataclass\n    class WithMap:', ns_body), "Expected WithMap class in generated Python code under namespace."
    withmap_body = extract_class_body('WithMap', ns_body)
    assert withmap_body is not None, "Could not extract WithMap class body."
    assert 'dict: dict[str, int]' in withmap_body, f"Expected 'dict: dict[str, int]' in WithMap, got:\n{withmap_body}"
    assert 'objMap: dict[str, Vec3]' in withmap_body, f"Expected 'objMap: dict[str, Vec3]' in WithMap, got:\n{withmap_body}"

    # WithArrays
    assert re.search(r'@dataclass\n    class WithArrays:', ns_body), "Expected WithArrays class in generated Python code under namespace."
    witharrays_body = extract_class_body('WithArrays', ns_body)
    assert witharrays_body is not None, "Could not extract WithArrays class body."
    assert 'tags: list[str]' in witharrays_body, f"Expected 'tags: list[str]' in WithArrays, got:\n{witharrays_body}"
    assert 'points: list[Vec3]' in witharrays_body, f"Expected 'points: list[Vec3]' in WithArrays, got:\n{witharrays_body}"
    assert 'ids: list[int]' in witharrays_body, f"Expected 'ids: list[int]' in WithArrays, got:\n{witharrays_body}"
