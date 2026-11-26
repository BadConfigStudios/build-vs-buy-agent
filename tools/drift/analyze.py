#!/usr/bin/env python3
"""Drift report for the build-vs-buy scorer. Report only: no pass/fail threshold.

Usage:
  analyze.py scores --locked LOCKED.md RUN_SET_DIR [RUN_SET_DIR ...]
  analyze.py context RUN_SET_DIR [RUN_SET_DIR ...]

A run set is a directory of run-*/ subdirectories. In `scores` mode each run
directory holds *.out.json files (the JSON printed by `claude -p
--output-format json`). In `context` mode each run directory holds a
locked-context.md.
"""
import collections
import itertools
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import score  # noqa: E402

FENCE = re.compile(r"```json\s*\n(.+?)\n```", re.S)
CONTEXT_FIELDS = ("mode", "environment", "business_stage", "expected_growth", "core_ness")


def parse_locked_context(text):
    """Return {"meta": {key: value}, "candidates": [name, ...]} from a locked-context file."""
    parts = text.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        raise ValueError("locked-context file has no frontmatter")
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    candidates = []
    in_candidates = False
    for line in parts[2].splitlines():
        if line.startswith("## "):
            in_candidates = line.strip() == "## Candidates"
        elif in_candidates and line.startswith("- "):
            candidates.append(line[2:].split(" (")[0].strip())
    return {"meta": meta, "candidates": candidates}


def extract_options(result_text):
    matches = list(FENCE.finditer(result_text or ""))
    if not matches:
        raise ValueError("no json block in the scorer reply")
    data = None
    for match in reversed(matches):
        try:
            candidate = json.loads(match.group(1))
        except (ValueError, RecursionError):
            continue
        if isinstance(candidate, dict) and "options" in candidate:
            data = candidate
            break
    if data is None:
        try:
            data = json.loads(matches[0].group(1))
        except RecursionError as exc:
            raise ValueError("json block is nested too deeply") from exc
    options = data.get("options") if isinstance(data, dict) else None
    if not isinstance(options, list) or not options:
        raise ValueError("scorer reply has no options list")
    return options


def load_run(run_dir):
    options, cost, errors = [], 0.0, []
    files = sorted(pathlib.Path(run_dir).glob("*.out.json"))
    if not files:
        errors.append("no *.out.json files")
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("output is not a JSON object")
            file_cost = float(payload.get("total_cost_usd") or 0)
            if math.isfinite(file_cost):
                cost += file_cost
            else:
                errors.append(f"{path.name}: total_cost_usd is not a finite number")
            options.extend(extract_options(payload.get("result", "")))
        except (ValueError, TypeError, OSError, RecursionError) as exc:
            errors.append(f"{path.name}: {exc}")
    return {"name": pathlib.Path(run_dir).name, "options": options, "cost": cost,
            "errors": errors}


def _pairwise_agreement(rankings):
    names = sorted({n for r in rankings for n in r})
    shares = []
    for a, b in itertools.combinations(names, 2):
        votes = [r.index(a) < r.index(b) for r in rankings if a in r and b in r]
        if votes:
            shares.append(max(votes.count(True), votes.count(False)) / len(votes))
    return sum(shares) / len(shares) if shares else None


