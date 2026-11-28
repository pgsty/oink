"""social shortcode (OINK 1.7.0) -> the native ``> [!SOCIAL]`` callout.

    {{< social author="Ada" handle="@ada" avatar="a.webp" url="https://x.com/ada/status/1" >}}
    The post text.
    {{< /social >}}

becomes

    > [!SOCIAL] Ada `@ada`
    >
    > The post text.
    {avatar="a.webp" url="https://x.com/ada/status/1" platform="x"}

The title carries the author as Markdown text and the handle as a code span;
avatar, date, url and platform become block attributes. The shortcode drew X
on a top-level card without ``platform``; the callout names no platform it is
not given, so that default is written out. A nested card defaulted to none and
stays without one. Innermost cards convert first, so a quoted post becomes a
nested callout (``> > [!SOCIAL]``). Anything the module cannot express is left
untouched and reported.
"""

from __future__ import annotations

import re
import textwrap

from ..base import QUOTE_PREFIX_RE, Result, Transformation, ensure_blank_around, strip_blank_edges, strip_prefix
from ..scanner import Document, Tag, find_tag, parse_tag_text
from .callout import CalloutTransformation, _quote

NAMES = {"social"}
PARAMS = ("author", "handle", "avatar", "date", "url", "platform")
ATTRIBUTES = ("avatar", "date", "url", "platform")
INLINE_SPECIALS_RE = re.compile(r"([\\`*_\[\]<>&~|])")
SPLIT_OPEN_RE = re.compile(r"\{\{[<%]\s*social\b")
# A split opening tag closes within this many lines or is left alone.
SPLIT_LIMIT = 20


def _plain(value: str) -> str:
    return re.sub(r"[\r\n\t]+", " ", value).strip()


def _escape_author(author: str) -> str:
    """Plain text as inline Markdown, as the shortcode printed it: syntax and
    GFM autolinks (URLs, ``www.`` and e-mail addresses) are neutralised."""

    text = INLINE_SPECIALS_RE.sub(r"\\\1", author)
    text = text.replace("://", "\\://")
    text = re.sub(r"(?i)(^|[^0-9A-Za-z_])(www)\.", r"\1\2\\.", text)
    return re.sub(r"([A-Za-z0-9.+_-])@", r"\1\\@", text)


def _code(handle: str) -> str:
    """A code span that holds any backtick run in the handle."""

    if "`" not in handle:
        return f"`{handle}`"
    fence = "`" * (max(len(run) for run in re.findall(r"`+", handle)) + 1)
    return f"{fence} {handle} {fence}"


def _title(author: str, handle: str) -> str:
    parts = []
    if author:
        parts.append(_escape_author(author))
    if handle:
        parts.append(_code(handle))
    return " ".join(parts)


