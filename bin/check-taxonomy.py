#!/usr/bin/env python3
"""Validate opt-in taxonomy localization without changing theme policy."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write_site(source: Path, plural: str | None) -> None:
    taxonomy = ""
    english_menu = ""
    chinese_menu = ""
    if plural:
        taxonomy = f"\ntaxonomies:\n  module: {plural}\n"
        english_menu = f"""
    menus:
      main:
        - name: Modules
          identifier: modules
          url: /{plural}/
          weight: 10"""
        chinese_menu = f"""
    menus:
      main:
        - name: 模块
          identifier: modules
          url: /zh-cn/{plural}/
          weight: 10"""

    (source / "hugo.yaml").write_text(
        f"""baseURL: https://example.org/
title: Taxonomy fixture
theme: {ROOT.name}
defaultContentLanguage: en
disableKinds: [RSS, sitemap]
{taxonomy}
languages:
  en:
    locale: en-US
    label: English
    contentDir: content/en
    weight: 1
{english_menu}
  zh-cn:
    locale: zh-CN
    label: 简体中文
    contentDir: content/zh-cn
    weight: 2
{chinese_menu}

params:
  ui:
    shell_types: [docs]
""",
        encoding="utf-8",
    )

    field = plural or "module"
    hook = source / "layouts/_partials/hooks/body-end.html"
    hook.parent.mkdir(parents=True)
    hook.write_text(
        '{{ partial "taxonomy-terms-cloud.html" (dict "context" . "taxo" "'
        + field
        + '" "title" "Cloud") }}\n',
        encoding="utf-8",
    )
    for language, title in (("en", "English guide"), ("zh-cn", "中文指南")):
        content = source / "content" / language
        docs = content / "docs"
        docs.mkdir(parents=True)
        (content / "_index.md").write_text(
            f"---\ntitle: {title}\n---\n",
            encoding="utf-8",
        )
        (docs / "_index.md").write_text(
            f"---\ntitle: {title}\n---\n",
            encoding="utf-8",
        )
        (docs / "guide.md").write_text(
            f"---\ntitle: {title}\n{field}: [CORE]\n---\n\nFixture.\n",
            encoding="utf-8",
        )


def build(hugo: str, source: Path, destination: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            hugo,
            "--source",
            str(source),
            "--themesDir",
            str(ROOT.parent),
            "--destination",
            str(destination),
            "--printPathWarnings",
            "--panicOnWarning",
            "--logLevel",
            "warn",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def check_disabled(hugo: str, root: Path) -> list[str]:
    errors: list[str] = []
    source = root / "disabled"
    public = source / "public"
    source.mkdir()
    write_site(source, None)
    result = build(hugo, source, public)
    require(
        result.returncode == 0,
        f"default taxonomy fixture failed to build: {result.stdout}{result.stderr}",
        errors,
    )
    if result.returncode == 0:
        for path in (
            public / "module",
            public / "modules",
            public / "zh-cn/module",
            public / "zh-cn/modules",
        ):
            require(not path.exists(), f"module taxonomy was enabled by default at {path}", errors)
    return errors


def check_enabled(hugo: str, root: Path, plural: str) -> list[str]:
    errors: list[str] = []
    source = root / f"enabled-{plural}"
    public = source / "public"
    source.mkdir()
    write_site(source, plural)
    result = build(hugo, source, public)
    require(
        result.returncode == 0,
        f"{plural} taxonomy fixture failed to build: {result.stdout}{result.stderr}",
        errors,
    )
    if result.returncode != 0:
        return errors

    english_plural = "Module" if plural == "module" else "Modules"
    pages = {
        public / plural / "index.html": f"<h1>{english_plural}</h1>",
        public / plural / "core/index.html": "<h1>Module: CORE</h1>",
        public / "zh-cn" / plural / "index.html": "<h1>模块</h1>",
        public / "zh-cn" / plural / "core/index.html": "<h1>模块: CORE</h1>",
    }
    for path, marker in pages.items():
        require(path.exists(), f"missing rendered taxonomy page {path}", errors)
        if path.exists():
            require(
                marker in path.read_text(encoding="utf-8"),
                f"{path} did not contain localized heading {marker}",
                errors,
            )

    navbar_pages = {
        public / plural / "index.html": f'href="/{plural}/core/"',
        public / "zh-cn" / plural / "index.html": f'href="/zh-cn/{plural}/core/"',
    }
    for path, term_link in navbar_pages.items():
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")
        require(
            "td-nav-menu__panel--taxonomy" in html
            and 'data-td-taxonomy="' + plural + '"' in html,
            f"{path} did not promote its URL menu to a taxonomy panel",
            errors,
        )
        require(term_link in html, f"{path} taxonomy panel lost its localized term URL", errors)
        require(
            'class="taxonomy td-taxonomy-terms-cloud' in html
            and 'class="td-taxonomy-count">1</span>' in html,
            f"{path} consumer taxonomy cloud partial is unavailable",
            errors,
        )

    article_pages = {
        public / "docs/guide/index.html": f"{english_plural}:",
        public / "zh-cn/docs/guide/index.html": "模块:",
    }
    for path, label in article_pages.items():
        require(path.exists(), f"missing rendered article page {path}", errors)
        if path.exists():
            html = path.read_text(encoding="utf-8")
            require(
                f'<span class="td-taxonomy-title">{label}</span>' in html,
                f"{path} did not contain localized article taxonomy label {label}",
                errors,
            )
    return errors




# The series fixture makes weight order, date order, and path order disagree,
# so a reading order that came out right by luck still comes out wrong here.
# Expected reading order: wal (weight 1), mvcc (weight 2), then the unweighted
# pair oldest first -- vacuum (Aug 2), buffers (Aug 4).
SERIES_MEMBERS = (
    # slug, date, series_weight
    ("wal", "2026-08-07", 1),
    ("mvcc", "2026-08-05", 2),
    ("vacuum", "2026-08-02", None),
    ("buffers", "2026-08-04", None),
)
SERIES_READING_ORDER = ["/blog/wal/", "/blog/mvcc/", "/blog/vacuum/", "/blog/buffers/"]


def write_series_site(source: Path, declared: bool) -> None:
    """A blog with one four-part series, one series of one, and a switch.

    Declaring the taxonomy is the whole feature switch, so the same content is
    built both ways: with the declaration the strip and the term pages exist,
    without it `series:` stays an ordinary page parameter nothing reads.
    """

    taxonomy = "\ntaxonomies:\n  series: series\n" if declared else ""
    (source / "hugo.yaml").write_text(
        f"""baseURL: https://example.org/
