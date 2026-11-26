---
name: scorer
description: Run the scoring stage on its own. Scores the given researcher reports against a locked-context file and prints the score entries as one json block. Used by the drift harness and for re-scoring saved reports.
argument-hint: <locked-context.md> [--model <alias>] <report.md> [<report.md> ...]
disable-model-invocation: true
---

# Scorer stage

Run only the scoring stage. Arguments: $ARGUMENTS

1. The first argument is the locked-context file. The other arguments are report files, except `--model <alias>`, which may appear anywhere and is not a report.
2. The matrix is `<skill base dir>/../build-vs-buy/matrix.md`.
3. Dispatch exactly one `build-vs-buy:bvb-scorer` subagent. Its prompt names three things: the locked-context file, the matrix, and every report file. If `--model <alias>` was given, dispatch it with that `model`. Otherwise do not pass a model, so the agent's pinned default applies.
4. Print the subagent's reply exactly as returned, with nothing before or after it. Do not edit, summarize, score or comment.
