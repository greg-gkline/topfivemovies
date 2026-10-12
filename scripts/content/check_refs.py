#!/usr/bin/env python3
"""Check the references between content files, which JSON Schema cannot see.

- Page filenames are lowercase slugs (apart from each section's _index.md).
- Every `author` (pages and data/responses.yaml) names a page in content/authors/.
- Every response `item` names an existing page.
- Every relref in a page body names an existing page, section page (_index.md) or
  top-level page (content/<name>.md).
- Every image reference resolves to a file in content/images/, and every file in
  content/images/ is referenced. Names there are unique ignoring case.

Usage: python3 scripts/content/check_refs.py
"""

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from front_matter import ROOT, SECTIONS, split  # noqa: E402

CONTENT = ROOT / "content"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RELREF = re.compile(r'{{<\s*relref\s+"([^"]+)"\s*>}}')
IMAGE_FIELDS = ("image", "image_full")


def main():
    errors = []
    pages = {}   # "section/name" -> front matter
    bodies = {}
    others = set()   # section pages ("section/_index") and top-level pages ("name")

    def read(path, key):
        try:
            front, body = split(path)
            front = yaml.safe_load(front) or {}
        except ValueError as e:   # also an impossible date
            errors.append(f"{path.relative_to(CONTENT)}: {e}")
            return None
        except yaml.YAMLError as e:
            errors.append(f"{path.relative_to(CONTENT)}: invalid front matter: {e}")
            return None
        bodies[key] = body
        return front

    for section in SECTIONS:
        for path in sorted((CONTENT / section).iterdir()):
            rel = path.relative_to(CONTENT)
            if path.name == "_index.md":
                if read(path, f"{section}/_index") is not None:
                    others.add(f"{section}/_index")
                continue
            if path.suffix != ".md" or not SLUG.match(path.stem):
                errors.append(f"{rel}: page filenames must be lowercase-slug.md")
                continue
            front = read(path, f"{section}/{path.stem}")
            if front is not None:
                pages[f"{section}/{path.stem}"] = front
    for path in sorted(CONTENT.glob("*.md")):
        if not SLUG.match(path.stem):
            errors.append(f"{path.relative_to(CONTENT)}: page filenames must be lowercase-slug.md")
        elif read(path, path.stem) is not None:
            others.add(path.stem)

    authors = {p.split("/", 1)[1] for p in pages if p.startswith("authors/")}
    referenced = {}
    for page, front in pages.items():
        if "author" in front and front["author"] not in authors:
            errors.append(f"{page}: unknown author {front['author']!r}")
        for field in IMAGE_FIELDS:
            if front.get(field):
                referenced.setdefault(front[field], page)

    for page, body in bodies.items():
        for target in RELREF.findall(body):
            if target.removesuffix(".md").lstrip("/") not in pages.keys() | others:
                errors.append(f"{page}: relref to missing page {target!r}")

    responses = yaml.safe_load((ROOT / "data/responses.yaml").read_text(encoding="utf-8")) or []
    for n, r in enumerate(responses, 1):
        if r.get("item") not in pages:
            errors.append(f"data/responses.yaml entry {n}: unknown item {r.get('item')!r}")
        if r.get("author") not in authors:
            errors.append(f"data/responses.yaml entry {n}: unknown author {r.get('author')!r}")

    images = {p.name for p in (CONTENT / "images").iterdir() if p.is_file()}
    for name, page in sorted(referenced.items()):
        if name not in images:
            errors.append(f"{page}: image {name!r} is not in content/images/")
    for name in sorted(images - set(referenced)):
        errors.append(f"content/images/{name}: not referenced by any page")
    seen = {}
    for name in sorted(images):
        if name.lower() in seen:
            errors.append(f"content/images/{name}: same name as {seen[name.lower()]} ignoring case")
        seen[name.lower()] = name

    for e in errors:
        print(e, file=sys.stderr)
    print(f"{len(pages)} pages, {len(responses)} responses, {len(images)} images: "
          f"{len(errors)} problems")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
