#!/usr/bin/env python3
"""Validate reading primitives: math passthrough and pager behavior."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit

from test_site import fixture_config_args, run_hugo_process

from test_site import theme_warnings


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"


class NavigationParser(HTMLParser):
    """Collect sidebar, pager, and head-link destinations from one page."""

    def __init__(self) -> None:
        super().__init__()
        self.in_sidebar = False
        self.sidebar_links: list[str] = []
        self.sidebar_current: list[str] = []
        self.sidebar_expanded: list[str] = []
        self.pager_links: dict[str, str] = {}
        self.head_links: dict[str, str] = {}
        self.has_pager = False
        self.has_disabled_pager = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "nav" and values.get("id") == "td-section-nav":
            self.in_sidebar = True
        if self.in_sidebar and tag == "a" and "td-shell-tree__link" in classes:
            if href := values.get("href"):
                self.sidebar_links.append(href)
                if values.get("aria-current") == "page":
                    self.sidebar_current.append(href)
        if self.in_sidebar and tag == "button" and values.get("aria-expanded") == "true":
            self.sidebar_expanded.append(values.get("aria-controls") or "")
        if tag == "nav" and "td-pager" in classes:
            self.has_pager = True
        if tag == "a":
            if "data-td-pager-prev" in values and values.get("href"):
                self.pager_links["prev"] = values["href"] or ""
            if "data-td-pager-next" in values and values.get("href"):
                self.pager_links["next"] = values["href"] or ""
            if "disabled" in classes and (
                "data-td-pager-prev" in values or "data-td-pager-next" in values
            ):
                self.has_disabled_pager = True
        if tag == "link" and values.get("rel") in ("prev", "next"):
            if href := values.get("href"):
                self.head_links[values["rel"] or ""] = href

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav" and self.in_sidebar:
            self.in_sidebar = False


def parse_navigation(source: str) -> NavigationParser:
    parser = NavigationParser()
    parser.feed(source)
    return parser


def url_path(url: str | None) -> str | None:
    if not url:
        return None
    path = urlsplit(url).path
    return path if path.endswith("/") else f"{path}/"


def page_path(public: Path, url: str) -> Path:
    relative = urlsplit(url).path.strip("/")
    return public / relative / "index.html"


def sidebar_markup(source: str) -> str:
    start = source.find('<div id="td-sidebar-menu"')
    end = source.find("</nav>", start)
    return source[start:end + len("</nav>")] if start >= 0 and end >= 0 else ""


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_example(hugo: str, destination: Path) -> subprocess.CompletedProcess[str]:
    return run_hugo_process(
        [
            hugo,
            "--source",
            str(FIXTURE),
            "--destination",
            str(destination),
            *fixture_config_args(),
            "--logLevel",
            "warn",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def check_math(public: Path) -> list[str]:
    errors: list[str] = []
    hook_path = ROOT / "layouts/_markup/render-passthrough.html"
    require(hook_path.exists(), "math passthrough render hook is missing", errors)
    if hook_path.exists():
        hook = hook_path.read_text()
        require(
            'partial "scripts/math.html" .' in hook,
            "math passthrough hook does not reuse scripts/math.html",
            errors,
        )

    math_path = public / "fixtures/math-passthrough/index.html"
    math_markdown_path = public / "fixtures/math-passthrough/index.md"
    plain_path = public / "fixtures/content-primitives/index.html"
    print_path = public / "_print/fixtures/index.html"
    for path in (math_path, math_markdown_path, plain_path, print_path):
        require(path.exists(), f"fixture output is missing: {path.relative_to(public)}", errors)
    if not all(path.exists() for path in (math_path, math_markdown_path, plain_path, print_path)):
        return errors

    math_page = math_path.read_text()
    math_markdown = math_markdown_path.read_text()
    plain_page = plain_path.read_text()
    print_page = print_path.read_text()

    require(math_page.count('class="katex"') >= 5, "math fixture lost rendered KaTeX", errors)
    require('class="katex-display"' in math_page, "math fixture lost block rendering", errors)
    require(
        math_page.count('class="katex-display" tabindex="0"') >= 4,
        "block mathematics is not keyboard-focusable for horizontal scrolling",
        errors,
    )
    require("<math" in math_page and "<annotation" in math_page, "math fixture lacks MathML", errors)
    require("$$" not in math_page, "math fixture leaked literal dollar delimiters", errors)
    require("third_party/katex/katex.min." in math_page, "math page did not load local KaTeX CSS", errors)
    require("third_party/katex/katex.min." not in plain_page, "formula-free page loaded KaTeX CSS", errors)
    renamed_classes = {
        "accent", "base", "fix", "hdashline", "hline", "inner", "newline", "overlay",
        "overline", "root", "rule", "sizing", "smash", "sout", "stretchy", "strut",
        "tag", "thinbox", "underline", "vbox",
    }
    for label, html in (("HTML", math_page), ("Print", print_page)):
        # Inspect the math spans, not prose, code examples, or TeX annotations.
        classes = {token for attr in re.findall(r'<span class="([^"]*)"', html)
                   for token in attr.split()}
        require(not (classes & renamed_classes),
                f"{label} math uses classes absent from vendored KaTeX CSS: {classes & renamed_classes}", errors)
        require({"katex-base", "katex-strut", "katex-sizing"} <= classes,
                f"{label} math lacks compatible base, strut, or sizing classes", errors)
    require('class="katex-display"' in print_page, "print output lost block mathematics", errors)
    require(
        'class="katex-display" tabindex="0"' not in print_page,
        "static print mathematics should not add a keyboard focus stop",
        errors,
    )
    require("$$" not in print_page, "print output leaked literal dollar delimiters", errors)
    require(
        "$$\n\\lim_{n \\to \\infty}\\left(1 + \\frac{1}{n}\\right)^n = e\n$$" in math_markdown,
        "parameter-free eq lost its Markdown TeX fallback",
        errors,
    )
    require("td-book-" not in math_markdown, "parameter-free eq leaked Book markup into Markdown", errors)

    eq = (ROOT / "layouts/_shortcodes/eq.html").read_text()
    require("if not $hasNum" in eq, "eq escape hatch still requires num", errors)
    require('partial "scripts/math.html"' in eq, "eq escape hatch bypasses the shared math renderer", errors)

    styles = (ROOT / "assets/scss/td/_content.scss").read_text()
    print_styles = (ROOT / "assets/scss/td/_print.scss").read_text()
    require(".katex-display" in styles, "theme lacks KaTeX overflow styles", errors)
    require("overflow-x: auto" in styles, "long equations do not scroll within the column", errors)
    require(
        ".katex-display:focus-visible" in styles,
        "focusable display mathematics lacks a visible focus indicator",
        errors,
    )
    require(
        ".row > [class*='col-']" in print_styles
        and re.search(r"^\s*\[class\*=.?col-.?\]\s*\{", print_styles, re.M) is None,
        "print Bootstrap-column reset can still match KaTeX col-align internals",
        errors,
    )
    return errors


def check_pager_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    # The nested-section fixture lives under /fixtures/; /docs/ is the flat
    # component reference and exercises no nesting.
    root_path = public / "fixtures/index.html"
    require(root_path.exists(), "fixtures root fixture is missing", errors)
    if not root_path.exists():
        return errors

    root = parse_navigation(root_path.read_text())
    sequence = root.sidebar_links
    require(len(sequence) >= 10, "fixtures sidebar sequence is unexpectedly short", errors)
    require(sequence[0] == "/fixtures/", "fixtures section index is not first", errors)
    nested = [
        "/fixtures/guides/",
        "/fixtures/guides/first/",
        "/fixtures/guides/opt-out/",
    ]
    require(
        all(item in sequence for item in nested)
        and [sequence.index(item) for item in nested]
        == sorted(sequence.index(item) for item in nested),
        "nested docs pages are not in pre-order tree sequence",
        errors,
    )

    opt_out = "/fixtures/guides/opt-out/"
    for index, url in enumerate(sequence):
        path = page_path(public, url)
        require(path.exists(), f"sidebar destination has no HTML output: {url}", errors)
        if not path.exists():
            continue
        parsed = parse_navigation(path.read_text())
        require(
            parsed.sidebar_links == sequence,
            f"sidebar order changed while rendering {url}",
            errors,
        )
        require(not parsed.has_disabled_pager, f"{url} emitted a disabled pager card", errors)

        if url == opt_out:
            require(not parsed.has_pager, "pager:false page emitted pager cards", errors)
            require(not parsed.pager_links, "pager:false page emitted pager links", errors)
            require(not parsed.head_links, "pager:false page emitted head relations", errors)
            continue

        expected_prev = sequence[index - 1] if index > 0 else None
        expected_next = sequence[index + 1] if index + 1 < len(sequence) else None
        actual_prev = url_path(parsed.pager_links.get("prev"))
        actual_next = url_path(parsed.pager_links.get("next"))
        head_prev = url_path(parsed.head_links.get("prev"))
        head_next = url_path(parsed.head_links.get("next"))
        require(actual_prev == expected_prev, f"{url} prev card is {actual_prev}, expected {expected_prev}", errors)
        require(actual_next == expected_next, f"{url} next card is {actual_next}, expected {expected_next}", errors)
        require(head_prev == expected_prev, f"{url} rel=prev is {head_prev}, expected {expected_prev}", errors)
        require(head_next == expected_next, f"{url} rel=next is {head_next}, expected {expected_next}", errors)
        require(
            parsed.has_pager == bool(expected_prev or expected_next),
            f"{url} pager container presence is wrong",
            errors,
        )

    first_nested = (public / "fixtures/guides/first/index.html").read_text()
    require("Nested guides" in first_nested, "pager card lost its optional parent section", errors)

    # Blog order is weighted pages first, then reverse date, walked as a tree.
    # The immersive example remains an ordinary blog page in that sequence.
    blog_cases = {
        "blog/index.html": {"prev": None, "next": None, "head_next": "/blog/page/2/"},
        "blog/typography/index.html": {"prev": "/blog/", "next": "/blog/oink/"},
        "blog/oink/index.html": {"prev": None, "next": None},
        "blog/oink/immersive-reading/index.html": {
            "prev": "/blog/oink/",
            "next": "/blog/oink/oink-announcement/",
        },
        "blog/older/index.html": {
            "prev": "/blog/oink/oink-implementation-diary/",
            "next": "/blog/legacy-byline/",
        },
        "blog/legacy-byline/index.html": {"prev": "/blog/older/", "next": "/blog/release/"},
    }
    for relative, expected in blog_cases.items():
        path = public / relative
        require(path.exists(), f"blog pager fixture is missing: {relative}", errors)
        if not path.exists():
            continue
        parsed = parse_navigation(path.read_text())
        for direction in ("prev", "next"):
            actual = url_path(parsed.pager_links.get(direction))
            head = url_path(parsed.head_links.get(direction))
            require(actual == expected[direction], f"{relative} {direction} sidebar order changed", errors)
            require(head == expected.get("head_" + direction, expected[direction]), f"{relative} head {direction} sidebar order changed", errors)

    print_page = public / "_print/fixtures/index.html"
    require(print_page.exists(), "docs print fixture is missing", errors)
    if print_page.exists():
        source = print_page.read_text()
        for marker in ("td-pager", "data-td-pager-prev", "data-td-pager-next", 'rel="prev"', 'rel="next"'):
            require(marker not in source, f"print output contains pager marker {marker}", errors)
    for relative in (
        "fixtures/guides/first/index.md",
        "fixtures/guides/opt-out/index.md",
    ):
        path = public / relative
        require(path.exists(), f"Markdown pager fixture is missing: {relative}", errors)
        if path.exists():
            source = path.read_text()
            require("td-pager" not in source and "data-td-pager" not in source, f"{relative} contains pager HTML", errors)
    return errors


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def create_theme_site(root: Path) -> None:
    (root / "themes").mkdir(parents=True)
    (root / "themes/oink").symlink_to(ROOT, target_is_directory=True)
    write_file(
        root / "hugo.yaml",
        """baseURL: https://example.org/