def summarize(runs, mode, environment):
    errors, scored = [], []
    for i, run in enumerate(runs, 1):
        label = run.get("name", f"run-{i}")
        errors += [f"{label}: {e}" for e in run["errors"]]
        if run["errors"] or not run["options"]:
            continue
        try:
            scored.append(score.evaluate({"mode": mode, "environment": environment,
                                          "options": run["options"]}))
        except ValueError as exc:
            errors.append(f"{label}: score.py rejected the scorer output: {exc}")
    names = sorted({o["name"] for r in scored for o in r["options"]})
    factors, totals, gates = {}, {}, {}
    for name in names:
        present = [o for r in scored for o in r["options"] if o["name"] == name]
        totals[name] = [o["weighted_total"] for o in present]
        factors[name] = {f: [o["factors"][f]["final"] for o in present]
                         for f in present[0]["factors"]}
        gates[name] = {g: sorted({o["gates"][g] for o in present}) for g in present[0]["gates"]}
    rankings = [tuple(r["ranking"]) for r in scored]
    counts = collections.Counter(rankings)
    modal = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0] if counts else ((), 0)
    return {
        "runs_total": len(runs),
        "runs_scored": len(scored),
        "errors": errors,
        "names": names,
        "factors": factors,
        "totals": totals,
        "gates": gates,
        "modal_ranking": list(modal[0]),
        "modal_share": modal[1],
        "pairwise_agreement": _pairwise_agreement(rankings),
        "close_call_runs": sum(1 for r in scored if r["close_call"]),
        "max_total": scored[0]["max_total"] if scored else None,
        "cost_total": sum(r["cost"] for r in runs),
    }


def _range(values):
    return (min(values), max(values))


def varying_factors(summary):
    out = {}
    for name, per_factor in summary["factors"].items():
        varied = {f: _range(v) for f, v in per_factor.items() if len(set(v)) > 1}
        if varied:
            out[name] = varied
    return out


def mean_total_range(summary):
    ranges = [max(v) - min(v) for v in summary["totals"].values() if v]
    return sum(ranges) / len(ranges) if ranges else None


def render(label, summary):
    n, s = summary["runs_total"], summary["runs_scored"]
    lines = [f"## {label}", "",
             f"- runs: {n}, scored: {s}, cost: ${summary['cost_total']:.3f}",
             f"- runs scored {s}/{n}"]
    if s:
        pair = summary["pairwise_agreement"]
        lines += [
            f"- same ranking as the most common one: {summary['modal_share']}/{s}",
            f"- pairwise order agreement: {'n/a' if pair is None else f'{pair:.0%}'}",
            f"- most common ranking: {' > '.join(summary['modal_ranking']) or 'none'}",
            f"- close call flagged in {summary['close_call_runs']}/{s} runs",
            "", "| Option | Total min | Total max | Spread |", "|---|---|---|---|",
        ]
        for name in summary["names"]:
            lo, hi = _range(summary["totals"][name])
            lines.append(f"| {name} | {lo}/{summary['max_total']} | {hi}/{summary['max_total']} | {hi - lo} |")
        varied = varying_factors(summary)
        lines += ["", "Factors whose final score varied (min to max):"]
        lines += [f"- {name}: " + ", ".join(f"{f} {lo}-{hi}" for f, (lo, hi) in v.items())
                  for name, v in varied.items()] or ["- none"]
        gate_diff = [f"{name}: {g} {outs}" for name, gs in summary["gates"].items()
                     for g, outs in gs.items() if len(outs) > 1]
        lines += ["", "Gates whose outcome varied:"] + ([f"- {g}" for g in gate_diff] or ["- none"])
    if summary["errors"]:
        lines += ["", "Errors:"] + [f"- {e}" for e in summary["errors"]]
    return "\n".join(lines) + "\n"


def render_comparison(summaries):
    lines = ["## Comparison", "",
             "| Run set | Scored | Same ranking | Pairwise agreement | Mean total spread | Varying factor cells | Cost |",
             "|---|---|---|---|---|---|---|"]
    for label, s in summaries.items():
        pair = s["pairwise_agreement"]
        spread = mean_total_range(s)
        cells = sum(len(v) for v in varying_factors(s).values())
        lines.append(
            f"| {label} | {s['runs_scored']}/{s['runs_total']} "
            f"| {s['modal_share']}/{s['runs_scored']} "
            f"| {'n/a' if pair is None else f'{pair:.0%}'} "
            f"| {'n/a' if spread is None else f'{spread:.1f}'} "
            f"| {cells} | ${s['cost_total']:.3f} |")
    return "\n".join(lines) + "\n"


def run_dirs(set_dir):
    def key(p):
        m = re.search(r"(\d+)$", p.name)
        return (0, int(m.group(1)), p.name) if m else (1, 0, p.name)
    return sorted((p for p in pathlib.Path(set_dir).glob("run-*") if p.is_dir()), key=key)


