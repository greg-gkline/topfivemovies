#!/usr/bin/env python3
"""Copy the YAML front matter of every content page into OUTDIR for validation.

Items go to OUTDIR/<section>/<name>.yaml, section pages (content/<section>/_index.md)
to OUTDIR/sections/<section>.yaml, and the pages at the top of content/ to
OUTDIR/pages/<name>.yaml. check-jsonschema and yamllint read plain YAML files, not
markdown, so CI validates these extracts. Line N of an extract is line N+1 of the page.

Usage: python3 scripts/content/front_matter.py OUTDIR
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = ["reviews", "chickflicks", "other", "top5", "authors"]


def split(path):
    """Return (front matter, body) of a page, or raise ValueError."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: must start with a '---' line")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise ValueError(f"{path}: front matter is not closed with a '---' line")
    return text[4:end + 1], text[end + 5:]


def pages():
    """Yield (page, extract path relative to OUTDIR) for every content page."""
    for section in SECTIONS:
        for page in sorted((ROOT / "content" / section).glob("*.md")):
            if page.name == "_index.md":
                yield page, Path("sections", f"{section}.yaml")
            else:
                yield page, Path(section, f"{page.stem}.yaml")
    for page in sorted((ROOT / "content").glob("*.md")):
        yield page, Path("pages", f"{page.stem}.yaml")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    errors = 0
    for directory in [*SECTIONS, "sections", "pages"]:
        (out / directory).mkdir(parents=True, exist_ok=True)
    for page, extract in pages():
        try:
            front, _ = split(page)
        except ValueError as e:
            print(e, file=sys.stderr)
            errors += 1
            continue
        (out / extract).write_text(front, encoding="utf-8")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
