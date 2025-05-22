from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree

def test_model_namespace_always_includes_file_namespace():
    dsl = '''
    // File-level (global) message
    message FileLevelMsg { x: int }
    // Namespaced message
    namespace Foo { message Bar { y: int } }
    '''
    tree = parse_message_dsl(dsl)
    model = build_model_from_lark_tree(tree, "test") # Pass the expected file namespace for in-memory DSL
    # The file-level namespace should be present in model.namespaces
    file_ns = getattr(model, 'main_file_path', None)
    if file_ns:
        file_ns = file_ns.split('/')[-1].split('\\')[-1].split('.')[0]
    else:
        file_ns = 'test'  # fallback for in-memory DSL
    assert file_ns in model.namespaces, f"File-level namespace '{file_ns}' missing in model.namespaces: {list(model.namespaces.keys())}"
    # All namespaces in the model should be present in model.namespaces
    for msg in model.messages.values():
        ns = getattr(msg, 'namespace', None)
        if ns:
            assert ns in model.namespaces, f"Namespace '{ns}' from message not found in model.namespaces: {list(model.namespaces.keys())}"