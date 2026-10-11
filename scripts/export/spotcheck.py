#!/usr/bin/env python3
"""Compare the exported content with the legacy pages captured in baseline/html/.

Renders every exported page with Hugo (so markdown goes through the real Goldmark),
then compares each field with the same field on the legacy page: titles, bylines,
dates, ratings, images, body text, top-five items, bios and staff responses. Polls
are compared with the dump, since the baseline captured no poll results.

Text is compared together with its inline formatting (italic, bold, underline, links)
and paragraph breaks, so a lost <i> or a merged paragraph shows up as a difference.

Usage: python3 scripts/export/spotcheck.py [-v]     (-v prints matching fields too)
Needs `hugo` on PATH. Exits non-zero if any field differs from the legacy page,
apart from the known, intended differences listed in EXPECTED.
"""

import datetime
import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, NavigableString, Comment

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export import ROOT, Exporter  # noqa: E402

BASELINE = ROOT / "baseline/html"

# Intended differences: (page, field) -> why. Colour is not compared, so the one
# styled span (other_72's bold firebrick spoiler warning, now plain bold) is not here.
EXPECTED = {}

HUGO_CONFIG = """
contentDir: {root}/content
dataDir: {root}/data
uglyURLs: true
disableKinds: [section, taxonomy, term, rss, sitemap, robotsTXT, 404]
buildDrafts: true
markup:
  goldmark:
    extensions:
      typographer: {disable: true}   # compare the literal characters
      extras: {insert: {enable: true}}
"""

# One JSON document per page with every field rendered to HTML.
HUGO_LAYOUT = r"""
{{- $path := strings.TrimSuffix ".md" (replace .File.Path "\\" "/") -}}
{{- $md := dict -}}
{{- range $k, $v := .Params -}}
  {{- if eq (printf "%T" $v) "string" -}}{{- $md = merge $md (dict $k ($.RenderString $v)) -}}{{- end -}}
{{- end -}}
{{- $items := slice -}}
{{- range .Params.items -}}
  {{- $i := dict -}}
  {{- range $k, $v := . -}}{{- $i = merge $i (dict $k ($.RenderString $v)) -}}{{- end -}}
  {{- $items = $items | append $i -}}
{{- end -}}
{{- $mentions := slice -}}
{{- range .Params.honorable_mentions -}}
  {{- $i := dict -}}
  {{- range $k, $v := . -}}{{- $i = merge $i (dict $k ($.RenderString $v)) -}}{{- end -}}
  {{- $mentions = $mentions | append $i -}}
{{- end -}}
{{- $facts := slice -}}
{{- range .Params.facts -}}
  {{- $rows := slice -}}
  {{- range .items -}}{{- $rows = $rows | append (dict "label" .label "value" ($.RenderString .value)) -}}{{- end -}}
  {{- $facts = $facts | append (dict "heading" .heading "items" $rows) -}}
{{- end -}}
{{- $responses := slice -}}
{{- range where site.Data.responses "item" $path -}}
  {{- $responses = $responses | append (dict "author" .author "text" ($.RenderString (dict "display" "block") .text)) -}}
{{- end -}}
{{- dict "path" $path "params" .Params "md" $md "body" .Content "items" $items "mentions" $mentions "facts" $facts "responses" $responses | jsonify -}}
"""

# The poll data, rendered.
HUGO_HOME_LAYOUT = r"""
{{- $polls := slice -}}
{{- range site.Data.polls -}}
  {{- $options := slice -}}
  {{- range .options -}}{{- $options = $options | append (dict "text" ($.RenderString .text) "votes" .votes) -}}{{- end -}}
  {{- $polls = $polls | append (dict "question" ($.RenderString .question) "options" $options) -}}
{{- end -}}
{{- dict "polls" $polls | jsonify -}}
"""

_FMT = {"i": "i", "em": "i", "b": "b", "strong": "b", "u": "u", "ins": "u", "a": "a", "h3": "h"}
_BLOCKS = {"p", "div", "br", "hr", "h2", "h3", "ul", "ol", "li", "blockquote", "table", "tr",
           "td", "th", "tfm-para"}


