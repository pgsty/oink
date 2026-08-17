#!/usr/bin/env python3
"""Verify bilingual component-migration coverage and starter/subpath output."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
EN = ROOT / "docs/migration-components.md"
ZH = ROOT / "docs/migration-components.zh.md"
MIGRATOR = ROOT / "scripts/migrations/book_figures.py"
# The one-time work orders for the corpora these profiles were derived from are
# site facts, not theme documentation; only the profile surface is public.
PROFILES = ("tpme", "ddia-v2", "ddia-v1", "pg-internal")


class DocumentationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DocumentationError(message)


def anchors(source: str) -> list[str]:
    return re.findall(r"^#{2,3}\s+.*?\s+\{#([a-z0-9-]+)\}\s*$", source, re.M)


def blocks(source: str, language: str) -> list[str]:
    return re.findall(rf"```{language}\n(.*?)\n```", source, re.S)


def build(hugo: str, base_url: str, destination: Path) -> None:
    result = subprocess.run(
        [
            hugo,
            "--source",
            str(EXAMPLE),
            "--destination",
            str(destination),
            "--baseURL",
            base_url,
            "--printPathWarnings",
            "--panicOnWarning",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(result.returncode == 0, f"starter site failed for {base_url}:\n{result.stdout}{result.stderr}")
    expected = {
        "math": destination / "docs/math-passthrough/index.html",
        "download": destination / "docs/download-demo/index.html",
        "pending": destination / "docs/download-pending/index.html",
        "release": destination / "blog/release/pig-1.10.0/index.html",
        "release_index": destination / "blog/release/index.html",
        "landing": destination / "landing-demo/index.html",
        "landing_print": destination / "_print/landing-demo/index.html",
        "landing_markdown": destination / "landing-demo/index.md",
        "book": destination / "book/index.html",
        "chapter": destination / "book/chapter-two/index.html",
    }
    for name, path in expected.items():
        require(path.exists(), f"starter {name} output is missing for {base_url}")

    math = expected["math"].read_text(encoding="utf-8")
    download = expected["download"].read_text(encoding="utf-8")
    pending = expected["pending"].read_text(encoding="utf-8")
    release = expected["release"].read_text(encoding="utf-8")
    release_index = expected["release_index"].read_text(encoding="utf-8")
    landing = expected["landing"].read_text(encoding="utf-8")
    landing_print = expected["landing_print"].read_text(encoding="utf-8")
    landing_markdown = expected["landing_markdown"].read_text(encoding="utf-8")
    book = expected["book"].read_text(encoding="utf-8")
    chapter = expected["chapter"].read_text(encoding="utf-8")

    require('class="katex-display"' in math and "<math" in math, "starter mathematics is not server-rendered")
    require("td-download" in download and "data-td-download-kind" in download, "starter download channels are missing")
    require('aria-disabled="true"' in pending, "starter unpublished download state is missing")
    require("td-release-card" in release and "td-asset-list" in release, "starter release primitives are missing")
    require("td-release-index" in release_index, "starter release index is missing")
    require("td-book-toc" in book and "Figure 1-1" in book and "Table 1-1" in book, "starter Book contract is missing")
    require("data-td-book-headings" in chapter and "#stable-heading" in chapter, "Book active-page heading branch is missing")
    require("data-td-landing" in landing and "Static pricing cards" in landing and "Project timeline" in landing, "starter landing registry is incomplete")
    require("td-landing-marquee--static" in landing_print and "data-td-landing" not in landing_print, "starter Landing print output is not static")
    require("## Any page can be a landing page" in landing_markdown and "td-landing-" not in landing_markdown, "starter Landing Markdown output is not semantic text")

    prefix = "/preview/" if "/preview/" in base_url else "/"
    require(f'{prefix}scss/' in math, "starter assets ignored the deployment prefix")
    require(f'{prefix}docs/' in math, "starter navigation ignored the deployment prefix")
    require(f'{prefix}blog/release/' in release_index, "starter release links ignored the deployment prefix")
    require(f'{prefix}book/chapter-one/' in book, "Book links ignored deployment prefix")
    require(f'{prefix}scss/' in landing, "Landing assets ignored deployment prefix")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()
    try:
        en = EN.read_text(encoding="utf-8")
        zh = ZH.read_text(encoding="utf-8")
        en_anchors = anchors(en)
        zh_anchors = anchors(zh)
        require(en_anchors and en_anchors == zh_anchors, f"EN/ZH component-guide anchors differ:\nEN={en_anchors}\nZH={zh_anchors}")
        require(len(en_anchors) == len(set(en_anchors)), "component guide has duplicate anchors")
        literals = (
            "OINK 0.4.0",
            "OINK 0.5.0",
            "OINK 0.6.0",
            "0.160.1",
            "data/docs_nav.json",
            "release-card",
            "release-assets",
            "data/download/<key>.yaml",
            "{{< eq >}}E = mc^2{{< /eq >}}",
            "hasLanding",
            "pricing-compare",
            "sidebar_headings",
            "book_draft_banner",
            "check-book.py",
            "book_figures.py",
            "pandoc --webtex",
            "/preview/",
        )
        for literal in literals:
            require(literal in en, f"English component guide lacks {literal}")
            require(literal in zh, f"Chinese component guide lacks {literal}")
        require(MIGRATOR.exists(), "Book figure migration tool is missing")
        migrator = MIGRATOR.read_text(encoding="utf-8")
        for profile in PROFILES:
            require(f'"{profile}"' in migrator, f"migration tool lacks the {profile} profile")
            require(profile in en, f"English guide lacks the {profile} profile")
            require(profile in zh, f"Chinese guide lacks the {profile} profile")
        for source, language in ((en, "English"), (zh, "Chinese")):
            lower = source.lower()
            require("source" in lower or "源码" in source, f"{language} guide lacks source-state language")
            require("tag" in lower and ("deployed" in lower or "部署" in source), f"{language} guide conflates release gates")
            require("rss" in lower and "print" in lower and "markdown" in lower, f"{language} guide lacks output validation")
            require("reduced motion" in lower and "forced colors" in lower, f"{language} guide lacks accessibility gates")
        en_yaml = blocks(en, "yaml")
        zh_yaml = blocks(zh, "yaml")
        require(len(en_yaml) == len(zh_yaml) and len(en_yaml) >= 5, "EN/ZH YAML example coverage differs")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        require("migration-components.md" in readme and "migration-components.zh.md" in readme, "README lacks bilingual component-guide links")
        for contract in ("reading-release-contract.md", "landing-contract.md", "book-contract.md"):
            require(contract in readme, f"README lacks {contract}")
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        commands = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        for checker in (
            "check-component-contract.py",
            "check-component-docs.py",
            "check-reading.py",
            "check-release-assets.py",
            "check-download.py",
            "check-landing.py",
            "check-book.py",
            "check-book-migrations.py",
            "check-shared-scenarios.py",
        ):
            require(checker in ci and checker in commands, f"{checker} is not wired into CI and Commands")
        with tempfile.TemporaryDirectory(prefix="td-landing-components-docs-") as temp:
            root = Path(temp)
            build(args.hugo, "https://example.org/", root / "root")
            build(args.hugo, "https://example.org/preview/", root / "subpath")
    except (OSError, DocumentationError) as exc:
        print(f"documentation check failed: {exc}", file=sys.stderr)
        return 1
    print("bilingual migration and starter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
