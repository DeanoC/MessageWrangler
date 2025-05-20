import pathlib
from lark_parser import parse_message_dsl

def test_duplicate_fields_def():
    def_path = pathlib.Path(__file__).parent.parent / "def" / "test_duplicate_fields.def"
    with open(def_path, encoding="utf-8") as f:
        text = f.read()
    tree = parse_message_dsl(text)
    pretty = tree.pretty()
    assert 'ParentMessage' in pretty, pretty
    assert 'ChildMessage' in pretty, pretty
    assert 'DuplicateFieldsMessage' in pretty, pretty
    assert 'field' in pretty or 'message_body' in pretty, pretty

def test_default_values_def():
    def_path = pathlib.Path(__file__).parent.parent / "def" / "test_default_values.def"
    with open(def_path, encoding="utf-8") as f:
        text = f.read()
    tree = parse_message_dsl(text)
    pretty = tree.pretty()
    assert 'DefaultValuesMessage' in pretty, pretty
    assert 'field_default' in pretty, pretty
    assert 'optional' in pretty or 'optionalWithDefault' in pretty, pretty

def test_standalone_enum_def():
    def_path = pathlib.Path(__file__).parent.parent / "def" / "test_standalone_enum.def"
    with open(def_path, encoding="utf-8") as f:
        text = f.read()
    tree = parse_message_dsl(text)
    pretty = tree.pretty()
    assert 'TestEnum' in pretty, pretty
    assert 'TestOpenEnum' in pretty or 'open_enum' in pretty, pretty
    assert 'TestEnumWithInheritance' in pretty, pretty
    assert 'NamespacedEnum' in pretty, pretty
    assert 'TestMessage' in pretty, pretty
    assert 'enum_type' in pretty or 'enum_def' in pretty, pretty

if __name__ == "__main__":
    test_duplicate_fields_def()
    test_default_values_def()
    test_standalone_enum_def()
    print("All tests passed.")
