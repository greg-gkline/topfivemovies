#!/usr/bin/env python3
"""Screenshot comparison: the Hugo build against the Phase 0 captures.

Serves public/ on a local port, screenshots the replacement of every page in
scripts/baseline/screenshots.py's PAGES with the same browser settings, and compares
each with baseline/screenshots/. For each page it writes the new screenshot, a diff
image (changed pixels in red over a faded copy of the baseline) and a side-by-side
image, and prints the share of pixels that differ.

The comparison is for review by eye, not a pass/fail gate: the new pages are meant to
look the same, but text wraps a pixel differently, the featured story differs by
design, and so on. --max-diff turns it into a gate for a percentage you choose.

Also takes screenshots at phone width (--mobile) for the responsive layout, which
has no baseline.

Usage (after `hugo`):
    python3 scripts/visual/compare.py                 # writes to /tmp/visual by default
    python3 scripts/visual/compare.py --out DIR --only review-movie,home
    python3 scripts/visual/compare.py --mobile        # also 390 px wide shots
"""

import argparse
import functools
import http.server
import sys
import threading
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/baseline"))
sys.path.insert(0, str(ROOT / "scripts/parity"))
import base64  # noqa: E402

from screenshots import PAGES, make_driver  # noqa: E402
from parity import legacy_targets, Exporter  # noqa: E402

# Baseline pages with no replacement to compare.
SKIP = {
    "quickstart": "not carried over",
    "other-draft": "draft, not published",
    "home-poll-archive": "rendered the home page; the poll archive is now /polls.html",
}

# The new page that replaces a baseline page whose path parity.py does not map.
EXTRA = {"home-poll-archive-new": "polls"}


def new_paths():
    """name -> path in the new site, for each baseline screenshot."""
    targets = legacy_targets(Exporter())
    out = {}
    for name, legacy in PAGES.items():
        if name in SKIP:
            continue
        key = legacy.lstrip("/").replace("?", "@")
        target = targets[key]
        out[name] = "/" + ("index" if target == "index" else target) + ".html"
    return out


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def screenshot(driver, url, path):
    """A full-page screenshot once every image has loaded, lazy ones included."""
    driver.get(url)
    driver.execute_script(
        "document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; });"
        "return Promise.all([...document.images].filter(i => !i.complete)"
        ".map(i => new Promise(r => { i.onload = i.onerror = r; })))")
    shot = driver.execute_cdp_cmd("Page.captureScreenshot",
                                  {"format": "png", "captureBeyondViewport": True})
    path.write_bytes(base64.b64decode(shot["data"]))


def serve(directory):
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def compare(old_path, new_path, out_dir, name):
    """Write diff and side-by-side images; return the share of pixels that differ."""
    old = Image.open(old_path).convert("RGB")
    new = Image.open(new_path).convert("RGB")
    width, height = max(old.width, new.width), max(old.height, new.height)
    canvas_old = Image.new("RGB", (width, height), "white")
    canvas_old.paste(old)
    canvas_new = Image.new("RGB", (width, height), "white")
    canvas_new.paste(new)

    mask = ImageChops.difference(canvas_old, canvas_new).convert("L").point(lambda v: 255 if v > 24 else 0)
    changed = mask.histogram()[255]

    faded = Image.blend(canvas_old, Image.new("RGB", (width, height), "white"), 0.7)
    faded.paste(Image.new("RGB", (width, height), (230, 0, 0)), mask=mask)
    faded.save(out_dir / f"{name}.diff.png")

    side = Image.new("RGB", (width * 2 + 10, height), (255, 0, 255))
    side.paste(canvas_old, (0, 0))
    side.paste(canvas_new, (width + 10, 0))
    side.save(out_dir / f"{name}.side.png")
    return 100.0 * changed / (width * height)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--public", type=Path, default=ROOT / "public")
    ap.add_argument("--baseline", type=Path, default=ROOT / "baseline/screenshots")
    ap.add_argument("--out", type=Path, default=Path("/tmp/visual"))
    ap.add_argument("--only", help="comma-separated page names")
    ap.add_argument("--mobile", action="store_true", help="also take 390 px wide screenshots")
    ap.add_argument("--max-diff", type=float, help="exit non-zero if any page differs by more (percent)")
    args = ap.parse_args()

    pages = new_paths()
    pages.update({name: f"/{path}.html" for name, path in EXTRA.items()})
    if args.only:
        wanted = set(args.only.split(","))
        pages = {k: v for k, v in pages.items() if k in wanted}
    args.out.mkdir(parents=True, exist_ok=True)

    server = serve(args.public)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    worst = 0.0
    try:
        driver = make_driver(1280, 900)
        try:
            for name, path in list(pages.items()):
                if not (args.public / path.lstrip("/")).exists():
                    print(f"  missing {name:28} {path} was not built (content held back?)")
                    del pages[name]
                    continue
                shot = args.out / f"{name}.png"
                screenshot(driver, base + path, shot)
                old = args.baseline / f"{name}.png"
                if old.exists():
                    pct = compare(old, shot, args.out, name)
                    worst = max(worst, pct)
                    print(f"{pct:6.2f}%  {name:30} {path}")
                else:
                    print(f"   new   {name:30} {path}")
        finally:
            driver.quit()

        if args.mobile:
            driver = make_driver(1280, 900)
            # Emulated, since headless Chrome will not size a window below about 500px.
            driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
            try:
                for name, path in pages.items():
                    screenshot(driver, base + path, args.out / f"{name}.mobile.png")
                print(f"mobile screenshots of {len(pages)} pages in {args.out}")
            finally:
                driver.quit()
    finally:
        server.shutdown()

    for name, reason in SKIP.items():
        print(f"  skip   {name}: {reason}")
    print(f"output in {args.out}")
    if args.max_diff is not None and worst > args.max_diff:
        sys.exit(1)


if __name__ == "__main__":
    main()
