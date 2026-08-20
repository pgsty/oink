#!/usr/bin/env python3
"""Verify the starter's root/subpath, search, component, and output wiring."""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

from test_site import fixture_config_args


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read(public: Path, relative: str) -> str:
    path = public / relative
    require(path.is_file(), f"starter output is missing {relative}")
    return path.read_text(encoding="utf-8")


def build(base_url: str, public: Path) -> None:
    result = subprocess.run(
        [
            "hugo",
            "--source",
            str(FIXTURE),
            "--destination",
            str(public),
            "--baseURL",
            base_url,
            *fixture_config_args(),
            "--printPathWarnings",
            "--panicOnWarning",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(result.returncode == 0, f"starter build failed for {base_url}:\n{result.stdout}{result.stderr}")

    home = read(public, "index.html")
    docs = read(public, "docs/index.html")
    math = read(public, "fixtures/math-passthrough/index.html")
    download = read(public, "fixtures/download-demo/index.html")
    pending = read(public, "fixtures/download-pending/index.html")
    release = read(public, "blog/release/pig-1.10.0/index.html")
    release_index = read(public, "blog/release/index.html")
    landing = read(public, "landing-demo/index.html")
    landing_print = read(public, "_print/landing-demo/index.html")
    landing_markdown = read(public, "landing-demo/index.md")
    book = read(public, "book/index.html")
    chapter = read(public, "book/chapter-two/index.html")

    require(home.count("data-td-navbar-menu") == 1, "starter navbar is not singular")
    require('href="https://github.com/pgsty/oink"' in home and 'rel="noopener noreferrer"' in home,
            "starter external navigation is unsafe")
    require('class="katex-display"' in math and "<math" in math, "starter math is not server-rendered")
    require("td-download" in download and "data-td-download-kind" in download, "starter download is missing")
    require('aria-disabled="true"' in pending, "starter pending download state is missing")
    require("td-release-card" in release and "td-asset-list" in release, "starter release primitives are missing")
    require("td-blog-table" in release_index, "starter release table is missing")
    require("data-td-landing" in landing and "Static pricing cards" in landing, "starter Landing is incomplete")
    require("td-landing-marquee--static" in landing_print and "data-td-landing" not in landing_print,
            "starter Landing print output is interactive")
    require("## Any page can be a landing page" in landing_markdown and "td-landing-" not in landing_markdown,
            "starter Landing Markdown is not semantic source")
    require("td-book-toc" in book and "Figure 1-1" in book and "Table 1-1" in book,
            "starter Book contract is incomplete")
    require("data-td-book-headings" in chapter and "#delivery-states" in chapter,
            "starter Book headings are incomplete")

    prefix = "/preview/" if "/preview/" in base_url else "/"
    for marker in (f'href="{prefix}docs/"', f'href="{prefix}blog/"'):
        require(marker in home, f"starter navigation ignored {prefix}")
    for page in (math, landing):
        require(f"{prefix}scss/" in page, f"starter assets ignored {prefix}")
    require(f"{prefix}blog/release/" in release_index and f"{prefix}book/chapter-one/" in book,
            f"starter component links ignored {prefix}")

    index_match = re.search(r'data-td-index-src="([^"]+)"', docs)
    require(index_match is not None, "starter emitted no local search index")
    index_path = urlparse(html.unescape(index_match.group(1))).path
    require(index_path.startswith(prefix), f"starter index ignored {prefix}: {index_path}")
    require((public / index_path.removeprefix(prefix)).is_file(), f"starter index is missing: {index_path}")

    manifest_match = re.search(
        r'<script type="application/json" id="td-action-manifest">(.*?)</script>',
        docs,
        re.DOTALL,
    )
    require(manifest_match is not None, "starter emitted no action manifest")
    manifest = json.loads(manifest_match.group(1))
    commands = {item["id"]: item for item in manifest.get("commands", [])}
    require(commands.get("example_status", {}).get("url") == "https://status.example.org/",
            "starter URL command changed")
    require(commands.get("print_example", {}).get("action") == "print", "starter built-in command changed")
    require(commands.get("example_docs", {}).get("url") == f"{prefix}docs/callout/",
            "starter internal command ignored the deployment prefix")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="oink-starter-") as temporary:
            workspace = Path(temporary)
            build("https://example.org/", workspace / "root")
            build("https://example.org/preview/", workspace / "subpath")
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"starter check failed: {exc}", file=sys.stderr)
        return 1
    print("starter root/subpath checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
