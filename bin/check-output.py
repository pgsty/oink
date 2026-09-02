#!/usr/bin/env python3
"""Structural output checks for the theme fixture.

Over a fresh strict regression fixture by default, or an existing build passed
explicitly with ``--public``:
  1. HTML structure — every strict container element (div, section, nav, ul/ol, table
     parts, a, button, span, main, aside, header, footer, details, summary, figure,
     form, svg, dialog, template, headings, pre, code, blockquote) closes in order;
     void elements and elements with optional end tags are ignored.
  2. duplicate IDs — no id value appears twice on one page.
  3. runtime graph — every page references exactly one shared js/actions bundle,
     every non-print page additionally references the shared js/core shell bundle,
     optional first-party features use unique stable js/chunks/<capability> files,
     no legacy page-combination bundle or remote script appears, and the number
     of distinct capability chunks is reported.
  4. stylesheet graph — the stable Font Awesome distribution precedes the
     consumer-specific main stylesheet on every rendered page.
  5. output security — bin/check-output-security.py over the same build (the
     fixture opts into third-party embeds) plus a synthetic negative fixture that must
     be rejected.
  6. social cards — exactly one featured image reaches Open Graph, schema, and
     Twitter metadata, all three agree, twitter:card follows, and a local card
     URL names a file the build actually shipped.
  7. Markdown labels — the LLMS link and section-page heading follow the active
     language, including localized punctuation in Simplified Chinese.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from test_site import checker_fixture_public, run_hugo_process

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"
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
        self.chunks: list[str] = []
        self.legacy_bundles: list[str] = []
        self.cores: list[str] = []
        self.actions: list[str] = []
        self.base_stylesheets: list[str] = []
        self.action_lines: list[int] = []
        self.manifest_lines: list[int] = []
        self.remote: list[str] = []
        self.in_template = 0
        self.print_chrome: set[str] = set()
        self.theme_init = False

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = dict(attrs_list)
        classes = set((attrs.get("class") or "").split())
        if tag == "template":
            self.in_template += 1
        if tag == "html" and "data-td-theme-init" in attrs:
            self.theme_init = True
        if tag == "header" and "td-site-header" in classes:
            self.print_chrome.add("site header")
        if tag == "nav" and "td-site-nav" in classes:
            self.print_chrome.add("site navigation")
        if attrs.get("id") == "td-shell-search" or "data-td-shell-search-open" in attrs:
            self.print_chrome.add("search")
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
            chunk_match = re.search(
                r"/js/chunks/([a-z0-9-]+?)(?:\.min\.[0-9a-f]{64})?\.js$",
                clean,
            )
            if chunk_match:
                self.chunks.append(chunk_match.group(1))
            if re.search(r"/js/page-[0-9a-f]{32}(?:\.min\.[0-9a-f]{64})?\.js$", clean):
                self.legacy_bundles.append(src)
            if src.startswith(("http://", "https://", "//")):
                self.remote.append(f"script {src[:60]}")
        if tag == "link" and "stylesheet" in (attrs.get("rel") or ""):
            href = attrs.get("href") or ""
            clean = href.split("?", 1)[0]
            if re.search(r"/scss/(?:fontawesome|main)(?:\.min\.[0-9a-f]{64})?\.css$", clean):
                self.base_stylesheets.append(href)
            if href.startswith(("http://", "https://", "//")):
                self.remote.append(f"stylesheet {href[:60]}")

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
    chunk_counts: dict[str, int] = {}
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
        is_print = "/_print/" in f"/{rel}"
        if is_print and parser.print_chrome:
            errors.append(f"{rel}: print output contains shell chrome: {', '.join(sorted(parser.print_chrome))}")
        if is_print and parser.theme_init:
            errors.append(f"{rel}: print output retains the interactive theme-init marker")
        for ident, n in parser.ids.items():
            if n > 1:
                errors.append(f"{rel}: duplicate id {ident!r} ({n}×)")
        # Print omits the core bundle; every other page loads it exactly once.
        if len(parser.actions) != 1:
            errors.append(f"{rel}: expected exactly one actions bundle, found {len(parser.actions)}")
        if len(parser.manifest_lines) != 1:
            errors.append(f"{rel}: expected exactly one action manifest, found {len(parser.manifest_lines)}")
        elif parser.action_lines and parser.manifest_lines[0] >= parser.action_lines[0]:
            errors.append(
                f"{rel}: action manifest line {parser.manifest_lines[0]} must precede "
                f"the actions bundle at line {parser.action_lines[0]}"
            )
        expected_cores = 0 if is_print else 1
        if len(parser.cores) != expected_cores:
            errors.append(f"{rel}: expected {expected_cores} core bundle(s), found {len(parser.cores)}: {parser.cores[:3]}")
        if parser.legacy_bundles:
            errors.append(f"{rel}: legacy page-combination bundle survived: {parser.legacy_bundles[:3]}")
        if len(parser.chunks) != len(set(parser.chunks)):
            errors.append(f"{rel}: repeated runtime chunk(s): {parser.chunks}")
        stylesheet_roles = []
        for href in parser.base_stylesheets:
            match = re.search(r"/scss/(fontawesome|main)(?:\.min\.[0-9a-f]{64})?\.css(?:\?.*)?$", href)
            if match:
                stylesheet_roles.append(match.group(1))
        if stylesheet_roles != ["fontawesome", "main"]:
            errors.append(
                f"{rel}: expected Font Awesome then main stylesheet, found "
                f"{stylesheet_roles}: {parser.base_stylesheets[:4]}"
            )
        for name in parser.chunks:
            chunk_counts[name] = chunk_counts.get(name, 0) + 1
        for r in parser.remote:
            errors.append(f"{rel}: remote asset {r}")
    if pages == 0:
        errors.append("no HTML pages found — build tests/site first")
    return errors, chunk_counts


def check_security(public: Path) -> list[str]:
    errors: list[str] = []
    result = subprocess.run([sys.executable, str(ROOT / "bin/check-output-security.py"), "--public", str(public), "--base-url", "https://example.org/", "--third-party"], capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("check-output-security.py failed on the regression fixture:\n" + result.stdout.strip())
    bad = ROOT / "tests/fixtures/output-security/bad"
    result = subprocess.run([sys.executable, str(ROOT / "bin/check-output-security.py"), "--public", str(bad), "--base-url", "https://example.org/"], capture_output=True, text=True)
    if result.returncode == 0:
        errors.append("check-output-security.py accepted the negative fixture tests/fixtures/output-security/bad")
    else:
        for needle in ("javascript:", "inline event handler", "third-party host", "scheme data:", "protocol-relative"):
            if needle not in result.stdout:
                errors.append(f"check-output-security.py negative fixture did not report {needle!r}")
    return errors


OG_IMAGE = re.compile(r'<meta property="og:image" content="([^"]+)"')
SCHEMA_IMAGE = re.compile(r'<meta itemprop="image" content="([^"]+)"')
TWITTER_CARD = re.compile(r'<meta name="twitter:card" content="([^"]+)"')
TWITTER_IMAGE = re.compile(r'<meta name="twitter:image" content="([^"]+)"')
BASE_URL = "https://example.org/"
HREFLANG = re.compile(r'<link rel="alternate" hreflang="[^"]*" href="([^"]+)">')
LANGUAGE_LINK = re.compile(r'<a class="td-language-selector__(?:trigger|item)" href="([^"]+)"')


def check_social_cards(public: Path) -> list[str]:
    """The image a page shows is the image it shares.

    Hugo's opengraph, twitter_cards, and schema templates take their images from
    `_partials/_funcs/get-page-images.html`, which the theme overrides so the
    featured-image resolver decides for all three. Without that override a page
    renders a featured image and shares nothing, so the wiring is pinned here:
    the card URL has to name a file the build shipped, which also catches a URL
    that lost or repeated a deployment subpath.
    """

    errors: list[str] = []
    carried = 0
    for page in sorted(public.rglob("*.html")):
        name = page.relative_to(public).as_posix()
        text = page.read_text(encoding="utf-8", errors="replace")
        images = OG_IMAGE.findall(text)
        schema = SCHEMA_IMAGE.findall(text)
        card = TWITTER_CARD.search(text)
        twitter = TWITTER_IMAGE.findall(text)
        if not images:
            if schema:
                errors.append(f"{name}: schema image {schema[0]} without og:image")
            if twitter:
                errors.append(f"{name}: twitter:image {twitter[0]} without og:image")
            if card and card.group(1) != "summary":
                errors.append(f"{name}: no image but twitter:card is {card.group(1)!r}")
            continue
        carried += 1
        if len(images) != 1:
            errors.append(f"{name}: expected one representative og:image, found {len(images)}")
        if len(twitter) != 1:
            errors.append(f"{name}: expected one twitter:image, found {len(twitter)}")
        if schema != images:
            errors.append(f"{name}: schema images {schema} disagree with og:image {images}")
        if not twitter:
            errors.append(f"{name}: og:image {images[0]} never reached twitter:image")
        elif twitter[0] != images[0]:
            errors.append(f"{name}: twitter:image {twitter[0]} disagrees with og:image {images[0]}")
        if not card:
            errors.append(f"{name}: og:image {images[0]} without a twitter:card")
        elif card.group(1) != "summary_large_image":
            errors.append(f"{name}: og:image present but twitter:card is {card.group(1)!r}")
        for image in images:
            if not image.startswith(BASE_URL):
                errors.append(f"{name}: og:image {image} is not an absolute URL on the fixture host")
            elif not (public / image[len(BASE_URL):]).is_file():
                errors.append(f"{name}: og:image {image} names a file the build did not ship")
    if not carried:
        errors.append("no page carried og:image — the featured image never reached the social card")
    return errors


def check_language_links(public: Path) -> list[str]:
    """Switching language must not switch hosts.

    A language link is an ordinary internal link and is written relative, so a
    build served from anywhere other than its configured `baseURL` -- `public/`
    behind a local static server, a deploy preview, a LAN address -- switches
    the language in place instead of navigating to the configured domain. The
    absolute form is reserved for a site that gives a language its own
    `baseURL`, which the fixture site does not. `hreflang` alternates are the
    opposite case: they are canonical URLs and must stay absolute.
    """

    errors: list[str] = []
    switches = 0
    alternates = 0
    for page in sorted(public.rglob("*.html")):
        name = page.relative_to(public).as_posix()
        text = page.read_text(encoding="utf-8", errors="replace")
        for href in LANGUAGE_LINK.findall(text):
            switches += 1
            if not href.startswith("/"):
                errors.append(f"{name}: language link {href} is not relative to the serving host")
        for href in HREFLANG.findall(text):
            alternates += 1
            if not href.startswith(BASE_URL):
                errors.append(f"{name}: hreflang alternate {href} is not an absolute canonical URL")
    if not switches:
        errors.append("no page offered a language switch — the bilingual fixture lost its selector")
    if not alternates:
        errors.append("no page emitted an hreflang alternate")
    return errors


def check_markdown_localization(public: Path) -> list[str]:
    """Markdown-only shell labels must use the active page language."""

    errors: list[str] = []
    cases = (
        ("fixtures/callouts/index.md", "LLMS index:", "LLMS 索引："),
        ("docs/index.md", "Section pages:", "本节页面："),
        ("zh/fixtures/callouts/index.md", "LLMS 索引：", "LLMS index:"),
        ("zh/docs/index.md", "本节页面：", "Section pages:"),
    )
    for relative, expected, forbidden in cases:
        path = public / relative
        if not path.is_file():
            errors.append(f"{relative}: localized Markdown fixture output is missing")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not any(line.startswith(expected) for line in lines):
            errors.append(f"{relative}: missing localized Markdown label {expected!r}")
        if any(line.startswith(forbidden) for line in lines):
            errors.append(f"{relative}: leaked Markdown label {forbidden!r} from another language")
    return errors


def check_featured_image_contract(hugo: str) -> list[str]:
    """Pin empty-list discovery, single-card metadata, and SVG resources."""

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-output-featured-") as temp:
        site = Path(temp)

        def write(relative: str, body: str) -> None:
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

        write(
            "hugo.yaml",
            f"""baseURL: {BASE_URL}