def set_labels(set_dirs):
    names = [pathlib.Path(d).resolve().name for d in set_dirs]
    return [str(pathlib.Path(d).resolve()) if not n or names.count(n) > 1 else n
            for d, n in zip(set_dirs, names)]


def check_set_dirs(set_dirs):
    for d in set_dirs:
        if not pathlib.Path(d).is_dir():
            return f"analyze.py: {d} is not a directory"
        if not run_dirs(d):
            return f"analyze.py: {d} contains no run-* directories"
    return None


def summarize_context(set_dir):
    values = {f: set() for f in CONTEXT_FIELDS}
    candidate_sets, errors = set(), []
    dirs = run_dirs(set_dir)
    for d in dirs:
        path = d / "locked-context.md"
        try:
            parsed = parse_locked_context(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            errors.append(f"{d.name}: {exc}")
            continue
        for f in CONTEXT_FIELDS:
            values[f].add(" ".join(parsed["meta"].get(f, "missing").lower().split()))
        candidate_sets.add(tuple(sorted(c.lower() for c in parsed["candidates"])))
    return {"runs_total": len(dirs), "values": {f: sorted(v) for f, v in values.items()},
            "candidate_sets": sorted(candidate_sets), "errors": errors}


def render_context(summaries):
    lines = ["## Context at Checkpoint 1", ""]
    for label, s in summaries.items():
        lines.append(f"### {label} ({s['runs_total']} runs)")
        for f in CONTEXT_FIELDS:
            lines.append(f"- {f}: {' | '.join(s['values'][f]) or 'missing'}")
        lines.append(f"- distinct candidate sets: {len(s['candidate_sets'])}")
        for cs in s["candidate_sets"]:
            lines.append(f"  - {', '.join(cs)}")
        lines += [f"- error: {e}" for e in s["errors"]]
        lines.append("")
    labels = list(summaries)
    if len(labels) > 1:
        first = summaries[labels[0]]
        differ = [f for f in CONTEXT_FIELDS
                  if any(summaries[l]["values"][f] != first["values"][f] for l in labels[1:])]
        same_cands = all(summaries[l]["candidate_sets"] == first["candidate_sets"] for l in labels[1:])
        lines.append("Fields that differ between run sets: " + (", ".join(differ) or "none"))
        lines.append("Candidate sets identical between run sets: " + ("yes" if same_cands else "no"))
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) < 3 or argv[1] not in ("scores", "context"):
        print(__doc__, file=sys.stderr)
        return 2
    if argv[1] == "context":
        problem = check_set_dirs(argv[2:])
        if problem:
            print(problem, file=sys.stderr)
            return 2
        summaries = dict(zip(set_labels(argv[2:]), map(summarize_context, argv[2:])))
        sys.stdout.write(render_context(summaries))
        return 0
    if len(argv) < 5 or argv[2] != "--locked":
        print(__doc__, file=sys.stderr)
        return 2
    try:
        meta = parse_locked_context(pathlib.Path(argv[3]).read_text(encoding="utf-8"))["meta"]
        mode, environment = meta["mode"], meta["environment"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"analyze.py: cannot read mode and environment from the locked-context file: {exc}",
              file=sys.stderr)
        return 2
    problem = check_set_dirs(argv[4:])
    if problem:
        print(problem, file=sys.stderr)
        return 2
    summaries = {}
    for label, set_dir in zip(set_labels(argv[4:]), argv[4:]):
        runs = [load_run(d) for d in run_dirs(set_dir)]
        summaries[label] = summarize(runs, mode, environment)
    for label, s in summaries.items():
        sys.stdout.write(render(label, s) + "\n")
    if len(summaries) > 1:
        sys.stdout.write(render_comparison(summaries))
    failed = [l for l, s in summaries.items() if s["runs_scored"] == 0]
    if failed:
        print("analyze.py: no run could be scored in: " + ", ".join(failed), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
