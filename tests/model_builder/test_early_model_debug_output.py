import os
import glob
import pytest
from lark_parser import parse_message_dsl
from def_file_loader import _build_early_model_from_lark_tree
from model_debug import debug_print_early_model

def_files = glob.glob(os.path.join(os.path.dirname(__file__), '../def/*.def'))
def_files = [os.path.abspath(f) for f in def_files if not any(x in os.path.basename(f) for x in ['invalid', 'corner_case'])]

def pytest_generate_tests(metafunc):
    if 'def_file' in metafunc.fixturenames:
        metafunc.parametrize('def_file', def_files)

def test_early_model_debug_output_matches_def(def_file, capsys):
    with open(def_file, 'r', encoding='utf-8') as f:
        text = f.read()
    tree = parse_message_dsl(text)
    early_model = _build_early_model_from_lark_tree(tree, os.path.splitext(os.path.basename(def_file))[0], source_file=def_file)
    debug_print_early_model(early_model)
    out = capsys.readouterr().out
    # Basic sanity: the output should mention the file
    assert os.path.basename(def_file) in out

    # Check that every message, enum, and namespace name in the .def appears in the debug output
    import re
    # Only match identifiers that are not keywords and not in comments
    keywords = {"message", "enum", "open_enum", "namespace", "Map", "string", "int", "float", "bool", "byte", "options"}
    # Remove comments from text
    def remove_comments(s):
        s = re.sub(r"//.*", "", s)
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
        s = re.sub(r"///.*", "", s)
        return s
    clean_text = remove_comments(text)
    msg_names = re.findall(r'\bmessage\s+([A-Za-z_][A-Za-z0-9_]*)', clean_text)
    enum_names = re.findall(r'\benum\s+([A-Za-z_][A-Za-z0-9_]*)', clean_text)
    open_enum_names = re.findall(r'\bopen_enum\s+([A-Za-z_][A-Za-z0-9_]*)', clean_text)
    ns_names = re.findall(r'\bnamespace\s+([A-Za-z_][A-Za-z0-9_]*)', clean_text)
    all_names = set(msg_names + enum_names + open_enum_names + ns_names)
    for name in all_names:
        assert name in out, f"Name '{name}' from {def_file} missing in debug output!"

    # Check that all field names in the .def appear in the debug output, but skip keywords and type names
    field_names = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*:', clean_text)
    for fname in field_names:
        if fname not in all_names and fname not in keywords:
            assert fname in out, f"Field '{fname}' from {def_file} missing in debug output!"
