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
from urllib.parse import urlsplit

from test_site import fixture_config_args


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"


class NavigationParser(HTMLParser):
    """Collect sidebar, pager, and head-link destinations from one page."""

    def __init__(self) -> None:
        super().__init__()
        self.in_sidebar = False
        self.sidebar_links: list[str] = []
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


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_example(hugo: str, destination: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
        "blog/index.html": {"prev": None, "next": "/blog/typography/"},
        "blog/typography/index.html": {"prev": "/blog/", "next": "/blog/oink/"},
        "blog/oink/index.html": {"prev": "/blog/typography/", "next": "/blog/oink/immersive-reading/"},
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
            require(head == expected[direction], f"{relative} head {direction} sidebar order changed", errors)

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
    return subprocess.run(
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
        for name, weight in (("alpha", 10), ("beta", 20), ("gamma", 30)):
            write_file(
                source / f"content/docs/{name}.md",
                f"---\ntitle: {name.title()}\nweight: {weight}\n---\n\n{name}\n",
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
            # An out-of-range value warns and falls back; only --panicOnWarning
            # turns that into a failure.
            require(result.returncode == 0,
                    f"invalid pager case {name} stopped the build instead of warning", errors)
            require(run_site(hugo, source, "--panicOnWarning").returncode != 0,
                    f"invalid pager case {name} survived --panicOnWarning", errors)
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
            require(expected in output, f"invalid eq escape case {name} did not report {expected!r}", errors)
            require(run_site(hugo, source, "--panicOnWarning").returncode != 0,
                    f"invalid eq escape case {name} survived --panicOnWarning", errors)
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
        + check_home_root_navigation(args.hugo)
        + check_invalid_pager_config(args.hugo)
        + check_invalid_eq_escape(args.hugo)
        + check_rss_pager_output(args.hugo)
        + check_pager_sources()
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
