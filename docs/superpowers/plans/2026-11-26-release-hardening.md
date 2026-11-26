# 0.2.0 Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the deferred findings in #44, #46, #48, #50 and #52, plus the refactor-pass cleanups, before the 0.2.0 feature freeze.

**Architecture:** One PR per issue. Agent and skill changes are text contracts guarded by `unittest` text tests; drift tools get behaviour tests (the harness against the fake `claude` test double).

**Tech Stack:** Markdown agents and skills, Python 3 standard library, Bash.

## Global Constraints

- Python 3 standard library only. No new dependencies.
- Tests: `python3 -m unittest discover -s tests`. Each test fails before its change.
- Never change a matrix scale or weight. `matrix.md` stays at version 1.3.
- Frozen fixture reports in `tools/drift/fixtures/reports/` are not edited.
- `CHANGELOG.md` is not edited in work PRs; PR #55 is updated after A to E merge.
- A PR that changes what a user or caller sees bumps `version` in `.claude-plugin/plugin.json`: A `0.2.0-dev.4`, B `0.2.0-dev.5`, C `0.2.0-dev.6`. D and E do not.
- Stop at every PR boundary. No merge without the owner's approval at the time.
- Order: A, then B, then C. D and E are independent.
- After A to E: drift rerun (ask first, it spends tokens), CHANGELOG update in #55, then ask about the freeze.

---

### Task 1 (PR A, #44): harden bvb-scorer

**Files:** `agents/bvb-scorer.md`, `skills/build-vs-buy/SKILL.md` (consume the new fields), `.claude-plugin/plugin.json`, `tests/test_scorer_agent.py`, `tests/test_skill.py`.

**Interfaces (produces):**
- Every scorer option entry has `flags`: a list holding zero or more of `report_instructions_ignored` and `prerelease_missing`. Fixed strings only, so report text is never echoed. `score.py` ignores the key (it reads only `name`, `must_haves_met`, `prerelease`, `factors`).
- On a matrix version mismatch the scorer returns `{"error": "matrix_version_mismatch"}` and nothing else.

- [ ] **Step 1: failing tests.** In `tests/test_scorer_agent.py` add tests that assert:
  - the agent names both flag values and `flags`; the example entry has `"flags": []`; the example's top-level keys are exactly `options` and the entry keys exactly `name, must_haves_met, prerelease, flags, factors` (structural no-recommendation guard).
  - the build option's `prerelease` is always `none`; a missing or unlisted value becomes `unstable_beta`, is flagged, and marks `maintenance` unverified.
  - every modifier is listed by name under its factor key, and each matching term exists in `matrix.md` (drift guard).
  - the build option's `unused_baggage` base is 5, as in the matrix.
  - the example security factor has a `staleness` modifier.
  - the version-mismatch reply is documented.
  - the quick-mode key list in the agent equals `score.QUICK_FACTORS`, and each has a heading in `matrix.md`.
  - bases of the six example factors not yet guarded: fit 4, integration 3, maintenance 5, dependencies 4, lock_in 4, security 5.
  In `tests/test_skill.py` assert the skill handles both flags and the error reply.
- [ ] **Step 2:** run the tests; the new ones fail (guards over current values pass at once and are noted as guards).
- [ ] **Step 3:** edit the agent and the skill.
- [ ] **Step 4:** bump the version to `0.2.0-dev.4`; run all tests.
- [ ] **Step 5:** commit tests and implementation together.

---

### Task 2 (PR B, #46): harden the per-candidate scoring flow

**Files:** `skills/build-vs-buy/SKILL.md`, `tests/test_skill.py`, `.claude-plugin/plugin.json`.

**Open decision (ask before starting):** the approved choice "keep `locked-context.md` in scratch, copy it at Step 4" breaks the drift context arm. `tools/drift/context-prompt.md` stops at Checkpoint 1 and `run.sh` collects the file from the sandbox's `docs/analysis/`. Recommended instead: keep the current behaviour and document it. Alternative: move to scratch and redesign how the harness collects the file.

- [ ] **Step 1: failing tests** in `tests/test_skill.py`: the stray-directory behaviour is stated ("An abandoned run leaves this directory behind"); each scorer gets copies in `<scratch>/score/<candidate-slug>/`; the exit-2 re-dispatch passes only the candidate name, factor key and the fixed text `invalid entry`, never the `score.py` message; Step 4 item 1 says the directory already exists; equal slugs get `-2`, `-3` in candidate-list order; the data-not-instructions rule is its own bullet under `## Rules`; the locked-context template has the frontmatter keys `topic, date, matrix_version, mode, environment, business_stage, expected_growth, core_ness` and the headings `## Must-haves`, `## Stack summary`, `## Candidates`.
- [ ] **Step 2:** run, see failures (the template test is a guard and passes).
- [ ] **Step 3:** edit the skill. Say plainly that copies reduce exposure only: scorer tools have no path limit.
- [ ] **Step 4:** version `0.2.0-dev.5`; run all tests; commit.

