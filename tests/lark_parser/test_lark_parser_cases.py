import pytest
from lark_parser import parse_message_dsl

# Minimal valid message
def test_minimal_message():
    text = """
    message Foo {
        bar: int
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Inline enum, explicit and implicit values
def test_inline_enum():
    text = """
    message Test {
        status: enum { OK = 0, FAIL, UNKNOWN = 5 }
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Top-level enum and reference
def test_top_level_enum_and_reference():
    text = """
    enum MyEnum {
        A = 1,
        B,
        C = 10
    }
    message Ref {
        e: MyEnum
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Enum inheritance
def test_enum_inheritance():
    text = """
    enum BaseEnum {
        X = 1,
        Y
    }
    enum SubEnum : BaseEnum {
        Z = 100
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Compound field
def test_compound_field():
    text = """
    message Vec {
        pos: float { x, y, z }
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Options field
def test_options_field():
    text = """
    message Opt {
        flags: options { A, B, C }
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Namespaces and message inheritance
def test_namespace_and_inheritance():
    text = """
    namespace Outer {
        message Base {
            foo: string
        }
        message Sub : Base {
            bar: int
        }
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Comments everywhere
def test_comments_everywhere():
    text = """
    /// File doc
    // Local file comment
    namespace N {
        /// Namespace doc
        // Local ns comment
        message M {
            /// Field doc
            // Local field comment
            f: int // trailing
        }
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Optional and default value
def test_optional_and_default():
    text = """
    message OptDef {
        optional foo: int
        bar: string = "baz"
    }
    """
    tree = parse_message_dsl(text)
    assert tree

# Import statement
def test_import_statement():
    text = 'import "./other.def" as Other\nmessage M { f: int }'
    tree = parse_message_dsl(text)
    assert tree
