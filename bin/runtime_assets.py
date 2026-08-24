"""Read stable first-party runtime chunks referenced by rendered HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit


SCRIPT_TAG = re.compile(
    r'<script\b[^>]*\bsrc="(?P<src>[^"]*?/js/chunks/'
    r'(?P<name>[a-z0-9-]+?)(?:\.min\.[0-9a-f]{64})?\.js(?:\?[^"#]*)?)"[^>]*>',
    re.I,
)


@dataclass(frozen=True)
class RuntimeChunk:
    name: str
    src: str
    tag: str
    start: int
    path: Path


def _published_path(public: Path, src: str) -> Path:
    """Resolve root and subpath deployments without assuming their prefix."""
    relative = unescape(urlsplit(src).path).lstrip("/")
    parts = Path(relative).parts
    for start in range(0, max(0, len(parts) - 1)):
        if parts[start : start + 2] == ("js", "chunks"):
            return public.joinpath(*parts[start:])
    return public / relative


def referenced_chunks(public: Path, source: str) -> list[RuntimeChunk]:
    return [
        RuntimeChunk(
            name=match.group("name"),
            src=match.group("src"),
            tag=match.group(0),
            start=match.start(),
            path=_published_path(public, match.group("src")),
        )
        for match in SCRIPT_TAG.finditer(source)
    ]


def chunk(public: Path, source: str, name: str) -> RuntimeChunk | None:
    return next((item for item in referenced_chunks(public, source) if item.name == name), None)


def combined_source(public: Path, source: str) -> str:
    return "\n".join(
        item.path.read_text(encoding="utf-8")
        for item in referenced_chunks(public, source)
        if item.path.is_file()
    )
