from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PatternAction:
    """A single pattern-action pair in a rule."""
    regex_str: str
    action: Optional[str]  # Python code, or None if no action
    priority: int          # Definition order (lower = higher precedence)


@dataclass
class Rule:
    """A rule entry point with its pattern-action pairs."""
    entrypoint: str
    patterns: list[PatternAction] = field(default_factory=list)


@dataclass
class NamedDef:
    """A named regex definition: let ident = regexp"""
    name: str
    regex_str: str


@dataclass
class YAlexSpec:
    """Complete parsed YALex specification."""
    header: Optional[str] = None
    definitions: list[NamedDef] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    trailer: Optional[str] = None