title: fixture
theme: oink
defaultContentLanguage: en
disableKinds: [home, RSS, sitemap, taxonomy, term]
outputs:
  page: [HTML]
  section: [HTML]
params:
  ui:
    shell_types: [docs, book, blog]
    docs_section: docs
    sidebar_root_enabled: true
    sidebar_root_menu: false
    sidebar_menu_foldable: true
    pager_types: [docs, book, blog]
""",
    )
    write_file(
        root / "content/docs/_index.md",
        """---
title: Explicit docs
type: docs
cascade:
  type: docs
---
""",
    )


def run_site(hugo: str, source: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run_hugo_process(
        [hugo, "--source", str(source), "--logLevel", "warn", *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def check_explicit_navigation(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-explicit-nav-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config_path = source / "hugo.yaml"
        config_path.write_text(
            config_path.read_text().replace(
                "    sidebar_menu_foldable: true\n",
                "    sidebar_menu_foldable: true\n"
                "    sidebar_menu_compact: true\n"
                "    sidebar_expand_levels: 1\n"
                "    sidebar_item_overflow: ellipsis\n"
                "    sidebar_cache_limit: 1\n",
            )
        )
        for name, weight in (("alpha", 10), ("beta", 20), ("gamma", 30)):
            overrides = (
                "sidebar_menu_foldable: false\nsidebar_item_overflow: wrap\n"
                if name == "alpha" else ""
            )
            write_file(
                source / f"content/docs/{name}.md",
                f"---\ntitle: {name.title()}\nweight: {weight}\n{overrides}---\n\n{name}\n",
            )
        write_file(
            source / "content/docs/ghost.md",
            """---
title: Link-only ghost
manual_link: /release/
build:
  render: link
  list: local
