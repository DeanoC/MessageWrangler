import pathlib
from lark_parser import parse_message_dsl

def test_options_def():
    def_path = pathlib.Path(__file__).parent.parent / "def" / "test_options.def"
    with open(def_path, encoding="utf-8") as f:
        text = f.read()
    tree = parse_message_dsl(text)
    pretty = tree.pretty()
    assert 'OptionsTest' in pretty, pretty
    assert 'options_type' in pretty, pretty
    assert 'field_default' in pretty or 'optional' in pretty, pretty

def test_multiline_def():
    def_path = pathlib.Path(__file__).parent.parent / "def" / "test_multiline.def"
    with open(def_path, encoding="utf-8") as f:
        text = f.read()
    tree = parse_message_dsl(text)
    pretty = tree.pretty()
    assert 'MultiLineMessage' in pretty, pretty
    assert 'DetailedMessage' in pretty, pretty
    assert 'enum_type' in pretty, pretty
    assert 'compound_type' in pretty, pretty
    assert 'inheritance' in pretty, pretty

def test_namespace_inheritance_def():
    def_path = pathlib.Path(__file__).parent.parent / "def" / "test_namespace_inheritance.def"
    with open(def_path, encoding="utf-8") as f:
        text = f.read()
    tree = parse_message_dsl(text)
    pretty = tree.pretty()
    assert 'ue_sh4c_comms' in pretty, pretty
    assert 'Base' in pretty, pretty
    assert 'Reply' in pretty, pretty
    assert 'ChangeModeReply' in pretty, pretty
    assert 'inheritance' in pretty, pretty

if __name__ == "__main__":
    test_options_def()
    test_multiline_def()
    test_namespace_inheritance_def()
    print("All tests passed.")
