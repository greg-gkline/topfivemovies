# Prose checks (Phase 4)

Two pull-request checks on the writing in `content/` and `data/`. Both are advisory, and both
look **only at the lines a pull request adds or changes**. Content was migrated as-is, so a fix to one sentence
of a legacy review does not have to clear every old error in the file.

| Check | Tool | Gate | Workflow |
|---|---|---|---|
| `spelling` | [typos](https://github.com/crate-ci/typos) | Advisory | `spelling.yml` |
| `grammar-review` | LanguageTool and Harper | Advisory | `grammar-review.yml` |

Neither is a required check and neither fails the job. Each posts a **pull request review**
(see below), so a finding is a comment you can answer, apply or ignore.

## How findings are reported

`review.py` posts one review per run, as a comment-only review from `github-actions[bot]`, with
an inline comment on each finding's line. Where the fix is one unambiguous replacement inside
that line, the comment carries a GitHub suggestion block, so the author can apply it with a
click. A comment that is already on the PR from an earlier run is not posted again, so a push
does not repeat them. At most 40 comments go in one review. The job summary always lists every
finding.

The workflows have `pull-requests: write` for this. On a **fork** the token is read-only, so
there (and locally, and whenever the API call fails) the findings are warning annotations on
the changed lines instead, at most 10 per tool.

## What gets checked

`prose.py` blanks everything that is not prose, keeping line numbers, so a finding lands on
the right line of the original file:

- `content/**/*.md`: the markdown body, plus `text` (top-five items and honorable mentions),
  `caption` and `subtitle` from the front matter. Shortcodes and link targets are dropped.
- `data/responses.yaml` (`text`) and `data/polls.yaml` (`question`).
- Not `data/quotes.yaml`: those are film lines, quoted verbatim.

`spelling` also reads titles, `starring` and the other front matter fields, since typos
scans the whole file, but it skips the fields that only name another file (`item`, `image`,
`author`).

## Spelling

typos flags *known misspellings*, not unknown words, so film titles and actor names rarely
trip it. When it does get a name or deliberate slang wrong, add the word to `_typos.toml` at
the repo root (the editor extension reads it too). A typo in a new file's name is reported on
line 1. Run it yourself:

    pip install typos==1.51.1
    scripts/prose/spelling.py --base origin/main     # what your branch changed (prints warnings)
    scripts/prose/spelling.py --all                  # everything: the legacy typos show up

## Grammar review

The aim is the errors a spell checker cannot see, because every word is spelled correctly:
to/too/two, its/it's, then/than, would of. LanguageTool and Harper catch different ones, so
both run. Their rules are in `rules.json`: style, punctuation, hyphenation, casing and tone
rules are off, because the voice is informal and irreverent on purpose, and a few rules that
were wrong on this content are off by name. Edit `rules.json` to turn a rule on or off.

    scripts/prose/grammar.py --base origin/main
    scripts/prose/grammar.py --all                   # about 35 s; a baseline of the existing content

It runs only on pull requests that touch `content/**` or `data/**`, checks at most 50 files
per run, and needs no secret of its own. The tools are downloaded and checksummed by `tools.sh` into `.cache/prose/`
(git-ignored); LanguageTool needs Java 17+.

### What to expect

Tested on all the content at the time (about 31,600 words): 63 findings, most of them
real (`Santa Clause`, `a Egyptian`, `suppose to`, `you're dream`, `alot`). The ones that are
wrong are mostly informal phrasing. Neither tool is reliable on its own: on a test file of
known errors, LanguageTool missed `their going` and Harper missed `your going`, and both
missed `looses` and `accept`/`except`. LanguageTool also has an optional n-gram data set
(several GB) that makes its confusable-word rules stronger. It is not used here.

## Branch protection

Only `validate` is meant to be required. See `scripts/github/branch-protection.sh`.
