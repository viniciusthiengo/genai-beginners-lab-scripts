#!/usr/bin/env python3
"""Build an eval-config.json for the course's run_eval.py from a small cases file.

run_eval.py only accepts each case's input as a literal string, so a test set
built from whole documents is painful to write by hand. This script reads a
cases file (JSON) where each case points at .txt files, embeds their text, and
writes the eval-config.json that run_eval.py expects.

Two ways to set the prompt, one per cases file:

    "prompt_from": "generate.py"          use generate.py's SYSTEM and PROMPT_TEMPLATE,
                                          so the eval tests exactly what your feature
                                          sends (Day 3, adversarial evaluation)
    "system" + "prompt_template"          your own prompt, written in the cases file
                                          (Day 1, choosing a model)

Each case has an "id", an "expected" description, and its input as one of:

    "input": "inline text"
    "input_file": "doc.txt"               or a list of files, joined with blank lines
    optional "replace": [["old", "new"]]  each "old" must occur exactly once — for a
                                          bias variant (change one name) or an
                                          injection (insert a line after an anchor)
    optional "append": "text"             added after a blank line, e.g. a question

>>> YOUR TASK: copy eval-cases-day1.json or eval-cases-day3.json and write your
own cases in it. No code change is needed. <<<

Usage:
    ./run.sh build_eval_config.py eval-cases-day3.json
    ./run.sh build_eval_config.py eval-cases-day3.json --only R1,I1 --out eval-config-repeat.json
    ./run.sh build_eval_config.py eval-cases-day1.json --model <model-a> --out eval-config-a.json

The model comes from --model, or from MODEL in .env.local. Free: no API call.
"""

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).parent

CASE_KEYS = {"id", "kind", "expected", "input", "input_file", "replace", "append"}
FILE_KEYS = {"version", "prompt_from", "system", "prompt_template", "max_tokens", "criteria", "cases"}


def fail(message: str) -> None:
    sys.exit(f"error: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"input file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_input(case: Dict, base: Path) -> str:
    """Assemble one case's input text from the cases file's instructions."""
    case_id = case["id"]
    if ("input" in case) == ("input_file" in case):
        fail(f"case {case_id}: give exactly one of 'input' or 'input_file'")

    if "input" in case:
        text = case["input"]
    else:
        files = case["input_file"]
        files = [files] if isinstance(files, str) else files
        text = "\n\n".join(read_text(base / name) for name in files)

    for pair in case.get("replace", []):
        if not (isinstance(pair, list) and len(pair) == 2):
            fail(f"case {case_id}: each 'replace' entry must be [\"old\", \"new\"]")
        old, new = pair
        count = text.count(old)
        if count != 1:
            fail(f"case {case_id}: {old!r} must occur exactly once in the input, found {count}")
        text = text.replace(old, new)

    if case.get("append"):
        text = f"{text}\n\n{case['append']}"
    return text


def load_prompt(spec: Dict) -> Dict:
    """Return system, prompt_template and max_tokens from the cases file or generate.py."""
    if "prompt_from" in spec:
        if "system" in spec or "prompt_template" in spec:
            fail("use either 'prompt_from' or 'system' + 'prompt_template', not both")
        module_name = Path(spec["prompt_from"]).stem
        sys.path.insert(0, str(HERE))
        module = importlib.import_module(module_name)
        return {
            "system": module.SYSTEM,
            "prompt_template": module.PROMPT_TEMPLATE,
            "max_tokens": getattr(module, "DEFAULT_MAX_TOKENS", 1000),
        }
    if "prompt_template" not in spec:
        fail("the cases file needs 'prompt_from' or a 'prompt_template'")
    return {
        "system": spec.get("system", ""),
        "prompt_template": spec["prompt_template"],
        "max_tokens": spec.get("max_tokens", 4000),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build eval-config.json for run_eval.py.")
    parser.add_argument("cases_file", help="JSON cases file, e.g. eval-cases-day3.json")
    parser.add_argument("--model", default=os.environ.get("MODEL", "").strip(),
                        help="model id (default: MODEL from .env.local)")
    parser.add_argument("--effort", default="low",
                        help="low / medium / high …, or 'none' to omit the parameter")
    parser.add_argument("--only", help="comma-separated case ids to keep, e.g. R1,I1")
    parser.add_argument("--out", default="eval-config.json", help="output path")
    args = parser.parse_args()

    if not args.model or "REPLACE_ME" in args.model:
        fail("no model set. Put your provider's model id in MODEL in .env.local, or pass --model.")

    cases_path = Path(args.cases_file)
    try:
        spec = json.loads(cases_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"cases file not found: {cases_path}")
    except json.JSONDecodeError as error:
        fail(f"{cases_path} is not valid JSON: {error}")

    unknown = set(spec) - FILE_KEYS
    if unknown:
        fail(f"unknown key(s) in {cases_path}: {', '.join(sorted(unknown))}")

    prompt = load_prompt(spec)
    if "{input}" not in prompt["prompt_template"]:
        fail("the prompt template must contain the placeholder {input}")

    cases: List[Dict] = spec.get("cases") or []
    if not cases:
        fail("the cases file has no cases")
    seen = set()
    for case in cases:
        if "id" not in case:
            fail("every case needs an 'id'")
        if case["id"] in seen:
            fail(f"duplicate case id {case['id']!r}")
        seen.add(case["id"])
        extra = set(case) - CASE_KEYS
        if extra:
            fail(f"case {case['id']}: unknown key(s) {', '.join(sorted(extra))}")

    if args.only:
        wanted = [name.strip() for name in args.only.split(",") if name.strip()]
        missing = [name for name in wanted if name not in seen]
        if missing:
            fail(f"--only names unknown case id(s): {', '.join(missing)}")
        cases = [case for case in cases if case["id"] in wanted]

    built = []
    for case in cases:
        entry = {"id": case["id"], "input": build_input(case, cases_path.parent)}
        label = f"{case['kind']}: " if case.get("kind") else ""
        if case.get("expected") or label:
            entry["expected"] = label + case.get("expected", "")
        built.append(entry)

    config = {
        "version": spec.get("version", cases_path.stem),
        "model": args.model,
        "max_tokens": prompt["max_tokens"],
        "effort": None if args.effort == "none" else args.effort,
        "system": prompt["system"],
        "prompt_template": prompt["prompt_template"],
        "cases": built,
    }
    if spec.get("criteria"):
        config["criteria"] = spec["criteria"]

    out = Path(args.out)
    out.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chars = sum(len(case["input"]) for case in built)
    source = spec.get("prompt_from", "the cases file")
    print(f"Wrote {out}: {len(built)} case(s), {chars:,} input characters, "
          f"model {args.model}, prompt from {source}")
    print(f"Next: ./run.sh run_eval.py {out} --out results.md   (billed)")


if __name__ == "__main__":
    main()
