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

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("taxonomy localization OK: module is opt-in and renders in English and Chinese")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
