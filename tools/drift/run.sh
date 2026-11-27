#!/usr/bin/env bash
# Drift harness for the build-vs-buy plugin. It SPENDS TOKENS. Never run it in CI.
#
#   scorer mode:  frozen researcher reports -> /build-vs-buy:scorer, repeated --runs times
#   context mode: the full skill up to Checkpoint 1, in the with-docs or no-docs sandbox,
#                 repeated --runs times; collects each run's locked-context.md
#
# Output: OUT/TAG/run-K/... ; read it with analyze.py.
#
# Scope note: in context mode, file writes are limited to the throwaway sandbox by an
# Edit(//<physical sandbox path>/**) rule, which also covers the Write tool (checked live on
# macOS; a Write(//path/**) rule was denied). Read and Bash(mkdir:*) are NOT path-scoped.
# Calls are also bounded by --setting-sources project, the budget cap and the timeout.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: run.sh --out DIR [--mode scorer|context] [--runs N] [--model ALIAS]
               [--topology independent|centralized] [--arm with-docs|no-docs]
               [--budget USD] [--timeout SECONDS] [--tag NAME]
  --mode      scorer (default) or context
  --runs      repetitions, integer 1..30 (default 5)
  --model     scorer model alias passed to the scorer skill (default: the agent's pinned model)
  --topology  scorer mode only: one scorer per candidate (default) or one scorer for all,
              with the candidate order shuffled per run
  --arm       context mode only (default with-docs)
  --budget    --max-budget-usd cap for each claude call, 0 < USD <= 5.00 (default 1.50).
              A single call costs about 0.07-0.10 USD baseline before any work.
  --timeout   wall-clock limit for each claude call, integer 1..3600 seconds (default 900).
              A timed-out call counts as failed; its child processes may outlive it.
  --tag       output subdirectory name, [A-Za-z0-9._-]+ (default derived from the options)
A non-empty OUT/TAG is refused: to rerun into the same tag, delete OUT/TAG first.
File writes are limited to the sandbox in context mode; Read and mkdir are not path-scoped.
Exit codes: 0 ok, 1 one or more claude calls failed, 2 bad usage.
EOF
  exit 2
}
die() { echo "run.sh: $*" >&2; usage; }

MODE=scorer RUNS=5 MODEL="" TOPOLOGY=independent ARM=with-docs BUDGET=1.50 TIMEOUT=900 TAG="" OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode|--runs|--model|--topology|--arm|--budget|--timeout|--tag|--out)
      [ $# -ge 2 ] && [ -n "$2" ] || die "missing value for $1"
      case "$1" in
        --mode) MODE="$2" ;; --runs) RUNS="$2" ;; --model) MODEL="$2" ;;
        --topology) TOPOLOGY="$2" ;; --arm) ARM="$2" ;; --budget) BUDGET="$2" ;;
        --tag) TAG="$2" ;; --out) OUT="$2" ;; --timeout) TIMEOUT="$2" ;;
      esac
      shift 2 ;;
    *) die "unknown option: $1" ;;
  esac
done
[ -n "$OUT" ] || die "--out is required"
case "$MODE" in scorer|context) ;; *) die "bad --mode" ;; esac
case "$TOPOLOGY" in independent|centralized) ;; *) die "bad --topology" ;; esac
case "$ARM" in with-docs|no-docs) ;; *) die "bad --arm" ;; esac
{ [[ "$RUNS" =~ ^[0-9]{1,3}$ ]] && [ "$((10#$RUNS))" -ge 1 ] && [ "$((10#$RUNS))" -le 30 ]; } \
  || die "--runs must be an integer 1..30"
