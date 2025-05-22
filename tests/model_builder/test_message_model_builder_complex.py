"""
Additional tests for build_model_from_lark_tree with more complex message/enum/comment/inheritance cases.
"""
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import _build_model_from_lark_tree
from message_model import FieldType

def test_multiple_enums_and_messages_with_comments():
    dsl = '''
    /// Enum for status
    enum Status {
        OK = 0,
        /// Error value
        ERROR = 1
    }
    /// User message
    message User {
        id: int
        /// The user's name
        name: string
    }
    /// Admin message inherits User
    message Admin : User {
        level: int
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # Enum
    enum = model.get_enum("Status")
    assert enum is not None
    assert enum.description.strip().startswith("/// Enum for status")
    assert [v.name for v in enum.values] == ["OK", "ERROR"]
    assert [v.value for v in enum.values] == [0, 1]
    # Messages
    user = model.get_message("User")
    assert user is not None
    assert user.description.strip().startswith("/// User message")
    assert len(user.fields) == 2
    assert user.fields[0].name == "id"
    assert user.fields[0].field_type == FieldType.INT
    assert user.fields[1].name == "name"
    assert user.fields[1].field_type == FieldType.STRING
    admin = model.get_message("Admin")
    assert admin is not None
    assert admin.parent == "User"
    assert admin.description.strip().startswith("/// Admin message inherits User")
    assert len(admin.fields) == 1
    assert admin.fields[0].name == "level"
    assert admin.fields[0].field_type == FieldType.INT

def test_enum_and_message_with_interleaved_comments():
    dsl = '''
    // Local comment
    /// Enum with interleaved comments
    enum Interleaved {
        // Local comment
        FIRST = 1,
        /// Second value
        SECOND = 2
    }
    // Local comment
    /// Message with interleaved comments
    message InterMsg {
        // Local comment
        foo: string
        /// Bar field
        bar: int
    }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    enum = model.get_enum("Interleaved")
    assert enum is not None
    assert enum.description.strip().startswith("/// Enum with interleaved comments")
    assert [v.name for v in enum.values] == ["FIRST", "SECOND"]
    assert [v.value for v in enum.values] == [1, 2]
    msg = model.get_message("InterMsg")
    assert msg is not None
    assert msg.description.strip().startswith("/// Message with interleaved comments")
    assert len(msg.fields) == 2
    assert msg.fields[0].name == "foo"
    assert msg.fields[0].field_type == FieldType.STRING
    assert msg.fields[1].name == "bar"
    assert msg.fields[1].field_type == FieldType.INT
