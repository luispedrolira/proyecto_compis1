from automata.models import NFA, DFA


def nfa_to_dfa(nfa: NFA) -> DFA:
    """Convert an NFA to a DFA using subset construction."""
    dfa = DFA()
    alphabet = nfa.get_alphabet()
    dfa.alphabet = alphabet

    # Map frozenset of NFA states -> DFA state id
    state_map: dict[frozenset[int], int] = {}
    next_id = 0

    start_closure = nfa.epsilon_closure({nfa.start})
    state_map[start_closure] = next_id
    _add_dfa_state(dfa, next_id, start_closure, nfa)
    dfa.start = next_id
    next_id += 1

    worklist = [start_closure]

    while worklist:
        current = worklist.pop()
        current_id = state_map[current]

        for symbol in alphabet:
            # Compute move(current, symbol)
            move_set = set()
            for s in current:
                for target in nfa.transitions.get(s, {}).get(symbol, set()):
                    move_set.add(target)

            if not move_set:
                continue

            next_closure = nfa.epsilon_closure(move_set)

            if next_closure not in state_map:
                state_map[next_closure] = next_id
                _add_dfa_state(dfa, next_id, next_closure, nfa)
                next_id += 1
                worklist.append(next_closure)

            dfa.add_transition(current_id, symbol, state_map[next_closure])

    return dfa


def _add_dfa_state(dfa: DFA, state_id: int, nfa_states: frozenset[int], nfa: NFA):
    """Add a DFA state, determining accept status from constituent NFA states."""
    best_action = None
    best_priority = None

    for nfa_sid in nfa_states:
        nfa_state = nfa.states[nfa_sid]
        if nfa_state.is_accept and nfa_state.accept_action is not None:
            if best_priority is None or nfa_state.accept_priority < best_priority:
                best_action = nfa_state.accept_action
                best_priority = nfa_state.accept_priority

    dfa.add_state(state_id, best_action, best_priority)
