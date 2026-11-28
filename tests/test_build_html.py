import html
import json
import pathlib
import re
import shutil
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


NODE = shutil.which("node")

NODE_DRIVER = r"""
const fs = require("fs"), vm = require("vm");
const [pagePath] = process.argv.slice(2);
const page = fs.readFileSync(pagePath, "utf8");
const scripts = [...page.matchAll(/<script(?: id="bvb-data" type="application\/json")?>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const [data, marked, inline] = scripts;
const panels = [];
const el = () => ({ children: [], setAttribute() {}, addEventListener() {}, appendChild(c) { this.children.push(c); } });
const document = {
  getElementById: id => id === "bvb-data" ? { textContent: data } : el(),
  createElement: () => { const e = el(); panels.push(e); return e; },
};
const ctx = vm.createContext({ document });
vm.runInContext(marked, ctx);
vm.runInContext(inline, ctx);
console.log(JSON.stringify(panels.filter(p => "innerHTML" in p).map(p => p.innerHTML)));
"""


def render_panels(markdown_by_tab):
    """Run the generated page's JS under node; return rendered HTML per panel."""
    tmp, run = make_run(final=markdown_by_tab)
    with tmp:
        page = build_html.build(run)
        driver = run / "driver.js"
        driver.write_text(NODE_DRIVER, encoding="utf-8")
        proc = subprocess.run([NODE, str(driver), str(page)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise AssertionError(proc.stderr)
        return json.loads(proc.stdout)


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

    def test_header_note_states_purpose_and_limits(self):
        tmp, run = make_run()
        with tmp:
            page = build_html.build(run).read_text(encoding="utf-8")
            self.assertIn('<p class="note">Analysis only, not a decision. It involves judgment and '
                          'some speculation. Treat it as one data point.</p>', page)

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


class Rendering(unittest.TestCase):
    def test_csp_still_blocks_remote_images(self):
        tmp, run = make_run()
        with tmp:
            page = build_html.build(run).read_text(encoding="utf-8")
            self.assertIn("img-src data:", page)

    @unittest.skipUnless(NODE, "node not installed")
    def test_link_title_not_double_escaped(self):
        out = render_panels('[a](https://x.test "T&C \\"q\\"")\n')[0]
        self.assertIn('title="T&amp;C &quot;q&quot;"', out)
        self.assertNotIn("&amp;amp;", out)
        self.assertNotIn("&amp;quot;", out)

    @unittest.skipUnless(NODE, "node not installed")
    def test_remote_image_becomes_plain_link(self):
        out = render_panels("![Logo & co](https://x.test/a.png)\n")[0]
        self.assertNotIn("<img", out)
        self.assertIn('<a href="https://x.test/a.png"', out)
        self.assertIn(">Logo &amp; co</a>", out)

    @unittest.skipUnless(NODE, "node not installed")
    def test_image_inside_link_has_no_nested_anchor(self):
        out = render_panels("[![img & co](https://x.test/i.png)](https://x.test/)\n")[0]
        self.assertEqual(out.count("<a "), 1)
        self.assertEqual(out.count("</a>"), 1)
        self.assertIn('<a href="https://x.test/"', out)
        self.assertIn("img &amp; co", out)

    @unittest.skipUnless(NODE, "node not installed")
    def test_non_http_image_is_alt_text_only(self):
        for src in ("javascript:alert(1)", "data:image/png;base64,AAAA", "./local.png"):
            with self.subTest(src=src):
                out = render_panels(f"![Alt <x>]({src})\n")[0]
                self.assertNotIn("<img", out)
                self.assertNotIn("<a ", out)
                self.assertIn("Alt &lt;x&gt;", out)


class CodeFenceHeadings(unittest.TestCase):
    def test_fenced_scores_heading_ignored(self):
        md = "# T\n\n```\n## Scores\n| a |\n```\n\ntext\n"
        summary, scores = build_html.split_scores(md)
        self.assertIsNone(scores)
        self.assertIn("## Scores", summary)

    def test_fenced_h2_does_not_end_scores_section(self):
        md = "## Scores\n\n```\n## not a heading\n```\n\nmore\n\n## Next\n\nx\n"
        summary, scores = build_html.split_scores(md)
        self.assertIn("more", scores)
        self.assertIn("## not a heading", scores)
        self.assertNotIn("## Next", scores)
        self.assertIn("## Next", summary)

    def test_tilde_fence_also_ignored(self):
        summary, scores = build_html.split_scores("~~~\n## Scores\n~~~\n")
        self.assertIsNone(scores)

    def test_real_scores_after_fence_still_found(self):
        md = "```\n## Scores\n```\n\n## Scores\n\n| a |\n"
        summary, scores = build_html.split_scores(md)
        self.assertEqual(scores, "## Scores\n\n| a |\n")

    def test_candidate_label_skips_fenced_h1(self):
        tmp, run = make_run(candidates={"c.md": "```\n# not a title\n```\n\n# Real\n"})
        with tmp:
            labels = [t["label"] for t in tabs_of(build_html.build(run).read_text(encoding="utf-8"))]
            self.assertEqual(labels[-1], "Real")

    def test_candidate_label_falls_back_when_only_fenced_h1(self):
        tmp, run = make_run(candidates={"c.md": "```\n# not a title\n```\n"})
        with tmp:
            labels = [t["label"] for t in tabs_of(build_html.build(run).read_text(encoding="utf-8"))]
            self.assertEqual(labels[-1], "c")

    def test_backtick_info_string_with_backtick_is_not_a_fence(self):
        md = "``` a`b\n\n## Scores\n\n| a |\n"
        summary, scores = build_html.split_scores(md)
        self.assertEqual(scores, "## Scores\n\n| a |\n")

    def test_tilde_info_string_may_contain_backtick(self):
        summary, scores = build_html.split_scores("~~~ a`b\n## Scores\n~~~\n")
        self.assertIsNone(scores)

    def test_backtick_fence_with_plain_info_string_masks(self):
        summary, scores = build_html.split_scores("```python\n## Scores\n```\n")
        self.assertIsNone(scores)

    def test_blockquote_fence_is_masked(self):
        md = "> ```\n> ## Scores\n> # Title\n> ```\nafter\n"
        masked = build_html._mask_fences(md)
        self.assertEqual(masked, " " * 5 + "\n" + " " * 11 + "\n" + " " * 9 + "\n" + " " * 5 + "\nafter\n")

    def test_blockquote_fence_masks_nested_quote_and_indent(self):
        masked = build_html._mask_fences(">> ```\n>> ## Scores\n>> ```\n")
        self.assertEqual(masked.strip(), "")

    def test_blockquote_fence_closes_before_following_text(self):
        masked = build_html._mask_fences("> ```\n> x\n> ```\n## Scores\n")
        self.assertTrue(masked.endswith("## Scores\n"))
        self.assertEqual(masked[:masked.index("## Scores")].strip(), "")

    def test_blockquote_fence_closes_and_real_scores_found(self):
        md = "> ```\n> ## Scores\n> ```\n\n## Scores\n\n| a |\n"
        summary, scores = build_html.split_scores(md)
        self.assertEqual(scores, "## Scores\n\n| a |\n")

    def test_masking_preserves_length(self):
        md = "> ```\n> ## Scores\n> ```\n``` a`b\n~~~\nx\n"
        self.assertEqual(len(build_html._mask_fences(md)), len(md))

    def test_indented_fence_masks_and_four_spaces_does_not(self):
        self.assertIsNone(build_html.split_scores("   ```\n## Scores\n   ```\n")[1])
        self.assertIsNotNone(build_html.split_scores("    ```\n## Scores\n")[1])

    def test_longer_closing_fence_closes(self):
        md = "```\n## Scores\n`````\n\n## Scores\n\nx\n"
        self.assertEqual(build_html.split_scores(md)[1], "## Scores\n\nx\n")

    def test_unterminated_fence_masks_to_eof(self):
        self.assertIsNone(build_html.split_scores("```\nx\n## Scores\n")[1])


class Frontmatter(unittest.TestCase):
    def test_crlf_frontmatter_parses(self):
        final = "---\r\ntopic: crlf topic\r\nstatus: analysis\r\n---\r\n\r\n# T\r\n\r\n## Scores\r\n\r\n| a |\r\n"
        tmp, run = make_run(final=None)
        with tmp:
            (run / "final.md").write_bytes(final.encode("utf-8"))
            page = build_html.build(run).read_text(encoding="utf-8")
            self.assertIn("<title>crlf topic</title>", page)
            tabs = tabs_of(page)
            self.assertIn("```yaml", tabs[0]["markdown"])
            self.assertEqual([t["label"] for t in tabs], ["Summary", "Scores"])
            self.assertNotIn("\r", tabs[0]["markdown"])

    def test_crlf_candidate_label(self):
        tmp, run = make_run(candidates={})
        with tmp:
            (run / "candidates").mkdir()
            (run / "candidates" / "c.md").write_bytes(b"# Title\r\n\r\nx\r\n")
            tabs = tabs_of(build_html.build(run).read_text(encoding="utf-8"))
            self.assertEqual(tabs[-1]["label"], "Title")

    def test_quoted_topic_unquoted(self):
        for raw, want in (('"secret rotation"', "secret rotation"), ("'secret rotation'", "secret rotation"),
                          ('"a: b"', "a: b"), ("plain", "plain"), ('"unterminated', '"unterminated')):
            with self.subTest(raw=raw):
                tmp, run = make_run(final=f"---\ntopic: {raw}\n---\n\n# T\n")
                with tmp:
                    page = build_html.build(run).read_text(encoding="utf-8")
                    self.assertIn(f"<title>{html.escape(want)}</title>", page)


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
