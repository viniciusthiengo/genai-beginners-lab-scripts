#!/usr/bin/env python3
"""A bounded tool-calling loop with two validated tools — Day 2 lab, Exercise 5.

Runnable version of the course's `chat_with_tools` sketch. Two real tools, a
calculator and a currency converter; arguments are validated before anything
runs, and every round of the loop is printed so the protocol is visible:

    send messages + tool definitions
    stop_reason == "tool_use"  ->  (1) append the assistant turn, with its call IDs
                                   (2) validate and run EVERY tool_use block
                                   (3) a failure is still a result (is_error)
                                   append all results in ONE user message
    stop_reason == "end_turn"  ->  done
    round == MAX_ROUNDS        ->  give up gracefully

>>> To adapt it to your own domain, follow the "YOUR TASK" block above TOOLS. <<<
The two bundled tools are domain-neutral EXAMPLES.

Usage:
    ./run.sh tools_demo.py "What is 15% of 4,000, and what is that in euros?"
    ./run.sh tools_demo.py --validation-demo     # free: bad arguments, no model call

Needs the `anthropic` package and ANTHROPIC_API_KEY — run.sh supplies both.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

try:
    import anthropic
except ImportError:
    sys.exit("This script needs the SDK. Run: pip install anthropic")

# >>> YOUR PROVIDER: the model id comes from MODEL in .env.local (or --model),
# so no model is hardcoded here. Use any model id your provider's docs list.
DEFAULT_MODEL = os.environ.get("MODEL", "").strip()
DEFAULT_MAX_TOKENS = 1000
MAX_ROUNDS = 6  # the exit condition is "the model stopped asking" — never trust it alone


# Optional: your model's price in USD per 1M input / output tokens, from your
# provider's pricing page (PRICE_INPUT_PER_MTOK and PRICE_OUTPUT_PER_MTOK in
# .env.local). Without them the cost line is skipped.
def prices() -> Optional[Tuple[float, float]]:
    try:
        return (
            float(os.environ["PRICE_INPUT_PER_MTOK"]),
            float(os.environ["PRICE_OUTPUT_PER_MTOK"]),
        )
    except (KeyError, ValueError):
        return None


def require_model(model: str) -> str:
    """Stop before any billed call when no real model id is configured."""
    if not model or "REPLACE_ME" in model:
        sys.exit("No model set. Put your provider's model id in MODEL in .env.local, or pass --model.")
    return model


# Fixed reference rates, units per 1 USD. A demo must not pretend to be live:
# the tool says so in its description and in every result.
RATES = {"USD": Decimal("1"), "EUR": Decimal("0.92"), "GBP": Decimal("0.79"),
         "BRL": Decimal("5.40"), "JPY": Decimal("150")}
MAX_AMOUNT = Decimal("1000000000")
MAX_EXPRESSION_CHARS = 200
MAX_EXPONENT = 100

# =============================================================================
# >>> YOUR TASK — replace or add tools for your domain, in three places:
#   1. TOOLS below: name, a description that says WHEN to call it, and a typed
#      input_schema with "required" and "additionalProperties": False.
#   2. A validate_<name>(args) that rejects bad arguments (raise ValueError) and
#      a run_<name>(...) that does the work and returns a string.
#   3. DISPATCH (below the functions): "name": (validate_<name>, run_<name>).
# Start with read-only lookups, for example:
#   car store       check_stock(model, year)        -> units available, price
#   medical clinic  find_open_slots(specialty, date) -> free appointment times
# Anything that changes data (book, buy, cancel) should only create a PENDING
# request that a person confirms. If you remove an example tool, remove its
# cases from validation_demo() too.
# =============================================================================

# -- Tool definitions: name, trigger-stating description, typed schema ----------------

TOOLS = [
    {
        "name": "calculate",
        "description": (
            "Evaluate an arithmetic expression exactly. Call this whenever the answer "
            "needs arithmetic (percentages, totals, ratios) instead of computing it "
            "yourself. Supports numbers, + - * / ** and parentheses. Write percentages "
            "as multiplication: 15% of 4000 is 4000 * 0.15."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": 'For example "4000 * 0.15".'},
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
    {
        "name": "convert_currency",
        "description": (
            "Convert an amount of money from one currency to another at this app's fixed "
            "reference rates (not live market rates). Call this whenever the user asks "
            "what an amount is worth in a different currency. Supported codes: "
            "USD, EUR, GBP, BRL, JPY. Read-only: it moves no money."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Amount in from_currency. Must be positive."},
                "from_currency": {"type": "string", "description": "ISO 4217 code of the amount, e.g. USD."},
                "to_currency": {"type": "string", "description": "ISO 4217 code to convert into, e.g. EUR."},
            },
            "required": ["amount", "from_currency", "to_currency"],
            "additionalProperties": False,
        },
    },
]

# -- Validation: arguments come from the model, so they are untrusted --------------------


def schema_of(name: str) -> Dict:
    """The input_schema of the tool called `name` in TOOLS."""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool["input_schema"]
    raise KeyError(f"no tool named {name!r} in TOOLS")


def check_parameters(args, schema: Dict) -> None:
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    allowed = set(schema["properties"])
    for name in schema["required"]:
        if name not in args:
            raise ValueError(f"missing parameter '{name}'")
    for name in args:
        if name not in allowed:
            raise ValueError(f"unexpected parameter '{name}'")


def validate_calculate(args) -> Dict:
    check_parameters(args, schema_of("calculate"))
    expression = args["expression"]
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression must be a non-empty string")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ValueError(f"expression longer than {MAX_EXPRESSION_CHARS} characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ValueError("expression is not valid arithmetic")
    # Whitelist the syntax tree. This is what stops "__import__('os')...": names,
    # calls and attributes are simply not allowed node types.
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float):
                raise ValueError("only numbers, + - * / ** and parentheses are allowed")
        elif not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub,
                                   ast.Mult, ast.Div, ast.Pow, ast.UAdd, ast.USub)):
            raise ValueError("only numbers, + - * / ** and parentheses are allowed")
    return {"tree": tree}


def run_calculate(tree) -> str:
    def evaluate(node) -> Decimal:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant):
            return Decimal(str(node.value))  # "0.15" stays exact; no float drift
        if isinstance(node, ast.UnaryOp):
            value = evaluate(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        left, right = evaluate(node.left), evaluate(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ZeroDivisionError("division by zero")
            return left / right
        if abs(right) > MAX_EXPONENT:  # 10 ** 10 ** 10 would hang the process
            raise ValueError(f"exponent larger than {MAX_EXPONENT}")
        return left ** right

    return format(evaluate(tree).normalize(), "f")


def validate_convert_currency(args) -> Dict:
    check_parameters(args, schema_of("convert_currency"))
    amount = args["amount"]
    # bool is a subclass of int in Python: True would otherwise pass as 1.
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError(f"amount must be a number, got {type(amount).__name__}")
    amount = Decimal(str(amount))
    if not amount.is_finite() or amount <= 0:
        raise ValueError("amount must be positive")
    if amount > MAX_AMOUNT:
        raise ValueError(f"amount exceeds the {MAX_AMOUNT:,} limit")
    codes = []
    for name in ("from_currency", "to_currency"):
        code = args[name]
        if not isinstance(code, str) or code.strip().upper() not in RATES:
            raise ValueError(f"unsupported {name} {code!r} (supported: {', '.join(RATES)})")
        codes.append(code.strip().upper())
    return {"amount": amount, "from_currency": codes[0], "to_currency": codes[1]}


def run_convert_currency(amount: Decimal, from_currency: str, to_currency: str) -> str:
    rate = RATES[to_currency] / RATES[from_currency]
    converted = (amount * rate).quantize(Decimal("0.01"))
    return json.dumps({
        "amount": str(amount), "from_currency": from_currency,
        "converted": str(converted), "to_currency": to_currency,
        "rate": str(rate.quantize(Decimal("0.000001"))), "rate_source": "fixed reference rate, not live",
    })


# >>> YOUR TASK: register every tool here — "name": (validate_fn, run_fn).
DISPATCH = {
    "calculate": (validate_calculate, run_calculate),
    "convert_currency": (validate_convert_currency, run_convert_currency),
}


def execute(tool_use_id: str, name: str, args) -> Dict:
    """One tool_use block in, exactly one tool_result block out — success or not."""
    def error(message: str) -> Dict:
        return {"type": "tool_result", "tool_use_id": tool_use_id, "content": message, "is_error": True}

    if name not in DISPATCH:
        return error(f"Unknown tool: {name}")
    validate, run = DISPATCH[name]
    try:
        clean = validate(args)
    except ValueError as exc:
        return error(f"Invalid arguments: {exc}")
    try:
        return {"type": "tool_result", "tool_use_id": tool_use_id, "content": run(**clean)}
    except (ValueError, ArithmeticError, InvalidOperation) as exc:
        return error(f"Tool failed: {exc}")


# -- The loop ------------------------------------------------------------------------------


def describe_block(block) -> str:
    if block.type == "thinking":
        return "thinking  (text omitted by the API; block kept and sent back)"
    if block.type == "text":
        return f"text      {block.text!r}"
    if block.type == "tool_use":
        return f"tool_use  id={block.id}  {block.name} {json.dumps(block.input)}"
    return block.type


def chat_with_tools(client, user_text: str, args) -> Tuple[str, List, Dict]:
    messages: List = [{"role": "user", "content": user_text}]
    usage = {"in": 0, "out": 0, "rounds": 0, "tool_calls": 0}

    for round_number in range(1, MAX_ROUNDS + 1):
        usage["rounds"] = round_number
        print(f"\n=== round {round_number} " + "=" * 60)
        print(f"send:      messages[0..{len(messages) - 1}] + {len(TOOLS)} tool definitions")

        request = {"model": args.model, "max_tokens": args.max_tokens, "tools": TOOLS, "messages": messages}
        if args.effort != "none":
            request["output_config"] = {"effort": args.effort}
        try:
            # >>> YOUR PROVIDER: the call to the model API. See README, "Using another provider".
            response = client.messages.create(**request)
        except anthropic.APIError as exc:
            return f"Request failed: {exc}", messages, usage

        usage["in"] += response.usage.input_tokens
        usage["out"] += response.usage.output_tokens
        print(f"received:  stop_reason={response.stop_reason}  "
              f"({response.usage.input_tokens:,} in / {response.usage.output_tokens:,} out)")
        for i, block in enumerate(response.content):
            print(f"  content[{i}] {describe_block(block)}")

        # stop_reason drives every decision — not the presence of text.
        if response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})
            text = "\n".join(b.text for b in response.content if b.type == "text").strip()
            return text, messages, usage
        if response.stop_reason == "refusal":
            return "The request was declined.", messages, usage
        if response.stop_reason != "tool_use":
            return f"Stopped: stop_reason={response.stop_reason}.", messages, usage

        # (1) Record the request BEFORE answering it: the results cite its IDs.
        messages.append({"role": "assistant", "content": response.content})
        print(f"append:    messages[{len(messages) - 1}] = assistant turn    <- the REQUEST is recorded here")

        # (2)+(3) Every tool_use block gets a result, errors included, in ONE message.
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            usage["tool_calls"] += 1
            result = execute(block.id, block.name, block.input)
            flag = "  is_error" if result.get("is_error") else ""
            print(f"execute:   {block.id}  {block.name} -> {result['content']}{flag}")
            results.append(result)
        messages.append({"role": "user", "content": results})
        print(f"append:    messages[{len(messages) - 1}] = user turn, {len(results)} tool_result(s)"
              "    <- the RESULTS go back here")

    return "I couldn't complete that request within the allowed steps.", messages, usage


def print_messages(messages: List) -> None:
    """The final message list, compact: one line per content block."""
    print("\n=== message list " + "=" * 62)
    for i, message in enumerate(messages):
        content = message["content"]
        if isinstance(content, str):
            print(f"[{i}] {message['role']:<9} {content!r}")
            continue
        for j, block in enumerate(content):
            head = f"[{i}] {message['role']:<9}" if j == 0 else " " * 13
            if isinstance(block, dict):  # a tool_result we built
                flag = ", is_error" if block.get("is_error") else ""
                print(f"{head} tool_result  tool_use_id={block['tool_use_id']}{flag}  {block['content']!r}")
            elif block.type == "thinking":
                print(f"{head} thinking")
            elif block.type == "text":
                print(f"{head} text         {block.text!r}")
            elif block.type == "tool_use":
                print(f"{head} tool_use     id={block.id}  {block.name} {json.dumps(block.input)}")


def validation_demo() -> None:
    """Free: push bad arguments through the same execute() the loop uses."""
    cases = [
        ("convert_currency", {"amount": -50, "from_currency": "USD", "to_currency": "EUR"}),
        ("convert_currency", {"amount": "600", "from_currency": "USD", "to_currency": "EUR"}),
        ("convert_currency", {"amount": 600, "from_currency": "USD", "to_currency": "XYZ"}),
        ("convert_currency", {"amount": 600, "from_currency": "USD"}),
        ("convert_currency", {"amount": 5e12, "from_currency": "USD", "to_currency": "EUR"}),
        ("calculate", {"expression": "__import__('os').system('rm -rf ~')"}),
        ("calculate", {"expression": "10 ** 10 ** 10"}),
        ("calculate", {"expression": "1 / 0"}),
        ("send_payment", {"amount": 600, "recipient": "attacker"}),
        ("convert_currency", {"amount": 600, "from_currency": "USD", "to_currency": "EUR"}),
    ]
    for n, (name, arguments) in enumerate(cases, start=1):
        result = execute(f"toolu_demo_{n:02d}", name, arguments)
        print(f"{name}({json.dumps(arguments)})")
        print(f"  -> {json.dumps(result)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="A bounded, validated tool-calling loop.")
    parser.add_argument("question", nargs="?", help="the user message")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--effort", default="low", choices=["low", "medium", "high", "xhigh", "max", "none"])
    parser.add_argument("--validation-demo", action="store_true", help="run bad arguments through the validators. Free.")
    args = parser.parse_args()

    if args.validation_demo:
        validation_demo()
        return
    if not args.question:
        parser.error("give a question, or --validation-demo")

    require_model(args.model)
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    print(f"user:      {args.question}")
    answer, messages, usage = chat_with_tools(client, args.question, args)
    print_messages(messages)

    print("\n=== answer " + "=" * 68)
    print(answer)
    price = prices()
    cost = f"   cost: ${(usage['in'] * price[0] + usage['out'] * price[1]) / 1e6:.4f}" if price else ""
    print(f"\nrounds: {usage['rounds']}   tool calls: {usage['tool_calls']}   "
          f"tokens: {usage['in']:,} in / {usage['out']:,} out{cost}")


if __name__ == "__main__":
    main()
