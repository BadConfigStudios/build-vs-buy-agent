import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import score  # noqa: E402

MATRIX = ROOT / "skills" / "build-vs-buy" / "matrix.md"
NAMES = {
    "Fit": "fit",
    "Unused baggage": "unused_baggage",
    "Install effort": "install",
    "Integration effort": "integration",
    "Maintenance effort": "maintenance",
    "Dependency count": "dependencies",
    "Lock-in and exit cost": "lock_in",
    "Monetary cost": "cost",
    "Time to value": "time_to_value",
    "Security": "security",
}
FORBIDDEN = ("Argo", "Kyverno", "Cloudflare", "BadConfig", "Bryan")


class MatrixWeights(unittest.TestCase):
    def setUp(self):
        self.text = MATRIX.read_text(encoding="utf-8")

    def test_step3_weights_match_score_py(self):
        section = self.text.split("## Step 3", 1)[1].split("## Step 4", 1)[0]
        found = {NAMES[m.group(1)]: int(m.group(2))
                 for m in re.finditer(r"^- (.+?): (\d)$", section, re.M)}
        self.assertEqual(found, score.WEIGHTS)

    def test_total_weight_and_max(self):
        self.assertIn("Total weight is 17", self.text)
        self.assertIn("maximum weighted score is 85", self.text)
        self.assertEqual(sum(score.WEIGHTS.values()), 17)

    def test_no_project_specific_names(self):
        for word in FORBIDDEN:
            self.assertNotIn(word, self.text, word)

    def test_declares_v1_3_and_stack_summary(self):
        self.assertIn("Version 1.3", self.text)
        self.assertIn("5. Stack summary", self.text)


if __name__ == "__main__":
    unittest.main()
