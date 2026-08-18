"""readfile -> include (named parameters only, strict booleans)."""

from __future__ import annotations

from ..base import Result, Transformation
from ..scanner import Document, render_tag


class IncludeTransformation(Transformation):
    key = "include"
    description = "readfile -> include (named file=, code=true, lang=)"
    residual_patterns = (r"\{\{[<%]\s*readfile\b",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        tags = [tag for tag in doc.iter_tags({"readfile"}) if not tag.closing]
        if not tags:
            return
        changed = False
        for tag in reversed(tags):
            if tag.is_named():
                unknown = [p.name for p in tag.params if p.name not in {"file", "code", "lang", "draft"}]
                if unknown:
                    self.note(result, path, tag.line, self.key, f"unsupported readfile parameters {unknown}", tag.raw)
                    continue
                file = (tag.get("file") or "").strip()
                if not file:
                    self.note(result, path, tag.line, self.key, "readfile without file=", tag.raw)
                    continue
                params = [("file", file)]
                code = (tag.get("code") or "").strip().lower()
                if code == "true":
                    params.append(("code", "true"))
                elif code and code != "false":
                    self.note(result, path, tag.line, self.key, f"readfile code={code!r} is not boolean", tag.raw)
                    continue
                if tag.has("lang"):
                    params.append(("lang", (tag.get("lang") or "").strip()))
                if tag.has("draft"):
                    result.counts["include.draft_dropped"] += 1
            else:
                positional = tag.positional()
                if len(positional) != 1:
                    self.note(result, path, tag.line, self.key, "positional readfile needs exactly one path", tag.raw)
                    continue
                params = [("file", positional[0])]
            new = render_tag("<", "include", params)
            line = doc.lines[tag.line]
            doc.lines[tag.line] = line[: tag.start] + new + line[tag.end :]
            result.counts["readfile"] += 1
            changed = True
        if changed:
            doc.rescan()
            result.text = doc.render()
