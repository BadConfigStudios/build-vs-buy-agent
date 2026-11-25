#!/usr/bin/env python3
"""Build one self-contained, tabbed index.html from a build-vs-buy run directory.

Usage: build_html.py <run_dir>
Reads <run_dir>/final.md and <run_dir>/candidates/*.md, writes <run_dir>/index.html.
"""
import html
import json
import pathlib
import re
import sys

VENDOR = pathlib.Path(__file__).resolve().parent / "vendor" / "marked.min.js"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SCORES_HEADING = re.compile(r"^## Scores[ \t]*$", re.M)
ANY_H2 = re.compile(r"^## ", re.M)
TOPIC = re.compile(r"^topic:[ \t]*(.+?)[ \t]*$", re.M)
H1 = re.compile(r"^# (.+?)[ \t]*$", re.M)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
PLACEHOLDER = re.compile(r"__(TITLE|DATA|MARKED)__")

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:">
<title>__TITLE__</title>
<style>
:root { --bg:#fff; --fg:#1b1f24; --muted:#59636e; --line:#d0d7de; --accent:#0969da; --soft:#f6f8fa; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --line:#30363d; --accent:#4493f8; --soft:#161b22; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui, sans-serif; }
header, nav, main { max-width: 980px; margin: 0 auto; padding: 0 16px; }
header { padding-top: 24px; }
h1.page { margin: 0 0 4px; font-size: 1.5rem; }
.note { margin: 0 0 16px; color: var(--muted); font-size: .9rem; }
nav { display:flex; flex-wrap:wrap; gap:4px; border-bottom:1px solid var(--line); }
nav button { background:none; border:0; border-bottom:2px solid transparent; color:var(--muted);
  padding:8px 12px; font:inherit; cursor:pointer; }
nav button[aria-selected="true"] { color:var(--fg); border-bottom-color:var(--accent); }
main { padding-top: 16px; padding-bottom: 48px; }
.panel[hidden] { display:none; }
table { border-collapse: collapse; display:block; overflow-x:auto; max-width:100%; }
th, td { border:1px solid var(--line); padding:6px 10px; vertical-align:top; text-align:left; }
th { background:var(--soft); }
pre { background:var(--soft); padding:12px; overflow-x:auto; border-radius:6px; }
code { background:var(--soft); padding:1px 4px; border-radius:4px; }
pre code { padding:0; background:none; }
a { color:var(--accent); }
@media print {
  nav { display:none; }
  .panel[hidden] { display:block; }
  .panel { break-before: page; }
  .panel:first-of-type { break-before: auto; }
}
</style>
</head>
<body>
<header>
<h1 class="page">__TITLE__</h1>
<p class="note">Analysis only. This is not a decision.</p>
</header>
<nav id="tabs" role="tablist"></nav>
<main id="panels"></main>
<script id="bvb-data" type="application/json">__DATA__</script>
<script>__MARKED__</script>
<script>
(function () {
  var tabs = JSON.parse(document.getElementById("bvb-data").textContent);
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  var renderer = new marked.Renderer();
  renderer.html = function (raw) {
    return esc(typeof raw === "string" ? raw : raw.text);
  };
  renderer.link = function (href, title, text) {
    if (!/^(https?:|mailto:|#)/i.test(href || "")) { return text; }
    return '<a href="' + esc(href) + '"' + (title ? ' title="' + title + '"' : "") +
      ' rel="noopener noreferrer">' + text + "</a>";
  };
  renderer.image = function (href, title, text) {
    if (!/^https?:/i.test(href || "")) { return text; }
    return '<a href="' + esc(href) + '" rel="noopener noreferrer">' + text + "</a>";
  };
  marked.use({ renderer: renderer });

  var nav = document.getElementById("tabs");
  var main = document.getElementById("panels");
  var buttons = [];
  var panels = [];
  function select(i) {
    buttons.forEach(function (b, j) { b.setAttribute("aria-selected", j === i ? "true" : "false"); });
    panels.forEach(function (p, j) { p.hidden = j !== i; });
  }
  tabs.forEach(function (tab, i) {
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "tab");
    b.textContent = tab.label;
    b.addEventListener("click", function () { select(i); });
    nav.appendChild(b);
    buttons.push(b);
    var p = document.createElement("section");
    p.className = "panel";
    p.setAttribute("role", "tabpanel");
    p.innerHTML = marked.parse(tab.markdown);
    main.appendChild(p);
    panels.push(p);
  });
  select(0);
})();
</script>
</body>
</html>
"""


def _mask_fences(md):
    """Blank out fenced code blocks (same length, newlines kept) so heading
    regexes cannot match inside them; offsets still index the original text."""
    out = []
    marker = None
    for line in md.splitlines(keepends=True):
        fence = FENCE.match(line)
        if marker is None:
            if fence:
                marker = fence.group(1)
                out.append(re.sub(r"[^\r\n]", " ", line))
            else:
                out.append(line)
        else:
            out.append(re.sub(r"[^\r\n]", " ", line))
            if fence and fence.group(1)[0] == marker[0] and len(fence.group(1)) >= len(marker) \
                    and not line.strip().strip(marker[0]):
                marker = None
    return "".join(out)


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def split_scores(md):
    """Return (summary, scores). scores is None when there is no '## Scores' section."""
    masked = _mask_fences(md)
    match = SCORES_HEADING.search(masked)
    if not match:
        return md, None
    rest = masked[match.end():]
    following = ANY_H2.search(rest)
    end = match.end() + (following.start() if following else len(rest))
    scores = md[match.start():end].strip() + "\n"
    summary = (md[:match.start()] + md[end:]).strip() + "\n"
    return summary, scores


def _split_frontmatter(md):
    match = FRONTMATTER.match(md)
    if not match:
        return None, md
    return match.group(1), md[match.end():]


def _read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def build(run_dir):
    run = pathlib.Path(run_dir)
    final = run / "final.md"
    if not final.is_file():
        raise FileNotFoundError(f"final.md not found in {run}")
    meta, body = _split_frontmatter(_read(final))
    summary, scores = split_scores(body)
    if meta:
        summary = "```yaml\n" + meta + "\n```\n\n" + summary
    tabs = [{"label": "Summary", "markdown": summary}]
    if scores:
        tabs.append({"label": "Scores", "markdown": scores})
    cdir = run / "candidates"
    if cdir.is_dir():
        for path in sorted(cdir.glob("*.md")):
            text = _read(path)
            heading = H1.search(_mask_fences(text))
            tabs.append({"label": heading.group(1) if heading else path.stem, "markdown": text})

    topic = TOPIC.search(meta) if meta else None
    title = _unquote(topic.group(1)) if topic else run.name
    marked = VENDOR.read_text(encoding="utf-8")
    if "</script" in marked.lower():
        raise ValueError("vendored marked.min.js contains a closing script tag")
    data = json.dumps(tabs).replace("<", "\\u003c")
    values = {"TITLE": html.escape(title), "DATA": data, "MARKED": marked}
    page = PLACEHOLDER.sub(lambda m: values[m.group(1)], TEMPLATE)
    out = run / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


def main(argv):
    if len(argv) != 2:
        print("usage: build_html.py <run_dir>", file=sys.stderr)
        return 2
    try:
        out = build(argv[1])
    except (OSError, ValueError) as exc:
        print(f"build_html.py: {exc}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
