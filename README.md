# YALex Lexer Generator — Proyecto 01

**Curso:** CC3071 - Diseño de Lenguajes de Programación
**Fecha de entrega:** Martes 24 de marzo de 2026, 19:00 hrs

## Descripción

Generador de analizadores léxicos que toma como entrada un archivo `.yal` (formato YALex) y produce:
1. Un **diagrama de transición de estados** del DFA resultante
2. Un **archivo Python standalone** que implementa el analizador léxico

El analizador léxico generado recibe un archivo de texto plano y produce los tokens identificados o reporta errores léxicos.

## Restricciones importantes

- **NO usar librerías de expresiones regulares** (re, regex, etc.) — todo se hace con autómatas finitos. Penalización: 0 puntos.
- **Interfaz gráfica** requerida (tkinter). Penalización: -3 puntos si falta.
- **El lexer generado debe ser independiente** del generador. Penalización: -3 puntos si no lo es.
- **3 pares de archivos de prueba** (.yal + .txt) con complejidad baja, media y alta. Penalización: 0 puntos si faltan.

## Arquitectura del pipeline

```
.yal file → [YALex Parser] → [Regex Parser] → [Thompson's NFA] → [Subset DFA] → [Minimize DFA]
                                                                                    ├→ [Diagrama]
                                                                                    └→ [Code Gen] → lexer.py (standalone)
```

## Estructura del proyecto

```
proyecto_compis1/
├── main.py                  # (Person 3) Entry point, lanza la GUI
├── pipeline.py              # Pipeline completo: .yal → lexer generado
├── gui/
│   └── app.py               # (Person 3) Interfaz gráfica con tkinter
├── yalex/
│   ├── models.py            # Modelos de datos: YAlexSpec, NamedDef, Rule, PatternAction
│   └── parser.py            # Parser de archivos .yal
├── regex/
│   ├── ast_nodes.py         # Nodos AST: CharNode, UnionNode, ConcatNode, StarNode, etc.
│   ├── tokenizer.py         # Tokeniza regex YALex → stream de tokens
│   └── parser.py            # Parser de regex con precedencia (precedence-climbing)
├── automata/
│   ├── models.py            # Clases NFA y DFA con transiciones
│   ├── nfa.py               # Construcción de Thompson (AST → NFA)
│   ├── dfa.py               # Construcción de subconjuntos (NFA → DFA)
│   └── minimize.py          # Minimización de Hopcroft
├── codegen/
│   └── generator.py         # Genera archivo Python standalone con el lexer
├── diagram/
│   └── visualizer.py        # (Person 3) Diagrama de transición con graphviz
├── tests/
│   ├── low/                 # (Person 1 ✅) Complejidad baja
│   │   ├── simple.yal
│   │   └── simple_input.txt
│   ├── medium/              # (Person 2) Complejidad media
│   │   ├── medium.yal
│   │   └── medium_input.txt
│   └── high/                # (Person 3) Complejidad alta
│       ├── high.yal
│       └── high_input.txt
└── output/                  # Lexers generados van aquí
```

---

## Estado actual (Person 1 — COMPLETADO ✅)

Person 1 construyó el pipeline completo de punta a punta con soporte para features básicos:

### Qué funciona ahora

- **Regex soportados:** caracteres literales `'c'`, operadores `* + ? |`, paréntesis `()`, character sets `['0'-'9']`, clases con múltiples chars `[' ' '\t' '\n']`
- **Pipeline completo:** `.yal` → parse → regex AST → NFA (Thompson) → DFA (subconjuntos) → DFA minimizado → código Python generado
- **El lexer generado es standalone** (no depende del generador, se puede copiar y ejecutar solo)
- **Longest match:** el lexer busca siempre el lexema más largo
- **Prioridad por orden:** en caso de empate, gana la regla definida primero
- **Reporte de errores:** el lexer reporta errores léxicos con línea y columna

### Test exitoso

```bash
# Generar el lexer
python pipeline.py tests/low/simple.yal -o output/simple_lexer.py

# Ejecutar el lexer generado (standalone, independiente)
python output/simple_lexer.py tests/low/simple_input.txt
```

Salida:
```
('NUMBER', '3')
('PLUS', '+')
('NUMBER', '42')
('TIMES', '*')
('LPAREN', '(')
('NUMBER', '7')
('MINUS', '-')
('NUMBER', '1')
('RPAREN', ')')
...
```

---

## Person 2 — Extensiones de complejidad media

### Objetivo
Extender el pipeline para soportar features de complejidad media en los regex y el parser de YALex.

### Qué hacer

#### 1. Extender `regex/ast_nodes.py`
Los nodos `CharClassNode` y `WildcardNode` ya existen. Verificar que funcionan correctamente con los nuevos features.

