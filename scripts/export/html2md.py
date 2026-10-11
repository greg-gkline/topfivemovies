"""Convert the legacy hand-written HTML fragments to Goldmark-flavored markdown.

The fragments use a small tag set (see the scan in README.md). Anything outside it
raises, so a new tag in the data fails the export instead of being dropped silently.

Underline has no markdown syntax. It is written as ++text++, Goldmark's "insert"
extra, which Hugo renders as <ins> when markup.goldmark.extensions.extras.insert is on.
"""

import re

from bs4 import BeautifulSoup, Comment, NavigableString

_PARA = "tfm-para"            # stand-in element for the legacy <P> paragraph hacks
_HARD = "\x01"                # hard line break marker, resolved per paragraph
_BLOCK = {"div", "blockquote", "h3", "hr", "ul", "ol", "table"}
_INLINE = {"i": "*", "em": "*", "b": "**", "strong": "**", "u": "++"}

# Character-level escapes for text nodes. `+` is escaped only when doubled, since
# that is the only form that means something (the insert extra).
_TEXT_ESCAPES = [
    (re.compile(r"([\\`*_\[\]~])"), r"\\\1"),
    (re.compile(r"\+\+"), r"\\+\\+"),
    (re.compile(r"<(?=[A-Za-z/!?])"), r"\\<"),
    (re.compile(r"&(?=#?\w+;)"), r"\\&"),
    # Bare URLs were plain text on the legacy site. Keep Goldmark's linkify off them.
    (re.compile(r"(?<=\w):(?=//)"), r"\\:"),
    (re.compile(r"\b([Ww]{3})\."), r"\1\\."),
]

# Things that mean something at the start of a line, after soft wrapping.
_LINE_START = [
    (re.compile(r"^([-+*])(?=\s|$)"), r"\\\1"),          # bullet list
    (re.compile(r"^(\d{1,9})([.)])(?=\s|$)"), r"\1\\\2"),  # ordered list
    (re.compile(r"^(#{1,6})(?=\s|$)"), r"\\\1"),           # heading
    (re.compile(r"^>"), r"\\>"),                          # blockquote
    (re.compile(r"^([=-]+)\s*$"), r"\\\1"),               # setext underline
]


class ConversionError(ValueError):
    pass


def _escape_text(s):
    for pattern, repl in _TEXT_ESCAPES:
        s = pattern.sub(repl, s)
    return s


def _escape_line_start(line):
    for pattern, repl in _LINE_START:
        line = pattern.sub(repl, line)
    return line


def _prepare(html):
    html = html.replace("\r\n", "\n").replace("\r", "\n")
    # <P> is used as a paragraph separator, <p>/</p> sometimes as real tags. Either way
    # every one of them is a paragraph boundary.
    return re.sub(r"</?p\b[^>]*>", f"<{_PARA}></{_PARA}>", html, flags=re.I)


def _wrap(marker, inner):
    """Wrap inline markdown in a delimiter, keeping edge whitespace outside it."""
    m = re.fullmatch(r"(\s*)(.*?)(\s*)", inner, re.S)
    lead, body, trail = m.groups()
    if not body:
        return inner
    return f"{lead}{marker}{body}{marker}{trail}"


class Converter:
    def __init__(self, link_resolver=None):
        # link_resolver(href) -> markdown link destination, or None to keep href
        self.link_resolver = link_resolver or (lambda href: None)

    # -- public API --------------------------------------------------------------

    def block(self, html):
        """Markdown for a fragment that may contain paragraphs and block elements."""
        soup = BeautifulSoup(_prepare(html), "html.parser")
        return "\n\n".join(self._blocks(soup.contents))

    def inline(self, html):
        """Single-line markdown for a short fragment (a front matter field)."""
        md = self.block(html)
        if "\n\n" in md:
            raise ConversionError(f"expected a single paragraph: {html!r}")
        # Soft breaks become spaces; hard breaks (a trailing backslash) stay.
        return re.sub(r"(?<!\\)\n", " ", md)

    # -- internals ---------------------------------------------------------------

    def _blocks(self, nodes):
        out, run = [], []

        def flush():
            para = self._paragraph("".join(run))
            run.clear()
            if para:
                out.append(para)

        for node in nodes:
            if isinstance(node, Comment):
                continue
            if isinstance(node, NavigableString):
                run.append(_escape_text(str(node)))
                continue
            name = node.name
            if name == _PARA:
                flush()
            elif name == "br":
                run.append(_HARD)
            elif name in _BLOCK:
                flush()
                out.extend(self._block_element(node))
            else:
                run.append(self._inline_element(node))
        flush()
        return out

    def _block_element(self, node):
        name = node.name
        if name == "div":
            return self._blocks(node.contents)
        if name == "h3":
            return ["### " + self._paragraph(self._inline_children(node)).replace("\n", " ")]
        if name == "hr":
            return ["---"]
        if name == "blockquote":
            inner = "\n\n".join(self._blocks(node.contents))
            return ["\n".join(("> " + line).rstrip() for line in inner.split("\n"))]
        if name in ("ul", "ol"):
            items = []
            for i, li in enumerate(node.find_all("li", recursive=False), 1):
                marker = "- " if name == "ul" else f"{i}. "
                body = "\n\n".join(self._blocks(li.contents))
                pad = " " * len(marker)
                lines = body.split("\n")
                items.append(marker + lines[0] + "".join(
                    "\n" + (pad + line if line else "") for line in lines[1:]))
            return ["\n".join(items)]
        raise ConversionError(f"unsupported block element <{name}>")

    def _inline_children(self, node):
        parts = []
        for child in node.contents:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                parts.append(_escape_text(str(child)))
            elif child.name == "br":
                parts.append(_HARD)
            elif child.name in _BLOCK or child.name == _PARA:
                raise ConversionError(f"block element <{child.name}> inside <{node.name}>")
            else:
                parts.append(self._inline_element(child))
        return "".join(parts)

    def _inline_element(self, node):
        name = node.name
        inner = self._inline_children(node)
        if name in _INLINE:
            return _wrap(_INLINE[name], inner)
        if name == "a":
            href = node.get("href", "").strip()
            dest = self.link_resolver(href) or href
            m = re.fullmatch(r"(\s*)(.*?)(\s*)", inner, re.S)
            return f"{m.group(1)}[{m.group(2)}]({dest}){m.group(3)}"
        if name == "span":
            # The one styled span (a spoiler warning) is bold red. Keep the bold.
            style = node.get("style", "")
            return _wrap("**", inner) if "bold" in style else inner
        if name == "font":
            return inner
        raise ConversionError(f"unsupported inline element <{name}>")

    def _paragraph(self, text):
        # HTML whitespace rules: a run containing a newline is a soft break, any other
        # run is one space. Lines are stripped so indentation never becomes a code block.
        text = re.sub(r"[ \t]*\n\s*", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(rf"\s*{_HARD}\s*", _HARD, text).strip(" \n" + _HARD)
        text = text.replace(_HARD, _HARD + "\n")
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(_escape_line_start(line) for line in lines if line)
        return text.replace(_HARD, "\\")