RUNS=$((10#$RUNS))
{ [[ "$BUDGET" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v b="$BUDGET" 'BEGIN{exit !(b>0 && b<=5)}'; } \
  || die "--budget must be a number > 0 and <= 5.00"
{ [[ "$TIMEOUT" =~ ^[0-9]{1,4}$ ]] && [ "$((10#$TIMEOUT))" -ge 1 ] && [ "$((10#$TIMEOUT))" -le 3600 ]; } \
  || die "--timeout must be an integer 1..3600"
TIMEOUT=$((10#$TIMEOUT))
[ -z "$TAG" ] || { [[ "$TAG" =~ ^[A-Za-z0-9._-]+$ ]] && [ "$TAG" != "." ] && [ "$TAG" != ".." ]; } \
  || die "bad --tag"
[ -z "$MODEL" ] || [[ "$MODEL" =~ ^[A-Za-z0-9._-]+$ ]] || die "bad --model"

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
case "$ROOT" in *[[:space:]]*) die "the repo path must not contain whitespace: $ROOT" ;; esac
FIXTURE="$HERE/fixtures"

REPORTS=("$FIXTURE"/reports/*.md)
[ -f "${REPORTS[0]}" ] || { echo "run.sh: no reports found in $FIXTURE/reports" >&2; exit 2; }

# A leftover override would silently change which model runs, so remove both.
unset CLAUDE_CODE_SUBAGENT_MODEL CLAUDE_CODE_SUBAGENT_MODEL_FORCE ANTHROPIC_MODEL \
  ANTHROPIC_DEFAULT_SONNET_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL

if [ -z "$TAG" ]; then
  if [ "$MODE" = scorer ]; then TAG="scorer-$TOPOLOGY-${MODEL:-default}"; else TAG="context-$ARM"; fi
fi

if [ "$MODE" = scorer ] && [ "$TOPOLOGY" = independent ]; then CALLS=${#REPORTS[@]}; else CALLS=1; fi
awk -v r="$RUNS" -v c="$CALLS" -v b="$BUDGET" 'BEGIN{printf "run.sh: up to %d calls, estimated max spend %.2f USD\n", r*c, r*c*b}' >&2

if [ -d "$OUT/$TAG" ] && [ -n "$(ls -A "$OUT/$TAG")" ]; then
  die "$OUT/$TAG already exists and is not empty; pick another --tag or --out"
fi
mkdir -p "$OUT/$TAG"

SANDBOX=""
trap 'rm -rf "${SANDBOX:-}"' EXIT
trap 'exit 130' INT TERM

FAILS=()
SCORER_TOOLS=(Skill Agent Read Grep Glob)

# call_to OUTFILE PROMPT TOOLS...  (cwd for claude: $CALL_DIR, default the repo root)
# Output goes to OUTFILE.tmp and is renamed only on success, so a failed or
# budget-capped call never leaves a file the analyzer would read as a result.
call_to() {
  local outfile="$1" prompt="$2"; shift 2
  # perl's alarm survives exec, so the signal ends claude itself (macOS has no timeout(1)).
  if (cd "${CALL_DIR:-$ROOT}" && perl -e 'alarm shift @ARGV; exec @ARGV or die' "$TIMEOUT" claude -p "$prompt" --plugin-dir "$ROOT" --output-format json \
        --setting-sources project --strict-mcp-config \
        --max-budget-usd "$BUDGET" --allowedTools "$@") > "$outfile.tmp"; then
    mv "$outfile.tmp" "$outfile"
  else
    rm -f "$outfile.tmp"
    FAILS+=("$outfile")
    echo "run.sh: claude failed for $outfile" >&2
  fi
}

if [ "$MODE" = scorer ]; then
  LOCKED="$FIXTURE/locked-context.md"
  EXTRA=""
  [ -z "$MODEL" ] || EXTRA=" --model $MODEL"
  for ((k=1; k<=RUNS; k++)); do
    dir="$OUT/$TAG/run-$k"
    mkdir -p "$dir"
    if [ "$TOPOLOGY" = independent ]; then
      for report in "${REPORTS[@]}"; do
        slug="$(basename "$report" .md)"
        call_to "$dir/$slug.out.json" "/build-vs-buy:scorer $LOCKED$EXTRA $report" "${SCORER_TOOLS[@]}"
      done
    else
      ORDER=()
      while IFS= read -r line; do ORDER+=("$line"); done < <(
        python3 -c 'import random,sys; r=random.Random(int(sys.argv[1])); a=sys.argv[2:]; r.shuffle(a); print("\n".join(a))' \
          "$k" "${REPORTS[@]}")
      printf '%s\n' "${ORDER[@]}" > "$dir/order.txt"
      call_to "$dir/all.out.json" "/build-vs-buy:scorer $LOCKED$EXTRA ${ORDER[*]}" "${SCORER_TOOLS[@]}"
    fi
  done
else
  for ((k=1; k<=RUNS; k++)); do
    dir="$OUT/$TAG/run-$k"
    mkdir -p "$dir"
    SANDBOX="$(cd "$(mktemp -d)" && pwd -P)"
    if [ "$ARM" = with-docs ]; then cp "$FIXTURE/sandbox-with-docs/README.md" "$SANDBOX/README.md"; fi
    CALL_DIR="$SANDBOX" call_to "$dir/session.out.json" "$(cat "$FIXTURE/context-prompt.md")" \
      Skill Agent Read Grep Glob "Edit(/$SANDBOX/**)" "Bash(mkdir:*)" "Bash(date:*)"
    found=()
    while IFS= read -r line; do [ -z "$line" ] || found+=("$line"); done < <(
      find "$SANDBOX/docs/analysis" -name locked-context.md 2>/dev/null || true)
    if [ "${#found[@]}" -gt 1 ]; then
      echo "run.sh: run-$k: more than one locked-context.md in the sandbox" >&2
      FAILS+=("$dir/locked-context.md (more than one)")
    elif [ "${#found[@]}" -eq 1 ]; then
      cp "${found[0]}" "$dir/locked-context.md"
    else
      echo "run.sh: run-$k: no locked-context.md written" >&2
      FAILS+=("$dir/locked-context.md (missing)")
    fi
    rm -rf "$SANDBOX"; SANDBOX=""
  done
fi

if [ "${#FAILS[@]}" -gt 0 ]; then
  echo "run.sh: ${#FAILS[@]} claude call(s) failed:" >&2
  printf '  %s\n' "${FAILS[@]}" >&2
  exit 1
fi
echo "Done: $OUT/$TAG" >&2