#### 2. Extender `regex/tokenizer.py`
Agregar soporte para:
- **String literals en regex:** `"abc"` ya se tokeniza como chars individuales, pero verificar que funcione dentro de charsets `["abc"]`
- **Identificadores como referencia a definiciones:** `IDENT` tokens ya se generan. Verificar que los nombres se resuelven correctamente cuando se usan en patterns del rule.
- **Wildcard `_`:** ya tokenizado como `UNDERSCORE`, verificar que funcione end-to-end.

#### 3. Extender `regex/parser.py`
- **Expansión de definiciones nombradas:** Cuando se encuentra un `IDENT` token en un pattern del rule, se busca en el diccionario `definitions` y se sustituye por su AST. Esto ya está implementado, pero hay que probarlo bien con definiciones que referencian otras definiciones (ej: `let id = letter (letter | digit)*`).
- Verificar que `CharClassNode` con rangos funcione correctamente en el parser.

#### 4. Mejorar `yalex/parser.py`
- **Robustez con multi-line regex:** verificar que los regex que ocupan varias líneas en el `.yal` se parsean correctamente.
- **Brace-depth counting mejorado:** las acciones `{ ... }` pueden contener código Python con `{` y `}` internos (dicts, f-strings). El parser actual cuenta profundidad de llaves — verificar que no se rompe con código Python complejo.
- **Secciones header/trailer:** verificar que se copian correctamente al archivo generado.

#### 5. Extender `codegen/generator.py`
- Verificar que las secciones `header` y `trailer` del `.yal` se insertan correctamente en el lexer generado.
- Verificar que acciones más complejas (con múltiples líneas de código) se generan correctamente.

#### 6. Crear archivos de test de complejidad media

Crear `tests/medium/medium.yal` con un lexer tipo C simplificado:

```yalex
(* medium.yal - Lexer para un subconjunto de C *)

let letter = ['a'-'z' 'A'-'Z']
let digit = ['0'-'9']
let id = letter (letter | digit)*
let number = digit+
let float_num = digit+ '.' digit+

rule tokens =
    [' ' '\t' '\n']+          { return None }
  | "if"                       { return ("IF", lxm) }
  | "else"                     { return ("ELSE", lxm) }
  | "while"                    { return ("WHILE", lxm) }
  | "return"                   { return ("RETURN", lxm) }
  | float_num                  { return ("FLOAT", lxm) }
  | number                     { return ("NUMBER", lxm) }
  | id                         { return ("ID", lxm) }
  | '+'                        { return ("PLUS", lxm) }
  | '-'                        { return ("MINUS", lxm) }
  | '*'                        { return ("TIMES", lxm) }
  | '/'                        { return ("DIV", lxm) }
  | '='                        { return ("ASSIGN", lxm) }
  | '('                        { return ("LPAREN", lxm) }
  | ')'                        { return ("RPAREN", lxm) }
  | '{'                        { return ("LBRACE", lxm) }
  | '}'                        { return ("RBRACE", lxm) }
  | ';'                        { return ("SEMICOLON", lxm) }
```

Y `tests/medium/medium_input.txt`:

```
if x = 3.14
while count + 1
return result
foo123 bar
```

**NOTA sobre keywords vs identifiers:** Como `"if"` es un string literal que se convierte en `'i' CONCAT 'f'`, y `id` es `letter (letter | digit)*`, ambos matchean "if". Gracias a la prioridad por orden, `"if"` (definido primero) gana. Asegurarse de que keywords van ANTES de `id` en el rule.

**NOTA sobre float vs number:** `float_num` debe ir ANTES de `number` en el rule para que `3.14` se reconozca como FLOAT y no como NUMBER `3` seguido de error.

### Cómo probar

```bash
# Generar lexer
python pipeline.py tests/medium/medium.yal -o output/medium_lexer.py

# Probar
python output/medium_lexer.py tests/medium/medium_input.txt
```

### Archivos a modificar
| Archivo | Acción |
|---------|--------|
| `regex/tokenizer.py` | Verificar/extender soporte para strings en charsets |
| `regex/parser.py` | Probar expansión de definiciones encadenadas |
| `yalex/parser.py` | Mejorar robustez con multiline y braces |
| `codegen/generator.py` | Verificar header/trailer y acciones complejas |
| `tests/medium/medium.yal` | **CREAR** |
| `tests/medium/medium_input.txt` | **CREAR** |

---

## Person 3 — Complejidad alta + GUI + Diagrama

### Objetivo
Agregar features de regex avanzados, construir la interfaz gráfica y el visualizador de diagramas.

### Qué hacer

