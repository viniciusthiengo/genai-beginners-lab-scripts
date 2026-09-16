#!/usr/bin/env python3
"""Multi-turn chat with an explicit, trimmable history — Day 2 lab, Exercise 3.

A runnable version of the `ChatSession` sketch from the course text. The model
remembers nothing between calls; everything that looks like memory is the list
in `ChatSession.history`, which this script resends in full on every request.

The persona has a checkable rule, as the exercise demands. The bundled
EXAMPLE is the night security guard of a university, who must answer in
**40 characters or less**. Every reply is measured against that rule and the
result is printed next to it, so "did the persona hold?" is a count, not an
impression.

>>> To adapt it to your own domain, edit the "YOUR TASK" block below and the
eight messages in chat-turns.txt. <<<

Three trimming strategies, same eight messages:

    ./run.sh chat.py chat-turns.txt                       # keep everything
    ./run.sh chat.py chat-turns.txt --max-turns 3         # truncate
    ./run.sh chat.py chat-turns.txt --max-turns 3 --summarize

The eight messages live in chat-turns.txt so all three runs are fed the exact
same input. Turn 8 can only be answered from turn 1, which is what the last
two runs trim away.

Other modes:

    ./run.sh chat.py                          # interactive; /quit to leave
    ./run.sh chat.py chat-turns.txt --dry-run # free: no API call, fake replies
    ./run.sh chat.py chat-turns.txt --show-payload   # dump what is sent

Needs the `anthropic` package and ANTHROPIC_API_KEY — run.sh supplies both.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Optional, Tuple

try:
    import anthropic
except ImportError:
    sys.exit("This script needs the SDK. Run: pip install anthropic")

# =============================================================================
# >>> YOUR TASK — edit this block, then write your own chat-turns.txt. <<<
#
# The values below are a runnable EXAMPLE (a university's night security
# guard). Replace them with a persona from your own domain, for example:
#
#   car store       "You are the WhatsApp assistant of a used-car store. You answer
#                    questions about stock, test drives and financing. Always reply
#                    in at most 80 characters."           USER_LABEL "Customer"
#   medical clinic  "You are the front-desk assistant of a dental clinic. You handle
#                    appointments and opening hours and never give medical advice.
#                    Always reply in at most 60 characters."  USER_LABEL "Patient"
#
# Keep the rule checkable by code: the script counts characters. If you pick a
# different kind of rule, also change the check marked "YOUR TASK" in send().
# =============================================================================

# The persona rule. It is a character count on purpose: "be brief" cannot be
# verified from the output, 40 characters can. Keep it equal to the number
# written in SYSTEM.
RULE_MAX_CHARS = 40

SYSTEM = (
    "You are the night security guard of the University of Business. You "
    "control building access, the keys and the lost-and-found desk, and you "
    "speak to students at the door. "
    f"Always reply in at most {RULE_MAX_CHARS} characters. Never write a longer reply."
)

# How the two sides are labelled in the printout and in the transcript the
# summarizer reads.
USER_LABEL = "Student"
ASSISTANT_LABEL = "Guard"

# >>> end of YOUR TASK <<<
# =============================================================================

# >>> YOUR PROVIDER: the model id comes from MODEL in .env.local (or --model),
# so no model is hardcoded here. Use any model id your provider's docs list.
DEFAULT_MODEL = os.environ.get("MODEL", "").strip()

# A persona's answer is a handful of words, but on models that think before
# answering, thinking tokens count against max_tokens too. 1000 leaves room for the
# reply plus any thinking at effort "low", and still fails loudly — with
# stop_reason "max_tokens" — instead of quietly returning a fragment.
DEFAULT_MAX_TOKENS = 1000

# The summarizer is a different job from the persona, so it gets its own system
# instruction. Handing it the persona would produce a 40-character summary,
# which is useless — the persona governs replies to the user, not the internal
# bookkeeping call. It is domain-neutral; you should not need to change it.
SUMMARIZER_SYSTEM = (
    "You compress chat transcripts. Write ONE short paragraph that preserves "
    "the facts a later reply might need: names, numbers, IDs, rooms, objects, "
    "and anything the assistant promised or refused. Keep exact numbers exact. "
    "No greeting, no commentary, no bullet points."
)
SUMMARY_MAX_TOKENS = 500

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


def extract_text(response) -> str:
    """Pull the text out of a response, ignoring non-text blocks.

    Content is a list of blocks, and on models that think there may be
    thinking blocks before the text. Filter by type rather than reading
    content[0] blindly.
    """
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()


def render_transcript(messages: List[Dict[str, str]]) -> str:
    """Flatten messages into plain text, for the summarizer to read."""
    label = {"user": USER_LABEL, "assistant": ASSISTANT_LABEL}
    return "\n".join(
        f"{label.get(m['role'], m['role'])}: {m['content']}" for m in messages
    )


class ChatSession:
    """Holds the conversation and decides what to send on each turn.

    The two things worth staring at are `_trim`, which is where the memory is
    actually thrown away, and `_system_for_request`, which is why the persona
    never is.
    """

    def __init__(
        self,
        client,
        system_prompt: str = SYSTEM,
        model: str = DEFAULT_MODEL,
        max_turns: Optional[int] = None,
        summarize: bool = False,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        effort: Optional[str] = "low",
        dry_run: bool = False,
    ) -> None:
        self.client = client
        self.system = system_prompt
        self.model = model
        self.max_turns = max_turns
        self.summarize = summarize
        self.max_tokens = max_tokens
        self.effort = effort
        self.dry_run = dry_run

        self.history: List[Dict[str, str]] = []  # alternating user/assistant
        self.summary: Optional[str] = None  # set only when --summarize trims

        # Running totals, for the cost report at the end.
        self.reply_calls = 0
        self.summary_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    # -- history management -------------------------------------------------

    def _trim(self) -> List[Dict[str, str]]:
        """Keep only the most recent turns. Returns what was dropped.

        Called after the new user message is appended, so the newest message is
        always kept. Two rules are enforced here, and the second one is the bug
        the course text warns about: after slicing, the list may start with an
        assistant message, which providers reject because the first message has
        to come from the user. Drop one more to realign.
        """
        if self.max_turns is None:
            return []
        max_messages = self.max_turns * 2
        if len(self.history) <= max_messages:
            return []

        keep = self.history[-max_messages:]
        dropped = self.history[: len(self.history) - len(keep)]
        while keep and keep[0]["role"] != "user":
            dropped.append(keep.pop(0))  # stays chronological: head then pops
        self.history = keep
        return dropped

    def _update_summary(self, dropped: List[Dict[str, str]]) -> None:
        """Fold the messages that were just trimmed into the rolling summary.

        This is the extra model call that summarization costs — one per trim,
        not one per turn. It is billed, and it happens before the reply call,
        so it also adds latency to that turn.
        """
        if self.dry_run:
            self.summary = f"[dry-run summary of {len(dropped)} trimmed messages]"
            return

        prior = f"Summary of even older turns:\n{self.summary}\n\n" if self.summary else ""
        prompt = (
            f"{prior}Conversation to summarize:\n{render_transcript(dropped)}"
        )
        request = {
            "model": self.model,
            "max_tokens": SUMMARY_MAX_TOKENS,
            "system": SUMMARIZER_SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.effort:
            request["output_config"] = {"effort": self.effort}

        try:
            # >>> YOUR PROVIDER: the call to the model API. See README, "Using another provider".
            response = self.client.messages.create(**request)
        except anthropic.APIError as error:
            # A failed summary must not take the turn down with it: the reply
            # call can still go ahead, just without the older context.
            print(f"warning: summarization failed ({error})", file=sys.stderr)
            return

        self.summary_calls += 1
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        text = extract_text(response)
        if text:
            self.summary = text

    def _system_for_request(self) -> str:
        """The system block actually sent: persona first, summary appended.

        The persona is never trimmed — it is not part of `history` at all, so
        no amount of trimming can reach it. The summary rides along here rather
        than in the message list, which keeps the list a clean alternation of
        real turns.
        """
        if not self.summary:
            return self.system
        return (
            f"{self.system}\n\n"
            "Earlier in this conversation (summary of trimmed turns):\n"
            f"{self.summary}"
        )

    # -- the turn -----------------------------------------------------------

    def send(self, user_text: str) -> Tuple[str, Dict]:
        """Run one turn. Returns (reply, meta).

        `meta` carries what the lab needs to measure: how many messages were
        sent, how many were thrown away first, whether the 40-character rule
        held, and what it cost.
        """
        meta: Dict = {
            "status": "ok",
            "stop_reason": None,
            "trimmed": 0,
            "summarized": False,
            "messages_sent": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "rule_ok": None,
            "reply_chars": 0,
        }

        self.history.append({"role": "user", "content": user_text})

        # Trim BEFORE the call, not after: the point is to bound what goes out.
        dropped = self._trim()
        meta["trimmed"] = len(dropped)
        if dropped and self.summarize:
            self._update_summary(dropped)
            meta["summarized"] = True

        system = self._system_for_request()
        meta["messages_sent"] = len(self.history)
        meta["system"] = system
        meta["payload"] = list(self.history)  # a copy: history grows below

        if self.dry_run:
            reply = "[dry-run — no model call]"
            self.history.append({"role": "assistant", "content": reply})
            meta["status"] = "dry_run"
            return reply, meta

        request = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,  # resent on every single request — see the totals
            "messages": self.history,
        }
        if self.effort:
            request["output_config"] = {"effort": self.effort}

        try:
            # >>> YOUR PROVIDER: the call to the model API. See README, "Using another provider".
            response = self.client.messages.create(**request)
        except anthropic.APITimeoutError:
            return self._failed(meta, "timeout", "The request timed out.")
        except anthropic.AuthenticationError:
            return self._failed(
                meta, "auth_error", "The API key was rejected. Check ANTHROPIC_API_KEY."
            )
        except anthropic.RateLimitError:
            return self._failed(
                meta, "rate_limited", "Too many requests. Try again in a minute."
            )
        except anthropic.APIError as error:
            meta["error"] = str(error)
            return self._failed(meta, "api_error", "Something went wrong.")

        self.reply_calls += 1
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        meta["stop_reason"] = response.stop_reason
        meta["usage"] = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        text = extract_text(response)

        # Check why it stopped before trusting the text. A fragment cut off by
        # max_tokens would sail through the 40-character check and look like a
        # very obedient reply.
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            meta["refusal_category"] = getattr(details, "category", None)
            meta["refusal_explanation"] = getattr(details, "explanation", None)
            return self._failed(meta, "refusal", "That request could not be processed.")
        if response.stop_reason == "max_tokens":
            meta["rejected_text"] = text
            return self._failed(
                meta, "max_tokens", "The reply was cut off by the output cap."
            )
        if response.stop_reason not in ("end_turn", "stop_sequence"):
            meta["rejected_text"] = text or None
            return self._failed(
                meta,
                "unexpected_stop",
                f"The model stopped for an unexpected reason ({response.stop_reason}).",
            )
        if not text:
            return self._failed(meta, "empty", "The model returned no text.")

        self.history.append({"role": "assistant", "content": text})
        meta["reply_chars"] = len(text)
        # >>> YOUR TASK (only if your persona rule is not a character limit):
        # replace this check with one that tests your rule.
        meta["rule_ok"] = len(text) <= RULE_MAX_CHARS
        return text, meta

    def _failed(self, meta: Dict, status: str, message: str) -> Tuple[str, Dict]:
        """Abandon the turn, leaving the history valid for the next one.

        The user message was already appended; with no assistant reply to pair
        it with, the list would stop alternating and the next request would be
        rejected. Pop it back off.
        """
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        meta["status"] = status
        return message, meta


def count_system_tokens(client, model: str, system: str) -> Optional[int]:
    """Size the persona in tokens, via the free count_tokens endpoint.

    Two counts and a subtraction, because count_tokens always prices a whole
    request: the difference between "with system" and "without" is the persona
    alone. Free, but never worth failing a run over.
    """
    probe = [{"role": "user", "content": "."}]
    try:
        base = client.messages.count_tokens(model=model, messages=probe).input_tokens
        full = client.messages.count_tokens(
            model=model, system=system, messages=probe
        ).input_tokens
    except anthropic.APIError:
        return None
    return full - base


def read_turns(path: str) -> List[str]:
    """One user message per line. Blank lines and #-comments are ignored."""
    if path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        try:
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            sys.exit(f"Turns file not found: {path}")
    turns = [line.strip() for line in lines]
    return [t for t in turns if t and not t.startswith("#")]


