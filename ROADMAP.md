# Top Five Movies: Modernization Roadmap

Move `www.topfivemovies.com` from a PHP 5 / MySQL site to a static site: content in YAML, rendered with Hugo, hosted on S3 behind CloudFront, with the infrastructure in Terraform.

## Goals

- No request-time processing. Content is YAML files in git, and the site is static HTML.
- A pull request renders a preview, gets a spelling check, and gets a separate agentic grammar review.
- Merging to `main` rebuilds everything and deploys it.
- Markdown in content is converted to HTML by the template engine.
- Modern, semantic HTML and CSS, visually faithful to the original design.
- Hosting is a private S3 bucket behind CloudFront, managed by Terraform.

## Decisions

| Topic         | Decision                                                                                                                                                                              |
|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Generator     | Hugo (single Go binary, no Node). YAML data, Goldmark markdown, one layout per content type.                                                                                          |
| URLs          | Legacy URLs (`review_N.html`, `topfive_N.html` and so on) are not preserved, since the site has been offline for years. Every item's address follows its filename, with no redirects. |
| Item identity | The filename is the identity (`the-hurricane.md`). There is no `id` field.                                                                                                            |
| Poll          | Read-only archive page. No voting, no cookies.                                                                                                                                        |
| Comments      | Read-only legacy. The 60 existing responses render statically. There is no way to add new ones.                                                                                       |
| Intranet      | `intra/` is fully retired and removed, including basic auth.                                                                                                                          |
| Look          | Inner pages match `styles/elegant_inner.css`. The home page keeps the original `styles/elegant.css` look.                                                                             |
| Domain        | `www.topfivemovies.com`, plus the bare `topfivemovies.com` redirecting to it.                                                                                                         |
| DNS           | Delegate the zone to Route 53 (option A). The domain registrar remains unchanged.                                                                                                     |
| Checks        | Spelling is a deterministic blocking check. Grammar is a separate, agentic, advisory check.                                                                                           |
| Search        | Dropped. The response search page is not carried over.                                                                                                                                |
| Content       | Migrated as-is. No editorial changes or removals.                                                                                                                                     |

## Current state (reference)

- Content: 69 `Article` rows (reviews and DVDs), 62 `Top5`, 8 `Author`, 60 `Response`, 106 `Quote`, plus a `poll` table. The `Image` blob table is empty, so `image.php3` is dead code.
- Pages are `.html` files executed as PHP via `AddHandler`. `.htaccess` rewrites `type_N.html` to `type.html?id=N`.
- Markup is XHTML 1.0 Transitional in latin1. Bodies are raw HTML with `<P>` tags, `<img>` tags are stored inside DB columns, and some author bios use layout tables.
- 8 stylesheets exist. Inner pages use `elegant_inner.css` (float and position layout, GIF/JPG decoration). Only `index.html` uses `elegant.css`.
- Dynamic features: poll voting, response search, the intranet response form, RSS, and a random quote script.

## Target architecture

```
content/*.yaml, data/*.yaml
        |
        v
   hugo build  ---->  public/  ---->  S3 (private)  <--OAC--  CloudFront  <--  Route 53  <--  domain registrar
        ^
   PR: validate, spelling, agentic grammar review, preview
   main: build, sync, invalidate (GitHub Actions + OIDC)
```

## Proposed repo layout

```
content/reviews/0012-the-hurricane.md   # YAML front matter + markdown body
content/{top5,other,chickflicks,authors}/…
content/images/rev_hurricane.jpg        # content images, a peer of the sections above
data/{quotes,responses,polls}.yaml
layouts/          # Hugo templates, one per content type, plus home
assets/           # theme only: CSS (elegant_inner port, elegant port), decorative images, quote script
static/
infra/            # Terraform
scripts/          # exporter, parity and screenshot tooling
legacy/sql/       # original SQL dumps, loaded by the devcontainer; archived at cutover
.github/workflows/
```

---

## Phase 0: Baseline and preparation

- [x] Crawl the devcontainer site and save the rendered HTML and extracted text of every page as the parity baseline. Output is in `baseline/` (see `baseline/README.md`), and the tooling is in `scripts/baseline/`.
- [x] Take full-page screenshots of every page type for the later visual comparison.
- [x] Check git history for leaked credentials. Rotate anything that was real. All DB passwords were already `REDACTED` in the initial commit. The intranet `.htaccess` only references an htpasswd path on the old host, and the dumps contain no emails, IPs or password hashes. Nothing in the repo needs rotating.
- [x] Create the repo skeleton above. The SQL dumps moved from `data/` to `legacy/sql/`, so `data/` is free for Hugo's YAML.

