"""alert / details / pageinfo shortcodes and raw <details> -> GFM/Obsidian callouts.

    {{% alert title="Note" color="info" %}}      >  [!NOTE] Note
    body                                        >  body
    {{% /alert %}}

    {{% details title="Output" %}}            ->  > [!DETAILS]- Output
    <details><summary>X</summary>…</details>  ->  > [!DETAILS]- X

Innermost blocks are converted first, so nested alerts become nested
callouts (``> > [!NOTE]``). Anything the module cannot express is left
untouched and reported.
"""

from __future__ import annotations

import re

from ..base import QUOTE_PREFIX_RE, Result, Transformation, dedent_lines, ensure_blank_around, strip_blank_edges, strip_prefix
from ..scanner import Document, Tag, is_block_start

COLOR_TO_TYPE = {
    "info": "NOTE",
    "warning": "WARNING",
    "danger": "CAUTION",
    "success": "TIP",
    "primary": "IMPORTANT",
    "secondary": "NOTE",
}
NAMES = {"alert", "details", "pageinfo"}
DETAILS_OPEN_RE = re.compile(r"^(?P<indent>[ \t]*)<details(?P<attrs>[^>]*)>(?P<rest>.*)$")
DETAILS_CLOSE_RE = re.compile(r"^[ \t]*</details>(?:\s*<br\s*/?>)*\s*$")
SUMMARY_RE = re.compile(r"^[ \t]*<summary>(?P<title>.*)</summary>\s*$")
SUMMARY_INLINE_RE = re.compile(r"^<summary>(?P<title>.*?)</summary>")
BLOCK_HTML_RE = re.compile(
    r"^[ \t]*<(?:/?)(?:div|table|details|summary|p|ul|ol|li|pre|figure|iframe|blockquote|h[1-6]|script|style|section|article|img|video|form|dl|nav|aside|hr|br)\b",
    re.I,
)


def _title_from_html(raw: str) -> str | None:
    """Lower simple inline HTML in a <summary> to Markdown; None when unsafe."""

    text = raw.strip()
    text = re.sub(r"<code>(.*?)</code>", lambda m: "`" + m.group(1) + "`", text)
    text = re.sub(r"<(?:b|strong)>(.*?)</(?:b|strong)>", lambda m: "**" + m.group(1) + "**", text)
    text = re.sub(r"<(?:i|em)>(.*?)</(?:i|em)>", lambda m: "*" + m.group(1) + "*", text)
    if re.search(r"<[A-Za-z/!]", text):
        return None
    return text


def _quote(lines: list[str]) -> list[str]:
    return [("> " + line) if line.strip() else ">" for line in lines]


