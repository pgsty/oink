"""gallery / gallery/image -> image list + {.gallery}."""

from __future__ import annotations

from ..base import Result, Transformation, ensure_blank_around
from ..scanner import Document, Tag


class GalleryTransformation(Transformation):
    key = "gallery"
    description = "gallery shortcode family -> image list {.gallery}"
    residual_patterns = (r"\{\{[<%]\s*/?gallery\b",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        opens = [tag for tag in doc.iter_tags({"gallery"}) if not tag.closing]
        if not opens:
            return
        changed = False
        for open_tag in reversed(opens):
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed gallery", open_tag.raw)
                continue
            if self._convert(path, doc, result, open_tag, close_tag):
                changed = True
        if changed:
            result.text = doc.render()

    def _convert(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> bool:
        lines = doc.lines
        if not doc.tag_alone(open_tag) or not doc.tag_alone(close_tag):
            self.note(result, path, open_tag.line, self.key, "gallery tags share a line with other content", lines[open_tag.line])
            return False
        unknown = [p.name for p in open_tag.params if p.name not in {"columns", "label"}]
        if unknown:
            self.note(result, path, open_tag.line, self.key, f"unsupported gallery parameters {unknown}", open_tag.raw)
            return False
        indent = lines[open_tag.line][: open_tag.start]
        images = [t for t in doc.iter_tags({"gallery/image"}) if (open_tag.line, open_tag.start) < (t.line, t.start) < (close_tag.line, close_tag.start)]
        image_lines = {t.line for t in images}
        for line in range(open_tag.line + 1, close_tag.line):
            if lines[line].strip() and line not in image_lines:
                self.note(result, path, line, self.key, "content inside gallery that is not gallery/image", lines[line])
                return False
        out = []
        for tag in images:
            if not doc.tag_alone(tag):
                self.note(result, path, tag.line, self.key, "gallery/image shares a line with other content", lines[tag.line])
                return False
            src = (tag.get("src") or "").strip()
            alt = (tag.get("alt") or "").strip()
            caption = (tag.get("caption") or "").strip()
            unknown = [p.name for p in tag.params if p.name not in {"src", "alt", "caption"}]
            if unknown or not src:
                self.note(result, path, tag.line, self.key, f"unsupported gallery/image parameters {unknown or 'missing src'}", tag.raw)
                return False
            if not alt:
                self.note(result, path, tag.line, self.key, "gallery/image without alt (alt is required by {.gallery})", tag.raw)
                return False
            entry = f"{indent}- ![{alt}]({src})"
            if caption:
                entry += f" — {caption}"
            out.append(entry)
        if not out:
            self.note(result, path, open_tag.line, self.key, "gallery without images", open_tag.raw)
            return False
        out.append(indent + "{.gallery}")
        for key in ("columns", "label"):
            if open_tag.has(key):
                result.counts[f"gallery.{key}_dropped"] += 1
        result.counts["gallery"] += 1
        result.counts["gallery.images"] += len(out) - 1
        self.replace_lines(doc, open_tag.line, close_tag.line, out)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(out) - 1)
        return True