title: Featured image fixture
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
params:
  images: [/site-card.svg]
""",
        )
        write(
            "content/blog/_index.md",
            "---\ntitle: Blog\ntype: blog\ncascade:\n  type: blog\n---\n",
        )
        write(
            "content/blog/resource/index.md",
            "---\ntitle: Bundled raster\ndate: 2026-01-04\nimages: []\n---\n\nEmpty images still discovers the bundle.\n",
        )
        raster = site / "content/blog/resource/featured.webp"
        raster.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE / "static/images/oink.webp", raster)
        write(
            "content/blog/vector/index.md",
            "---\ntitle: Bundled vector\ndate: 2026-01-03\nimages: [feature.svg]\n---\n\nAn SVG resource is framed without image processing.\n",
        )
        write(
            "content/blog/vector/feature.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320"><rect width="640" height="320" fill="#2f6793"/></svg>\n',
        )
        write(
            "content/blog/empty.md",
            "---\ntitle: Empty configured image\ndate: 2026-01-02\nimages: []\n---\n\nNo bundle means no thumbnail.\n",
        )
        write(
            "content/blog/single.md",
            "---\ntitle: Single social image\ndate: 2026-01-01\nimages: [/first.svg, /second.svg]\n---\n\nOnly the first configured image is shared.\n",
        )
        for name, color in (("site-card", "#17385c"), ("first", "#2f6793"), ("second", "#d58b46")):
            write(
                f"static/{name}.svg",
                f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320"><rect width="640" height="320" fill="{color}"/></svg>\n',
            )

        public = site / "public"
        result = run_hugo_process(
            [
                hugo,
                "--source",
                str(site),
                "--themesDir",
                str(ROOT.parent),
                "--destination",
                str(public),
                "--printPathWarnings",
                "--panicOnWarning",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"featured-image fixture failed to build: {result.stdout}{result.stderr}"]

        expected = {
            "blog/resource/index.html": f"{BASE_URL}blog/resource/featured.webp",
            "blog/vector/index.html": f"{BASE_URL}blog/vector/feature.svg",
            "blog/empty/index.html": f"{BASE_URL}site-card.svg",
            "blog/single/index.html": f"{BASE_URL}first.svg",
        }
        for relative, image in expected.items():
            source = (public / relative).read_text(encoding="utf-8")
            actual = OG_IMAGE.findall(source)
            if actual != [image]:
                errors.append(f"{relative}: expected one og:image {image}, got {actual}")
            twitter = TWITTER_IMAGE.findall(source)
            if twitter != [image]:
                errors.append(f"{relative}: expected one twitter:image {image}, got {twitter}")
            schema = SCHEMA_IMAGE.findall(source)
            if schema != [image]:
                errors.append(f"{relative}: expected one schema image {image}, got {schema}")

        listing = (public / "blog/index.html").read_text(encoding="utf-8")
        if re.search(r'/blog/resource/featured_hu_[0-9a-f]+\.webp', listing) is None:
            errors.append("blog list did not process the bundled raster discovered after images: []")
        if 'src="/blog/vector/feature.svg"' not in listing:
            errors.append("blog list did not render the non-processable SVG resource as-is")
        # The wrapper carries the published form as an attribute, so match the
        # opening tag rather than a closed one.
        posts_start = listing.find('<div class="td-blog-posts"')
        empty_link = listing.find('href="/blog/empty/"', posts_start)
        empty_start = listing.rfind('<li class="td-blog-posts-list__item">', 0, empty_link)
        empty_end = listing.find("</li>", empty_link)
        if min(empty_link, empty_start, empty_end) < 0:
            errors.append(
                "blog list is missing the empty-image fixture entry "
                f"(link={empty_link}, start={empty_start}, end={empty_end})"
            )
        elif "<img " in listing[empty_start:empty_end]:
            errors.append("images: [] without a bundle rendered the site social card as a thumbnail")
    return errors


THEME_COLOR_STYLE = re.compile(r"<style>[^<]*--td-accent[^<]*</style>")


def check_theme_color_contract(hugo: str) -> list[str]:
    """Pin the theme-color emission: exact derived palettes, no emission
    without configuration, no emission into print, and an invalid value
    dropped whole rather than repaired."""

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-output-theme-color-") as temp:
        site = Path(temp)

        def write(relative: str, body: str) -> None:
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

        write(
            "hugo.yaml",
            f"""baseURL: {BASE_URL}
