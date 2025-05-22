import pytest
from lark_parser import parse_message_dsl

def test_import_statement_parsing():
    dsl = '''
    import "base.def" as Base
    namespace ClientCommands {
        message CommCommand : Base::Command {
            foo: int
        }
    }
    '''
    tree = parse_message_dsl(dsl)
    pretty = tree.pretty()
    # Should contain import statement and reference to Base::Command as qualified_name_with_dot
    assert 'import' in pretty, pretty
    assert 'Base' in pretty, pretty
    assert 'CommCommand' in pretty, pretty
    assert 'qualified_name_with_dot' in pretty, pretty
    assert 'Base' in pretty and 'Command' in pretty, pretty
    # Should parse the parent reference as an inheritance node
    assert 'inheritance' in pretty, pretty
