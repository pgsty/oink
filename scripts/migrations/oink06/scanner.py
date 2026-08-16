"""Line-oriented Markdown scanner: front matter, fences, shortcode tags.

The scanner never interprets Markdown beyond what the migrations need:

* front matter (``---`` / ``+++`` / JSON) is left untouched;
* fenced code (backtick or tilde, length >= 3, any indentation, inside list
  items included) is tracked so text inside a fence is never rewritten;
* shortcode tags (``{{< … >}}`` / ``{{% … %}}``) are parsed with their ordered
  parameters and matched to their closing tags with a per-name stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Iterator


FENCE_OPEN_RE = re.compile(r"^(?P<indent>(?:[ \t]*>)*[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
FRONT_MATTER_DELIMS = ("---", "+++")

# Leaf shortcodes that never have a closing tag even without a trailing `/`.
LEAF_SHORTCODES = frozenset(
    {
        "filetree/file",
        "gallery/image",
        "readfile",
        "include",
        "param",
        "_param",
        "badge",
        "kbd",
        "book-toc",
        "book-figures",
        "book-tables",
        "book-equations",
        "book-examples",
        "iframe",
        "contributors",
        "asciinema",
        "download",
        "release-card",
        "release-assets",
        "netlify",
        "td/site-build-info/netlify",
        "field-ref",
    }
)


class ScanError(ValueError):
    """Raised for malformed input the scanner refuses to guess about."""


@dataclass
class Param:
    name: str | None  # None for positional parameters
    value: str
    raw: str  # original token text


@dataclass
class Tag:
    """One shortcode tag occurrence."""

    delim: str  # '<' or '%'
    name: str
    closing: bool
    self_closing: bool
    params: list[Param]
    line: int  # 0-based line index
    start: int  # column of '{{'
    end: int  # column after '}}'
    raw: str

    def get(self, name: str, default: str | None = None) -> str | None:
        for param in self.params:
            if param.name == name:
                return param.value
        return default

    def has(self, name: str) -> bool:
        return any(param.name == name for param in self.params)

    def positional(self) -> list[str]:
        return [param.value for param in self.params if param.name is None]

    def is_named(self) -> bool:
        return any(param.name is not None for param in self.params)


def parse_params(text: str) -> list[Param]:
    """Parse the parameter section of a shortcode tag preserving order.

    Accepts ``name=value`` and positional values; values may be double-quoted
    (backslash escapes), single-quoted, backtick raw strings, or bare tokens.
    """

    params: list[Param] = []
    pos = 0
    length = len(text)
    while pos < length:
        char = text[pos]
        if char.isspace():
            pos += 1
            continue
        start = pos
        name: str | None = None
        match = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\s*=").match(text, pos)
        if match:
            name = match.group(0)[:-1].strip()
            pos = match.end()
            while pos < length and text[pos].isspace():
                pos += 1
        if pos >= length:
            if name is not None:
                params.append(Param(name, "", text[start:pos]))
            break
        quote = text[pos]
        if quote == '"':
            value_chars: list[str] = []
            pos += 1
            while pos < length and text[pos] != '"':
                if text[pos] == "\\" and pos + 1 < length:
                    nxt = text[pos + 1]
                    if nxt in '"\\':
                        value_chars.append(nxt)
                    elif nxt == "n":
                        value_chars.append("\n")
                    elif nxt == "t":
                        value_chars.append("\t")
                    else:
                        value_chars.append("\\" + nxt)
                    pos += 2
                    continue
                value_chars.append(text[pos])
                pos += 1
            if pos >= length:
                raise ScanError("unterminated double-quoted parameter")
            pos += 1
            value = "".join(value_chars)
        elif quote == "'":
            end = text.find("'", pos + 1)
            if end == -1:
                raise ScanError("unterminated single-quoted parameter")
            value = text[pos + 1 : end]
            pos = end + 1
        elif quote == "`":
            end = text.find("`", pos + 1)
            if end == -1:
                raise ScanError("unterminated raw parameter")
            value = text[pos + 1 : end]
            pos = end + 1
        else:
            end = pos
            while end < length and not text[end].isspace():
                end += 1
            value = text[pos:end]
            pos = end
        params.append(Param(name, value, text[start:pos]))
    return params


def quote(value: str) -> str:
    """Hugo-compatible double-quoted string with deterministic escaping."""

    return json.dumps(value, ensure_ascii=False)


def render_tag(delim: str, name: str, params: list[tuple[str, str]], *, closing: bool = False, self_closing: bool = False) -> str:
    close_delim = ">" if delim == "<" else "%"
    if closing:
        return "{{" + delim + " /" + name + " " + close_delim + "}}"
    rendered = " ".join(f"{key}={quote(value)}" if not _is_bare_literal(value) else f"{key}={value}" for key, value in params)
    body = name + ((" " + rendered) if rendered else "")
    suffix = " /" if self_closing else " "
    return "{{" + delim + " " + body + suffix + close_delim + "}}"


def _is_bare_literal(value: str) -> bool:
    return value in ("true", "false") or bool(re.fullmatch(r"-?[0-9]+", value))


def find_tag(text: str, pos: int) -> tuple[int, int, str] | None:
    """Locate the next shortcode tag at/after ``pos``.

    Returns ``(start, end, delim)`` where ``end`` is the index after ``}}``.
    Quotes inside the tag are honoured so ``>`` in a quoted value does not end
    the tag.
    """

    while True:
        start = text.find("{{", pos)
        if start == -1:
            return None
        if start + 2 >= len(text) or text[start + 2] not in "<%":
            pos = start + 2
            continue
        delim = text[start + 2]
        close_delim = ">" if delim == "<" else "%"
        index = start + 3
        length = len(text)
        while index < length:
            char = text[index]
            if char == '"':
                index += 1
                while index < length and text[index] != '"':
                    index += 2 if text[index] == "\\" else 1
                index += 1
                continue
            if char == "'":
                index = text.find("'", index + 1)
                if index == -1:
                    return None
                index += 1
                continue
            if char == "`":
                index = text.find("`", index + 1)
                if index == -1:
                    return None
                index += 1
                continue
            if char == close_delim and text.startswith("}}", index + 1):
                return start, index + 3, delim
            if char == "\n":
                break  # tags do not span lines in this corpus
            index += 1
        pos = start + 2


TAG_HEAD_RE = re.compile(r"\{\{([<%])\s*(/?)\s*([A-Za-z_][A-Za-z0-9_./-]*)")


def parse_tag_text(raw: str, line: int, start: int, end: int) -> Tag | None:
    match = TAG_HEAD_RE.match(raw)
    if not match:
        return None
    delim, closing, name = match.groups()
    inner = raw[match.end() : -3]
    self_closing = False
    stripped = inner.rstrip()
    if stripped.endswith("/"):
        self_closing = True
        stripped = stripped[:-1]
    params = parse_params(stripped) if not closing else []
    return Tag(delim, name, bool(closing), self_closing, params, line, start, end, raw)


@dataclass
class Fence:
    start: int  # line index of the opening fence
    end: int  # line index of the closing fence (== start when unterminated at EOF -> len-1)
    indent: str
    marker: str
    info: str


@dataclass
class Document:
    """A Markdown source split into lines with fence and front-matter maps."""

    text: str
    lines: list[str] = field(default_factory=list)
    newline: str = "\n"
    trailing_newline: bool = True
    front_matter_end: int = 0  # first content line index
    fences: list[Fence] = field(default_factory=list)
    in_fence: list[bool] = field(default_factory=list)  # per line, True for fence body AND fence markers

    @classmethod
    def parse(cls, text: str) -> "Document":
        newline = "\r\n" if "\r\n" in text else "\n"
        normalised = text.replace("\r\n", "\n")
        trailing = normalised.endswith("\n")
        lines = normalised.split("\n")
        if trailing:
            lines = lines[:-1]
        doc = cls(text=text, lines=lines, newline=newline, trailing_newline=trailing)
        doc._scan()
        return doc

    # -- scanning ---------------------------------------------------------
    def _scan(self) -> None:
        self.front_matter_end = self._front_matter_end()
        self.fences = []
        self.in_fence = [False] * len(self.lines)
        index = self.front_matter_end
        while index < len(self.lines):
            match = FENCE_OPEN_RE.match(self.lines[index])
            if match and (match.group("fence")[0] == "~" or "`" not in match.group("info")):
                marker = match.group("fence")
                indent = match.group("indent")
                closer = re.compile(r"^(?:[ \t]*>)*[ \t]*" + re.escape(marker[0]) + "{" + str(len(marker)) + ",}[ \t]*$")
                end = index + 1
                while end < len(self.lines) and not closer.match(self.lines[end]):
                    end += 1
                if end >= len(self.lines):
                    end = len(self.lines) - 1
                self.fences.append(Fence(index, end, indent, marker, match.group("info").strip()))
                for pos in range(index, end + 1):
                    self.in_fence[pos] = True
                index = end + 1
                continue
            index += 1

    def _front_matter_end(self) -> int:
        if not self.lines:
            return 0
        first = self.lines[0].strip()
        if first in FRONT_MATTER_DELIMS:
            for index in range(1, len(self.lines)):
                if self.lines[index].strip() == first:
                    return index + 1
            return 0
        if first.startswith("{") and not first.startswith("{{"):
            depth = 0
            for index, line in enumerate(self.lines):
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    return index + 1
        return 0

    # -- helpers ----------------------------------------------------------
    def rescan(self) -> None:
        """Rebuild the fence/front-matter maps after ``lines`` was mutated."""

        self._scan()

    def render(self) -> str:
        result = self.newline.join(self.lines)
        if self.trailing_newline:
            result += self.newline
        return result

    def fence_at(self, line: int) -> Fence | None:
        for fence in self.fences:
            if fence.start <= line <= fence.end:
                return fence
        return None

    def iter_tags(self, names: set[str] | None = None) -> Iterator[Tag]:
        """Yield shortcode tags outside fences and front matter, in order."""

        for index in range(self.front_matter_end, len(self.lines)):
            if self.in_fence[index]:
                continue
            line = self.lines[index]
            pos = 0
            while True:
                found = find_tag(line, pos)
                if not found:
                    break
                start, end, _ = found
                tag = parse_tag_text(line[start:end], index, start, end)
                pos = end
                if tag is None:
                    continue
                if names is None or tag.name in names:
                    yield tag

    def find_close(self, open_tag: Tag) -> Tag | None:
        """Find the closing tag matching ``open_tag`` (same name, nesting-aware)."""

        depth = 0
        for tag in self.iter_tags({open_tag.name}):
            if (tag.line, tag.start) <= (open_tag.line, open_tag.start):
                continue
            if tag.closing:
                if depth == 0:
                    return tag
                depth -= 1
            elif not tag.self_closing and tag.name not in LEAF_SHORTCODES:
                depth += 1
        return None

    def tag_alone(self, tag: Tag) -> bool:
        """True when the tag is the only content on its line (whitespace aside)."""

        line = self.lines[tag.line]
        return not line[: tag.start].strip() and not line[tag.end :].strip()

    def indent_of(self, line: int) -> str:
        text = self.lines[line]
        return text[: len(text) - len(text.lstrip(" \t"))]


def is_block_start(line: str) -> bool:
    """Lines that start a Markdown block (never lazy continuation of a quote)."""

    stripped = line.lstrip()
    if not stripped:
        return True
    return bool(re.match(r"([-*+]\s|\d+[.)]\s|#{1,6}\s|```|~~~|>|\{\{|<[A-Za-z/!]|\||\{[.#a-zA-Z])", stripped))
