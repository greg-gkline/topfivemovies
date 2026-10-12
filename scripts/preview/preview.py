#!/usr/bin/env python3
"""Screenshots of the pages a pull request adds or changes, from the built site.

Finds the pages affected by the content and data files that differ from the base commit:
  content/**/*.md       the page itself
  content/images/*      every page whose front matter names the image
  data/responses.yaml   the item pages whose responses changed
  data/polls.yaml       the poll page
  data/quotes.yaml      the home page (the quote rotator)
Serves public/ locally and writes a full-page PNG of each at desktop width and at phone
width, plus summary.md listing them. A page that was not built (a draft) is listed, not
shot. Template and style changes are not content, so they get no preview.

Usage (after `hugo`):
    python3 scripts/preview/preview.py --base origin/main --out preview/
Needs Chromium and Selenium, as scripts/quality/a11y.py does.
"""
import argparse
import base64
import csv
import io
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prose"))
sys.path.insert(0, str(ROOT / "scripts/quality"))
import prose  # noqa: E402
from a11y import make_driver, serve  # noqa: E402

WIDTHS = {"desktop": 1280, "phone": 390}
# The home page's quote rotator picks at random; fix it so a screenshot is repeatable.
SEEDED_RANDOM = """
(() => {
  let s = 20011003;
  Math.random = () => { s = (s * 1103515245 + 12345) % 2147483648; return s / 2147483648; };
})();
"""


def page_paths():
    """{content file: URL path} for every page Hugo knows, from `hugo list all`."""
    out = subprocess.run(["hugo", "list", "all"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    paths = {}
    for row in csv.DictReader(io.StringIO(out)):
        path = urlparse(row["permalink"]).path
        paths[row["path"]] = path + "index.html" if path.endswith("/") else path
    return paths


def changed_files(base):
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", "content", "data"],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return out.split()


def affected_pages(base, paths):
    """[(URL path, why)] in a stable order."""
    pages = {}
    files = changed_files(base)

    def add(page, why):
        pages.setdefault(page, why)

    changed = prose.changed_lines(base)
    for path in files:
        if path.endswith(".md") and path in paths:
            add(paths[path], path)
        elif path.startswith("content/images/"):
            name = Path(path).name
            for md, page in paths.items():
                if md.endswith(".md") and re.search(rf"^image(_full)?:\s*['\"]?{re.escape(name)}['\"]?\s*$",
                                                    (ROOT / md).read_text(encoding="utf-8"), re.M):
                    add(page, f"{path} (image)")
    # Responses are attached to a page by `item:`; find the entries whose lines changed.
    if "data/responses.yaml" in changed:
        item = None
        for number, line in enumerate((ROOT / "data/responses.yaml").read_text(encoding="utf-8").split("\n"), 1):
            m = re.match(r"- item:\s*(\S+)", line)
            if m:
                item = m.group(1)
            if number in changed["data/responses.yaml"] and item and f"content/{item}.md" in paths:
                add(paths[f"content/{item}.md"], "data/responses.yaml")
    if "data/polls.yaml" in changed and "content/polls.md" in paths:
        add(paths["content/polls.md"], "data/polls.yaml")
    if "data/quotes.yaml" in changed:
        add("/index.html", "data/quotes.yaml")
    return sorted(pages.items())


def shot(driver, url, path, width):
    # Emulated, since headless Chrome will not size a window below about 500px.
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 740})
    driver.get(url)
    driver.execute_script(
        "return Promise.all([...document.images].filter(i => !i.complete)"
        ".map(i => new Promise(r => { i.onload = i.onerror = r; })))")
    data = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
    path.write_bytes(base64.b64decode(data["data"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="the commit the pull request branches from")
    ap.add_argument("--public", type=Path, default=ROOT / "public")
    ap.add_argument("--out", type=Path, default=ROOT / "preview")
    ap.add_argument("--max-pages", type=int, default=20)
    args = ap.parse_args()

    pages = affected_pages(args.base, page_paths())
    args.out.mkdir(parents=True, exist_ok=True)
    lines, shots, skipped, over = [], [], [], []
    for page, why in pages:
        if not (args.public / page.lstrip("/")).exists():
            skipped.append((page, why))
        elif len(shots) >= args.max_pages:
            over.append(page)
        else:
            shots.append((page, why))

    if shots:
        server = serve(args.public)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        driver = make_driver()
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": SEEDED_RANDOM})
            for page, why in shots:
                stem = page.strip("/").removesuffix(".html").replace("/", "__") or "index"
                for label, width in WIDTHS.items():
                    shot(driver, base + page, args.out / f"{stem}.{label}.png", width)
                lines.append(f"| `{page}` | `{why}` | `{stem}.desktop.png`, `{stem}.phone.png` |")
                print(f"{page}  ({why})")
        finally:
            driver.quit()
            server.shutdown()

    summary = []
    if lines:
        summary += ["| Page | Changed by | Images |", "|---|---|---|", *lines]
    else:
        summary.append("No built page is affected by the content and data in this pull request.")
    if over:
        summary.append(f"\nOnly the first {args.max_pages} pages were shot. Not shot: "
                       + ", ".join(f"`{p}`" for p in over) + ".")
    if skipped:
        summary.append("\nNot built (drafts): " + ", ".join(f"`{p}`" for p, _ in skipped) + ".")
    (args.out / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"{len(shots)} page(s) shot, {len(skipped)} not built.")


if __name__ == "__main__":
    main()
