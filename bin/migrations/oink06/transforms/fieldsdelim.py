"""fields / field written with the withdrawn % delimiter -> {{< >}} (count only in practice)."""

from __future__ import annotations

from ..base import Result, Transformation
from ..scanner import Document, render_tag


class FieldsDelimTransformation(Transformation):
    key = "fieldsdelim"
    description = "{{% fields %}} / {{% field %}} -> {{< fields >}} / {{< field >}}"
    residual_patterns = (r"\{\{%\s*/?fields?\b",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        tags = [tag for tag in doc.iter_tags({"fields", "field"}) if tag.delim == "%"]
        if not tags:
            return
        for tag in reversed(tags):
            params = [(p.name, p.value) for p in tag.params]
            if any(name is None for name, _ in params):
                self.note(result, path, tag.line, self.key, f"positional {tag.name} parameters", tag.raw)
                continue
            new = render_tag("<", tag.name, params, closing=tag.closing, self_closing=tag.self_closing)
            line = doc.lines[tag.line]
            doc.lines[tag.line] = line[: tag.start] + new + line[tag.end :]
            result.counts[f"fieldsdelim.{tag.name}"] += 1
        doc.rescan()
        result.text = doc.render()
