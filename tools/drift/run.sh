#!/usr/bin/env bash
# Drift harness for the build-vs-buy plugin. It SPENDS TOKENS. Never run it in CI.
#
#   scorer mode:  frozen researcher reports -> /build-vs-buy:scorer, repeated --runs times
#   context mode: the full skill up to Checkpoint 1, in the with-docs or no-docs sandbox,
#                 repeated --runs times; collects each run's locked-context.md
#
# Output: OUT/TAG/run-K/... ; read it with analyze.py.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: run.sh --out DIR [--mode scorer|context] [--runs N] [--model ALIAS]
               [--topology independent|centralized] [--arm with-docs|no-docs]
               [--budget USD] [--tag NAME]
  --mode      scorer (default) or context
  --runs      repetitions (default 5)
  --model     scorer model alias passed to the scorer skill (default: the agent's pinned model)
  --topology  scorer mode only: one scorer per candidate (default) or one scorer for all,
              with the candidate order shuffled per run
  --arm       context mode only (default with-docs)
  --budget    --max-budget-usd cap for each claude call (default 1.50)
  --tag       output subdirectory name (default derived from the options)
EOF
  exit 2
}

MODE=scorer RUNS=5 MODEL="" TOPOLOGY=independent ARM=with-docs BUDGET=1.50 TAG="" OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:?}"; shift 2 ;;
    --runs) RUNS="${2:?}"; shift 2 ;;
    --model) MODEL="${2:?}"; shift 2 ;;
    --topology) TOPOLOGY="${2:?}"; shift 2 ;;
    --arm) ARM="${2:?}"; shift 2 ;;
    --budget) BUDGET="${2:?}"; shift 2 ;;
    --tag) TAG="${2:?}"; shift 2 ;;
    --out) OUT="${2:?}"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$OUT" ] || usage
case "$MODE" in scorer|context) ;; *) usage ;; esac
case "$TOPOLOGY" in independent|centralized) ;; *) usage ;; esac
case "$ARM" in with-docs|no-docs) ;; *) usage ;; esac
case "$RUNS" in ''|*[!0-9]*) usage ;; esac

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
FIXTURE="$HERE/fixtures"

# A leftover override would silently change which model runs, so remove both.
unset CLAUDE_CODE_SUBAGENT_MODEL CLAUDE_CODE_SUBAGENT_MODEL_FORCE

if [ -z "$TAG" ]; then
  if [ "$MODE" = scorer ]; then TAG="scorer-$TOPOLOGY-${MODEL:-default}"; else TAG="context-$ARM"; fi
fi
mkdir -p "$OUT/$TAG"

claude_call() {  # claude_call PROMPT TOOLS...  -> JSON on stdout
  local prompt="$1"; shift
  claude -p "$prompt" --plugin-dir "$ROOT" --output-format json \
    --max-budget-usd "$BUDGET" --allowedTools "$@"
}

if [ "$MODE" = scorer ]; then
  LOCKED="$FIXTURE/locked-context.md"
  REPORTS=("$FIXTURE"/reports/*.md)
  EXTRA=""
  [ -n "$MODEL" ] && EXTRA=" --model $MODEL"
  for k in $(seq 1 "$RUNS"); do
    dir="$OUT/$TAG/run-$k"
    mkdir -p "$dir"
    if [ "$TOPOLOGY" = independent ]; then
      for report in "${REPORTS[@]}"; do
        slug="$(basename "$report" .md)"
        claude_call "/build-vs-buy:scorer $LOCKED$EXTRA $report" Skill Agent Read Grep Glob \
          > "$dir/$slug.out.json" || echo "run-$k $slug: claude exited non-zero" >&2
      done
    else
      ORDER=()
      while IFS= read -r line; do ORDER+=("$line"); done < <(
        python3 -c 'import random,sys; r=random.Random(int(sys.argv[1])); a=sys.argv[2:]; r.shuffle(a); print("\n".join(a))' \
          "$k" "${REPORTS[@]}")
      printf '%s\n' "${ORDER[@]}" > "$dir/order.txt"
      claude_call "/build-vs-buy:scorer $LOCKED$EXTRA ${ORDER[*]}" Skill Agent Read Grep Glob \
        > "$dir/all.out.json" || echo "run-$k: claude exited non-zero" >&2
    fi
  done
else
  for k in $(seq 1 "$RUNS"); do
    dir="$OUT/$TAG/run-$k"
    mkdir -p "$dir"
    sandbox="$(mktemp -d)"
    if [ "$ARM" = with-docs ]; then cp "$FIXTURE/sandbox-with-docs/README.md" "$sandbox/README.md"; fi
    (cd "$sandbox" && claude_call "$(cat "$FIXTURE/context-prompt.md")" \
        Skill Agent Read Grep Glob Write "Bash(mkdir:*)" "Bash(date:*)") \
      > "$dir/session.out.json" || echo "run-$k: claude exited non-zero" >&2
    found="$(find "$sandbox/docs/analysis" -name locked-context.md 2>/dev/null | head -1 || true)"
    if [ -n "$found" ]; then cp "$found" "$dir/locked-context.md"; else echo "run-$k: no locked-context.md written" >&2; fi
    rm -rf "$sandbox"
  done
fi
echo "Done: $OUT/$TAG" >&2
