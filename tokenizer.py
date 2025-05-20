# tokenizer.py
# Simple tokenizer for MessageWrangler parser refactor

import re
from typing import List, Tuple, Optional

Token = Tuple[str, str]  # (token_type, value)

class Tokenizer:
    def __init__(self, text: str):
        self.text = text
        self.tokens: List[Token] = []
        self.pos = 0
        self._tokenize()

    def _tokenize(self):
        # Define token regex patterns
        token_specification = [
            ('SKIP',      r'[ \t]+'),
            ('NEWLINE',   r'\n'),
            ('COMMENT',   r'//.*'),
            ('LBRACE',    r'\{'),
            ('RBRACE',    r'\}'),
            ('LPAREN',    r'\('),
            ('RPAREN',    r'\)'),
            ('COLON',     r':'),
            ('SEMICOLON', r';'),
            ('COMMA',     r','),
            ('EQUALS',    r'='),
            ('PIPE',      r'\|'),
            ('LT',        r'<'),
            ('GT',        r'>'),
            ('IDENT',     r'[A-Za-z_][A-Za-z0-9_]*'),
            ('NUMBER',    r'\d+(?:\.\d+)?'),
            ('STRING',    r'".*?"'),
            ('OTHER',     r'.'),
        ]
        tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
        get_token = re.compile(tok_regex).match
        line = self.text
        mo = get_token(line)
        while mo is not None:
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'NEWLINE':
                pass
            elif kind == 'SKIP' or kind == 'COMMENT':
                pass
            else:
                self.tokens.append((kind, value))
            self.pos = mo.end()
            mo = get_token(line, self.pos)

    def peek(self) -> Optional[Token]:
        if self.tokens:
            return self.tokens[0]
        return None

    def next(self) -> Optional[Token]:
        if self.tokens:
            return self.tokens.pop(0)
        return None

    def expect(self, token_type: str) -> Token:
        token = self.next()
        if token is None or token[0] != token_type:
            raise SyntaxError(f"Expected token {token_type}, got {token}")
        return token

    def has_tokens(self) -> bool:
        return bool(self.tokens)
