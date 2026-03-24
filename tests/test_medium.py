"""
tests/test_medium.py
Casos de prueba para la Persona 2 — complejidad media.

Ejecutar desde la raíz del proyecto:
    python tests/test_medium.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex.tokenizer import tokenize_regex, TokenType
from regex.parser import parse_regex
from regex.ast_nodes import CharNode, ConcatNode, UnionNode, StarNode, PlusNode, CharClassNode, WildcardNode
from yalex.parser import parse_yalex

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    msg = f"{status} — {name}"
    if detail:
        msg += f"\n       {detail}"
    print(msg)
    results.append(condition)
    return condition



print("\n── Tokenizer: identificadores con underscore ──")

tokens = tokenize_regex("float_num")
ident_tokens = [t for t in tokens if t.type == TokenType.IDENT]
underscore_tokens = [t for t in tokens if t.type == TokenType.UNDERSCORE]

check(
    "float_num se tokeniza como un solo IDENT",
    len(ident_tokens) == 1 and ident_tokens[0].value == "float_num",
    f"tokens obtenidos: {tokens}"
)
check(
    "float_num no genera UNDERSCORE suelto",
    len(underscore_tokens) == 0,
    f"tokens obtenidos: {tokens}"
)

tokens2 = tokenize_regex("my_var_1")
idents2 = [t for t in tokens2 if t.type == TokenType.IDENT]
check(
    "my_var_1 es un solo IDENT",
    len(idents2) == 1 and idents2[0].value == "my_var_1",
    f"tokens obtenidos: {tokens2}"
)

# Underscore sola sigue siendo wildcard
tokens3 = tokenize_regex("_")
check(
    "Underscore sola sigue siendo UNDERSCORE (wildcard)",
    len(tokens3) == 1 and tokens3[0].type == TokenType.UNDERSCORE,
    f"tokens obtenidos: {tokens3}"
)

# Underscore en expresión compuesta: 'a' _ 'b'  → CHAR CONCAT UNDERSCORE CONCAT CHAR
tokens4 = tokenize_regex("'a' _ 'b'")
types4 = [t.type for t in tokens4]
check(
    "Wildcard _ funciona en expresión: 'a' _ 'b'",
    TokenType.UNDERSCORE in types4,
    f"types: {types4}"
)


print("\n── Parser: expansión de definiciones encadenadas ──")

# Simula el pipeline: digit → letter → id
from regex.parser import parse_regex

digit_ast = parse_regex("['0'-'9']")
letter_ast = parse_regex("['a'-'z' 'A'-'Z']")

definitions = {"digit": digit_ast, "letter": letter_ast}

# id = letter (letter | digit)*
id_ast = parse_regex("letter (letter | digit)*", definitions)
check(
    "Definición encadenada: id = letter (letter | digit)* se parsea sin error",
    id_ast is not None,
    f"tipo raíz: {type(id_ast).__name__}"
)

# float_num = digit+ '.' digit+
float_ast = parse_regex("digit+ '.' digit+", definitions)
check(
    "Definición encadenada: float_num = digit+ '.' digit+ se parsea sin error",
    float_ast is not None,
    f"tipo raíz: {type(float_ast).__name__}"
)

# Referencia a definición no existente debe lanzar error
try:
    parse_regex("undefined_name", {})
    check("Referencia a nombre no definido lanza ValueError", False)
except ValueError as e:
    check("Referencia a nombre no definido lanza ValueError", True, str(e))



print("\n── YALex parser: medium.yal ──")

MEDIUM_YAL = """\
(* medium.yal - Lexer para un subconjunto de C *)

let letter = ['a'-'z' 'A'-'Z']
let digit = ['0'-'9']
let id = letter (letter | digit)*
let number = digit+
let float_num = digit+ '.' digit+

rule tokens =
    [' ' '\\t' '\\n']+          { return None }
  | "if"                       { return ("IF", lxm) }
  | "else"                     { return ("ELSE", lxm) }
  | "while"                    { return ("WHILE", lxm) }
  | "return"                   { return ("RETURN", lxm) }
  | float_num                  { return ("FLOAT", lxm) }
  | number                     { return ("NUMBER", lxm) }
  | id                         { return ("ID", lxm) }
  | '+'                        { return ("PLUS", lxm) }
  | '-'                        { return ("MINUS", lxm) }
  | '='                        { return ("ASSIGN", lxm) }
  | ';'                        { return ("SEMICOLON", lxm) }
