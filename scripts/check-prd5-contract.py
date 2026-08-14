#!/usr/bin/env python3
"""Keep the published PRD 5 0.4 human and machine contracts aligned."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests/fixtures/prd5/contract.json"
DOC = ROOT / "docs/prd5-reading-release-contract.md"


class ContractError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate_machine(contract: dict[str, object]) -> None:
    require(contract.get("version") == 1, "contract version must be 1")
    require(contract.get("release_assignment") == "0.4.0", "release assignment changed")
    require(contract.get("compatibility_floor") == "0.160.1", "Hugo floor changed")
    require(
        contract.get("authority")
        == {
            "navigation": "existing_sidebar_tree",
            "release_facts": "page_front_matter",
            "download_facts": "data_download_key",
        },
        "authority boundaries changed",
    )
    pager = contract.get("pager", {})
    require(pager.get("default_types") == ["docs", "book", "blog"], "pager defaults changed")
    require(pager.get("docs_book_order") == "sidebar_preorder", "reading order changed")
    require(pager.get("docs_root_values") == ["section", "home"], "docs root modes changed")
    require(pager.get("blog_order") == "time" and pager.get("non_html") == "strip", "pager outputs changed")
    require(
        contract.get("mathematics")
        == {
            "passthrough_hook": True,
            "eq_escape_parameters": "none",
            "eq_escape_registers_target": False,
            "runtime": False,
        },
        "mathematics escape-hatch contract changed",
    )
    release = contract.get("release", {})
    require(release.get("forge") == "github.com", "release forge boundary changed")
    require(release.get("network_fetch") is False and release.get("runtime") is False, "release local-first boundary changed")
    download = contract.get("download", {})
    require(download.get("channel_kinds") == ["rolling", "pinned"], "download channel kinds changed")
    require(download.get("rolling_interpolation") is False and download.get("rss") == "strip", "download safety/output changed")
    require(contract.get("runtime_flags") == {"hasAssetList": "asset-list.js"}, "runtime flags changed")
    require(contract.get("planned_tracks") == {"landing": "0.5.0", "book": "0.6.0"}, "future milestone plan changed")
    matrix = contract.get("output_matrix", {})
    require(
        set(matrix) == {"pager", "release_card", "release_assets", "download", "eq_escape"},
        "0.4 output matrix component set changed",
    )
    require(all(set(row) == {"html", "print", "markdown", "rss"} for row in matrix.values()), "output matrix surfaces changed")


def validate_doc() -> None:
    source = DOC.read_text(encoding="utf-8")
    for literal in (
        "# PRD 5 reading and release contract",
        "Version assignment: OINK 0.4.0",
        "Status: frozen for implementation",
        "Compatibility floor: Hugo Extended 0.160.1",
        "## 1. Sequential reading pager",
        "## 2. Mathematics passthrough",
        "## 3. Release primitives",
        "## 4. Release assets and download data",
        "## 5. Shared production-site compatibility",
        "tests/fixtures/prd5/contract.json",
        "prd5-migration-guide.md",
        "prd5-migration-guide.zh.md",
        "{{< eq >}}...{{< /eq >}}",
        "hasAssetList",
        "data/docs_nav.json",
    ):
        require(literal in source, f"{DOC.name} lacks {literal}")


def main() -> int:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        require(isinstance(contract, dict), "PRD 5 contract must be a JSON object")
        validate_machine(contract)
        validate_doc()
    except (OSError, json.JSONDecodeError, ContractError, TypeError, AttributeError) as exc:
        print(f"PRD 5 contract check failed: {exc}", file=sys.stderr)
        return 1
    print("PRD 5 0.4 contracts are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
