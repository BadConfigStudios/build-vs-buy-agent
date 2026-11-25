import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_html  # noqa: E402

FINAL = """---
topic: secret rotation
status: analysis
---

# Analysis: secret rotation

Intro text.

## Scores

| Option | Score |
|---|---|
| Script | 85% |

## Revisit conditions

- more secrets
"""

CAND_A = "# Script\n\nDetails.\n"
CAND_B = "# Vault\n\nHostile </script><script>alert(1)</script> text.\n"


def make_run(final=FINAL, candidates=None):
    tmp = tempfile.TemporaryDirectory()
    run = pathlib.Path(tmp.name)
    if final is not None:
        (run / "final.md").write_text(final, encoding="utf-8")
    if candidates:
        (run / "candidates").mkdir()
        for name, text in candidates.items():
            (run / "candidates" / name).write_text(text, encoding="utf-8")
    return tmp, run


def tabs_of(page):
    match = re.search(r'<script id="bvb-data" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(match.group(1))


class SplitScores(unittest.TestCase):
    def test_extracts_scores_section(self):
        summary, scores = build_html.split_scores("# T\n\n## Scores\n\n| a |\n\n## Next\n\ntext\n")
        self.assertIn("| a |", scores)
        self.assertNotIn("## Scores", summary)
        self.assertIn("## Next", summary)

    def test_no_scores_section(self):
        summary, scores = build_html.split_scores("# T\n\ntext\n")
        self.assertIsNone(scores)
        self.assertIn("text", summary)


class Build(unittest.TestCase):
    def test_tabs_in_order(self):
        tmp, run = make_run(candidates={"b-vault.md": CAND_B, "a-script.md": CAND_A})
        with tmp:
            page = build_html.build(run).read_text(encoding="utf-8")
            labels = [t["label"] for t in tabs_of(page)]
            self.assertEqual(labels, ["Summary", "Scores", "Script", "Vault"])

    def test_summary_excludes_scores_and_shows_frontmatter(self):
        tmp, run = make_run()
        with tmp:
            tabs = tabs_of(build_html.build(run).read_text(encoding="utf-8"))
            summary = tabs[0]["markdown"]
            self.assertIn("```yaml", summary)
            self.assertIn("topic: secret rotation", summary)
            self.assertNotIn("| Script | 85% |", summary)
            self.assertIn("| Script | 85% |", tabs[1]["markdown"])

    def test_no_scores_tab_when_section_missing(self):
        tmp, run = make_run(final="# T\n\ntext\n")
        with tmp:
            labels = [t["label"] for t in tabs_of(build_html.build(run).read_text(encoding="utf-8"))]
            self.assertEqual(labels, ["Summary"])

    def test_no_candidates_dir(self):
        tmp, run = make_run()
        with tmp:
            labels = [t["label"] for t in tabs_of(build_html.build(run).read_text(encoding="utf-8"))]
            self.assertEqual(labels, ["Summary", "Scores"])

    def test_label_falls_back_to_file_stem(self):
        tmp, run = make_run(candidates={"plain.md": "no heading here\n"})
        with tmp:
            labels = [t["label"] for t in tabs_of(build_html.build(run).read_text(encoding="utf-8"))]
            self.assertEqual(labels[-1], "plain")

    def test_hostile_script_tag_cannot_break_out(self):
        tmp, run = make_run(candidates={"b.md": CAND_B})
        with tmp:
            page = build_html.build(run).read_text(encoding="utf-8")
            self.assertEqual(page.count("</script>"), 3)
            self.assertNotIn("<script>alert(1)", page)
            self.assertIn("alert(1)", tabs_of(page)[-1]["markdown"])

    def test_page_is_self_contained_and_hardened(self):
        tmp, run = make_run()
        with tmp:
            page = build_html.build(run).read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", page)
            self.assertIn("default-src 'none'", page)
            self.assertIn("renderer.html", page)
            self.assertIn("renderer.link", page)
            self.assertNotRegex(page, r'<script[^>]+src=')
            self.assertNotRegex(page, r'<link[^>]+href=')

    def test_title_from_topic_and_escaped(self):
        tmp, run = make_run(final="---\ntopic: a <b> & c\n---\n\n# T\n")
        with tmp:
            page = build_html.build(run).read_text(encoding="utf-8")
            self.assertIn("<title>a &lt;b&gt; &amp; c</title>", page)

    def test_placeholders_in_content_not_substituted(self):
        tmp, run = make_run(final="# T\n\nliteral __MARKED__ and __TITLE__ text\n")
        with tmp:
            page = build_html.build(run).read_text(encoding="utf-8")
            self.assertIn("literal __MARKED__ and __TITLE__ text", tabs_of(page)[0]["markdown"])

    def test_missing_final_raises(self):
        tmp, run = make_run(final=None)
        with tmp:
            with self.assertRaises(FileNotFoundError):
                build_html.build(run)


class Cli(unittest.TestCase):
    def test_cli_writes_index_html(self):
        tmp, run = make_run(candidates={"a.md": CAND_A})
        with tmp:
            proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_html.py"), str(run)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((run / "index.html").is_file())
            self.assertIn("index.html", proc.stdout)

    def test_cli_missing_final_exits_2(self):
        tmp, run = make_run(final=None)
        with tmp:
            proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_html.py"), str(run)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("build_html.py:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
