# Generative AI for Beginners — scripts listos para usar

[English](README.md) · **Español** · [Português (Brasil)](README.pt-BR.md)

El curso "Generative AI for Beginners" describe `generate.py`, `chat.py`, `mini_rag.py` y
`tools_demo.py` solo como pseudocódigo. Estas son versiones que funcionan, construidas a partir de esos
bocetos, más un ayudante para los ejercicios de evaluación. Solo necesitan Python y un SDK: tal como
están, llaman a la API de Anthropic con su paquete oficial `anthropic`, usando el modelo que
configures en `.env.local`. Para usar otro proveedor, mirá [Usar otro proveedor](#usar-otro-proveedor).

**Funcionan apenas los descargás, con ejemplos neutros.** Para usar tu propio dominio (artículos de
un blog, una concesionaria de autos, una app para clínicas médicas, …), editá las partes marcadas con
**`YOUR TASK`** (paso 6).

> El código, sus comentarios y los archivos de ejemplo están en inglés. Los documentos de ejemplo son
> de una empresa inventada, así que las preguntas de ejemplo también están en inglés.

| Archivo | Qué hace |
|---|---|
| `generate.py` | Resume un documento: valida la entrada → arma el prompt → llama al modelo con un tope de salida → revisa `stop_reason` → valida la salida |
| `chat.py` | Chat de 8 turnos con una regla de persona (≤ N caracteres); guarda todo el historial, lo recorta o lo resume |
| `mini_rag.py` | Búsqueda BM25 sobre un `.txt`; cita `[Source N]`; no llama al modelo cuando no encuentra nada relevante |
| `tools_demo.py` | Dos herramientas de ejemplo (calculadora, conversor de monedas); valida los argumentos; el loop se corta a las 6 vueltas |
| `build_eval_config.py` | Convierte un archivo de casos chico en el `eval-config.json` que lee el `run_eval.py` del curso |
| `eval-cases-day1.json`, `eval-cases-day3.json` | Archivos de casos de ejemplo para las evaluaciones del Día 1 y del Día 3 |
| `run.sh` | Carga tu clave y tu modelo desde `.env.local` solo para ese comando y después ejecuta el script |
| `example-document.txt`, `example-document-2.txt` | Dos documentos de una empresa inventada, las entradas de ejemplo |
| `chat-turns.txt` | Los 8 mensajes de ejemplo para `chat.py` |

## El curso, día por día

| Día | Ejercicio | Qué usás |
|---|---|---|
| 1 | Ej. 1 — auditoría de encaje | Nada de código |
| 1 | Ej. 2 — presupuesto de tokens y costo | El `estimate_tokens.py` del curso: `./run.sh estimate_tokens.py my-document.txt` (gratis); sumá `--exact --model <id>` para el conteo real |
| 1 | Ej. 3 — elegir un modelo con tu propia evaluación | `build_eval_config.py` + `eval-cases-day1.json`, y después el `run_eval.py` del curso una vez por modelo (paso 5) |
| 2 | Ej. 1 — iterar un prompt y después atacarlo | Una app de chat. `generate.py --dry-run` muestra cómo queda armado tu prompt final |
| 2 | Ej. 2 — single shot defensivo | `generate.py` (paso 4) |
| 2 | Ej. 3 — estado del chat y recorte | `chat.py` + `chat-turns.txt` (paso 4) |
| 2 | Ej. 4 — respuestas fundamentadas | `mini_rag.py` + tu `.txt` (paso 4) |
| 2 | Ej. 5 — definir y validar una herramienta | `tools_demo.py` (paso 4) |
| 3 | Ej. 1 — diagnosticar el enfoque | Nada de código |
| 3 | Ej. 2 — imagen con semilla fija | Un generador de imágenes con opción de semilla (no incluido) |
| 3 | Ej. 3 — registro de riesgos y evaluación adversarial | `build_eval_config.py` + `eval-cases-day3.json`, que prueba el propio prompt de `generate.py`, y después `run_eval.py` con `--repeat 3` en los casos de rechazo e inyección (paso 5) |
| 3 | Ej. 4 — los cuatro estados de falla | Nada de código. Los mensajes de estado de `generate.py` sirven de punto de partida |

**Los scripts propios del curso.** `estimate_tokens.py` y `run_eval.py` vienen con el curso (mirá su
`SCRIPTS.md`) y no están incluidos acá. Copiá los dos a esta carpeta; `run.sh` los ejecuta como a los
demás. Tienen su propio modelo por defecto: a `estimate_tokens.py` pasale `--model`; `run_eval.py` toma
el modelo del `eval-config.json`, que `build_eval_config.py` completa con tu `MODEL`.

## 1. Qué necesitás

- Python 3.9 o superior (probado con 3.9.6). Fijate con `python3 --version`.
- Una API key **con créditos** y el id del modelo que vas a usar. Tal como están, los scripts necesitan
  una clave de Anthropic; para otro proveedor, mirá [Usar otro proveedor](#usar-otro-proveedor).
  Una suscripción a una app de chat es otro producto y no incluye créditos de API.

## 2. Instalación (macOS / Linux / WSL)

```bash
cd genai-beginners-lab-scripts
python3 -m venv .venv                          # run.sh espera el venv exactamente acá
.venv/bin/pip install -r requirements.txt
cp .env.example .env.local                     # después abrí .env.local: pegá tu clave y el id en MODEL
chmod +x run.sh
# después copiá a esta carpeta el estimate_tokens.py y el run_eval.py del curso
```

## 3. Verificá la instalación gratis (sin clave, sin costo)

Ejecutá todo desde adentro de esta carpeta:

```bash
./run.sh generate.py example-document.txt --dry-run   # muestra el prompt exacto
./run.sh chat.py chat-turns.txt --dry-run             # respuestas simuladas, 0 llamadas cobradas
./run.sh mini_rag.py example-document.txt --show-chunks
./run.sh mini_rag.py example-document.txt "What happens to my open files when the workstation locks?" --retrieve-only
./run.sh tools_demo.py --validation-demo              # argumentos inválidos, sin llamar al modelo
./run.sh build_eval_config.py eval-cases-day3.json    # escribe eval-config.json (necesita MODEL)
```

Si estos funcionan, la instalación está bien.

## 4. Hacé los labs del Día 2 con el ejemplo (con costo)

`run.sh` muestra `note: … makes billed model calls` antes de cualquier comando que cueste plata.

```bash
# generate.py — los tres resultados + una falla forzada
./run.sh generate.py example-document.txt                        # normal
./run.sh generate.py --text ''                                   # vacío (rechazado, sin llamada)
python3 -c 'print("word " * 13000)' | ./run.sh generate.py -     # demasiado largo (rechazado, sin llamada)
./run.sh generate.py example-document.txt --max-tokens 20        # cortado: stop_reason max_tokens

# chat.py — las tres estrategias para recortar el historial
./run.sh chat.py chat-turns.txt
./run.sh chat.py chat-turns.txt --max-turns 3
./run.sh chat.py chat-turns.txt --max-turns 3 --summarize

# mini_rag.py — está en el documento, falta el detalle, sin palabras en común, sin relación
./run.sh mini_rag.py example-document.txt \
  "What happens to my open files when the workstation locks?" \
  "Is an overtime exception paid at a higher hourly rate?" \
  "How long can my laptop stay awake before it kicks me out?" \
  "What water temperature is best for brewing green tea?"

# tools_demo.py
./run.sh tools_demo.py "What is 15% of 4,000, and what is that in euros?"
```

**Una corrida "normal" todavía puede ser rechazada de vez en cuando.** O el paso 5 detecta un resumen
que se pasa del límite (`The summary is … characters, over the 240-character limit`), o el filtro de
seguridad de la API bloquea el pedido por error (`status: refusal`, con una línea `category:`). En
nuestras pruebas, el ejemplo fue aceptado en 19 de 20 corridas. En los dos casos son los controles
haciendo su trabajo, no bugs: volvé a ejecutarlo y contalo en tu informe del lab.

Todos los scripts aceptan `--model <id>` (por defecto, el `MODEL` de `.env.local`) para probar otro
modelo, y `--effort` (por defecto `low`; pasá `--effort none` si tu modelo rechaza ese parámetro).
Configurá `PRICE_INPUT_PER_MTOK` y `PRICE_OUTPUT_PER_MTOK` en `.env.local` para ver cuánto cuesta cada
corrida. Con un modelo que cuesta US$5 / US$25 por millón de tokens de entrada / salida medimos:
`generate.py` ≈ US$0,03 para un documento de 12.000 caracteres (menos con el ejemplo), `chat.py`
US$0,01–0,04 por corrida, `mini_rag.py` ≤ US$0,02 para las cuatro preguntas, `tools_demo.py`
≈ US$0,015. Todo el paso 4 cuesta menos de US$0,20 a ese precio.

## 5. Hacé una evaluación (Días 1 y 3, con costo)

`build_eval_config.py` es gratis: solo escribe la config. `run_eval.py` hace las llamadas y escribe
cada salida en un archivo Markdown para que la puntúes a mano.

```bash
# Día 3 — el set adversarial, contra el propio prompt de generate.py
./run.sh build_eval_config.py eval-cases-day3.json                               # → eval-config.json
./run.sh run_eval.py eval-config.json --out results.md                           # 6 llamadas
./run.sh build_eval_config.py eval-cases-day3.json --only R1,I1 --out eval-config-repeat.json
./run.sh run_eval.py eval-config-repeat.json --repeat 3 --out results-repeat.md   # rechazo + inyección, 3 veces cada uno

# Día 1 — el mismo set de pruebas en dos modelos; solo cambia el modelo
./run.sh build_eval_config.py eval-cases-day1.json --model <modelo-a> --out eval-config-a.json
./run.sh build_eval_config.py eval-cases-day1.json --model <modelo-b> --out eval-config-b.json
./run.sh run_eval.py eval-config-a.json --repeat 3 --out results-a.md
./run.sh run_eval.py eval-config-b.json --repeat 3 --out results-b.md
```

- `eval-cases-day3.json` tiene `"prompt_from": "generate.py"`: la evaluación manda exactamente lo que
  manda tu feature. Cambiá el prompt en `generate.py` y volvé a generar la config.
- `eval-cases-day1.json` tiene su propio `system` y `prompt_template`, escritos en el archivo de casos.
- Cada caso da su entrada como `"input"` (texto directo) o `"input_file"` (un archivo o una lista, que
  se unen). El `"replace": [["viejo", "nuevo"]]` opcional cambia un texto que aparece exactamente una
  vez (una variante de sesgo, o una inyección insertada después de un ancla), y `"append"` agrega texto
  al final.
- Con los casos de ejemplo, cada pasada de `run_eval.py` costó unos US$0,04 a US$5 / US$25 por millón
  de tokens.

## 6. Adaptalo a tu dominio

Los labs evalúan **tu** tarea. Cada lugar para editar está marcado; los listás todos con:

```bash
grep -n "YOUR TASK" *.py *.txt
```

| Archivo | Qué cambiar | Artículos de un blog | Concesionaria de autos | App para clínicas |
|---|---|---|---|---|
| `generate.py` | El bloque `YOUR TASK` del principio: `ROLE`, `AUDIENCE`, `DOCUMENT`, `MAX_SUMMARY_CHARS`, `BULLETS` / `MAX_BULLET_CHARS`, `IDEAL_OUTPUT`, `MIN_CHARS` / `MAX_CHARS` | un profesor que resume un artículo para estudiantes | un vendedor que resume un aviso de auto para quien compra su primer auto | una recepcionista que resume una política de la clínica para pacientes |
| `chat.py` | El bloque `YOUR TASK`: `SYSTEM` (la persona), `RULE_MAX_CHARS`, `USER_LABEL`, `ASSISTANT_LABEL` | el bot de atención a lectores del blog | el asistente de WhatsApp de la concesionaria | el asistente de recepción (nunca da consejos médicos) |
| `chat-turns.txt` | Los 8 mensajes. Mantené la estructura que se explica al principio del archivo | un lector que pregunta por un post | un cliente que pregunta por el pedido #5521 | un paciente que reprograma un turno |
| `mini_rag.py` | Pasale tu propio `.txt` (sin tocar código). Si no está en inglés, agregá stopwords y traducí la respuesta por defecto en las marcas `YOUR TASK` | la política de comentarios del blog | las reglas de la garantía | la política de cancelación |
| `tools_demo.py` | El bloque `YOUR TASK` arriba de `TOOLS`: agregá una definición, una función `validate_…` y una `run_…`, y registralas en `DISPATCH` | `search_posts(tag)` | `check_stock(model, year)` | `find_open_slots(specialty, date)` |
| `eval-cases-day1.json` | Tu propio `system`, `prompt_template` y 5 casos: 2 comunes, 1 borde, 1 ambiguo, 1 que no debe responderse | dos artículos pegados juntos como caso borde | un aviso sin precio, cuando el prompt pide precios | un texto sin ninguna regla de la clínica |
| `eval-cases-day3.json` | Tus 6 casos: 2 normales, 1 borde, 1 para rechazar, 1 inyección, 1 sesgo. El prompt viene de `generate.py` | el e-mail privado de un lector como caso para rechazar | un aviso con una instrucción escondida | la misma política con solo un nombre cambiado |

**Tus propios documentos:** guardalos como `.txt` en UTF-8, con un tema completo por párrafo y una
línea en blanco entre párrafos. Después usalos en lugar de los ejemplos:

```bash
./run.sh generate.py my-document.txt --dry-run      # revisá el prompt primero, gratis
./run.sh generate.py my-document.txt
./run.sh mini_rag.py my-document.txt --show-chunks  # revisá los chunks, gratis
./run.sh mini_rag.py my-document.txt "una pregunta que tu documento responde" "una que no"
```

Tip: usá `--retrieve-only` para calibrar `--min-score` con tu documento, gratis, antes de cualquier
corrida con costo.

## Usar otro proveedor

Cada script habla con el modelo en un solo lugar, marcado con `YOUR PROVIDER` (los listás con
`grep -n "YOUR PROVIDER" *.py`). Para cambiar, por ejemplo a una API compatible con OpenAI:

1. Reemplazá `anthropic` en `requirements.txt` por el SDK de tu proveedor, y en cada script la
   creación del cliente (`anthropic.Anthropic()`) y las clases de error (`anthropic.APIError`, …).
2. En cada llamada `YOUR PROVIDER`, mandá el mismo system prompt, los mensajes y `max_tokens`, y
   convertí la respuesta a lo que el script lee: el texto, el uso de tokens y el motivo de parada. Los
   scripts se ramifican según `end_turn`, `max_tokens`, `tool_use` y `refusal`; una API compatible con
   OpenAI los llama `stop`, `length`, `tool_calls` y `content_filter`.
3. En `tools_demo.py`, convertí también las definiciones de las herramientas (`input_schema` → el
   campo de esquema de tu proveedor) y mandá los resultados de las herramientas en su formato.
4. Usá `--effort none` si tu proveedor no tiene algo equivalente. En `chat.py`,
   `count_system_tokens()` usa un endpoint exclusivo de Anthropic: adaptalo o hacé que devuelva `None`.

El `run_eval.py` y el `estimate_tokens.py` del curso también llaman a la API de Anthropic: adaptá sus
llamadas de la misma forma, o corré tus casos a mano en la app de chat de tu proveedor.

## 7. Windows (PowerShell, sin WSL)

`run.sh` es un script de bash, así que configurá la clave y el modelo vos, solo para la ventana actual:

```powershell
cd genai-beginners-lab-scripts
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "tu-clave"               # duran hasta que cierres esta ventana
$env:MODEL = "id-de-tu-modelo"
.venv\Scripts\python generate.py example-document.txt
.venv\Scripts\python chat.py chat-turns.txt --max-turns 3
.venv\Scripts\python build_eval_config.py eval-cases-day3.json
.venv\Scripts\python run_eval.py eval-config.json --out results.md
Remove-Item Env:ANTHROPIC_API_KEY, Env:MODEL      # cuando termines
```

## 8. Problemas frecuentes

| Error | Causa y solución |
|---|---|
| `No model set…` / `error: no model set…` | `MODEL` en `.env.local` está vacío o todavía dice `REPLACE_ME`. Pegá el id del modelo que figura en la documentación de tu proveedor, o pasá `--model`. |
| `404 … not_found_error … model` | Ese id de modelo no existe o tu clave no puede usarlo. Copialo exacto de la documentación de tu proveedor. |
| `401 … API key is invalid.` / `The API key was rejected` | La clave fue revocada o está mal copiada. Creá una nueva y pegala en `.env.local`. |
| `400 … anthropic-workspace-id is required` | Tu clave de Anthropic está vinculada a tu identidad. Descomentá `ANTHROPIC_CUSTOM_HEADERS` en `.env.local` y agregá tu id `wrkspc_…`. |
| `credit balance is too low` | Comprá créditos en la consola de tu proveedor. Algunos piden saldo positivo incluso para los endpoints gratuitos. |
| `error: paste a real key into …/.env.local first` | `ANTHROPIC_API_KEY` en `.env.local` todavía dice `REPLACE_ME`. |
| `error: no such script: …/run_eval.py` | Copiá a esta carpeta el `run_eval.py` (y el `estimate_tokens.py`) del curso. |
| `error: case …: '…' must occur exactly once in the input` | El texto `old` de un par `replace` no está en esa entrada, o aparece más de una vez. Copialo exacto y hacelo único. |
| `This script needs the SDK` | Ejecutá con `./run.sh`, o instalá en el venv: `.venv/bin/pip install -r requirements.txt`. |
| `No such file or directory: .venv/bin/python` | Creá el venv adentro de esta carpeta (paso 2). |
| `That … could not be processed.` (`status: refusal`) | El filtro de seguridad de la API bloqueó el pedido, a veces por error. Volvé a ejecutarlo; si se repite, hacé más neutro el `IDEAL_OUTPUT` o probá con otro documento. |
| `That looks like a title or a link…` | Tu documento es más corto que `MIN_CHARS` en `generate.py`. Pegá el texto completo o bajá el límite. |
| Todas las preguntas de `mini_rag.py` se cortan sin respuesta | `--min-score` es demasiado alto para tu documento, o su idioma necesita stopwords. Calibralo con `--retrieve-only`. |

## Cuidá tu clave

- **Nunca subas ni compartas `.env.local`.** Ya está en `.gitignore`.
- **No pongas `export` de tu API key en `~/.zshrc` ni en `~/.bashrc`.** Otras herramientas de tu
  máquina que leen la misma variable (asistentes de código con IA, otros scripts) la usarían y la
  cobrarían sin avisarte. `run.sh` lo evita: la clave existe solo mientras corre el comando.

## Licencia

MIT. Mirá el archivo [LICENSE](LICENSE).