title: Theme color fixture
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
outputs:
  section: [HTML, print]
""",
        )
        write("content/docs/_index.md", "---\ntitle: Docs\n---\n\nDefault palette.\n")
        # An explicit light/dark pair is emitted verbatim with derived hovers.
        write(
            "content/pair/_index.md",
            "---\ntitle: Pair\ncascade:\n  theme_color: '#7c3aed'\n  theme_color_dark: '#a78bfa'\n---\n\nBoth palettes written.\n",
        )
        write("content/pair/page.md", "---\ntitle: Pair page\n---\n\nInherits both.\n")
        # A light-only section derives its dark palette toward white.
        write(
            "content/solo/_index.md",
            "---\ntitle: Solo\ncascade:\n  theme_color: '#7c3aed'\n---\n\nDark derives.\n",
        )
        write(
            "content/solo/own.md",
            "---\ntitle: Own\ntheme_color: '#0f766e'\n---\n\nPage override, full derived palette.\n",
        )
        # The bare-boolean idiom: false opts a page out of the section's
        # color, inherited dark half included, without a word -- this file
        # sits inside the --panicOnWarning build, which is the proof.
        write(
            "content/solo/optout.md",
            "---\ntitle: Optout\ntheme_color: false\n---\n\nDeliberately plain.\n",
        )
        # A dark corporate navy: the first +32% step still reads under 4.5:1
        # on the dark canvas, so the derivation walks to +36% -- the
        # derive-to-target contract, not a fixed constant.
        write(
            "content/deep/_index.md",
            "---\ntitle: Deep\ncascade:\n  theme_color: '#1e3a8a'\n---\n\nNavy walks a step further.\n",
        )

        public = site / "public"
        command = [hugo, "--source", str(site), "--themesDir", str(ROOT.parent),
                   "--destination", str(public), "--printPathWarnings", "--panicOnWarning"]
        result = run_hugo_process(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return [f"theme-color fixture failed to build: {result.stdout}{result.stderr}"]

        # A theme color drives accent GROUNDS only. The Bootstrap link family
        # is deliberately absent: prose links, external URLs and inline code
        # keep the brand palette in every section.
        light_7c = (":root,[data-bs-theme=light]{--td-accent:#7c3aed;"
                    "--td-accent-rgb:124,58,237;--td-accent-hover:#8c52ef}")
        expected = {
            "pair/page/index.html": "<style>" + light_7c
            + "[data-bs-theme=dark]{--td-accent:#a78bfa;--td-accent-rgb:167,139,250;"
              "--td-accent-hover:#baa5fb}</style>",
            "solo/index.html": "<style>" + light_7c
            + "[data-bs-theme=dark]{--td-accent:#a679f3;--td-accent-rgb:166,121,243;"
              "--td-accent-hover:#ba96f6}</style>",
            "solo/own/index.html": "<style>:root,[data-bs-theme=light]{--td-accent:#0f766e;"
            "--td-accent-rgb:15,118,110;--td-accent-hover:#2c867f}"
            "[data-bs-theme=dark]{--td-accent:#5ca29c;--td-accent-rgb:92,162,156;"
            "--td-accent-hover:#80b6b2}</style>",
            "deep/index.html": "<style>:root,[data-bs-theme=light]{--td-accent:#1e3a8a;"
            "--td-accent-rgb:30,58,138;--td-accent-hover:#395298}"
            # The hover's blue channel lands on an exact .5 and Hugo's
            # math.Round goes away from zero: 180 + round(75*0.22) = 197.
            "[data-bs-theme=dark]{--td-accent:#6f81b4;--td-accent-rgb:111,129,180;"
            "--td-accent-hover:#8f9dc5}</style>",
        }
        for relative, style in expected.items():
            source = (public / relative).read_text(encoding="utf-8")
            found = THEME_COLOR_STYLE.findall(source)
            if found != [style]:
                errors.append(f"{relative}: expected the exact theme-color style block, got {found}")
        for relative in ("docs/index.html", "solo/optout/index.html", "_print/solo/index.html"):
            if "--td-accent:#" in (public / relative).read_text(encoding="utf-8"):
                errors.append(f"{relative}: emitted theme-color tokens it must not carry")
        generic_print = (public / "_print/solo/index.html").read_text(encoding="utf-8")
        parsed_print = Structure("_print/solo/index.html")
        parsed_print.feed(generic_print)
        if parsed_print.print_chrome or parsed_print.theme_init:
            errors.append("generic print output contains shell chrome or theme initialization")

        # An invalid value warns, builds, and emits nothing -- never a
        # repaired or partial style block. A low-contrast value warns too,
        # but ships: the contrast check is advisory, not a validity gate.
        write("content/solo/bad.md",
              "---\ntitle: Bad\ntheme_color: 'url(x);}html{--x:'\n---\n\nDropped whole.\n")
        write("content/solo/loud.md",
              "---\ntitle: Loud\ntheme_color: '#ffff00'\n---\n\nWarned, kept.\n")
        # The light color is the key. A dark color alone, or one beside an
        # invalid light value, must not leak a dark-only block: the page is
        # colored in both modes or in neither, and the head block and the
        # root switcher read the same answer.
        write("content/dusk/_index.md",
              "---\ntitle: Dusk\ncascade:\n  theme_color_dark: '#a78bfa'\n---\n\nUnpaired dark.\n")
        write("content/solo/mixed.md",
              "---\ntitle: Mixed\ntheme_color: tomato\ntheme_color_dark: '#a78bfa'\n---\n\nInvalid light, valid dark.\n")
        write("content/solo/zero.md",
              "---\ntitle: Zero\ntheme_color: 0\n---\n\nA number is a mistake, said out loud.\n")
        result = run_hugo_process([hugo, "--source", str(site), "--themesDir", str(ROOT.parent),
                                 "--destination", str(public), "--logLevel", "warn"],
                                capture_output=True, text=True, check=False)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            errors.append(f"an invalid theme_color stopped the build instead of warning: {output[-400:]}")
        if "is not a #rgb or #rrggbb hex color" not in output:
            errors.append(f"an invalid theme_color did not warn with the hex shape: {output[-400:]}")
        bad = (public / "solo/bad/index.html").read_text(encoding="utf-8")
        if "url(x)" in bad:
            errors.append("an invalid theme_color leaked into the emitted output")
        # The page's own key shadows the cascade in Hugo's params merge, so
        # dropping the invalid value leaves the default palette -- no block
        # at all, never a repaired or partial one.
        if THEME_COLOR_STYLE.findall(bad):
            errors.append("an invalid page theme_color still emitted a style block")
        if "AA body text needs 4.5:1" not in output:
            errors.append(f"a low-contrast theme_color did not warn with the AA reading: {output[-400:]}")
        loud = (public / "solo/loud/index.html").read_text(encoding="utf-8")
        if "--td-accent:#ffff00" not in loud:
            errors.append("a low-contrast theme_color was dropped; the contrast warning is advisory and must ship the color")
        if 'theme_color "0"' not in output:
            errors.append(f"a numeric theme_color was swallowed instead of warned: {output[-400:]}")
        if THEME_COLOR_STYLE.findall((public / "solo/zero/index.html").read_text(encoding="utf-8")):
            errors.append("a numeric theme_color still emitted a style block")
        if "has no theme_color to pair with" not in output:
            errors.append(f"an unpaired theme_color_dark did not warn: {output[-400:]}")
        for relative, case in (("dusk/index.html", "an unpaired theme_color_dark"),
                               ("solo/mixed/index.html", "a theme_color_dark beside an invalid theme_color")):
            if THEME_COLOR_STYLE.findall((public / relative).read_text(encoding="utf-8")):
                errors.append(f"{case} leaked a dark-only style block")
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
            "site-social-card",
            {"HUGOxPARAMSxIMAGES": "javascript:alert(1)"},
            "unsupported images scheme",
        ),
    )
    strict_canaries = {"wordmark", "site-social-card"}
    for name, overrides, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-output-{name}-") as temp:
            environment = {**os.environ, **overrides}
            result = run_hugo_process(
                [
                    hugo,
                    "--source",
                    str(FIXTURE),
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
            # The URL validator warns and drops the value rather than stopping
            # the build; refusing to emit it is the protection. What must hold
            # is that the problem is named and that publishing still fails.
            if expected not in output:
                errors.append(f"configured image case {name} did not report {expected!r}: {output[-400:]}")
            if result.returncode != 0:
                errors.append(f"configured image case {name} stopped the ordinary build: {output[-400:]}")
            home = Path(temp) / "public/index.html"
            if not home.is_file():
                errors.append(f"configured image case {name} emitted no safe home output")
            if name == "site-social-card":
                metadata = home.read_text(encoding="utf-8") if home.is_file() else ""
                if OG_IMAGE.findall(metadata) or SCHEMA_IMAGE.findall(metadata) or TWITTER_IMAGE.findall(metadata):
                    errors.append("an invalid site social card still reached page metadata")
            if name in strict_canaries:
                strict = run_hugo_process(
                    [
                        hugo,
                        "--source",
                        str(FIXTURE),
                        "--destination",
                        str(Path(temp) / "public-strict"),
                        "--logLevel",
                        "warn",
                        "--panicOnWarning",
                    ],
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if strict.returncode == 0:
                    errors.append(f"configured image case {name} survived --panicOnWarning")
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


def check_merge_markers(public: Path) -> list[str]:
    """No unresolved merge marker reached the rendered output.

    A conflict marker left in a template is not a template error: Hugo emits it
    as literal text, every string-presence assertion still passes, and a golden
    refreshed afterwards enshrines it. Only the product shows the damage, so
    the guard belongs here. Authored content is safe from the match -- Goldmark
    escapes `<` in prose and in fenced code -- so a raw marker at the start of a
    line in the output came from a template.
    """

    errors: list[str] = []
    # Leading whitespace is kept by Hugo, so the marker is rarely at column 0.
    # Only the two markers that carry a ref are matched: a bare `=======` is a
    # plausible line of authored ASCII art, and two of the three are enough to
    # catch any real conflict.
    pattern = re.compile(r"^[ \t]*(?:<{7}|>{7}) \S", re.M)
    for path in sorted(public.rglob("*")):
        if not path.is_file() or path.suffix not in (".html", ".xml", ".txt", ".md", ".json"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            snippet = text[match.start():match.start() + 40].splitlines()[0]
            errors.append(
                f"{path.relative_to(public).as_posix()}:{line}: "
                f"unresolved merge marker in the output ({snippet!r})")
    return errors[:20]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--public", type=Path)
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()
    public, result = checker_fixture_public(args.public, args.hugo)
    if result is not None and result.returncode != 0:
        print("Strict regression fixture failed to build:")
        print(result.stdout + result.stderr)
        return 1
    errors = self_test()
    html_errors, chunks = check_html(public)
    errors += html_errors
    errors += check_merge_markers(public)
    errors += check_security(public)
    errors += check_social_cards(public)
    errors += check_language_links(public)
    errors += check_markdown_localization(public)
    errors += check_featured_image_contract(args.hugo)
    errors += check_theme_color_contract(args.hugo)
    errors += check_config_image_policy(args.hugo)
    if errors:
        print("Output checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"Output checks passed ({len(chunks)} stable runtime chunks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
