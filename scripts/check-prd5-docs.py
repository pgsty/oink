#!/usr/bin/env python3
"""Verify PRD 5 0.4-0.5 bilingual guidance and starter output."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
EN = ROOT / "docs/prd5-migration-guide.md"
ZH = ROOT / "docs/prd5-migration-guide.zh.md"


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
    require(result.returncode == 0, f"PRD 5 starter failed for {base_url}:\n{result.stdout}{result.stderr}")

    expected = {
        "math": destination / "docs/math-passthrough/index.html",
        "download": destination / "docs/download-demo/index.html",
        "pending": destination / "docs/download-pending/index.html",
        "release": destination / "blog/release/pig-1.10.0/index.html",
        "release_index": destination / "blog/release/index.html",
        "landing": destination / "landing-demo/index.html",
        "landing_print": destination / "_print/landing-demo/index.html",
        "landing_markdown": destination / "landing-demo/index.md",
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

    require('class="katex-display"' in math and "<math" in math, "starter mathematics is not server-rendered")
    require("td-download" in download and "data-download-kind" in download, "starter download channels are missing")
    require('aria-disabled="true"' in pending, "starter unpublished download state is missing")
    require("td-release-card" in release and "td-asset-list" in release, "starter release primitives are missing")
    require("td-release-index" in release_index, "starter release index is missing")
    require(
        "data-td-landing" in landing
        and "Static pricing cards" in landing
        and "Project timeline" in landing,
        "starter Landing registry is incomplete",
    )
    require(
        "oink-marquee--static" in landing_print and "data-td-landing" not in landing_print,
        "starter Landing print output is not static",
    )
    require(
        "## Any page can be a landing page" in landing_markdown
        and "oink-" not in landing_markdown,
        "starter Landing Markdown output is not semantic text",
    )

    prefix = "/preview/" if "/preview/" in base_url else "/"
    require(f'{prefix}scss/' in math, "starter assets ignored the deployment prefix")
    require(f'{prefix}docs/' in math, "starter navigation ignored the deployment prefix")
    require(f'{prefix}blog/release/' in release_index, "starter release links ignored the deployment prefix")
    require(f'{prefix}scss/' in landing, "starter Landing assets ignored the deployment prefix")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()
    try:
        en = EN.read_text(encoding="utf-8")
        zh = ZH.read_text(encoding="utf-8")
        expected_anchors = [
            "release-gates",
            "reading-navigation",
            "mathematics",
            "release-pages",
            "download-data",
            "landing-migration",
            "shared-overrides",
            "validation-checklist",
        ]
        require(anchors(en) == expected_anchors, f"English PRD 5 anchors changed: {anchors(en)}")
        require(anchors(zh) == expected_anchors, f"EN/ZH PRD 5 anchors differ: {anchors(zh)}")
        for literal in (
            "OINK 0.4.0",
            "OINK 0.5.0",
            "0.160.1",
            "data/docs_nav.json",
            "release-card",
            "release-assets",
            "data/download/<key>.yaml",
            "{{< eq >}}E = mc^2{{< /eq >}}",
            "asset-list.js",
            "layout: landing",
            "data/landing/<key>/<lang>.yaml",
            "hasLanding",
            "landing_search",
            "reduced motion",
            "forced colors",
            "RSS",
            "print",
            "Markdown",
            "/preview/",
        ):
            require(literal in en, f"English PRD 5 guide lacks {literal}")
            require(literal in zh, f"Chinese PRD 5 guide lacks {literal}")
        for forbidden in (
            "prd5-book-contract",
            "check-book.py",
            "check-prd5-migrations.py",
            "sidebar_headings",
            "book_draft_banner",
        ):
            require(forbidden not in en and forbidden not in zh, f"0.5 guide publishes future surface {forbidden}")
        require(len(blocks(en, "yaml")) == len(blocks(zh, "yaml")) == 6, "EN/ZH YAML example coverage differs")
        require(
            len(blocks(en, "go-html-template")) == len(blocks(zh, "go-html-template")) == 1,
            "EN/ZH shortcode example coverage differs",
        )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for literal in ("prd5-migration-guide.md", "prd5-migration-guide.zh.md", "prd5-landing-contract.md", "0.4–0.5"):
            require(literal in readme, f"README lacks {literal}")
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        commands = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        for checker in (
            "check-prd5-contract.py",
            "check-prd5-docs.py",
            "check-prd5-reading.py",
            "check-release-assets.py",
            "check-download.py",
            "check-landing.py",
            "check-prd5-misc.py",
        ):
            require(checker in ci and checker in commands, f"{checker} is not wired into CI and Commands")
        for future in ("check-book.py", "check-prd5-migrations.py"):
            require(future not in ci and future not in commands, f"0.5 CI publishes future checker {future}")

        with tempfile.TemporaryDirectory(prefix="oink-prd5-docs-") as temp:
            root = Path(temp)
            build(args.hugo, "https://example.org/", root / "root")
            build(args.hugo, "https://example.org/preview/", root / "subpath")
    except (OSError, DocumentationError) as exc:
        print(f"PRD 5 documentation check failed: {exc}", file=sys.stderr)
        return 1
    print("PRD 5 0.4-0.5 bilingual migration and starter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
