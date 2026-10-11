# Legacy site baseline (Phase 0)

A snapshot of the PHP site as served by the devcontainer, captured 2026-10-11. Later phases compare against it: the Phase 2 parity diff uses `text/`, and the Phase 3 visual comparison uses `screenshots/`.

Treat these files as read-only reference. Regenerate them only if the legacy site or its data changes.

## Contents

| Path | What it is |
|---|---|
| `manifest.json` | One entry per crawled URL: status, content type, size, sha256 of the raw body, title, meta description and keywords, `<img>` tags (src, alt, width, height) and internal links. |
| `html/` | Raw response bodies, byte-exact (`-text` in `.gitattributes`, since bodies contain CRLFs from the DB). The query string is folded into the name: `index.html?viewpoll=3` becomes `index.html@viewpoll=3`. |
| `text/` | Visible text of each page, one line per text node, whitespace collapsed, scripts and styles removed. UTF-8. |
| `screenshots/` | Full-page PNGs at 1280 px wide, one or more per page type (see `PAGES` in `scripts/baseline/screenshots.py`). |

## Coverage

181 URLs: 180 return 200, and 1 returns 404.

| Pages | Count |
|---|---|
| `review_N.html` (movie and DVD) | 51 |
| `topfive_N.html` | 62 |
| `other_N.html` (includes the `QA=0` draft `other_15`) | 10 |
| `chickflick_N.html` | 8 |
| `about_N.html` (authors) | 8 |
| `index.html?viewpoll=N` (poll archive) | 14 |
| Index pages, plus their `?order=` sort variants | 5 + 14 |
| Home, group bio, quickstart, `poll.php3`, `response_search.php3`, `rss.php`, `index.xml`, `robots.txt` | 8 |
| Broken legacy link `top5.php3?id=49` | 1 |

The crawl is seeded from the navigation pages plus every ID in the `Article`, `Top5`, `Author` and `poll` tables. Pages that nothing links to are still captured, and links found while crawling are followed. `/intra/` is excluded because it is being retired.

## Things to know when comparing

- **Deterministic.** Two consecutive crawls produce identical hashes, and two screenshot runs produce identical PNGs. The screenshot script seeds `Math.random`, so the home page quote rotator always shows the same first quote.
- **The home page's featured story changes daily.** `selectRandomArticle()` seeds `mt_rand` with the day of the year, so a capture on another day picks a different story. This baseline shows *The Village*.
- **Fonts.** The CSS asks for Bitstream Vera Sans (installed) and Georgia (not available on Linux, so DejaVu Serif renders instead). Compare screenshots taken in the same devcontainer, not against a browser on another OS.
- **Broken in the legacy site, not by the capture:**
  - `topfive_50.html` links to `top5.php3?id=49`, which does not exist (404).
  - `response_search.php3` emits PHP warnings, because `includes/title.inc` and `includes/response.php3` are missing. Search is dropped, so it has no screenshot.
  - `poll.php3` without a vote shows "You have reached this page in error". The poll archive is `index.html?viewpoll=N`.
- **Item URLs aren't checked against the item type.** `review_7.html` renders the "other" article 7 with the review template. The crawl and screenshots use each item's correct prefix, taken from `Article.Type`.

## Regenerating

From the devcontainer, with the site running on `localhost:80`:

```sh
python3 scripts/baseline/crawl.py          # writes html/, text/, manifest.json
python3 scripts/baseline/screenshots.py    # writes screenshots/
python3 scripts/baseline/screenshots.py --all --out /tmp/all-shots   # every page, not committed
```

The tools are installed by `postCreateCommand` in `.devcontainer/devcontainer.json`.
