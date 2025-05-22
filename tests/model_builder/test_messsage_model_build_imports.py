import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree



def test_model_builder_recursive_import_merges_namespaces_and_messages():
    # Use real .def files in tests/def/
    import os
    from message_model_builder import build_model_from_file_recursive
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'def')
    main_def = os.path.abspath(os.path.join(test_dir, 'main.def'))
    model = build_model_from_file_recursive(main_def)
    # The model should now contain messages from both main.def and base.def
    # Check that imported namespace 'Base' and its messages are present
    assert 'base::BaseMessage' in model.messages, "base::BaseMessage from base.def should be present in merged model"
    assert 'base::AnotherBaseMessage' in model.messages, "base::AnotherBaseMessage from base.def should be present in merged model"
    assert 'main::MainMessage' in model.messages, "main::MainMessage from main.def should be present in merged model"
    assert 'main::DerivedMessage' in model.messages, "main::DerivedMessage from main.def should be present in merged model"
    # Check that cross-file inheritance is resolved
    main_msg = model.get_message('main::MainMessage')
    assert main_msg is not None
    assert main_msg.parent == 'Base::BaseMessage' or main_msg.parent == 'BaseMessage'
    derived_msg = model.get_message('main::DerivedMessage')
    assert derived_msg is not None
    assert derived_msg.parent == 'Base::AnotherBaseMessage' or derived_msg.parent == 'AnotherBaseMessage'