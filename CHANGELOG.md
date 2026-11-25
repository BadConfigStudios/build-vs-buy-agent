# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0-rc.1] - 2026-11-25

Feature freeze declared; only fixes merge until 0.1.0.

### Added
- Plugin manifests and marketplace entry.
- `score.py`: deterministic matrix scoring, gates, ranking and close-call flag. Input is validated: option names must be non-blank strings and unique (compared after trimming), and odd-typed `environment` or `prerelease` values are rejected.
- `build_html.py`: single-file tabbed HTML view with vendored marked 12.0.2. Remote images render as plain links (the page stays offline and its CSP unchanged), headings inside fenced code are ignored, and CRLF frontmatter and quoted `topic:` values are handled.
- Generic matrix v1.3 and two worked examples.
- Final and candidate templates, including a quick-mode Scores table (5 factors, out of 60) beside the full table (out of 85); read-only `bvb-researcher` agent that returns prerelease status as `none`, `stable_beta`, `unstable_beta` or `alpha`, with an explicit prompt-injection rule.
- `/build-vs-buy` command and skill.
- Tests: unit, template, matrix-weight, skill and an integration test chaining `score.py`, the templates and `build_html.py`.
