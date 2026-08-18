"""Transformation base types shared by every migration module."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re

from .scanner import Document, Tag


@dataclass
class Finding:
    """One thing a transformation refused to rewrite (or wants a human to see)."""

    path: str
    line: int  # 1-based
    kind: str  # transformation key
    reason: str
    source: str = ""


@dataclass
class Result:
    text: str
    counts: Counter = field(default_factory=Counter)  # e.g. {"alert": 3, "alert.title": 1}
    findings: list[Finding] = field(default_factory=list)
    changed: bool = False


class Transformation:
    """Rewrite one family of legacy forms in one file.

    ``run`` returns a Result; ``find`` (used by ``report``) is ``run`` without
    the rewrite, i.e. counts + findings only. Subclasses implement ``_apply``.
    """

    key = "base"
    description = ""
    residual_patterns: tuple[str, ...] = ()  # regexes marking leftovers for `check`

    def run(self, path: str, text: str) -> Result:
        result = Result(text=text)
        for _ in range(64):  # innermost-first families iterate until stable
            before = result.text
            result.findings = []  # only the final (stable) pass keeps line-accurate findings
            doc = Document.parse(result.text)
            self._apply(path, doc, result)
            if result.text == before:
                break
        result.changed = result.text != text
        return result

    def find(self, path: str, text: str) -> Result:
        result = self.run(path, text)
        return Result(text=text, counts=result.counts, findings=result.findings, changed=False)

    # subclasses override
    def _apply(self, path: str, doc: Document, result: Result) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    # helpers -----------------------------------------------------------------
    @staticmethod
    def note(result: Result, path: str, line: int, kind: str, reason: str, source: str = "") -> None:
        finding = Finding(path, line + 1, kind, reason, source[:200])
        for existing in result.findings:
            if (existing.path, existing.line, existing.kind, existing.reason) == (finding.path, finding.line, finding.kind, finding.reason):
                return
        result.findings.append(finding)

    @staticmethod
    def replace_lines(doc: Document, start: int, end: int, new_lines: list[str]) -> None:
        """Replace lines[start:end+1] with new_lines (in place on doc.lines)."""

        doc.lines[start : end + 1] = new_lines
        doc.rescan()


def slugify(value: str) -> str:
    """Slug for tab values / groups: ``^[a-z0-9][a-z0-9_-]*$`` or empty."""

    slug = value.strip().lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9_-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", slug or ""):
        return ""
    return slug


def quote_attr_value(value: str) -> str:
    """Goldmark/Hugo fence attribute value: bare booleans and integers, quoted otherwise."""

    if value in ("true", "false") or re.fullmatch(r"-?[0-9]+", value):
        return value
    return '"' + value.replace('"', "'") + '"'


def dedent_lines(lines: list[str], indent: str) -> list[str]:
    """Strip ``indent`` from lines that carry it; leave less-indented lines alone."""

    result = []
    for line in lines:
        if indent and line.startswith(indent):
            result.append(line[len(indent) :])
        elif indent and line.strip() and len(line) - len(line.lstrip(" \t")) < len(indent):
            result.append(line.lstrip(" \t"))
        else:
            result.append(line)
    return result


QUOTE_PREFIX_RE = re.compile(r"^(?:[ \t]*>)*[ \t]*")


def strip_prefix(line: str, prefix: str) -> str:
    """Remove ``prefix`` (indentation and/or ``>`` markers) from ``line``.

    Exact prefix first; otherwise the same number of ``>`` markers (blank
    quote lines are written ``>`` without the trailing space); otherwise the
    leading whitespace only.
    """

    if not prefix:
        return line
    if line.startswith(prefix):
        return line[len(prefix) :]
    quotes = prefix.count(">")
    if quotes:
        match = re.match(r"^(?:[ \t]*>){%d}[ \t]?" % quotes, line)
        if match:
            return line[match.end() :]
        return line.lstrip(" \t")
    if line.strip() and len(line) - len(line.lstrip(" \t")) < len(prefix):
        return line.lstrip(" \t")
    return line


def reindent_lines(lines: list[str], indent: str) -> list[str]:
    return [(indent + line) if line.strip() else "" for line in lines]


def strip_blank_edges(lines: list[str]) -> list[str]:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def ensure_blank_around(doc: Document, start: int, end: int) -> tuple[int, int]:
    """Guarantee blank separation before/after the block lines[start:end+1].

    Adds a blank line after when the next line would otherwise be swallowed as
    lazy continuation / adjacent block, and before when the previous line is a
    paragraph at the same or deeper indentation. Returns the (start, end)
    indices after insertion.
    """

    from .scanner import is_block_start

    lines = doc.lines
    quote_block = lines[start].lstrip().startswith(">") if start < len(lines) else False
    if end + 1 < len(lines) and lines[end + 1].strip():
        nxt = lines[end + 1].lstrip()
        if not is_block_start(lines[end + 1]) or (quote_block and nxt.startswith(">")):
            lines.insert(end + 1, "")
    if start > 0 and lines[start - 1].strip():
        prev = lines[start - 1]
        prev_indent = len(prev) - len(prev.lstrip(" \t"))
        cur_indent = len(lines[start]) - len(lines[start].lstrip(" \t"))
        merges = quote_block and prev.lstrip().startswith(">")
        if (prev_indent >= cur_indent and not is_block_start(prev)) or merges:
            lines.insert(start, "")
            start += 1
            end += 1
    doc.rescan()
    return start, end