class SocialTransformation(Transformation):
    key = "social"
    description = "social shortcodes (1.7.0) -> > [!SOCIAL] callouts with block attributes"
    residual_patterns = (r"\{\{[<%]\s*/?social\b",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        joined = self._join_split_tags(path, doc, result)
        opens = [tag for tag in doc.iter_tags(NAMES) if not tag.closing]
        if not opens:
            if joined:
                result.text = doc.render()
            return
        blocks: list[tuple[Tag, Tag]] = []
        for open_tag in opens:
            if open_tag.self_closing:
                blocks.append((open_tag, open_tag))
                continue
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed social", open_tag.raw)
                continue
            blocks.append((open_tag, close_tag))

        def contains(outer: tuple[Tag, Tag], inner: tuple[Tag, Tag]) -> bool:
            (o_open, o_close), (i_open, i_close) = outer, inner
            return (i_open.line, i_open.start) > (o_open.line, o_open.start) and (i_close.line, i_close.start) < (o_close.line, o_close.start)

        innermost = []
        for block in blocks:
            if any(contains(block, other) for other in blocks if other is not block):
                continue
            nested = any(contains(other, block) for other in blocks if other is not block)
            innermost.append((block, nested))
        changed = joined
        # bottom-up so earlier indices stay valid
        for (open_tag, close_tag), nested in sorted(innermost, key=lambda item: (item[0][0].line, item[0][0].start), reverse=True):
            if self._convert(path, doc, result, open_tag, close_tag, nested):
                changed = True
        # Every social tag still in the file breaks the build: report the ones
        # no finding names yet (the card around a refused one, its closing tag).
        noted = {finding.line - 1 for finding in result.findings if finding.kind == self.key}
        for tag in doc.iter_tags(NAMES):
            if tag.line not in noted:
                noted.add(tag.line)
                self.note(result, path, tag.line, self.key, "social shortcode left unconverted", doc.lines[tag.line])
        if changed:
            result.text = doc.render()

    def _join_split_tags(self, path: str, doc: Document, result: Result) -> bool:
        """Put an opening tag that spans lines (the 1.7.0 docs wrapped long
        ones) on one line, so it converts like any other. A tag the
        conversion would refuse stays as written and is reported."""

        joined = False
        index = doc.front_matter_end
        while index < len(doc.lines):
            line = doc.lines[index]
            match = None if doc.in_fence[index] else SPLIT_OPEN_RE.search(line)
            if not match or find_tag(line, match.start()):
                index += 1
                continue
            prefix = QUOTE_PREFIX_RE.match(line).group(0)
            text, last, found = line.rstrip(), index, None
            while last + 1 < len(doc.lines) and last - index < SPLIT_LIMIT and not doc.in_fence[last + 1]:
                last += 1
                text += " " + strip_prefix(doc.lines[last], prefix).strip()
                found = find_tag(text, match.start())
                if found:
                    break
            tag = parse_tag_text(text[found[0] : found[1]], index, found[0], found[1]) if found else None
            if tag is None or self._refusal(tag):
                self.note(result, path, index, self.key, "social tag spans lines and cannot be joined safely", line)
                index += 1
                continue
            self.replace_lines(doc, index, last, [text])
            joined = True
            index += 1
        return joined

    @staticmethod
    def _refusal(open_tag: Tag) -> str:
        """Why a social opening tag cannot become a callout, or ''."""

        unknown = [p.name for p in open_tag.params if p.name is not None and p.name not in PARAMS]
        if unknown or open_tag.positional():
            return f"unsupported social parameters {unknown or open_tag.positional()}"
        if any('"' in _plain(open_tag.get(name) or "") for name in ATTRIBUTES):
            return "a social value contains a double quote"
        return ""

    def _convert(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag, nested: bool) -> bool:
        lines = doc.lines
        open_line = lines[open_tag.line]
        close_line = lines[close_tag.line]
        if QUOTE_PREFIX_RE.match(open_line).end() != open_tag.start:
            self.note(result, path, open_tag.line, self.key, "social tag is not the first thing on its line", open_line)
            return False
        if close_line[close_tag.end :].strip():
            self.note(result, path, close_tag.line, self.key, "text after the closing social tag", close_line)
            return False
        refusal = self._refusal(open_tag)
        if refusal:
            self.note(result, path, open_tag.line, self.key, refusal, open_tag.raw)
            return False
        values = {name: _plain(open_tag.get(name) or "") for name in PARAMS}
        if not nested and not values["platform"]:
            values["platform"] = "x"
            result.counts["social.platform.x"] += 1
        indent = open_line[: open_tag.start]  # whitespace and/or `> ` markers
        title = _title(values["author"], values["handle"])
        header = indent + "> [!SOCIAL]" + ((" " + title) if title else "")
        # body -------------------------------------------------------------
        body_lines: list[str] = []
        if open_tag is close_tag:
            pass
        elif open_tag.line == close_tag.line:
            between = open_line[open_tag.end : close_tag.start]
            if between.strip():
                body_lines = [between.strip()]
        else:
            head_rest = open_line[open_tag.end :]
            if head_rest.strip():
                body_lines.append(head_rest.strip())
            body_lines.extend(strip_prefix(line, indent) for line in lines[open_tag.line + 1 : close_tag.line])
            tail = strip_prefix(close_line[: close_tag.start], indent)
            if tail.strip():
                body_lines.append(tail)
        # The shortcode read its body deindented (.InnerDeindent).
        body = strip_blank_edges(textwrap.dedent("\n".join(body_lines)).split("\n")) if body_lines else []
        quoted = _quote(([""] + body) if body else [])
        attrs = " ".join(f'{name}="{values[name]}"' for name in ATTRIBUTES if values[name])
        if ">" in indent:
            new_lines = [header] + [(indent + line) if line != ">" else (indent.rstrip() + " >") for line in quoted]
        else:
            new_lines = [header] + [indent + line for line in quoted]
        if attrs:
            new_lines.append(indent + "{" + attrs + "}")
        result.counts["social"] += 1
        if nested:
            result.counts["social.nested"] += 1
        self.replace_lines(doc, open_tag.line, close_tag.line, new_lines)
        end = open_tag.line + len(new_lines) - 1
        # A card without an attribute line ends on a quoted line, which the
        # next line would continue lazily (a table, a shortcode, an HTML
        # block): always close it with a blank or a bare quote line.
        if not attrs and end + 1 < len(doc.lines) and strip_prefix(doc.lines[end + 1], indent).strip():
            doc.lines.insert(end + 1, indent.rstrip() if ">" in indent else "")
            doc.rescan()
        if ">" in indent:
            CalloutTransformation._separate_in_quote(doc, open_tag.line, end, indent)
        else:
            ensure_blank_around(doc, open_tag.line, end)
        return True
