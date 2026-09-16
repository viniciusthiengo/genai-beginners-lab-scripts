#!/usr/bin/env bash
# Run one of this directory's Python scripts against the local venv, loading
# ANTHROPIC_API_KEY, MODEL and the optional PRICE_* values from .env.local for
# the lifetime of this process only. The credentials die with this script, so
# they never enter your interactive shell, where other tools that read the same
# variable (AI coding assistants, other scripts) would silently use and bill them.
#
#   ./run.sh estimate_tokens.py my-document.txt          # free, no key needed
#   ./run.sh estimate_tokens.py my-document.txt --exact  # free, needs a key
#   ./run.sh run_eval.py eval-config.json                # BILLED model calls
#   ./run.sh generate.py example-document.txt            # BILLED model call
#   ./run.sh chat.py chat-turns.txt --max-turns 3        # BILLED model calls
#   ./run.sh mini_rag.py example-document.txt "question" # BILLED model call
#   ./run.sh tools_demo.py "question"                    # BILLED model calls
#   ./run.sh build_eval_config.py eval-cases-day3.json   # free: writes eval-config.json
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
    cat >&2 <<'USAGE'
usage: ./run.sh <script.py> [args...]

  estimate_tokens.py   count tokens in a file. Free; needs a key only with --exact
  run_eval.py          run a prompt template over a test set. BILLED model calls
  generate.py          summarize one document, single shot. BILLED model call
  chat.py              multi-turn chat with a trimmable history. BILLED model calls
  mini_rag.py          grounded answers over one .txt file. BILLED; --retrieve-only is free
  tools_demo.py        tool-calling loop with validation. BILLED; --validation-demo is free
  build_eval_config.py build eval-config.json for run_eval.py from a cases file. Free
USAGE
    exit 2
fi

script="$1"
shift
[[ "$script" == *.py ]] || script="$script.py"
if [[ ! -f "$DIR/$script" ]]; then
    echo "error: no such script: $DIR/$script" >&2
    exit 1
fi

# estimate_tokens.py reaches the API only with --exact. Everything else is
# assumed to need credentials from its first call.
needs_key=1
if [[ "$script" == "estimate_tokens.py" && " $* " != *" --exact "* ]]; then
    needs_key=0
fi
if [[ "$script" == "mini_rag.py" && ( " $* " == *" --retrieve-only "* || " $* " == *" --show-chunks "* ) ]]; then
    needs_key=0
fi
if [[ "$script" == "tools_demo.py" && " $* " == *" --validation-demo "* ]]; then
    needs_key=0
fi
if [[ "$script" == "build_eval_config.py" ]]; then
    needs_key=0
fi
if [[ ( "$script" == "generate.py" || "$script" == "chat.py" ) && " $* " == *" --dry-run "* ]]; then
    needs_key=0
fi

# Load .env.local whenever it exists, so free scripts see MODEL too; only the
# billed ones insist on a key.
if [[ -f "$DIR/.env.local" ]]; then
    set -a
    # shellcheck disable=SC1091
    . "$DIR/.env.local"
    set +a
fi
if (( needs_key )); then
    if [[ ! -f "$DIR/.env.local" ]]; then
        echo "error: $script needs credentials, but $DIR/.env.local is missing" >&2
        exit 1
    fi
    if [[ -z "${ANTHROPIC_API_KEY:-}" || "${ANTHROPIC_API_KEY}" == *REPLACE_ME* ]]; then
        echo "error: paste a real key into $DIR/.env.local first" >&2
        exit 1
    fi
fi

# estimate_tokens.py --exact uses the free count_tokens endpoint; run_eval.py,
# generate.py and chat.py call messages.create, which draws down real credit. Say
# so once, on stderr, so it never pollutes piped stdout. --dry-run never calls out.
if [[ "$script" == "run_eval.py" ]] || { [[ "$script" == "generate.py" || "$script" == "chat.py" ]] && [[ " $* " != *" --dry-run "* ]]; } \
    || { [[ "$script" == "mini_rag.py" || "$script" == "tools_demo.py" ]] && (( needs_key )); }; then
    echo "note: $script makes billed model calls (messages.create)." >&2
fi

exec "$DIR/.venv/bin/python" "$DIR/$script" "$@"
