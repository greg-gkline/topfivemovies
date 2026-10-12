# Content export (Phase 1)

Moves the legacy MySQL content into the files Hugo reads. The tooling is re-runnable and deterministic: two runs produce byte-identical output.

```sh
python3 scripts/export/export.py      # regenerate content/, data/, assets/images/, static/favicon.ico
python3 scripts/export/spotcheck.py   # compare the result with the legacy pages in baseline/html/
scripts/content/validate.sh           # schemas, YAML lint, cross-references (what CI runs)
```

The exporter owns everything it writes and rewrites it from scratch. Once the content has been edited by hand after the migration PR, do not run it again.

## Sources

| Source | Notes |
|---|---|
| `legacy/sql/*.sql` | Parsed directly (`sqldump.py`), so no database is needed. The dumps are UTF-8 (`SET NAMES utf8mb4`) over latin1 tables, so reading them as UTF-8 is the latin1 to UTF-8 step. The parser was checked value by value against the devcontainer DB (1,676 strings, no differences). |
| `web/includes/quotes.js` | The live quote rotator. Its bytes are Windows-1252 (`0x92` is `’`), decoded strictly. |
| `web/images/` | Content images are copied, not moved, so the legacy site keeps working until `web/` is deleted in Phase 7. |

Every string is scanned for mojibake (`Ã`, `â€`, C1 control characters, U+FFFD) and the export fails if any is found. None are.

## What it writes

| Output | From | Count |
|---|---|---|
| `content/reviews/*.md` | `Article` rows with `Type` movie or dvd, with `type: movie` or `type: dvd` | 51 |
| `content/chickflicks/*.md` | `Article` rows with `Type` chick | 8 |
| `content/other/*.md` | `Article` rows with `Type` other (one `QA=0` row, `jinkies.md`, has `draft: true`) | 10 |
| `content/top5/*.md` | `Top5` | 62 |
| `content/authors/*.md` | `Author` | 8 |
| `data/responses.yaml` | `Response`, attached to items by path (`item: reviews/swordfish`) | 59 |
| `data/polls.yaml` | `poll`, oldest first, empty options (`"0"`) dropped | 14 |
| `data/quotes.yaml` | `quotes.js` merged with the `Quote` table | 111 |
| `content/images/` | Every picture an item or author references | 134 |
| `assets/images/`, `static/favicon.ico` | Theme images of the two ported stylesheets and the templates | 12 + 1 |

The JSON Schemas in `scripts/content/schemas/` are the reference for every field.

### Names and references

- **Filenames** are lowercase slugs of the title (`&` and apostrophes dropped). When items in a section share a title, each of them gets its author appended (`american-pie-2-brian.md`, `american-pie-2-bruce.md`), so neither looks like the canonical one. If one author reused a title, a number would follow in date order, but that never happens. Titles are shared five times: the two *American Pie 2* reviews and four top-five titles (Hitchcock movies, mafia movies, tear-jerkers, sports movies).
- **Authors** are referenced by filename (`author: jesse`), consistent with "the filename is the identity". The staff account becomes `the-topfivemovies-staff`.
- **Internal links** in bodies become `{{< relref "top5/….md" >}}`. That includes `topfive_50`'s broken legacy link `top5.php3?id=49`, which pointed at a list that does exist (*Top 5 Comedic Duos of the Motion Pictures*) under an old URL scheme. It now resolves.
- **Legacy IDs** are used only during the export (to name files and attach responses) and are not written anywhere.

### Field mapping

- **Reviews and chick flicks:** `type` (reviews only), `title`, `subtitle` (3 items), `author`, `date`, `rating`, `release_year`, `starring`, `caption`, `image`, `image_alt`. Chick flicks have the same fields minus `type`; Hugo takes their type from the section.
- **Other features:** `title`, `subtitle`, `author`, `date`, `caption`, image fields. `rating` and `release_year` were always 0 or NULL and are dropped.
- **Image fields:** `image` and `image_alt` come from the stored `<img>` tag. All legacy alt text is empty, so `image_alt: ''` is carried over as-is; writing real alt text is Phase 3 work. `image_width` and `image_height` are written only for the 3 pictures the legacy page showed scaled (`watersjohn.jpg`, `odonnell.jpg`, `spanking.jpg`). Everywhere else the tag's size matched the file. `image_full` is `Image_fullsize` (5 "other" rows). The legacy templates never displayed it, but it is content, so it is kept.
- **Top-five items** are structured: `title`, then `film` (from `div.quote`, used by the musician cameos list) and `text` (from `div.bodyText` or `font.bodyText`). Three lists put honorable mentions after item 5. These become `honorable_mentions: [{title, text}]`, with the "Honorable Mention:" prefix removed from `title` so the template can add it back.
- **Author bios** become the markdown body. The two table bios (Matt, Brian) become `facts: [{heading, items: [{label, value}]}]`. The labels lose their trailing colon, which the template adds back. Matt's spacer row is dropped.
- **Plain-text fields** (`title`, `subtitle`, `starring`, `caption`, `name`, `jobtitle`) have entities decoded and whitespace collapsed. Everything else is markdown.
- **Quotes** are plain text, not markdown, because the rotator inserts them with `textContent`. `text` has no outer quotation marks; the page adds them. In the few multi-speaker quotes the inner marks stay (`…tongue." "Who pays the rent on time.`).

