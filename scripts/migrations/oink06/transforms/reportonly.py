"""Count-only inventory of legacy forms that need a human decision."""

from __future__ import annotations

from ..base import Result, Transformation
from ..scanner import Document

NAMES = {
    "iframe": "iframe shortcode (0.5 removal): use raw <iframe>",
    "conditional-text": "conditional-text shortcode (0.5 removal)",
    "blocks/cover": "Docsy landing block (0.5 removal): layout: landing",
    "blocks/feature": "Docsy landing block (0.5 removal): layout: landing",
    "blocks/lead": "Docsy landing block (0.5 removal): layout: landing",
    "blocks/link-down": "Docsy landing block (0.5 removal): layout: landing",
    "blocks/section": "Docsy landing block (0.5 removal): layout: landing",
    "td/site-build-info/netlify": "netlify shortcode (0.5 removal)",
    "netlify": "netlify shortcode (0.5 removal)",
}


class ReportOnlyTransformation(Transformation):
    key = "reportonly"
    description = "count-only: iframe, conditional-text, blocks/*, netlify, kind-less xref"
    residual_patterns = ()

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        for tag in doc.iter_tags(set(NAMES) | {"xref"}):
            if tag.closing:
                continue
            if tag.name == "xref":
                if not any(tag.has(kind) for kind in ("fig", "tbl", "eq", "eg")):
                    result.counts["xref.kindless"] += 1
                else:
                    result.counts["xref.kind"] += 1
                continue
            result.counts[f"reportonly.{tag.name}"] += 1
            self.note(result, path, tag.line, self.key, NAMES[tag.name], tag.raw)
