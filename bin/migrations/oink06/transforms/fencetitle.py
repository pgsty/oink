"""Fence info string attribute filename="x" -> title="x" (`.full-width` etc. untouched)."""

from __future__ import annotations

import re

from ..base import Result, Transformation
from ..scanner import FENCE_OPEN_RE, Document

FILENAME_RE = re.compile(r"(?<![A-Za-z0-9_-])filename\s*=")
TITLE_RE = re.compile(r"(?<![A-Za-z0-9_-])title\s*=")


class FenceTitleTransformation(Transformation):
    key = "fencetitle"
    description = "fence attribute filename= -> title="
    residual_patterns = ()

    def residual_findings(self, doc: Document):
        for fence in doc.fences:
            if FILENAME_RE.search(fence.info):
                yield fence.start, "fence attribute filename= (use title=)", doc.lines[fence.start]

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        changed = False
        for fence in doc.fences:
            info = fence.info
            if not FILENAME_RE.search(info) or "{" not in info:
                continue
            if TITLE_RE.search(info):
                self.note(result, path, fence.start, self.key, "fence has both filename= and title=", doc.lines[fence.start])
                continue
            line = doc.lines[fence.start]
            match = FENCE_OPEN_RE.match(line)
            new_info = FILENAME_RE.sub("title=", match.group("info"), count=1)
            doc.lines[fence.start] = match.group("indent") + match.group("fence") + new_info
            result.counts["fencetitle"] += 1
            changed = True
        if changed:
            doc.rescan()
            result.text = doc.render()
