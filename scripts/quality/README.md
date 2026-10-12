# Design and quality gates (Phase 3)

Phase 3 rebuilt the markup as semantic HTML and replaced the two legacy stylesheets with a port that looks the same on a desktop browser and also works on a phone. This file records how the CSS is organised, the decisions made while porting it, and the checks that guard it.

```sh
scripts/quality/check.sh                    # clean build, then HTML, accessibility and link checks
scripts/quality/check.sh external           # links to other sites (advisory)
python3 scripts/visual/compare.py           # screenshots against baseline/screenshots/
python3 scripts/visual/compare.py --mobile  # also 390 px wide screenshots
```

## Stylesheets

| File | What it holds |
|---|---|
| `assets/css/common.css` | Design tokens (colours, fonts, type sizes, the arrow), the page frame, header, navigation and footer: the rules both legacy sheets repeated |
| `assets/css/inner.css` | Every page but the home page: the port of `web/styles/elegant_inner.css` |
| `assets/css/home.css` | The home page: the port of `web/styles/elegant.css` |

`head.html` joins `common.css` with the page's own sheet, minifies the result and fingerprints it, so each page loads one stylesheet of about 3.5 KB.

Every colour, font and type size is a custom property on `:root`. The type sizes are the legacy pixel sizes (9–24 px), and the phone layout redefines them (12–26 px), since 11 px body text is too small to read on a phone.

### How the port keeps the look

- **Lengths are the legacy ones.** Element boxes were measured on the legacy pages in the devcontainer, and the grid columns and margins reproduce them. Where a legacy margin collapsed into float clearance (the breadcrumb, section headings, the group bio), the effective value is used, with a comment.
- **Grids replace the float layout:** the item pages (recent additions | item), About Us (origins | authors), author pages (bio | contributions), the home page (poll | featured story and recent additions) and the header. Pictures still float, because text wraps around them.
- **Almost-standards mode.** The legacy XHTML Transitional doctype ran in almost-standards mode, where an image alone on a line has no gap under it. Under the HTML5 doctype such images are `display: block`.
- **`<picture>` is `display: contents`,** so a picture lays out exactly as its `<img>` did, and image borders are `content-box`, outside the width and height attributes, as before. Table cells are `content-box` too.
- **The navigation stays inline:** the spaces between the items are part of the legacy spacing.

### Images redrawn in CSS and SVG

| Legacy image | Now |
|---|---|
| `fadeframe.gif` (the frame around the page top) | `.page::before`: three 1 px lines and a 6 px shadow, faded by a mask. The opacities were sampled from the GIF |
| `grayfade.gif` (side boxes) | A linear gradient at the bottom of the box |
| `smokefadeleft.jpg`, `smokefaderight.jpg` (striped rows) | Linear gradients on the first and last cell |
| `bubble_left/mid/right.gif` (staff responses) | `.bubble`: a rounded, outlined box with a drop shadow, and a tail drawn with two `clip-path` wedges. It grows with long responses, which overflowed the fixed-height GIF |
| `grayarrow.gif` (list bullets) | An SVG data URI in `--arrow`, the same 13 × 20 size, so the bullets sit where they did |
| `maroon_dot.jpg` (poll bars) | An inline `<svg>` per bar, sized by its `width` attribute, so no style attribute is needed |

The banner, the RSS image and the licence badge are still images. Every content and theme picture is served as WebP when that is smaller (339 of 485), with the original as the `<img>` fallback, which cuts image bytes by about 55%. Hugo 0.147 cannot encode AVIF, so WebP is the only modern format. Every `<img>` has `width` and `height`, and pictures below the fold load lazily.

### Markup

HTML5 in UTF-8 with `lang`, a viewport meta tag, `header`/`nav`/`main`/`article`/`aside`/`section`/`footer`, and one "Skip to main content" link that appears on focus. That link replaces the legacy hidden skip links, which were `display: none` and so could not be used. Each page has one `h1`: the item title, the section heading, or the site name on the home page (a visually hidden heading on About Us). Dates are `<time>`. Table headings have `scope`. The navigation marks the current section with `aria-current`.

Pictures with `image_alt` in their front matter use it. Most legacy rows had none, and those pictures are marked decorative (`alt=""`), since the title beside each one names the film. Writing alt text for them is content work for a later PR.

### Small screens

Below 740 px everything is one column: the frame goes, the navigation wraps, the item comes before recent additions, the poll follows the featured story, pictures shrink to 40% of the width, and wide tables scroll inside their own box. No page scrolls sideways at 360 px. Links in lists and tables are spaced at least 24 px apart.

## Deliberate differences from the legacy look

- The home page shows the poll's results (Phase 2), and its quote stays as built until the first change, 20 seconds in, so loading the page moves nothing. On a phone the quote keeps room for four lines.
- The author pages' contributions table has 24 px rows. The legacy table was always empty, so there was nothing to match.
- The previous/next links (Phase 2) push the staff responses down.
- `chasing-liberty`, `batman-begins`, `m-night-shyamalan` and `top-5-movies-starring-brad-pitt` are held back from `content/` for later testing. The pages that listed them show other titles in recent additions and the indexes, and the parity diff and spot check report them as missing.

