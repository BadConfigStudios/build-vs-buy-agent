# build-vs-buy-agent

A Claude Code plugin that helps you decide whether to build something or adopt an existing tool. It interviews you, researches each candidate in parallel, scores them with a transparent matrix, lets you challenge every score, and writes the analysis as markdown plus a single-file HTML view you can send to people who do not read markdown.

It produces analysis only. You make the decision.

## Install

```
/plugin marketplace add BadConfigStudios/build-vs-buy-agent
/plugin install build-vs-buy@build-vs-buy-agent
```

## Use

```
/build-vs-buy <topic>
/build-vs-buy <topic> --quick
```

`--quick` scores only five factors for small decisions.

The agent will:

1. Ask for your must-haves (now, deferred, nice-to-have), environment, business stage and expected growth.
2. Scan the repo docs for a stack summary and propose candidates (build is always one). You confirm both (checkpoint 1).
3. Research each candidate with a read-only subagent and score it.
4. Show you the scores and evidence. You challenge or override any score (checkpoint 2).
5. Write the results.

### Run one stage

The stages can run on their own, on files. This is how the drift harness in `tools/drift/` works.

```
/build-vs-buy:researcher <locked-context.md> <candidate name and type>
/build-vs-buy:scorer <locked-context.md> <report.md> [<report.md> ...]
```

Add `--model <alias>` to override a stage's pinned model for one run. `locked-context.md` is written into the run directory at checkpoint 1.

## Output

```
docs/analysis/bvb-<topic>-YYYYMMDD/
  final.md              summary for people and other agents
  candidates/<name>.md  one file per option: every score with its reason and evidence
  index.html            single-file tabbed view, no network needed
```

Each candidate file has a table with Base, Modifiers, Final, Why, Evidence and Status for every factor, so any score can be checked and refuted. Overrides are recorded next to the original score.

## The matrix

See [skills/build-vs-buy/matrix.md](skills/build-vs-buy/matrix.md) and the worked examples in [docs/examples/](docs/examples/). Scales and weights are fixed; the agent proposes changes in a tuning section and never applies them.

## Development

Python 3 standard library only.

```
python3 -m unittest discover -s tests -v
```

## License

MIT
