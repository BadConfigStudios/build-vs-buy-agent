# build-vs-buy-agent — design

Date: 2026-11-24. Status: design approved by owner, written spec pending owner review.

## Purpose

A Claude Code plugin that evaluates "build or adopt?" questions. It interviews the owner, researches candidates in parallel, scores them with the build-vs-buy matrix, lets the owner challenge scores, and writes the analysis as markdown (plus a generated HTML view). It produces analysis only. The owner makes the decision.

Public repo: `BadConfigStudios/build-vs-buy-agent`, MIT license.

## Decisions

| Topic | Decision |
|---|---|
| Form | Claude Code plugin: slash command + skill + read-only researcher subagent |
| Orchestration | Skill drives the main thread (owner dialogue, scoring, writing). One researcher subagent per candidate, parallel, sonnet. Subagents cannot hold a dialogue, so no monolithic agent |
| Output location | Current repo, `docs/analysis/bvb-<topic>-YYYYMMDD/` |
| Output meaning | Analysis that feeds a decision. Never a decision. `status: analysis` in frontmatter |
| Stack context | No dedicated stack file. Agent scans repo docs each run, owner confirms at checkpoint 1. No cache |
| HTML | Generated from the markdown for non-markdown readers (management, leadership). Single self-contained file |
| HTML renderer | Vendored pinned `marked.min.js` (MIT), inlined by a stdlib-only Python script. No network at view time |
| Math | Deterministic `scripts/score.py`. Agent decides factor scores, script computes gates, totals, ranking |

## Output layout

```
docs/analysis/bvb-<topic>-YYYYMMDD/
  final.md              # summary, for other agents to read
  candidates/
    <candidate>.md      # one per option, including "build"
  index.html            # generated view, tabs: Summary, Scores, one per candidate
```

If the directory already exists for that day, append `-2`, `-3`, and so on.

### final.md

- Frontmatter: topic, date, matrix version, `status: analysis`, environment, business stage, expected growth.
- Step 0 context: must-haves (now / deferred / nice-to-have) and the confirmed stack summary.
- Score table: one row per option; columns per factor final score, weighted total, percentage, gate result.
- Ranking and close-call flag (top two within about 10 points).
- Owner overrides from checkpoint 2, each shown with the agent's original score.
- Unverified items, revisit conditions, exit note per option.
- Tuning suggestions (proposed scale or weight changes, never applied).
- No "choose X" recommendation.

### candidates/<candidate>.md

Written so every score can be checked and refuted. Each candidate file contains a scoring table with one row per factor:

| Factor | Base | Modifiers | Final | Why (matrix condition met) | Evidence (source, retrieved date) | Status |
|---|---|---|---|---|---|---|

- **Base**: score from the matrix scale before modifiers.
- **Modifiers**: each applied modifier with its sign and reason (for example `scaling -1: outgrown at 10x`). Empty if none.
- **Final**: after modifiers and clamping. Security shows its pre-clamp value.
- **Why**: names the exact matrix condition that produced the base score and states the facts that satisfy it.
- **Evidence**: URL plus retrieval date. For the build option, the estimate and its basis.
- **Status**: `verified`, `unverified` (with what could not be checked), or `override` (shows original score, new score, owner reason).

The file also holds the gate results, weighted subtotal, and a short list of what the researcher could not verify.

## Flow

Command: `/build-vs-buy <topic>`, optional `--quick` for the matrix's quick version (five factors).

1. **Context interview.** One question at a time: must-haves (now, deferred, nice-to-have), environment, business stage, expected growth. Stop and ask if any is missing. Scan repo docs (CLAUDE.md, README, ARCHITECTURE.md, DEVELOPMENT.md, `docs/`, infra manifests) and draft a stack summary: what already runs, operating models followed, policy constraints. If the scan finds too little, ask the owner for a doc or path. Propose candidates, always including build. Hosted and self-hosted versions of one tool are separate candidates.
2. **Checkpoint 1.** Owner confirms context, stack summary and candidate list. They are then locked. Changing Step 0 afterward means a new run.
3. **Research.** One `bvb-researcher` subagent per candidate, in parallel. Read-only tools: WebSearch, WebFetch, Read, Grep, Glob. Returns release dates, pricing, features, docs, source URLs, and flags anything unverified. The build option is estimated by the main thread from the stack summary.
4. **Scoring.** Main thread scores each factor with evidence, writes the rationale per row, then runs `score.py`.
5. **Checkpoint 2.** Owner sees the score table, challenges or overrides scores. Overrides are recorded beside the original, never silent. Totals are recomputed by `score.py`.
6. **Write.** Create the directory, candidate files, `final.md`, then run `build_html.py`.

Standing rules:
- Never change a scale or weight. Propose changes under Tuning suggestions.
- Never edit locked Step 0 after candidates are seen.
- End at the analysis. No decision.

## Plugin layout

```
.claude-plugin/plugin.json, marketplace.json
commands/build-vs-buy.md
skills/build-vs-buy/
  SKILL.md                  # orchestration (flow above)
  matrix.md                 # generic matrix, versioned
  templates/final.md, candidate.md
agents/bvb-researcher.md
scripts/score.py            # stdlib only
scripts/build_html.py       # stdlib only
scripts/vendor/marked.min.js
tests/
README.md  CHANGELOG.md  LICENSE
docs/examples/              # the two worked examples, neutral names
```

## Matrix generalization

Source: owner's `build-vs-buy-matrix.md` v1.2. Scales and weights unchanged. Wording changes only, recorded as v1.3 with a dated tuning note:

- Hardcoded stack mentions (Argo CD, Kyverno, Cloudflare, "container focused") become references to the confirmed stack summary.
- Integration alignment modifier: "follows a model the stack summary says is already run".
- Integration automatic minus one: "breaks an existing policy or guardrail named in the stack summary".
- Worked examples move to `docs/examples/` with neutral names so no private project details are published. Owner reviews them before the first commit.

## score.py

Input: JSON of options with per-factor base score, modifiers, and Step 0 flags (environment, stage maturity). Output: JSON with final scores (clamped 1 to 5, Security unclamped for the veto check), gate results, weighted totals, percentage of 85, ranking, close-call flag. Weights are read from the matrix constants in one place.

## build_html.py

Reads `final.md` and `candidates/*.md`, writes `index.html`: one file, `marked.min.js` and the markdown embedded as data, tabs rendered client-side. Escapes `</script>` inside embedded markdown. Tabs: Summary, Scores, one per candidate. Print-friendly CSS.

## Errors

- Missing Step 0 item: stop and ask.
- Researcher cannot verify a fact: score marked `unverified`, listed in `final.md`.
- No stack docs found: ask owner for a pointer.
- Existing run directory for that day: suffix `-N`.

## Testing

- `score.py`: clamping, security veto at zero, close-call flag, and a reproduction of the matrix worked examples (Vault 55/85, rotation script 72/85).
- `build_html.py`: one tab per candidate, `</script>` escaping, empty candidates directory.
- Skill flow: manual verification by dry run on a real topic before first release.

## Out of scope (v1)

- Caching the stack summary.
- Automatic weight tuning.
- Making the decision or writing to a decisions log.
- Non-GitHub hosting or distribution beyond the plugin marketplace file.