def canon(fragment):
    """Text with inline formatting as ⟨i⟩…⟨/i⟩ markers and block breaks as ¶."""
    if isinstance(fragment, str):
        fragment = BeautifulSoup(re.sub(r"<P>", "<tfm-para></tfm-para>", fragment), "html.parser")
    chars = []   # (char, frozenset of formats)

    def walk(node, fmt):
        for child in node.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                for ch in str(child):
                    chars.append((" " if ch.isspace() else ch, fmt))
                continue
            name = child.name
            f = fmt
            if name in _FMT:
                f = fmt | {_FMT[name]}
            elif name == "span" and "bold" in child.get("style", ""):
                f = fmt | {"b"}
            if name in _BLOCKS:
                chars.append(("¶", frozenset()))
            if name == "hr":
                chars.append(("―", frozenset()))
            walk(child, f)
            if name in _BLOCKS:
                chars.append(("¶", frozenset()))

    walk(fragment, frozenset())
    # Whitespace never carries formatting, and collapses like HTML.
    out, prev_fmt = [], frozenset()
    text = []
    for ch, fmt in chars:
        if ch == " ":
            text.append((" ", None))
        else:
            text.append((ch, fmt))
    s = []
    for ch, fmt in text:
        if fmt is None:
            s.append(" ")
            continue
        if ch == "¶":                 # formatting never spans a block break
            fmt = frozenset()
        if fmt != prev_fmt:
            for f in sorted(prev_fmt - fmt):
                s.append(f"⟨/{f}⟩")
            for f in sorted(fmt - prev_fmt):
                s.append(f"⟨{f}⟩")
            prev_fmt = fmt
        s.append(ch)
    for f in sorted(prev_fmt):
        s.append(f"⟨/{f}⟩")
    result = "".join(s)
    # Move spaces out of formatting runs, then collapse whitespace and breaks.
    for _ in range(3):
        result = re.sub(r"(⟨[a-z]⟩) ", r" \1", result)
        result = re.sub(r" (⟨/[a-z]⟩)", r"\1 ", result)
        result = re.sub(r"⟨([a-z])⟩((?:⟨[a-z]⟩)*)⟨/\1⟩", r"\2", result)  # empty runs
        result = re.sub(r"⟨/([a-z])⟩(\s*)⟨\1⟩", r"\2", result)          # split runs
    result = re.sub(r" +", " ", result)
    result = re.sub(r"\s*¶[\s¶]*", "¶", result).strip("¶ ")
    return result


def flat(s):
    return re.sub(r"\s*¶\s*", " ", s).strip()


def legacy_date(d):
    if isinstance(d, str):
        d = datetime.date.fromisoformat(d[:10])
    return d.strftime("(%B %d, %Y)")


class Report:
    def __init__(self, verbose):
        self.verbose = verbose
        self.failures = self.expected = self.checked = 0

    def compare(self, page, field, legacy, new):
        self.checked += 1
        if legacy == new:
            if self.verbose:
                print(f"ok    {page} {field}")
            return
        if (page, field) in EXPECTED:
            self.expected += 1
            print(f"known {page} {field}: {EXPECTED[(page, field)]}")
            return
        self.failures += 1
        print(f"DIFF  {page} {field}")
        a, b = legacy.split("¶"), new.split("¶")
        for line in difflib.unified_diff(a, b, "legacy", "export", lineterm="", n=0):
            if not line.startswith("@@"):
                print("      " + line)


