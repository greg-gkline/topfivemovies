#!/usr/bin/env python3
"""Take full-page screenshots of the legacy site, one or more per page type.

Uses headless Chromium through Selenium. Math.random is replaced with a seeded
generator before any page script runs, so the home page quote rotator shows the
same quote on every run.

Usage (inside the devcontainer, with the site on localhost:80):
    python3 scripts/baseline/screenshots.py [--base http://localhost] [--out baseline/screenshots]
    python3 scripts/baseline/screenshots.py --all --out /tmp/all-shots   # every page in the manifest
"""

import argparse
import base64
import json
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# name -> path. One entry per page type, plus variants that exercise
# different layouts (responses, table-based bios, drafts).
PAGES = {
    "home": "/index.html",
    "home-poll-archive": "/index.html?viewpoll=1",
    "reviews-index": "/reviews.html",
    "topfives-index": "/topfives.html",
    "chickflicks-index": "/chickflicks.html",
    "others-index": "/others.html",
    "about-index": "/about.html",
    "groupbio": "/groupbio.html",
    "quickstart": "/quickstart.html",
    "review-movie": "/review_67.html",
    "review-movie-with-responses": "/review_21.html",
    "review-dvd": "/review_47.html",
    "topfive": "/topfive_62.html",
    "topfive-with-responses": "/topfive_27.html",
    "chickflick": "/chickflick_69.html",
    "other": "/other_51.html",
    "other-with-responses": "/other_7.html",
    "other-draft": "/other_15.html",
    "author": "/about_3.html",
    "author-table-bio": "/about_6.html",
}

SEEDED_RANDOM = """
(() => {
  let s = 20011003;
  Math.random = () => { s = (s * 1103515245 + 12345) % 2147483648; return s / 2147483648; };
})();
"""


def make_driver(width, height):
    opts = webdriver.ChromeOptions()
    opts.binary_location = "/usr/bin/chromium"
    for arg in ("--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1", f"--window-size={width},{height}"):
        opts.add_argument(arg)
    driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": SEEDED_RANDOM})
    return driver


def screenshot(driver, url, path):
    driver.get(url)
    driver.execute_script(
        "return Promise.all([...document.images].filter(i => !i.complete)"
        ".map(i => new Promise(r => { i.onload = i.onerror = r; })))")
    shot = driver.execute_cdp_cmd("Page.captureScreenshot",
                                  {"format": "png", "captureBeyondViewport": True})
    path.write_bytes(base64.b64decode(shot["data"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost")
    ap.add_argument("--out", default="baseline/screenshots")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--all", action="store_true", help="screenshot every page in the manifest")
    ap.add_argument("--manifest", default="baseline/manifest.json")
    args = ap.parse_args()

    pages = PAGES
    if args.all:
        manifest = json.loads(Path(args.manifest).read_text())
        pages = {v["file"]: p for p, v in manifest["pages"].items()
                 if v["status"] == 200 and "html" in (v["content_type"] or "")}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    driver = make_driver(args.width, args.height)
    try:
        for name, path in pages.items():
            screenshot(driver, args.base.rstrip("/") + path, out / f"{name}.png")
            print(f"{name}.png  {path}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
