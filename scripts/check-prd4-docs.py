#!/usr/bin/env python3
"""Verify PRD 4 EN/ZH reference parity, release language, and starter builds."""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
EN_DOC = ROOT / "docs" / "prd4-migration-guide.md"
ZH_DOC = ROOT / "docs" / "prd4-migration-guide.zh.md"
EXAMPLE = ROOT / "exampleSite"


class DocumentationError(RuntimeError):
    """Raised when the bilingual release reference loses its contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DocumentationError(message)


def anchor_ids(text: str) -> list[str]:
    return re.findall(r"^#{2,3}\s+.+?\s+\{#([a-z0-9-]+)\}\s*$", text, re.MULTILINE)


def code_blocks(text: str, language: str) -> list[str]:
    return re.findall(rf"```{language}\n(.*?)\n```", text, re.DOTALL)


def build_example(base_url: str, destination: Path) -> None:
    result = subprocess.run(
        [
            "hugo",
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
    require(
        result.returncode == 0,
        f"starter build failed for {base_url}:\n{(result.stdout + result.stderr).strip()}",
    )

    home = (destination / "index.html").read_text(encoding="utf-8")
    docs = (destination / "docs" / "index.html").read_text(encoding="utf-8")
    require(
        home.count("data-td-navbar-menu") == 1
        and home.count("data-td-navbar-accordion-toggle") == 0,
        f"starter desktop nested menu missing or mobile accordion returned at {base_url}",
    )
    require(
        'data-sidebar-icon-policy="all"' in docs,
        f"starter did not keep all authored sidebar icons at {base_url}",
    )
    require(
        'class="fa-solid fa-route"' in docs,
        f"starter suppressed the authored leaf-page icon at {base_url}",
    )
    require(
        'id="td-shell-search"' in docs and 'id="oink-action-manifest"' in docs,
        f"starter lost Palette/index/action manifest at {base_url}",
    )
    prefix = "/preview/" if "/preview/" in base_url else "/"
    require(
        f'href="{prefix}docs/"' in home
        and f'href="{prefix}blog/"' in home,
        f"starter internal navigation ignored the deployment prefix at {base_url}",
    )
    require(
        'href="https://github.com/pgsty/oink"' in home
        and 'target="_blank" rel="noopener noreferrer"' in home,
        f"starter lost safe external navigation at {base_url}",
    )

    index_match = re.search(r'data-index-src="([^"]+)"', docs)
    require(index_match is not None, f"starter emitted no local index reference at {base_url}")
    index_url = html.unescape(index_match.group(1))
    index_path = urlparse(index_url).path
    require(
        index_path.startswith(prefix) and "offline-search-index" in index_path,
        f"starter local index ignored the deployment prefix at {base_url}: {index_url}",
    )
    output_index = destination / index_path.removeprefix(prefix)
    require(output_index.is_file(), f"starter referenced a missing local index: {index_url}")

    manifest_match = re.search(
        r'<script type="application/json" id="oink-action-manifest">(.*?)</script>',
        docs,
        re.DOTALL,
    )
    require(manifest_match is not None, f"starter emitted no action manifest at {base_url}")
    manifest = json.loads(manifest_match.group(1))
    commands = {entry["id"]: entry for entry in manifest.get("commands", [])}
    require(
        commands.get("example_status", {}).get("url") == "https://status.example.org/"
        and commands.get("example_status", {}).get("target") == "blank"
        and commands.get("print_example", {}).get("action") == "print"
        and commands.get("example_docs", {}).get("url")
        == f"{prefix}docs/content-primitives/"
        and commands.get("example_docs", {}).get("target") == "self",
        f"starter URL/built-in command examples changed at {base_url}",
    )
    quick_links = {entry["id"]: entry for entry in manifest.get("quickLinks", [])}
    require(
        quick_links.get("quick_docs", {}).get("url") == f"{prefix}docs/"
        and quick_links.get("quick_blog", {}).get("url") == f"{prefix}blog/",
        f"starter quick links ignored the deployment prefix at {base_url}",
    )


def main() -> int:
    try:
        en = EN_DOC.read_text(encoding="utf-8")
        zh = ZH_DOC.read_text(encoding="utf-8")

        en_anchors = anchor_ids(en)
        zh_anchors = anchor_ids(zh)
        require(en_anchors, "English reference has no explicit section anchors")
        require(len(en_anchors) == len(set(en_anchors)), "English reference has duplicate anchors")
        require(len(zh_anchors) == len(set(zh_anchors)), "Chinese reference has duplicate anchors")
        require(
            en_anchors == zh_anchors,
            "English and Chinese section coverage differs:\n"
            f"EN={en_anchors}\nZH={zh_anchors}",
        )

        required_literals = (
            "sidebar_icon_policy",
            "navbar_accordion_single_open",
            "search_keywords",
            "search_boost",
            "search_exclude",
            "exclude_search",
            "excludeSearch",
            "offlineSearchIndex",
            "copy_markdown",
            "open_chatgpt",
            "open_claude",
            "view_history",
            "switch_theme",
            "switch_language",
            "switch_version",
            "noopener noreferrer",
            "0.160.1",
            "2 MiB",
            "512 KiB",
        )
        for literal in required_literals:
            require(literal in en, f"English reference is missing {literal}")
            require(literal in zh, f"Chinese reference is missing {literal}")

        # Version-language gate. The references name the version containing the
        # implementation without claiming that its public tag already exists.
        # Both languages must agree, and the changelog must have that section.
        # Deliberately version-agnostic so the next release does not have to
        # edit this check.
        en_release = re.search(r"included in OINK (\d+\.\d+\.\d+)", en)
        zh_release = re.search(r"纳入 OINK (\d+\.\d+\.\d+)", zh)
        require(en_release is not None, "English reference does not name its containing version")
        require(zh_release is not None, "Chinese reference does not name its containing version")
        require(
            en_release.group(1) == zh_release.group(1),
            "English and Chinese references name different containing versions",
        )
        released_version = en_release.group(1)

        for text, language in ((en, "English"), (zh, "Chinese")):
            lower = text.lower()
            require("1.0" in text and "0.x" in text, f"{language} alias removal window is missing")
            require(
                "deprecated" in lower or "弃用" in text,
                f"{language} legacy alias deprecation is missing",
            )
            require(
                "root" in lower and "subpath" in lower and "/preview/" in text,
                f"{language} root/subpath migration guidance is incomplete",
            )
            require(
                ("site-owned internal" in lower and "external destinations" in lower)
                or ("站点拥有的内部" in text and "外部" in text),
                f"{language} subpath guidance does not distinguish external URLs",
            )
            require(
                "telemetry" in lower and "print" in lower,
                f"{language} privacy/runtime gates are incomplete",
            )
            require(
                ("historical rail-only actions" in lower)
                or ("历史" in text and "rail-only actions" in lower),
                f"{language} action-registry scope is overstated",
            )
            require(
                "https://github.com/pgsty/oink/issues/18#issuecomment-5263306916" in text
                and "https://github.com/pgsty/oink.pgsty.com/issues/3#issuecomment-5263727126" in text,
                f"{language} release ledger lost passing local evidence links",
            )

        en_yaml = code_blocks(en, "yaml")
        zh_yaml = code_blocks(zh, "yaml")
        require(len(en_yaml) == len(zh_yaml), "bilingual YAML example coverage differs")
        require(len(en_yaml) >= 5, "bilingual YAML example coverage regressed")
        for blocks, language in ((en_yaml, "English"), (zh_yaml, "Chinese")):
            combined = "\n".join(blocks)
            require("parent: docs" in combined, f"{language} nested menu example is missing")
            require("search_keywords:" in combined, f"{language} search metadata example is missing")
            require("command_palette:" in combined, f"{language} command example is missing")
            require("assistant_links: true" in combined, f"{language} assistant-link opt-in example is missing")

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        require(
            "prd4-migration-guide.md" in readme
            and "prd4-migration-guide.zh.md" in readme,
            "README must link both language references",
        )
        require(
            f"## [{released_version}]" in changelog,
            f"changelog has no section for the released version {released_version}",
        )

        with tempfile.TemporaryDirectory(prefix="oink-prd4-docs-") as temporary:
            workspace = Path(temporary)
            build_example("https://example.org/", workspace / "root")
            build_example("https://example.org/preview/", workspace / "subpath")
    except (OSError, DocumentationError, json.JSONDecodeError) as exc:
        print(f"PRD 4 documentation check failed: {exc}", file=sys.stderr)
        return 1

    print("PRD 4 bilingual migration and starter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
