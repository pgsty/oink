#!/usr/bin/env python3
"""Render an opt-in OINK BookManifest's whole-Book Print view as PDF."""

from __future__ import annotations

import argparse
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import posixpath
import shutil
import subprocess
import sys
import tempfile
from threading import Thread
from typing import NoReturn
from urllib.parse import quote, unquote, urlsplit


MAC_CHROME = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
)
RESOURCE_LINK_RELS = {"icon", "modulepreload", "preload", "stylesheet"}
REMOTE_MEDIA_TAGS = {"audio", "img", "source", "track", "video"}
PUBLICATION_CSP = (
    "default-src 'none'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self' data:; "
    "img-src 'self' data: http: https:; "
    "media-src 'self' data: http: https:; "
    "script-src 'none'; connect-src 'none'; frame-src 'none'; "
    "object-src 'none'; base-uri 'none'"
)


def fail(message: str) -> NoReturn:
    raise ValueError(message)


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
    book = value.get("book")
    if not isinstance(book, dict) or not book.get("print"):
        fail("BookManifest book.print is required")
    base_url = value.get("baseURL")
    if not isinstance(base_url, str) or urlsplit(base_url).scheme not in {"http", "https"}:
        fail("BookManifest baseURL must be an absolute HTTP(S) URL")
    return value


def print_document(public: Path, manifest: dict) -> tuple[Path, str, str]:
    base_path = urlsplit(str(manifest["baseURL"])).path.rstrip("/")
    raw_path = unquote(urlsplit(str(manifest["book"]["print"])).path or "/")
    served_path = raw_path
    if not served_path.startswith("/"):
        served_path = "/" + served_path
    candidate = public_file(public, raw_path, base_path)
    if raw_path.endswith("/"):
        candidate /= "index.html"
    if not candidate.is_file():
        fail(f"whole-Book Print output is missing: {candidate}")
    return candidate, served_path, base_path


def resource_url(value: str, document_route: str) -> str:
    parsed = urlsplit(value)
    if parsed.path.startswith("/"):
        return parsed.path
    return "/" + posixpath.normpath(
        posixpath.join(posixpath.dirname(document_route), parsed.path)
    ).lstrip("/")


class PublicationResources(HTMLParser):
    """Collect fetched resources, excluding ordinary outbound hyperlinks."""

    def __init__(self) -> None:
        super().__init__()
        self.resources: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = dict(attrs)
        for name in ("src", "poster"):
            value = values.get(name)
            if value:
                self.resources.append((tag, name, value))
        srcset = values.get("srcset")
        if srcset:
            for candidate in srcset.split(","):
                value = candidate.strip().split()[0] if candidate.strip() else ""
                if value:
                    self.resources.append((tag, "srcset", value))
        if tag == "object" and values.get("data"):
            self.resources.append((tag, "data", str(values["data"])))
        if tag == "link" and values.get("href"):
            rels = set((values.get("rel") or "").lower().split())
            if rels & RESOURCE_LINK_RELS:
                self.resources.append((tag, "href", str(values["href"])))


def validate_resources(
    document: Path,
    *,
    public: Path,
    document_route: str,
    base_path: str,
    allow_remote_resources: bool,
) -> None:
    parser = PublicationResources()
    parser.feed(document.read_text(encoding="utf-8"))
    parser.close()
    for tag, attribute, value in parser.resources:
        parsed = urlsplit(value)
        if parsed.scheme == "data":
            continue
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            fail(f"unsupported publication resource scheme: <{tag} {attribute}> {value}")
        if parsed.scheme or parsed.netloc:
            if tag not in REMOTE_MEDIA_TAGS:
                fail(f"remote active publication resource is not allowed: <{tag}> {value}")
            if not allow_remote_resources:
                fail(f"remote publication resource is not allowed: <{tag}> {value}")
            continue
        route = resource_url(value, document_route)
        candidate = public_file(public, route, base_path)
        if not candidate.is_file():
            fail(f"local publication resource is missing: {value} -> {candidate}")


