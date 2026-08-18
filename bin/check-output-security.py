#!/usr/bin/env python3
"""Product-level trust checks over a built site.

Authors are trusted (`unsafe: true` baseline) so there is no element allowlist;
instead the *outputs* — html, print html, markdown, rss/xml — must satisfy:

  1. every href / src / srcset / poster (and form action) is site-relative or uses
     one of the schemes http, https, mailto, tel — never javascript:, data:, vbscript:
     or an unknown scheme;
  2. <iframe> <script> <link> <img> <video> <audio> <embed> <object> <source> that
     reference another host fail unless the run passes --third-party (the site
     knowingly embeds third-party content);
  3. no inline event handlers (on*=) and no javascript: URLs anywhere;
  4. <form action> to another host also needs privacy.third_party.

Usage:
  bin/check-output-security.py --public exampleSite/public --base-url https://example.org/
  bin/check-output-security.py --public DIR --base-url URL --third-party   # site embeds third-party content
  --allow-host HOST   additional hosts treated as first-party (repeatable; multihost languages)
Exit 1 with a per-file report on any violation.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_SCHEMES = {"http", "https", "mailto", "tel"}
URL_ATTRS = {"href", "src", "srcset", "poster"}
REMOTE_ELEMENTS = {"iframe", "script", "link", "img", "video", "audio", "embed", "object", "source"}
SKIP_LINK_RELS = {"canonical", "alternate", "prev", "next", "me", "author", "license", "help", "search"}


class Scanner(HTMLParser):
    def __init__(self, path: str, base_host: str, first_party: set[str], third_party: bool):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.base_host = base_host
        self.first_party = first_party
        self.third_party = third_party
        self.problems: list[str] = []

    def report(self, message: str) -> None:
        self.problems.append(f"{self.path}:{self.getpos()[0]}: {message}")

    def check_url(self, tag: str, attr: str, value: str, attrs: dict[str, str | None]) -> None:
        raw = (value or "").strip()
        if not raw:
            return
        candidates = [raw]
        if attr == "srcset":
            candidates = [part.strip().split(" ")[0] for part in raw.split(",") if part.strip()]
        for candidate in candidates:
            lowered = candidate.lower()
            if lowered.startswith("javascript:") or lowered.startswith("vbscript:"):
                self.report(f"<{tag} {attr}> uses {lowered.split(':', 1)[0]}: ({candidate[:60]})")
                continue
            if candidate.startswith("//"):
                self.report(f"<{tag} {attr}> is protocol-relative ({candidate[:60]})")
                continue
            parts = urlsplit(candidate)
            if parts.scheme:
                if parts.scheme.lower() not in ALLOWED_SCHEMES:
                    self.report(f"<{tag} {attr}> uses scheme {parts.scheme}: ({candidate[:60]})")
                    continue
                host = (parts.hostname or "").lower()
                if parts.scheme.lower() in ("http", "https") and host and host != self.base_host and host not in self.first_party:
                    if tag in REMOTE_ELEMENTS and not (tag == "link" and (attrs.get("rel") or "").lower().split() and set((attrs.get("rel") or "").lower().split()) & SKIP_LINK_RELS):
                        if not self.third_party:
                            self.report(f"<{tag} {attr}> loads from third-party host {host} (pass --third-party if intended) ({candidate[:60]})")
                    if tag == "form" and attr == "action" and not self.third_party:
                        self.report(f"<form action> submits to third-party host {host} (pass --third-party if intended)")

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k.lower(): v for k, v in attrs_list}
        for name, value in attrs.items():
            if name.startswith("on") and len(name) > 2:
                self.report(f"<{tag}> has inline event handler {name}")
            if name in URL_ATTRS or (tag == "form" and name == "action"):
                self.check_url(tag, name, value or "", attrs)

    handle_startendtag = handle_starttag


def scan_html(path: Path, rel: str, base_host: str, first_party: set[str], third_party: bool) -> list[str]:
    scanner = Scanner(rel, base_host, first_party, third_party)
    try:
        scanner.feed(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return [f"{rel}: could not parse ({exc})"]
    return scanner.problems


MD_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)")
XML_ATTR = re.compile(r'\b(?:href|src|url)\s*=\s*"([^"]+)"', re.I)


def scan_markdown(path: Path, rel: str) -> list[str]:
    problems = []
    for match in MD_LINK.finditer(path.read_text(encoding="utf-8", errors="replace")):
        target = match.group(1).strip().lower()
        if target.startswith(("javascript:", "vbscript:", "data:")):
            problems.append(f"{rel}: markdown link uses {target.split(':', 1)[0]}: ({target[:60]})")
    return problems


def scan_xml(path: Path, rel: str, base_host: str, first_party: set[str], third_party: bool) -> list[str]:
    """RSS/XML: check embedded HTML (escaped in <description>/<content>) after unescaping."""
    import html
    text = html.unescape(path.read_text(encoding="utf-8", errors="replace"))
    scanner = Scanner(rel, base_host, first_party, third_party)
    try:
        scanner.feed(text)
    except Exception as exc:  # noqa: BLE001
        return [f"{rel}: could not parse ({exc})"]
    return scanner.problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--base-url", required=True, help="site baseURL (host comparison)")
    parser.add_argument("--third-party", action="store_true", help="the site knowingly embeds third-party content")
    parser.add_argument("--allow-host", action="append", default=[], help="extra first-party hosts (repeatable)")
    parser.add_argument("--max-report", type=int, default=50)
    args = parser.parse_args()
    base_host = (urlsplit(args.base_url).hostname or "").lower()
    first_party = {h.lower() for h in args.allow_host}
    problems: list[str] = []
    files = 0
    for path in sorted(args.public.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(args.public).as_posix()
        suffix = path.suffix.lower()
        if suffix in {".html", ".htm"}:
            problems += scan_html(path, rel, base_host, first_party, args.third_party)
        elif suffix == ".md":
            problems += scan_markdown(path, rel)
        elif suffix == ".xml" and path.name != "sitemap.xml":
            problems += scan_xml(path, rel, base_host, first_party, args.third_party)
        else:
            continue
        files += 1
    if problems:
        print(f"Output security check failed ({len(problems)} problem(s) in {files} files):")
        for problem in problems[: args.max_report]:
            print(f"  {problem}")
        if len(problems) > args.max_report:
            print(f"  … {len(problems) - args.max_report} more")
        return 1
    print(f"Output security check passed ({files} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
