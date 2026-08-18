#!/usr/bin/env python3
"""Structural output checks for the theme fixture.

Over the built exampleSite (--public, default exampleSite/public):
  1. HTML structure — every strict container element (div, section, nav, ul/ol, table
     parts, a, button, span, main, aside, header, footer, details, summary, figure,
     form, svg, dialog, template, headings, pre, code, blockquote) closes in order;
     void elements and elements with optional end tags are ignored.
  2. duplicate IDs — no id value appears twice on one page.
  3. bundle graph — every page references exactly one shared js/actions bundle,
     every non-print page additionally references the shared js/core shell bundle,
     any page references at most one per-page js/page-<key> feature bundle, no
     remote <script src> / stylesheet <link> appears, and the number of distinct
     feature bundles is reported.
  4. output security — bin/check-output-security.py over the same build (the
     fixture opts into third-party embeds) plus a synthetic negative fixture that must
     be rejected.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
STRICT = {"div", "section", "article", "nav", "ul", "ol", "table", "thead", "tbody", "tfoot", "a", "button", "span",
          "main", "aside", "header", "footer", "details", "summary", "figure", "figcaption", "form", "select", "svg",
          "symbol", "template", "dialog", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "code", "blockquote", "label",
          "small", "strong", "em", "kbd", "dl", "fieldset", "legend", "picture", "video", "audio", "textarea", "script", "style", "noscript", "title"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr",
        "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "use", "stop"}


class Structure(HTMLParser):
    def __init__(self, rel: str):
        super().__init__(convert_charrefs=True)
        self.rel = rel
        self.stack: list[tuple[str, int]] = []
        self.ids: dict[str, int] = {}
        self.problems: list[str] = []
        self.bundles: list[str] = []
        self.cores: list[str] = []
        self.actions: list[str] = []
        self.action_lines: list[int] = []
        self.manifest_lines: list[int] = []
        self.remote: list[str] = []
        self.in_template = 0

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = dict(attrs_list)
        if tag == "template":
            self.in_template += 1
        if tag in STRICT and tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))
        ident = attrs.get("id")
        if ident and not self.in_template:
            self.ids[ident] = self.ids.get(ident, 0) + 1
        if tag == "script" and ident == "td-action-manifest":
            self.manifest_lines.append(self.getpos()[0])
        if tag == "script" and attrs.get("src"):
            src = attrs["src"]
            clean = src.split("?", 1)[0]
            if re.search(r"/js/actions(?:\.min\.[0-9a-f]{64})?\.js$", clean):
                self.actions.append(src)
                self.action_lines.append(self.getpos()[0])
            if re.search(r"/js/core(?:\.min\.[0-9a-f]{64})?\.js$", clean):
                self.cores.append(src)
            if re.search(r"/js/page-[0-9a-f]{32}(?:\.min\.[0-9a-f]{64})?\.js$", clean):
                self.bundles.append(src)
            if src.startswith(("http://", "https://", "//")):
                self.remote.append(f"script {src[:60]}")
        if tag == "link" and "stylesheet" in (attrs.get("rel") or "") and (attrs.get("href") or "").startswith(("http://", "https://", "//")):
            self.remote.append(f"stylesheet {attrs.get('href')[:60]}")

    def handle_startendtag(self, tag: str, attrs_list) -> None:
        # <foo/> — treat as open+close only for non-void tags
        attrs = dict(attrs_list)
        ident = attrs.get("id")
        if ident and not self.in_template:
            self.ids[ident] = self.ids.get(ident, 0) + 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "template" and self.in_template:
            self.in_template -= 1
        if tag not in STRICT or tag in VOID:
            return
        # pop to the matching open tag; anything skipped over was left open
        for depth in range(len(self.stack) - 1, -1, -1):
            if self.stack[depth][0] == tag:
                skipped = self.stack[depth + 1:]
                for name, line in skipped:
                    self.problems.append(f"{self.rel}:{line}: <{name}> not closed before </{tag}> (line {self.getpos()[0]})")
                del self.stack[depth:]
                return
        self.problems.append(f"{self.rel}:{self.getpos()[0]}: stray </{tag}>")

    def close_all(self) -> None:
        for name, line in self.stack:
            self.problems.append(f"{self.rel}:{line}: <{name}> never closed")


def check_html(public: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    bundle_counts: dict[str, int] = {}
    pages = 0
    for path in sorted(public.rglob("*.html")):
        rel = path.relative_to(public).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if "<body" not in text and "http-equiv=\"refresh\"" in text.replace("'", '"'):
            continue  # alias redirect stub
        pages += 1
        parser = Structure(rel)
        parser.feed(text)
        parser.close_all()
        errors += parser.problems[:20]
        for ident, n in parser.ids.items():
            if n > 1:
                errors.append(f"{rel}: duplicate id {ident!r} ({n}×)")
        # Print pages carry no shell runtime at all; every other page loads the
        # one shared core exactly once and at most one feature bundle.
        if len(parser.actions) != 1:
            errors.append(f"{rel}: expected exactly one actions bundle, found {len(parser.actions)}")
        if len(parser.manifest_lines) != 1:
            errors.append(f"{rel}: expected exactly one action manifest, found {len(parser.manifest_lines)}")
        elif parser.action_lines and parser.manifest_lines[0] >= parser.action_lines[0]:
            errors.append(
                f"{rel}: action manifest line {parser.manifest_lines[0]} must precede "
                f"the actions bundle at line {parser.action_lines[0]}"
            )
        expected_cores = 0 if "/_print/" in f"/{rel}" else 1
        if len(parser.cores) != expected_cores:
            errors.append(f"{rel}: expected {expected_cores} core bundle(s), found {len(parser.cores)}: {parser.cores[:3]}")
        if len(parser.bundles) > 1:
            errors.append(f"{rel}: expected at most one feature bundle, found {len(parser.bundles)}: {parser.bundles[:3]}")
        if expected_cores == 0 and parser.bundles:
            # A print page may still need diagram runtimes, but never the shell ones.
            for b in parser.bundles:
                bundle_counts[b] = bundle_counts.get(b, 0) + 1
        for b in parser.bundles:
            bundle_counts[b] = bundle_counts.get(b, 0) + 1
        for r in parser.remote:
            errors.append(f"{rel}: remote asset {r}")
    if pages == 0:
        errors.append("no HTML pages found — build exampleSite first")
    return errors, bundle_counts


def check_security(public: Path) -> list[str]:
    errors: list[str] = []
    result = subprocess.run([sys.executable, str(ROOT / "bin/check-output-security.py"), "--public", str(public), "--base-url", "https://example.org/", "--third-party"], capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("check-output-security.py failed on exampleSite:\n" + result.stdout.strip())
    bad = ROOT / "tests/fixtures/output-security/bad"
    result = subprocess.run([sys.executable, str(ROOT / "bin/check-output-security.py"), "--public", str(bad), "--base-url", "https://example.org/"], capture_output=True, text=True)
    if result.returncode == 0:
        errors.append("check-output-security.py accepted the negative fixture tests/fixtures/output-security/bad")
    else:
        for needle in ("javascript:", "inline event handler", "third-party host", "scheme data:", "protocol-relative"):
            if needle not in result.stdout:
                errors.append(f"check-output-security.py negative fixture did not report {needle!r}")
    return errors


def check_config_image_policy(hugo: str) -> list[str]:
    """Configured shell images must reach the same URL policy as content."""

    errors: list[str] = []
    cases = (
        (
            "wordmark",
            {"HUGOxPARAMSxWORDMARK": "//evil.example/wordmark.svg"},
            "wordmark must not use a protocol-relative URL",
        ),
        (
            "logo-without-footer",
            {
                "HUGOxPARAMSxLOGO": "//evil.example/logo.svg",
                "HUGOxPARAMSxUIxFOOTER_STYLE": "none",
            },
            "logo must not use a protocol-relative URL",
        ),
        (
            "default-featured",
            {"HUGOxPARAMSxDEFAULT_FEATURED": "//evil.example/featured.svg"},
            "src must not use a protocol-relative URL",
        ),
    )
    for name, overrides, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-output-{name}-") as temp:
            environment = {**os.environ, **overrides}
            result = subprocess.run(
                [
                    hugo,
                    "--source",
                    str(EXAMPLE),
                    "--destination",
                    str(Path(temp) / "public"),
                    "--logLevel",
                    "warn",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                errors.append(f"configured image case {name} unexpectedly built")
            elif expected not in output:
                errors.append(f"configured image case {name} did not report {expected!r}: {output[-400:]}")
    return errors


def self_test() -> list[str]:
    """The structure parser must catch what it claims to catch."""
    errors: list[str] = []
    bad = Structure("self-test.html")
    bad.feed('<div id="a"><section><span id="a">x</div><p>optional end tags are fine<script src="https://cdn.example.net/x.js"></script>')
    bad.close_all()
    text = " ".join(bad.problems) + " " + " ".join(bad.remote)
    if "<section> not closed" not in text and "<span> not closed" not in text:
        errors.append("self-test: unclosed elements were not reported")
    if bad.ids.get("a") != 2:
        errors.append("self-test: duplicate ids were not counted")
    if not bad.remote:
        errors.append("self-test: remote script was not reported")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--public", type=Path, default=EXAMPLE / "public")
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()
    errors = self_test()
    html_errors, bundles = check_html(args.public)
    errors += html_errors
    errors += check_security(args.public)
    errors += check_config_image_policy(args.hugo)
    if errors:
        print("Output checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"Output checks passed ({len(bundles)} distinct feature bundles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
