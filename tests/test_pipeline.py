"""Integration: score.py -> filled templates -> build_html.py, all through the CLIs."""
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TEMPLATES = ROOT / "skills" / "build-vs-buy" / "templates"
FACTORS = ["fit", "unused_baggage", "install", "integration", "maintenance",
           "dependencies", "lock_in", "cost", "time_to_value", "security"]
HOSTILE = "</script><script>alert('pwned')</script><img src=x onerror=alert(1)>"


def option(name, scores, **extra):
    opt = {
        "name": name,
        "must_haves_met": True,
        "prerelease": "none",
        "factors": {f: {"base": s, "modifiers": []} for f, s in zip(FACTORS, scores)},
    }
    opt.update(extra)
    return opt


FIXTURE = {
    "mode": "full",
    "environment": "production",
    "options": [
        option("Alpha Tool", [4, 3, 4, 4, 3, 4, 3, 4, 4, 4]),
        option("Build", [5, 5, 3, 4, 3, 5, 5, 4, 2, 4]),
        option("Risky Beta", [5, 5, 5, 5, 5, 5, 5, 5, 5, 5], prerelease="alpha"),
    ],
}


def run_script(name, *args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        input=stdin, capture_output=True, text=True, check=False,
    )


def render_final(result):
    """Fill the real final.md template: keep its prose, replace the score table rows."""
    text = (TEMPLATES / "final.md").read_text(encoding="utf-8")
    text = text.replace("<topic>", "pipeline fixture")
    header = re.search(r"^\| Option \|.*\n\|[-| ]+\|\n", text, re.M)
    row_pat = re.compile(r"^\| <name> \|.*\n", re.M)
    rows = []
    for opt in result["options"]:
        cells = [str(opt["factors"][f]["final"]) for f in FACTORS]
        gate = "pass" if opt["passed"] else "failed " + ", ".join(
            g for g, v in opt["gates"].items() if v == "fail")
        rows.append("| " + " | ".join(
            [opt["name"], *cells,
             f'{opt["weighted_total"]}/{result["max_total"]}', str(opt["percentage"]), gate]) + " |\n")
    assert header and row_pat.search(text), "final.md template lost its score table"
    return row_pat.sub("".join(rows), text, count=1)


def render_candidate(opt, result, evidence):
    text = (TEMPLATES / "candidate.md").read_text(encoding="utf-8")
    text = text.replace("<Candidate name>", opt["name"], 1)
    text = text.replace("<N>/<max> (<pct>%), <weak|mixed|strong>",
                        f'{opt["weighted_total"]}/{result["max_total"]} ({opt["percentage"]}%), {opt["band"]}')
    return text.replace("<URL, YYYY-MM-DD>", evidence)


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.run_dir = pathlib.Path(cls.tmp.name)
        scored = run_script("score.py", stdin=json.dumps(FIXTURE))
        assert scored.returncode == 0, scored.stderr
        cls.result = json.loads(scored.stdout)
        (cls.run_dir / "final.md").write_text(render_final(cls.result), encoding="utf-8")
        (cls.run_dir / "candidates").mkdir()
        for opt in cls.result["options"]:
            evidence = HOSTILE if opt["name"] == "Alpha Tool" else "https://example.com, 2026-11-25"
            slug = opt["name"].lower().replace(" ", "-")
            (cls.run_dir / "candidates" / f"{slug}.md").write_text(
                render_candidate(opt, cls.result, evidence), encoding="utf-8")
        built = run_script("build_html.py", str(cls.run_dir))
        assert built.returncode == 0, built.stderr
        cls.page = (cls.run_dir / "index.html").read_text(encoding="utf-8")
        data = re.search(r'<script id="bvb-data" type="application/json">(.*?)</script>',
                         cls.page, re.S).group(1)
        cls.tabs = json.loads(data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_tab_set_is_summary_scores_then_one_per_candidate(self):
        labels = [t["label"] for t in self.tabs]
        self.assertEqual(labels, ["Summary", "Scores", "Alpha Tool", "Build", "Risky Beta"])

    def test_scores_tab_totals_match_score_script_output(self):
        scores_md = next(t["markdown"] for t in self.tabs if t["label"] == "Scores")
        for opt in self.result["options"]:
            self.assertIn(f'{opt["weighted_total"]}/{self.result["max_total"]}', scores_md)
            self.assertIn(str(opt["percentage"]), scores_md)

    def test_candidate_tabs_carry_script_totals(self):
        for opt in self.result["options"]:
            md = next(t["markdown"] for t in self.tabs if t["label"] == opt["name"])
            self.assertIn(f'{opt["weighted_total"]}/{self.result["max_total"]} ({opt["percentage"]}%)', md)

    def test_gate_failure_shows_in_scores_and_ranking_excludes_it(self):
        scores_md = next(t["markdown"] for t in self.tabs if t["label"] == "Scores")
        self.assertIn("failed environment", scores_md)
        self.assertNotIn("Risky Beta", self.result["ranking"])
        self.assertEqual(self.result["ranking"][0], "Build" if
                         self.result["options"][1]["weighted_total"] >
                         self.result["options"][0]["weighted_total"] else "Alpha Tool")

    def test_summary_tab_keeps_frontmatter_and_no_decision_line(self):
        summary = self.tabs[0]["markdown"]
        self.assertIn("status: analysis", summary)
        self.assertIn("does not make a decision", summary)
        self.assertNotIn("## Scores", summary)

    def test_hostile_evidence_stays_inert_in_page(self):
        # marked + data block + app script; the hostile string adds none
        self.assertEqual(self.page.lower().count("<script"), 3)
        data = re.search(r'<script id="bvb-data" type="application/json">(.*?)</script>',
                         self.page, re.S).group(1)
        self.assertNotIn("<", data)  # every hostile "<" is \u003c inside the JSON block
        self.assertIn("\\u003c/script>", data)
        alpha = next(t["markdown"] for t in self.tabs if t["label"] == "Alpha Tool")
        self.assertIn(HOSTILE, alpha)  # preserved as data, rendered escaped client-side

    def test_bad_score_input_stops_pipeline_with_exit_2(self):
        bad = run_script("score.py", stdin=json.dumps({"environment": "production", "options": []}))
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, "")


if __name__ == "__main__":
    unittest.main()