## Screenshot comparison

`scripts/visual/compare.py` serves `public/`, screenshots each page type of `scripts/baseline/screenshots.py` with the same browser settings, and writes, per page, the new screenshot, a diff (changed pixels in red over the faded baseline) and a side-by-side image. It prints the share of pixels that differ. It is a review tool, not a gate: content differences move whole rows, so a percentage alone cannot tell good from bad. `--max-diff` makes it a gate if wanted.

At the end of Phase 3, against the Phase 0 captures: About Us 0.05%, group bio 0.03%, Other feature 1.0%, and 1.4–6.5% elsewhere. Those differences are the held-back content, the previous/next links, the poll results, the filled contributions table and the removed XHTML and intranet links. Against the Phase 2 build, which had the same content, the DVD review, the Other feature and the group bio are pixel-identical, and the other item pages differ by 0.2–4%: the arrow bullets, the bubbles, and the previous/next links (new in Phase 2, now a flex row), whose height moves what follows by a few pixels. The index pages, About Us and the author pages differ more from Phase 2 than from the legacy pages, because Phase 3 corrected where Phase 2 had drifted (table column widths, line heights, spacing).

## Quality gates

`check.sh` builds the site with `--cleanDestinationDir` (stale fingerprinted files in `public/` would otherwise be checked) and runs:

| Check | Tool | Rule |
|---|---|---|
| `html` | Nu HTML Checker (`vnu.jar`) on every page, stylesheet and SVG | Any error or warning fails |
| `a11y` | axe-core in headless Chromium (`a11y.py`), every page at 1280 px and 390 px | WCAG 2.0 and 2.1 A and AA plus axe best practices. At 390 px, WCAG 2.2 AA too. Any violation fails |
| `links` | lychee, offline, with `#fragment` checks | Any broken internal link fails. Absolute `https://www.topfivemovies.com/` URLs (canonical, prev/next) are remapped onto the build and checked too |
| `external` | lychee, online | Advisory. At the end of Phase 3 the only dead link is `http://petty.cjb.net/` in `other/cameron-diaz.md`, kept because content is migrated as-is |

WCAG 2.2 applies only at phone width. Its target-spacing rule (2.5.8) wants links 24 px apart, and the legacy desktop design sets rows of links 22–23 px apart (the index tables, recent additions). The desktop layout keeps the legacy look, and the phone layout, which is new, meets 2.2 in full.

`tools.sh` downloads the pinned tools into `.cache/quality/` (git-ignored) on first use and checks each against its published checksum: vnu-jar 26.9.16 and axe-core 4.13.0 from npm, lychee 0.24.2 from GitHub. The HTML checker needs Java, which the devcontainer installs.

### Lighthouse CI

`lighthouserc.json` runs Lighthouse (mobile emulation) three times on each of seven representative pages and asserts, on the best of the three runs:

- performance ≥ 0.95, accessibility and SEO 1.0, best practices ≥ 0.95;
- no console errors, legible font sizes, LCP ≤ 2 s, CLS ≤ 0.01, TBT ≤ 200 ms (Lighthouse's "good" threshold: a single run on a shared CI runner measured 64 ms on the reviews index, under 4× CPU throttling);
- budgets per page: document 60 KB, CSS 12 KB, JavaScript 6 KB, images 150 KB, total 250 KB, no third-party requests.

Best practices scores 0.96 rather than 1, because the 2001 pictures exist only at their original size and Lighthouse wants 2× images for phone screens. At the end of Phase 3 every page scores 1.0 for performance, accessibility and SEO, and weighs 11–27 KB.

Lighthouse CI needs Node, so it runs in the `validate` workflow (`lighthouse` job), not in `check.sh`. To run it locally with Node installed:

```sh
CHROME_PATH=/usr/bin/chromium npx @lhci/cli@0.15.1 autorun --config=scripts/quality/lighthouserc.json
```

Reports are written to `.cache/lighthouse/`, and the workflow uploads them as an artifact.

### In CI

The `validate` workflow builds once and passes `public/` to three jobs: `html-links` runs `check.sh html links` on the runner's Java, `a11y` runs `check.sh a11y` in the runner's Chrome (Selenium Manager fetches the matching driver), and `lighthouse` runs Lighthouse CI. The `validate` job at the end of the workflow collects them, along with the content checks, into the one required status.

`html-links` runs on every change, since content can break links and markup. `a11y` and `lighthouse` run only when a pull request or push changes the design or the checks: `assets/`, `layouts/`, `static/`, `hugo.yaml`, `scripts/quality/` or the workflow itself (`DESIGN_PATHS` in `validate.yml`). A change to content or data alone skips them, since Hugo's build already fails on a broken `relref` or a missing image. They are skipped jobs, not a path filter on the workflow, so the `validate` check is still satisfied when they do not run.

## Notes for Phase 5

The response-headers policy's CSP must allow `img-src 'self' data:`, for the arrow bullet in the stylesheet. The pages use no inline scripts or style attributes: the home page's quotes are a `<script type="application/json">` data block, which is never executed, and the scripts and the stylesheet carry `integrity` attributes.