## Phase 1: Content migration (DB to YAML)

- [ ] Write a re-runnable exporter that reads the devcontainer DB or the SQL dumps and writes one YAML file per article, top-five list and author. It runs in the devcontainer (Python or PHP, no Node).
- [ ] Per-type fields:
  - Review and DVD: `type, title, author, date, rating, release_year, starring, caption, image, image_alt`, with the review text as the markdown body.
  - Top five: `title, author, date, image, image_alt, items[5]`, with the intro as the markdown body.
  - Author: `name, jobtitle, image, bio` (markdown or structured fields).
- [ ] Clean data in the exporter:
  - latin1 to UTF-8, with a check for mojibake.
  - `<P>` and raw HTML to markdown.
  - Decode entities such as `&quot;`.
  - Extract `<img>` attributes into structured image fields.
  - Convert the table-based bios (Matt, Brian) to markdown or key/value data.
  - Mark `QA=0` rows as `draft: true`.
- [ ] Separate content images from theme images (see Image organization below), and have the exporter move each content image into `content/images/`.
- [ ] Export `Response` and `poll` rows to `data/*.yaml`.
- [ ] Build `data/quotes.yaml` from **both** quote sources (see Quotes below).
- [ ] Add a JSON Schema per content type and validate in CI with `check-jsonschema` and `yamllint`.
- [ ] Spot-check the export against the legacy pages, with `diff`-style review.

### Image organization

`web/images/` mixes theme images and content images (218 files). Scanning the SQL dumps and the code gives roughly:

- **~134 content images**, referenced from article, top-five and author rows. All move to a single flat `content/images/` folder, a peer of `reviews`, `top5`, `authors` and the other sections, so a PR for a new review adds the `.md` file and its picture under `content/`. Author photos go there too.
- **~21 theme images** referenced from CSS, templates and RSS. These move to `assets/` and are used only by templates.
- **4 referenced from both** (`brian`, `greg`, `matt`, `nick`.jpg), which are author photos also hard-coded in code. They become content images in `content/images/`, and templates reference them through the author's front matter.
- **~67 unreferenced.** They are mostly old "beige" theme sidebars, the splash page pieces, and `test.gif`. Before deleting, confirm they are not used by the two themes we port. Do not trust the scan alone, since image paths can be built dynamically in code.
- **1 reference to a missing file** (`maroon_lines.jpg`) to resolve while porting.
- `lockgray.gif` is only used by the intranet link and goes away with it.

Rules the exporter enforces and CI checks:
- Front matter references images by filename (`image: rev_hurricane.jpg`), never by site path.
- Filenames in `content/images/` are unique by construction, since the folder is flat. The exporter fails on any collision.
- CI fails on any content image reference that does not resolve, and on any file in `content/images/` that nothing references.
- Hugo only publishes non-markdown files in `content/` when they belong to a page bundle, and a flat images folder is not one. So `hugo.yaml` mounts `content/images` into Hugo's asset pipeline (`module.mounts`), and templates load images with `resources.Get`. Hugo then resizes and converts them at build time, so the WebP/AVIF, sizes and `width/height` in Phase 3 come from the originals, with no manual conversion step.
- Only the images that templates request are published, so unused originals add nothing to the output.

### What a content file looks like

Content pages are `.md` files. Each starts with **front matter**: a block of structured YAML fenced by `---` lines that holds the item's fields. The markdown body follows and is converted to HTML by Hugo. Example, `content/reviews/the-hurricane.md`, migrated from the `Article` row for *The Hurricane*:

```markdown
---
type: movie
title: The Hurricane
author: Jesse
date: 2000-10-01
rating: 5
release_year: 1999
starring: Denzel Washington
image: rev_hurricane.jpg
image_alt: Denzel Washington as Rubin "Hurricane" Carter
---

The Hurricane follows the true-life story of champion boxer Rubin "Hurricane"
Carter's wrongful conviction for murder and subsequent jail-cell efforts to
clear his own name.

The story itself is very compelling. A crooked cop frames Carter for a series
of crimes throughout his childhood...
```

An item's address comes from its filename, so `content/reviews/the-hurricane.md` is published as `/reviews/the-hurricane.html`.

- **Filenames:** lowercase slugs of the title, with a year or number suffix when two titles collide. CI fails on duplicates.
- **Ordering and navigation:** the previous/next links, "recent additions" and the featured story are driven by `date` (and filename as a tiebreaker), not by numeric ID. The old `id-1` and `id+1` logic is not carried over.
- **Links between items:** content links to other items by file path (`{{< relref "reviews/the-hurricane.md" >}}`), so Hugo checks them at build time, and a renamed or deleted file fails the build instead of leaving a dead link.
- **Responses:** each legacy response is attached to its item by the item's filename (`item: reviews/the-hurricane`) in `data/responses.yaml`, not by numeric ID.
- The exporter uses the old numeric ID only during migration, to map responses to items and to name the files. It is not stored anywhere in the new site.

