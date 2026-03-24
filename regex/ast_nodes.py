from dataclasses import dataclass, field
from typing import Optional


class RegexNode:
    """Base class for all regex AST nodes."""
    pass


@dataclass
class CharNode(RegexNode):
    """A single literal character."""
    char: str


@dataclass
class EpsilonNode(RegexNode):
    """Empty string (epsilon)."""
    pass


@dataclass
class ConcatNode(RegexNode):
    """Concatenation of two regexes."""
    left: RegexNode
    right: RegexNode


@dataclass
class UnionNode(RegexNode):
    """Alternation (r1 | r2)."""
    left: RegexNode
    right: RegexNode


@dataclass
class StarNode(RegexNode):
    """Kleene closure (r*)."""
    child: RegexNode


@dataclass
class PlusNode(RegexNode):
    """Positive closure (r+). Sugar for r followed by r*."""
    child: RegexNode


@dataclass
class OptionNode(RegexNode):
    """Optional (r?). Sugar for r | epsilon."""
    child: RegexNode


@dataclass
class CharClassNode(RegexNode):
    """A character class [charset] or [^charset].
    Stores the explicit set of characters that match.
    For negated classes, the complement is computed at parse time.
    """
    chars: set = field(default_factory=set)


@dataclass
class WildcardNode(RegexNode):
    """Matches any single character (_)."""
    pass


@dataclass
class SetDiffNode(RegexNode):
    """Set difference (r1 # r2). Both operands must be CharClassNode."""
    left: RegexNode
    right: RegexNode
