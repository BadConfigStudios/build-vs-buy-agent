# Evals

Run with `claude plugin eval . --allow-tools Write Bash WebSearch WebFetch Agent` from the repo root (full run spends tokens and uses the network). Add `--case stops-at-checkpoint-1` for the cheap case.

The cases run in an empty sandbox, so each prompt carries the stack summary and every Step 0 answer inline. `pre-answered-full-run` needs Bash (included in the command above).

## Tool gating (checked against `claude plugin eval --help`, 2.1.283; no eval was run)

`--allow-tools` is documented as the "operator grant for gated tools (Bash, Write, Edit, WebFetch, mcp__*)". The help text does not list `Agent`, `WebSearch`, `Skill`, `Read`, `Glob` or `Grep` as gated, so they appear to be governed only by each case's `allowed_tools`. Both cases already list `Agent` and `WebSearch` there. Not confirmed by a run: whether `Agent` needs an explicit grant (it is harmless to pass). A paid full run is the only way to settle it.
