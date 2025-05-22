from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from message_model import FieldType

def test_basic_types_are_not_message_reference():
    dsl = '''
    message BasicTypes {
        s: string
        i: int
        f: float
        b: bool
        by: byte
    }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree, "test")
    msg = model.get_message("BasicTypes")
    assert msg is not None
    assert len(msg.fields) == 5
    assert msg.fields[0].name == "s" and msg.fields[0].field_type == FieldType.STRING
    assert msg.fields[1].name == "i" and msg.fields[1].field_type == FieldType.INT
    assert msg.fields[2].name == "f" and msg.fields[2].field_type == FieldType.FLOAT
    assert msg.fields[3].name == "b" and msg.fields[3].field_type == FieldType.BOOL
    assert msg.fields[4].name == "by" and msg.fields[4].field_type == FieldType.BYTE
    # None should be MESSAGE_REFERENCE
    for field in msg.fields:
        assert field.field_type != FieldType.MESSAGE_REFERENCE, f"Field {field.name} incorrectly marked as MESSAGE_REFERENCE"
