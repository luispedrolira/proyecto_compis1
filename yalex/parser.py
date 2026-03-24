from yalex.models import YAlexSpec, NamedDef, Rule, PatternAction


def parse_yalex(text: str) -> YAlexSpec:
    """Parse a YALex (.yal) file into a YAlexSpec."""
    spec = YAlexSpec()

    # Step 1: Strip comments (* ... *)
    text = _strip_comments(text)

    pos = 0
    length = len(text)

    # Step 2: Parse optional header { ... }
    pos = _skip_whitespace(text, pos)
    if pos < length and text[pos] == '{':
        header, pos = _extract_braced_block(text, pos)
        spec.header = header

    # Step 3: Parse let definitions
    pos = _skip_whitespace(text, pos)
    while pos < length and text[pos:pos+3] == 'let':
        name, regex_str, pos = _parse_let(text, pos)
        spec.definitions.append(NamedDef(name, regex_str))
        pos = _skip_whitespace(text, pos)

    # Step 4: Parse rule
    pos = _skip_whitespace(text, pos)
    if pos < length and text[pos:pos+4] == 'rule':
        rule, pos = _parse_rule(text, pos)
        spec.rules.append(rule)

    # Step 5: Parse optional trailer { ... }
    pos = _skip_whitespace(text, pos)
    if pos < length and text[pos] == '{':
        trailer, pos = _extract_braced_block(text, pos)
        spec.trailer = trailer

    return spec


def _strip_comments(text: str) -> str:
    """Remove all (* ... *) comments, supporting nesting."""
    result = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == '(' and text[i + 1] == '*':
            depth = 1
            i += 2
            while i < len(text) and depth > 0:
                if i + 1 < len(text) and text[i] == '(' and text[i + 1] == '*':
                    depth += 1
                    i += 2
                elif i + 1 < len(text) and text[i] == '*' and text[i + 1] == ')':
                    depth -= 1
                    i += 2
                else:
                    i += 1
            # Replace comment with a space to preserve token boundaries
            result.append(' ')
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)


def _skip_whitespace(text: str, pos: int) -> int:
    """Skip whitespace characters."""
    while pos < len(text) and text[pos] in ' \t\n\r':
        pos += 1
    return pos


def _extract_braced_block(text: str, pos: int) -> tuple[str, int]:
    """Extract content between balanced { }, starting at the opening brace.
    Returns (content, position after closing brace).
    """
    if text[pos] != '{':
        raise ValueError(f"Expected '{{' at position {pos}")
    depth = 1
    start = pos + 1
    pos += 1
    while pos < len(text) and depth > 0:
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
        pos += 1
    content = text[start:pos - 1].strip()
    return content, pos


def _parse_let(text: str, pos: int) -> tuple[str, str, int]:
    """Parse: let ident = regexp
    Returns (name, regex_str, new_pos).
    """
    # Skip 'let'
    pos += 3
    pos = _skip_whitespace(text, pos)

    # Read identifier
    start = pos
    while pos < len(text) and (text[pos].isalnum() or text[pos] == '_'):
        pos += 1
    name = text[start:pos]
    if not name:
        raise ValueError(f"Expected identifier after 'let' at position {start}")

    pos = _skip_whitespace(text, pos)

    # Expect '='
    if pos >= len(text) or text[pos] != '=':
        raise ValueError(f"Expected '=' after 'let {name}' at position {pos}")
    pos += 1
    pos = _skip_whitespace(text, pos)

    # Read regex until next 'let', 'rule', or '{' (for trailer)
    regex_start = pos
    while pos < len(text):
        remaining = text[pos:]
        # Check for next keyword boundary
        if remaining.startswith('let ') or remaining.startswith('let\t') or remaining.startswith('let\n'):
            break
        if remaining.startswith('rule ') or remaining.startswith('rule\t') or remaining.startswith('rule\n'):
            break
        if text[pos] == '{':
            # Could be trailer - but only if not inside quotes
            break
        pos += 1

    regex_str = text[regex_start:pos].strip()
    return name, regex_str, pos


