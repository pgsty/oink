"""badge: drop the pure-presentation outline= parameter."""

from __future__ import annotations

from ..base import Result, Transformation
from ..scanner import Document, render_tag


class BadgeTransformation(Transformation):
    key = "badge"
    description = "badge outline= dropped"
    residual_patterns = (r"\{\{[<%]\s*badge\b[^>%]*\boutline\s*=",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        tags = [tag for tag in doc.iter_tags({"badge"}) if not tag.closing and tag.has("outline")]
        if not tags:
            return
        for tag in reversed(tags):
            params = [(p.name, p.value) for p in tag.params if p.name != "outline"]
            if any(name is None for name, _ in params):
                self.note(result, path, tag.line, self.key, "badge with positional parameters", tag.raw)
                continue
            new = render_tag(tag.delim, "badge", params, self_closing=tag.self_closing)
            line = doc.lines[tag.line]
            doc.lines[tag.line] = line[: tag.start] + new + line[tag.end :]
            result.counts["badge.outline_dropped"] += 1
        doc.rescan()
        result.text = doc.render()
