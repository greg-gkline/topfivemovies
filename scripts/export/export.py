#!/usr/bin/env python3
"""Export the legacy MySQL content to Hugo content files and data files.

Reads the dumps in legacy/sql/ (the same files the devcontainer DB is loaded from)
and regenerates, from scratch:

    content/{reviews,chickflicks,other,top5,authors}/*.md
    content/images/*            content images, copied from web/images/
    assets/images/*             theme images the templates still use
    static/favicon.ico
    data/{responses,polls,quotes}.yaml

It is safe to re-run: every output above is owned by the exporter and rewritten.
Once content is edited by hand (after the migration PR), do not run it again.

Usage: python3 scripts/export/export.py
"""

import datetime
import html
import re
import shutil
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, NavigableString
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from html2md import Converter, ConversionError  # noqa: E402
from sqldump import read_tables  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
CONTENT = ROOT / "content"
DATA = ROOT / "data"

# Article.Type -> content section
SECTIONS = {"movie": "reviews", "dvd": "reviews", "chick": "chickflicks", "other": "other"}
OWNED_SECTIONS = ["reviews", "chickflicks", "other", "top5", "authors"]

# Theme images the templates use: the banner, the RSS channel image and the footer
# licence badge. Phase 3 redrew the rest of the legacy stylesheets' images (bubbles,
# fades, arrow, frame, poll bar) in CSS and SVG. See README.md for the full inventory,
# including what is deliberately left behind.
THEME_IMAGES = ["top5gray.jpg", "top5gray_small.jpg", "somerights20.png"]
STATIC_FILES = ["favicon.ico"]

# Legacy internal link forms. top5.php3 is an older URL scheme that one intro still uses.
LINK_PATTERNS = [
    (re.compile(r"/?(?:review|chickflick|other)_(\d+)\.html"), "article"),
    (re.compile(r"/?topfive_(\d+)\.html"), "top5"),
    (re.compile(r"/?top5\.php3\?id=(\d+)"), "top5"),
    (re.compile(r"/?about_(\d+)\.html"), "author"),
]

# Responses whose item no longer exists, so they never rendered on the legacy site.
# Response 19 belongs to Top5 21, which was deleted before the dump.
ORPHAN_RESPONSES = {19}

MOJIBAKE = re.compile("Ã[\x80-\xbf]|Â[\x80-\xbf]|â€|�|[\x80-\x9f]")


class ExportError(Exception):
    pass


# -- helpers ---------------------------------------------------------------------------

def slugify(title):
    s = title.lower().replace("&", " ")
    s = re.sub(r"['’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def plain(value):
    """A plain-text field: decode entities and collapse whitespace."""
    if value is None:
        return None
    value = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return value or None


def date(value):
    return datetime.date.fromisoformat(value)


def number(value):
    return int(value) if float(value).is_integer() else float(value)


def parse_img(tag_html, where):
    """Pull the structured fields out of a stored <img> tag."""
    soup = BeautifulSoup(tag_html, "html.parser")
    imgs = soup.find_all("img")
    if len(imgs) != 1 or soup.get_text().strip():
        raise ExportError(f"{where}: expected a single <img>, got {tag_html!r}")
    img = imgs[0]
    src = img["src"]
    if not src.startswith("images/") or "/" in src[len("images/"):]:
        raise ExportError(f"{where}: unexpected image path {src!r}")
    name = src[len("images/"):]
    path = WEB / "images" / name
    if not path.is_file():
        raise ExportError(f"{where}: image {name} does not exist")
    fields = {"image": name, "image_alt": img.get("alt", "")}
    # Only record a display size when it differs from the file's own size, i.e. when
    # the legacy page scaled the picture.
    w, h = img.get("width"), img.get("height")
    natural = Image.open(path).size
    if (w or h) and (int(w or natural[0]), int(h or natural[1])) != natural:
        fields["image_width"] = int(w)
        fields["image_height"] = int(h)
    return fields


def image_path_field(value, where):
    """Image_fullsize holds a bare path (images/x.jpg), not a tag."""
    value = (value or "").strip()
    if not value:
        return None
    if not value.startswith("images/") or not (WEB / value).is_file():
        raise ExportError(f"{where}: bad image path {value!r}")
    return value[len("images/"):]


class _Dumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)   # indent lists under their key


def _str_representer(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str_representer)