#### 1. Extender `regex/tokenizer.py` y `regex/parser.py`
Agregar soporte para:
- **Charsets negados `[^...]`:** ya tokenizado (CARET después de LBRACKET), ya parseado en `_parse_charset()`. Probar que funciona end-to-end.
- **Set difference `#`:** ya tokenizado como HASH, ya parseado como `SetDiffNode`. El operador `#` tiene la **mayor precedencia**. En `automata/nfa.py`, `SetDiffNode` se resuelve calculando la diferencia de conjuntos de chars. Probar end-to-end.
- **Escape sequences:** `'\n'`, `'\t'`, `'\r'`, `'\\'` ya soportadas. Verificar que funcionan dentro de strings y charsets.

#### 2. Crear `diagram/visualizer.py`

Generar diagrama de transición del DFA usando la librería `graphviz`:

```bash
pip install graphviz
```

También necesita Graphviz instalado en el sistema: https://graphviz.org/download/

El módulo debe:
- Recibir un objeto `DFA` (de `automata/models.py`)
- Generar un grafo dirigido donde:
  - Cada estado es un nodo (doble círculo si es de aceptación)
  - Los nodos de aceptación muestran la acción asociada
  - Cada transición es una arista con el símbolo
- **Comprimir labels:** si múltiples caracteres van al mismo estado destino, agrupar como `[a-z]` o `[0-9]` en lugar de 26 aristas separadas
- Renderizar a PNG o SVG para mostrar en la GUI

Ejemplo de API:

```python
from diagram.visualizer import render_dfa_diagram

# Retorna path al archivo de imagen generado
image_path = render_dfa_diagram(min_dfa, output_path="output/diagram.png")
```

#### 3. Crear `gui/app.py` — Interfaz gráfica con tkinter

Layout sugerido:

```
+------------------------------------------------------------+
|  YALex Lexer Generator                                      |
+------------------------------------------------------------+
| Archivo YALex: [________________________] [Examinar]        |
|                                          [Generar Lexer]    |
+-----------------------------+------------------------------+
| Código fuente YALex         | Diagrama de transición       |
| (ScrolledText, read-only)   | (Canvas/Image)               |
|                             |                              |
|                             |                              |
+-----------------------------+------------------------------+
| Log de generación           | Probar Lexer                 |
| (ScrolledText, read-only)   | Archivo: [________] [Abrir]  |
|                             | [Ejecutar Lexer]             |
|                             | Tokens:                      |
|                             | (ScrolledText, read-only)    |
+-----------------------------+------------------------------+
```

Funcionalidades:
- **Examinar:** abre file dialog para seleccionar un `.yal`
- **Generar Lexer:** ejecuta el pipeline completo, muestra log y diagrama
- **Probar Lexer:** permite cargar un `.txt` y ejecutar el lexer generado, mostrando tokens y errores
- El diagrama se muestra como imagen dentro de la GUI
- Manejar errores gracefully (mostrar en el log, no crashear)

#### 4. Crear `main.py`

```python
from gui.app import YALexApp

if __name__ == "__main__":
    app = YALexApp()
    app.run()
```

#### 5. Crear archivos de test de complejidad alta

Crear `tests/high/high.yal` con un lexer completo:

```yalex
(* high.yal - Lexer completo para un lenguaje de programación *)

let letter = ['a'-'z' 'A'-'Z' '_']
let digit = ['0'-'9']
let id = letter (letter | digit)*
let number = digit+
let float_num = digit+ '.' digit+
let whitespace = [' ' '\t' '\n' '\r']

rule tokens =
    whitespace+                    { return None }
  | "if"                           { return ("IF", lxm) }
  | "else"                         { return ("ELSE", lxm) }
  | "while"                        { return ("WHILE", lxm) }
  | "for"                          { return ("FOR", lxm) }
  | "return"                       { return ("RETURN", lxm) }
  | "int"                          { return ("TYPE_INT", lxm) }
  | "float"                        { return ("TYPE_FLOAT", lxm) }
  | "void"                         { return ("VOID", lxm) }
  | "true"                         { return ("TRUE", lxm) }
  | "false"                        { return ("FALSE", lxm) }
  | float_num                      { return ("FLOAT_LIT", lxm) }
  | number                         { return ("INT_LIT", lxm) }
  | id                             { return ("ID", lxm) }
  | "++"                           { return ("INCREMENT", lxm) }
  | "+"                            { return ("PLUS", lxm) }
  | "--"                           { return ("DECREMENT", lxm) }
  | "-"                            { return ("MINUS", lxm) }
  | "**"                           { return ("POWER", lxm) }
  | "*"                            { return ("TIMES", lxm) }
  | "/"                            { return ("DIV", lxm) }
  | "%"                            { return ("MOD", lxm) }
  | "=="                           { return ("EQ", lxm) }
  | "!="                           { return ("NEQ", lxm) }
  | "<="                           { return ("LEQ", lxm) }
  | ">="                           { return ("GEQ", lxm) }
  | "<"                            { return ("LT", lxm) }
  | ">"                            { return ("GT", lxm) }
  | "&&"                           { return ("AND", lxm) }
  | "||"                           { return ("OR", lxm) }
  | "!"                            { return ("NOT", lxm) }
  | "="                            { return ("ASSIGN", lxm) }
  | '('                            { return ("LPAREN", lxm) }
  | ')'                            { return ("RPAREN", lxm) }
  | '{'                            { return ("LBRACE", lxm) }
  | '}'                            { return ("RBRACE", lxm) }
  | '['                            { return ("LBRACKET", lxm) }
  | ']'                            { return ("RBRACKET", lxm) }
  | ';'                            { return ("SEMICOLON", lxm) }
  | ','                            { return ("COMMA", lxm) }
```

