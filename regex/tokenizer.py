from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class TokenType(Enum):
    CHAR = auto()       # Literal character
    STAR = auto()       # *
    PLUS = auto()       # +
    QUESTION = auto()   # ?
    PIPE = auto()       # |
    HASH = auto()       # # (set difference)
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    LBRACKET = auto()   # [
    RBRACKET = auto()   # ]
    CARET = auto()      # ^ (negation in charset)
    DASH = auto()       # - (range in charset)
    UNDERSCORE = auto() # _ (wildcard, solo)
    IDENT = auto()      # Named regex reference
    CONCAT = auto()     # Implicit concatenation (inserted by tokenizer)
    EOF_TOKEN = auto()  # Special "eof" keyword


@dataclass
class Token:
    type: TokenType
    value: Optional[str] = None

    def __repr__(self):
        if self.value is not None:
            return f"Token({self.type.name}, {self.value!r})"
        return f"Token({self.type.name})"


ESCAPE_MAP = {
    'n': '\n',
    't': '\t',
    'r': '\r',
    's': ' ',
    '\\': '\\',
    "'": "'",
    '"': '"',
}


def _parse_escape(text: str, pos: int) -> tuple[str, int]:
    """Parse an escape sequence starting at the backslash. Returns (char, new_pos)."""
    if pos >= len(text):
        raise ValueError("Unexpected end of input in escape sequence")
    ch = text[pos]
    if ch in ESCAPE_MAP:
        return ESCAPE_MAP[ch], pos + 1
    raise ValueError(f"Unknown escape sequence: \\{ch}")


