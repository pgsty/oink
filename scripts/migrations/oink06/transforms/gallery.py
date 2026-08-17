"""gallery shortcodes and the interim ``{.gallery}`` list -> ```gallery fence.

    {{< gallery >}}                                 ```gallery
      {{< gallery/image src="a.png" alt="A"         ![A](a.png) # Overview
                        caption="Overview" />}}     ![B](b.png)
      {{< gallery/image src="b.png" alt="B" />}}    ```
    {{< /gallery >}}

    - ![A](a.png) — Overview                        ```gallery
    - ![B](b.png)                                   ![A](a.png) # Overview
    {.gallery}                                      ![B](b.png)
                                                    ```

The em-dash separator of the list form becomes the fence's `#` description
marker. A description that already contains a hash is escaped as `\\#`, because
in the fence an unescaped hash starts the description.
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, ensure_blank_around
from ..scanner import Document, Tag


MARKER_RE = re.compile(r"^[ \t]*\{\.gallery\}[ \t]*$")
LIST_ITEM_RE = re.compile(r"^(?P<indent>[ \t]*)[-*+][ \t]+(?P<text>\S.*)$")
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\)(?P<rest>.*)$")


def describe(text: str) -> str:
    """Turn trailing list-item text into a fence description."""

    text = text.strip()
    if text.startswith("—"):
        text = text[1:].strip()
    elif text.startswith("-"):
        text = text[1:].strip()
    return text.replace("#", "\\#")


class GalleryTransformation(Transformation):
    key = "gallery"
    description = "gallery shortcode family and {.gallery} lists -> ```gallery fence"
    residual_patterns = (r"\{\{[<%]\s*/?gallery\b", r"^[ \t]*\{\.gallery\}[ \t]*$")

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        changed = False
        opens = [tag for tag in doc.iter_tags({"gallery"}) if not tag.closing]
        for open_tag in reversed(opens):
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed gallery", open_tag.raw)
                continue
            if self._convert(path, doc, result, open_tag, close_tag):
                changed = True
        if self._convert_lists(path, doc, result):
            changed = True
        if changed:
            result.text = doc.render()

    # --- shortcode form ---------------------------------------------------
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
        rows = []
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
                self.note(result, path, tag.line, self.key, "gallery/image without alt (the gallery fence requires alt)", tag.raw)
                return False
            if "{" in src or "}" in src or "{" in alt or "}" in alt:
                self.note(result, path, tag.line, self.key, "gallery/image contains braces (would parse as fence attributes)", tag.raw)
                return False
            entry = f"{indent}![{alt}]({src})"
            if caption:
                entry += f" # {describe(caption)}"
            rows.append(entry)
        if not rows:
            self.note(result, path, open_tag.line, self.key, "gallery without images", open_tag.raw)
            return False
        out = [f"{indent}```gallery"] + rows + [f"{indent}```"]
        for key in ("columns", "label"):
            if open_tag.has(key):
                result.counts[f"gallery.{key}_dropped"] += 1
        result.counts["gallery"] += 1
        result.counts["gallery.images"] += len(rows)
        self.replace_lines(doc, open_tag.line, close_tag.line, out)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(out) - 1)
        return True

    # --- interim {.gallery} list form -------------------------------------
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
                    self.note(result, path, start, self.key, "{.gallery} list item spans several lines", lines[start])
                    return False
                break
            items.append((match.group("indent").replace("\t", "    "), match.group("text")))
            start -= 1
        start += 1
        if not items:
            self.note(result, path, marker, self.key, "{.gallery} marker without a list above it", lines[marker])
            return False
        items.reverse()
        indent = items[0][0]
        rows = []
        for line_index, (_, text) in zip(range(start, marker), items):
            image = IMAGE_RE.match(text.strip())
            if not image:
                self.note(result, path, line_index, self.key, "{.gallery} item is not a Markdown image", lines[line_index])
                return False
            alt = image.group("alt").strip()
            src = image.group("src")
            if not alt:
                self.note(result, path, line_index, self.key, "{.gallery} item without alt (the gallery fence requires alt)", lines[line_index])
                return False
            if any(ch in src or ch in alt for ch in "{}"):
                self.note(result, path, line_index, self.key, "{.gallery} item contains braces (would parse as fence attributes)", lines[line_index])
                return False
            entry = f"{indent}![{alt}]({src})"
            description = describe(image.group("rest"))
            if "{" in description or "}" in description:
                self.note(result, path, line_index, self.key, "{.gallery} description contains braces (would parse as fence attributes)", lines[line_index])
                return False
            if description:
                entry += f" # {description}"
            rows.append(entry)
        out = [f"{indent}```gallery"] + rows + [f"{indent}```"]
        result.counts["gallery.list"] += 1
        result.counts["gallery.images"] += len(rows)
        self.replace_lines(doc, start, marker, out)
        ensure_blank_around(doc, start, start + len(out) - 1)
        return True
