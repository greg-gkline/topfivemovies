"""Shared helpers for the prose checks (spelling.py, grammar.py).

prose_lines(path) returns the file's prose with every other line blanked, so line N of
the result is line N of the file and a finding can be reported against the original.
  content/**/*.md   the markdown body, plus the prose fields of the front matter:
                    text (top-five items, honorable mentions), caption and subtitle
  data/responses.yaml  text
  data/polls.yaml      question
data/quotes.yaml is not checked: those are film lines, quoted verbatim.

changed_lines(base) returns the lines a pull request adds or changes, per file, so a
check can ignore errors that were already there. Content was migrated as-is, and a fix
to one sentence of a legacy review should not have to clear the whole file.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKED = ("content/", "data/")

FRONT_MATTER_PROSE = {"text", "caption", "subtitle"}
DATA_PROSE = {"data/responses.yaml": {"text"}, "data/polls.yaml": {"question"}}

SHORTCODE = re.compile(r"\{\{<.*?>\}\}|\{\{%.*?%\}\}")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
KEY_VALUE = re.compile(r"^\s*(?:- )?([a-z_]+):\s+(.+?)\s*$")


def unquote(value):
    """The text of a one-line YAML scalar."""
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def clean(text):
    """Drop what is markup, not prose: Hugo shortcodes, and link targets."""
    return LINK.sub(r"\1", SHORTCODE.sub("", text))


def prose_lines(path):
    path = str(path)
    lines = (ROOT / path).read_text(encoding="utf-8").split("\n")
    out = [""] * len(lines)
    keys = DATA_PROSE.get(path)
    body_from = 0
    if path.startswith("content/") and lines and lines[0] == "---":
        keys = FRONT_MATTER_PROSE
        end = lines.index("---", 1) if "---" in lines[1:] else len(lines)
        body_from = end + 1
    if keys:
        for i, line in enumerate(lines[:body_from] if body_from else lines):
            m = KEY_VALUE.match(line)
            if m and m.group(1) in keys:
                out[i] = clean(unquote(m.group(2)))
    for i in range(body_from, len(lines)) if path.startswith("content/") else ():
        out[i] = clean(lines[i])
    return out


def changed_lines(base):
    """{path: set of 1-based line numbers added or changed since `base`}, for the
    content and data files that still exist. The diff is against the merge base."""
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", "--diff-filter=AM", f"{base}...HEAD",
         "--", *CHECKED],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout
    result, current = {}, None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            result[current] = set()
        elif line.startswith("@@") and current:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start, count = int(m.group(1)), int(m.group(2) or 1)
            result[current].update(range(start, start + count))
    return {p: ls for p, ls in result.items() if ls and p.endswith((".md", ".yaml"))}


def all_lines():
    """Every line of every checked file, for a full run."""
    files = {}
    for p in sorted((ROOT / "content").rglob("*.md")) + [ROOT / "data/responses.yaml", ROOT / "data/polls.yaml"]:
        rel = str(p.relative_to(ROOT))
        files[rel] = set(range(1, len(p.read_text(encoding="utf-8").split("\n")) + 1))
    return files


def annotation(level, path, line, title, message):
    """A GitHub Actions workflow command, which shows on the PR's changed line."""
    esc = lambda s: s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return f"::{level} file={path},line={line},title={esc(title)}::{esc(message)}"
