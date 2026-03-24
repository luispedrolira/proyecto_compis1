from automata.models import NFA, State
from regex.ast_nodes import (
    RegexNode, CharNode, EpsilonNode, ConcatNode, UnionNode,
    StarNode, PlusNode, OptionNode, CharClassNode, WildcardNode,
    SetDiffNode,
)
from regex.parser import ALL_CHARS


def _build_fragment(nfa: NFA, node: RegexNode) -> tuple[int, int]:
    """Build an NFA fragment for a regex AST node. Returns (start_id, accept_id)."""

    if isinstance(node, CharNode):
        s = nfa.new_state()
        a = nfa.new_state()
        nfa.add_transition(s.id, node.char, a.id)
        return s.id, a.id

    if isinstance(node, EpsilonNode):
        s = nfa.new_state()
        a = nfa.new_state()
        nfa.add_transition(s.id, None, a.id)
        return s.id, a.id

    if isinstance(node, CharClassNode):
        s = nfa.new_state()
        a = nfa.new_state()
        for ch in node.chars:
            nfa.add_transition(s.id, ch, a.id)
        return s.id, a.id

    if isinstance(node, WildcardNode):
        s = nfa.new_state()
        a = nfa.new_state()
        for ch in ALL_CHARS:
            nfa.add_transition(s.id, ch, a.id)
        return s.id, a.id

    if isinstance(node, ConcatNode):
        s1, a1 = _build_fragment(nfa, node.left)
        s2, a2 = _build_fragment(nfa, node.right)
        nfa.add_transition(a1, None, s2)
        return s1, a2

    if isinstance(node, UnionNode):
        s = nfa.new_state()
        a = nfa.new_state()
        s1, a1 = _build_fragment(nfa, node.left)
        s2, a2 = _build_fragment(nfa, node.right)
        nfa.add_transition(s.id, None, s1)
        nfa.add_transition(s.id, None, s2)
        nfa.add_transition(a1, None, a.id)
        nfa.add_transition(a2, None, a.id)
        return s.id, a.id

    if isinstance(node, StarNode):
        s = nfa.new_state()
        a = nfa.new_state()
        s1, a1 = _build_fragment(nfa, node.child)
        nfa.add_transition(s.id, None, s1)
        nfa.add_transition(s.id, None, a.id)
        nfa.add_transition(a1, None, s1)
        nfa.add_transition(a1, None, a.id)
        return s.id, a.id

    if isinstance(node, PlusNode):
        # r+ = r r*
        concat = ConcatNode(node.child, StarNode(node.child))
        return _build_fragment(nfa, concat)

    if isinstance(node, OptionNode):
        # r? = r | epsilon
        union = UnionNode(node.child, EpsilonNode())
        return _build_fragment(nfa, union)

    if isinstance(node, SetDiffNode):
        # Both operands should be CharClassNode at this point
        if isinstance(node.left, CharClassNode) and isinstance(node.right, CharClassNode):
            diff_chars = node.left.chars - node.right.chars
            return _build_fragment(nfa, CharClassNode(diff_chars))
        raise ValueError("Set difference (#) operands must be character classes")

    raise ValueError(f"Unknown AST node type: {type(node)}")


def build_nfa(node: RegexNode) -> NFA:
    """Build a complete NFA from a single regex AST."""
    nfa = NFA()
    start_id, accept_id = _build_fragment(nfa, node)
    nfa.start = start_id
    nfa.states[accept_id].is_accept = True
    nfa.accept_states.add(accept_id)
    return nfa


def build_combined_nfa(patterns: list[tuple[RegexNode, str, int]]) -> NFA:
    """Build a combined NFA from multiple pattern-action pairs.

    Args:
        patterns: List of (regex_ast, action_code, priority) tuples.
                  Lower priority number = higher precedence (defined first).

    Returns:
        A single NFA with a global start state that has epsilon transitions
        to each pattern's NFA. Accept states are tagged with action and priority.
    """
    nfa = NFA()
    global_start = nfa.new_state()
    nfa.start = global_start.id

    for ast, action, priority in patterns:
        start_id, accept_id = _build_fragment(nfa, ast)
        nfa.add_transition(global_start.id, None, start_id)
        state = nfa.states[accept_id]
        state.is_accept = True
        state.accept_action = action
        state.accept_priority = priority
        nfa.accept_states.add(accept_id)

    return nfa
