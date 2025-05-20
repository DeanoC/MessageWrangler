import pathlib
import pytest
from lark_parser import parse_message_dsl

def test_enum_references_def():
    def_path = pathlib.Path(__file__).parent.parent / "def" / "test_enum_references.def"
    with open(def_path, encoding="utf-8") as f:
        text = f.read()
    tree = parse_message_dsl(text)
    pretty = tree.pretty()
    # Check for key constructs from the .def file
    assert 'EnumContainer' in pretty, pretty
    assert 'EnumUser' in pretty, pretty
    assert 'NamespacedEnum' in pretty, pretty
    assert 'NamespacedEnumUser' in pretty, pretty
    assert 'MultipleEnums' in pretty, pretty
    assert 'MultipleEnumUser' in pretty, pretty
    assert 'ExtendedEnumUser' in pretty or 'ExtendedNamespacedEnumUser' in pretty or 'ExtendedMultipleEnumUser' in pretty, pretty
    assert 'enum_type' in pretty or 'ref_type' in pretty, pretty

if __name__ == "__main__":
    test_enum_references_def()
    print("Test passed.")
