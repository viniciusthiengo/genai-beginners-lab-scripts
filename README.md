# Generative AI for Beginners — ready-to-run scripts

**English** · [Español](README.es.md) · [Português (Brasil)](README.pt-BR.md)

The "Generative AI for Beginners" course describes `generate.py`, `chat.py`, `mini_rag.py` and
`tools_demo.py` only as pseudocode. These are working versions built from those sketches, plus a
helper for the evaluation exercises. They need only Python and one SDK: as written, they call the
Anthropic API through its official `anthropic` package, with whatever model you set in `.env.local`.
To use another provider, see [Using another provider](#using-another-provider).

**They run out of the box on neutral examples.** To use your own domain (blog articles, a car
store, a medical clinic app, …), edit the parts marked **`YOUR TASK`** (step 6).

| File | What it does |
|---|---|
| `generate.py` | Summarizes one document: validate input → build prompt → call with an output cap → check `stop_reason` → validate output |
| `chat.py` | 8-turn chat with a persona rule (≤ N characters); keeps the full history, truncates it, or summarizes it |
| `mini_rag.py` | BM25 retrieval over one `.txt`; cites `[Source N]`; skips the model call when nothing is relevant |
| `tools_demo.py` | Two example tools (calculator, currency converter); validates arguments; the loop stops after 6 rounds |
| `build_eval_config.py` | Turns a small cases file into the `eval-config.json` that the course's `run_eval.py` reads |
| `eval-cases-day1.json`, `eval-cases-day3.json` | Example cases files for the Day 1 and Day 3 evaluations |
| `run.sh` | Loads your key and model from `.env.local` for one command only, then runs the script |
| `example-document.txt`, `example-document-2.txt` | Two invented company documents, the example inputs |
| `chat-turns.txt` | The 8 example user messages for `chat.py` |

## The course, day by day

| Day | Exercise | What you use |
|---|---|---|
| 1 | Ex. 1 — fit audit | No code |
| 1 | Ex. 2 — token and cost budget | The course's `estimate_tokens.py`: `./run.sh estimate_tokens.py my-document.txt` (free); add `--exact --model <id>` for the real count |
| 1 | Ex. 3 — choose a model with your own evaluation | `build_eval_config.py` + `eval-cases-day1.json`, then the course's `run_eval.py` once per model (step 5) |
| 2 | Ex. 1 — iterate a prompt, then attack it | A chat app. `generate.py --dry-run` shows how your final prompt is assembled |
| 2 | Ex. 2 — defensive single shot | `generate.py` (step 4) |
| 2 | Ex. 3 — chat state and trimming | `chat.py` + `chat-turns.txt` (step 4) |
| 2 | Ex. 4 — grounded answers | `mini_rag.py` + your `.txt` (step 4) |
| 2 | Ex. 5 — define and validate a tool | `tools_demo.py` (step 4) |
| 3 | Ex. 1 — diagnose the approach | No code |
| 3 | Ex. 2 — image with a fixed seed | An image generator with a seed setting (not included) |
| 3 | Ex. 3 — risk register and adversarial evaluation | `build_eval_config.py` + `eval-cases-day3.json`, which tests `generate.py`'s own prompt, then `run_eval.py` with `--repeat 3` on the refusal and injection cases (step 5) |
| 3 | Ex. 4 — the four failure states | No code. `generate.py`'s status messages are a starting point |

**The course's own scripts.** `estimate_tokens.py` and `run_eval.py` come with the course (see its
`SCRIPTS.md`) and are not included here. Copy both into this folder; `run.sh` runs them like the
others. They have their own default model: pass `--model` to `estimate_tokens.py`; `run_eval.py`
takes the model from `eval-config.json`, which `build_eval_config.py` fills in from `MODEL`.

## 1. What you need

