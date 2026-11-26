import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools" / "drift"))
import analyze  # noqa: E402
import score  # noqa: E402

LOCKED = """---
topic: email notifier
date: 2026-11-25
matrix_version: 1.3
mode: full
environment: production
business_stage: pre-revenue
expected_growth: 5,000 monthly active users in a year
core_ness: not core
---

## Must-haves
- now: send an email when a report finishes
- deferred: bounce handling
- nice-to-have: hosted templates

## Stack summary
Python API, managed Postgres.

## Candidates
- Alpha (hosted)
- Beta (self-hosted)
- Build (build)
"""


def entry(name, **overrides):
    factors = {f: {"base": 3, "modifiers": [], "why": "w", "evidence": "e", "status": "ok"}
               for f in score.WEIGHTS}
    for factor, base in overrides.items():
        factors[factor]["base"] = base
    return {"name": name, "must_haves_met": True, "prerelease": "none", "factors": factors}


def out_json(options, cost=0.1):
    reply = "```json\n" + json.dumps({"options": options}) + "\n```"
    return json.dumps({"result": reply, "total_cost_usd": cost})


def write_run(set_dir, index, files):
    run = pathlib.Path(set_dir) / f"run-{index}"
    run.mkdir(parents=True)
    for name, text in files.items():
        (run / name).write_text(text, encoding="utf-8")
    return run


class ParseLockedContext(unittest.TestCase):
    def test_reads_frontmatter_and_candidates(self):
        parsed = analyze.parse_locked_context(LOCKED)
        self.assertEqual(parsed["meta"]["mode"], "full")
        self.assertEqual(parsed["meta"]["environment"], "production")
        self.assertEqual(parsed["candidates"], ["Alpha", "Beta", "Build"])

    def test_missing_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            analyze.parse_locked_context("# no frontmatter\n")


class ExtractOptions(unittest.TestCase):
    def test_reads_fenced_json(self):
        reply = "```json\n" + json.dumps({"options": [entry("A")]}) + "\n```"
        self.assertEqual(analyze.extract_options(reply)[0]["name"], "A")

    def test_rejects_reply_without_block(self):
        with self.assertRaises(ValueError):
            analyze.extract_options("no block here")

    def test_rejects_empty_options(self):
        with self.assertRaises(ValueError):
            analyze.extract_options('```json\n{"options": []}\n```')


