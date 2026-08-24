#!/usr/bin/env python3
"""Package an opt-in OINK BookManifest and whole-Book Print HTML as EPUB 3.

Requires Pandoc 3.x: chapter splitting relies on `--split-level` and on
pandoc's `ch%03d.xhtml` chunk naming (CI pins 3.10; pandoc 2.x fails
cleanly on the unknown flag, and a naming change is caught by
`check-book-epub.py`'s chapter and fragment gates, never silently).
"""

from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import NoReturn
from urllib.parse import unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSS = ROOT / "assets/css/book-epub.css"
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
SKIP_TAGS = {
    "button", "dialog", "embed", "iframe", "noscript", "object", "script",
    "style", "template",
}
SKIP_CLASSES = {"d-print-none", "td-book-print-cover", "td-book-print-toc", "td-book-toc"}
REMOTE_MEDIA_TAGS = {"audio", "img", "source", "track", "video"}
MAIN_RE = re.compile(
    r"<main\b[^>]*\bid=(?:\"td-main-content\"|'td-main-content'|td-main-content)(?=[\s>])"
    r"[^>]*>(?P<body>.*)</main>",
    re.I | re.S,
)


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def normalized_route(value: str) -> str:
    path = unquote(urlsplit(value).path or "/")
    if not path.startswith("/"):
        path = "/" + path
    path = posixpath.normpath(path)
    return "/" if path == "/" else path.rstrip("/")


def public_file(public: Path, url: str, base_path: str = "") -> Path:
    path = unquote(urlsplit(url).path)
    if base_path and (path == base_path or path.startswith(base_path + "/")):
        path = path[len(base_path) :]
    candidate = (public / path.lstrip("/")).resolve()
    try:
        candidate.relative_to(public.resolve())
    except ValueError:
        fail(f"resource escapes public directory: {url}")
    return candidate


def print_file(public: Path, url: str, base_path: str) -> Path:
    candidate = public_file(public, url, base_path)
    if urlsplit(url).path.endswith("/"):
        candidate /= "index.html"
    if not candidate.is_file():
        fail(f"whole-Book Print output is missing: {candidate}")
    return candidate