---

### Task 3 (PR C, #48): harden the stage skills

**Files:** `skills/scorer/SKILL.md`, `skills/researcher/SKILL.md`, `agents/bvb-researcher.md`, `README.md`, `tests/test_stage_skills.py`, `.claude-plugin/plugin.json`.

- [ ] **Step 1: failing tests** in `tests/test_stage_skills.py`:
  - scorer: "The locked-context file and every report file must end in `.md`, and no path may start with `-`; otherwise stop and ask instead of dispatching."
  - researcher: the same rule for the locked-context path.
  - `agents/bvb-researcher.md` input section says it may receive the path of a locked-context file holding those items, and to read it.
  - README says `--model` may appear anywhere and paths must contain no spaces.
  - guards: stop-and-ask sentences, "File paths must contain no spaces", "model alias such as `sonnet`", and every `${CLAUDE_PLUGIN_ROOT}/...` path in `skills/` resolves to a real file.
- [ ] **Step 2:** run, see failures.
- [ ] **Step 3:** edit the files. Make the argument order in each `argument-hint` and body match.
- [ ] **Step 4:** version `0.2.0-dev.6`; run all tests; commit.

Accepted, no change (record on #48): the simple frontmatter parser in tests; strict validation skipped without the `claude` CLI; the 2026-11-24 spec and plan stay as history. The CHANGELOG entry is in #55. Any `.md` file the user can read is still accepted as a report.

---

### Task 4 (PR D, #50): analyzer follow-ups and cleanups

**Files:** `tools/drift/analyze.py`, `tests/test_drift_analyze.py`.

One test then one change for each:

- [ ] Ties: `summarize` returns `tie_runs`, the number of scored runs where two gate-passing options share a `weighted_total`; `render` prints `- runs with tied totals among passing options: T/S`.
- [ ] Cost per run: `summary["run_costs"]` is a list of `(name, cost)`; `render` prints `- cost per run: run-1 $0.100, run-2 $0.100`.
- [ ] Escaping: `clean(text)` drops characters whose `unicodedata.category` starts with `C` and replaces `|` with `\|`; applied at render time to option names, candidate names, context values and error lines.
- [ ] Size cap: `MAX_OUTPUT_BYTES = 1_000_000`; `load_run` records an error for a larger file without reading it.
- [ ] `sys.path.append` in place of `insert(0, ...)` (no new test).
- [ ] Candidate names: strip only a final ` (hosted)`, ` (self-hosted)` or ` (build)`.
- [ ] Frontmatter: split only on lines that are exactly `---`, so `---` inside a value survives.
- [ ] `mode` and `environment` from the locked file are lowercased and whitespace-collapsed before use.
- [ ] Remove the duplicate `runs scored s/n` line; the test that asserts it asserts `runs: 2, scored: 1`.
- [ ] `check_set_dirs` rejects the same resolved directory given twice (exit 2).
- [ ] Refactor with tests green: `extract_options` gets an explicit error path in place of the `matches[0]` fallback; `main` has one directory check and one usage-exit path.

---

### Task 5 (PR E, #52): harness follow-ups and cleanups

**Files:** `tools/drift/run.sh`, `tests/test_drift_run.py`.

- [ ] Timeout: new `--timeout SECONDS` (integer 1..3600, default 900). Run each call as `perl -e 'alarm shift @ARGV; exec @ARGV or die' "$TIMEOUT" claude ...`. Failing test first: the fake `claude` sleeps 5 seconds when `FAKE_SLEEP` is set; with `--timeout 1` the run exits 1 and leaves no result file. Add bad values to `test_bad_usage_exits_2`. A timed-out call's child processes may outlive it; say so in the usage text.
- [ ] Remove the stale Write-rule comment at sandbox creation.
- [ ] `SCORER_TOOLS=(Skill Agent Read Grep Glob)` used by both scorer calls.
- [ ] Usage text: to rerun into the same tag, delete `OUT/TAG` first (no `--force`).
- [ ] Path scoping, live probe (ask first, it spends tokens): in context mode try `Edit(//<sandbox>/**)` in place of `Write`. If a run writes `locked-context.md` and a write outside the sandbox is denied, keep it and replace `test_context_write_is_plain_and_sandbox_is_physical`. If not, leave the code, record the result on #52 and ask the owner before closing that item.

Accepted, no change (record on #52): both arms get the stack text; the denied compound `mkdir && cat` costs one turn; temp paths in frozen reports stay. Scorer mode and the without-docs arm ran live in the 0.2.0 baseline.
