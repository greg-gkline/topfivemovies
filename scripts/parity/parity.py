#!/usr/bin/env python3
"""Parity diff: check that the text of every legacy page is present in the new site.

Each page captured in baseline/ (Phase 0) is matched with the page of the Hugo build
that replaces it, and every line of its visible text (baseline/text/, one text node
per line) must appear in the new page's visible text. Order and markup are not
compared: scripts/export/spotcheck.py already compares every field with its
formatting. This check catches what the templates drop: a missing byline, response,
navigation label or list entry.

Legacy pages that have no counterpart, and text that was removed on purpose, are
listed below with the reason. Anything else that is missing is a failure.

Usage: hugo && python3 scripts/parity/parity.py [--public DIR] [-v]
Exits non-zero if any legacy text is missing from the new output.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/export"))
from export import Exporter  # noqa: E402

BASELINE = ROOT / "baseline"

# Legacy pages with no counterpart in the new site.
NOT_CARRIED_OVER = {
    "quickstart.html": "the web host's 'coming soon' placeholder page, not site content",
    "poll.php3": "voting endpoint; voting is retired (it only showed 'reached this page in error')",
    "response_search.php3": "response search is dropped",
    "rss.php": "the script that regenerated index.xml; the feed is now built by Hugo",
    "index.xml": "RSS feed, regenerated from the content (its items are checked as pages)",
    "robots.txt": "rewritten for the new site; it listed directories that no longer exist",
    "top5.php3@id=49": "404 in the legacy site; the link that pointed here now resolves",
}

# Text removed from every page on purpose: exact line -> reason.
REMOVED_LINES = {
    "xhtml 1.0": "XHTML validator link; the pages are HTML5 now",
    "View results w/o voting": "voting is retired; the home page shows the latest results",
}
# The legacy pages had hidden "skip" links before each block (display: none, so no one
# could use them). Phase 3 replaced them with one "Skip to main content" link and landmarks.
SKIP_LINKS = "hidden skip link; replaced by one 'Skip to main content' link and landmarks"
REMOVED_LINES.update({line: SKIP_LINKS for line in (
    "skip navigation", "skip recent additions", "skip poll", "skip featured story",
    "Go to Featured Story")})

# Text removed from one page on purpose: (legacy page, exact line) -> reason.
# The home page's featured story was a random recent review chosen each day; it is
# now the newest movie review, so the 2026-10-11 baseline's pick is not expected.
HOME_FEATURE = "featured story is now the newest movie review, not the day's random pick"


def extract_lines(html):
    """Visible text, one line per text node: the same extraction as scripts/baseline/crawl.py."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    lines = (re.sub(r"\s+", " ", line).strip() for line in soup.get_text("\n").splitlines())
    return [line for line in lines if line]


def legacy_targets(exp):
    """Map each legacy page (baseline filename) to its new output file, or to a reason."""
    targets = {}
    for ident, path in exp.article_path.items():
        prefix = {"movie": "review", "dvd": "review", "chick": "chickflick", "other": "other"}[
            exp.articles[ident]["Type"]]
        targets[f"{prefix}_{ident}.html"] = path
    for ident, path in exp.top5_path.items():
        targets[f"topfive_{ident}.html"] = path
    for ident, slug in exp.author_slug.items():
        targets[f"about_{ident}.html"] = f"authors/{slug}"
    index_pages = {
        "index.html": "index", "reviews.html": "reviews", "chickflicks.html": "chickflicks",
        "others.html": "other", "topfives.html": "top5", "about.html": "authors",
        "groupbio.html": "groupbio",
    }
    targets.update(index_pages)
    # Sort variants (?order=) list the same rows; the poll archive pages (?viewpoll=)
    # rendered the home page, since the parameter never took effect.
    for name in json.loads((BASELINE / "manifest.json").read_text())["pages"].values():
        base, _, query = name["file"].partition("@")
        if query and base in index_pages:
            targets[name["file"]] = index_pages[base]
    return targets


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--public", type=Path, default=ROOT / "public", help="Hugo output directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="list every page checked")
    args = parser.parse_args()

    exp = Exporter()
    targets = legacy_targets(exp)
    drafts = {path for ident, path in exp.article_path.items() if exp.articles[ident]["QA"] == 0}
    drafts |= {path for ident, path in exp.top5_path.items() if exp.top5s[ident]["QA"] == 0}

    failures = 0
    home_feature = set()

    manifest = json.loads((BASELINE / "manifest.json").read_text())["pages"]
    pages = sorted(p["file"] for p in manifest.values() if p["status"] == 200)
    checked = lines_checked = 0
    for name in pages:
        if name in NOT_CARRIED_OVER:
            print(f"skip  {name}: {NOT_CARRIED_OVER[name]}")
            continue
        if name not in targets:
            print(f"FAIL  {name}: no counterpart in the new site")
            failures += 1
            continue
        target = targets[name]
        if target in drafts:
            print(f"skip  {name}: draft ({target}), not published")
            continue
        new_file = args.public / f"{target}.html"
        if not new_file.exists():
            print(f"FAIL  {name}: {new_file.relative_to(args.public)} was not built")
            failures += 1
            continue

        new_text = " ".join(extract_lines(new_file.read_text(encoding="utf-8")))
        legacy = (BASELINE / "text" / f"{name}.txt").read_text(encoding="utf-8").splitlines()
        if target == "index" and not home_feature:
            home_feature = feature_lines(legacy)
        missing = []
        for line in legacy:
            if (line in new_text or line in REMOVED_LINES
                    or (target == "index" and line in home_feature)):
                continue
            missing.append(line)
        checked += 1
        lines_checked += len(legacy)
        if missing:
            failures += 1
            print(f"FAIL  {name} -> {target}.html: {len(missing)} of {len(legacy)} lines missing")
            for line in missing:
                print(f"        {line}")
        elif args.verbose:
            print(f"ok    {name} -> {target}.html ({len(legacy)} lines)")

    print(f"\n{checked} pages, {lines_checked} lines checked: {failures} pages with missing text")
    print("Removed on purpose everywhere: " + "; ".join(f"{k!r} ({v})" for k, v in REMOVED_LINES.items()))
    print(f"Home page: {HOME_FEATURE}")
    sys.exit(1 if failures else 0)


def feature_lines(legacy):
    """The lines of the legacy home page's featured story (from its heading to 'Read more...')."""
    try:
        start = legacy.index("skip featured story") + 1
        end = legacy.index("Read more...", start)
    except ValueError:
        return set()
    return set(legacy[start:end])


if __name__ == "__main__":
    main()