def find_chrome(value: str | None) -> str:
    if value:
        candidate = Path(value).expanduser().resolve()
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            fail(f"Chrome executable is not runnable: {candidate}")
        return str(candidate)
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        candidate = shutil.which(name)
        if candidate:
            return candidate
    for candidate in MAC_CHROME:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    fail("Chrome/Chromium was not found; pass --chrome with an executable path")


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: object, base_path: str = "", **kwargs: object) -> None:
        self.base_path = base_path
        super().__init__(*args, **kwargs)

    def translate_path(self, path: str) -> str:
        parsed = urlsplit(path)
        route = parsed.path
        if self.base_path and (
            route == self.base_path or route.startswith(self.base_path + "/")
        ):
            route = route[len(self.base_path) :] or "/"
        if parsed.query:
            route += "?" + parsed.query
        return super().translate_path(route)

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", PUBLICATION_CSP)
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--public", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--chrome")
    parser.add_argument("--virtual-time-budget", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--allow-remote-resources", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        manifest_path = args.manifest.resolve(strict=True)
        public = args.public.resolve(strict=True)
        if not public.is_dir():
            fail(f"public path is not a directory: {public}")
        output = args.output.resolve()
        if output.suffix.lower() != ".pdf":
            fail("output must use the .pdf suffix")
        if output.exists() and not args.force:
            fail(f"output already exists; pass --force to replace it: {output}")
        if args.virtual_time_budget < 0:
            fail("virtual-time-budget must not be negative")
        if args.timeout < 1:
            fail("timeout must be at least one second")

        manifest = load_manifest(manifest_path)
        document, served_path, base_path = print_document(public, manifest)
        validate_resources(
            document,
            public=public,
            document_route=served_path,
            base_path=base_path,
            allow_remote_resources=args.allow_remote_resources,
        )
        chrome = find_chrome(args.chrome)
        version = subprocess.run(
            [chrome, "--version"], capture_output=True, text=True, check=False, timeout=10
        )
        if version.returncode != 0:
            fail(f"cannot read Chrome version: {version.stdout}{version.stderr}")

        output.parent.mkdir(parents=True, exist_ok=True)
        handler = partial(QuietHandler, directory=str(public), base_path=base_path)
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                url = f"http://{host}:{port}{quote(served_path, safe='/@:')}"
                with tempfile.TemporaryDirectory(prefix="oink-book-pdf-") as profile:
                    # Chrome prints into the temporary profile; the file moves
                    # to --output only after it proves structurally complete,
                    # so a failed run never strands a half-written artifact for
                    # the next run's exists-without---force gate to refuse.
                    rendered = Path(profile) / "book.pdf"
                    command = [
                        chrome,
                        "--headless",
                        "--disable-background-networking",
                        "--disable-component-update",
                        "--disable-default-apps",
                        "--disable-extensions",
                        "--disable-sync",
                        "--metrics-recording-only",
                        "--mute-audio",
                        "--no-default-browser-check",
                        "--no-first-run",
                        "--no-pdf-header-footer",
                        "--run-all-compositor-stages-before-draw",
                        f"--user-data-dir={profile}",
                        f"--print-to-pdf={rendered}",
                    ]
                    if args.virtual_time_budget:
                        command.append(f"--virtual-time-budget={args.virtual_time_budget}")
                    if not args.allow_remote_resources:
                        # ~NOTFOUND fails every non-loopback lookup outright.
                        # Mapping to 0.0.0.0 would connect to loopback on
                        # Linux, where a remapped remote fetch could reach a
                        # local service listening on 80/443.
                        command.append("--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1")
                    command.append(url)
                    timed_out = None
                    result = None
                    try:
                        result = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=args.timeout,
                        )
                    except subprocess.TimeoutExpired as error:
                        timed_out = error
                    if result is not None and result.returncode != 0:
                        fail(f"Chrome failed ({result.returncode}):\n{result.stdout}{result.stderr}")
                    tail = rendered.read_bytes()[-1024:] if rendered.is_file() else b""
                    complete = (
                        rendered.is_file()
                        and rendered.stat().st_size >= 1024
                        and rendered.read_bytes()[:5] == b"%PDF-"
                        and b"%%EOF" in tail
                    )
                    if not complete:
                        if timed_out is not None:
                            fail(f"Chrome timed out after {args.timeout} seconds: {timed_out}")
                        fail(f"Chrome did not produce a usable PDF: {rendered}")
                    shutil.move(str(rendered), str(output))
                    if timed_out is not None:
                        # Desktop Chrome on some platforms finishes the write
                        # and then never exits; the artifact is complete, so
                        # the render succeeded -- but say what happened and
                        # name the binary that exits cleanly.
                        print(
                            f"warning: Chrome wrote the whole PDF but had to be killed after "
                            f"{args.timeout}s; desktop Chrome may never exit under --headless "
                            "-- chrome-headless-shell (or Chrome for Testing) exits cleanly",
                            file=sys.stderr,
                        )
            finally:
                server.shutdown()
                thread.join(timeout=5)

        browser = (version.stdout or version.stderr).strip()
        print(f"PDF created: {output} ({output.stat().st_size} bytes; {browser})")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Book PDF rendering failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
