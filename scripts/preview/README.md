# Pull request preview

The `preview` job in `.github/workflows/validate.yml` screenshots the pages that a pull
request's content changes affect, from the build the same workflow made, and publishes the
images as the `preview` artifact. It also comments a link and a table on the pull request,
and updates that comment on each push. There is no staging site.

`preview.py` works out the affected pages from the diff against the merge base:

| Changed | Pages shot |
|---|---|
| `content/**/*.md` | that page |
| `content/images/*` | every page whose front matter names the image |
| `data/responses.yaml` | the item pages whose responses changed |
| `data/polls.yaml` | the poll page |
| `data/quotes.yaml` | the home page |

Each page gets a full-page PNG at desktop width (1280 px) and at phone width (390 px), and
`summary.md` lists them. A draft is listed but not shot, and at most 20 pages are shot. Changes
to templates and styles are not content, so they get no preview: they are checked by the
quality gates, and by running the site in a codespace. On a fork the comment is skipped,
because the token is read-only, and the images are in the artifact only.

Locally, after `hugo`:

    python3 scripts/preview/preview.py --base origin/main --out /tmp/preview

The comment is posted by `scripts/github/pr_comment.py`, which edits its own earlier comment,
found by a marker, instead of adding a new one each time.
