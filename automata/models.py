from dataclasses import dataclass, field
from typing import Optional


@dataclass
class State:
    """A state in an NFA or DFA."""
    id: int
    is_accept: bool = False
    accept_action: Optional[str] = None
    accept_priority: Optional[int] = None


class NFA:
    """Non-deterministic finite automaton."""

    def __init__(self):
        self._next_id = 0
        self.states: dict[int, State] = {}
        # transitions[state_id][symbol] = set of target state ids
        # symbol=None means epsilon transition
        self.transitions: dict[int, dict[Optional[str], set[int]]] = {}
        self.start: Optional[int] = None
        self.accept_states: set[int] = set()

    def new_state(self, is_accept=False, accept_action=None, accept_priority=None) -> State:
        state = State(self._next_id, is_accept, accept_action, accept_priority)
        self.states[state.id] = state
        self.transitions[state.id] = {}
        self._next_id += 1
        return state

    def add_transition(self, from_id: int, symbol: Optional[str], to_id: int):
        if symbol not in self.transitions[from_id]:
            self.transitions[from_id][symbol] = set()
        self.transitions[from_id][symbol].add(to_id)

    def epsilon_closure(self, state_ids: set[int]) -> frozenset[int]:
        """Compute the epsilon closure of a set of states."""
        stack = list(state_ids)
        closure = set(state_ids)
        while stack:
            s = stack.pop()
            for target in self.transitions.get(s, {}).get(None, set()):
                if target not in closure:
                    closure.add(target)
                    stack.append(target)
        return frozenset(closure)

    def get_alphabet(self) -> set[str]:
        """Return all non-epsilon symbols used in transitions."""
        alphabet = set()
        for trans in self.transitions.values():
            for symbol in trans:
                if symbol is not None:
                    alphabet.add(symbol)
        return alphabet


class DFA:
    """Deterministic finite automaton."""

    def __init__(self):
        self.states: set[int] = set()
        # transitions[state_id][symbol] = target state id
        self.transitions: dict[int, dict[str, int]] = {}
        self.start: Optional[int] = None
        # accept_states[state_id] = (action_code, priority)
        self.accept_states: dict[int, tuple[str, int]] = {}
        self.alphabet: set[str] = set()

    def add_state(self, state_id: int, accept_action=None, accept_priority=None):
        self.states.add(state_id)
        if state_id not in self.transitions:
            self.transitions[state_id] = {}
        if accept_action is not None:
            self.accept_states[state_id] = (accept_action, accept_priority)

    def add_transition(self, from_id: int, symbol: str, to_id: int):
        if from_id not in self.transitions:
            self.transitions[from_id] = {}
        self.transitions[from_id][symbol] = to_id

    def simulate(self, input_str: str) -> Optional[tuple[str, int]]:
        """Simulate the DFA on input. Returns (action, priority) if accepted, None otherwise."""
        state = self.start
        for ch in input_str:
            if state in self.transitions and ch in self.transitions[state]:
                state = self.transitions[state][ch]
            else:
                return None
        return self.accept_states.get(state)