---
""",
        )
        data = {
            "sections": [
                {"page": "/docs/gamma", "url": "/docs/gamma/", "children": []},
                {
                    "page": "/docs/beta",
                    "url": "/docs/beta/",
                    "children": [
                        {"page": "/docs/ghost", "url": "/release/", "children": []},
                        {"page": "/docs/alpha", "url": "/docs/alpha/", "children": []},
                    ],
                },
            ],
            "active_path_by_url": {},
        }
        write_file(source / "data/docs_nav.json", json.dumps(data))
        result = run_site(hugo, source)
        if result.returncode != 0:
            errors.append(f"explicit docs_nav fixture failed: {result.stdout}{result.stderr}")
            return errors

        expected = ["/docs/", "/docs/gamma/", "/docs/beta/", "/docs/alpha/"]
        root_page = source / "public/docs/index.html"
        require(root_page.exists(), "explicit docs root output is missing", errors)
        if root_page.exists():
            parsed = parse_navigation(root_page.read_text())
            require(
                parsed.sidebar_links == ["/docs/", "/docs/gamma/", "/docs/beta/", "/release/", "/docs/alpha/"],
                "explicit sidebar no longer follows docs_nav.json",
                errors,
            )
        alpha_sidebar = sidebar_markup((source / "public/docs/alpha/index.html").read_text())
        gamma_sidebar = sidebar_markup((source / "public/docs/gamma/index.html").read_text())
        for name, markup in (("alpha", alpha_sidebar), ("gamma", gamma_sidebar)):
            require(markup and "data-td-sidebar-hydrate-active" in markup and "d-none" not in markup,
                    f"cached docs_nav sidebar for {name} is not visible before JavaScript", errors)
        require("data-td-shell-tree-toggle" not in alpha_sidebar
                and 'href="/docs/beta/" title=' not in alpha_sidebar,
                "docs_nav ignored the page foldable/wrap overrides", errors)
        require("data-td-shell-tree-toggle" in gamma_sidebar
                and 'href="/docs/beta/" title="Beta"' in gamma_sidebar,
                "docs_nav default foldable/ellipsis variant was polluted by another page", errors)
        for index, url in enumerate(expected):
            path = page_path(source / "public", url)
            require(path.exists(), f"explicit navigation output is missing: {url}", errors)
            if not path.exists():
                continue
            parsed = parse_navigation(path.read_text())
            expected_prev = expected[index - 1] if index else None
            expected_next = expected[index + 1] if index + 1 < len(expected) else None
            require(url_path(parsed.pager_links.get("prev")) == expected_prev, f"explicit {url} prev is wrong", errors)
            require(url_path(parsed.pager_links.get("next")) == expected_next, f"explicit {url} next is wrong", errors)
        require(not (source / "public/docs/ghost/index.html").exists(), "link-only ghost unexpectedly rendered", errors)
        for url in expected:
            page = page_path(source / "public", url)
            if page.exists():
                parsed = parse_navigation(page.read_text())
                require(
                    "/release/" not in map(url_path, parsed.pager_links.values()),
                    f"explicit navigation points at link-only ghost from {url}",
                    errors,
                )
    return errors


def check_cached_content_navigation(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-cached-content-nav-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config_path = source / "hugo.yaml"
        config_path.write_text(
            config_path.read_text().replace(
                "    sidebar_menu_foldable: true\n",
                "    sidebar_menu_foldable: true\n"
                "    sidebar_cache_limit: 1\n",
            )
        )
        write_file(
            source / "content/book/_index.md",
            "---\ntitle: Book\ntype: book\ncascade:\n  type: book\n"
            "  sidebar_menu_compact: true\n  sidebar_menu_foldable: true\n"
            "  sidebar_expand_levels: 1\n  sidebar_item_overflow: ellipsis\n"
            "  sidebar_headings: false\n---\n",
        )
        write_file(
            source / "content/book/part/_index.md",
            "---\ntitle: Part\nweight: 10\n---\n",
        )
        write_file(
            source / "content/book/part/expanded.md",
            "---\ntitle: Expanded\nweight: 10\nsidebar_menu_compact: false\n"
            "sidebar_menu_foldable: false\nsidebar_expand_levels: 0\n"
            "sidebar_item_overflow: wrap\n---\n\nExpanded.\n",
        )
        write_file(
            source / "content/book/part/compact.md",
            "---\ntitle: Compact\nweight: 20\n---\n\nCompact.\n",
        )
        write_file(
            source / "content/book/part/headings.md",
            "---\ntitle: Headings\nweight: 30\nsidebar_headings: 3\n---\n\n"
            "## First heading {#first-heading}\n\n### Nested heading {#nested-heading}\n",
        )

        result = run_site(hugo, source)
        if result.returncode != 0:
            return [f"cached content sidebar fixture failed: {result.stdout}{result.stderr}"]

        expanded = sidebar_markup(
            (source / "public/book/part/expanded/index.html").read_text()
        )
        compact = sidebar_markup(
            (source / "public/book/part/compact/index.html").read_text()
        )
        headings = sidebar_markup(
            (source / "public/book/part/headings/index.html").read_text()
        )
        for name, markup in (("expanded", expanded), ("compact", compact)):
            require(markup and "data-td-sidebar-hydrate-active" in markup and "d-none" not in markup,
                    f"cached content sidebar for {name} is not visible before JavaScript", errors)
            require('href="/book/"' in markup and 'href="/book/part/"' in markup,
                    f"cached content sidebar for {name} has no usable neutral links", errors)
        require("data-td-shell-tree-toggle" not in expanded
                and "td-shell-tree__item--hidden" not in expanded
                and 'href="/book/part/" title=' not in expanded,
                "content tree ignored compact/foldable/expand/overflow overrides", errors)
        require("data-td-shell-tree-toggle" in compact
                and "td-shell-tree__item--hidden" not in compact
                and 'href="/book/part/" title="Part"' in compact,
                "content-tree default cache variant was polluted by another page", errors)
        require("data-td-sidebar-hydrate-active" not in headings
                and "data-td-book-headings" in headings
                and 'href="#first-heading"' in headings
                and 'href="#nested-heading"' in headings,
                "Book sidebar headings were cached or omitted instead of rendering per page", errors)
    return errors


def check_foldable_content_navigation(hugo: str) -> list[str]:
    """Compact filtering must not permanently hide a disclosure's leaves."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-foldable-content-nav-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config_path = source / "hugo.yaml"
        config = config_path.read_text().replace(
            "    sidebar_menu_foldable: true\n",
            "    sidebar_menu_foldable: true\n"
            "    sidebar_menu_compact: true\n"
            "    sidebar_expand_levels: 1\n",
        )
        for kind in ("docs", "book"):
            pages = {
                "_index": f"title: {kind.title()}\ntype: {kind}\ncascade:\n  type: {kind}",
                "about/_index": "title: About",
                "about/compare/_index": "title: Compare",
                "about/compare/cost": "title: Cost",
                "about/compare/impact": "title: Impact",
                "about/compare/private": "title: Private\ntoc_hide: true",
                "other/_index": "title: Other",
                "other/deep/_index": "title: Deep",
                "other/deep/tip": "title: Tip",
                "static": "title: Static compact\nsidebar_menu_foldable: false",
            }
            for path, frontmatter in pages.items():
                write_file(source / f"content/{kind}/{path}.md", f"---\n{frontmatter}\n---\n")

        for cache_limit in (1, 10000):
            config_path.write_text(config + f"    sidebar_cache_limit: {cache_limit}\n")
            result = run_site(hugo, source)
            if result.returncode:
                return errors + [f"foldable sidebar fixture failed: {result.stdout}{result.stderr}"]
            for kind in ("docs", "book"):
                for page in ("", "about/compare/", "about/compare/cost/"):
                    label = f"{kind}/{page} cache_limit={cache_limit}"
                    markup = sidebar_markup((source / f"public/{kind}/{page}index.html").read_text())
                    require(bool(markup), f"{label}: missing sidebar", errors)
                    require(("data-td-sidebar-hydrate-active" in markup) == (cache_limit == 1),
                            f"{label}: unexpected cache path", errors)
                    require("td-shell-tree__item--hidden" not in markup,
                            f"{label}: compact filtering permanently hides foldable children", errors)
                    for leaf in ("about/compare/cost/", "about/compare/impact/", "other/deep/tip/"):
                        require(f'href="/{kind}/{leaf}"' in markup,
                                f"{label}: missing reachable leaf {leaf}", errors)
                    require(f'href="/{kind}/about/compare/private/"' not in markup,
                            f"{label}: toc_hide leaf leaked into navigation", errors)
                static = sidebar_markup((source / f"public/{kind}/static/index.html").read_text())
                require("data-td-shell-tree-toggle" not in static
                        and "td-shell-tree__item--hidden" in static,
                        f"{kind} cache_limit={cache_limit}: non-foldable compact filtering changed", errors)
    return errors