title: Series fixture
theme: {ROOT.name}
defaultContentLanguage: en
disableKinds: [RSS, sitemap]
{taxonomy}
params:
  ui:
    shell_types: [blog]
""",
        encoding="utf-8",
    )

    blog = source / "content/blog"
    blog.mkdir(parents=True)
    (source / "content/_index.md").write_text("---\ntitle: Home\n---\n", encoding="utf-8")
    (blog / "_index.md").write_text("---\ntitle: Blog\n---\n", encoding="utf-8")

    term = source / "content/series/pg-internals"
    term.mkdir(parents=True)
    (term / "_index.md").write_text(
        "---\ntitle: Postgres internals\n---\n\nThe series introduction is the term page.\n",
        encoding="utf-8",
    )

    for slug, date, weight in SERIES_MEMBERS:
        front = [f"title: Part {slug}", f"date: {date}", "series: [pg-internals]"]
        if weight is not None:
            front.append(f"series_weight: {weight}")
        (blog / f"{slug}.md").write_text(
            "---\n" + "\n".join(front) + "\n---\n\nA member of the series.\n",
            encoding="utf-8",
        )

    # A series of one has nowhere to navigate to, and its term carries no
    # _index.md either, so the implicit-term path is exercised at once.
    (blog / "solo.md").write_text(
        "---\ntitle: On its own\ndate: 2026-08-09\nseries: [solo-note]\n---\n\nOne member.\n",
        encoding="utf-8",
    )
    # A page in no series at all: the strip must never reach it.
    (blog / "unrelated.md").write_text(
        "---\ntitle: Unrelated\ndate: 2026-08-08\n---\n\nNo series.\n",
        encoding="utf-8",
    )


def strip_of(html: str) -> str:
    match = re.search(r'<nav class="td-series-strip".*?</nav>', html, re.S)
    return match.group(0) if match else ""


def bundles_of(html: str) -> list[str]:
    return sorted(re.findall(r'src="([^"]*/js/[^"]+)"', html))


def check_series_declared(hugo: str, root: Path) -> list[str]:
    errors: list[str] = []
    source = root / "series-declared"
    public = source / "public"
    source.mkdir()
    write_series_site(source, True)
    result = build(hugo, source, public)
    require(
        result.returncode == 0,
        f"series fixture failed to build: {result.stdout}{result.stderr}",
        errors,
    )
    if result.returncode != 0:
        return errors

    # Reading order, on the term page, in an <ol> whose numbers are the parts.
    term_page = public / "series/pg-internals/index.html"
    require(term_page.exists(), "series term page was not built", errors)
    if term_page.exists():
        html = term_page.read_text(encoding="utf-8")
        listing = re.search(r'<ol class="td-blog-posts-list td-blog-posts-list--numbered">(.*?)\n\s*</ol>', html, re.S)
        require(listing is not None, "series term page did not number its members with an <ol>", errors)
        if listing:
            found = re.findall(r'<h2 class="h5[^"]*">\s*<a href="([^"]+)"', listing.group(1))
            require(
                found == SERIES_READING_ORDER,
                f"series term page order is {found}, expected reading order {SERIES_READING_ORDER}",
                errors,
            )
        require("<h1>Series: Postgres internals</h1>" in html,
                "series term page lost its localized taxonomy label", errors)

    # The fixture is only worth building while reading order disagrees with
    # every order something else could have produced: newest first, oldest
    # first, and the alphabetical path order used as the tie-breaker.
    def url(member) -> str:
        return f"/blog/{member[0]}/"

    wrong_orders = {
        "newest first": [url(m) for m in sorted(SERIES_MEMBERS, key=lambda m: m[1], reverse=True)],
        "oldest first": [url(m) for m in sorted(SERIES_MEMBERS, key=lambda m: m[1])],
        "path order": sorted(url(m) for m in SERIES_MEMBERS),
    }
    for label, order in wrong_orders.items():
        require(SERIES_READING_ORDER != order,
                f"the series fixture stopped disagreeing with {label}, so its order proves nothing", errors)

    # The strip: position in the series, the next part, and the whole list.
    middle = public / "blog/mvcc/index.html"
    require(middle.exists(), "series member page was not built", errors)
    if middle.exists():
        html = middle.read_text(encoding="utf-8")
        strip = strip_of(html)
        require(bool(strip), "a series member rendered no strip", errors)
        require("Part 2 of 4" in strip, f"strip did not place the second part: {strip[:200]}", errors)
        require('href="/series/pg-internals/"' in strip,
                "strip did not link its series term page", errors)
        require('class="td-series-strip__next-link" href="/blog/vacuum/"' in strip,
                "strip did not point at the next part in reading order", errors)
        found = re.findall(r'<li class="td-series-strip__item"><a[^>]*href="([^"]+)"', strip)
        require(found == SERIES_READING_ORDER,
                f"strip listed {found}, expected reading order {SERIES_READING_ORDER}", errors)
        require(strip.count('aria-current="page"') == 1
                and 'href="/blog/mvcc/" aria-current="page"' in strip,
                "strip did not mark exactly the reader's own place", errors)
        require("<details" in strip and "<summary" in strip and "data-td-" not in strip,
                "the series list stopped being a scriptless disclosure", errors)
        plain = public / "blog/unrelated/index.html"
        if plain.exists():
            require(bundles_of(html) == bundles_of(plain.read_text(encoding="utf-8")),
                    "the series strip changed the page's script bundles", errors)
        # The strip carries the series, so the chips row must not repeat it.
        require("taxo-series" not in html,
                "the article chips row still repeats the series term", errors)

    last = public / "blog/buffers/index.html"
    if last.exists():
        strip = strip_of(last.read_text(encoding="utf-8"))
        require("Part 4 of 4" in strip, "strip did not place the last part", errors)
        require("td-series-strip__next" not in strip,
                "the last part of a series still offers a next part", errors)

    for name, why in (
        ("blog/solo/index.html", "a series of one still renders a strip"),
        ("blog/unrelated/index.html", "a page in no series renders a strip"),
    ):
        page = public / name
        require(page.exists(), f"{name} was not built", errors)
        if page.exists():
            require(not strip_of(page.read_text(encoding="utf-8")), why, errors)
    return errors


def check_series_undeclared(hugo: str, root: Path) -> list[str]:
    """Without the declaration `series:` is an ordinary parameter again."""

    errors: list[str] = []
    source = root / "series-undeclared"
    public = source / "public"
    source.mkdir()
    write_series_site(source, False)
    result = build(hugo, source, public)
    require(
        result.returncode == 0,
        f"undeclared series fixture failed to build: {result.stdout}{result.stderr}",
        errors,
    )
    if result.returncode != 0:
        return errors
    # content/series/ is an ordinary section either way; a term with no content
    # file of its own exists only when the taxonomy does.
    require(not (public / "series/solo-note/index.html").exists(),
            "series term pages were built without the taxonomy being declared", errors)
    require(not (public / "series/pg-internals/index.html").read_text(encoding="utf-8").count(
                "td-blog-posts-list--numbered"),
            "an undeclared series still listed its members in reading order", errors)
    for page in public.rglob("*.html"):
        require("td-series-strip" not in page.read_text(encoding="utf-8"),
                f"{page.relative_to(public)} rendered a series strip without the taxonomy", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-taxonomy-") as temp:
        root = Path(temp)
        errors.extend(check_disabled(args.hugo, root))
        errors.extend(check_enabled(args.hugo, root, "module"))
        errors.extend(check_enabled(args.hugo, root, "modules"))
        errors.extend(check_series_declared(args.hugo, root))
        errors.extend(check_series_undeclared(args.hugo, root))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("taxonomy checks OK: module is opt-in and bilingual; the series reading order holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
