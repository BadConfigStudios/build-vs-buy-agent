# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0] - 2026-11-28

### Added
- Read-only `bvb-scorer` agent (pinned to sonnet) that scores a researcher report against the matrix and returns the `score.py` input entry, with a reason, evidence and status for every factor.
- Stage skills `/build-vs-buy:researcher` and `/build-vs-buy:scorer` to run one stage on saved files, each with an optional `--model` override for that stage's agent.
- `locked-context.md`, written into the run directory when checkpoint 1 is confirmed and read by the scorers.
- Drift harness in `tools/drift/`: `run.sh` (spends tokens; not for CI), a frozen fixture, and `analyze.py`, a deterministic report on score, ranking and checkpoint-1 context variation with no pass/fail threshold.
- Drift reports: the first baseline (`docs/drift/2026-11-26-baseline.md`) and a rerun after the hardening changes (`docs/drift/2026-11-27-rerun.md`).
- Tests for the scorer agent, stage skills, drift tools and fixture, plus strict plugin validation (skipped when the `claude` CLI is not installed).

### Changed
- The orchestrator no longer scores. It dispatches one scorer per candidate, build included, and each scorer is given only that candidate's report. It writes the build report itself, without scores.
- The `build-vs-buy` skill is now the entry point. It sets `model: sonnet`, which does not hold for the whole run (see Known limitations).
- Scripts are located through `${CLAUDE_PLUGIN_ROOT}`.
- The README, the report and the HTML view say what the analysis is for: it informs a decision without making one, involves judgment and some speculation, and is one data point. The report says tied totals are listed in name order and do not indicate a preference.
- Each scorer is given copies of `locked-context.md` and its own report in a scratch directory. This limits what it is pointed at, not what its tools can read.
- Each scorer entry has a `flags` list for ignored report instructions and a missing prerelease status; the analysis lists them under "Could not verify" and shows them at checkpoint 2. A missing or unlisted prerelease status is scored as `unstable_beta`.
- The scorer checks the matrix version and the run stops on a mismatch.
- Scorer retries do not pass `score.py` messages or scorer replies into a prompt.
- Candidates with the same slug get numbered suffixes, and the skill says an abandoned run leaves its run directory behind.
- The researcher may be given a locked-context file, the only local file it is told to read.

### Removed
- `commands/build-vs-buy.md`, replaced by the skill as entry point.

### Fixed
- Checkpoint 1 asks for the run directory to be created with plain commands, one per call, with no shell loop, variables, `cd` or chaining. In the `0.2.0-dev.6` drift rerun, 12 commands that created it were denied (#65).
- The researcher agent's instructions no longer say that the orchestrator scores; they say a separate scorer agent does (#73).
- The skill no longer offers to reuse research from an earlier run. Research is always fresh, and the stack scan skips earlier analysis directories.

### Security
- Text-level hardening against instructions planted in reports and web pages: reports and scorer entries are treated as data, the scorer lists every allowed modifier and flag, and the stage skills stop and ask for file paths that do not end in `.md` or that start with `-`. These are instructions to the model, not an enforced sandbox.

### Known limitations
- The orchestrator does not stay on sonnet. In one checked run of the full skill, `model: sonnet` lasted until the researcher's task notification started a new turn, and the session then returned to the Opus model it had started on. Whether later owner replies do the same was not tested. The drift runner sets the session model itself.
- Rankings are not fully stable. In drift tests on one frozen case, the same three options stayed on top, but first place varied between runs and setups. Treat options in a close call as unranked. Tied totals are listed in name order.
- Some `/build-vs-buy:scorer` replies end with the Agent tool's `agentId` and usage text: 2 of 55 in the `0.2.0-dev.6` drift rerun and none of 55 in the baseline. The relaying session is told to print the reply exactly as returned and usually leaves this text off; why it kept it in those 2 is not known. The drift analyzer ignores it. The full skill builds its own scoring input, so the text is not expected in written results; its transcripts were not checked for this (#66).

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
