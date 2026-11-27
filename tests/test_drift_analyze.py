import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
    def test_scorer_error_reply_is_named(self):
        with self.assertRaisesRegex(ValueError, "scorer returned an error: matrix_version_mismatch"):
            analyze.extract_options('```json\n{"error": "matrix_version_mismatch"}\n```')

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


class Hardening(unittest.TestCase):
    def tmp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return pathlib.Path(d.name)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "tools" / "drift" / "analyze.py"), *args],
                              capture_output=True, text=True)

    def locked(self, root):
        p = root / "locked.md"
        p.write_text(LOCKED, encoding="utf-8")
        return str(p)

    def test_bad_set_dirs_exit_2_in_both_modes(self):
        root = self.tmp()
        (root / "empty").mkdir()
        for mode in ("scores", "context"):
            pre = ["--locked", self.locked(root)] if mode == "scores" else []
            for target in (root / "missing", root / "empty"):
                proc = self.cli(mode, *pre, str(target))
                self.assertEqual(proc.returncode, 2, (mode, target))
                self.assertIn(str(target), proc.stderr)
                self.assertNotIn("runs:", proc.stdout)

    def test_all_runs_failed_exits_2(self):
        root = self.tmp()
        write_run(root / "set", 1, {"a.out.json": "not json"})
        proc = self.cli("scores", "--locked", self.locked(root), str(root / "set"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no run could be scored", proc.stderr)

    def test_partial_independent_run_is_unscored(self):
        root = self.tmp()
        write_run(root, 1, {"a.out.json": out_json([entry("Alpha"), entry("Beta")])})
        write_run(root, 2, {"a.out.json": out_json([entry("Alpha")]), "b.out.json": "garbage"})
        runs = [analyze.load_run(d) for d in analyze.run_dirs(root)]
        s = analyze.summarize(runs, "full", "production")
        self.assertEqual((s["runs_total"], s["runs_scored"]), (2, 1))
        self.assertEqual(s["totals"]["Alpha"].__len__(), 1)
        self.assertTrue(any(e.startswith("run-2: b.out.json") for e in s["errors"]))
        text = analyze.render("x", s)
        self.assertIn("runs: 2, scored: 1", text)
        self.assertNotIn("runs scored", text)

    def test_run_names_and_numeric_order(self):
        root = self.tmp()
        for i in (10, 2, 1):
            write_run(root, i, {"a.out.json": out_json([entry("Alpha")]) if i != 10 else "bad"})
        dirs = analyze.run_dirs(root)
        self.assertEqual([d.name for d in dirs], ["run-1", "run-2", "run-10"])
        runs = [analyze.load_run(d) for d in dirs]
        self.assertEqual(runs[2]["name"], "run-10")
        s = analyze.summarize(runs, "full", "production")
        self.assertTrue(any(e.startswith("run-10:") for e in s["errors"]))

    def test_label_collisions_use_full_paths(self):
        root = self.tmp()
        a, b = root / "x" / "set", root / "y" / "set"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        labels = analyze.set_labels([str(a), str(b)])
        self.assertEqual(labels, [str(a.resolve()), str(b.resolve())])
        self.assertEqual(analyze.set_labels([str(a)]), ["set"])
        self.assertNotEqual(analyze.set_labels(["/"])[0], "")

    def test_deeply_nested_json_is_an_error_not_a_crash(self):
        root = self.tmp()
        deep = "[" * 100000 + "]" * 100000
        write_run(root, 1, {"a.out.json": deep})
        write_run(root, 2, {"a.out.json": json.dumps({"result": "```json\n" + deep + "\n```"})})
        for i in (1, 2):
            run = analyze.load_run(root / f"run-{i}")
            self.assertEqual(run["options"], [])
            self.assertEqual(len(run["errors"]), 1)

    def test_non_finite_cost_is_an_error(self):
        root = self.tmp()
        reply = "```json\n" + json.dumps({"options": [entry("Alpha")]}) + "\n```"
        write_run(root, 1, {"a.out.json": '{"result": %s, "total_cost_usd": NaN}' % json.dumps(reply)})
        run = analyze.load_run(root / "run-1")
        self.assertEqual(run["cost"], 0.0)
        self.assertEqual(len(run["errors"]), 1)
        self.assertIn("finite", run["errors"][0])

    def test_last_fence_with_options_wins(self):
        good = json.dumps({"options": [entry("Real")]})
        example = json.dumps({"options": [entry("Example")]})
        reply = f"e.g.\n```json\n{example}\n```\nfinal\n```json\n{good}\n```\nnote\n```json\n{{\"x\": 1}}\n```"
        self.assertEqual(analyze.extract_options(reply)[0]["name"], "Real")


class FollowUps(unittest.TestCase):
    def tmp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return pathlib.Path(d.name)

    def summary(self, per_run_options, costs=None):
        root = self.tmp()
        for i, options in enumerate(per_run_options, 1):
            cost = costs[i - 1] if costs else 0.1
            write_run(root, i, {"all.out.json": out_json(options, cost)})
        runs = [analyze.load_run(d) for d in analyze.run_dirs(root)]
        return analyze.summarize(runs, "full", "production")

    def test_ties_among_passing_options_are_counted(self):
        tied = [entry("Alpha"), entry("Beta")]
        untied = [entry("Alpha", fit=5), entry("Beta")]
        failing = entry("Beta")
        failing["must_haves_met"] = False
        s = self.summary([tied, untied, [entry("Alpha"), failing]])
        self.assertEqual(s["tie_runs"], 1)
        self.assertIn("- runs with tied totals among passing options: 1/3", analyze.render("x", s))

    def test_cost_is_listed_per_run(self):
        opts = [entry("Alpha"), entry("Beta")]
        s = self.summary([opts, opts], costs=[0.1, 0.25])
        self.assertEqual(s["run_costs"], [("run-1", 0.1), ("run-2", 0.25)])
        self.assertIn("- cost per run: run-1 $0.100, run-2 $0.250", analyze.render("x", s))

    def test_clean_strips_control_characters_and_escapes_pipes(self):
        self.assertEqual(analyze.clean("a|b\x1b[31m\u202ed"), "a\\|b[31md")

    def test_option_names_and_errors_are_cleaned_in_the_report(self):
        bad = "Al|pha\x1b"
        low = entry("Beta", fit=1)
        gated = entry(bad, fit=5)
        gated["must_haves_met"] = False
        s = self.summary([[entry(bad), low], [gated, low]])
        s["errors"].append("run-9: a|b\x1b")
        text = analyze.render("x", s)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("Al|pha", text)
        self.assertIn("| Al\\|pha |", text)
        self.assertIn("- run-9: a\\|b", text)

    def test_context_values_candidates_and_errors_are_cleaned(self):
        root = self.tmp()
        text = LOCKED.replace("pre-revenue", "pre|revenue\x1b").replace("- Alpha (hosted)", "- Al|pha\x1b (hosted)")
        write_run(root, 1, {"locked-context.md": text})
        s = analyze.summarize_context(root)
        s["errors"].append("run-9: a|b\x1b")
        out = analyze.render_context({"x": s})
        self.assertNotIn("\x1b", out)
        self.assertIn("pre\\|revenue", out)
        self.assertIn("al\\|pha", out)
        self.assertIn("- error: run-9: a\\|b", out)

    def test_oversized_output_is_an_error_and_is_not_read(self):
        root = self.tmp()
        write_run(root, 1, {"a.out.json": " " * (analyze.MAX_OUTPUT_BYTES + 1)})
        with mock.patch.object(pathlib.Path, "read_text", side_effect=AssertionError("read")):
            run = analyze.load_run(root / "run-1")
        self.assertEqual(run["options"], [])
        self.assertEqual(len(run["errors"]), 1)
        self.assertIn("larger than 1000000 bytes", run["errors"][0])

    def test_only_the_type_tag_is_stripped_from_candidate_names(self):
        lines = ["Mail (EU) (hosted)", "Relay (v2)", "Postal (self-hosted)",
                 "Build (build)", "Build (build): outbox table (Postgres)",
                 "Build (build: outbox table and a worker)"]
        text = LOCKED.split("## Candidates")[0] + "## Candidates\n" + "".join(f"- {c}\n" for c in lines)
        self.assertEqual(analyze.parse_locked_context(text)["candidates"],
                         ["Mail (EU)", "Relay (v2)", "Postal", "Build", "Build", "Build"])

    def test_dashes_inside_a_frontmatter_value_survive(self):
        parsed = analyze.parse_locked_context(LOCKED.replace("email notifier", "email --- notifier"))
        self.assertEqual(parsed["meta"]["topic"], "email --- notifier")
        self.assertEqual(parsed["meta"]["mode"], "full")
        self.assertEqual(parsed["candidates"], ["Alpha", "Beta", "Build"])

    def test_mode_and_environment_are_normalized(self):
        text = LOCKED.replace("mode: full", "mode:  Full ").replace("environment: production", "environment: PRODUCTION")
        meta = analyze.parse_locked_context(text)["meta"]
        self.assertEqual((meta["mode"], meta["environment"]), ("full", "production"))

    def test_type_tag_ignores_case_nesting_and_qualifiers(self):
        lines = ["Alpha (Hosted)", "Build (build: a table (Postgres) and worker)", "Beta (hosted, EU region)"]
        text = LOCKED.split("## Candidates")[0] + "## Candidates\n" + "".join(f"- {c}\n" for c in lines)
        self.assertEqual(analyze.parse_locked_context(text)["candidates"], ["Alpha", "Build", "Beta"])

    def test_trailing_blanks_after_a_frontmatter_fence_are_accepted(self):
        parsed = analyze.parse_locked_context(LOCKED.replace("---\n", "--- \t\n"))
        self.assertEqual(parsed["meta"]["mode"], "full")
        self.assertEqual(parsed["candidates"], ["Alpha", "Beta", "Build"])

    def test_clean_escapes_a_backslash_before_a_pipe(self):
        self.assertEqual(analyze.clean("A\\|B"), "A\\\\\\|B")

    def test_clean_turns_every_line_break_into_a_space(self):
        self.assertEqual(analyze.clean("a\nb\tc\u2028d\u2029e\r\nf"), "a b c d e  f")

    def test_parse_error_is_kept_when_no_block_has_options(self):
        reply = '```json\n{"options": [,]}\n```\n```json\n[1]\n```'
        with self.assertRaisesRegex(ValueError, "no options list .*did not parse: Expecting value"):
            analyze.extract_options(reply)

    def test_the_same_directory_in_another_letter_case_exits_2(self):
        root = self.tmp()
        write_run(root / "set", 1, {"locked-context.md": LOCKED})
        if not (root / "SET").is_dir():
            self.skipTest("case-sensitive filesystem")
        self.assertIn("given more than once",
                      analyze.check_set_dirs([str(root / "set"), str(root / "SET")]) or "")

    def test_the_same_directory_twice_exits_2(self):
        root = self.tmp()
        write_run(root / "set", 1, {"locked-context.md": LOCKED})
        proc = subprocess.run([sys.executable, str(ROOT / "tools" / "drift" / "analyze.py"), "context",
                               str(root / "set"), str(root / "set") + "/."],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("given more than once", proc.stderr)


if __name__ == "__main__":
    unittest.main()
