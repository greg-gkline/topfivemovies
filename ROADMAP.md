# Top Five Movies: Modernization Roadmap

Move `www.topfivemovies.com` from a PHP 5 / MySQL site to a static site: content in YAML, rendered with Hugo, hosted on S3 behind CloudFront, with the infrastructure in Terraform.

## Goals

- No request-time processing. Content is YAML files in git, and the site is static HTML.
- A pull request renders a preview, gets a spelling check, and gets a separate grammar review.
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
| Checks        | Spelling and grammar are separate, advisory checks that post PR reviews. Spelling is deterministic (`typos`); grammar uses LanguageTool and Harper.                                                                                           |
| Environments  | One. There is no staging site: the PR build publishes screenshots of the changed pages, and a codespace is for trying a change. Before the cutover the site is checked on its `*.cloudfront.net` address. |
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
   PR: validate, spelling and grammar reviews, preview
   main: build, sync, invalidate (GitHub Actions + IAM access keys)
```

## Proposed repo layout

```
content/reviews/the-hurricane.md         # YAML front matter + markdown body
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

Done. The tooling and every decision made during the export are documented in `scripts/export/README.md`.

- [x] Write a re-runnable exporter that reads the devcontainer DB or the SQL dumps and writes one YAML file per article, top-five list and author. It runs in the devcontainer (Python or PHP, no Node). `scripts/export/export.py` parses the SQL dumps directly, and its output is byte-identical between runs.
- [x] Per-type fields:
  - Review and DVD: `type, title, author, date, rating, release_year, starring, caption, image, image_alt`, with the review text as the markdown body.
  - Top five: `title, author, date, image, image_alt, items[5]`, with the intro as the markdown body.
  - Author: `name, jobtitle, image, bio` (markdown or structured fields).
  - As built: the author's bio is the markdown body. Items keep `subtitle` and `caption` where the legacy data has them, plus `image_full`, and `image_width/height` for the 3 pictures that displayed scaled. Top-five items are `{title, film, text}`, with `honorable_mentions` after them.
- [x] Clean data in the exporter:
  - latin1 to UTF-8, with a check for mojibake.
  - `<P>` and raw HTML to markdown.
  - Decode entities such as `&quot;`.
  - Extract `<img>` attributes into structured image fields.
  - Convert the table-based bios (Matt, Brian) to markdown or key/value data.
  - Mark `QA=0` rows as `draft: true`.
- [x] Separate content images from theme images (see Image organization below), and have the exporter move each content image into `content/images/`. They are copied, not moved, so the legacy devcontainer site keeps working until `web/` is deleted in Phase 7.
- [x] Export `Response` and `poll` rows to `data/*.yaml`. Response 19 is not exported: its top-five list was deleted before the dump, so it never rendered. That leaves 59 responses.
- [x] Build `data/quotes.yaml` from **both** quote sources (see Quotes below).
- [x] Add a JSON Schema per content type and validate in CI with `check-jsonschema` and `yamllint`. The schemas are in `scripts/content/schemas/`. `scripts/content/validate.sh` also checks author, item, relref and image references, and runs as the `content` job of the `validate` workflow.
- [x] Spot-check the export against the legacy pages, with `diff`-style review. `scripts/export/spotcheck.py` renders the export with Hugo and diffs 1,478 fields against `baseline/html/`, with no differences.

### Image organization

`web/images/` mixes theme images and content images (218 files). Scanning the SQL dumps and the code gives roughly:

- **~134 content images**, referenced from article, top-five and author rows. All move to a single flat `content/images/` folder, a peer of `reviews`, `top5`, `authors` and the other sections, so a PR for a new review adds the `.md` file and its picture under `content/`. Author photos go there too.
- **~21 theme images** referenced from CSS, templates and RSS. These move to `assets/` and are used only by templates.
- **4 referenced from both** (`brian`, `greg`, `matt`, `nick`.jpg), which are author photos also hard-coded in code. They become content images in `content/images/`, and templates reference them through the author's front matter.
- **~67 unreferenced.** They are mostly old "beige" theme sidebars, the splash page pieces, and `test.gif`. Before deleting, confirm they are not used by the two themes we port. Do not trust the scan alone, since image paths can be built dynamically in code.
- **1 reference to a missing file** (`maroon_lines.jpg`) to resolve while porting. Resolved: only `sepia.css` uses it, and that theme is not ported.
- `lockgray.gif` is only used by the intranet link and goes away with it.

