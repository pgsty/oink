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
from ..scanner import Document, Tag
from .callout import CalloutTransformation, _quote

NAMES = {"social"}
PARAMS = ("author", "handle", "avatar", "date", "url", "platform")
ATTRIBUTES = ("avatar", "date", "url", "platform")
INLINE_SPECIALS_RE = re.compile(r"([\\`*_\[\]<>&~])")


def _plain(value: str) -> str:
    return re.sub(r"[\r\n\t]+", " ", value).strip()


def _title(author: str, handle: str) -> str:
    parts = []
    if author:
        parts.append(INLINE_SPECIALS_RE.sub(r"\\\1", author))
    if handle:
        parts.append(f"`` {handle} ``" if "`" in handle else f"`{handle}`")
    return " ".join(parts)


class SocialTransformation(Transformation):
    key = "social"
    description = "social shortcodes (1.7.0) -> > [!SOCIAL] callouts with block attributes"
    residual_patterns = (r"\{\{[<%]\s*/?social\b",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        opens = [tag for tag in doc.iter_tags(NAMES) if not tag.closing]
        if not opens:
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
        changed = False
        # bottom-up so earlier indices stay valid
        for (open_tag, close_tag), nested in sorted(innermost, key=lambda item: (item[0][0].line, item[0][0].start), reverse=True):
            if self._convert(path, doc, result, open_tag, close_tag, nested):
                changed = True
        if changed:
            result.text = doc.render()

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
        unknown = [p.name for p in open_tag.params if p.name is not None and p.name not in PARAMS]
        if unknown or open_tag.positional():
            self.note(result, path, open_tag.line, self.key, f"unsupported social parameters {unknown or open_tag.positional()}", open_tag.raw)
            return False
        values = {name: _plain(open_tag.get(name) or "") for name in PARAMS}
        if any('"' in values[name] for name in ATTRIBUTES):
            self.note(result, path, open_tag.line, self.key, "a social value contains a double quote", open_tag.raw)
            return False
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
        if ">" in indent:
            CalloutTransformation._separate_in_quote(doc, open_tag.line, end, indent)
        else:
            ensure_blank_around(doc, open_tag.line, end)
        return True
