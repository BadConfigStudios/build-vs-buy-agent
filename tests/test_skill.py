import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "build-vs-buy" / "SKILL.md"
COMMAND = ROOT / "commands" / "build-vs-buy.md"


class SkillFile(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_frontmatter(self):
        head = self.text.split("---", 2)[1]
        self.assertIn("name: build-vs-buy", head)
        self.assertRegex(head, r"description: .+")

    def test_references_every_runtime_asset(self):
        for ref in ("matrix.md", "templates/final.md", "templates/candidate.md",
                    "bvb-researcher", "score.py", "build_html.py"):
            self.assertIn(ref, self.text, ref)

    def test_names_both_checkpoints_and_rules(self):
        for phrase in ("Checkpoint 1", "Checkpoint 2", "Never change a scale or weight",
                       "analysis only", "bvb-<slug>-YYYYMMDD"):
            self.assertIn(phrase, self.text, phrase)

    def test_score_input_schema_keys_documented(self):
        for key in ("must_haves_met", "prerelease", "modifiers", "delta", "environment"):
            self.assertIn(key, self.text, key)


class CommandFile(unittest.TestCase):
    def test_command_hands_args_to_skill(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertRegex(text, r"description: .+")
        self.assertIn("$ARGUMENTS", text)
        self.assertIn("build-vs-buy", text)


class Readme(unittest.TestCase):
    def test_readme_documents_install_and_output(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in ("/plugin marketplace add BadConfigStudios/build-vs-buy-agent",
                       "/plugin install build-vs-buy@build-vs-buy-agent",
                       "/build-vs-buy", "docs/analysis/", "MIT"):
            self.assertIn(phrase, text, phrase)

    def test_no_private_details(self):
        for path in ROOT.rglob("*.md"):
            if ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"/Users/\w+", str(path))
            self.assertNotRegex(text, r"[\w.]+@gmail\.com", str(path))


if __name__ == "__main__":
    unittest.main()
