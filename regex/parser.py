from regex.tokenizer import Token, TokenType, tokenize_regex
from regex.ast_nodes import (
    RegexNode, CharNode, EpsilonNode, ConcatNode, UnionNode,
    StarNode, PlusNode, OptionNode, CharClassNode, WildcardNode,
    SetDiffNode,
)

# All printable ASCII + common control chars
ALL_CHARS = set(chr(i) for i in range(32, 127)) | {'\t', '\n', '\r'}


class RegexParser:
    """Precedence-climbing parser for YALex regex syntax.

    Precedence (highest to lowest):
      1. # (set difference)
      2. *, +, ? (postfix)
      3. concatenation (implicit)
      4. | (alternation)
    """

    def __init__(self, tokens: list[Token], definitions: dict[str, RegexNode] = None):
        self.tokens = tokens
        self.pos = 0
        self.definitions = definitions or {}

    def peek(self) -> Token | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        tok = self.peek()
        if tok is None or tok.type != token_type:
            raise ValueError(f"Expected {token_type}, got {tok}")
        return self.consume()

    def parse(self) -> RegexNode:
        """Parse the full token stream into a regex AST."""
        if not self.tokens:
            return EpsilonNode()
        node = self._parse_union()
        if self.pos < len(self.tokens):
            raise ValueError(f"Unexpected token: {self.tokens[self.pos]}")
        return node

    def _parse_union(self) -> RegexNode:
        """Parse alternation: expr ('|' expr)*"""
        left = self._parse_concat()
        while self.peek() and self.peek().type == TokenType.PIPE:
            self.consume()  # skip |
            right = self._parse_concat()
            left = UnionNode(left, right)
        return left

    def _parse_concat(self) -> RegexNode:
        """Parse concatenation: expr (CONCAT expr)*"""
        left = self._parse_hash()
        while self.peek() and self.peek().type == TokenType.CONCAT:
            self.consume()  # skip CONCAT
            right = self._parse_hash()
            left = ConcatNode(left, right)
        return left

    def _parse_hash(self) -> RegexNode:
        """Parse set difference: expr ('#' expr)*"""
        left = self._parse_postfix()
        while self.peek() and self.peek().type == TokenType.HASH:
            self.consume()  # skip #
            right = self._parse_postfix()
            left = SetDiffNode(left, right)
        return left

    def _parse_postfix(self) -> RegexNode:
        """Parse postfix operators: atom ('*' | '+' | '?')*"""
        node = self._parse_atom()
        while self.peek() and self.peek().type in (TokenType.STAR, TokenType.PLUS, TokenType.QUESTION):
            tok = self.consume()
            if tok.type == TokenType.STAR:
                node = StarNode(node)
            elif tok.type == TokenType.PLUS:
                node = PlusNode(node)
            elif tok.type == TokenType.QUESTION:
                node = OptionNode(node)
        return node

    def _parse_atom(self) -> RegexNode:
        """Parse an atomic regex expression."""
        tok = self.peek()
        if tok is None:
            raise ValueError("Unexpected end of regex")

        # Character literal
        if tok.type == TokenType.CHAR:
            self.consume()
            return CharNode(tok.value)

        # Grouping: (expr)
        if tok.type == TokenType.LPAREN:
            self.consume()
            node = self._parse_union()
            self.expect(TokenType.RPAREN)
            return node

        # Character set: [...] or [^...]
        if tok.type == TokenType.LBRACKET:
            return self._parse_charset()

        # Wildcard: _
        if tok.type == TokenType.UNDERSCORE:
            self.consume()
            return WildcardNode()

        # Named reference
        if tok.type == TokenType.IDENT:
            self.consume()
            name = tok.value
            if name not in self.definitions:
                raise ValueError(f"Undefined regex name: {name}")
            return self.definitions[name]

        # EOF keyword
        if tok.type == TokenType.EOF_TOKEN:
            self.consume()
            # EOF is represented as a special character that won't appear in normal input
            return CharNode('\x00')

        raise ValueError(f"Unexpected token in regex: {tok}")

    def _parse_charset(self) -> RegexNode:
        """Parse a character set: [chars], [^chars], with ranges and strings."""
        self.expect(TokenType.LBRACKET)
        negated = False
        if self.peek() and self.peek().type == TokenType.CARET:
            self.consume()
            negated = True

        chars = set()
        char_list = []

        # Collect all CHAR tokens inside the brackets
        while self.peek() and self.peek().type != TokenType.RBRACKET:
            tok = self.peek()
            if tok.type == TokenType.CHAR:
                self.consume()
                char_list.append(tok.value)
            elif tok.type == TokenType.DASH:
                self.consume()
                char_list.append('-')
            else:
                raise ValueError(f"Unexpected token in charset: {tok}")

        self.expect(TokenType.RBRACKET)

        # Process char_list: detect ranges like 'a' - 'z'
        i = 0
        while i < len(char_list):
            if i + 2 < len(char_list) and char_list[i + 1] == '-':
                # Range: c1 - c2
                c1 = char_list[i]
                c2 = char_list[i + 2]
                for code in range(ord(c1), ord(c2) + 1):
                    chars.add(chr(code))
                i += 3
            else:
                chars.add(char_list[i])
                i += 1

        if negated:
            chars = ALL_CHARS - chars

        return CharClassNode(chars)


def parse_regex(regex_str: str, definitions: dict[str, RegexNode] = None) -> RegexNode:
    """Convenience function: tokenize and parse a YALex regex string."""
    tokens = tokenize_regex(regex_str)
    parser = RegexParser(tokens, definitions)
    return parser.parse()
