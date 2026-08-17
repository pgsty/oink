"""filetree shortcodes and the interim ``{.filetree}`` list -> ```filetree fence.

    {{< filetree label="x" >}}                      ```filetree {title="x"}
      {{< filetree/folder name="content" open=true   - content/                # 0755
                          comment="0755" >}}    ->      - _index.md            # landing
        {{< filetree/file name="_index.md"          ```
                          comment="landing" >}}
      {{< /filetree/folder >}}
    {{< /filetree >}}

    - content/ — 0755                              ```filetree
      - [_index.md](/docs/) — landing        ->     - content/                # 0755
    {.filetree}                                       - [_index.md](/docs/)   # landing
                                                     ```

Shortcode mapping: ``label`` -> ``title``; ``open`` (0.4 default closed) ->
``{open=false}`` unless ``open=true``; ``icon`` -> ``{icon="…"}``; ``color`` ->
``{tone=…}`` (``primary`` -> ``info``, ``secondary`` -> ``neutral``); ``comment``
-> ``# comment``; ``link`` -> ``[name](link)``. List mapping: `` — `` splits the
description off; Markdown escapes and emphasis / code-span wrappers around a
whole name or description are removed. Comments are aligned in one column.
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, ensure_blank_around
from ..scanner import Document, Tag

TONE_MAP = {
    "neutral": "neutral",
    "info": "info",
    "success": "success",
    "warning": "warning",
    "danger": "danger",
    "primary": "info",
    "secondary": "neutral",
}
LIST_ITEM_RE = re.compile(r"^(?P<indent>[ \t]*)[-*+][ \t]+(?P<text>\S.*)$")
MARKER_RE = re.compile(r"^[ \t]*\{\.filetree\}[ \t]*$")
UNESCAPE_RE = re.compile(r"\\([*`\[\]<_#{}\\])")
WRAP_RE = re.compile(r"^(\*\*|__|\*|_|`)(.+)\1$")
LINK_RE = re.compile(r"^\[([^\]]+)\]\(([^)\s]+)\)$")


def unwrap(text: str) -> str:
    """Drop one emphasis / code-span wrapper around the whole text and Markdown escapes."""

    text = text.strip()
    match = WRAP_RE.match(text)
    if match:
        text = match.group(2).strip()
    return UNESCAPE_RE.sub(r"\1", text)


def align_comments(rows: list[tuple[str, str, str]]) -> list[str]:
    """rows of (entry, comment, attrs) -> lines with `#` comments in one column."""

    width = max((len(entry) for entry, comment, _ in rows if comment), default=0)
    out = []
    for entry, comment, attrs in rows:
        line = entry
        if comment:
            line = f"{entry.ljust(width)}   # {comment}"
        if attrs:
            line = f"{line}   {attrs}"
        out.append(line.rstrip())
    return out


class FileTreeTransformation(Transformation):
    key = "filetree"
    description = "filetree shortcode family and {.filetree} lists -> ```filetree fence"
    residual_patterns = (r"\{\{[<%]\s*/?filetree\b", r"^[ \t]*\{\.filetree\}[ \t]*$")

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        changed = False
        opens = [tag for tag in doc.iter_tags({"filetree"}) if not tag.closing]
        for open_tag in reversed(opens):
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed filetree", open_tag.raw)
                continue
            if self._convert_shortcode(path, doc, result, open_tag, close_tag):
                changed = True
        if self._convert_lists(path, doc, result):
            changed = True
        if changed:
            result.text = doc.render()

    # -- shortcode family -----------------------------------------------------
    def _convert_shortcode(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> bool:
        lines = doc.lines
        if lines[open_tag.line][: open_tag.start].strip() or lines[close_tag.line][close_tag.end :].strip():
            self.note(result, path, open_tag.line, self.key, "filetree tags share a line with other content", lines[open_tag.line])
            return False
        indent = lines[open_tag.line][: open_tag.start]
        unknown = [p.name for p in open_tag.params if p.name != "label"]
        if unknown:
            self.note(result, path, open_tag.line, self.key, f"unsupported filetree parameters {unknown}", open_tag.raw)
            return False
        inner = [t for t in doc.iter_tags({"filetree/folder", "filetree/file"}) if (open_tag.line, open_tag.start) < (t.line, t.start) < (close_tag.line, close_tag.start)]
        sequence = [open_tag] + inner + [close_tag]
        for prev, nxt in zip(sequence, sequence[1:]):
            if prev.line == nxt.line:
                gap = lines[prev.line][prev.end : nxt.start]
            else:
                gap = lines[prev.line][prev.end :] + "".join(lines[prev.line + 1 : nxt.line]) + lines[nxt.line][: nxt.start]
            if gap.strip():
                self.note(result, path, prev.line, self.key, "content inside filetree that is not a folder/file tag", gap.strip()[:80])
                return False
        rows: list[tuple[str, str, str]] = []
        depth = 0
        counts = {"open": 0, "icon": 0, "tone": 0, "tone_mapped": 0, "link": 0, "comment": 0}
        for tag in inner:
            if tag.closing:
                if tag.name != "filetree/folder" or depth == 0:
                    self.note(result, path, tag.line, self.key, "unbalanced filetree/folder close", tag.raw)
                    return False
                depth -= 1
                continue
            name = (tag.get("name") or "").strip()
            if not name or not tag.is_named():
                self.note(result, path, tag.line, self.key, "filetree node without name=", tag.raw)
                return False
            allowed = {"filetree/folder": {"name", "open", "icon", "color", "comment"}, "filetree/file": {"name", "link", "icon", "color", "comment"}}[tag.name]
            unknown = [p.name for p in tag.params if p.name not in allowed]
            if unknown:
                self.note(result, path, tag.line, self.key, f"unsupported {tag.name} parameters {unknown}", tag.raw)
                return False
            attrs: list[str] = []
            if tag.name == "filetree/folder":
                if not name.endswith("/"):
                    name += "/"
                if (tag.get("open") or "").strip().lower() != "true":
                    attrs.append("open=false")
                    counts["open"] += 1
            icon = (tag.get("icon") or "").strip()
            if icon:
                if not re.fullmatch(r"fa-(solid|regular|brands) fa-[a-z0-9-]+", icon):
                    self.note(result, path, tag.line, self.key, f"icon {icon!r} is not one Font Awesome class pair", tag.raw)
                    return False
                attrs.append(f'icon="{icon}"')
                counts["icon"] += 1
            color = (tag.get("color") or "").strip()
            if color:
                mapped = TONE_MAP.get(color)
                if mapped is None:
                    self.note(result, path, tag.line, self.key, f"unsupported color {color!r}", tag.raw)
                    return False
                attrs.append(f"tone={mapped}")
                counts["tone"] += 1
                if mapped != color:
                    counts["tone_mapped"] += 1
            link = (tag.get("link") or "").strip()
            label = name
            if link:
                label = f"[{name}]({link})"
                counts["link"] += 1
            comment = (tag.get("comment") or "").strip()
            if comment:
                counts["comment"] += 1
                if "{" in comment or "}" in comment:
                    self.note(result, path, tag.line, self.key, "comment contains braces (would parse as fence attributes)", tag.raw)
                    return False
            rows.append((f"{indent}{'  ' * depth}- {label}", comment, "{" + " ".join(attrs) + "}" if attrs else ""))
            if tag.name == "filetree/folder" and not tag.self_closing:
                depth += 1
        if depth != 0:
            self.note(result, path, open_tag.line, self.key, "unbalanced filetree/folder nesting", open_tag.raw)
            return False
        if not rows:
            self.note(result, path, open_tag.line, self.key, "empty filetree", open_tag.raw)
            return False
        label = (open_tag.get("label") or "").strip() if open_tag.has("label") else ""
        if '"' in label:
            self.note(result, path, open_tag.line, self.key, "filetree label contains a double quote", open_tag.raw)
            return False
        opener = f'{indent}```filetree {{title="{label}"}}' if label else f"{indent}```filetree"
        out = [opener] + align_comments(rows) + [f"{indent}```"]
        result.counts["filetree"] += 1
        result.counts["filetree.nodes"] += len(rows)
        if label:
            result.counts["filetree.title"] += 1
        for key, count in counts.items():
            if count:
                result.counts[f"filetree.{key}"] += count
        self.replace_lines(doc, open_tag.line, close_tag.line, out)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(out) - 1)
        return True

    # -- {.filetree} lists ------------------------------------------------------
    def _convert_lists(self, path: str, doc: Document, result: Result) -> bool:
        markers = [i for i, line in enumerate(doc.lines) if i >= doc.front_matter_end and not doc.in_fence[i] and MARKER_RE.match(line)]
        changed = False
        for marker in reversed(markers):
            if self._convert_list(path, doc, result, marker):
                changed = True
        return changed

    def _convert_list(self, path: str, doc: Document, result: Result, marker: int) -> bool:
        lines = doc.lines
        start = marker - 1
        items: list[tuple[str, str]] = []  # (indent, text) bottom-up
        while start >= doc.front_matter_end and lines[start].strip():
            match = LIST_ITEM_RE.match(lines[start])
            if not match:
                if items and lines[start].startswith((" ", "\t")):
                    self.note(result, path, start, self.key, "{.filetree} list item spans several lines", lines[start])
                    return False
                break
            items.append((match.group("indent").replace("\t", "    "), match.group("text")))
            start -= 1
        start += 1
        if not items:
            self.note(result, path, marker, self.key, "{.filetree} marker without a list above it", lines[marker])
            return False
        items.reverse()
        base = len(items[0][0])
        rows: list[tuple[str, str, str]] = []
        stack: list[int] = []
        for line_index, (indent, text) in zip(range(start, marker), items):
            width = len(indent)
            if width < base:
                self.note(result, path, line_index, self.key, "{.filetree} list dedents past its first item", lines[line_index])
                return False
            if not stack or width > stack[-1]:
                stack.append(width)
            else:
                while stack and width < stack[-1]:
                    stack.pop()
                if not stack or width != stack[-1]:
                    self.note(result, path, line_index, self.key, "{.filetree} list dedents to an unknown level", lines[line_index])
                    return False
            depth = len(stack) - 1
            name, comment = text, ""
            if " — " in text:
                name, comment = text.split(" — ", 1)
            elif text.endswith(" —"):
                name = text[:-2]
            name = unwrap(name)
            comment = unwrap(comment)
            link = LINK_RE.match(name)
            if link:
                name = f"[{unwrap(link.group(1))}]({link.group(2)})"
            if not name:
                self.note(result, path, line_index, self.key, "{.filetree} item without a name", lines[line_index])
                return False
            if any(ch in comment for ch in "{}") or any(ch in name for ch in "{}"):
                self.note(result, path, line_index, self.key, "{.filetree} item contains braces (would parse as fence attributes)", lines[line_index])
                return False
            if re.search(r"(\*[^*]+\*|`[^`]+`|_[^_]+_)", name) or re.search(r"(\*[^*]+\*|`[^`]+`|\[[^\]]*\]\()", comment):
                result.counts["filetree.list_inline_markdown"] += 1  # inline Markdown renders literally in the fence
            rows.append((f"{' ' * base}{'  ' * depth}- {name}", comment, ""))
        out = [f"{' ' * base}```filetree"] + align_comments(rows) + [f"{' ' * base}```"]
        result.counts["filetree.list"] += 1
        result.counts["filetree.nodes"] += len(rows)
        self.replace_lines(doc, start, marker, out)
        ensure_blank_around(doc, start, start + len(out) - 1)
        return True
