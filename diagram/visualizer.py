"""
DFA diagram visualizer using graphviz.
Generates a transition diagram image from a DFA object.
"""
from __future__ import annotations
import os
from typing import Optional

from automata.models import DFA


def _compress_labels(chars: list[str]) -> str:
    """Compress a list of characters into a readable label.

    Examples:
        ['a','b','c',...,'z'] → '[a-z]'
        ['0','1',...,'9']     → '[0-9]'
        ['a','b']             → 'a|b'
        [' ']                 → ' '
    """
    if not chars:
        return ""
    if len(chars) == 1:
        c = chars[0]
        # Escape special graphviz/dot characters
        return _escape_label(c)

    # Sort by ordinal value
    sorted_chars = sorted(chars, key=ord)

    # Try to find contiguous ranges
    ranges = []
    start = sorted_chars[0]
    end = sorted_chars[0]

    for c in sorted_chars[1:]:
        if ord(c) == ord(end) + 1:
            end = c
        else:
            ranges.append((start, end))
            start = c
            end = c
    ranges.append((start, end))

    # Build compressed label
    parts = []
    for s, e in ranges:
        if s == e:
            parts.append(_escape_label(s))
        elif ord(e) - ord(s) == 1:
            parts.append(_escape_label(s) + _escape_label(e))
        else:
            parts.append(f"{_escape_label(s)}-{_escape_label(e)}")

    if len(parts) == 1 and len(sorted_chars) <= 3:
        return "|".join(_escape_label(c) for c in sorted_chars)

    return "[" + "".join(parts) + "]"


def _escape_label(c: str) -> str:
    """Escape a character for use in a graphviz label."""
    special = {
        '"': '\\"',
        '\\': '\\\\',
        '\n': '\\n',
        '\t': '\\t',
        '\r': '\\r',
        '<': '\\<',
        '>': '\\>',
        '{': '\\{',
        '}': '\\}',
        '|': '\\|',
    }
    return special.get(c, c)


def _short_action(action: str) -> str:
    """Return a short version of an action string for display."""
    if not action:
        return ""
    # Extract token name from: return ("TOKEN", lxm)
    import re
    m = re.search(r'return\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']', action)
    if m:
        return m.group(1)
    if "None" in action:
        return "skip"
    return action[:20].strip()


def render_dfa_diagram(dfa: DFA, output_path: str = "output/diagram") -> Optional[str]:
    """Render a DFA transition diagram to a PNG/SVG file.

    Args:
        dfa: The DFA object from automata/models.py
        output_path: Output file path (without extension, or with .png/.svg)

    Returns:
        Path to the generated image file, or None on failure.
    """
    try:
        import graphviz
    except ImportError:
        print("graphviz not installed. Run: pip install graphviz")
        return None

    # Strip extension if provided — graphviz adds it
    base_path = output_path
    fmt = "png"
    for ext in (".png", ".svg", ".pdf"):
        if output_path.endswith(ext):
            base_path = output_path[: -len(ext)]
            fmt = ext[1:]
            break

    dot = graphviz.Digraph(
        name="DFA",
        graph_attr={
            "rankdir": "LR",
            "fontsize": "12",
            "bgcolor": "white",
        },
        node_attr={"fontsize": "11"},
        edge_attr={"fontsize": "10"},
    )

    # Invisible start arrow
    dot.node("__start__", shape="none", label="")
    dot.edge("__start__", str(dfa.start), label="")

    # Add all states
    for state_id in sorted(dfa.states):
        if state_id in dfa.accept_states:
            action, _priority = dfa.accept_states[state_id]
            token_label = _short_action(action)
            label = f"q{state_id}\\n{token_label}" if token_label else f"q{state_id}"
            dot.node(
                str(state_id),
                label=label,
                shape="doublecircle",
                style="filled",
                fillcolor="lightgreen",
            )
        else:
            dot.node(
                str(state_id),
                label=f"q{state_id}",
                shape="circle",
                style="filled",
                fillcolor="lightblue",
            )

    # Group transitions: (from, to) → list of chars
    edge_labels: dict[tuple[int, int], list[str]] = {}
    for from_id, trans in dfa.transitions.items():
        for symbol, to_id in trans.items():
            key = (from_id, to_id)
            if key not in edge_labels:
                edge_labels[key] = []
            edge_labels[key].append(symbol)

    # Add edges with compressed labels
    for (from_id, to_id), chars in edge_labels.items():
        label = _compress_labels(chars)
        dot.edge(str(from_id), str(to_id), label=label)

    # Ensure output directory exists
    out_dir = os.path.dirname(base_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        rendered = dot.render(
            filename=os.path.basename(base_path),
            directory=out_dir or ".",
            format=fmt,
            cleanup=True,
        )
        return rendered
    except Exception as e:
        print(f"Error rendering diagram: {e}")
        # Try saving the .dot source as fallback
        try:
            dot_path = base_path + ".dot"
            dot.save(filename=os.path.basename(base_path) + ".dot", directory=out_dir or ".")
            print(f"Saved DOT source to: {dot_path}")
            return dot_path
        except Exception:
            return None
