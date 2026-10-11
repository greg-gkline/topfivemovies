#!/usr/bin/env python3
"""Crawl the legacy PHP site and save the parity baseline.

For every page it saves the raw response bytes and the extracted visible text,
and writes a manifest with per-page metadata (status, title, meta tags, images,
internal links, hashes).

Seeds are the navigation pages plus every item ID found in the database, so
items that nothing links to (drafts, orphans) are captured too.

Usage (inside the devcontainer, with the site on localhost:80):
    python3 scripts/baseline/crawl.py [--base http://localhost] [--out baseline]
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

from bs4 import BeautifulSoup

# Static, non-item pages. Item pages and poll archives come from the database.
STATIC_SEEDS = [
    "/index.html",
    "/topfives.html",
    "/reviews.html",
    "/chickflicks.html",
    "/others.html",
    "/about.html",
    "/groupbio.html",
    "/quickstart.html",
    "/poll.php3",
    "/response_search.php3",
    "/rss.php",
    "/index.xml",
    "/robots.txt",
]

# Article.Type -> URL prefix (mirrors getGenericFile in includes/classes.php)
ARTICLE_PREFIX = {"movie": "review", "dvd": "review", "other": "other", "chick": "chickflick"}

CRAWLABLE = re.compile(r"\.(html?|php3?|xml|txt)$|/$")
EXCLUDED = re.compile(r"^/(intra|images|styles|includes)/")


def db_query(sql, args):
    cmd = ["mysql", "-h", args.db_host, "-u", args.db_user, f"-p{args.db_password}",
           "--skip-ssl", "--batch", "--skip-column-names", "-e", sql]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return [line.split("\t") for line in out.splitlines() if line]


def db_seeds(args):
    seeds = []
    for id_, type_ in db_query("SELECT ID_, Type FROM gklinec_top5primary.Article ORDER BY ID_", args):
        seeds.append(f"/{ARTICLE_PREFIX[type_]}_{id_}.html")
    for (id_,) in db_query("SELECT ID_ FROM gklinec_top5primary.Top5 ORDER BY ID_", args):
        seeds.append(f"/topfive_{id_}.html")
    for (id_,) in db_query("SELECT ID_ FROM gklinec_top5primary.Author ORDER BY ID_", args):
        seeds.append(f"/about_{id_}.html")
    for (id_,) in db_query("SELECT ID_ FROM gklinec_poll.poll ORDER BY ID_", args):
        seeds.append(f"/index.html?viewpoll={id_}")
    return seeds


def normalize(url, base_url, current):
    """Resolve a link to a site-relative path+query, or None if it is not a crawlable page."""
    absolute = urllib.parse.urljoin(base_url + current, url.strip())
    parts = urllib.parse.urlsplit(absolute)
    base = urllib.parse.urlsplit(base_url)
    if parts.scheme not in ("http", "https") or parts.netloc != base.netloc:
        return None
    path = parts.path or "/"
    if path == "/":
        path = "/index.html"
    if EXCLUDED.match(path) or not CRAWLABLE.search(path):
        return None
    return path + ("?" + parts.query if parts.query else "")


def filename_for(page):
    """Map '/index.html?viewpoll=3' to 'index.html@viewpoll=3' (flat, filesystem-safe)."""
    name = page.lstrip("/").replace("/", "__")
    return re.sub(r"[^A-Za-z0-9._=@,-]", "_", name.replace("?", "@").replace("&", ","))


def extract_text(soup):
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    lines = (re.sub(r"\s+", " ", line).strip() for line in soup.get_text("\n").splitlines())
    return "\n".join(line for line in lines if line) + "\n"


def meta(soup, name):
    tag = soup.find("meta", attrs={"name": name})
    return tag.get("content") if tag else None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "topfive-baseline/1.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers.get("Content-Type"), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Content-Type"), err.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost")
    ap.add_argument("--out", default="baseline")
    ap.add_argument("--db-host", default="db")
    ap.add_argument("--db-user", default="root")
    ap.add_argument("--db-password", default="devroot")
    ap.add_argument("--max-pages", type=int, default=2000)
    args = ap.parse_args()

    base = args.base.rstrip("/")
    out = Path(args.out)
    (out / "html").mkdir(parents=True, exist_ok=True)
    (out / "text").mkdir(parents=True, exist_ok=True)

    seeds = STATIC_SEEDS + db_seeds(args)
    queue = deque(seeds)
    seen = set(seeds)
    pages = {}

    while queue and len(pages) < args.max_pages:
        page = queue.popleft()
        status, ctype, body = fetch(base + page)
        name = filename_for(page)
        (out / "html" / name).write_bytes(body)

        # Every byte in the legacy content is ASCII; cp1252 is the declared
        # iso-8859-1 as browsers actually interpret it.
        is_xml = page.endswith(".xml") or page.endswith("rss.php")
        soup = BeautifulSoup(body.decode("cp1252", errors="replace"), "xml" if is_xml else "lxml")

        links = []
        if not is_xml:
            for a in soup.find_all("a", href=True):
                target = normalize(a["href"], base, page)
                if target and target not in links:
                    links.append(target)
                if target and target not in seen:
                    seen.add(target)
                    queue.append(target)

        images = [{"src": img.get("src"), "alt": img.get("alt"),
                   "width": img.get("width"), "height": img.get("height")}
                  for img in soup.find_all("img")]
        title = soup.title.get_text(strip=True) if soup.title else None
        description, keywords = meta(soup, "description"), meta(soup, "keywords")
        text = extract_text(soup)
        (out / "text" / (name + ".txt")).write_text(text, encoding="utf-8")

        pages[page] = {
            "file": name,
            "status": status,
            "content_type": ctype,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "seed": page in seeds,
            "title": title,
            "description": description,
            "keywords": keywords,
            "images": images,
            "links": links,
        }
        print(f"{status} {page}", file=sys.stderr)

    manifest = {"base": base, "page_count": len(pages), "pages": dict(sorted(pages.items()))}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(pages)} pages written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
