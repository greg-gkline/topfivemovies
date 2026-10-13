#!/usr/bin/env python3
"""List the valid `author` values in the comment on the `author` line of each template.

The valid values are the file names (without .md) in content/authors/, apart from _index.
Every template except author.md, which has no `author` field, gets its comment rewritten:

    author: CHANGEME        # one of: brian, bruce, greg, ...

Used by .github/workflows/author-list.yml when a pull request adds an author; it can also be
run by hand:

    python3 scripts/new-content/update_authors.py

Safe to run again: a template that is already current is left alone.
Exit status: 0 always, and the paths of the templates it changed are printed.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORS = ROOT / "content" / "authors"
TEMPLATES = Path(__file__).resolve().parent / "templates"

# `author: <value>`, the padding, then the comment that is replaced
AUTHOR_LINE = re.compile(r"^(author:[ \t]+\S+[ \t]*)#.*$", re.MULTILINE)


def main():
    names = sorted(p.stem for p in AUTHORS.glob("*.md") if p.stem != "_index")
    comment = "# one of: " + ", ".join(names)
    for template in sorted(TEMPLATES.glob("*.md")):
        if template.name == "author.md":
            continue
        text = template.read_text()
        new = AUTHOR_LINE.sub(lambda m: m.group(1) + comment, text)
        if new != text:
            template.write_text(new)
            print(template.relative_to(ROOT))


if __name__ == "__main__":
    main()
