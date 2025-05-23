import tempfile
import os
import pytest
from def_file_loader import build_model_from_file_recursive

def test_enum_inheritance_from_non_enum_type_fails_model_building():
    """
    Tests that attempting to inherit an enum from a non-existent enum
    (e.g., a C++ type name like 'int16' used in the DSL inheritance syntax)
    causes model building to fail, as 'int16' is not a valid enum reference.
    """
    dsl_content = """
    namespace TestInvalidParent {
        enum MyStatus : int16 { // 'int16' is not a defined enum in the DSL
            OK = 0;
            ERROR = 1;
        }
    }
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        def_path = os.path.join(tmpdir, "invalid_enum_parent.def")
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(dsl_content)
        expected_error_pattern = (
            r"Cannot resolve parent enum 'int16' for enum '([\w:]+::)?MyStatus'|"
            r"Unresolved parent enum 'int16' for '([\w:]+::)?MyStatus'"
        )
        with pytest.raises(RuntimeError, match=expected_error_pattern):
            build_model_from_file_recursive(def_path)

def test_message_inheritance_from_non_message_type_fails_model_building():
    """
    Tests that attempting to inherit a message from a non-existent message
    (e.g., a C++ type name like 'int16' used in the DSL inheritance syntax)
    causes model building to fail, as 'int16' is not a valid message reference.
    """
    dsl_content = """
    namespace TestInvalidParent {
        message MyMessage : int16 { // 'int16' is not a defined message in the DSL
            value: int;
        }
    }
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        def_path = os.path.join(tmpdir, "invalid_message_parent.def")
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(dsl_content)
        expected_error_pattern = (
            r"Cannot resolve parent message 'int16' for message '([\w:]+::)?MyMessage'|"
            r"Unresolved parent message 'int16' for '([\w:]+::)?MyMessage'"
        )
        with pytest.raises(RuntimeError, match=expected_error_pattern):
            build_model_from_file_recursive(def_path)
