import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_model_from_lark_tree

def test_message_inheritance_sets_parent():
    dsl = '''
    namespace Base {
        message BaseMessage { baseField: string }
    }
    message MainMessage : Base::BaseMessage { mainField: string }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # MainMessage should have parent 'Base::BaseMessage'
    msg = model.messages.get('test::MainMessage')
    assert msg is not None, 'test::MainMessage not found in model.messages'
    assert getattr(msg, 'parent', None) == 'Base::BaseMessage', f"Expected parent 'Base::BaseMessage', got {getattr(msg, 'parent', None)}"
    # BaseMessage should have no parent
    base_msg = model.namespaces['Base'].messages.get('BaseMessage')
    assert base_msg is not None, 'BaseMessage not found in Base namespace'
    assert getattr(base_msg, 'parent', None) is None, f"Expected no parent for BaseMessage, got {getattr(base_msg, 'parent', None)}"