Rules the exporter enforces and CI checks:
- Front matter references images by filename (`image: rev_hurricane.jpg`), never by site path.
- Filenames in `content/images/` are unique by construction, since the folder is flat. The exporter fails on any collision.
- CI fails on any content image reference that does not resolve, and on any file in `content/images/` that nothing references.
- Hugo only publishes non-markdown files in `content/` when they belong to a page bundle, and a flat images folder is not one. So `hugo.yaml` mounts `content/images` into Hugo's asset pipeline (`module.mounts`), and templates load images with `resources.Get`. Hugo then resizes and converts them at build time, so the WebP copies, sizes and `width/height` in Phase 3 come from the originals, with no manual conversion step.
- Only the images that templates request are published, so unused originals add nothing to the output.

### What a content file looks like

Content pages are `.md` files. Each starts with **front matter**: a block of structured YAML fenced by `---` lines that holds the item's fields. The markdown body follows and is converted to HTML by Hugo. Example, `content/reviews/the-hurricane.md`, migrated from the `Article` row for *The Hurricane*:

```markdown
---
type: movie
title: The Hurricane
author: jesse
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

- **Filenames:** lowercase slugs of the title. When titles collide, every colliding item gets its author appended (`american-pie-2-brian.md`, `american-pie-2-bruce.md`), with a number only if one author reuses a title. CI fails on duplicates.
- **Ordering and navigation:** the previous/next links, "recent additions" and the featured story are driven by `date` (and filename as a tiebreaker), not by numeric ID. The old `id-1` and `id+1` logic is not carried over.
- **Links between items:** content links to other items by file path (`{{< relref "reviews/the-hurricane.md" >}}`), so Hugo checks them at build time, and a renamed or deleted file fails the build instead of leaving a dead link.
- **Authors:** items name their author by filename (`author: jesse` is `content/authors/jesse.md`).
- **Responses:** each legacy response is attached to its item by the item's filename (`item: reviews/the-hurricane`) in `data/responses.yaml`, not by numeric ID.
- The exporter uses the old numeric ID only during migration, to map responses to items and to name the files. It is not stored anywhere in the new site.

### Quotes

Today there are two separate quote sources, and they disagree:

- The rotator on the home page (`includes/quotes.js`) is a **hard-coded array of 111 quotes** that picks one at random every 20 seconds. It does not touch the database.
- The `Quote` table has 106 rows, read only by `includes/quote.php`, which nothing includes. That path is dead code.

So the rotator already works without the database. The work is to put the quotes in one place as data and keep the behavior:

- [x] Merge both sources into `data/quotes.yaml`, de-duplicated, with fields `text` and `source` (movie). Review the differences once in a PR. The merge decides what the live set is. The table turned out to be a subset of `quotes.js`. The six rows worded differently are listed in `scripts/export/README.md`, and `quotes.js` wins in each case.
- [x] Quotes with inline HTML (such as `<i>`) become markdown or plain text. They are plain text, since the rotator inserts them with `textContent`.
- [x] At build time, Hugo emits the list as JSON (`quotes.json`, or inlined in the page, which is about 10 KB). Inlined in the home page.
- [x] Rewrite the rotator as a small ES module with the same behavior: random order with no repeats until all are shown, a new quote every 20 seconds, text inserted with `textContent`. Fix the old issues while doing so: the inline `setTimeout` string, the global variables, and the repeat-check bug in `getRandom`. Pause rotation when the tab is hidden and when the user prefers reduced motion.
- [x] No-JavaScript fallback: the page is built with one quote already in `#quote`, so it is never empty. Hugo picks it deterministically per build.
- [x] Remove `quote.php`, `quotes.js` and the `Quote` table with the PHP code in cleanup. `web/` is gone (tag `0.0.2`), and the dumps stay in `legacy/sql/`.

## Phase 2: Hugo site and templates

Done. The templates, the behaviour decided while building them and the parity diff are documented in `scripts/parity/README.md`.

