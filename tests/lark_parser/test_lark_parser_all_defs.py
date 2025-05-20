import pathlib
import pytest
from lark_parser import parse_message_dsl


def passing_def_files():
    # List of all .def files that should parse successfully
    return [
        "test_unresolved.def",
        "test_standalone_enum.def",
        "test_pipe_options_fixed.def",
        "test_options.def",
        "test_optional.def",
        "test_namespace_inheritance.def",
        "test_namespaces.def",
        "test_multiline_root.def",
        "test_multiline.def",
        "test_messages.def",
        "test_enum_sizes.def",
        "test_enum_single_value.def",
        "test_enum_references.def",
        "test_enum_numbering.def",
        "test_enum_inheritance.def",
        "test_duplicate_messages.def",
        "test_duplicate_fields.def",
        "test_default_values.def",
        "sh4c_comms.def",
        "sh4c_base.def",
        "main.def",
        "base.def",
    ]

def failing_def_files():
    # List of .def files that should fail to parse
    return [
        "test_invalid.def",
    ]


def test_all_def_files():
    folder = pathlib.Path(__file__).parent
    # Files that should parse successfully
    for fname in passing_def_files():
        def_path = folder.parent / "def" / fname
        with open(def_path, encoding="utf-8") as f:
            text = f.read()
        try:
            tree = parse_message_dsl(text)
            pretty = tree.pretty()
            assert any(x in pretty for x in ("message", "enum", "namespace", "field", "options", "compound", "def")), f"No key constructs in {fname}:\n{pretty}"
        except Exception as e:
            print(f"FAILED parsing {fname}: {e}")
            raise
    # Files that should fail to parse
    for fname in failing_def_files():
        def_path = folder.parent / "def" / fname
        with open(def_path, encoding="utf-8") as f:
            text = f.read()
        try:
            tree = parse_message_dsl(text)
        except Exception:
            # Expected to fail
            continue
        raise AssertionError(f"Expected parsing to fail for {fname}, but it succeeded.")

if __name__ == "__main__":
    test_all_def_files()
    print("All .def files parsed successfully.")
