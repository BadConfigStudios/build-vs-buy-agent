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

This analysis does not make a decision. It reports scores and evidence so the owner can decide.

## Context

- Must-haves now: <list>
- Deferred must-haves: <list or none>
- Nice-to-haves: <list or none>
- Core-ness: <is this what makes the product distinctive? lean build or adopt>

## Stack summary

<what already runs, operating models in use, policies or guardrails; confirmed by the owner on <date>>

## Scores

| Option | Fit | Baggage | Install | Integration | Maintenance | Dependencies | Lock-in | Cost | Time to value | Security | Total | % | Gates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <name> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <n> | <N>/<max> | <pct> | <pass or failed gate> |

Per-option evidence and reasoning: see `candidates/<name>.md`.

## Ranking

- <1. name, pct, band> (options that failed a gate are listed as out, with the gate)
- Close call: <yes or no>. Top-two gap: <points or n/a>. If yes, this is a judgment call; prefer the simplest option behind an interface the owner controls.

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
