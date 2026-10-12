#!/usr/bin/env python3
"""Create the starting file for a new item from the name of a branch.

A branch called `review-popeye` gets content/reviews/popeye.md, filled in from
templates/review.md. Used by .github/workflows/new-content.yml; it can also be run by hand:

    python3 scripts/new-content/new_content.py review-the-hurricane

The branch name is untrusted input (anyone who can create a branch picks it), so it is
checked against a strict pattern before it becomes a file name.

Exit status: 0 file written, 1 the name cannot be used (the reason is printed and, in CI,
reported to the person who made the branch), 2 not a content branch (nothing to do).
"""

import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = Path(__file__).resolve().parent / "templates"

# branch prefix -> (content folder, template, front matter type)
KINDS = {
    "review": ("reviews", "review.md", "movie"),
    "dvd": ("reviews", "review.md", "dvd"),
    "chickflick": ("chickflicks", "chickflick.md", None),
    "top5": ("top5", "top5.md", None),
    "other": ("other", "other.md", None),
    "author": ("authors", "author.md", None),
}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SMALL_WORDS = {"a", "an", "and", "at", "for", "in", "of", "on", "or", "the", "to", "vs"}


def title_from(slug):
    words = slug.split("-")
    return " ".join(w if i and w in SMALL_WORDS else w.capitalize() for i, w in enumerate(words))


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    branch = argv[1]
    prefix, _, slug = branch.partition("-")
    if prefix not in KINDS:
        print(f"{branch!r} is not a content branch.")
        return 2
    folder, template, kind_type = KINDS[prefix]
    if not SLUG.match(slug) or len(slug) > 80:
        print(f"Cannot use the branch name {branch!r}: after '{prefix}-' use only lowercase letters, "
              "digits and single hyphens, for example "
              f"'{prefix}-the-hurricane'. Delete the branch and create it again with a name like that.")
        return 1
    target = ROOT / "content" / folder / f"{slug}.md"
    if target.exists():
        print(f"Cannot use the branch name {branch!r}: content/{folder}/{slug}.md already exists. "
              f"If this is a different item with the same title, delete the branch and create it "
              f"again with the author's name on the end, for example '{prefix}-{slug}-greg'.")
        return 1
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    title = title_from(slug)
    text = (text.replace("{{TITLE}}", title)
                .replace("{{DATE}}", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
                .replace("{{TYPE}}", kind_type or ""))
    target.write_text(text, encoding="utf-8")
    print(f"content/{folder}/{slug}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
