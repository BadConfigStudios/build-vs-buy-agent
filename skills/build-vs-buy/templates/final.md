---
topic: <topic>
date: <YYYY-MM-DD>
matrix_version: 1.3
status: analysis
mode: <full | quick>
environment: <production | lower>
business_stage: <pre-revenue | break-even | strong-revenue>
expected_growth: <declared growth>
---

# Analysis: <topic>

This analysis organizes evidence to inform a decision; it does not make one. Like any analysis, it involves judgment and some speculation: research can be incomplete, some figures are estimates, and scores can differ between runs. Treat it as one data point, and check the evidence and unverified items before relying on it.

## Context

- Must-haves now: <list>
- Deferred must-haves: <list or none>
- Nice-to-haves: <list or none>
- Core-ness: <is this what makes the product distinctive? lean build or adopt>

## Stack summary

<what already runs, operating models in use, policies or guardrails; confirmed by the owner on <date>>

## Scores

Use the table that matches the frontmatter `mode` and delete the other.

mode: full (10 factors, max 85)

| Option | Fit | Baggage | Install | Integration | Maintenance | Dependencies | Lock-in | Cost | Time to value | Security | Total | % | Gates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <name> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <N>/<max> | <pct> | <pass or failed gate> |

mode: quick (5 factors, max 60)

| Option | Fit | Maintenance | Dependencies | Time to value | Security | Total | % | Gates |
|---|---|---|---|---|---|---|---|---|
| <name> | <n> | <n> | <n> | <n> | <n> | <N>/60 | <pct> | <pass or failed gate> |

Per-option evidence and reasoning: see `candidates/<name>.md`.

## Ranking

- <1. name, pct, band> (options that failed a gate are listed as out, with the gate)
- Close call: <yes or no>. Top-two gap: <points or n/a>. If yes, this is a judgment call; prefer the simplest option behind an interface the owner controls.
- Tied totals are listed in name order and do not indicate a preference.

## Owner overrides

- <option, factor: original -> new, reason, or "none">

## Could not verify

- <unverified items across all options, or "none">

## Revisit conditions

- <what would make the owner re-run this>

## Exit notes

- <option: how to switch away>

## Tuning suggestions

- <proposed matrix scale or weight changes with reason, never applied; or "none">
