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
    if not (header and row_pat.search(text)):
        raise RuntimeError("final.md template lost its score table")
    table = "".join(rows)
    return row_pat.sub(lambda m: table, text, count=1)


def render_candidate(opt, result, evidence):
    text = (TEMPLATES / "candidate.md").read_text(encoding="utf-8")
    text = text.replace("<Candidate name>", opt["name"], 1)
    text = text.replace("<N>/<max> (<pct>%), <weak|mixed|strong>",
                        f'{opt["weighted_total"]}/{result["max_total"]} ({opt["percentage"]}%), {opt["band"]}')
    return text.replace("<URL, YYYY-MM-DD>", evidence)


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.run_dir = pathlib.Path(tmp.name)
        scored = run_script("score.py", stdin=json.dumps(FIXTURE))
        if scored.returncode != 0:
            raise RuntimeError(scored.stderr)
        cls.result = json.loads(scored.stdout)
        (cls.run_dir / "final.md").write_text(render_final(cls.result), encoding="utf-8")
        (cls.run_dir / "candidates").mkdir()
        for opt in cls.result["options"]:
            evidence = HOSTILE if opt["name"] == "Alpha Tool" else "https://example.com, 2026-11-25"
            slug = opt["name"].lower().replace(" ", "-")
            (cls.run_dir / "candidates" / f"{slug}.md").write_text(
                render_candidate(opt, cls.result, evidence), encoding="utf-8")
        built = run_script("build_html.py", str(cls.run_dir))
        if built.returncode != 0:
            raise RuntimeError(built.stderr)
        cls.page = (cls.run_dir / "index.html").read_text(encoding="utf-8")
        data = re.search(r'<script id="bvb-data" type="application/json">(.*?)</script>',
                         cls.page, re.S).group(1)
        cls.tabs = json.loads(data)

    def test_tab_set_is_summary_scores_then_one_per_candidate(self):
        labels = [t["label"] for t in self.tabs]
        self.assertEqual(labels, ["Summary", "Scores", "Alpha Tool", "Build", "Risky Beta"])

    def test_scores_tab_totals_match_known_values(self):
        scores_md = next(t["markdown"] for t in self.tabs if t["label"] == "Scores")
        for total, pct in [("63/85", "74.1"), ("66/85", "77.6"), ("85/85", "100.0")]:
            self.assertIn(total, scores_md)
            self.assertIn(pct, scores_md)

    def test_candidate_tabs_carry_known_totals(self):
        expected = {"Alpha Tool": "63/85 (74.1%)", "Build": "66/85 (77.6%)", "Risky Beta": "85/85 (100.0%)"}
        for name, text in expected.items():
            md = next(t["markdown"] for t in self.tabs if t["label"] == name)
            self.assertIn(text, md)

    def test_gate_failure_shows_in_scores_and_ranking_excludes_it(self):
        scores_md = next(t["markdown"] for t in self.tabs if t["label"] == "Scores")
        self.assertIn("failed environment", scores_md)
        risky = next(o for o in self.result["options"] if o["name"] == "Risky Beta")
        self.assertEqual(risky["gates"]["environment"], "fail")
        self.assertEqual(self.result["ranking"], ["Build", "Alpha Tool"])

    def test_summary_tab_keeps_frontmatter_and_no_decision_line(self):
        summary = self.tabs[0]["markdown"]
        self.assertIn("status: analysis", summary)
        self.assertIn("does not make a decision", summary)
        self.assertNotIn("## Scores", summary)

    def test_hostile_evidence_stays_inert_in_page(self):
        block = re.compile(r'<script id="bvb-data" type="application/json">(.*?)</script>', re.S)
        self.assertEqual(len(block.findall(self.page)), 1)
        data = block.search(self.page).group(1)
        self.assertNotIn("<", data)  # every hostile "<" is \u003c inside the JSON block
        self.assertIn("\\u003c/script>", data)
        # outside the data block the payload appears nowhere (independent of vendored marked)
        outside = block.sub("", self.page)
        self.assertNotIn("pwned", outside)
        self.assertNotIn("<img src=x", outside)
        alpha = next(t["markdown"] for t in self.tabs if t["label"] == "Alpha Tool")
        self.assertIn(HOSTILE, alpha)  # preserved as data; escaping at render time is covered in test_build_html


if __name__ == "__main__":
    unittest.main()