- [x] Scaffold Hugo and the layouts for `review`, `dvd`, `top5`, `other`, `chickflick`, `author` and `about`. Goldmark settings the content depends on are listed under "Notes for Phase 2" in `scripts/export/README.md`.
- [x] Build the index pages: reviews, top fives, others, chickflicks, author bios, quickstart and group bio. Add the "recent additions" partial. Quickstart is not carried over: it is the web host's "coming soon" placeholder, not site content.
- [x] Build the home page as its own layout. The featured story is chosen deterministically at build time, replacing the old "older than 2 weeks, so pick random" logic. It is the newest movie review.
- [x] Generate prev/next links, excerpts, keywords and meta descriptions at build time.
- [x] Output filename-based `.html` addresses, an RSS feed, a sitemap, `robots.txt` and canonical URLs.
- [x] Replace the request-time features:
  - Quote rotator: see Quotes below.
  - Search: dropped. Remove `response_search.php3` and any links to it. Nothing links to it; the file goes with `web/` in Phase 7.
  - Comments: rendered statically from `data/responses.yaml` under each item.
  - Poll: archive page rendered from `data/polls.yaml`, showing final results.
- [x] Build the parity diff against the Phase 0 snapshot. Every legacy page's text should be present in the new output. `scripts/parity/parity.py` checks 12,549 lines on 169 pages. It is a cutover tool, run by hand (see Phase 7), not a PR check, since the site will diverge from the legacy one as content is added. The `validate` workflow builds the site, with Hugo pinned to 0.147.9 there and in the devcontainer.

## Phase 3: Design: faithful look, modern foundation

Done. The stylesheets, the decisions made while porting them, the screenshot comparison and the quality gates are documented in `scripts/quality/README.md`.

- [x] Port `elegant_inner.css` rule by rule for all inner pages. Pull colors and fonts into CSS custom properties. `assets/css/inner.css`, with the colours, fonts and type sizes as tokens in `common.css`.
- [x] Port `elegant.css` separately for the home page, sharing the common tokens and header. `assets/css/home.css`. Each page loads `common.css` plus its own sheet as one minified file.
- [x] Replace float and position layout mechanics with Grid and Flexbox without changing the appearance. The page layouts are grids, with lengths measured from the legacy pages. Pictures still float, so text wraps around them.
- [x] Rebuild the image-based decoration with CSS or SVG where it keeps the look:
  - Gradient fades (`grayfade`, `fadeframe`, `smokefade*`) become CSS gradients.
  - The speech-bubble GIFs become one SVG or CSS shape. A CSS shape, which also grows with long responses.
  - The arrow becomes inline SVG. An SVG data URI in the stylesheet, so the CSP needs `img-src data:` (Phase 5). The poll bars are inline SVG too.
  - Banners and photos are converted to AVIF/WebP with a JPEG fallback. WebP only, where it is smaller (55% fewer image bytes): Hugo 0.147 cannot encode AVIF.
- [x] Semantic HTML5: UTF-8, `lang`, viewport meta, `header/nav/main/article/footer`, a skip link, real `alt` text, and `width/height` with lazy loading. Alt text comes from `image_alt`. The 125 pictures whose legacy rows had none are marked decorative, since the title beside each names the film. Writing alt text for them is left for a content PR.
- [x] Keep the desktop appearance identical, and add responsive behavior for small screens. One column below 740 px, with larger type and 24 px link spacing.
- [x] Screenshot comparison against the Phase 0 captures for each page type, including the home page. `scripts/visual/compare.py`, a review tool rather than a gate. Against the Phase 2 build, which has the same content, item pages are within 0–4%, and the index pages are closer to the legacy look than Phase 2 was.
- [x] Quality gates: HTML validation (`vnu`), accessibility (pa11y or axe), Lighthouse CI budgets, and a link check (`lychee`). `scripts/quality/check.sh` (vnu, axe, lychee) and `lighthouserc.json`, run by the `validate` workflow. Every page passes. axe applies WCAG 2.2 at phone width only, because the legacy desktop rows of links are 22–23 px apart, short of 2.2's 24 px.

## Phase 4: PR pipeline

Each item is its own workflow and its own status check.

