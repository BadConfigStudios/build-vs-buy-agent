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
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "scripts"))
import score  # noqa: E402

FENCE = re.compile(r"```json\s*\n(.+?)\n```", re.S)
CONTEXT_FIELDS = ("mode", "environment", "business_stage", "expected_growth", "core_ness")
# The type tag after a candidate name, with any description written inside or after it.
TYPE_TAG = re.compile(r" \((?:hosted|self-hosted|build|<[^>]*>)(?:[,:].*\)|\))(?::.*)?$", re.I)
MAX_OUTPUT_BYTES = 1_000_000


def _normalize(value):
    return " ".join(value.lower().split())


def clean(text):
    """Make model-written text safe for a terminal and a markdown table cell."""
    spaced = "".join(" " if c.isspace() else c for c in str(text))
    kept = "".join(c for c in spaced if not unicodedata.category(c).startswith("C"))
    return kept.replace("\\", "\\\\").replace("|", "\\|")


def parse_locked_context(text):
    """Return {"meta": {key: value}, "candidates": [name, ...]} from a locked-context file."""
    parts = re.split(r"^---[ \t]*$", text, maxsplit=2, flags=re.M)
    if len(parts) < 3 or parts[0].strip():
        raise ValueError("locked-context file has no frontmatter")
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    for key in ("mode", "environment"):
        if key in meta:
            meta[key] = _normalize(meta[key])
    candidates = []
    in_candidates = False
    for line in parts[2].splitlines():
        if line.startswith("## "):
            in_candidates = line.strip() == "## Candidates"
        elif in_candidates and line.startswith("- "):
            candidates.append(TYPE_TAG.sub("", line[2:].strip()).strip())
    return {"meta": meta, "candidates": candidates}


def extract_options(result_text):
    matches = list(FENCE.finditer(result_text or ""))
    if not matches:
        raise ValueError("no json block in the scorer reply")
    parsed, failure = [], None
    for match in matches:
        try:
            parsed.append(json.loads(match.group(1)))
        except RecursionError:
            failure = failure or "json block is nested too deeply"
        except ValueError as exc:
            failure = failure or str(exc)
    blocks = [d for d in parsed if isinstance(d, dict)]
    with_options = [d for d in blocks if "options" in d]
    chosen = with_options[-1:] or blocks
    for data in chosen:
        if "error" in data:
            raise ValueError(f"scorer returned an error: {str(data['error'])[:100]}")
    if not with_options and not parsed:
        raise ValueError(failure)
    options = with_options[-1]["options"] if with_options else None
    if not isinstance(options, list) or not options:
        detail = f" (a json block did not parse: {failure})" if failure and not with_options else ""
        raise ValueError("scorer reply has no options list" + detail)
    return options


def load_run(run_dir):
    options, cost, errors = [], 0.0, []
    files = sorted(pathlib.Path(run_dir).glob("*.out.json"))
    if not files:
        errors.append("no *.out.json files")
    for path in files:
        try:
            if path.stat().st_size > MAX_OUTPUT_BYTES:
                raise ValueError(f"larger than {MAX_OUTPUT_BYTES} bytes, not read")
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


def _has_tie(result):
    totals = [o["weighted_total"] for o in result["options"] if o["passed"]]
    return len(set(totals)) < len(totals)


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
        "tie_runs": sum(1 for r in scored if _has_tie(r)),
        "max_total": scored[0]["max_total"] if scored else None,
        "cost_total": sum(r["cost"] for r in runs),
        "run_costs": [(run.get("name", f"run-{i}"), run["cost"]) for i, run in enumerate(runs, 1)],
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
             "- cost per run: " + (", ".join(f"{clean(name)} ${cost:.3f}"
                                             for name, cost in summary["run_costs"]) or "none")]
    if s:
        pair = summary["pairwise_agreement"]
        lines += [
            f"- same ranking as the most common one: {summary['modal_share']}/{s}",
            f"- pairwise order agreement: {'n/a' if pair is None else f'{pair:.0%}'}",
            f"- most common ranking: {' > '.join(map(clean, summary['modal_ranking'])) or 'none'}",
            f"- runs with tied totals among passing options: {summary['tie_runs']}/{s}",
            f"- close call flagged in {summary['close_call_runs']}/{s} runs",
            "", "| Option | Total min | Total max | Spread |", "|---|---|---|---|",
        ]
        for name in summary["names"]:
            lo, hi = _range(summary["totals"][name])
            lines.append(f"| {clean(name)} | {lo}/{summary['max_total']} | {hi}/{summary['max_total']} | {hi - lo} |")
        varied = varying_factors(summary)
        lines += ["", "Factors whose final score varied (min to max):"]
        lines += [f"- {clean(name)}: " + ", ".join(f"{f} {lo}-{hi}" for f, (lo, hi) in v.items())
                  for name, v in varied.items()] or ["- none"]
        gate_diff = [f"{clean(name)}: {g} {outs}" for name, gs in summary["gates"].items()
                     for g, outs in gs.items() if len(outs) > 1]
        lines += ["", "Gates whose outcome varied:"] + ([f"- {g}" for g in gate_diff] or ["- none"])
    if summary["errors"]:
        lines += ["", "Errors:"] + [f"- {clean(e)}" for e in summary["errors"]]
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
    seen = set()
    for d in set_dirs:
        if not pathlib.Path(d).is_dir():
            return f"analyze.py: {d} is not a directory"
        stat = pathlib.Path(d).stat()
        identity = (stat.st_dev, stat.st_ino)
        if identity in seen:
            return f"analyze.py: {d} was given more than once"
        seen.add(identity)
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
            values[f].add(_normalize(parsed["meta"].get(f, "missing")))
        candidate_sets.add(tuple(sorted(c.lower() for c in parsed["candidates"])))
    return {"runs_total": len(dirs), "values": {f: sorted(v) for f, v in values.items()},
            "candidate_sets": sorted(candidate_sets), "errors": errors}


def render_context(summaries):
    lines = ["## Context at Checkpoint 1", ""]
    for label, s in summaries.items():
        lines.append(f"### {label} ({s['runs_total']} runs)")
        for f in CONTEXT_FIELDS:
            lines.append(f"- {f}: {' | '.join(map(clean, s['values'][f])) or 'missing'}")
        lines.append(f"- distinct candidate sets: {len(s['candidate_sets'])}")
        for cs in s["candidate_sets"]:
            lines.append(f"  - {', '.join(map(clean, cs))}")
        lines += [f"- error: {clean(e)}" for e in s["errors"]]
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
    command = argv[1] if len(argv) > 1 else None
    if command == "context" and len(argv) >= 3:
        locked, set_dirs = None, argv[2:]
    elif command == "scores" and len(argv) >= 5 and argv[2] == "--locked":
        locked, set_dirs = argv[3], argv[4:]
    else:
        print(__doc__, file=sys.stderr)
        return 2
    if locked is not None:
        try:
            meta = parse_locked_context(pathlib.Path(locked).read_text(encoding="utf-8"))["meta"]
            mode, environment = meta["mode"], meta["environment"]
        except (OSError, ValueError, KeyError) as exc:
            print(f"analyze.py: cannot read mode and environment from the locked-context file: {exc}",
                  file=sys.stderr)
            return 2
    problem = check_set_dirs(set_dirs)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    if locked is None:
        summaries = dict(zip(set_labels(set_dirs), map(summarize_context, set_dirs)))
        sys.stdout.write(render_context(summaries))
        return 0
    summaries = {}
    for label, set_dir in zip(set_labels(set_dirs), set_dirs):
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
