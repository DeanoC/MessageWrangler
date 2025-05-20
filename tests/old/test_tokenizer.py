import unittest
from tokenizer import Tokenizer

class TestTokenizer(unittest.TestCase):
    def test_simple_field(self):
        text = 'myField: int;'
        tokenizer = Tokenizer(text)
        expected = [
            ('IDENT', 'myField'),
            ('COLON', ':'),
            ('IDENT', 'int'),
            ('SEMICOLON', ';')
        ]
        self.assertEqual(tokenizer.tokens, expected)

    def test_enum_inline(self):
        text = 'status: enum { OK = 0, ERROR = 1, PENDING = 2 }'
        tokenizer = Tokenizer(text)
        expected = [
            ('IDENT', 'status'),
            ('COLON', ':'),
            ('IDENT', 'enum'),
            ('LBRACE', '{'),
            ('IDENT', 'OK'),
            ('EQUALS', '='),
            ('NUMBER', '0'),
            ('COMMA', ','),
            ('IDENT', 'ERROR'),
            ('EQUALS', '='),
            ('NUMBER', '1'),
            ('COMMA', ','),
            ('IDENT', 'PENDING'),
            ('EQUALS', '='),
            ('NUMBER', '2'),
            ('RBRACE', '}')
        ]
        self.assertEqual(tokenizer.tokens, expected)

    def test_multiline_enum(self):
        text = 'status: enum {\n  OK = 0,\n  ERROR = 1,\n  PENDING = 2\n}'
        tokenizer = Tokenizer(text)
        # Remove SKIP and NEWLINE tokens for comparison
        filtered = [t for t in tokenizer.tokens if t[0] not in ('SKIP', 'NEWLINE')]
        expected = [
            ('IDENT', 'status'),
            ('COLON', ':'),
            ('IDENT', 'enum'),
            ('LBRACE', '{'),
            ('IDENT', 'OK'),
            ('EQUALS', '='),
            ('NUMBER', '0'),
            ('COMMA', ','),
            ('IDENT', 'ERROR'),
            ('EQUALS', '='),
            ('NUMBER', '1'),
            ('COMMA', ','),
            ('IDENT', 'PENDING'),
            ('EQUALS', '='),
            ('NUMBER', '2'),
            ('RBRACE', '}')
        ]
        self.assertEqual(filtered, expected)

    def test_options(self):
        text = 'flags: options { READ = 1, WRITE = 2, EXEC = 4 }'
        tokenizer = Tokenizer(text)
        filtered = [t for t in tokenizer.tokens if t[0] not in ('SKIP', 'NEWLINE')]
        expected = [
            ('IDENT', 'flags'),
            ('COLON', ':'),
            ('IDENT', 'options'),
            ('LBRACE', '{'),
            ('IDENT', 'READ'),
            ('EQUALS', '='),
            ('NUMBER', '1'),
            ('COMMA', ','),
            ('IDENT', 'WRITE'),
            ('EQUALS', '='),
            ('NUMBER', '2'),
            ('COMMA', ','),
            ('IDENT', 'EXEC'),
            ('EQUALS', '='),
            ('NUMBER', '4'),
            ('RBRACE', '}')
        ]
        self.assertEqual(filtered, expected)

    def test_string_and_comment(self):
        text = 'name: string // this is a comment'
        tokenizer = Tokenizer(text)
        filtered = [t for t in tokenizer.tokens if t[0] not in ('SKIP', 'NEWLINE', 'COMMENT')]
        expected = [
            ('IDENT', 'name'),
            ('COLON', ':'),
            ('IDENT', 'string')
        ]
        self.assertEqual(filtered, expected)

if __name__ == '__main__':
    unittest.main()