- [x] **validate**: schema and YAML lint, Hugo build, HTML validation, link check. Required. `validate.yml` runs the content checks, the build and `html-links` on every change, and the accessibility and Lighthouse jobs only when the design changes. A final job named `validate` collects them, so branch protection needs only that name. It replaces the earlier `content` and `site` workflows.
- [x] **spelling** (advisory): `typos` on the lines a PR changes, with a project dictionary (`_typos.toml`) for actor names and slang. `spelling.yml`, `scripts/prose/spelling.py`. It checks changed lines, not whole files, so touching a legacy review does not mean fixing its old typos. Not a required check.
- [x] **grammar-review** (advisory): `grammar-review.yml`, `scripts/prose/grammar.py`, documented in `scripts/prose/README.md`.
  - Runs on PRs that touch `content/**` or `data/**`, over the changed prose only, with a cap of 50 files per run.
  - Changed from the plan: it uses LanguageTool and Harper, not the Claude API. The goal is wrong-word errors a spell checker misses (to/too/two, its/it's), and the two tools together cover them for free. So it needs no `ANTHROPIC_API_KEY`.
  - The rules (`scripts/prose/rules.json`) leave out style, punctuation and tone, since the voice is intentionally informal and irreverent.
  - Both prose checks post a comment-only PR review with inline comments and, where the fix is a plain replacement, a suggestion block (`scripts/prose/review.py`). Comments already posted are not repeated on a push. On a fork, where the token is read-only, they fall back to warning annotations.
  - Not a required check until the grammar review has proven useful.
- [x] **preview**: changed from the plan. There is no staging site, so the PR build publishes screenshots instead: full-page PNGs, at desktop and phone width, of every page the content changes affect, as an artifact of the `validate` workflow, with a link commented on the PR. `scripts/preview/`, documented in its README.
- [x] **terraform-plan**: `terraform-plan.yml` runs on `infra/**` changes and comments the plan. It signs in as a read-only IAM user with an access key from repository secrets (the account does not support OIDC), and does nothing until those secrets exist after the first apply. The formatting, validation, tflint and checkov checks are the `terraform` job of `validate.yml`, so the one required check, `validate`, covers them.
- [x] Turn on branch protection requiring `validate`, which includes the Terraform checks. `scripts/github/branch-protection.sh` does it; run it by hand once `validate` has reported.

## Phase 5: Infrastructure (Terraform)

Written, and passing `terraform validate`, `tflint` and `checkov`, but **not applied yet**: see the first item. It is in `infra/`, documented in `infra/README.md`. There is one environment: to test a change, use a codespace.

- [x] Set up AWS for Terraform and apply, by hand (`infra/README.md`). Applied, and the site works at the distribution's `*.cloudfront.net` address after a manual build and `aws s3 sync`. The `import` block is removed.
- [x] Create the access keys for the two CI users (Terraform does not, so the secrets stay out of the state) and put them in GitHub: `AWS_PLAN_*` (and `ALERT_EMAIL`, if the budget is on) as repository secrets, and `AWS_DEPLOY_*` in the `Production AWS` environment, which is limited to `main`.
- [x] State: the bucket `infrastructure-<account id>-us-east-2-an` was made by hand, so there is no bootstrap stack. The state is `topfivemovies/terraform/terraform.tfstate` in it, with lockfile locking and the AWS provider pinned by `.terraform.lock.hcl`.
- [x] S3 bucket: the hand-made `topfivemovies` bucket is imported, then made private (Block Public Access, bucket-owner-enforced) and encrypted. No versioning and no lifecycle rules, on purpose: the site is rebuilt from git, and a rollback is a redeploy of an earlier commit.
- [x] CloudFront: Origin Access Control, HTTPS only, HTTP/3, a response-headers policy (HSTS, a strict CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`), a CloudFront Function for `index.html` handling, and the custom 404.
- [x] Redirect from `topfivemovies.com` to `https://www.topfivemovies.com`: the same CloudFront Function, with the apex also on the distribution.
- [x] ACM certificate in `us-east-1` covering `www.topfivemovies.com` and `topfivemovies.com`, validated by DNS records Terraform creates in Route 53. It is created at the cutover, not before: ACM can only validate once the domain is served from Route 53, so the custom domain, certificate and alias records are behind `enable_custom_domain`, which is `false` until Phase 7.
- [x] Route 53 hosted zone for `topfivemovies.com`, with alias records for `www` and the apex pointing to CloudFront (A and AAAA, created with the custom domain).
- [x] Two IAM users for CI, with the permissions attached to each user since the account supports neither OIDC nor IAM groups: `deploy`, limited to the bucket sync and CloudFront invalidations, and `plan`, read-only and unable to read object data. Their access keys are created by hand and kept in repository secrets, not in Terraform.
- [x] ~~Separate `staging` and `prod` environments.~~ Dropped: one environment. Before the cutover the site is reachable at the distribution's `*.cloudfront.net` address.
- [x] Terraform checks in CI: `fmt`, `validate`, `tflint`, `checkov`. Each `checkov` skip is explained beside the resource.
- [x] Optional: a monthly cost budget that emails `alert_email`, off unless that is set. The CloudFront error-rate alarm is dropped: it needs an SNS topic, which the account's organization policy denies.

## Phase 6: Deploy on merge to `main`

Written, not yet run: it needs the `DISTRIBUTION_ID` (and, before the cutover, `SITE_URL`) repository variables from `infra/README.md`. `deploy.yml` and `scripts/deploy/`.

- [x] Full Hugo build. The site is small, so a full build is fast and avoids stale-output bugs, and template and content changes use the same path.
- [x] Sync with `--delete` semantics, with long immutable caching on fingerprinted assets (a digest in the name, or Hugo's `_hu_` image suffix), five minutes on HTML, feeds and `robots.txt`, and a day on the rest. `deploy.sh` compares ETags so only changed files upload, uploads fingerprinted files before HTML, and deletes removed files last. It is not a literal `aws s3 sync`, because that cannot set caching by file name pattern.
- [x] Invalidate the changed paths, or `/*` when templates, CSS or the site configuration changed (or a manual run asks for it, or a rollback). Fingerprinted files are never invalidated, since a change gives them a new name.
- [x] Post-deploy smoke test against the live URL (`scripts/deploy/smoke.sh`): the home page, a page of each section, the feed, sitemap, 404 status, the assets the home page names, and the security headers.
- [x] Rollback by redeploying the previous commit: run the workflow by hand with `ref` set to that commit.

## Phase 7: DNS migration and cutover

DNS delegation is the riskiest step. Do it only after the site is verified on the distribution's `*.cloudfront.net` address.

The current zone has no records beyond the registrar's domain parking, so there is no mail or verification setup to preserve. The parking records are replaced by the new site and are not recreated.

**Before touching registrar**
- [x] Confirm the zone holds only the parking configuration (check with `dig` for A, AAAA, CNAME, MX, TXT and NS on the apex and `www`).
- [x] Confirm DNSSEC is **off** at the registrar. If it is on, it must be disabled first or the domain will fail validation after the move.
- [x] Disable parking at the registrar when switching the nameservers, if it does not release automatically.

**Verify**
- [x] Query the new Route 53 nameservers directly and confirm `www` and the apex resolve to CloudFront: `dig @<aws-ns> www.topfivemovies.com`.
- [x] Verify the site on the `*.cloudfront.net` address (`terraform output distribution_domain`): parity diff, screenshots, link check.
- [x] Lower TTLs at the registrar a day or two before the switch, if the registrar allows it.

**Switch**
- [x] At the registrar, replace the nameservers with the four Route 53 nameservers (`terraform output name_servers`).
- [x] When the Route 53 servers answer for the domain, set `enable_custom_domain = true` in `infra/terraform.tfvars` and apply: Terraform requests the certificate, validates it through the zone, and attaches the domain to CloudFront.
- [ ] Monitor the site and 404s. Propagation can take up to about 48 hours. Visitors on the old nameservers briefly see the parking page.
- [ ] **Rollback:** switch the nameservers back to the registrar's.

**Cleanup**
- [ ] Raise TTLs again once stable.
- [ ] Retire the PHP host and MySQL, and archive the SQL dumps.
- [x] Delete `web/` (which held `intra/` and the PHP includes) and the devcontainer's PHP/MySQL stack from `main`, keeping them reachable through the `0.0.2` tag. The devcontainer itself stays, reduced to the Hugo and checking tools, since the codespace is where changes are tried. `scripts/export` and `scripts/baseline` need the tag now (see their READMEs).
- [x] Write the contributor docs: `CONTRIBUTING.md`, a click-by-click guide that works entirely in the GitHub UI. Creating a branch named `review-<title>`, `dvd-`, `chickflick-`, `top5-`, `other-` or `author-` runs `new-content.yml`, which commits the starting file from `scripts/new-content/templates/`. The contributor edits it in the UI and opens the PR, so the usual checks run (a workflow cannot open the PR itself without a bot token, since PRs made with `GITHUB_TOKEN` do not trigger other workflows).

---

## Risks

- **DNS cutover:** low risk, since the zone holds no mail or verification records. The main hazard is DNSSEC being enabled, which would break resolution after the move. Mitigated by checking it first and querying the Route 53 nameservers directly before the switch.
- **Visual fidelity:** the float layout and image decoration are where the look drifts. Mitigated by screenshot diffs against the Phase 0 captures.
- **Silent data loss:** the encoding conversion and the hand-written HTML bodies. Mitigated by the parity diff.
- **Grammar check noise:** bounded by scoping to changed lines, a per-run cap, a rule list that leaves out style, and keeping it advisory.

## Open items

None.