def render(exp):
    """Build the exported content with Hugo; return {path: page JSON}."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "hugo.yaml").write_text(HUGO_CONFIG.replace("{root}", str(ROOT)))
        (tmp / "layouts/_default").mkdir(parents=True)
        (tmp / "layouts/_default/single.html").write_text(HUGO_LAYOUT)
        (tmp / "layouts/index.html").write_text(HUGO_HOME_LAYOUT)
        subprocess.run(["hugo", "--quiet", "--source", tmp, "--destination", tmp / "public"],
                       check=True)
        pages = {}
        for f in (tmp / "public").rglob("*.html"):
            if f == tmp / "public/index.html":
                pages["/"] = json.loads(f.read_text())
                continue
            page = json.loads(f.read_text())
            pages[page["path"]] = page
        return pages


def legacy_page(name):
    # html5lib repairs the malformed legacy markup the way a browser does.
    return BeautifulSoup((BASELINE / name).read_bytes().decode("cp1252"), "html5lib")


def main():
    report = Report("-v" in sys.argv)
    exp = Exporter()
    pages = render(exp)
    authors = {p.stem: yaml.safe_load(p.read_text().split("---")[1])
               for p in (ROOT / "content/authors").glob("*.md")}
    author_names = {slug: a["name"] for slug, a in authors.items()}

    def check_responses(name, region, page):
        legacy = [canon(div) for div in region.select("div.response_text")]
        legacy_who = [img["alt"] for img in region.select("div.response_img img")]
        new = [canon(r["text"]) for r in page["responses"]]
        new_who = [f"{author_names[r['author']]} says:" for r in page["responses"]]
        report.compare(name, "responses", "¶".join(legacy), "¶".join(new))
        report.compare(name, "response authors", " ".join(legacy_who), " ".join(new_who))

    def check_image(name, region, params):
        img = region.find("img", recursive=False)
        legacy = (img["src"].split("/")[-1], img.get("width"), img.get("height")) if img else None
        new = None
        if params.get("image"):
            from PIL import Image
            w, h = Image.open(ROOT / "content/images" / params["image"]).size
            new = (params["image"], str(params.get("image_width", w)), str(params.get("image_height", h)))
            if legacy and legacy[1] is None:          # legacy tag had no size
                new = (new[0], None, None)
        report.compare(name, "image", str(legacy), str(new))

    for ident, path in sorted(exp.article_path.items()):
        row = exp.articles[ident]
        prefix = {"movie": "review", "dvd": "review", "chick": "chickflick", "other": "other"}[row["Type"]]
        name = f"{prefix}_{ident}.html"
        page = pages[path]
        params = page["params"]
        region = legacy_page(name).select_one("div.review")
        title = params["title"] + (f" ({params['release_year']})" if prefix != "other" else "")
        report.compare(name, "title", region.select_one("h2.title").get_text(), title)
        report.compare(name, "author", region.select_one("div.author").get_text(),
                       f"by {author_names[params['author']]}")
        report.compare(name, "date", region.select_one("div.date").get_text(), legacy_date(params["date"]))
        if prefix == "other":
            report.compare(name, "subtitle", region.select_one("div.subtitle").get_text().strip(),
                           params.get("subtitle", ""))
        else:
            report.compare(name, "starring", region.select_one("div.starring").get_text().strip(),
                           params["starring"])
            report.compare(name, "rating", region.select_one("div.rating").get_text(),
                           f"Rating: {params['rating']:.1f} / 10.0")
        check_image(name, region, params)
        report.compare(name, "body", canon(region.select_one("div.text")), canon(page["body"]))
        check_responses(name, region, page)

    for ident, path in sorted(exp.top5_path.items()):
        name = f"topfive_{ident}.html"
        page = pages[path]
        params = page["params"]
        region = legacy_page(name).select_one("div.topfive")
        report.compare(name, "title", region.select_one("h2.title").get_text(), params["title"])
        report.compare(name, "author", region.select_one("div.author").get_text(),
                       f"by {author_names[params['author']]}")
        report.compare(name, "date", region.select_one("div.date").get_text(), legacy_date(params["date"]))
        check_image(name, region, params)
        report.compare(name, "body", canon(region.select_one("div.text")), canon(page["body"]))
        lis = region.select("ol > li")
        for n, (li, item) in enumerate(zip(lis, page["items"]), 1):
            new = " ".join(canon(item[k]) for k in ("title", "film", "text") if k in item)
            if n == 5:
                for m in page["mentions"]:
                    head = f"Honorable Mention: {canon(m['title'])}" if "title" in m else "Honorable Mentions:"
                    new += " " + head + " " + canon(m.get("text", ""))
            report.compare(name, f"item {n}", flat(canon(li)), flat(new).strip())
        report.compare(name, "item count", str(len(lis)), str(len(page["items"])))
        check_responses(name, region, page)

    for ident, slug in sorted(exp.author_slug.items()):
        name = f"about_{ident}.html"
        page = pages[f"authors/{slug}"]
        params = page["params"]
        region = legacy_page(name).select_one("div.author_info")
        report.compare(name, "name", region.select_one("h2.name").get_text(), params["name"])
        report.compare(name, "jobtitle", region.select_one("div.jobtitle").get_text(),
                       params.get("jobtitle", ""))
        img = region.select_one("div.image img")
        report.compare(name, "image", img["src"].split("/")[-1] if img["src"] != "images/" else "",
                       params.get("image", ""))
        bio = region.select_one("div.bio")
        if params.get("facts"):
            new = " ".join(
                (canon(g["heading"]) + " " if g.get("heading") else "")
                + " ".join(f"{r['label']}: {canon(r['value'])}" for r in g["items"])
                for g in page["facts"])
            report.compare(name, "facts", flat(canon(bio)), new)
        else:
            report.compare(name, "bio", canon(bio), canon(page["body"]))

    # The baseline has no poll results (the legacy ?viewpoll= parameter never took
    # effect), so polls are compared with the dump.
    rows = sorted(exp.tables["poll"], key=lambda r: r["Poll_date"])
    report.compare("polls", "count", str(len(rows)), str(len(pages["/"]["polls"])))
    for row, poll in zip(rows, pages["/"]["polls"]):
        name = f"poll {row['ID_']}"
        report.compare(name, "question", canon(row["Question"]), canon(poll["question"]))
        legacy = [f"{canon(row[f'Text{n}'])} {row[f'Votes{n}']}" for n in range(1, 6)
                  if row[f"Text{n}"].strip() != "0"]
        new = [f"{canon(o['text'])} {o['votes']}" for o in poll["options"]]
        report.compare(name, "options", "¶".join(legacy), "¶".join(new))

    print(f"\n{report.checked} fields checked: {report.failures} differ, "
          f"{report.expected} known differences")
    sys.exit(1 if report.failures else 0)


if __name__ == "__main__":
    main()
