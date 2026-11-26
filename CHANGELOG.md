# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0] - Unreleased

### Added
- Read-only `bvb-scorer` agent (pinned to sonnet) that scores a researcher report against the matrix and returns the `score.py` input entry, with a reason, evidence and status for every factor.
- Stage skills `/build-vs-buy:researcher` and `/build-vs-buy:scorer` to run one stage on saved files, each with an optional `--model` override for that stage's agent.
- `locked-context.md`, written into the run directory when checkpoint 1 is confirmed and read by the scorers.
- Drift harness in `tools/drift/`: `run.sh` (spends tokens; not for CI), a frozen fixture, and `analyze.py`, a deterministic report on score, ranking and checkpoint-1 context variation with no pass/fail threshold.
- First drift baseline: `docs/drift/2026-11-26-baseline.md`.
- Tests for the scorer agent, stage skills, drift tools and fixture, plus strict plugin validation (skipped when the `claude` CLI is not installed).

### Changed
- The orchestrator no longer scores. It dispatches one scorer per candidate, build included, and each scorer is given only that candidate's report. It writes the build report itself, without scores.
- The `build-vs-buy` skill is now the entry point, and its orchestrator is pinned to sonnet.
- Scripts are located through `${CLAUDE_PLUGIN_ROOT}`.

### Removed
- `commands/build-vs-buy.md`, replaced by the skill as entry point.

### Fixed
- The skill no longer offers to reuse research from an earlier run. Research is always fresh, and the stack scan skips earlier analysis directories.

## [0.1.0] - 2026-11-25

First release. A feature freeze was declared at 0.1.0-rc.1; the manual dry-run found no defects, so no further release candidate was needed.

### Added
- Plugin manifests and marketplace entry.
- `score.py`: deterministic matrix scoring, gates, ranking and close-call flag. Input is validated: option names must be non-blank strings and unique (compared after trimming), and odd-typed `environment` or `prerelease` values are rejected.
- `build_html.py`: single-file tabbed HTML view with vendored marked 12.0.2. Remote images render as plain links (the page stays offline and its CSP unchanged), headings inside fenced code are ignored, and CRLF frontmatter and quoted `topic:` values are handled.
- Generic matrix v1.3 and two worked examples.
- Final and candidate templates, including a quick-mode Scores table (5 factors, out of 60) beside the full table (out of 85); read-only `bvb-researcher` agent that returns prerelease status as `none`, `stable_beta`, `unstable_beta` or `alpha`, with an explicit prompt-injection rule.
- `/build-vs-buy` command and skill.
- Tests: unit, template, matrix-weight, skill and an integration test chaining `score.py`, the templates and `build_html.py`.
