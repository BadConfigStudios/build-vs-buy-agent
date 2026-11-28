# Handoff — 0.2.0-rc.3 (release of MVP 2)

**Read `~/.claude/CLAUDE.md` in full before anything else.**

## Just merged
PR #74: the researcher agent says a separate scorer agent scores (closes #73, version `0.2.0-rc.3`) — https://github.com/BadConfigStudios/build-vs-buy-agent/pull/74

## Current milestone
MVP 2 — 0.2.0 — https://github.com/BadConfigStudios/build-vs-buy-agent/milestone/2

## Next task
Issue #54: docs: 0.2.0 release notes and refactor pass — https://github.com/BadConfigStudios/build-vs-buy-agent/issues/54

The release still needs the CHANGELOG date for 0.2.0 (it says "Unreleased"), the owner's approval to tag, and then closing #54 and the milestone. `0.2.0-rc.3` is not tagged.

## Carry-over context

### Owner rules
- Feature freeze declared 2026-11-27 (#54): only fixes merge, and each fix moves to the next `rc.N`.
- Tags only with owner approval, including any `rc` tag.
- Ask before spending tokens.
- Never merge without owner approval at the time. Stop at every PR boundary.

### State
- At `ee50a05` (the #74 merge), 259 tests passed.
- #66 is a known limit listed in the CHANGELOG. The issue is still open on the milestone.

### Refactor pass for #54 (done, not yet recorded on the issue)
- PR #55 covered the `analyze.py` and `run.sh` cleanup items through #60 and #61.
- A later pass read `analyze.py`, `run.sh`, the three skills, both agents and the locked-context template.
- Tests were only searched for repeated definitions and unused names. The `build_html.py` changes were not reviewed.
- The one wording bug it found was fixed in #74. Minor duplication was left as is.

### Not decided
- Whether to create an issue for the missing stdin redirect in `tools/drift/run.sh`, and on which milestone.
- Whether to post the refactor-pass comment on #54.
- Whether to close #66.

### Live checks
- `0.2.0-rc.3`: one researcher stage (Postmark, 0.45 USD) returned all 13 sections with no permission denials, and a keyword search found no scoring. The facts in the report were not checked.
- #71, on `0.2.0-rc.2` (Claude Code 2.1.332, sonnet session):
  - 6 context runs: no denials, all wrote `locked-context.md` and used the four separate commands (1.00 USD).
  - 1 existing-directory run: created `-2` and left the marker file unchanged (0.25 USD). It used a one-off script that also redirected stdin.
  - `/code-review low` returned only "(none)".
- Outputs are in `drift-runs/<version>/` (ignored by git, local only).

### Still open or untested
- The tie rule's effect on ranking agreement figures is not measured.
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
