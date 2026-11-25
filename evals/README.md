# Evals

Run with `claude plugin eval . --allow-tools Write Bash WebSearch WebFetch Agent` from the repo root (full run spends tokens and uses the network). Add `--case stops-at-checkpoint-1` for the cheap case.

The cases run in an empty sandbox, so each prompt carries the stack summary and every Step 0 answer inline. `pre-answered-full-run` needs `--allow-tools Bash ...`; the eval refuses Bash-granting runs while `~/.docker` contains a symlink.
