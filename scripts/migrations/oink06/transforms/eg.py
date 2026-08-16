"""example leaf + following fence -> {{< eg >}} wrapper; book-figures kind= -> book-*.

    {{< example num="4-1" id="x" caption="…" />}}     {{< eg num="4-1" id="x" caption="…" >}}
                                                 ->   ```sql
    ```sql                                            SELECT 1;
    SELECT 1;                                         ```
    ```                                               {{< /eg >}}
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, ensure_blank_around
from ..scanner import FENCE_OPEN_RE, Document, Tag, render_tag

KIND_TO_NAME = {"fig": "book-figures", "tbl": "book-tables", "eq": "book-equations", "eg": "book-examples", "example": "book-examples"}


class ExampleTransformation(Transformation):
    key = "eg"
    description = "example leaf + fence -> {{< eg >}} wrapper; book-figures kind= -> book-tables/equations"
    residual_patterns = (
        r"\{\{[<%]\s*example\b",
        r"\{\{[<%]\s*book-figures\b[^>%]*\bkind\s*=",
    )

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        changed = False
        # book-figures kind= ------------------------------------------------
        for tag in reversed([t for t in doc.iter_tags({"book-figures"}) if not t.closing and t.has("kind")]):
            kind = (tag.get("kind") or "").strip()
            name = KIND_TO_NAME.get(kind)
            if name is None:
                self.note(result, path, tag.line, self.key, f"book-figures kind={kind!r} unknown", tag.raw)
                continue
            others = [(p.name, p.value) for p in tag.params if p.name != "kind"]
            new = render_tag("<", name, others)
            line = doc.lines[tag.line]
            doc.lines[tag.line] = line[: tag.start] + new + line[tag.end :]
            result.counts[f"book-figures.kind.{kind}"] += 1
            changed = True
        if changed:
            doc.rescan()
        # example leaf --------------------------------------------------------
        examples = [t for t in doc.iter_tags({"example"}) if not t.closing]
        for tag in reversed(examples):
            if self._convert_example(path, doc, result, tag):
                changed = True
        if changed:
            result.text = doc.render()

    def _convert_example(self, path: str, doc: Document, result: Result, tag: Tag) -> bool:
        lines = doc.lines
        if not doc.tag_alone(tag):
            self.note(result, path, tag.line, self.key, "example tag shares a line with other content", lines[tag.line])
            return False
        if not tag.self_closing:
            close = doc.find_close(tag)
            if close is not None:
                self.note(result, path, tag.line, self.key, "paired example with inner content — rewrite by hand as {{< eg >}}", tag.raw)
                return False
        num = (tag.get("num") or tag.get("number") or "").strip()
        caption = (tag.get("caption") or tag.get("title") or "").strip()
        if not num:
            self.note(result, path, tag.line, self.key, "example without num (unnumbered caption) — no eg form", tag.raw)
            return False
        if not caption:
            self.note(result, path, tag.line, self.key, "example without caption (eg requires caption)", tag.raw)
            return False
        unknown = [p.name for p in tag.params if p.name not in {"num", "number", "id", "caption", "title", "class"}]
        if unknown or tag.positional():
            self.note(result, path, tag.line, self.key, f"unsupported example parameters {unknown or tag.positional()}", tag.raw)
            return False
        indent = lines[tag.line][: tag.start]
        # the next non-blank line must open a fence at the same indentation
        nxt = tag.line + 1
        while nxt < len(lines) and not lines[nxt].strip():
            nxt += 1
        if nxt >= len(lines):
            self.note(result, path, tag.line, self.key, "example not followed by a fence", tag.raw)
            return False
        fence = doc.fence_at(nxt)
        head = FENCE_OPEN_RE.match(lines[nxt])
        if fence is None or fence.start != nxt or head is None or head.group("indent") != indent:
            self.note(result, path, tag.line, self.key, "example not followed by a fence at the same indentation", lines[nxt][:80])
            return False
        params = [("num", num)]
        if tag.has("id"):
            params.append(("id", (tag.get("id") or "").strip()))
        params.append(("caption", caption))
        if tag.has("class"):
            params.append(("class", (tag.get("class") or "").strip()))
        out = [indent + render_tag("<", "eg", params)]
        out.extend(lines[nxt : fence.end + 1])
        out.append(indent + "{{< /eg >}}")
        result.counts["example"] += 1
        self.replace_lines(doc, tag.line, fence.end, out)
        ensure_blank_around(doc, tag.line, tag.line + len(out) - 1)
        return True