### Quotes

Today there are two separate quote sources, and they disagree:

- The rotator on the home page (`includes/quotes.js`) is a **hard-coded array of 111 quotes** that picks one at random every 20 seconds. It does not touch the database.
- The `Quote` table has 106 rows, read only by `includes/quote.php`, which nothing includes. That path is dead code.

So the rotator already works without the database. The work is to put the quotes in one place as data and keep the behavior:

- [ ] Merge both sources into `data/quotes.yaml`, de-duplicated, with fields `text` and `source` (movie). Review the differences once in a PR. The merge decides what the live set is.
- [ ] Quotes with inline HTML (such as `<i>`) become markdown or plain text.
- [ ] At build time, Hugo emits the list as JSON (`quotes.json`, or inlined in the page, which is about 10 KB).
- [ ] Rewrite the rotator as a small ES module with the same behavior: random order with no repeats until all are shown, a new quote every 20 seconds, text inserted with `textContent`. Fix the old issues while doing so: the inline `setTimeout` string, the global variables, and the repeat-check bug in `getRandom`. Pause rotation when the tab is hidden and when the user prefers reduced motion.
- [ ] No-JavaScript fallback: the page is built with one quote already in `#quote`, so it is never empty. Hugo picks it deterministically per build.
- [ ] Remove `quote.php`, `quotes.js` and the `Quote` table with the PHP code in cleanup.

## Phase 2: Hugo site and templates

- [ ] Scaffold Hugo and the layouts for `review`, `dvd`, `top5`, `other`, `chickflick`, `author` and `about`.
- [ ] Build the index pages: reviews, top fives, others, chickflicks, author bios, quickstart and group bio. Add the "recent additions" partial.
- [ ] Build the home page as its own layout. The featured story is chosen deterministically at build time, replacing the old "older than 2 weeks, so pick random" logic.
- [ ] Generate prev/next links, excerpts, keywords and meta descriptions at build time.
- [ ] Output filename-based `.html` addresses, an RSS feed, a sitemap, `robots.txt` and canonical URLs.
- [ ] Replace the request-time features:
  - Quote rotator: see Quotes below.
  - Search: dropped. Remove `response_search.php3` and any links to it.
  - Comments: rendered statically from `data/responses.yaml` under each item.
  - Poll: archive page rendered from `data/polls.yaml`, showing final results.
- [ ] Build the parity diff against the Phase 0 snapshot. Every legacy page's text should be present in the new output.

## Phase 3: Design: faithful look, modern foundation

- [ ] Port `elegant_inner.css` rule by rule for all inner pages. Pull colors and fonts into CSS custom properties.
- [ ] Port `elegant.css` separately for the home page, sharing the common tokens and header.
- [ ] Replace float and position layout mechanics with Grid and Flexbox without changing the appearance.
- [ ] Rebuild the image-based decoration with CSS or SVG where it keeps the look:
  - Gradient fades (`grayfade`, `fadeframe`, `smokefade*`) become CSS gradients.
  - The speech-bubble GIFs become one SVG or CSS shape.
  - The arrow becomes inline SVG.
  - Banners and photos are converted to AVIF/WebP with a JPEG fallback.
- [ ] Semantic HTML5: UTF-8, `lang`, viewport meta, `header/nav/main/article/footer`, a skip link, real `alt` text, and `width/height` with lazy loading.
- [ ] Keep the desktop appearance identical, and add responsive behavior for small screens.
- [ ] Screenshot comparison against the Phase 0 captures for each page type, including the home page.
- [ ] Quality gates: HTML validation (`vnu`), accessibility (pa11y or axe), Lighthouse CI budgets, and a link check (`lychee`).

## Phase 4: PR pipeline

Each item is its own workflow and its own status check.

- [ ] **validate**: schema and YAML lint, Hugo build, HTML validation, link check. Required.
- [ ] **spelling**: `typos` or `codespell` on changed content only, with a project dictionary for actor names, film titles and the site's slang. Inline annotations on the PR. Required.
- [ ] **grammar-review** (agentic, advisory):
  - Runs on PRs that touch `content/**` or `data/**`, and only on same-repo branches because it needs a secret.
  - Uses the Claude Code Action or a small Python script against the Claude API, over the changed prose only, with a cap on files per run.
  - The prompt includes a style guide: the voice is intentionally informal and irreverent, so flag real errors and not tone.
  - Posts an inline review with suggestions, and is not a required check until it has proven useful.
  - Needs an `ANTHROPIC_API_KEY` repo secret.
