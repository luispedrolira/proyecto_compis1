from automata.models import DFA


def minimize_dfa(dfa: DFA) -> DFA:
    """Minimize a DFA using Hopcroft's algorithm.

    Partitions states by their accept action first, then refines
    until no more splits are possible.
    """
    if not dfa.states:
        return dfa

    # Initial partition: group by accept action (None for non-accepting)
    groups: dict[tuple, set[int]] = {}
    for state_id in dfa.states:
        if state_id in dfa.accept_states:
            key = dfa.accept_states[state_id]  # (action, priority)
        else:
            key = (None, None)
        if key not in groups:
            groups[key] = set()
        groups[key].add(state_id)

    partition = list(groups.values())

    # Build state->partition-index map
    def get_partition_map():
        pmap = {}
        for idx, group in enumerate(partition):
            for s in group:
                pmap[s] = idx
        return pmap

    changed = True
    while changed:
        changed = False
        new_partition = []
        pmap = get_partition_map()

        for group in partition:
            if len(group) <= 1:
                new_partition.append(group)
                continue

            # Try to split this group
            splits: dict[tuple, set[int]] = {}
            for state_id in group:
                # Signature: for each symbol, which partition does the transition go to?
                sig = []
                for symbol in sorted(dfa.alphabet):
                    target = dfa.transitions.get(state_id, {}).get(symbol)
                    if target is not None:
                        sig.append(pmap[target])
                    else:
                        sig.append(-1)  # dead state
                sig_key = tuple(sig)
                if sig_key not in splits:
                    splits[sig_key] = set()
                splits[sig_key].add(state_id)

            if len(splits) > 1:
                changed = True
            new_partition.extend(splits.values())

        partition = new_partition

    # Build minimized DFA
    pmap = get_partition_map()
    min_dfa = DFA()
    min_dfa.alphabet = dfa.alphabet

    # Map partition index -> representative state (lowest id in group)
    rep = {}
    for idx, group in enumerate(partition):
        rep[idx] = min(group)

    # Remap partition indices to sequential IDs
    new_ids = {}
    next_id = 0
    for idx in range(len(partition)):
        new_ids[idx] = next_id
        next_id += 1

    for idx, group in enumerate(partition):
        representative = rep[idx]
        new_id = new_ids[idx]

        accept_action = None
        accept_priority = None
        if representative in dfa.accept_states:
            accept_action, accept_priority = dfa.accept_states[representative]

        min_dfa.add_state(new_id, accept_action, accept_priority)

        if representative == dfa.start or dfa.start in group:
            min_dfa.start = new_id

        for symbol in dfa.alphabet:
            target = dfa.transitions.get(representative, {}).get(symbol)
            if target is not None:
                target_group = pmap[target]
                min_dfa.add_transition(new_id, symbol, new_ids[target_group])

    return min_dfa