"""

spec = parse_yalex(MEDIUM_YAL)

check("medium.yal: 5 definiciones parseadas",
      len(spec.definitions) == 5,
      f"definiciones: {[d.name for d in spec.definitions]}")

check("medium.yal: 1 regla parseada",
      len(spec.rules) == 1)

check("medium.yal: nombre de regla es 'tokens'",
      spec.rules[0].entrypoint == "tokens")

patterns = spec.rules[0].patterns
check("medium.yal: 12 patterns en la regla",
      len(patterns) == 12,
      f"patterns encontrados: {len(patterns)}")

# Verificar orden: float_num ANTES que number (prioridad)
pattern_regexes = [p.regex_str for p in patterns]
idx_float = next((i for i, p in enumerate(patterns) if "float_num" in p.regex_str), -1)
idx_number = next((i for i, p in enumerate(patterns) if p.regex_str.strip() == "number"), -1)
check(
    "float_num aparece ANTES que number en la regla (prioridad correcta)",
    idx_float != -1 and idx_number != -1 and idx_float < idx_number,
    f"float_num en posición {idx_float}, number en posición {idx_number}"
)

# Verificar orden: keywords ANTES que id
idx_if = next((i for i, p in enumerate(patterns) if '"if"' in p.regex_str), -1)
idx_id = next((i for i, p in enumerate(patterns) if p.regex_str.strip() == "id"), -1)
check(
    '"if" aparece ANTES que id en la regla (keywords con prioridad)',
    idx_if != -1 and idx_id != -1 and idx_if < idx_id,
    f'"if" en posición {idx_if}, id en posición {idx_id}'
)



print("\n── Pipeline end-to-end ──")

try:
    from pipeline import run_pipeline
    import tempfile, os

    # Escribir medium.yal a un archivo temporal
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yal',
                                     delete=False, encoding='utf-8') as f:
        f.write(MEDIUM_YAL)
        yal_tmp = f.name

    out_tmp = yal_tmp.replace('.yal', '_lexer.py')

    try:
        result = run_pipeline(yal_tmp, out_tmp)
        check("Pipeline genera lexer sin excepciones", True)

        check("Archivo de salida existe",
              os.path.exists(out_tmp),
              f"path: {out_tmp}")

        # Cargar el lexer generado y tokenizar entrada de prueba
        import importlib.util
        spec_mod = importlib.util.spec_from_file_location("gen_lexer", out_tmp)
        mod = importlib.util.module_from_spec(spec_mod)
        spec_mod.loader.exec_module(mod)

        # ── Prueba clave 1: float_num gana sobre number ──
        tokens_out, errors = mod.tokenize("3.14")
        check(
            "3.14 se tokeniza como FLOAT (float_num > number)",
            len(tokens_out) == 1 and tokens_out[0] == ("FLOAT", "3.14"),
            f"tokens: {tokens_out}, errores: {errors}"
        )

        # ── Prueba clave 2: number no consume el punto ──
        tokens_out2, errors2 = mod.tokenize("42")
        check(
            "42 se tokeniza como NUMBER",
            len(tokens_out2) == 1 and tokens_out2[0] == ("NUMBER", "42"),
            f"tokens: {tokens_out2}"
        )

        # ── Prueba clave 3: keywords ganan sobre id ──
        for kw, tok_type in [("if", "IF"), ("else", "ELSE"),
                              ("while", "WHILE"), ("return", "RETURN")]:
            tokens_kw, _ = mod.tokenize(kw)
            check(
                f'"{kw}" se tokeniza como {tok_type} (no como ID)',
                len(tokens_kw) == 1 and tokens_kw[0] == (tok_type, kw),
                f"tokens: {tokens_kw}"
            )

        # ── Prueba clave 4: identificadores con letras y dígitos ──
        tokens_id, _ = mod.tokenize("foo123")
        check(
            "foo123 se tokeniza como ID",
            len(tokens_id) == 1 and tokens_id[0] == ("ID", "foo123"),
            f"tokens: {tokens_id}"
        )

        # ── Prueba clave 5: keyword como prefijo no rompe el id ──
        tokens_iffy, _ = mod.tokenize("iffy")
        check(
            '"iffy" (empieza con "if") se tokeniza como ID, no IF',
            len(tokens_iffy) == 1 and tokens_iffy[0] == ("ID", "iffy"),
            f"tokens: {tokens_iffy}"
        )

        # ── Prueba clave 6: expresión completa ──
        src = "if x = 3.14"
        tokens_expr, errors_expr = mod.tokenize(src)
        expected = [("IF", "if"), ("ID", "x"), ("ASSIGN", "="), ("FLOAT", "3.14")]
        check(
            f'"{src}" produce {expected}',
            tokens_expr == expected,
            f"obtenido: {tokens_expr}"
        )

    except Exception as e:
        check(f"Pipeline end-to-end (error: {e})", False)
    finally:
        for f in [yal_tmp, out_tmp]:
            try: os.unlink(f)
            except: pass

except ImportError:
    print("   pipeline.py no encontrado — saltando pruebas end-to-end")


print(f"\n{'─'*45}")
passed = sum(results)
total = len(results)
print(f"Resultado: {passed}/{total} pruebas pasaron")
if passed == total:
    print(" Todo OK para complejidad media")
else:
    print(f"{total - passed} prueba(s) fallaron — revisar arriba")