def check_home_root_navigation(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-home-root-") as temp:
        source = Path(temp)
        (source / "themes").mkdir(parents=True)
        (source / "themes/oink").symlink_to(ROOT, target_is_directory=True)
        write_file(
            source / "hugo.yaml",
            """baseURL: https://example.org/
title: Root manual fixture
theme: oink
defaultContentLanguage: en
disableKinds: [RSS, sitemap, taxonomy, term]
outputs:
  home: [HTML]
  page: [HTML]
  section: [HTML]
params:
  offline_search: false
  ui:
    shell_types: [docs, blog]
    docs_section: docs
    docs_sidebar_root: home
    sidebar_root_enabled: true
    sidebar_root_menu: false
    sidebar_menu_foldable: true
    pager_types: [docs, blog]
""",
        )
        write_file(
            source / "content/_index.md",
            "---\ntitle: Root manual\ntype: home\ncascade:\n  type: docs\n---\n",
        )
        write_file(
            source / "content/docs/_index.md",
            "---\ntitle: Docs overview\ntype: docs\ntoc_root: true\nweight: 1\n---\n",
        )
        for name, weight in (("alpha", 10), ("beta", 20)):
            write_file(
                source / f"content/{name}.md",
                f"---\ntitle: {name.title()}\nweight: {weight}\n---\n\n{name}\n",
            )
        write_file(
            source / "content/blog/_index.md",
            "---\ntitle: Blog\ntype: blog\ntoc_root: true\nweight: 30\ncascade:\n  type: blog\n---\n",
        )
        write_file(source / "content/blog/post.md", "---\ntitle: Post\ndate: 2026-08-14\n---\n")
        # A docs_nav file in the same repository must not override an explicit
        # home-root manual: it belongs to the section-root mode only.
        write_file(
            source / "data/docs_nav.json",
            json.dumps(
                {
                    "sections": [
                        {"page": "/docs", "url": "/docs/", "children": []}
                    ],
                    "active_path_by_url": {},
                }
            ),
        )
        result = run_site(hugo, source)
        if result.returncode != 0:
            errors.append(f"home-root docs fixture failed: {result.stdout}{result.stderr}")
            return errors

        expected_tree = ["/", "/alpha/", "/beta/"]
        for name, prev, next_ in (
            ("alpha", None, "/beta/"),
            ("beta", "/alpha/", None),
        ):
            output = source / f"public/{name}/index.html"
            require(output.exists(), f"home-root output is missing: {name}", errors)
            if not output.exists():
                continue
            parsed = parse_navigation(output.read_text())
            require(
                parsed.sidebar_links == expected_tree,
                f"home-root sidebar for {name} is {parsed.sidebar_links}",
                errors,
            )
            require(
                url_path(parsed.pager_links.get("prev")) == prev,
                f"home-root {name} prev is wrong",
                errors,
            )
            require(
                url_path(parsed.pager_links.get("next")) == next_,
                f"home-root {name} next is wrong",
                errors,
            )
            require("/docs/" not in parsed.sidebar_links, "docs overview leaked into home tree", errors)
            require("/blog/" not in parsed.sidebar_links, "blog root leaked into home tree", errors)
    return errors


def check_invalid_pager_config(hugo: str) -> list[str]:
    errors: list[str] = []
    cases = (
        ("bad-type", "", "    pager_types: [docs, archive]", "invalid params.ui.pager_types value"),
        ("scalar-types", "", "    pager_types: docs", "params.ui.pager_types must be an array"),
        ("page-string", 'pager: "false"\n', None, "front matter pager must be a boolean"),
        ("bad-docs-root", "", "    docs_sidebar_root: archive\n    pager_types: [docs, book, blog]", "params.ui.docs_sidebar_root must be home or section"),
        ("scalar-docs-root", "", "    docs_sidebar_root: true\n    pager_types: [docs, book, blog]", "params.ui.docs_sidebar_root must be a string"),
    )
    for name, front_matter, config_extra, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-components-pager-{name}-") as temp:
            source = Path(temp)
            create_theme_site(source)
            if config_extra is not None:
                config_path = source / "hugo.yaml"
                config = config_path.read_text()
                config = config.replace(
                    "    pager_types: [docs, book, blog]",
                    config_extra,
                )
                config_path.write_text(config)
            write_file(
                source / "content/docs/page.md",
                f"---\ntitle: Invalid pager\n{front_matter}---\n\nInvalid fixture.\n",
            )
            result = run_site(hugo, source)
            output = result.stdout + result.stderr
            require(expected in output, f"invalid pager case {name} did not report {expected!r}", errors)


            require(result.returncode == 0,
                    f"invalid pager case {name} stopped the build instead of warning", errors)
            require((source / "public/docs/page/index.html").is_file(),
                    f"invalid pager case {name} emitted no safe page output", errors)
    return errors


def check_explicit_shell_overrides(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-shell-overrides-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config = source / 'hugo.yaml'
        config.write_text(config.read_text().replace(
            'taxonomy, term', ''
        ).replace('params:\n', 'params:\n  page_width: wide\n  offline_search: true\n')
            .replace('    docs_section: docs', '    docs_section: docs\n    quick_links: []')
            + 'menus:\n  main:\n    - {identifier: docs, name: Docs, pageRef: /docs}\n')
        write_file(source / 'content/docs/default.md', '---\ntitle: Default\n---\n')
        write_file(source / 'content/docs/invalid.md', '---\ntitle: Invalid\npage_width: false\n---\n')
        write_file(source / 'content/docs/nested/_index.md',
                   '---\ntitle: Nested\nsidebar_root_for: self\nsidebar_root_link_self: 0\n---\n')
        write_file(source / 'content/docs/nested/page.md', '---\ntitle: Nested page\n---\n')
        write_file(source / 'content/tags/_index.md', '---\ntitle: Tags\npage_width: wrong\n---\n')
        write_file(source / 'content/tags/test/_index.md', '---\ntitle: Test\npage_width: wrong\n---\n')
        result = run_site(hugo, source)
        if result.returncode:
            return [f'shell override fixture failed: {result.stdout}{result.stderr}']
        public = source / 'public'
        default = (public / 'docs/default/index.html').read_text()
        require('td-shell-layout--w-wide' in default, 'site page width no longer inherits', errors)
        for relative in ('docs/invalid/index.html', 'tags/index.html', 'tags/test/index.html'):
            html = (public / relative).read_text()
            require('td-shell-layout--w-normal' in html,
                    f'{relative} bypassed page-width validation or ignored false', errors)
        manifest = re.search(r'id="td-action-manifest">(.*?)</script>', default, re.S)
        require(manifest is not None and json.loads(manifest[1])['quickLinks'] == [],
                'an explicit empty quick_links list restored default links', errors)
        nested = parse_navigation((public / 'docs/nested/page/index.html').read_text())
        require('/docs/nested/' in nested.sidebar_links and '/docs/' not in nested.sidebar_links,
                'invalid sidebar_root_link_self did not fall back to true', errors)
    return errors


def check_print_relative_links(hugo: str) -> list[str]:
    """A relocated Print body resolves links from its source HTML URL."""
    errors: list[str] = []

    class QuotedAttributes(HTMLParser):
        def __init__(self, source: str) -> None:
            super().__init__()
            self.links: dict[str, dict[str, str | None]] = {}
            self.feed(source)

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == "a" and values.get("data-test-relative-link"):
                self.links[values["data-test-relative-link"]] = values

    def check_quoted_attributes(source: str, context: str, href: str) -> None:
        links = QuotedAttributes(source).links
        titles = {
            "single": "Literal href='../two/'",
            "double": 'Literal href="../two/"',
            "bare": "Literal HREF = ../two/ > text",
        }
        require(set(links) == set(titles), f"{context} lost quoted-attribute probes", errors)
        for key, title in titles.items():
            require(links.get(key) == {
                "data-test-relative-link": key, "title": title, "href": href,
            }, f"{context} rewrote title text or damaged attributes for {key}: {links.get(key)}", errors)

    with tempfile.TemporaryDirectory(prefix="oink-print-links-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config = source / "hugo.yaml"
        settings = config.read_text().replace(
            "page: [HTML]", "page: [HTML, PRINT]"
        ).replace("section: [HTML]", "section: [HTML, PRINT]") + """languages:
  en: {locale: en-US}
  zh: {locale: zh-CN}
markup:
  goldmark:
    renderer: {unsafe: true}
"""
        body = """## Topic

[sibling](../two/?mode=print&view=full#topic)
[parent](../)
[asset](files/report%20one.txt)
[current-query](?mode=print&view=full#topic)
[local](#topic)
[root](/fixed/)
[external](https://elsewhere.example/path/)
[network](//cdn.example/path/)
[email](mailto:reader@example.org)

<a href='../two/'>single-quoted</a>
<a href=../two/>unquoted</a>
<a title="one > two" href="../">raw-parent</a>
<a title="Literal href='../decoy/'" href="../two/">quoted-attribute</a>
<a data-test-relative-link="single" title="Literal href='../two/'" href='../two/'>identical-single-quoted</a>
<a data-test-relative-link="double" title='Literal href="../two/"' href="../two/">identical-double-quoted</a>
<a data-test-relative-link="bare" title="Literal HREF = ../two/ > text" HREF = ../two/>identical-unquoted</a>
<a href="#topic">raw-local</a>

`<a href="../code/">literal</a>`
"""
        for kind in ("docs", "book", "blog", "expo"):
            for suffix in (".md", ".zh.md"):
                write_file(source / f"content/{kind}/_index{suffix}",
                           f"---\ntitle: {kind}\ntype: {kind}\ncascade:\n  type: {kind}\n---\n")
                write_file(source / f"content/{kind}/part/_index{suffix}",
                           "---\ntitle: Part\n---\n")
                write_file(source / f"content/{kind}/part/one{suffix}",
                           "---\ntitle: One\n---\n" + body)
                write_file(source / f"content/{kind}/part/two{suffix}",
                           "---\ntitle: Two\n---\n\n## Topic\n")
        for base_path in ("/", "/preview/"):
            config.write_text(settings.replace("https://example.org/", f"https://example.org{base_path}"))
            result = run_site(hugo, source)
            if result.returncode:
                return [f"Print relative-link fixture failed: {result.stdout}{result.stderr}"]
            for language in ("", "zh/"):
                for kind in ("docs", "book", "blog", "expo"):
                    page_url = f"{base_path}{language}{kind}/part/one/"
                    sibling_url = f"{base_path}{language}{kind}/part/two/"
                    expected = {
                        "sibling": sibling_url + "?mode=print&amp;view=full#topic",
                        # Hugo's embedded hook resolves this source reference
                        # before Print sees it. Preserve that canonical route.
                        "parent": f"{base_path}{language}{kind}/",
                        "raw-parent": f"{base_path}{language}{kind}/part/",
                        "asset": page_url + "files/report%20one.txt",
                        "current-query": page_url + "?mode=print&amp;view=full#topic",
                        "root": "/fixed/",
                        "external": "https://elsewhere.example/path/",
                        "network": "//cdn.example/path/",
                        "email": "mailto:reader@example.org",
                        "single-quoted": sibling_url,
                        "unquoted": sibling_url,
                        "quoted-attribute": sibling_url,
                    }
                    for tail in ("", "part/", "part/one/"):
                        relative = f"{language}_print/{kind}/{tail}index.html"
                        output = (source / "public" / relative).read_text()
                        check_quoted_attributes(output, f"{base_path} {relative}", sibling_url)
                        for label, href in expected.items():
                            require(f'href="{href}">{label}</a>' in output,
                                    f"{base_path} {relative} misresolved {label}", errors)
                        require('&lt;a href=&quot;../code/&quot;&gt;literal&lt;/a&gt;' in output,
                                f"{relative} rewrote an escaped code example", errors)
                        require('title="Literal href=\'../decoy/\'"' in output,
                                f"{relative} mistook quoted text for a link attribute", errors)
                        local = re.search(r'href=[\"\']#([^\"\']+)[\"\']>raw-local</a>', output)
                        require(bool(local) and f'id="{local[1]}"' in output,
                                f"{relative} broke the local heading link", errors)
                    regular = (source / "public" / language / kind / "part/one/index.html").read_text()
                    check_quoted_attributes(regular, f"{base_path} {language}{kind} HTML", "../two/")
                    require('href="../two/?mode=print&amp;view=full#topic">sibling</a>' in regular,
                            f"{base_path} {language}{kind} changed ordinary HTML links", errors)
    return errors


def check_print_encoded_fragments(hugo: str) -> list[str]:
    """Aggregate links decode fragments once without changing URL ownership."""
    errors: list[str] = []

    class Anchors(HTMLParser):
        def __init__(self, source: str) -> None:
            super().__init__()
            self.ids: set[str] = set()
            self.links: dict[str, str] = {}
            self.href: str | None = None
            self.label = ""
            self.feed(source)

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if values.get("id"):
                self.ids.add(values["id"])
            if tag == "a":
                self.href = values.get("href")
                self.label = ""

        def handle_data(self, data):
            if self.href is not None:
                self.label += data

        def handle_endtag(self, tag):
            if tag == "a" and self.href is not None:
                self.links[self.label] = self.href
                self.href = None

    fragments = {
        "markdown-chinese": "中文标题",
        "encoded-chinese": "中文标题",
        "encoded-ascii": "topic",
        "encoded-explicit": "自定义",
        "literal-plus": "a+b",
        "encoded-plus": "a+b",
        "encoded-once": "encoded%20id",
        "self-path": "中文标题",
        "legacy-local": "legacy",
        "custom-heading": "custom",
        "nested-heading": "nested-topic",
        "nested-chinese": "嵌套中文",
        "nested-plus": "nested+a+b",
        "nested-once": "nested%20id",
    }
    with tempfile.TemporaryDirectory(prefix="oink-print-encoded-fragments-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config = source / "hugo.yaml"
        settings = config.read_text().replace("page: [HTML]", "page: [HTML, PRINT]").replace(
            "section: [HTML]", "section: [HTML, PRINT]"
        ) + """languages:
  en: {locale: en-US}
  zh: {locale: zh-CN}
markup:
  goldmark:
    renderer: {unsafe: true}
"""
        for base in ("/", "/preview/"):
            config.write_text(settings.replace("https://example.org/", f"https://example.org{base}"))
            for kind in ("docs", "book"):
                for suffix, lang in ((".md", ""), (".zh.md", "zh/")):
                    write_file(source / f"content/{kind}/_index{suffix}",
                               f"---\ntitle: {kind}\ntype: {kind}\ncascade:\n  type: {kind}\n---\n")
                    for chapter in ("one", "two"):
                        page_url = f"{base}{lang}{kind}/{chapter}/"
                        body = f"""## 中文标题

[markdown-chinese-{chapter}](#中文标题)
<a href="#%E4%B8%AD%E6%96%87%E6%A0%87%E9%A2%98">encoded-chinese-{chapter}</a>
<a href="#%74opic">encoded-ascii-{chapter}</a>
<a href='#%e8%87%aa%e5%ae%9a%e4%b9%89'>encoded-explicit-{chapter}</a>
<a href="#a+b">literal-plus-{chapter}</a>
<a href=#a%2Bb>encoded-plus-{chapter}</a>
<a href="#encoded%2520id">encoded-once-{chapter}</a>
<a href="{page_url}#%E4%B8%AD%E6%96%87%E6%A0%87%E9%A2%98">self-path-{chapter}</a>
<a href="{page_url}?mode=read#%74opic">queried-{chapter}</a>
<a href="https://elsewhere.example{page_url}#%74opic">external-{chapter}</a>
<a href="#%ZZ">malformed-{chapter}</a>
<a href="#%6cegacy">legacy-local-{chapter}</a>
<a href="#custom">custom-heading-{chapter}</a>
<a href="#nested-topic">nested-heading-{chapter}</a>
<a href="#%E5%B5%8C%E5%A5%97%E4%B8%AD%E6%96%87">nested-chinese-{chapter}</a>
<a href="#nested%2Ba%2Bb">nested-plus-{chapter}</a>
<a href="#nested%2520id">nested-once-{chapter}</a>
<span id="legacy" data-td-print-local></span>
<h2 DATA-TD-PRINT-LOCAL id="custom">Custom heading</h2>
<span id="global-{chapter}" title="data-td-print-local"></span>
<h2 id="global-heading-{chapter}">Authored global heading</h2>

## Topic {{#topic}}
## Explicit {{#自定义}}
## Plus {{id="a+b"}}
## Once {{id="encoded%20id"}}

{{{{< tabs group="nested-heading" >}}}}
{{{{< tab label="Example" value="example" >}}}}
### Nested heading {{#nested-topic}}
### Nested Chinese {{#嵌套中文}}
### Nested plus {{id="nested+a+b"}}
### Nested percent {{id="nested%20id"}}
{{{{< /tab >}}}}
{{{{< /tabs >}}}}
"""
                        write_file(source / f"content/{kind}/{chapter}{suffix}",
                                   f"---\ntitle: {chapter}\n---\n" + body)
            result = run_site(hugo, source)
            if result.returncode:
                return [f"Print encoded-fragment fixture failed: {result.stdout}{result.stderr}"]
            for kind in ("docs", "book"):
                for lang in ("", "zh/"):
                    aggregate = Anchors((source / f"public/{lang}_print/{kind}/index.html").read_text())
                    for chapter in ("one", "two"):
                        page_url = f"{base}{lang}{kind}/{chapter}/"
                        outputs = {
                            "HTML": Anchors((source / f"public/{lang}{kind}/{chapter}/index.html").read_text()),
                            "Print": Anchors((source / f"public/{lang}_print/{kind}/{chapter}/index.html").read_text()),
                            "aggregate": aggregate,
                        }
                        for output, parsed in outputs.items():
                            context = f"{base}{lang}{kind}/{chapter} {output}"
                            require(f"global-{chapter}" in parsed.ids,
                                    f"{context}: renamed an unmarked authored global ID", errors)
                            require(f"global-heading-{chapter}" in parsed.ids,
                                    f"{context}: renamed an unmarked authored global heading", errors)
                            for label, anchor in fragments.items():
                                href = parsed.links.get(f"{label}-{chapter}", "")
                                target = unquote(urlsplit(href).fragment)
                                require(target in parsed.ids, f"{context}: {label} misses {target!r}", errors)
                                if output == "aggregate":
                                    require(href.startswith("#pg-") and target.endswith("--" + anchor),
                                            f"{context}: {label} escaped its source chapter", errors)
                                else:
                                    require(target == anchor, f"{context}: {label} changed ordinary ID", errors)
                            for label, expected in {
                                "queried": page_url + "?mode=read#%74opic",
                                "external": "https://elsewhere.example" + page_url + "#%74opic",
                                "malformed": "#%ZZ",
                            }.items():
                                require(parsed.links.get(f"{label}-{chapter}") == expected,
                                        f"{context}: rewrote {label} URL", errors)
    return errors


def check_print_math_and_heading(hugo: str) -> list[str]:
    """Print must own its math flags even when formulas occur only in children."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-print-math-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config = source / "hugo.yaml"
        config.write_text(config.read_text().replace(
            'page: [HTML]', 'page: [HTML, PRINT]'
        ).replace('section: [HTML]', 'section: [HTML, PRINT]')
            + 'languages:\n  en: {locale: en-US}\n  zh: {locale: zh-CN}\n')
        for shell in ('docs', 'blog', 'expo', 'plain'):
            for suffix in ('.md', '.zh.md'):
                kind = 'docs' if shell == 'plain' else shell
                write_file(source / f'content/{shell}/_index{suffix}',
                           f'---\ntitle: {shell}\ntype: {kind}\ncascade:\n  type: {kind}\n---\n')
                body = 'No formula.' if shell == 'plain' else '{{< eq >}}E=mc^2{{< /eq >}}'
                write_file(source / f'content/{shell}/part/_index{suffix}',
                           '---\ntitle: Part\n---\n')
                write_file(source / f'content/{shell}/part/page{suffix}',
                           f'---\ntitle: Page\ndescription: Lead exactly once.\n---\n\n{body}\n')
        result = run_site(hugo, source)
        if result.returncode:
            return [f'Print math fixture failed: {result.stdout}{result.stderr}']
        for language in ('', 'zh/'):
            for shell in ('docs', 'blog', 'expo', 'plain'):
                for tail in ('', 'part/', 'part/page/'):
                    relative = f'{language}_print/{shell}/{tail}index.html'
                    html = (source / 'public' / relative).read_text()
                    has_math = shell != 'plain'
                    require(('third_party/katex/katex.min.' in html) == has_math,
                            f'{relative} selected the wrong KaTeX styles', errors)
                    require(('class="katex-display"' in html) == has_math,
                            f'{relative} lost or invented a formula', errors)
                    require(html.count('<div class="lead">') == 1,
                            f'{relative} duplicated the page description', errors)
    return errors


def check_unnumbered_math_attributes(hugo: str) -> list[str]:
    """Generic block attributes must not opt a formula into Book numbering."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-math-attributes-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config = source / "hugo.yaml"
        config.write_text(config.read_text().replace(
            "page: [HTML]", "page: [HTML, PRINT, MARKDOWN]"
        ) + "markup:\n  goldmark:\n    extensions:\n      passthrough:\n        enable: true\n        delimiters:\n          block: [['$$', '$$']]\n    parser:\n      attribute:\n        block: true\n")
        page = source / "content/docs/page.md"
        for attrs, warning in (
            ('{.wide data-formula="plain" aria-label="Energy"}', None),
            ('{id="orphan" caption="Ignored caption"}', "id/caption attributes require num"),
            ('{num="" caption="Ignored caption"}', "num must not be empty"),
            ('{num="!" caption="Ignored caption"}', "num must match"),
        ):
            write_file(page, f"---\ntitle: Formula\n---\n\n$$\nE=mc^2\n$$\n{attrs}\n")
            result = run_site(hugo, source)
            output = result.stdout + result.stderr
            require(result.returncode == 0, f"unnumbered math failed: {output}", errors)
            require((warning in output) if warning else (not theme_warnings(output)),
                    f"unexpected unnumbered math diagnostics: {output}", errors)
            if result.returncode:
                continue
            for relative in ('docs/page/index.html', '_print/docs/page/index.html'):
                html = (source / "public" / relative).read_text()
                require('class="katex-display"' in html and 'td-book-figure--eq' not in html
                        and 'id="eq-"' not in html and 'Ignored caption' not in html,
                        f"{relative} invented a numbered equation", errors)
            markdown = (source / "public/docs/page/index.md").read_text()
            require('E=mc^2' in markdown and 'Equation ' not in markdown,
                    "unnumbered Markdown invented an equation label", errors)
    return errors


def check_invalid_eq_escape(hugo: str) -> list[str]:
    errors: list[str] = []
    cases = (
        ("empty", "{{< eq >}}{{< /eq >}}", "requires TeX content"),
        ("caption-without-num", '{{< eq caption="ambiguous" >}}x{{< /eq >}}', 'parameter "caption" requires num'),
        ("id-without-num", '{{< eq id="equation" >}}x{{< /eq >}}', 'parameter "id" requires num'),
        ("class-without-num", '{{< eq class="wide" >}}x{{< /eq >}}', 'parameter "class" requires num'),
        ("positional", '{{< eq "x" >}}x{{< /eq >}}', "accepts named parameters only"),
    )
    for name, body, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-components-eq-{name}-") as temp:
            source = Path(temp)
            create_theme_site(source)
            write_file(
                source / "content/docs/page.md",
                f"---\ntitle: Invalid eq escape\n---\n\n{body}\n",
            )
            result = run_site(hugo, source)
            output = result.stdout + result.stderr
            require(result.returncode == 0,
                    f"invalid eq escape case {name} stopped the ordinary build", errors)
            require(expected in output, f"invalid eq escape case {name} did not report {expected!r}", errors)
            require((source / "public/docs/page/index.html").is_file(),
                    f"invalid eq escape case {name} emitted no safe page output", errors)
    return errors


def check_rss_pager_output(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-pager-rss-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config_path = source / "hugo.yaml"
        config = config_path.read_text()
        config = config.replace(
            "disableKinds: [home, RSS, sitemap, taxonomy, term]",
            "disableKinds: [home, sitemap, taxonomy, term]",
        ).replace(
            "outputs:\n  page: [HTML]\n  section: [HTML]",
            "outputs:\n  page: [RSS]\n  section: [HTML]",
        )
        config_path.write_text(config)
        write_file(source / "content/docs/one.md", "---\ntitle: One\nweight: 1\n---\n")
        write_file(source / "content/docs/two.md", "---\ntitle: Two\nweight: 2\n---\n")
        write_file(
            source / "layouts/docs/single.rss.xml",
            '{{- .Store.Set "tdOutputFormat" "rss" -}}<fixture>{{ partial "pager.html" . }}</fixture>\n',
        )
        result = run_site(hugo, source)
        if result.returncode != 0:
            errors.append(f"RSS pager fixture failed: {result.stdout}{result.stderr}")
            return errors
        outputs = list((source / "public/docs").glob("*/index.xml"))
        require(len(outputs) == 2, "RSS pager fixture did not emit both pages", errors)
        for path in outputs:
            content = path.read_text()
            require("td-pager" not in content and "data-td-pager" not in content, f"RSS output contains pager HTML: {path}", errors)
    return errors


def check_pager_sources() -> list[str]:
    errors: list[str] = []
    state = (ROOT / "layouts/_partials/pager-state.html").read_text()
    pager = (ROOT / "layouts/_partials/pager.html").read_text()
    head = (ROOT / "layouts/_partials/head.html").read_text()
    styles = (ROOT / "assets/scss/td/_pager.scss").read_text()
    page_end = (ROOT / "layouts/_partials/page-end.html").read_text()
    nav_flatten = (ROOT / "layouts/_partials/shell/nav-flatten-section.html").read_text()
    nav_children = (ROOT / "layouts/_partials/shell/nav-children.html").read_text()
    require('partialCached "shell/nav-flatten.html"' in state, "pager does not cache its flattened tree", errors)
    # Child selection lives in one shared partial so the reading chain and
    # the navigation JSON cannot order blogs differently from the sidebar.
    require(
        'partial "shell/nav-children.html"' in nav_flatten
        and 'partial "shell/blog-pages.html"' in nav_children,
        "blog pager no longer shares the rendered sidebar order",
        errors,
    )
    require("data-td-pager-prev" in pager and "data-td-pager-next" in pager, "keyboard pager hooks are missing", errors)
    require("disabled" not in pager, "pager still renders disabled controls", errors)
    require('rel="prev"' in head and 'rel="next"' in head, "head pager relations are missing", errors)
    require(
        head.count('href="{{ .RelPermalink }}"') >= 2,
        "head pager relations are not same-origin relative links",
        errors,
    )
    require(
        page_end.index('partial "feedback.html"')
        < page_end.index('partial "page-annotation.html"')
        < page_end.index('partial "pager.html"')
        < page_end.index('partial "comments.html"'),
        "page-end order is not feedback, annotation, pager, comments",
        errors,
    )
    require("&__link--prev {\n    margin-inline-end: auto;" in styles
            and "&__link--next {\n    margin-inline-start: auto;" in styles,
            "a single-direction pager does not keep its own edge", errors)
    require("td-pager__summary" not in pager and "td-pager__title" in pager,
            "pager renders more than the linked title", errors)
    for marker in (
        "[dir='rtl']",
        "@media (prefers-reduced-motion: reduce)",
        "@media (forced-colors: active)",
        "@media print",
    ):
        require(marker in styles, f"pager styles lack {marker}", errors)
    return errors


def check_group_only_sections(hugo: str) -> list[str]:
    """Both navigation authorities keep group children without dead destinations."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-group-sections-") as temp:
        source = Path(temp)
        write_file(source / "hugo.yaml", f"""baseURL: https://example.org/sub/
title: Groups
theme: {ROOT.name}
themesDir: {ROOT.parent}
defaultContentLanguage: en
languages:
  en:
    locale: en-US
  zh:
    locale: zh-CN
outputs:
  home: [HTML, NAVJSON]
  section: [HTML, PRINT, MARKDOWN]
params:
  offline_search: true
  ui:
    sidebar_menu_compact: false
    sidebar_menu_foldable: true
    sidebar_root_menu: true
""")
        pages = {
            "_index": "title: Docs\ntype: docs\ncascade:\n  type: docs",
            "before": "title: Before\nweight: 1",
            "group/_index": "title: Group only\nweight: 2\nsidebar_divider: true\nbuild:\n  render: never",
            "group/a": "title: Child A\nweight: 1",
            "group/b": "title: Child B\nweight: 2",
            "after": "title: After\nweight: 3",
            "divider": "title: Leaf divider\nweight: 4\nsidebar_divider: true\nbuild:\n  render: never",
        }
        for name, frontmatter in pages.items():
            for suffix in (".md", ".zh.md"):
                write_file(source / "content/docs" / (name + suffix),
                           f"---\n{frontmatter}\n---\n\nBody {name}.\n"
                           + ("\n## Unpublished group heading\n" if name == "group/_index" else ""))
        for explicit in (False, True):
            if explicit:
                def node(name, children=None):
                    return {"page": "/docs/" + name, "url": "/docs/" + name + "/",
                            "children": children or []}
                write_file(source / "data/docs_nav.json", json.dumps({
                    "sections": [node("before"), node("group", [node("group/a"), node("group/b")]),
                                 node("after"), node("divider")],
                    "active_path_by_url": {"/docs/group/a/": ["/docs/group/", "/docs/group/a/"]},
                }))
            result = run_site(hugo, source)
            if result.returncode:
                return [f"group fixture ({explicit=}) failed: {result.stdout}{result.stderr}"]
            public = source / "public"
            for language in ("", "zh/"):
                prefix = "/sub/" + language
                html = (public / language / "docs/group/a/index.html").read_text()
                sidebar = sidebar_markup(html)
                require('td-shell-tree__group' in sidebar and 'Group only' in sidebar,
                        f"{language} {explicit=} lost the non-link group", errors)
                require(f'href="{prefix}docs/group/"' not in html and 'href=""' not in html,
                        f"{language} {explicit=} links to an unpublished group", errors)
                parsed = parse_navigation(html)
                require('aria-expanded="true"' in sidebar,
                        f"{language} {explicit=} current group path is not expanded", errors)
                for child in ("a", "b"):
                    require(prefix + "docs/group/" + child + "/" in parsed.sidebar_links,
                            f"{language} {explicit=} drops child {child}", errors)
                require(parsed.pager_links == {"prev": prefix + "docs/before/", "next": prefix + "docs/group/b/"},
                        f"{language} {explicit=} pager does not traverse group children", errors)
                require('td-shell-tree__heading-label' in sidebar and 'Leaf divider' in sidebar,
                        "leaf divider compatibility changed", errors)
                require(not (public / language / "docs/group/index.html").exists(),
                        "never-rendered group acquired an HTML page", errors)
                printable = (public / language / "_print/docs/index.html").read_text()
                require('Body group/a.' in printable and 'Body group/b.' in printable
                        and 'Body group/_index.' not in printable,
                        f"{language} {explicit=} Print loses grouped pages or includes the hidden index", errors)
                nav = json.loads((public / language / "navigation.json").read_text())
                def urls(node):
                    return [node.get("url")] + [url for child in node.get("children", []) for url in urls(child)]
                destinations = [urlsplit(url).path for url in urls(nav["root"]) if url]
                require(prefix + "docs/group/" not in destinations and prefix + "docs/group/a/" in destinations,
                        f"{language} {explicit=} machine navigation loses children or links the group", errors)
            for index in public.glob("offline-search-index.*.json"):
                docs = json.loads(index.read_text())
                require(all(doc.get("ref") and not doc["ref"].endswith("/docs/group/") for doc in docs),
                        "search indexes an unpublished group", errors)
                require(any(doc["ref"].endswith("/docs/group/a/") for doc in docs),
                        "search loses group children", errors)
        # The same group must retain Book TOC/Markdown and aggregate Print.
        for path in (source / "content/docs").glob("_index*.md"):
            path.write_text(path.read_text().replace("type: docs", "type: book")
                            + '\n{{< book-toc depth=3 >}}\n', encoding="utf-8")
        result = run_site(hugo, source)
        if result.returncode:
            return errors + [f"group Book fixture failed: {result.stdout}{result.stderr}"]
        for language in ("", "zh/"):
            prefix = "/sub/" + language
            html = (public / language / "docs/index.html").read_text()
            markdown = (public / language / "docs/index.md").read_text()
            printable = (public / language / "_print/docs/index.html").read_text()
            require('Group only' in html and f'href="{prefix}docs/group/a/"' in html
                    and f'href="{prefix}docs/group/"' not in html,
                    f"{language} Book TOC drops grouped children or links the group", errors)
            require('Group only' in markdown and prefix + "docs/group/a/" in markdown,
                    f"{language} Book Markdown drops grouped children", errors)
            require('Body group/a.' in printable and 'Body group/b.' in printable,
                    f"{language} Book Print drops grouped children", errors)
            require(all('Unpublished group heading' not in output for output in (html, markdown, printable)),
                    f"{language} Book TOC links to unpublished group headings", errors)
    return errors


def check_explicit_navigation_scopes(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-nav-scopes-") as temp:
        source = Path(temp)
        write_file(source / "hugo.yaml", f"""baseURL: https://example.org/sub/
title: Scoped navigation
theme: {ROOT.name}
themesDir: {ROOT.parent}
defaultContentLanguage: en
languages:
  en: {{locale: en-US}}
  zh: {{locale: zh-CN}}
outputs:
  home: [HTML, NAVJSON]
params:
  ui:
    sidebar_cache_limit: 1
    sidebar_menu_compact: false
""")
        for section in ("docs", "book"):
            published = "manual" if section == "book" else section
            for name, weight in (("_index", 0), ("a", 1), ("b", 2)):
                path = published + ("" if name == "_index" else "/" + name)
                for suffix in (".md", ".zh.md"):
                    write_file(source / "content" / section / (name + suffix),
                               f"---\ntitle: {section} {name}\nweight: {weight}\nurl: /{'zh/' if suffix == '.zh.md' else ''}{path}/\n---\n")

        def node(section, name="", children=None):
            published = "manual" if section == "book" else section
            return {"page": "/" + section + ("/" + name if name else ""),
                    "url": "/" + published + ("/" + name if name else "") + "/",
                    "children": children or []}

        for scopes in (("docs",), ("book",), ("docs", "book")):
            write_file(source / "data/docs_nav.json", json.dumps({"sections": [
                node(section, children=[node(section, "b"), node(section, "a")])
                for section in scopes]}))
            result = run_site(hugo, source)
            if result.returncode:
                return errors + [f"scoped navigation {scopes} failed: {result.stdout}{result.stderr}"]
            for language in ("", "zh/"):
                prefix = "/sub/" + language
                public = source / "public" / language
                nav = json.loads((public / "navigation.json").read_text())["root"]["children"]
                for section in ("docs", "book"):
                    published = "manual" if section == "book" else section
                    order = ("b", "a") if section in scopes else ("a", "b")
                    expected = [prefix + published + "/" + name + "/" for name in order]
                    root_url = prefix + published + "/"
                    # Navigation JSON identity drops the deployment and language
                    # prefixes; its URLs keep the published path (shell contract).
                    tree = next((item for item in nav if item["id"] == "/" + published + "/"), None)
                    if tree is None:
                        errors.append(f"{scopes} {language} {section} navigation.json lost its section root")
                        continue
                    require(tree["url"].endswith(root_url),
                            f"{scopes} {language} {section} navigation.json dropped its published path", errors)
                    require([item["id"] for item in tree["children"]] == ["/" + published + "/" + name + "/" for name in order],
                            f"{scopes} {language} {section} navigation.json escaped its scope", errors)
                    for i, url in enumerate([root_url, *expected]):
                        html = page_path(source / "public", url.removeprefix("/sub")).read_text()
                        parsed = parse_navigation(html)
                        require(parsed.sidebar_links == [root_url, *expected],
                                f"{scopes} {language} {section} sidebar order/scope differs", errors)
                        sequence = [root_url, *expected]
                        require(url_path(parsed.pager_links.get("prev")) == (sequence[i-1] if i else None)
                                and url_path(parsed.pager_links.get("next")) == (sequence[i+1] if i+1 < len(sequence) else None),
                                f"{scopes} {language} {url} pager order/scope differs", errors)
        # A nested root selects its branch from the same explicit authority.
        for suffix in (".md", ".zh.md"):
            write_file(source / ("content/book/part/_index" + suffix),
                       "---\ntitle: Part\nsidebar_root_for: self\n---\n")
            for name, weight in (("a", 1), ("b", 2)):
                write_file(source / ("content/book/part/" + name + suffix),
                           f"---\ntitle: Part {name}\nweight: {weight}\n---\n")
        write_file(source / "data/docs_nav.json", json.dumps({"sections": [node("book", children=[
            node("book", "a"), node("book", "part", [node("book", "part/b"), node("book", "part/a")])])]}))
        result = run_site(hugo, source)
        if result.returncode:
            return errors + [f"nested navigation failed: {result.stdout}{result.stderr}"]
        for language in ("", "zh/"):
            prefix = "/sub/" + language + "book/part/"
            parsed = parse_navigation((source / "public" / language / "book/part/b/index.html").read_text())
            require(parsed.sidebar_links == [prefix, prefix + "b/", prefix + "a/"],
                    f"{language} nested root lost explicit order or leaked outer entries", errors)
    return errors


def check_explicit_navigation_state(hugo: str) -> list[str]:
    """Uncached trees resolve current pages even without matching URL hints."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-nav-state-") as temp:
        source = Path(temp)
        create_theme_site(source)
        config = source / "hugo.yaml"
        config.write_text(config.read_text().replace(
            "baseURL: https://example.org/", "baseURL: https://example.org/sub/"
        ) + "    sidebar_cache_limit: 10000\nlanguages:\n  en: {locale: en-US}\n  zh: {locale: zh-CN}\n")
        for suffix in (".md", ".zh.md"):
            write_file(source / ("content/docs/_index" + suffix), "---\ntitle: Docs\n---\n")
            write_file(source / ("content/docs/part/_index" + suffix), "---\ntitle: Part\n---\n")
            write_file(source / ("content/docs/part/page" + suffix),
                       f"---\ntitle: Page\nurl: /{'zh/' if suffix == '.zh.md' else ''}read/\n---\n")
        for url_hint in (None, "/docs/part/page/"):
            child = {"page": "/docs/part/page"}
            if url_hint is not None:
                child["url"] = url_hint
            write_file(source / "data/docs_nav.json", json.dumps({"sections": [
                {"page": "/docs/part", "children": [child]}
            ]}))
            result = run_site(hugo, source)
            if result.returncode:
                return errors + [f"navigation state fixture failed: {result.stdout}{result.stderr}"]
            for language in ("", "zh/"):
                parsed = parse_navigation((source / "public" / language / "read/index.html").read_text())
                require(parsed.sidebar_current == ["/sub/" + language + "read/"],
                        f"{language} {url_hint=}: resolved current page is not marked", errors)
                require(len(parsed.sidebar_expanded) == 1,
                        f"{language} {url_hint=}: current content ancestor is not expanded", errors)
    return errors


def check_explicit_navigation_boundaries(hugo: str) -> list[str]:
    """Irrelevant explicit data cannot warn in home or non-Docs/Book trees."""
    errors: list[str] = []
    for shell in ("home", "blog", "expo"):
        with tempfile.TemporaryDirectory(prefix=f"oink-nav-boundary-{shell}-") as temp:
            source = Path(temp)
            create_theme_site(source)
            config = source / "hugo.yaml"
            text = config.read_text().replace(
                "disableKinds: [home, RSS, sitemap, taxonomy, term]",
                "disableKinds: [RSS, sitemap, taxonomy, term]"
            ).replace("outputs:\n", "outputs:\n  home: [HTML, NAVJSON]\n")
            if shell == "home":
                text += "    docs_sidebar_root: home\n"
                write_file(source / "content/one.md", "---\ntitle: One\ntype: docs\n---\n")
            else:
                (source / "content/docs/_index.md").unlink()
                write_file(source / f"content/{shell}/_index.md", "---\ntitle: Collection\n---\n")
                write_file(source / f"content/{shell}/page.md", "---\ntitle: Page\n---\n")
            config.write_text(text)
            for sections in ([], [{"page": "/missing-docs"}]):
                write_file(source / "data/docs_nav.json", json.dumps({"sections": sections}))
                result = run_site(hugo, source)
                require(result.returncode == 0,
                        f"{shell} consumed irrelevant docs_nav data: {result.stdout}{result.stderr}", errors)
                require(not theme_warnings(result.stdout + result.stderr),
                        f"{shell} emitted an irrelevant navigation warning", errors)
    # Empty data remains invalid when a Docs section actually owns navigation.
    with tempfile.TemporaryDirectory(prefix="oink-nav-empty-docs-") as temp:
        source = Path(temp)
        create_theme_site(source)
        write_file(source / "data/docs_nav.json", '{"sections": []}')
        result = run_site(hugo, source)
        require(result.returncode == 0 and "does not define any Docs navigation sections" in result.stdout + result.stderr,
                "an applicable empty explicit tree must warn and fall back", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path)
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    if args.public is not None:
        errors = check_math(args.public) + check_pager_outputs(args.public)
    else:
        with tempfile.TemporaryDirectory(prefix="oink-components-reading-") as temp:
            public = Path(temp) / "public"
            result = build_example(args.hugo, public)
            if result.returncode != 0:
                print("reading fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_math(public) + check_pager_outputs(public)

    errors += (
        check_explicit_navigation(args.hugo)
        + check_explicit_navigation_scopes(args.hugo)
        + check_explicit_navigation_state(args.hugo)
        + check_explicit_navigation_boundaries(args.hugo)
        + check_cached_content_navigation(args.hugo)
        + check_foldable_content_navigation(args.hugo)
        + check_home_root_navigation(args.hugo)
        + check_invalid_pager_config(args.hugo)
        + check_invalid_eq_escape(args.hugo)
        + check_unnumbered_math_attributes(args.hugo)
        + check_print_math_and_heading(args.hugo)
        + check_print_relative_links(args.hugo)
        + check_print_encoded_fragments(args.hugo)
        + check_explicit_shell_overrides(args.hugo)
        + check_rss_pager_output(args.hugo)
        + check_pager_sources()
        + check_group_only_sections(args.hugo)
    )

    if errors:
        print("reading checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("reading checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
