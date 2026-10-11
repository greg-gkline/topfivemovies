#!/usr/bin/env python3
"""Copy the YAML front matter of every content page into OUTDIR/<section>/<name>.yaml.

check-jsonschema and yamllint read plain YAML files, not markdown, so CI validates
these extracts. Line N of an extract is line N+1 of the page.

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


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    errors = 0
    for section in SECTIONS:
        (out / section).mkdir(parents=True, exist_ok=True)
        for page in sorted((ROOT / "content" / section).glob("*.md")):
            try:
                front, _ = split(page)
            except ValueError as e:
                print(e, file=sys.stderr)
                errors += 1
                continue
            (out / section / f"{page.stem}.yaml").write_text(front, encoding="utf-8")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
