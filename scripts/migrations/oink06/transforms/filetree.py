"""filetree / filetree/folder / filetree/file -> nested list + {.filetree}.

    {{< filetree label="x" >}}                -   - content/
      {{< filetree/folder name="content" >}}        - _index.md — Site landing
        {{< filetree/file name="_index.md" comment="Site landing" >}}
      {{< /filetree/folder >}}                    {.filetree}
    {{< /filetree >}}

``open`` / ``icon`` / ``color`` / ``label`` are dropped (counted); ``link``
becomes a Markdown link; ``comment`` follows an em dash.
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, ensure_blank_around
from ..scanner import Document, Tag

NAME_ESCAPE_RE = re.compile(r"([*`\[\]<])")


def escape_name(name: str) -> str:
    return NAME_ESCAPE_RE.sub(r"\\\1", name)


class FileTreeTransformation(Transformation):
    key = "filetree"
    description = "filetree shortcode family -> nested list {.filetree}"
    residual_patterns = (r"\{\{[<%]\s*/?filetree\b",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        opens = [tag for tag in doc.iter_tags({"filetree"}) if not tag.closing]
        if not opens:
            return
        changed = False
        for open_tag in reversed(opens):
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed filetree", open_tag.raw)
                continue
            if self._convert(path, doc, result, open_tag, close_tag):
                changed = True
        if changed:
            result.text = doc.render()

    def _convert(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> bool:
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
        # only whitespace may separate consecutive tags (tags may share a line)
        sequence = [open_tag] + inner + [close_tag]
        for prev, nxt in zip(sequence, sequence[1:]):
            if prev.line == nxt.line:
                gap = lines[prev.line][prev.end : nxt.start]
            else:
                gap = lines[prev.line][prev.end :] + "".join(lines[prev.line + 1 : nxt.line]) + lines[nxt.line][: nxt.start]
            if gap.strip():
                self.note(result, path, prev.line, self.key, "content inside filetree that is not a folder/file tag", gap.strip()[:80])
                return False
        out: list[str] = []
        depth = 0
        dropped = {"open": 0, "icon": 0, "color": 0}
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
            for key in dropped:
                if tag.has(key):
                    dropped[key] += 1
            label = escape_name(name)
            if tag.name == "filetree/folder":
                if not label.endswith("/"):
                    label += "/"
            link = (tag.get("link") or "").strip()
            if link:
                label = f"[{label}]({link})"
            comment = (tag.get("comment") or "").strip()
            entry = f"{indent}{'  ' * depth}- {label}"
            if comment:
                entry += f" — {comment}"
            out.append(entry)
            if tag.name == "filetree/folder" and not tag.self_closing:
                depth += 1
        if depth != 0:
            self.note(result, path, open_tag.line, self.key, "unbalanced filetree/folder nesting", open_tag.raw)
            return False
        if not out:
            self.note(result, path, open_tag.line, self.key, "empty filetree", open_tag.raw)
            return False
        out.append(indent + "{.filetree}")
        if open_tag.has("label"):
            result.counts["filetree.label_dropped"] += 1
        for key, count in dropped.items():
            if count:
                result.counts[f"filetree.{key}_dropped"] += count
        result.counts["filetree"] += 1
        result.counts["filetree.nodes"] += len(out) - 1
        self.replace_lines(doc, open_tag.line, close_tag.line, out)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(out) - 1)
        return True