def tokenize_regex(text: str) -> list[Token]:
    """Tokenize a YALex regex string into a list of tokens.

    Handles:
    - Character literals: 'c', '\\n', etc.
    - String literals: "abc"
    - Character sets: [...], [^...]
    - Operators: * + ? | #
    - Parentheses: ( )
    - Wildcard: _ (standalone underscore, not inside an identifier)
    - Named references: identifiers (alphabetic words, may contain _)
    - Special keyword: eof
    """
    tokens = []
    pos = 0

    while pos < len(text):
        ch = text[pos]

        # Skip whitespace (outside of quotes/brackets)
        if ch in ' \t\n\r':
            pos += 1
            continue

        # Character literal: 'c' or '\n'
        if ch == "'":
            pos += 1  # skip opening quote
            if pos >= len(text):
                raise ValueError("Unterminated character literal")
            if text[pos] == '\\':
                pos += 1
                char, pos = _parse_escape(text, pos)
            else:
                char = text[pos]
                pos += 1
            if pos >= len(text) or text[pos] != "'":
                raise ValueError("Unterminated character literal")
            pos += 1  # skip closing quote
            tokens.append(Token(TokenType.CHAR, char))
            continue

        # String literal: "abc"
        if ch == '"':
            pos += 1
            while pos < len(text) and text[pos] != '"':
                if text[pos] == '\\':
                    pos += 1
                    char, pos = _parse_escape(text, pos)
                    tokens.append(Token(TokenType.CHAR, char))
                else:
                    tokens.append(Token(TokenType.CHAR, text[pos]))
                    pos += 1
            if pos >= len(text):
                raise ValueError("Unterminated string literal")
            pos += 1  # skip closing quote
            continue

        # Character set: [...] or [^...]
        if ch == '[':
            tokens.append(Token(TokenType.LBRACKET))
            pos += 1
            if pos < len(text) and text[pos] == '^':
                tokens.append(Token(TokenType.CARET))
                pos += 1
            # Tokenize inside brackets until ]
            while pos < len(text) and text[pos] != ']':
                if text[pos] in ' \t\n\r':
                    pos += 1
                    continue
                if text[pos] == "'":
                    pos += 1
                    if pos >= len(text):
                        raise ValueError("Unterminated char literal in charset")
                    if text[pos] == '\\':
                        pos += 1
                        char, pos = _parse_escape(text, pos)
                    else:
                        char = text[pos]
                        pos += 1
                    if pos >= len(text) or text[pos] != "'":
                        raise ValueError("Unterminated char literal in charset")
                    pos += 1
                    tokens.append(Token(TokenType.CHAR, char))
                elif text[pos] == '"':
                    pos += 1
                    while pos < len(text) and text[pos] != '"':
                        if text[pos] == '\\':
                            pos += 1
                            char, pos = _parse_escape(text, pos)
                            tokens.append(Token(TokenType.CHAR, char))
                        else:
                            tokens.append(Token(TokenType.CHAR, text[pos]))
                            pos += 1
                    if pos >= len(text):
                        raise ValueError("Unterminated string in charset")
                    pos += 1
                elif text[pos] == '-':
                    tokens.append(Token(TokenType.DASH))
                    pos += 1
                else:
                    tokens.append(Token(TokenType.CHAR, text[pos]))
                    pos += 1
            if pos >= len(text):
                raise ValueError("Unterminated character set")
            tokens.append(Token(TokenType.RBRACKET))
            pos += 1
            continue

        # Operators
        if ch == '*':
            tokens.append(Token(TokenType.STAR))
            pos += 1
            continue
        if ch == '+':
            tokens.append(Token(TokenType.PLUS))
            pos += 1
            continue
        if ch == '?':
            tokens.append(Token(TokenType.QUESTION))
            pos += 1
            continue
        if ch == '|':
            tokens.append(Token(TokenType.PIPE))
            pos += 1
            continue
        if ch == '#':
            tokens.append(Token(TokenType.HASH))
            pos += 1
            continue
        if ch == '(':
            tokens.append(Token(TokenType.LPAREN))
            pos += 1
            continue
        if ch == ')':
            tokens.append(Token(TokenType.RPAREN))
            pos += 1
            continue

        # FIX: Identifier check comes BEFORE standalone underscore.
        # An identifier can start with a letter OR underscore and contain
        # letters, digits, and underscores (e.g. float_num, my_id, _private).
        # A standalone '_' with no alphanumeric continuation is the wildcard.
        if ch.isalpha() or ch == '_':
            start = pos
            while pos < len(text) and (text[pos].isalnum() or text[pos] == '_'):
                pos += 1
            word = text[start:pos]
            if word == '_':
                # Standalone underscore = wildcard
                tokens.append(Token(TokenType.UNDERSCORE))
            elif word == 'eof':
                tokens.append(Token(TokenType.EOF_TOKEN))
            else:
                tokens.append(Token(TokenType.IDENT, word))
            continue

        raise ValueError(f"Unexpected character in regex: {ch!r} at position {pos}")

    return insert_concat_tokens(tokens)


def _is_atom_end(token: Token) -> bool:
    """Can this token appear at the end of an atom (left side of concat)?"""
    return token.type in (
        TokenType.CHAR, TokenType.RPAREN, TokenType.STAR,
        TokenType.PLUS, TokenType.QUESTION, TokenType.RBRACKET,
        TokenType.UNDERSCORE, TokenType.IDENT, TokenType.EOF_TOKEN,
    )


def _is_atom_start(token: Token) -> bool:
    """Can this token appear at the start of an atom (right side of concat)?"""
    return token.type in (
        TokenType.CHAR, TokenType.LPAREN, TokenType.LBRACKET,
        TokenType.UNDERSCORE, TokenType.IDENT, TokenType.EOF_TOKEN,
    )


def insert_concat_tokens(tokens: list[Token]) -> list[Token]:
    """Insert explicit CONCAT tokens between adjacent atoms.
    Does NOT insert CONCAT inside character sets [...].
    """
    result = []
    bracket_depth = 0
    for i, token in enumerate(tokens):
        result.append(token)
        if token.type == TokenType.LBRACKET:
            bracket_depth += 1
        elif token.type == TokenType.RBRACKET:
            bracket_depth -= 1
        if i + 1 < len(tokens) and bracket_depth == 0:
            if _is_atom_end(token) and _is_atom_start(tokens[i + 1]):
                result.append(Token(TokenType.CONCAT))
    return result