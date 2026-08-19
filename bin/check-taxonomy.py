#!/usr/bin/env python3
"""Validate opt-in taxonomy localization without changing theme policy."""

from __future__ import annotations

import argparse
from pathlib import Path
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


def write_authors_site(source: Path) -> None:
    """A bare blog whose only author configuration is the taxonomy itself."""

    (source / "hugo.yaml").write_text(
        f"""baseURL: https://example.org/
title: Authors fixture
theme: {ROOT.name}
defaultContentLanguage: en
disableKinds: [sitemap]
taxonomies:
  author: authors
languages:
  en:
    locale: en-US
    label: English
    contentDir: content/en
    weight: 1
  zh-cn:
    locale: zh-CN
    label: 简体中文
    contentDir: content/zh-cn
    weight: 2

params:
  offline_search: false
""",
        encoding="utf-8",
    )

    profiles = {
        "en": {"vonng": "Ruohang Feng", "nolan": "Nolan Vega"},
        "zh-cn": {"vonng": "冯若航", "nolan": "诺兰·维加"},
    }
    posts = {
        "en": ("Ordered byline", "Legacy byline"),
        "zh-cn": ("有序署名", "旧式署名"),
    }
    for language, names in profiles.items():
        content = source / "content" / language
        (content / "blog").mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Home\n---\n", encoding="utf-8")
        (content / "blog/_index.md").write_text(
            "---\ntitle: Blog\ntype: blog\ncascade:\n  type: blog\n---\n",
            encoding="utf-8",
        )
        for slug, name in names.items():
            profile = content / "authors" / slug
            profile.mkdir(parents=True)
            (profile / "_index.md").write_text(
                f"---\ntitle: {name}\ndescription: One line about {name}.\n---\n\n"
                f"The long biography of {name}.\n",
                encoding="utf-8",
            )
        ordered, legacy = posts[language]
        # `nolan` sorts ahead of `vonng`, and `ghost` has no profile page at
        # all: the byline must still read vonng, nolan, ghost.
        (content / "blog/ordered.md").write_text(
            f"---\ntitle: {ordered}\ndate: 2026-08-11\nauthors: [vonng, nolan, ghost]\n---\n\nOrdered.\n",
            encoding="utf-8",
        )
        (content / "blog/legacy.md").write_text(
            f"---\ntitle: {legacy}\ndate: 2026-08-10\nauthor: |\n"
            "  [Someone](https://example.org/someone) | [Elsewhere](https://example.org/elsewhere)\n"
            "---\n\nLegacy.\n",
            encoding="utf-8",
        )


def check_authors(hugo: str, root: Path) -> list[str]:
    """The `authors` plural is the whole switch: profiles, order, degradation."""

    errors: list[str] = []
    source = root / "authors"
    public = source / "public"
    source.mkdir()
    write_authors_site(source)
    result = build(hugo, source, public)
    require(
        result.returncode == 0,
        f"authors fixture failed to build: {result.stdout}{result.stderr}",
        errors,
    )
    if result.returncode != 0:
        return errors

    ordered = public / "blog/ordered/index.html"
    require(ordered.is_file(), "authors byline fixture page is missing", errors)
    if ordered.is_file():
        html = ordered.read_text(encoding="utf-8")
        positions = [
            html.find('href="/authors/vonng/"'),
            html.find('href="/authors/nolan/"'),
            html.find('href="/authors/ghost/"'),
        ]
        require(
            all(index >= 0 for index in positions) and positions == sorted(positions),
            "byline does not follow the front matter order of `authors`",
            errors,
        )
        require(
            ">Ghost<" in html
            and 'class="td-byline__avatar td-byline__avatar--placeholder" aria-hidden="true">G<' in html,
            "an author term with no profile page did not degrade to its link title and an initial",
            errors,
        )
        # The byline is the author surface; a generic chip row would repeat it.
        require(
            "taxo-authors" not in html,
            "the generic taxonomy chip row still renders the reserved `authors` plural",
            errors,
        )

    legacy = public / "blog/legacy/index.html"
    require(legacy.is_file(), "legacy byline fixture page is missing", errors)
    if legacy.is_file():
        html = legacy.read_text(encoding="utf-8")
        require(
            '<div class="td-byline mb-4">' in html
            and 'By <b><a href="https://example.org/someone">Someone</a> | '
                '<a href="https://example.org/elsewhere">Elsewhere</a></b> |' in html,
            "the 0.4 `author` string path changed shape on a site that declares the taxonomy",
            errors,
        )
        require(
            "td-byline--authors" not in html,
            "a page with no `authors` fell into the taxonomy byline",
            errors,
        )

    profiles = {
        public / "authors/vonng/index.html": (
            "Ruohang Feng", "One line about Ruohang Feng.", "The long biography"),
        public / "zh-cn/authors/vonng/index.html": (
            "冯若航", "One line about 冯若航.", "The long biography"),
    }
    for path, (name, description, biography) in profiles.items():
        require(path.is_file(), f"missing author profile page {path}", errors)
        if not path.is_file():
            continue
        html = path.read_text(encoding="utf-8")
        require(
            f'<h1 class="td-author-profile__name">{name}</h1>' in html
            and f'<p class="td-author-profile__description">{description}</p>' in html
            and biography in html,
            f"{path} did not render the term page as an author profile",
            errors,
        )
        require(
            f"<h1>Author: {name}</h1>" not in html,
            f"{path} still carries the generic term heading",
            errors,
        )
        require(
            'class="td-blog-posts-list' in html,
            f"{path} lost the archive list beneath the profile",
            errors,
        )

    listings = {
        public / "authors/index.html": "<h1>Authors</h1>",
        public / "zh-cn/authors/index.html": "<h1>作者</h1>",
    }
    for path, heading in listings.items():
        require(path.is_file(), f"missing author listing page {path}", errors)
        if path.is_file():
            require(
                heading in path.read_text(encoding="utf-8"),
                f"{path} did not localize the reserved `authors` plural ({heading})",
                errors,
            )

    feed = public / "blog/index.xml"
    require(feed.is_file(), "authors fixture blog feed is missing", errors)
    if feed.is_file():
        xml = feed.read_text(encoding="utf-8")
        require(
            'xmlns:dc="http://purl.org/dc/elements/1.1/"' in xml
            and "<dc:creator>Ruohang Feng</dc:creator>" in xml
            and "<dc:creator>Ghost</dc:creator>" in xml,
            "the blog feed does not carry a per-item dc:creator",
            errors,
        )
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
        errors.extend(check_authors(args.hugo, root))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "taxonomy localization OK: module is opt-in, renders in English and Chinese, "
        "and the reserved `authors` plural drives profiles and bylines"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
