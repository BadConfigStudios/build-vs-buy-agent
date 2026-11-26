# Drift test and stage split: design (0.2.0), with roadmap to 0.8.0

Status: draft for owner review. Date: 2026-11-26.

## Why

Two full runs of the same topic in the 0.1.0 dry-run differed in candidate set, some factor scores and the ranking format. The inputs were not identical (the owner corrected the stack in one run), so this is a signal, not a measurement. The goal of 0.2.0 is to measure run-to-run variation of the scoring step, and to give every stage its own model setting so variation can be compared per model.

Also fixed in 0.2.0: the 0.1.0 skill offered to reuse earlier research on a same-day rerun. The owner's ideas file records this as decided against (research is always fresh, no reuse and no flag). See issue #30.

## Pipeline and roles

| Role | Implementation | Model setting |
|---|---|---|
| orchestrator | the `build-vs-buy` skill in the main thread: interview, checkpoints, overrides, writing files | `model:` in skill frontmatter, if verified; otherwise the session model |
| researcher | `bvb-researcher` agent (exists), read-only, never scores | agent `model:` (sonnet today) |
| scorer | new `bvb-scorer` agent, read-only (`tools: Read, Grep, Glob`) | agent `model:` |
| writer | 0.3.0 | agent `model:` |

The orchestrator stays in the main thread because it talks to the owner. Subagents may nest (docs: up to three layers), so this is a choice, not a limit.

Scorer: input is the locked Step 0 block, `matrix.md` and the researcher reports; output is the `score.py` input JSON with a Why per factor. It carries the researcher's no-recommendation and prompt-injection rules. The orchestrator runs `score.py`, shows Checkpoint 2 and handles overrides (edit the JSON, rerun, record `original -> new`).

This departs from the ideas file, where each per-option sub-agent also scores. Centralised scoring gives one calibration across options. Flagged for owner confirmation.

## Entry points

Per current plugin guidance, new components are skills; `commands/` is the older format.

- `/build-vs-buy:build-vs-buy`: the full run (unchanged name; orchestrator is a role name only).
- `/build-vs-buy:researcher`, `/build-vs-buy:scorer`: standalone stages that take file paths, with `model:` pins and `context: fork` plus `agent:`. The writer follows in 0.3.0.
- The locked context is written to a file at Checkpoint 1 in one defined format, which the standalone stages read.
- The standalone scorer taking a reports directory is for tests and re-scoring. The production flow always dispatches fresh researchers.

Cleanup in the same task: the same-name command is expected to be shadowed by the skill (skill wins on a name clash). Verify, fold `argument-hint` into the skill, delete `commands/build-vs-buy.md`. Replace the relative script path with `${CLAUDE_PLUGIN_ROOT}/scripts/...`. Add `claude plugin validate --strict` to the checks.

Verify before relying on them (not documented): the namespaced `agent:` value for a plugin agent; `claude -p "/build-vs-buy:scorer ..."` with `--plugin-dir`; the shadowing above.

## Fixture

One live research run on the email-notifier case with the fictional stack, five candidates. The unscored researcher reports are frozen under `evals/drift/fixtures/` with their retrieval dates and a label saying they are a point-in-time snapshot. The case is a close call, which is where drift shows.

Two arms, one shared prompt file with identical scripted Step 0 answers:

- with-docs: the sandbox contains the stack README; the skill drafts the stack summary from it.
- no-docs: the sandbox is empty; the same prompt supplies the README text when the skill asks for a path.

## Harness

Report only. No pass/fail threshold; thresholds come later from data.

- First task is a spike: a custom `claude -p --plugin-dir` loop versus `claude plugin eval --runs N --keep-temp --ablation none`. Choose by whether each run's output files and cost can be kept. Eval by default also runs a no-plugin baseline arm, which roughly doubles cost.
- Options: `--arm`, `--runs N` (default 5), `--model`. Unset `CLAUDE_CODE_SUBAGENT_MODEL` and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, or the model comparison is silently wrong. Cap spend with `--max-budget-usd` / `--max-cost-usd`. Never run in CI.
- Deterministic analyzer, unit-tested on canned outputs: per-factor score range, rank agreement and ties, gate outcomes, close-call flag, section and ranking-format conformance, cost per run. For the arm comparison: must-haves, environment, stage and candidate set at Checkpoint 1.
- Baseline: run on sonnet and opus and report the numbers. Wording is out of scope.

## Testing

- Analyzer: unit tests with canned run outputs.
- `bvb-scorer`: template-style tests like the researcher's (read-only tools, no-recommendation text, enum bindings).
- Skill: Step 3 dispatches the scorer; the skill never offers research reuse.
- Plugin: `claude plugin validate --strict`.

## Out of scope for 0.2.0

Renderer, writer, validator (0.3.0); threshold gating; end-to-end live-research drift; executive summary (0.4.0).

## Roadmap

| Milestone | Issue | Piece |
|---|---|---|
| 0.2.0 | #30, #31, #32 | never offer reuse; scorer and stage skills; drift harness |
| 0.3.0 | #33 | redesign, deterministic renderer (ranking fix), writer, validator |
| 0.4.0 | #34 | executive summary, analysis only |
| 0.5.0 | #35 | no-revenue-expected stage |
| 0.6.0 | #36 | features vs integrations |
| 0.7.0 | #37 | tunable weights and config file |
| 0.8.0 | #38 | weight presets |

0.1.1 was dropped by the owner (not releasing publicly yet); the ranking fix is folded into 0.3.0. The drift baseline is taken on the 0.1.0 templates, so the ranking change in 0.3.0 appears as an intended difference.

0.3.0 renderer and validator: scripts produce frontmatter, Scores, Ranking, close-call and overrides from `score.py` output; the writer (model is a setting, chosen for token efficiency) writes only narrative sections; `verify_report.py` checks that every URL appears in the researcher reports, every number matches `score.py`, and no recommendation phrase appears.

0.4.0 guardrail: analysis only, never a verdict. The ideas file says the markdown is consumed by other agents and the HTML is shared with people.

## Open items

- Exact `model:` pin behaviour on skills (verify in the first task).
- Spike outcome: eval versus custom loop.
- Owner confirmation of centralised scoring.
