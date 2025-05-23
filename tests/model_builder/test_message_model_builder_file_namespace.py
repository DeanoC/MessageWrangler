from lark_parser import parse_message_dsl
from def_file_loader import _build_model_from_lark_tree
from message_model import Namespace

def test_file_level_namespace_is_created_and_populated():
    dsl = '''
    // File-level (global) message
    message GlobalMsg { x: int }
    // Namespaced message
    namespace Foo { message Bar { y: int } }
    '''
    tree = parse_message_dsl(dsl)
    model = _build_model_from_lark_tree(tree, "test")
    # The file-level namespace should be the default (e.g., 'test' or None)
    # Find the file-level namespace (should match the model's main_file_path if set, else fallback)
    file_ns = getattr(model, 'main_file_path', None)
    if file_ns:
        file_ns = file_ns.split('/')[-1].split('\\')[-1].split('.')[0]
    else:
        file_ns = 'test'  # fallback for in-memory DSL
    # The file-level namespace should exist in model.namespaces
    assert file_ns in model.namespaces, f"File-level namespace '{file_ns}' missing in model.namespaces: {list(model.namespaces.keys())}"
    ns_obj = model.namespaces[file_ns]
    assert isinstance(ns_obj, Namespace)
    # The global message should be attached to the file-level namespace
    assert 'GlobalMsg' in ns_obj.messages, f"GlobalMsg not found in file-level namespace messages: {list(ns_obj.messages.keys())}"
    # The namespaced message should be in its own namespace
    assert 'Foo' in model.namespaces
    assert 'Bar' in model.namespaces['Foo'].messages
