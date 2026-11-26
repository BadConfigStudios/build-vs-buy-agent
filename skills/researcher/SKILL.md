---
name: researcher
description: Run the research stage on its own for one candidate. Reads a locked-context file and prints the researcher report. Used to capture frozen reports for the drift harness and to refresh one candidate.
argument-hint: <locked-context.md> [--model <alias>] <candidate name and type>
disable-model-invocation: true
---

# Researcher stage

Run only the research stage for one candidate. Arguments: $ARGUMENTS

1. The first argument is the locked-context file. Everything after it, except `--model <alias>`, is the candidate name and type, for example `Amazon SES (hosted)`.
2. Dispatch exactly one `build-vs-buy:bvb-researcher` subagent. Its prompt gives the candidate name and type and the path of the locked-context file, and tells it to read that file for the must-haves, environment, stage, growth and stack summary, and to use the file's `date:` value as today's date. If `--model <alias>` was given, dispatch it with that `model`. Otherwise do not pass a model, so the agent's pinned default applies.
3. Print the subagent's reply exactly as returned, with nothing before or after it. Do not edit, summarize, score or comment.