def cost_of(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    price = prices()
    if not price:
        return None
    return (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000


def print_turn(number: int, user_text: str, reply: str, meta: Dict, show_payload: bool) -> None:
    print()
    print(f"=== turn {number} " + "=" * 52)
    print(f"{USER_LABEL.lower() + ':':<10}{user_text}")
    print(f"{ASSISTANT_LABEL.lower() + ':':<10}{reply}")

    if meta["rule_ok"] is not None:
        verdict = "OK" if meta["rule_ok"] else "VIOLATION"
        print(
            f"          rule: {verdict} "
            f"({meta['reply_chars']}/{RULE_MAX_CHARS} chars)"
        )
    elif meta["status"] not in ("ok", "dry_run"):
        print(f"          status: {meta['status']}")
        if meta.get("error"):
            print(f"          error: {meta['error']}")
        if meta.get("refusal_category"):
            print(f"          refusal category: {meta['refusal_category']}")
        if meta.get("refusal_explanation"):
            print(f"          refusal explanation: {meta['refusal_explanation']}")
        if meta.get("rejected_text"):
            print(f"          text produced but not used: {meta['rejected_text']!r}")

    detail = f"          sent: system + {meta['messages_sent']} messages"
    if meta["trimmed"]:
        detail += f" ({meta['trimmed']} trimmed away"
        detail += " — summarized first)" if meta["summarized"] else ")"
    print(detail)

    usage = meta["usage"]
    if usage["input_tokens"] or usage["output_tokens"]:
        line = (
            f"          tokens: {usage['input_tokens']:,} in / "
            f"{usage['output_tokens']:,} out"
        )
        print(line)

    if show_payload:
        print("          --- exact payload sent ---")
        for line in meta["system"].splitlines():
            print(f"          [system] {line}")
        for message in meta.get("payload", []):
            print(f"          [{message['role']}] {message['content']}")
        print("          --- end payload ---")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-turn chat with a trimmable history and a checkable persona."
    )
    parser.add_argument(
        "turns_file",
        nargs="?",
        help="file with one user message per line, or - for stdin. "
        "Omit it for an interactive session.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="keep only the last N exchanges (default: keep everything). "
        "The exercise uses 3.",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="replace trimmed turns with a rolling summary instead of "
        "dropping them. Costs one extra model call per trim.",
    )
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--effort",
        default="low",
        choices=["low", "medium", "high", "xhigh", "max", "none"],
        help="thinking depth (default: low). 'none' omits the parameter, for models that reject it.",
    )
    parser.add_argument(
        "--show-payload",
        action="store_true",
        help="print the exact system block and message list sent each turn.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="walk the turns without calling the model. Free; shows trimming.",
    )
    args = parser.parse_args()

    if not args.dry_run:
        require_model(args.model)
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    session = ChatSession(
        client,
        model=args.model,
        max_turns=args.max_turns,
        summarize=args.summarize,
        max_tokens=args.max_tokens,
        effort=None if args.effort == "none" else args.effort,
        dry_run=args.dry_run,
    )

    strategy = "keep everything"
    if args.max_turns is not None:
        strategy = f"last {args.max_turns} turns"
        strategy += " + rolling summary" if args.summarize else " (truncate)"

    print(f"model:     {args.model or '(not set)'}")
    print(f"history:   {strategy}")
    print(f"persona:   {SYSTEM}")
    print(f"rule:      every reply <= {RULE_MAX_CHARS} characters")

    turns = read_turns(args.turns_file) if args.turns_file else None
    violations: List[int] = []
    failures = 0
    turns_run = 0

    def run_turn(number: int, text: str) -> None:
        nonlocal failures, turns_run
        turns_run += 1
        reply, meta = session.send(text)
        print_turn(number, text, reply, meta, args.show_payload)
        if meta["rule_ok"] is False:
            violations.append(number)
        if meta["status"] not in ("ok", "dry_run"):
            failures += 1

    if turns is not None:
        for number, text in enumerate(turns, start=1):
            run_turn(number, text)
    else:
        print("\ninteractive session — /quit to leave")
        number = 0
        while True:
            try:
                text = input(f"\n{USER_LABEL.lower()}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text:
                continue
            if text in ("/quit", "/exit"):
                break
            number += 1
            run_turn(number, text)

    if session.summary:
        print()
        print("=== rolling summary held at the end " + "=" * 32)
        print(session.summary)

    print()
    print("=== run totals " + "=" * 53)
    calls = session.reply_calls + session.summary_calls
    print(f"turns:              {turns_run}")
    print(
        f"billed calls:       {calls} "
        f"({session.reply_calls} replies + {session.summary_calls} summaries)"
    )
    print(f"rule violations:    {len(violations) or 'none'}"
          + (f" (turns {', '.join(str(v) for v in violations)})" if violations else ""))
    if failures:
        print(f"failed turns:       {failures}")

    if session.input_tokens or session.output_tokens:
        print(
            f"tokens:             {session.input_tokens:,} in / "
            f"{session.output_tokens:,} out"
        )
        cost = cost_of(args.model, session.input_tokens, session.output_tokens)
        if cost is not None:
            print(f"cost:               ${cost:.4f}")

        # The system instruction is resent on every call. This is the number
        # the write-up asks for, and the reason a long persona is not free.
        system_tokens = count_system_tokens(client, args.model, SYSTEM)
        if system_tokens is not None and calls:
            total = system_tokens * calls
            share = 100.0 * total / session.input_tokens if session.input_tokens else 0
            print(
                f"persona:            {system_tokens} tokens x {calls} calls = "
                f"{total:,} tokens ({share:.1f}% of all input)"
            )

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
