#!/usr/bin/env python3
"""Accessibility check: run axe-core on every page of the build, in headless Chromium.

Serves the build on a local port, loads each page at desktop and phone width, injects
axe (fetched by tools.sh) and runs the WCAG 2.0 and 2.1 A and AA rules plus axe's best
practices. Any violation fails the check.

At phone width the WCAG 2.2 AA rules apply too. The desktop layout keeps the legacy
design, whose 22-23px rows of links fall just short of 2.2's 24px target spacing
(2.5.8); the phone layout is new, so it meets 2.2 in full.

Usage (check.sh runs it after building):
    source scripts/quality/tools.sh && python3 scripts/quality/a11y.py [--public DIR] [--only PATH,...]
"""

import argparse
import functools
import http.server
import os
import sys
import threading
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

ROOT = Path(__file__).resolve().parents[2]
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]
# label -> (window width, rule tags)
WIDTHS = {"desktop": (1280, TAGS), "phone": (390, TAGS + ["wcag22aa"])}
DEBIAN_CHROMIUM = ("/usr/bin/chromium", "/usr/bin/chromedriver")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def make_driver():
    """Headless Chromium. CHROME_BIN and CHROMEDRIVER choose the browser and driver;
    otherwise the devcontainer's Debian pair, or else Selenium Manager finds Chrome and
    fetches a matching driver (the CI runners)."""
    opts = webdriver.ChromeOptions()
    for arg in ("--headless=new", "--no-sandbox", "--disable-gpu", "--window-size=1280,900"):
        opts.add_argument(arg)
    browser = os.environ.get("CHROME_BIN")
    driver_path = os.environ.get("CHROMEDRIVER")
    if not (browser or driver_path) and all(Path(p).exists() for p in DEBIAN_CHROMIUM):
        browser, driver_path = DEBIAN_CHROMIUM
    if browser:
        opts.binary_location = browser
    service = Service(driver_path) if driver_path else Service()
    return webdriver.Chrome(service=service, options=opts)


def run_axe(driver, axe_source, tags):
    driver.execute_script(axe_source)
    return driver.execute_async_script(
        "const done = arguments[arguments.length - 1];"
        "axe.run(document, {runOnly: {type: 'tag', values: arguments[0]}})"
        ".then(r => done(r.violations.map(v => ({id: v.id, impact: v.impact, help: v.help,"
        " nodes: v.nodes.map(n => n.target.join(' '))}))))"
        ".catch(e => done([{id: 'axe-error', impact: 'critical', help: String(e), nodes: []}]));",
        tags)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--public", type=Path, default=ROOT / "public")
    ap.add_argument("--only", help="comma-separated page paths, such as index.html,reviews.html")
    args = ap.parse_args()

    axe_path = os.environ.get("AXE_JS")
    if not axe_path:
        sys.exit("AXE_JS is not set: source scripts/quality/tools.sh first")
    axe_source = Path(axe_path).read_text(encoding="utf-8")

    pages = sorted(str(p.relative_to(args.public)) for p in args.public.rglob("*.html"))
    if args.only:
        pages = args.only.split(",")

    server = serve(args.public)
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    driver = make_driver()
    driver.set_script_timeout(60)
    failures = 0
    try:
        for label, (width, tags) in WIDTHS.items():
            # Emulated, since headless Chrome will not size a window below about 500px.
            driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 740})
            for page in pages:
                driver.get(base + page)
                for v in run_axe(driver, axe_source, tags):
                    failures += 1
                    print(f"FAIL  {page} ({label}): {v['id']} [{v['impact']}] {v['help']}")
                    for node in v["nodes"][:5]:
                        print(f"        {node}")
    finally:
        driver.quit()
        server.shutdown()

    print(f"\n{len(pages)} pages at {len(WIDTHS)} widths: {failures} violations")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
