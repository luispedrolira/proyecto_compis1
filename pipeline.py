"""
YALex Lexer Generator - Pipeline
Reads a .yal file, builds DFA, generates standalone lexer.
"""
import sys
import os
import re

from yalex.parser import parse_yalex
from regex.parser import parse_regex
from regex.ast_nodes import RegexNode
from automata.nfa import build_combined_nfa
from automata.dfa import nfa_to_dfa
from automata.minimize import minimize_dfa
from codegen.generator import generate_lexer


def _extract_token_name(action: str) -> str | None:
    """Extract a readable token name from an action string.

    Examples:
        'return ("IF", lxm)'   → 'IF'
        'return ("FLOAT", lxm)' → 'FLOAT'
        'return None'           → None   (skip/whitespace rule)
        'return lxm'            → None   (no named token)
    """
    if not action:
        return None
    # Match: return ("TOKEN_NAME", ...) or return ('TOKEN_NAME', ...)
    match = re.search(r'return\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']', action)
    if match:
        return match.group(1)
    return None


def run_pipeline(yal_path: str, output_path: str) -> dict:
    """Run the full YALex pipeline.

    Args:
        yal_path: Path to the .yal input file.
        output_path: Path for the generated lexer Python file.

    Returns:
        dict with keys: 'spec', 'dfa', 'min_dfa', 'output_path'
    """
    # 1. Read and parse the YALex file
    with open(yal_path, 'r', encoding='utf-8') as f:
        yal_text = f.read()

    spec = parse_yalex(yal_text)
    print(f"Parsed YALex file: {len(spec.definitions)} definitions, "
          f"{len(spec.rules)} rules")

    if not spec.rules:
        raise ValueError("No rules found in YALex file")

    rule = spec.rules[0]  # We support one rule entry point
    print(f"Rule entry point: {rule.entrypoint} with {len(rule.patterns)} patterns")

    # 2. Parse named definitions into regex ASTs
    definitions: dict[str, RegexNode] = {}
    for defn in spec.definitions:
        print(f"  Parsing definition: let {defn.name} = {defn.regex_str}")
        ast = parse_regex(defn.regex_str, definitions)
        definitions[defn.name] = ast

    # 3. Parse each pattern's regex, extract token_name, and build combined NFA
    patterns = []
    for pattern in rule.patterns:
        print(f"  Parsing pattern: {pattern.regex_str}")
        ast = parse_regex(pattern.regex_str, definitions)

        # Populate token_name for use by the diagram visualizer (Person 3)
        pattern.token_name = _extract_token_name(pattern.action or "")

        patterns.append((ast, pattern.action or "return None", pattern.priority))

    print(f"\nBuilding combined NFA for {len(patterns)} patterns...")
    nfa = build_combined_nfa(patterns)
    print(f"  NFA: {len(nfa.states)} states")

    # 4. Convert NFA to DFA
    print("Converting NFA to DFA...")
    dfa = nfa_to_dfa(nfa)
    print(f"  DFA: {len(dfa.states)} states")

    # 5. Minimize DFA
    print("Minimizing DFA...")
    min_dfa = minimize_dfa(dfa)
    print(f"  Minimized DFA: {len(min_dfa.states)} states")

    # 6. Generate lexer code
    print(f"\nGenerating lexer: {output_path}")
    generate_lexer(min_dfa, spec, rule.patterns, output_path)
    print("Done!")

    return {
        'spec': spec,
        'dfa': dfa,
        'min_dfa': min_dfa,
        'output_path': output_path,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <input.yal> [-o output.py]")
        sys.exit(1)

    yal_path = sys.argv[1]
    output_path = "output/generated_lexer.py"

    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    run_pipeline(yal_path, output_path)
