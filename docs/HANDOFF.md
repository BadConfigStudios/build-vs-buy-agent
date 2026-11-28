# Handoff — 0.2.0-rc.2 (release of MVP 2)

**Read `~/.claude/CLAUDE.md` in full before anything else.**

## Just merged
PR #71: create the run directory with plain separate commands (fixes #65, version `0.2.0-rc.2`) — https://github.com/BadConfigStudios/build-vs-buy-agent/pull/71
PR #55: 0.2.0 changelog and drift rerun — https://github.com/BadConfigStudios/build-vs-buy-agent/pull/55

## Current milestone
MVP 2 — 0.2.0 — https://github.com/BadConfigStudios/build-vs-buy-agent/milestone/2

## Next task
Issue #54: docs: 0.2.0 release notes and refactor pass — https://github.com/BadConfigStudios/build-vs-buy-agent/issues/54

`0.2.0-rc.2` is not tagged, and the CHANGELOG entry for 0.2.0 still says "Unreleased". #54 stays open until the release is done. Its comments do not record whether the refactor pass was done, so check that first.

## Carry-over context

### Owner rules
- Feature freeze declared 2026-11-27 (#54): only fixes merge, and each fix moves to the next `rc.N`.
- Tags only with owner approval, including any `rc` tag.
- Ask before spending tokens.
- Never merge without owner approval at the time. Stop at every PR boundary.

### State
- `main` is at `754789f`; 259 tests pass.
- #56 is closed.
- #66 is a known limit listed in the CHANGELOG. The issue is still open on the milestone. Closing it was suggested and is not approved.
- The branch `docs/release-0.2.0-changelog` (local and remote) is not deleted yet.
- #67 (show tied totals as ties) is on MVP 4.

### Live checks for #71 (Claude Code 2.1.332, sonnet session)
- 6 context runs: no denials, all wrote `locked-context.md` and used the four separate commands (1.00 USD).
- 1 existing-directory run: created `-2` and left the marker file unchanged (0.25 USD). It used a one-off script that also redirected stdin.
- `/code-review low` returned only "(none)".
- Outputs are in `drift-runs/0.2.0-rc.2/` (ignored by git, local only).

### Still open or untested
- The tie rule's effect on ranking agreement figures is not measured.
- `run.sh` does not redirect stdin.
- Not tested: the retry after a failed `mkdir`; extra permission prompts in normal use.
- Not tested live:
  - a skill run with the new report wording
  - retries, colliding slugs, abandoned runs, `report_instructions_ignored`, the build-only `unused_baggage` rule
  - the absolute run-directory path fix (#58) across a full run through `final.md`
  - the researcher read limit against a hostile file or page, and the scorer's leading-dash path rule (#59)
  - the post-review runner fixes (#61)

### Gotchas
- The Mac idle-sleeps on battery, which stalls live runs. `caffeinate -i` prevents it.
- A global hook blocks any command with `git push` followed later by `main` (for example, chained with `gh pr create --base main`). Run the push as its own command.