class BookHTML(HTMLParser):
    """Keep the semantic Print document while rewriting publication URLs."""

    def __init__(
        self,
        *,
        public: Path,
        base_url: str,
        pages: list[dict],
        anchor_owners: dict[str, str],
        allow_remote_resources: bool,
    ) -> None:
        super().__init__(convert_charrefs=False)
        self.public = public.resolve()
        self.base_url = base_url
        self.base_path = urlsplit(base_url).path.rstrip("/")
        self.allow_remote_resources = allow_remote_resources
        self.anchor_owners = anchor_owners
        self.output: list[str] = []
        self.skip_depth = 0
        self.section_pages: list[str | None] = []
        self.section_emitted: list[bool] = []
        self.current_page: str | None = None
        self.pending_page_id: str | None = None
        self.by_path = {str(page["path"]): page for page in pages}
        self.chunk_by_path = {
            str(page["path"]): f"ch{index:03}.xhtml"
            for index, page in enumerate(pages, start=1)
        }
        self.by_route = {
            normalized_route(str(page["html"])): page
            for page in pages
            if page.get("html")
        }

    def _page_route(self) -> str:
        if self.current_page and self.current_page in self.by_path:
            return urlsplit(str(self.by_path[self.current_page].get("html") or "/")).path or "/"
        return "/"

    def _absolute(self, value: str) -> str:
        page_url = urljoin(self.base_url, self._page_route())
        return urljoin(page_url, value)

    def _chunk(self, page_path: str, source: str) -> str:
        chunk = self.chunk_by_path.get(page_path)
        if chunk is None:
            fail(f"{source} belongs to Book page absent from BookManifest: {page_path}")
        return chunk

    def _link(self, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme:
            if parsed.scheme not in {"http", "https", "mailto", "tel"}:
                fail(f"unsupported publication link scheme: {value}")
            return value
        if parsed.netloc:
            fail(f"protocol-relative publication link is not allowed: {value}")
        if value.startswith("#"):
            fragment = unquote(value[1:])
            owner = self.anchor_owners.get(fragment)
            if owner and owner != self.current_page:
                return f"{self._chunk(owner, f'fragment #{fragment}')}#{fragment}"
            return "#" + fragment
        absolute = self._absolute(value)
        route = normalized_route(absolute)
        target = self.by_route.get(route)
        if target is None:
            return absolute
        fragment = unquote(parsed.fragment)
        if not fragment:
            fragment = str(target["aggregateId"])
        if fragment in set(target.get("headings", [])):
            fragment = f"{target['aggregateId']}--{fragment}"
        target_path = str(target["path"])
        if target_path != self.current_page:
            return f"{self._chunk(target_path, f'link {value!r}')}#{fragment}"
        return "#" + fragment

    def _resource(self, value: str, tag: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme == "data":
            return value
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            fail(f"unsupported publication resource scheme: {value}")
        if parsed.scheme or parsed.netloc:
            if self.allow_remote_resources and tag in REMOTE_MEDIA_TAGS:
                return value
            if tag not in REMOTE_MEDIA_TAGS:
                fail(f"remote active publication resource is not allowed: <{tag}> {value}")
            fail(f"remote publication resource is not allowed: {value}")
        resource_url = value if parsed.path.startswith("/") else self._absolute(value)
        candidate = public_file(self.public, resource_url, self.base_path)
        if not candidate.is_file():
            fail(f"local publication resource is missing: {value} -> {candidate}")
        return candidate.relative_to(self.public).as_posix()

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> tuple[dict[str, str | None], set[str]]:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        return values, classes

    def _start(self, tag: str, attrs: list[tuple[str, str | None]], *, closed: bool) -> None:
        tag = tag.lower()
        values, classes = self._attrs(attrs)
        if self.skip_depth:
            if not closed and tag not in VOID_TAGS:
                self.skip_depth += 1
            return
        if tag in SKIP_TAGS or classes & SKIP_CLASSES or (
            "katex-html" in classes and values.get("aria-hidden") == "true"
        ):
            if not closed and tag not in VOID_TAGS:
                self.skip_depth = 1
            return
        if tag == "section":
            self.section_pages.append(self.current_page)
            page_path = values.get("data-td-book-page")
            self.current_page = page_path or self.current_page
            if page_path:
                self.pending_page_id = values.get("id")
                self.section_emitted.append(False)
                return
            self.section_emitted.append(True)
        if tag == "h1" and self.pending_page_id and "id" not in values:
            attrs = [("id", self.pending_page_id), *attrs]
            self.pending_page_id = None

        rendered: list[tuple[str, str | None]] = []
        for name, value in attrs:
            if name == "href" and value is not None:
                value = self._link(value)
            elif name in {"src", "poster"} and value is not None:
                value = self._resource(value, tag)
            elif name == "srcset":
                # The ordinary src is sufficient for EPUB and avoids asking a
                # reading system to interpret responsive web candidates.
                continue
            elif name in {"loading", "decoding"}:
                continue
            rendered.append((name, value))
        attributes = "".join(
            f" {name}" if value is None else f' {name}="{escape(value, quote=True)}"'
            for name, value in rendered
        )
        suffix = " /" if closed and tag not in VOID_TAGS else ""
        self.output.append(f"<{tag}{attributes}{suffix}>")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, closed=tag.lower() in VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, closed=True)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if tag == "section" and self.section_pages:
            emitted = self.section_emitted.pop()
            self.current_page = self.section_pages.pop()
            if not emitted:
                self.pending_page_id = None
                return
        self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.output.append(data)

    def handle_entityref(self, name: str) -> None:
        if not self.skip_depth:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.skip_depth:
            self.output.append(f"&#{name};")

    def html(self) -> str:
        return "".join(self.output)


def load_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read BookManifest {path}: {error}")
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        fail("BookManifest schemaVersion must be 1")
    pages = value.get("pages")
    if not isinstance(pages, list) or not pages:
        fail("BookManifest pages must be a non-empty list")
    for page in pages:
        if not isinstance(page, dict) or not all(page.get(key) for key in ("path", "aggregateId")):
            fail(f"BookManifest contains an invalid page: {page!r}")
    book = value.get("book")
    if not isinstance(book, dict) or not book.get("print"):
        fail("BookManifest book.print is required")
    base_url = value.get("baseURL")
    if not isinstance(base_url, str) or urlsplit(base_url).scheme not in {"http", "https"}:
        fail("BookManifest baseURL must be an absolute HTTP(S) URL")
    return value


class AnchorCollector(HTMLParser):
    """Map every aggregate Print identifier to its owning Book page."""

    def __init__(self) -> None:
        super().__init__()
        self.current_page: str | None = None
        self.section_pages: list[str | None] = []
        self.owners: dict[str, str] = {}
        self.duplicates: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "section":
            self.section_pages.append(self.current_page)
            self.current_page = values.get("data-td-book-page") or self.current_page
        identifier = values.get("id")
        if identifier and self.current_page:
            prior = self.owners.get(identifier)
            if prior and prior != self.current_page:
                self.duplicates.add(identifier)
            else:
                self.owners[identifier] = self.current_page

    def handle_endtag(self, tag: str) -> None:
        if tag == "section" and self.section_pages:
            self.current_page = self.section_pages.pop()


def transformed_html(public: Path, manifest: dict, allow_remote_resources: bool) -> str:
    base_url = str(manifest["baseURL"])
    source_path = print_file(public, str(manifest["book"]["print"]), urlsplit(base_url).path.rstrip("/"))
    source = source_path.read_text(encoding="utf-8")
    match = MAIN_RE.search(source)
    if match is None:
        fail(f"Print output has no #td-main-content document: {source_path}")
    anchors = AnchorCollector()
    anchors.feed(match.group("body"))
    anchors.close()
    if anchors.duplicates:
        fail("whole-Book Print output contains duplicate cross-page IDs: " + ", ".join(sorted(anchors.duplicates)[:10]))
    parser = BookHTML(
        public=public,
        base_url=base_url,
        pages=manifest["pages"],
        anchor_owners=anchors.owners,
        allow_remote_resources=allow_remote_resources,
    )
    parser.feed(match.group("body"))
    parser.close()
    result = parser.html().strip()
    if not result:
        fail("Print output produced an empty publication document")
    return result + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--public", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--css", action="append", type=Path, default=[])
    parser.add_argument("--resource-path", action="append", type=Path, default=[])
    parser.add_argument("--pandoc", default="pandoc")
    parser.add_argument("--toc-depth", type=int, default=3)
    parser.add_argument("--allow-remote-resources", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        manifest_path = args.manifest.resolve(strict=True)
        public = args.public.resolve(strict=True)
        metadata = args.metadata.resolve(strict=True)
        if not public.is_dir():
            fail(f"public path is not a directory: {public}")
        output = args.output.resolve()
        if output.suffix.lower() != ".epub":
            fail("output must use the .epub suffix")
        if output.exists() and not args.force:
            fail(f"output already exists; pass --force to replace it: {output}")
        pandoc = shutil.which(args.pandoc)
        if pandoc is None:
            fail(f"Pandoc executable was not found: {args.pandoc}")
        manifest = load_manifest(manifest_path)
        html = transformed_html(public, manifest, args.allow_remote_resources)
        css_paths = [path.resolve(strict=True) for path in args.css]
        if not css_paths and DEFAULT_CSS.is_file():
            css_paths = [DEFAULT_CSS]
        resources = [public, metadata.parent, *[path.resolve(strict=True) for path in args.resource_path]]
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="oink-book-epub-") as temporary:
            source = Path(temporary) / "book.html"
            source.write_text(html, encoding="utf-8")
            command = [
                pandoc,
                str(source),
                "--from=html",
                "--to=epub3",
                "--standalone",
                "--toc",
                f"--toc-depth={args.toc_depth}",
                "--split-level=1",
                "--mathml",
                "--wrap=none",
                f"--metadata-file={metadata}",
                f"--resource-path={os.pathsep.join(str(path) for path in resources)}",
                "--output",
                str(output),
            ]
            for css in css_paths:
                command.append(f"--css={css}")
            result = subprocess.run(
                command,
                cwd=metadata.parent,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                fail(f"Pandoc failed ({result.returncode}):\n{result.stdout}{result.stderr}")
        print(
            f"EPUB created: {output} "
            f"({len(manifest['pages'])} pages, {output.stat().st_size} bytes)"
        )
        return 0
    except (OSError, ValueError) as error:
        print(f"Book EPUB packaging failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
