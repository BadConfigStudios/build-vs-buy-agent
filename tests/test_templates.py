import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_html  # noqa: E402
import score  # noqa: E402

TEMPLATES = ROOT / "skills" / "build-vs-buy" / "templates"
FACTORS = ["Fit", "Unused baggage", "Install effort", "Integration effort", "Maintenance effort",
           "Dependency count", "Lock-in and exit cost", "Monetary cost", "Time to value", "Security"]
FACTOR_LABELS = {
    "fit": "Fit", "unused_baggage": "Baggage", "install": "Install", "integration": "Integration",
    "maintenance": "Maintenance", "dependencies": "Dependencies", "lock_in": "Lock-in", "cost": "Cost",
    "time_to_value": "Time to value", "security": "Security",
}
HEADER = "| Factor | Base | Modifiers | Final | Why (matrix condition met) | Evidence (source, retrieved) | Status |"


class CandidateTemplate(unittest.TestCase):
    def setUp(self):
        self.text = (TEMPLATES / "candidate.md").read_text(encoding="utf-8")

    def test_table_header_and_all_factor_rows_in_order(self):
        self.assertIn(HEADER, self.text)
        rows = [m.group(1).strip() for m in re.finditer(r"^\| ([^|]+?) \|", self.text, re.M)]
        rows = [r for r in rows if r in FACTORS]
        self.assertEqual(rows, FACTORS)

    def test_has_h1_and_required_sections(self):
        self.assertTrue(self.text.startswith("# "))
        for heading in ("## Scoring", "## Could not verify", "## Owner overrides"):
            self.assertIn(heading, self.text)


class FinalTemplate(unittest.TestCase):
    def setUp(self):
        self.text = (TEMPLATES / "final.md").read_text(encoding="utf-8")

    def test_frontmatter_declares_analysis(self):
        self.assertTrue(self.text.startswith("---\n"))
        for key in ("topic:", "date:", "matrix_version:", "status: analysis", "mode:",
                    "environment:", "business_stage:", "expected_growth:"):
            self.assertIn(key, self.text)

    def test_scores_section_is_splittable(self):
        _, scores = build_html.split_scores(self.text)
        self.assertIsNotNone(scores)
        self.assertIn("| Option |", scores)

    def _columns(self, mode):
        _, scores = build_html.split_scores(self.text)
        lines = scores.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("| Option |") and any(f"mode: {mode}" in l for l in lines[max(0, i - 3):i]):
                return [c.strip() for c in line.strip("|").split("|")], lines[i + 2]
        self.fail(f"no {mode} scores table labelled 'mode: {mode}'")

    def test_full_table_factor_columns_match_weights(self):
        cols, _ = self._columns("full")
        factors = [FACTOR_LABELS[k] for k in score.WEIGHTS]
        self.assertEqual(cols, ["Option"] + factors + ["Total", "%", "Gates"])
        self.assertEqual(5 * sum(score.WEIGHTS.values()), 85)

    def test_quick_table_factor_columns_match_quick_factors(self):
        cols, row = self._columns("quick")
        factors = [FACTOR_LABELS[k] for k in score.QUICK_FACTORS]
        self.assertEqual(cols, ["Option"] + factors + ["Total", "%", "Gates"])
        self.assertIn("/60", row)
        self.assertEqual(5 * sum(score.WEIGHTS[k] for k in score.QUICK_FACTORS), 60)

    def test_required_sections(self):
        for heading in ("## Context", "## Stack summary", "## Scores", "## Ranking",
                        "## Owner overrides", "## Could not verify", "## Revisit conditions",
                        "## Exit notes", "## Tuning suggestions"):
            self.assertIn(heading, self.text)

    def test_no_recommendation_language(self):
        self.assertIn("This analysis does not make a decision.", self.text)


class ResearcherAgent(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "agents" / "bvb-researcher.md").read_text(encoding="utf-8")

    def test_frontmatter_is_read_only(self):
        head = self.text.split("---", 2)[1]
        self.assertIn("name: bvb-researcher", head)
        self.assertIn("tools: WebSearch, WebFetch, Read, Grep, Glob", head)
        self.assertNotRegex(head, r"\b(Write|Edit|Bash)\b")

    def test_forbids_scoring(self):
        self.assertIn("Do not score", self.text)


if __name__ == "__main__":
    unittest.main()