def _parse_rule(text: str, pos: int) -> tuple[Rule, int]:
    """Parse: rule entrypoint [args] = pattern { action } | ...
    Returns (Rule, new_pos).
    """
    # Skip 'rule'
    pos += 4
    pos = _skip_whitespace(text, pos)

    # Read entrypoint name
    start = pos
    while pos < len(text) and (text[pos].isalnum() or text[pos] == '_'):
        pos += 1
    entrypoint = text[start:pos]

    pos = _skip_whitespace(text, pos)

    # Skip optional arguments until '='
    while pos < len(text) and text[pos] != '=':
        pos += 1
    if pos >= len(text):
        raise ValueError("Expected '=' in rule definition")
    pos += 1  # skip '='
    pos = _skip_whitespace(text, pos)

    rule = Rule(entrypoint)
    priority = 0

    # Parse first pattern (no leading |)
    regex_str, action, pos = _parse_pattern_action(text, pos)
    rule.patterns.append(PatternAction(regex_str, action, priority))
    priority += 1

    # Parse remaining patterns with leading |
    pos = _skip_whitespace(text, pos)
    while pos < len(text) and text[pos] == '|':
        pos += 1  # skip |
        pos = _skip_whitespace(text, pos)
        regex_str, action, pos = _parse_pattern_action(text, pos)
        rule.patterns.append(PatternAction(regex_str, action, priority))
        priority += 1
        pos = _skip_whitespace(text, pos)

    return rule, pos


def _parse_pattern_action(text: str, pos: int) -> tuple[str, str | None, int]:
    """Parse a single pattern followed by an optional { action }.
    Returns (regex_str, action_code_or_None, new_pos).
    """
    # Read regex until we hit '{' (action) or '|' (next pattern) or end
    regex_parts = []
    while pos < len(text):
        ch = text[pos]

        # Opening brace starts an action block
        if ch == '{':
            break

        # Pipe starts next pattern (but not inside brackets or quotes)
        if ch == '|':
            break

        # Handle character literals in the regex (don't break on internal chars)
        if ch == "'":
            # Read the whole char literal
            start = pos
            pos += 1
            if pos < len(text) and text[pos] == '\\':
                pos += 2  # escape char
            else:
                pos += 1  # literal char
            if pos < len(text) and text[pos] == "'":
                pos += 1
            regex_parts.append(text[start:pos])
            continue

        # Handle string literals
        if ch == '"':
            start = pos
            pos += 1
            while pos < len(text) and text[pos] != '"':
                if text[pos] == '\\':
                    pos += 1
                pos += 1
            if pos < len(text):
                pos += 1  # closing quote
            regex_parts.append(text[start:pos])
            continue

        # Handle character sets
        if ch == '[':
            start = pos
            pos += 1
            while pos < len(text) and text[pos] != ']':
                if text[pos] == "'":
                    pos += 1
                    if pos < len(text) and text[pos] == '\\':
                        pos += 2
                    else:
                        pos += 1
                    if pos < len(text) and text[pos] == "'":
                        pos += 1
                elif text[pos] == '"':
                    pos += 1
                    while pos < len(text) and text[pos] != '"':
                        if text[pos] == '\\':
                            pos += 1
                        pos += 1
                    if pos < len(text):
                        pos += 1
                else:
                    pos += 1
            if pos < len(text):
                pos += 1  # closing ]
            regex_parts.append(text[start:pos])
            continue

        regex_parts.append(ch)
        pos += 1

    regex_str = ''.join(regex_parts).strip()

    # Parse optional action
    action = None
    pos = _skip_whitespace(text, pos)
    if pos < len(text) and text[pos] == '{':
        action, pos = _extract_braced_block(text, pos)

    return regex_str, action, pos