class Summarize(unittest.TestCase):
    def run_sets(self, per_run_options, costs=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for i, options in enumerate(per_run_options, 1):
            cost = (costs or [0.1] * len(per_run_options))[i - 1]
            write_run(tmp.name, i, {"all.out.json": out_json(options, cost)})
        return [analyze.load_run(d) for d in analyze.run_dirs(tmp.name)]

    def test_identical_runs_show_no_spread(self):
        opts = [entry("Alpha", fit=5), entry("Beta", fit=2)]
        runs = self.run_sets([opts, opts, opts])
        s = analyze.summarize(runs, "full", "production")
        self.assertEqual(s["runs_scored"], 3)
        self.assertEqual(analyze.varying_factors(s), {})
        self.assertEqual(s["modal_share"], 3)
        self.assertEqual(s["modal_ranking"], ["Alpha", "Beta"])
        self.assertEqual(s["pairwise_agreement"], 1.0)
        self.assertAlmostEqual(s["cost_total"], 0.3)

    def test_factor_spread_and_rank_flip_are_reported(self):
        runs = self.run_sets([
            [entry("Alpha", fit=5), entry("Beta", fit=2)],
            [entry("Alpha", fit=5), entry("Beta", fit=2)],
            [entry("Alpha", fit=2), entry("Beta", fit=5)],
        ])
        s = analyze.summarize(runs, "full", "production")
        self.assertEqual(analyze.varying_factors(s)["Alpha"], {"fit": (2, 5)})
        self.assertEqual(s["modal_ranking"], ["Alpha", "Beta"])
        self.assertEqual(s["modal_share"], 2)
        self.assertAlmostEqual(s["pairwise_agreement"], 2 / 3)
        self.assertEqual(s["totals"]["Alpha"], [score.evaluate(
            {"environment": "production", "options": [entry("Alpha", fit=5)]}
        )["options"][0]["weighted_total"]] * 2 + [score.evaluate(
            {"environment": "production", "options": [entry("Alpha", fit=2)]}
        )["options"][0]["weighted_total"]])

    def test_gate_change_is_reported(self):
        failing = entry("Alpha")
        failing["must_haves_met"] = False
        runs = self.run_sets([[entry("Alpha"), entry("Beta")], [failing, entry("Beta")]])
        s = analyze.summarize(runs, "full", "production")
        self.assertEqual(s["gates"]["Alpha"]["must_haves"], ["fail", "pass"])

    def test_unparseable_and_rejected_runs_are_listed_not_fatal(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        write_run(tmp.name, 1, {"a.out.json": out_json([entry("Alpha"), entry("Beta")])})
        write_run(tmp.name, 2, {"a.out.json": json.dumps({"result": "oops", "total_cost_usd": 0})})
        bad = entry("Alpha")
        del bad["factors"]["fit"]
        write_run(tmp.name, 3, {"a.out.json": out_json([bad])})
        write_run(tmp.name, 4, {})
        runs = [analyze.load_run(d) for d in analyze.run_dirs(tmp.name)]
        s = analyze.summarize(runs, "full", "production")
        self.assertEqual((s["runs_total"], s["runs_scored"]), (4, 1))
        text = " ".join(s["errors"])
        self.assertIn("run-2", text)
        self.assertIn("run-3", text)
        self.assertIn("run-4", text)

    def test_independent_runs_merge_files_into_one_option_list(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        write_run(tmp.name, 1, {"alpha.out.json": out_json([entry("Alpha")]),
                                "beta.out.json": out_json([entry("Beta")])})
        run = analyze.load_run(analyze.run_dirs(tmp.name)[0])
        self.assertEqual([o["name"] for o in run["options"]], ["Alpha", "Beta"])

    def test_render_mentions_key_numbers(self):
        runs = self.run_sets([[entry("Alpha", fit=5), entry("Beta")],
                              [entry("Alpha", fit=2), entry("Beta")]])
        s = analyze.summarize(runs, "full", "production")
        text = analyze.render("sonnet-independent", s)
        for needle in ("## sonnet-independent", "runs: 2, scored: 2", "Alpha: fit 2-5",
                       "pairwise order agreement", "close call flagged"):
            self.assertIn(needle, text)
        table = analyze.render_comparison({"a": s, "b": s})
        self.assertIn("| a |", table)
        self.assertIn("| b |", table)


class ContextMode(unittest.TestCase):
    def test_arms_agree_or_differ(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        for arm, stage in (("with-docs", "pre-revenue"), ("no-docs", "break-even")):
            for i in (1, 2):
                write_run(root / arm, i, {"locked-context.md": LOCKED.replace("pre-revenue", stage)})
        summaries = {a: analyze.summarize_context(root / a) for a in ("with-docs", "no-docs")}
        text = analyze.render_context(summaries)
        self.assertIn("Fields that differ between run sets: business_stage", text)
        self.assertIn("Candidate sets identical between run sets: yes", text)

    def test_missing_file_is_an_error_line(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        write_run(tmp.name, 1, {})
        s = analyze.summarize_context(tmp.name)
        self.assertEqual(len(s["errors"]), 1)


class TemplateStaysParseable(unittest.TestCase):
    def test_locked_context_template_matches_the_parser(self):
        text = (ROOT / "skills" / "build-vs-buy" / "templates" / "locked-context.md").read_text(encoding="utf-8")
        parsed = analyze.parse_locked_context(text)
        for key in ("topic", "date", "matrix_version", *analyze.CONTEXT_FIELDS):
            self.assertIn(key, parsed["meta"], key)
        self.assertEqual(parsed["candidates"], ["<name>"])


class Cli(unittest.TestCase):
    def test_scores_command_prints_report(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        locked = root / "locked.md"
        locked.write_text(LOCKED, encoding="utf-8")
        for i in (1, 2):
            write_run(root / "set-a", i, {"all.out.json": out_json([entry("Alpha"), entry("Beta", fit=1)])})
        proc = subprocess.run([sys.executable, str(ROOT / "tools" / "drift" / "analyze.py"),
                               "scores", "--locked", str(locked), str(root / "set-a")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("## set-a", proc.stdout)

    def test_bad_usage_exits_2(self):
        proc = subprocess.run([sys.executable, str(ROOT / "tools" / "drift" / "analyze.py")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