- Python 3.9 or newer (tested on 3.9.6). Check with `python3 --version`.
- An API key **with credits** and the id of the model you want to use. As written, the scripts need an
  Anthropic key; for another provider, see [Using another provider](#using-another-provider).
  A chat-app subscription is a separate product and does not include API credits.

## 2. Set up (macOS / Linux / WSL)

```bash
cd genai-beginners-lab-scripts
python3 -m venv .venv                          # run.sh expects the venv exactly here
.venv/bin/pip install -r requirements.txt
cp .env.example .env.local                     # then open .env.local: paste your key and your MODEL id
chmod +x run.sh
# then copy the course's estimate_tokens.py and run_eval.py into this folder
```

## 3. Check the setup for free (no key, no cost)

Run everything from inside this folder:

```bash
./run.sh generate.py example-document.txt --dry-run   # prints the exact prompt
./run.sh chat.py chat-turns.txt --dry-run             # fake replies, 0 billed calls
./run.sh mini_rag.py example-document.txt --show-chunks
./run.sh mini_rag.py example-document.txt "What happens to my open files when the workstation locks?" --retrieve-only
./run.sh tools_demo.py --validation-demo              # bad arguments, no model call
./run.sh build_eval_config.py eval-cases-day3.json    # writes eval-config.json (needs MODEL set)
```

If these work, the setup is correct.

## 4. Run the Day 2 labs on the example (billed)

`run.sh` prints `note: … makes billed model calls` before any command that costs money.

```bash
# generate.py — the three outcomes + a forced failure
./run.sh generate.py example-document.txt                        # normal
./run.sh generate.py --text ''                                   # empty (rejected, no call)
python3 -c 'print("word " * 13000)' | ./run.sh generate.py -     # too long (rejected, no call)
./run.sh generate.py example-document.txt --max-tokens 20        # cut off: stop_reason max_tokens

# chat.py — the three trimming strategies
./run.sh chat.py chat-turns.txt
./run.sh chat.py chat-turns.txt --max-turns 3
./run.sh chat.py chat-turns.txt --max-turns 3 --summarize

# mini_rag.py — in the doc, detail absent, no shared words, unrelated
./run.sh mini_rag.py example-document.txt \
  "What happens to my open files when the workstation locks?" \
  "Is an overtime exception paid at a higher hourly rate?" \
  "How long can my laptop stay awake before it kicks me out?" \
  "What water temperature is best for brewing green tea?"

# tools_demo.py
./run.sh tools_demo.py "What is 15% of 4,000, and what is that in euros?"
```

**A "normal" run can still be rejected now and then.** Either step 5 catches a summary over the
limit (`The summary is … characters, over the 240-character limit`), or the API's safety filter blocks
the request by mistake (`status: refusal`, plus a `category:` line). In our tests the example was
accepted in 19 of 20 runs. Both are the checks doing their job, not bugs: run it again, and report
it in your lab write-up.

Every script accepts `--model <id>` (default: `MODEL` from `.env.local`) to try another model, and
`--effort` (default `low`; pass `--effort none` if your model rejects that parameter). Set
`PRICE_INPUT_PER_MTOK` and `PRICE_OUTPUT_PER_MTOK` in `.env.local` to see what each run costs.
With a model priced at US$5 / US$25 per million input / output tokens we measured: `generate.py`
≈ $0.03 for a 12,000-character document (less for the example), `chat.py` $0.01–0.04 per run,
`mini_rag.py` ≤ $0.02 for the four questions, `tools_demo.py` ≈ $0.015. All of step 4 costs under
$0.20 at that price.

## 5. Run an evaluation (Days 1 and 3, billed)

`build_eval_config.py` is free: it only writes the config. `run_eval.py` makes the calls and writes
every output to a Markdown file for you to score by hand.

```bash
# Day 3 — the adversarial set, against generate.py's own prompt
./run.sh build_eval_config.py eval-cases-day3.json                               # → eval-config.json
./run.sh run_eval.py eval-config.json --out results.md                           # 6 calls
./run.sh build_eval_config.py eval-cases-day3.json --only R1,I1 --out eval-config-repeat.json
./run.sh run_eval.py eval-config-repeat.json --repeat 3 --out results-repeat.md   # refusal + injection, 3 runs each

# Day 1 — the same test set on two models; only the model changes
./run.sh build_eval_config.py eval-cases-day1.json --model <model-a> --out eval-config-a.json
./run.sh build_eval_config.py eval-cases-day1.json --model <model-b> --out eval-config-b.json
./run.sh run_eval.py eval-config-a.json --repeat 3 --out results-a.md
./run.sh run_eval.py eval-config-b.json --repeat 3 --out results-b.md
```

- `eval-cases-day3.json` has `"prompt_from": "generate.py"`: the eval sends exactly what your feature
  sends. Change the prompt in `generate.py`, then rebuild the config.
- `eval-cases-day1.json` has its own `system` and `prompt_template`, written in the cases file.
- Each case gives its input as `"input"` (inline text) or `"input_file"` (one file or a list, joined).
  Optional `"replace": [["old", "new"]]` changes text that occurs exactly once (a bias variant, or an
  injection inserted after an anchor), and `"append"` adds text at the end.
- With the example cases, each `run_eval.py` pass cost about $0.04 at US$5 / US$25 per million tokens.

## 6. Adapt it to your domain

The labs grade **your** task. Every place to edit is marked; list them all with:

```bash
grep -n "YOUR TASK" *.py *.txt
```

| File | What to change | Blog articles | Car store | Medical clinic app |
|---|---|---|---|---|
| `generate.py` | The `YOUR TASK` block at the top: `ROLE`, `AUDIENCE`, `DOCUMENT`, `MAX_SUMMARY_CHARS`, `BULLETS` / `MAX_BULLET_CHARS`, `IDEAL_OUTPUT`, `MIN_CHARS` / `MAX_CHARS` | a professor summarizing a blog article for students | a salesperson summarizing a car listing for first-time buyers | a receptionist summarizing a clinic policy for patients |
| `chat.py` | The `YOUR TASK` block: `SYSTEM` (the persona), `RULE_MAX_CHARS`, `USER_LABEL`, `ASSISTANT_LABEL` | the blog's reader-support bot | the store's WhatsApp assistant | the front-desk assistant (never gives medical advice) |
| `chat-turns.txt` | The 8 messages. Keep the structure described at the top of the file | a reader asking about a post | a customer asking about order #5521 | a patient rescheduling an appointment |
| `mini_rag.py` | Pass your own `.txt` (no code change). If it isn't in English, add stopwords and translate the fallback answer at the `YOUR TASK` markers | the blog's comment policy | the warranty rules | the cancellation policy |
| `tools_demo.py` | The `YOUR TASK` block above `TOOLS`: add a definition, a `validate_…` and a `run_…` function, and register them in `DISPATCH` | `search_posts(tag)` | `check_stock(model, year)` | `find_open_slots(specialty, date)` |
| `eval-cases-day1.json` | Your own `system`, `prompt_template` and 5 cases: 2 ordinary, 1 edge, 1 ambiguous, 1 that should not be answered | two articles pasted together as the edge case | a listing with no price, when the prompt asks for prices | a text with no clinic rules at all |
| `eval-cases-day3.json` | Your 6 cases: 2 normal, 1 edge, 1 to refuse, 1 injection, 1 bias. The prompt comes from `generate.py` | a reader's private e-mail as the case to refuse | a listing with an instruction hidden in it | the same policy with only a name changed |

**Your own documents:** save them as UTF-8 `.txt`, with one self-contained topic per paragraph
and a blank line between paragraphs. Then use them in place of the examples:

```bash
./run.sh generate.py my-document.txt --dry-run      # check the prompt first, for free
./run.sh generate.py my-document.txt
./run.sh mini_rag.py my-document.txt --show-chunks  # check the chunks, for free
./run.sh mini_rag.py my-document.txt "a question your document answers" "one it doesn't"
```

Tip: use `--retrieve-only` to calibrate `--min-score` on your document for free before any billed run.

## Using another provider

Each script talks to the model in one place, marked `YOUR PROVIDER` (list them with
`grep -n "YOUR PROVIDER" *.py`). To switch, for example to an OpenAI-compatible API:

1. Replace `anthropic` in `requirements.txt` with your provider's SDK, and the client creation
   (`anthropic.Anthropic()`) and error classes (`anthropic.APIError`, …) in each script.
2. At each `YOUR PROVIDER` call, send the same system prompt, messages and `max_tokens`, then map
   the response back to what the script reads: the text, the token usage, and the stop reason. The
   scripts branch on `end_turn`, `max_tokens`, `tool_use` and `refusal`; an OpenAI-compatible API
   calls them `stop`, `length`, `tool_calls` and `content_filter`.
3. In `tools_demo.py`, also convert the tool definitions (`input_schema` → your provider's schema
   field) and send tool results in your provider's format.
4. Use `--effort none` if your provider has no equivalent. In `chat.py`, `count_system_tokens()`
   uses an Anthropic-only endpoint: adapt it or make it return `None`.

The course's `run_eval.py` and `estimate_tokens.py` call the Anthropic API too: adapt their API
calls the same way, or run your cases by hand in your provider's chat app.

## 7. Windows (PowerShell, without WSL)

`run.sh` is a bash script, so set the key and model yourself, for the current window only:

```powershell
cd genai-beginners-lab-scripts
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "your-key"               # these last until this window closes
$env:MODEL = "your-model-id"
.venv\Scripts\python generate.py example-document.txt
.venv\Scripts\python chat.py chat-turns.txt --max-turns 3
.venv\Scripts\python build_eval_config.py eval-cases-day3.json
.venv\Scripts\python run_eval.py eval-config.json --out results.md
Remove-Item Env:ANTHROPIC_API_KEY, Env:MODEL      # when you are done
```

## 8. Troubleshooting

| Error | Cause and fix |
|---|---|
| `No model set…` / `error: no model set…` | `MODEL` in `.env.local` is empty or still `REPLACE_ME`. Paste the model id from your provider's docs, or pass `--model`. |
| `404 … not_found_error … model` | The model id doesn't exist or your key can't use it. Copy it exactly from your provider's docs. |
| `401 … API key is invalid.` / `The API key was rejected` | The key was revoked or mistyped. Create a new one and paste it into `.env.local`. |
| `400 … anthropic-workspace-id is required` | Your Anthropic key is identity-linked. Uncomment `ANTHROPIC_CUSTOM_HEADERS` in `.env.local` and add your `wrkspc_…` id. |
| `credit balance is too low` | Buy credits in your provider's console. Some providers require a positive balance even for free endpoints. |
| `error: paste a real key into …/.env.local first` | `ANTHROPIC_API_KEY` in `.env.local` still says `REPLACE_ME`. |
| `error: no such script: …/run_eval.py` | Copy the course's `run_eval.py` (and `estimate_tokens.py`) into this folder. |
| `error: case …: '…' must occur exactly once in the input` | The `old` text of a `replace` pair isn't in that input, or appears more than once. Copy it exactly and make it unique. |
| `This script needs the SDK` | Run through `./run.sh`, or install into the venv: `.venv/bin/pip install -r requirements.txt`. |
| `No such file or directory: .venv/bin/python` | Create the venv inside this folder (step 2). |
| `That … could not be processed.` (`status: refusal`) | The API's safety filter blocked the request, sometimes by mistake. Run it again; if it keeps happening, make `IDEAL_OUTPUT` more neutral or try another document. |
| `That looks like a title or a link…` | Your document is shorter than `MIN_CHARS` in `generate.py`. Paste the full text, or lower the limit. |
| Every question in `mini_rag.py` short-circuits | `--min-score` is too high for your document, or its language needs stopwords. Calibrate with `--retrieve-only`. |

## Keep your key safe

- **Never commit or share `.env.local`.** It is already in `.gitignore`.
- **Don't `export` your API key in `~/.zshrc` or `~/.bashrc`.** Other tools on your machine that read
  the same variable (AI coding assistants, other scripts) would silently use and bill it. `run.sh`
  avoids this: the key exists only while the command runs.

## License

MIT. See [LICENSE](LICENSE).
