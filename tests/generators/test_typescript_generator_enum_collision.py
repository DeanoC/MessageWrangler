import pytest
from generators.typescript_generator import generate_typescript_code
from tests.test_utils import load_early_model_with_imports
from early_model_transforms import EarlyModelToModel

# This test simulates a model with two enums that have the same value name, which should cause a TypeScript error
# if the enum values are not made unique. This test should fail before the transform is added, and pass after.
def test_typescript_enum_value_name_collision(tmp_path):
    # Simulate a .def file with two enums that have the same value name
    def_text = '''
    enum FooType {
        Live = 0;
        Dead = 1;
    }
    enum BarType {
        Live = 0;
        Sleep = 1;
    }
    message TestMsg {
        foo: FooType;
        bar: BarType;
    }
    '''
    def_path = tmp_path / "collision.def"
    def_path.write_text(def_text)
    early_model, _ = load_early_model_with_imports(str(def_path))
    model = EarlyModelToModel().process(early_model)
    ts_code = generate_typescript_code(model)
    # Check for duplicate enum value names in the generated TypeScript code
    import re
    enum_value_names = re.findall(r'export enum [^{]+{([^}]*)}', ts_code, re.MULTILINE | re.DOTALL)
    value_names = []
    for enum_body in enum_value_names:
        for line in enum_body.splitlines():
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            # Extract the value name before '=' or ','
            m = re.match(r'(\w+)\s*[=,]', line)
            if m:
                value_names.append(m.group(1))
    # If there are duplicates, this is a failure (should not happen after the transform)
    duplicates = set([x for x in value_names if value_names.count(x) > 1])
    assert not duplicates, f"Duplicate enum value names found in generated TypeScript code: {duplicates}"