class CalloutTransformation(Transformation):
    key = "callout"
    description = "alert/details/pageinfo shortcodes and raw <details> -> > [!TYPE] callouts"
    residual_patterns = (
        r"\{\{[<%]\s*/?(?:alert|details|pageinfo)\b",
        r"^[ \t]*<details\b",
    )

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        if self._apply_shortcodes(path, doc, result):
            result.text = doc.render()
            return
        if self._apply_raw_details(path, doc, result):
            result.text = doc.render()

    # -- shortcode form ---------------------------------------------------
    def _apply_shortcodes(self, path: str, doc: Document, result: Result) -> bool:
        opens = [tag for tag in doc.iter_tags(NAMES) if not tag.closing]
        if not opens:
            return False
        blocks: list[tuple[Tag, Tag]] = []
        for open_tag in opens:
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                if not any(f.line == open_tag.line + 1 and f.kind == self.key for f in result.findings):
                    self.note(result, path, open_tag.line, self.key, f"unclosed {open_tag.name}", open_tag.raw)
                continue
            blocks.append((open_tag, close_tag))
        # innermost first: blocks that contain no other candidate block
        innermost = []
        for open_tag, close_tag in blocks:
            nested = any(
                (o.line, o.start) > (open_tag.line, open_tag.start) and (c.line, c.start) < (close_tag.line, close_tag.start)
                for o, c in blocks
                if o is not open_tag
            )
            if not nested:
                innermost.append((open_tag, close_tag))
        changed = False
        # bottom-up so earlier indices stay valid
        for open_tag, close_tag in sorted(innermost, key=lambda pair: (pair[0].line, pair[0].start), reverse=True):
            if self._convert_block(path, doc, result, open_tag, close_tag):
                changed = True
        return changed

    def _convert_block(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> bool:
        lines = doc.lines
        open_line = lines[open_tag.line]
        close_line = lines[close_tag.line]
        prefix_match = QUOTE_PREFIX_RE.match(open_line)
        if prefix_match.end() != open_tag.start:
            self.note(result, path, open_tag.line, self.key, f"{open_tag.name} tag is not the first thing on its line", open_line)
            return False
        if close_line[close_tag.end :].strip():
            self.note(result, path, close_tag.line, self.key, f"text after closing {open_tag.name} tag", close_line)
            return False
        indent = open_line[: open_tag.start]  # whitespace and/or `> ` markers
        # header -----------------------------------------------------------
        title = (open_tag.get("title") or "").strip()
        if open_tag.name == "alert":
            color = (open_tag.get("color") or "primary").strip().lower()
            if color not in COLOR_TO_TYPE:
                self.note(result, path, open_tag.line, self.key, f"alert color {color!r} has no callout type", open_tag.raw)
                return False
            marker = "[!" + COLOR_TO_TYPE[color] + "]"
            result.counts[f"alert.color.{color}"] += 1
        elif open_tag.name == "details":
            closed_param = open_tag.get("closed")
            closed = True
            if closed_param is not None:
                closed = closed_param.strip().lower() != "false"
            marker = "[!DETAILS]" + ("-" if closed else "+")
        else:  # pageinfo
            marker = "[!NOTE]"
        if title and ("\n" in title):
            self.note(result, path, open_tag.line, self.key, "multi-line title", open_tag.raw)
            return False
        unknown = [p.name for p in open_tag.params if p.name not in {"title", "color", "closed"} and p.name is not None]
        if unknown or open_tag.positional():
            self.note(result, path, open_tag.line, self.key, f"unsupported {open_tag.name} parameters {unknown or open_tag.positional()}", open_tag.raw)
            return False
        header = indent + "> " + marker + ((" " + title) if title else "")
        # body -------------------------------------------------------------
        if open_tag.line == close_tag.line:
            between = open_line[open_tag.end : close_tag.start]
            body_lines = [between] if between.strip() else []
        else:
            body_lines = []
            head_rest = open_line[open_tag.end :]
            if head_rest.strip():
                body_lines.append(head_rest.strip())
            body_lines.extend(lines[open_tag.line + 1 : close_tag.line])
            tail = strip_prefix(close_line[: close_tag.start], indent)
            if tail.strip():
                body_lines.append(tail)
        body = strip_blank_edges([strip_prefix(line, indent) for line in body_lines])
        quoted = _quote(body)
        if ">" in indent:
            new_lines = [header] + [(indent + line) if line != ">" else (indent.rstrip() + " >") for line in quoted]
        else:
            new_lines = [header] + [indent + line for line in quoted]
        result.counts[open_tag.name] += 1
        if title:
            result.counts[f"{open_tag.name}.title"] += 1
        self.replace_lines(doc, open_tag.line, close_tag.line, new_lines)
        if ">" in indent:
            self._separate_in_quote(doc, open_tag.line, open_tag.line + len(new_lines) - 1, indent)
        else:
            ensure_blank_around(doc, open_tag.line, open_tag.line + len(new_lines) - 1)
        return True

    @staticmethod
    def _separate_in_quote(doc: Document, start: int, end: int, prefix: str) -> None:
        """Inside an enclosing blockquote, separate the new nested callout with bare quote lines."""

        lines = doc.lines
        blank = prefix.rstrip()
        if end + 1 < len(lines):
            content = strip_prefix(lines[end + 1], prefix)
            if content.strip() and (not is_block_start(content) or content.lstrip().startswith(">")):
                lines.insert(end + 1, blank)
        if start > 0:
            content = strip_prefix(lines[start - 1], prefix)
            if content.strip() and (not is_block_start(content) or content.lstrip().startswith(">")):
                lines.insert(start, blank)
        doc.rescan()

    # -- raw <details> ----------------------------------------------------
    def _apply_raw_details(self, path: str, doc: Document, result: Result) -> bool:
        lines = doc.lines
        candidates = []
        for index in range(doc.front_matter_end, len(lines)):
            if doc.in_fence[index]:
                continue
            match = DETAILS_OPEN_RE.match(lines[index])
            if match:
                candidates.append((index, match))
        if not candidates:
            return False
        changed = False
        for index, match in reversed(candidates):
            if self._convert_raw(path, doc, result, index, match):
                changed = True
        return changed

    def _convert_raw(self, path: str, doc: Document, result: Result, start: int, match: re.Match) -> bool:
        lines = doc.lines
        indent = match.group("indent")
        attrs = match.group("attrs").strip()
        rest = match.group("rest").strip()
        if attrs and attrs != "open":
            self.note(result, path, start, "rawdetails", f"<details> with attributes {attrs!r}", lines[start])
            return False
        title = ""
        head_body: list[str] = []  # content on the <details> line after the tag
        summary = SUMMARY_INLINE_RE.match(rest)
        if summary:
            lowered = _title_from_html(summary.group("title"))
            if lowered is None:
                self.note(result, path, start, "rawdetails", "summary contains HTML that has no Markdown form", lines[start])
                return False
            title = lowered
            rest = rest[summary.end() :].strip()
        rest = re.sub(r"^(?:<br\s*/?>\s*)+", "", rest)
        one_line_close = False
        close_match = re.search(r"</details>(?:\s*<br\s*/?>)*\s*$", rest)
        if close_match:
            rest = rest[: close_match.start()].strip()
            one_line_close = True
        if rest:
            if BLOCK_HTML_RE.match(rest) or "<summary" in rest or "<details" in rest:
                self.note(result, path, start, "rawdetails", "unsupported content on the <details> line", lines[start])
                return False
            head_body.append(rest)
        if one_line_close:
            end = start
        else:
            end = None
            for index in range(start + 1, len(lines)):
                if doc.in_fence[index]:
                    continue
                if DETAILS_OPEN_RE.match(lines[index]):
                    self.note(result, path, start, "rawdetails", "nested <details>", lines[start])
                    return False
                if DETAILS_CLOSE_RE.match(lines[index]):
                    end = index
                    break
            if end is None:
                self.note(result, path, start, "rawdetails", "unclosed <details>", lines[start])
                return False
        body_start = start + 1
        if not title and end > start:
            first = next((i for i in range(start + 1, end) if lines[i].strip()), None)
            if first is not None:
                summary = SUMMARY_RE.match(lines[first])
                if summary:
                    lowered = _title_from_html(summary.group("title"))
                    if lowered is None:
                        self.note(result, path, first, "rawdetails", "summary contains HTML that has no Markdown form", lines[first])
                        return False
                    title = lowered
                    body_start = first + 1
                elif "<summary" in lines[first]:
                    self.note(result, path, first, "rawdetails", "multi-line or attributed <summary>", lines[first])
                    return False
        for index in range(body_start, end):
            if doc.in_fence[index]:
                continue
            if BLOCK_HTML_RE.match(lines[index]):
                self.note(result, path, index, "rawdetails", "block-level HTML inside <details> body", lines[index])
                return False
        body = head_body + (lines[body_start:end] if end > start else [])
        marker = "[!DETAILS]" + ("+" if attrs == "open" else "-")
        header = indent + "> " + marker + ((" " + title) if title else "")
        quoted = [indent + line for line in _quote(strip_blank_edges(dedent_lines(body, indent)))]
        new_lines = [header] + quoted
        result.counts["rawdetails"] += 1
        self.replace_lines(doc, start, end, new_lines)
        ensure_blank_around(doc, start, start + len(new_lines) - 1)
        return True