- [ ] **preview**: build and publish under a per-PR prefix in staging, comment the link on the PR, and clean up when the PR closes.
- [ ] **terraform-plan**: runs on `infra/**` changes and posts the plan as a PR comment.
- [ ] Turn on branch protection requiring `validate`, `spelling` and the Terraform checks.

## Phase 5: Infrastructure (Terraform)

- [ ] Bootstrap stack: remote state in S3 with lockfile locking, pinned providers.
- [ ] S3 bucket: private, Block Public Access, versioning, lifecycle rules.
- [ ] CloudFront: Origin Access Control, HTTPS only, HTTP/3, a response-headers policy (HSTS, CSP, `X-Content-Type-Options`, `Referrer-Policy`), a CloudFront Function for `index.html` handling, and a custom 404.
- [ ] Redirect from `topfivemovies.com` to `https://www.topfivemovies.com` (a CloudFront Function, with the apex also on the distribution).
- [ ] ACM certificate in `us-east-1` covering `www.topfivemovies.com` and `topfivemovies.com`, validated by DNS records Terraform creates in Route 53.
- [ ] Route 53 hosted zone for `topfivemovies.com`, with alias records for `www` and the apex pointing to CloudFront (A and AAAA).
- [ ] GitHub OIDC provider and a least-privilege deploy role limited to the bucket sync and CloudFront invalidations. No long-lived AWS keys.
- [ ] Separate `staging` and `prod` environments.
- [ ] Terraform checks in CI: `fmt`, `validate`, `tflint`, `checkov`.
- [ ] Optional: a budget alert and CloudFront error-rate alarm.

## Phase 6: Deploy on merge to `main`

- [ ] Full Hugo build. The site is small, so a full build is fast and avoids stale-output bugs, and template and content changes use the same path.
- [ ] `aws s3 sync --delete`, with long immutable caching on fingerprinted assets and short caching on HTML.
- [ ] Invalidate changed paths, or `/*` when templates or CSS changed.
- [ ] Post-deploy smoke test against the live URL.
- [ ] Rollback by redeploying the previous commit.

## Phase 7: DNS migration and cutover

DNS delegation is the riskiest step. Do it only after the site is verified on a staging hostname.

The current zone has no records beyond the registrar's domain parking, so there is no mail or verification setup to preserve. The parking records are replaced by the new site and are not recreated.

**Before touching registrar**
- [ ] Confirm the zone holds only the parking configuration (check with `dig` for A, AAAA, CNAME, MX, TXT and NS on the apex and `www`).
- [ ] Confirm DNSSEC is **off** at the registrar. If it is on, it must be disabled first or the domain will fail validation after the move.
- [ ] Disable parking at the registrar when switching the nameservers, if it does not release automatically.

**Verify**
- [ ] Query the new Route 53 nameservers directly and confirm `www` and the apex resolve to CloudFront: `dig @<aws-ns> www.topfivemovies.com`.
- [ ] Verify the site on the staging hostname: parity diff, screenshots, link check.
- [ ] Lower TTLs at the registrar a day or two before the switch, if the registrar allows it.

**Switch**
- [ ] At the registrar, replace the nameservers with the four Route 53 nameservers.
- [ ] Monitor the site and 404s. Propagation can take up to about 48 hours. Visitors on the old nameservers briefly see the parking page.
- [ ] **Rollback:** switch the nameservers back to the registrar's.

**Cleanup**
- [ ] Raise TTLs again once stable.
- [ ] Retire the PHP host and MySQL, and archive the SQL dumps.
- [ ] Delete `web/`, `intra/`, the PHP includes and the devcontainer from `main`, keeping them reachable through a git tag.
- [ ] Write the contributor docs: how to add a review, a top-five list or an author by PR, with a content template for each type.

---

## Risks

- **DNS cutover:** low risk, since the zone holds no mail or verification records. The main hazard is DNSSEC being enabled, which would break resolution after the move. Mitigated by checking it first and querying the Route 53 nameservers directly before the switch.
- **Visual fidelity:** the float layout and image decoration are where the look drifts. Mitigated by screenshot diffs against the Phase 0 captures.
- **Silent data loss:** the encoding conversion and the hand-written HTML bodies. Mitigated by the parity diff.
- **Agentic check noise and cost:** bounded by scoping to changed files, a per-run cap, and keeping it advisory.

## Open items

None.