Y `tests/high/high_input.txt` con un programa realista que incluya errores léxicos intencionales:

```
int main() {
    float x = 3.14;
    int count = 0;
    while (count < 10) {
        x = x + 1.5;
        count++;
    }
    if (x >= 15.0 && count == 10) {
        return 0;
    }
    @ $ ~
}
```

Los caracteres `@`, `$`, `~` son errores léxicos intencionales que el lexer debe reportar.

### Cómo probar

```bash
# Instalar graphviz
pip install graphviz

# Generar lexer de complejidad alta
python pipeline.py tests/high/high.yal -o output/high_lexer.py

# Probar standalone
python output/high_lexer.py tests/high/high_input.txt

# Lanzar la GUI
python main.py
```

### Archivos a crear
| Archivo | Descripción |
|---------|-------------|
| `diagram/visualizer.py` | **CREAR** — Renderizado de DFA con graphviz |
| `gui/app.py` | **CREAR** — Interfaz gráfica con tkinter |
| `main.py` | **CREAR** — Entry point |
| `tests/high/high.yal` | **CREAR** |
| `tests/high/high_input.txt` | **CREAR** |

---

## Cómo funciona cada módulo (para las preguntas de la evaluación)

### `regex/tokenizer.py`
Convierte un string de regex YALex en tokens. Maneja literales `'c'`, strings `"abc"`, charsets `[...]`, operadores `* + ? | #`. Inserta tokens CONCAT implícitos entre átomos adyacentes (ej: `'a' 'b'` → `CHAR(a) CONCAT CHAR(b)`).

### `regex/parser.py`
Parser de precedencia (precedence-climbing). Precedencia de mayor a menor: `#` > `* + ?` > concatenación > `|`. Convierte tokens en un AST. Cuando encuentra un identificador, lo busca en el diccionario de definiciones y sustituye por su AST.

### `automata/nfa.py` — Construcción de Thompson
Convierte recursivamente cada nodo AST en un fragmento NFA (par start-accept). Para combinar múltiples patterns de un rule, crea un estado inicial global con transiciones epsilon a cada fragmento. Los estados de aceptación se etiquetan con la acción y prioridad.

### `automata/dfa.py` — Construcción de subconjuntos
Algoritmo estándar. Cada estado DFA es un frozenset de estados NFA. Se computa el epsilon-closure para expandir transiciones epsilon. Si un estado DFA contiene múltiples estados NFA de aceptación, gana el de mayor prioridad (menor número = definido primero).

### `automata/minimize.py` — Minimización de Hopcroft
Particiona estados inicialmente por acción de aceptación. Itera refinando particiones: separa estados que difieren en a qué partición van sus transiciones. Resultado: DFA con mínimo número de estados.

### `codegen/generator.py`
Genera un archivo Python standalone que contiene:
- Tabla de transiciones del DFA como diccionario
- Mapeo de estados de aceptación a acciones
- Función `tokenize(text)` con algoritmo de longest-match (maximal munch)
- Reporte de errores con línea y columna
- Bloque `__main__` para ejecutar desde CLI

### `yalex/parser.py`
Parsea archivos `.yal`: elimina comentarios `(* *)`, extrae header `{ }`, parsea definiciones `let name = regex`, parsea reglas `rule name = pattern { action } | ...`, extrae trailer `{ }`.

---

## Orden de integración

1. **Person 1** ✅ — Pipeline completo funcionando con complejidad baja
2. **Person 2** — Extiende para complejidad media, crea tests medium
3. **Person 3** — Agrega complejidad alta + GUI + diagrama
4. **Integración final** — Merge de todo, probar los 3 niveles juntos

## Comandos útiles

```bash
# Generar un lexer
python pipeline.py <archivo.yal> -o <salida.py>

# Ejecutar un lexer generado
python <salida.py> <archivo_entrada.txt>

# Lanzar la GUI (cuando Person 3 lo implemente)
python main.py
```