### HTML to markdown (`html2md.py`)

- Every `<P>`, `<p>` and `</p>` is a paragraph boundary. `<div>` is a block. Other whitespace follows HTML rules: a run containing a newline becomes a soft break, so the original line wrapping is kept, and indentation is stripped so nothing turns into a code block.
- `<i>`/`<em>` become `*…*`, `<b>`/`<strong>` become `**…**`, `<br>` becomes a hard break (trailing `\`), and `<ul>`, `<h3>`, `<hr>` and `<blockquote>` map directly. Entities are decoded.
- Underline has no markdown syntax. It is written as `++text++`, Goldmark's *insert* extra, which renders `<ins>` (underlined by default). There are 2 uses.
- The one styled `<span>` (bold firebrick spoiler warning, `m-night-shyamalan.md`) keeps its bold and loses its colour.
- External links keep their URL but lose `target=…`.
- Text is escaped wherever it would otherwise be markup, for example a leading `- ` in top-five item text (`\- J. Lo.`) or a line starting `2001.`. Bare URLs are escaped (`http\://`) so Goldmark's linkify leaves them as plain text, as they were.
- Any tag outside this set fails the export instead of being dropped.

## Spot-check

`spotcheck.py` renders the exported content with Hugo, so markdown goes through the real Goldmark. It then compares every field with the same field on the legacy page in `baseline/html/`: titles, bylines, dates, ratings, images and sizes, bodies, top-five items and mentions, bios and facts, and the text and author of every response. Text is compared together with its italic, bold, underline and link formatting and its paragraph breaks.

Current result: **1,478 fields checked, 0 differences.** Planted defects (a dropped `*…*`, merged paragraphs, a changed rating, an edited response) are each reported.

Polls are compared with the dump instead, because the baseline captured no poll results. All 14 `index.html?viewpoll=N` pages show the current poll's ballot, since the parameter never took effect in the devcontainer.

## Decisions made during the export

- **Response 19 is not exported.** It belongs to `Top5` 21, which was deleted before the dump, so it never rendered anywhere. The exporter skips it by an explicit allowlist (`ORPHAN_RESPONSES`), and any other orphan fails the export. That leaves 59 responses, not 60.
- **Quotes:** the `Quote` table (106 rows) is a subset of `quotes.js` (111). Six table rows are worded differently, and `quotes.js` wins in each case, since it is what visitors saw and it is already plain text. The differences:
  - Four use `<i>`/`<u>` where `quotes.js` uses capitals (*WITH nail polish*, *I DO mind*, *A gun*) or no emphasis (*You're Mr. Lebowski*).
  - One table row quotes *'morally casual'*.
  - The Meet the Parents quote is attributed to *Robert DeNiro in "Meet the Parents"* in `quotes.js`.

## Image inventory

`web/images/` holds 218 files:

| Group | Count | Where it goes |
|---|---|---|
| Content: referenced by `Article`, `Top5` or `Author` rows | 134 | `content/images/` |
| Theme: the banner `top5gray.jpg`, the RSS image `top5gray_small.jpg` and the footer badge `somerights20.png` | 3 | `assets/images/` |
| Theme, redrawn in CSS and SVG in Phase 3: the bubbles, fades, arrow and frame of `elegant.css` and `elegant_inner.css`, and the poll bar `maroon_dot.jpg` | 9 | left behind |
| `favicon.ico` | 1 | `static/` |
| Referenced only by retired code: `gasmask.gif` (`gasmask.css`), `fiveback.jpg` and `greenmenufade.jpg` (`lime.css`), `lockgray.gif` (intranet link) | 4 | left behind |
| Not referenced by any code or row: the beige theme sidebars, the splash pieces, `test.gif`, and a few unused stills (`apes_*.jpg`, `village_v2.jpg`, …) | 67 | left behind |

The author photos `brian`, `greg`, `matt` and `nick` are also hard-coded in `groupbio.html`. They are content images, and templates should reach them through the author's front matter. The missing `maroon_lines.jpg` is referenced only by `sepia.css`, which is not being ported, so nothing needs to replace it. Content images and theme images never overlap; the exporter checks this.

## Notes for Phase 2

- Enable `markup.goldmark.extensions.extras.insert` for the two `++underline++` spans. Without it, they render as literal `++`.
- Goldmark's typographer is on by default and turns `"` into curly quotes and `--` into dashes. The legacy pages show straight quotes and `--`. Disable it if the text should look exactly as before.
- Leave `markup.goldmark.renderer.unsafe` off. The content contains no raw HTML.
- Reviews set Hugo's `type` (`movie` or `dvd`), so layout lookup goes to `layouts/movie/` and `layouts/dvd/`, not `layouts/reviews/`.
- Author pages have `name`, not `title`. Use `.Params.name` in templates, or map it to the title.
- `content/images` must be mounted into `assets` (see the roadmap) before `resources.Get` can find the pictures.
