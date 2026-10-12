# Hugo site and parity diff (Phase 2)

The site is built by Hugo from `content/`, `data/`, `layouts/` and `assets/`. This file records how the templates are organised, the decisions made while building them, and the parity check against the legacy site.

```sh
hugo --gc --panicOnWarning           # build into public/
hugo server                          # preview on localhost:1313
python3 scripts/parity/parity.py     # every legacy page's text is in public/ (run after a build)
python3 scripts/export/spotcheck.py  # field-by-field comparison of the content (Phase 1)
scripts/content/validate.sh          # schemas, YAML lint, cross-references
```

Hugo is pinned to **0.147.9 extended**, in `.github/workflows/site.yml` and `.devcontainer/devcontainer.json`, and `hugo.yaml` requires at least that version. The templates use the template layout introduced in 0.146 (`layouts/_partials/`, `layouts/<type>/page.html`), so Debian's older Hugo package cannot build the site. Two builds of the same commit are byte-identical.

## Addresses

`uglyURLs` publishes every item at its filename: `content/reviews/the-hurricane.md` is `/reviews/the-hurricane.html`. Sections are `/reviews.html`, `/chickflicks.html`, `/other.html`, `/top5.html` and `/authors.html` (About Us). The standalone pages are `/groupbio.html` and `/polls.html`. Also built: `/index.xml` (RSS), `/sitemap.xml`, `/robots.txt` and `/404.html`.

Content images are published at `/content/images/<name>`, with a WebP copy beside each where it is smaller; theme images at `/images/<name>`. The CSS and JavaScript are fingerprinted, with `integrity` attributes.

## Templates

| Page | Layout |
|---|---|
| Movie and DVD reviews, chick flicks | `movie/page.html`, `dvd/page.html`, `chickflicks/page.html`, all through `_partials/review.html` |
| Other features, top-five lists, authors | `other/page.html`, `top5/page.html`, `authors/page.html` |
| Index pages | `<section>/section.html`; About Us is `authors/section.html` |
| Home | `home.html`, RSS `home.rss.xml` |
| Group bio, poll archive | `groupbio.html`, `polls.html`, chosen by `layout:` in `content/groupbio.md` and `content/polls.md` |

All pages share `baseof.html` (header, navigation, footer). Phase 3 moved the markup to semantic HTML and replaced the legacy stylesheets with `assets/css/common.css`, `inner.css` and `home.css`; see `scripts/quality/README.md`.

The copy that the legacy templates hard-coded is now content, so the spelling and grammar checks will cover it: each section's introduction is its `_index.md`, About Us's teaser is `content/authors/_index.md`, and the group bio is `content/groupbio.md`, laid out with the `origins` and `member` shortcodes. Their front matter is checked by `scripts/content/schemas/section.json` and `page.json`.

## Behaviour decided while building

- **Order.** Every list, "recent additions", the previous/next links and the featured story use one order: date, then filename (`_partials/ordered.html`). Index pages list newest first.
- **Featured story:** the newest movie review. The legacy page picked a random one of the ten newest each day.
- **Recent additions:** the five newest movie reviews and chick flicks, and the five newest top-five lists, as on the legacy site. DVD reviews and other features were not included there and still are not.
- **The Reviews index includes DVD reviews.** The legacy index listed only `movie` reviews, so the six DVD reviews were reachable only by URL.
- **Sorting.** The legacy `?order=` links become column buttons added by `assets/js/sort-table.js`, with the same directions (title, author A–Z, rating and date high to low). Without JavaScript the table stays newest first.
- **Previous/next:** within the section, shown under each item and as `<link rel="prev/next">`. Authors have none.
- **Excerpts** (meta description, featured story, RSS) follow the legacy `generatePreview()`: the plain text up to the first full stop after *length* − 10 characters, then `...`. 300 characters for the meta description, 350 elsewhere.
- **Keywords:** the site's four, then the item's title and cast (or a top-five list's entries). Index pages and the home page join those of their five newest items.
- **Author pages** list the author's contributions, newest first. The baseline shows that table empty, because the legacy query needs a temporary table the devcontainer's read-only user could not create; the new table shows what the query intended.
- **The staff account** (`the-topfivemovies-staff`) has `listed: false`, which keeps it off About Us, as the legacy page did by its ID.
- **Subtitles** show on the three reviews that have one. The legacy review template never printed them.
- **Polls:** the home page shows the newest poll's final results, linking to the archive of all 14. Percentages truncate as before.
- **Quotes:** `data/quotes.yaml` is inlined in the home page as JSON. `assets/js/quotes.js` shows a random quote on load, then a new one every 20 seconds, with no repeats until all have been shown, and it pauses while the tab is hidden or the visitor prefers reduced motion. The page is built with one quote already in place, picked by hashing the date of the newest content, so the page is never empty without JavaScript.
- **Footer:** the XHTML validator link and the intranet lock are gone. The Creative Commons and RSS links remain.
- **Feed:** RSS 2.0 with the 20 newest items, authors as `dc:creator`. Its dates are those of the newest item, not the build time, so the output stays deterministic.
- **Not carried over:** `quickstart.html` (the web host's "coming soon" page, not site content), `poll.php3`, `response_search.php3` and `rss.php`.

## Parity diff

The parity diff is a cutover tool: run it by hand while verifying the new site, and again on the staging hostname before the DNS switch (Phase 7). It is not a CI check, because once the site is live, new content makes it diverge from the legacy baseline.

`parity.py` matches each of the 181 baseline pages with its replacement and checks that every line of the legacy page's visible text (`baseline/text/`) appears in the new page's visible text. Sort variants (`?order=`) map to their index page, and the `?viewpoll=` pages to the home page, which is what they rendered. Order and markup are not compared, since `spotcheck.py` already compares every field with its formatting.

Expected differences are listed in the script with the reason for each:

- pages not carried over (above), and the draft `other_15`;
- the "xhtml 1.0" and "View results w/o voting" links;
- the hidden "skip navigation"-style links, replaced in Phase 3 by one "Skip to main content" link and landmarks;
- the home page's featured story, since the baseline captured that day's random pick.

With every legacy item in `content/`, it checks 12,549 lines on 169 pages and finds nothing missing. A changed rating or byline in one built page is reported.
