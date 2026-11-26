import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools" / "drift"))
import analyze  # noqa: E402
import score  # noqa: E402

FIX = ROOT / "tools" / "drift" / "fixtures"
SLUGS = {"Build": "build", "Amazon SES": "amazon-ses", "Postmark": "postmark",
         "Resend": "resend", "Postal": "postal"}


class DriftFixture(unittest.TestCase):
    def test_locked_context_is_complete_and_has_no_placeholders(self):
        parsed = analyze.parse_locked_context((FIX / "locked-context.md").read_text(encoding="utf-8"))
        meta = parsed["meta"]
        self.assertEqual((meta["mode"], meta["environment"]), ("full", "production"))
        for key in ("topic", "date", "matrix_version", *analyze.CONTEXT_FIELDS):
            self.assertTrue(meta[key], key)
        self.assertNotIn("<", " ".join(meta.values()))
        self.assertEqual(parsed["candidates"], list(SLUGS))

    def test_there_is_one_report_per_candidate(self):
        found = sorted(p.stem for p in (FIX / "reports").glob("*.md"))
        self.assertEqual(found, sorted(SLUGS.values()))

    def test_every_report_has_a_valid_prerelease_value(self):
        pattern = re.compile(r"prerelease:\**\s*`?(" + "|".join(score.PRERELEASE) + r")\b")
        for path in (FIX / "reports").glob("*.md"):
            self.assertRegex(path.read_text(encoding="utf-8"), pattern, path.name)

    def test_captured_reports_are_dated_and_sourced(self):
        for slug in ("amazon-ses", "postmark", "resend", "postal"):
            text = (FIX / "reports" / f"{slug}.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("<!-- Captured "), slug)
            self.assertIn("http", text, slug)

    def test_build_report_is_marked_as_an_estimate(self):
        text = (FIX / "reports" / "build.md").read_text(encoding="utf-8")
        self.assertIn("estimate", text)
        self.assertIn("not a measurement", text)

    def test_arm_inputs_exist(self):
        self.assertTrue((FIX / "sandbox-with-docs" / "README.md").is_file())
        prompt = (FIX / "context-prompt.md").read_text(encoding="utf-8")
        for phrase in ("/build-vs-buy email notifier", "locked-context.md", "Do not start research."):
            self.assertIn(phrase, prompt, phrase)


if __name__ == "__main__":
    unittest.main()