def to_yaml(data):
    return yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True,
                     width=10**9, default_flow_style=False)


def write_page(path, front, body):
    front = {k: v for k, v in front.items() if v is not None}
    text = "---\n" + to_yaml(front) + "---\n"
    if body:
        text += "\n" + body + "\n"
    path.write_text(text, encoding="utf-8")


def write_data(name, header, data):
    (DATA / name).write_text(header + to_yaml(data), encoding="utf-8")


# -- export ----------------------------------------------------------------------------

class Exporter:
    def __init__(self):
        self.tables = read_tables(ROOT / "legacy/sql/gklinec_top5primary.sql")
        self.tables.update(read_tables(ROOT / "legacy/sql/gklinec_poll.sql"))
        self.check_mojibake()
        self.articles = {r["ID_"]: r for r in self.tables["Article"]}
        self.top5s = {r["ID_"]: r for r in self.tables["Top5"]}
        self.authors = {r["ID_"]: r for r in self.tables["Author"]}
        self.assign_paths()
        self.md = Converter(self.resolve_link)
        self.images = set()   # content images referenced by exported content

    def check_mojibake(self):
        for table, rows in self.tables.items():
            for row in rows:
                for col, value in row.items():
                    if isinstance(value, str) and MOJIBAKE.search(value):
                        raise ExportError(f"possible mojibake in {table} {row['ID_']}.{col}: "
                                          f"{MOJIBAKE.search(value).group()!r}")

    def assign_paths(self):
        """Give every item its filename: the slug of its title.

        Items in a section that share a title all get their author's slug appended
        (american-pie-2-brian, american-pie-2-bruce). If one author reused a title, those
        items are numbered in date order after that.
        """
        self.author_slug = {r["ID_"]: slugify(r["Name"]) for r in self.tables["Author"]}
        if len(set(self.author_slug.values())) != len(self.author_slug):
            raise ExportError("two authors have the same slug")

        def assign(rows, section_of):
            groups = {}
            for row in sorted(rows, key=lambda r: (r["Article_date"], r["ID_"])):
                groups.setdefault((section_of(row), slugify(row["Title"])), []).append(row)
            paths = {}
            for (section, base), group in groups.items():
                if len(group) == 1:
                    paths[group[0]["ID_"]] = f"{section}/{base}"
                    continue
                seen = {}
                for row in group:
                    slug = f"{base}-{self.author_slug[row['Author_ID_FK']]}"
                    seen[slug] = seen.get(slug, 0) + 1
                    if seen[slug] > 1:
                        slug = f"{slug}-{seen[slug]}"
                    paths[row["ID_"]] = f"{section}/{slug}"
            if len(set(paths.values())) != len(paths):
                raise ExportError("two items got the same filename")
            return paths

        self.article_path = assign(self.tables["Article"], lambda r: SECTIONS[r["Type"]])
        self.top5_path = assign(self.tables["Top5"], lambda r: "top5")

    def resolve_link(self, href):
        """Map a legacy internal link to a relref, so Hugo checks it at build time."""
        if re.match(r"https?://", href):
            return None
        for pattern, kind in LINK_PATTERNS:
            m = pattern.fullmatch(href)
            if m:
                break
        else:
            raise ConversionError(f"unrecognized internal link {href!r}")
        ident = int(m.group(1))
        if kind == "author":
            path = ident in self.author_slug and f"authors/{self.author_slug[ident]}"
        else:
            path = (self.article_path if kind == "article" else self.top5_path).get(ident)
        if not path:
            raise ConversionError(f"link {href!r} points to a missing {kind} {ident}")
        return f'{{{{< relref "{path}.md" >}}}}'

    def note_images(self, fields):
        for key in ("image", "image_full"):
            if fields.get(key):
                self.images.add(fields[key])

    # -- content types -----------------------------------------------------------------

    def export_articles(self):
        for ident, row in sorted(self.articles.items()):
            where = f"Article {ident}"
            section = SECTIONS[row["Type"]]
            front = {}
            if section == "reviews":
                front["type"] = row["Type"]
            front["title"] = plain(row["Title"])
            front["subtitle"] = plain(row["Subtitle"])
            front["author"] = self.author_slug[row["Author_ID_FK"]]
            front["date"] = date(row["Article_date"])
            if section != "other":
                front["rating"] = number(row["Rating"])
                front["release_year"] = row["Release_year"]
                front["starring"] = plain(row["Starring"])
            front["caption"] = plain(row["Caption"])
            if (row["Image"] or "").strip():
                front.update(parse_img(row["Image"], where))
            front["image_full"] = image_path_field(row["Image_fullsize"], where)
            if row["QA"] == 0:
                front["draft"] = True
            self.note_images(front)
            try:
                body = self.md.block(row["Text"] or "")
            except ConversionError as e:
                raise ExportError(f"{where}: {e}") from e
            write_page(CONTENT / f"{self.article_path[ident]}.md", front, body)

    def export_top5s(self):
        for ident, row in sorted(self.top5s.items()):
            where = f"Top5 {ident}"
            front = {
                "title": plain(row["Title"]),
                "author": self.author_slug[row["Author_ID_FK"]],
                "date": date(row["Article_date"]),
                "caption": plain(row["Caption"]),
            }
            if (row["Image"] or "").strip():
                front.update(parse_img(row["Image"], where))
            front["image_full"] = image_path_field(row["Image_fullsize"], where)
            if row["QA"] == 0:
                front["draft"] = True
            items, mentions = [], []
            for n in range(1, 6):
                item, extra = self.parse_item(row[f"Item{n}"], f"{where} Item{n}")
                if extra and n != 5:
                    raise ExportError(f"{where}: honorable mention outside the last item")
                items.append(item)
                mentions += extra
            front["items"] = items
            front["honorable_mentions"] = mentions or None
            self.note_images(front)
            try:
                body = self.md.block(row["Intro"] or "")
            except ConversionError as e:
                raise ExportError(f"{where}: {e}") from e
            write_page(CONTENT / f"{self.top5_path[ident]}.md", front, body)

    def parse_item(self, raw, where):
        """Split a list item into title, film (div.quote) and text (div/font.bodyText).

        Trailing div.headline / "Honorable Mentions:" blocks become honorable mentions.
        """
        raw = re.sub(r"<p>", "", raw.replace("\r\n", "\n"), flags=re.I)
        soup = BeautifulSoup(raw, "html.parser")
        entries = [{"title": [], "film": None, "text": None}]
        for node in soup.contents:
            cls = None if isinstance(node, NavigableString) else (node.get("class") or [None])[0]
            entry = entries[-1]
            if cls is None:
                if entry["film"] is None and entry["text"] is None:
                    entry["title"].append(str(node))
                elif str(node).strip():
                    raise ExportError(f"{where}: unexpected content after the item text: {node!r}")
            elif cls == "bodyText" and node.name in ("div", "font") and entry["text"] is None:
                entry["text"] = node.decode_contents()
            elif cls == "quote" and re.match(r"\s*Honorable Mentions?:\s*$", node.get_text()):
                entries.append({"title": [], "film": None, "text": None, "mention": True})
            elif cls == "quote" and entry["film"] is None and entry["text"] is None:
                entry["film"] = node.decode_contents()
            elif cls == "headline":
                heading = re.sub(r"^\s*Honorable Mentions?:\s*", "", node.decode_contents())
                entries.append({"title": [heading], "film": None, "text": None, "mention": True})
            else:
                raise ExportError(f"{where}: unexpected element {node!r}")

        def build(entry):
            try:
                out = {
                    "title": self.md.inline("".join(entry["title"])) or None,
                    "film": entry["film"] and self.md.inline(entry["film"]),
                    "text": entry["text"] and self.md.inline(entry["text"]),
                }
            except ConversionError as e:
                raise ExportError(f"{where}: {e}") from e
            return {k: v for k, v in out.items() if v}

        item = build(entries[0])
        if not item.get("title"):
            raise ExportError(f"{where}: item has no title")
        return item, [build(e) for e in entries[1:]]

    def export_authors(self):
        for ident, row in sorted(self.authors.items()):
            where = f"Author {ident}"
            image = (row["Image"] or "").strip() or None
            if image and not (WEB / "images" / image).is_file():
                raise ExportError(f"{where}: image {image} does not exist")
            front = {
                "name": plain(row["Name"]),
                "jobtitle": plain(row["Jobtitle"]),
                "image": image,
                "image_alt": row["Name"] if image else None,  # the legacy alt text
            }
            bio = row["Bio"] or ""
            body = None
            try:
                if "<table" in bio:
                    front["facts"] = self.parse_facts(bio, where)
                else:
                    body = self.md.block(bio)
            except ConversionError as e:
                raise ExportError(f"{where}: {e}") from e
            self.note_images(front)
            write_page(CONTENT / f"authors/{self.author_slug[ident]}.md", front, body)

    def parse_facts(self, bio, where):
        """Turn a key/value layout table into [{heading, items: [{label, value}]}]."""
        soup = BeautifulSoup(bio, "html.parser")
        if soup.find_all(string=lambda s: s.strip(), recursive=False):
            raise ExportError(f"{where}: text outside the bio table")
        groups = [{"heading": None, "items": []}]
        for tr in soup.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) == 1:
                heading = plain(cells[0].get_text())
                if heading:            # a row of &nbsp; is only a spacer
                    groups.append({"heading": heading, "items": []})
            elif len(cells) == 2:
                label = plain(cells[0].get_text())
                if not label.endswith(":"):
                    raise ExportError(f"{where}: label without a colon: {label!r}")
                groups[-1]["items"].append({
                    "label": label[:-1].strip(),
                    "value": self.md.inline(cells[1].decode_contents()),
                })
            else:
                raise ExportError(f"{where}: unexpected row {tr!r}")
        return [{k: v for k, v in g.items() if v} for g in groups if g["items"]]

    # -- data files --------------------------------------------------------------------

    def export_responses(self):
        out = []
        for row in sorted(self.tables["Response"], key=lambda r: r["ID_"]):
            where = f"Response {row['ID_']}"
            article, top5 = row["ARTICLE_ID_FK"] or 0, row["TOP5_ID_FK"] or 0
            if bool(article) == bool(top5):
                raise ExportError(f"{where}: must belong to exactly one item")
            item = self.top5_path.get(top5) if top5 else self.article_path.get(article)
            if (item is None) != (row["ID_"] in ORPHAN_RESPONSES):
                raise ExportError(f"{where}: orphan status does not match ORPHAN_RESPONSES")
            if item is None:
                continue
            out.append({
                "item": item,
                "author": self.author_slug[row["AUTHOR_ID_FK"]],
                "date": date(row["Response_date"]),
                "text": self.md.block(row["Text"]),
            })
        write_data("responses.yaml",
                   "# Legacy staff responses, read-only. Shown under `item` in this order.\n", out)
        return out

    def export_polls(self):
        out = []
        for row in sorted(self.tables["poll"], key=lambda r: r["Poll_date"]):
            options = []
            for n in range(1, 6):
                text = (row[f"Text{n}"] or "").strip()
                if text and text != "0":      # "0" is the legacy marker for no option
                    options.append({"text": self.md.inline(text), "votes": row[f"Votes{n}"]})
                elif row[f"Votes{n}"]:
                    raise ExportError(f"poll {row['ID_']}: votes for an empty option {n}")
            out.append({
                "date": date(row["Poll_date"]),
                "question": self.md.inline(row["Question"]),
                "options": options,
            })
        write_data("polls.yaml", "# Legacy polls, read-only archive with final results.\n", out)
        return out

    def export_quotes(self):
        """Merge the live rotator array (includes/quotes.js) with the dead Quote table.

        The rotator is what visitors saw, so its wording wins and its order comes first.
        Table-only quotes are appended in ID order.
        """
        # Served as iso-8859-1, but the bytes are Windows-1252 (0x92 is a curly apostrophe).
        js = (WEB / "includes/quotes.js").read_text(encoding="cp1252")
        rotator = []
        for m in re.finditer(r"^q\[(\d+)\] = '((?:[^'\\]|\\.)*)';\s*$", js, re.M):
            if int(m.group(1)) != len(rotator):
                raise ExportError(f"quotes.js: q[{m.group(1)}] out of sequence")
            rotator.append(re.sub(r"\\(.)", r"\1", m.group(2)))
        if len(rotator) != js.count("\nq["):
            raise ExportError("quotes.js: could not parse every q[] line")
        table = [r["Quote"] for r in sorted(self.tables["Quote"], key=lambda r: r["ID_"])]

        def key(text):
            text = BeautifulSoup(text, "html.parser").get_text().lower()
            text = text.translate(str.maketrans("‘’“”", "''\"\""))
            return re.sub(r"[^a-z0-9]+", " ", text).strip()

        merged, seen, report = [], {}, {"rotator": len(rotator), "table": len(table),
                                        "rotator_dupes": [], "table_only": [], "worded_differently": []}
        for origin, quotes in (("rotator", rotator), ("table", table)):
            for raw in quotes:
                q = self.split_quote(raw)
                k = key(q["text"])
                if k in seen:
                    if origin == "rotator":
                        report["rotator_dupes"].append(raw)
                    elif seen[k][1] != raw:
                        report["worded_differently"].append((seen[k][1], raw))
                    continue
                seen[k] = (q, raw)
                if origin == "table":
                    report["table_only"].append(raw)
                merged.append(q)
        write_data("quotes.yaml",
                   "# Home page quote rotator. Merged from includes/quotes.js and the Quote table.\n",
                   merged)
        return merged, report

    def split_quote(self, raw):
        """'"Line."  -- Source' -> {text: 'Line.', source: 'Source'}."""
        m = (re.fullmatch(r'(".*")\s*--\s*(.+)', raw, re.S)
             or re.fullmatch(r'(".*")\s+([^"]+)', raw, re.S))   # one quote has no "--"
        if not m:
            raise ExportError(f"cannot split quote {raw!r}")
        head, source = m.groups()
        # Plain text, not markdown: the rotator inserts quotes with textContent. The
        # outer quotation marks are left to the template.
        text, source = (plain(BeautifulSoup(x, "html.parser").get_text()) for x in (head[1:-1], source))
        return {"text": text, "source": source}

    # -- images ------------------------------------------------------------------------

    def copy_images(self):
        lowered = {}
        for name in self.images:
            if name.lower() in lowered:
                raise ExportError(f"image name collision: {name} and {lowered[name.lower()]}")
            lowered[name.lower()] = name
        overlap = self.images & set(THEME_IMAGES)
        if overlap:
            raise ExportError(f"images used as both content and theme: {sorted(overlap)}")
        reset_dir(CONTENT / "images")
        for name in sorted(self.images):
            shutil.copyfile(WEB / "images" / name, CONTENT / "images" / name)
        reset_dir(ROOT / "assets/images")
        for name in THEME_IMAGES:
            shutil.copyfile(WEB / "images" / name, ROOT / "assets/images" / name)
        for name in STATIC_FILES:
            shutil.copyfile(WEB / "images" / name, ROOT / "static" / name)

    def run(self):
        for section in OWNED_SECTIONS:
            reset_dir(CONTENT / section)
        self.export_articles()
        self.export_top5s()
        self.export_authors()
        responses = self.export_responses()
        polls = self.export_polls()
        quotes, qreport = self.export_quotes()
        self.copy_images()

        print(f"articles {len(self.articles)}, top fives {len(self.top5s)}, "
              f"authors {len(self.authors)}, responses {len(responses)}, polls {len(polls)}")
        drafts = [p for i, p in self.article_path.items() if self.articles[i]["QA"] == 0]
        drafts += [p for i, p in self.top5_path.items() if self.top5s[i]["QA"] == 0]
        print(f"drafts: {', '.join(drafts) or 'none'}")
        print(f"skipped orphan responses: {sorted(ORPHAN_RESPONSES)}")
        all_images = {p.name for p in (WEB / "images").iterdir() if p.is_file()}
        unused = all_images - self.images - set(THEME_IMAGES) - set(STATIC_FILES)
        print(f"images: {len(self.images)} content, {len(THEME_IMAGES)} theme, "
              f"{len(STATIC_FILES)} static, {len(unused)} of {len(all_images)} left in web/images")
        print(f"quotes: {len(quotes)} merged from {qreport['rotator']} in quotes.js "
              f"and {qreport['table']} in the Quote table")
        for raw in qreport["rotator_dupes"]:
            print(f"  duplicate in quotes.js, dropped: {raw}")
        for raw in qreport["table_only"]:
            print(f"  only in the table, added: {raw}")
        for js, tbl in qreport["worded_differently"]:
            print(f"  worded differently, kept quotes.js:\n    js:    {js}\n    table: {tbl}")


def reset_dir(path):
    """Empty a directory the exporter owns, keeping it in place."""
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            raise ExportError(f"unexpected directory {child}")
        child.unlink()


if __name__ == "__main__":
    try:
        Exporter().run()
    except (ExportError, ConversionError) as e:
        sys.exit(f"export failed: {e}")
