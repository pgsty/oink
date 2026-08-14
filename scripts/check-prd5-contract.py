#!/usr/bin/env python3
"""Keep the published PRD 5 0.4 and 0.5 contracts aligned."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests/fixtures/prd5/contract.json"
DOCS = {
    "reading_release": ROOT / "docs/prd5-reading-release-contract.md",
    "landing": ROOT / "docs/prd5-landing-contract.md",
}


class ContractError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate_machine(contract: dict[str, object]) -> None:
    require(contract.get("version") == 1, "contract version must be 1")
    require(contract.get("compatibility_floor") == "0.160.1", "Hugo floor changed")
    require(
        contract.get("release_assignments")
        == {"reading_release": "0.4.0", "landing": "0.5.0"},
        "release assignments changed",
    )
    require(
        contract.get("authority")
        == {
            "navigation": "existing_sidebar_tree",
            "landing_content": "local_data_or_inline_sections",
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
    landing = contract.get("landing", {})
    require(landing.get("runtime_flag") == "hasLanding", "Landing runtime flag changed")
    require(
        landing.get("new_sections")
        == ["pricing", "pricing-compare", "command-box", "steps", "timeline", "code-plate", "case-study", "download", "bar-chart"],
        "Landing section registry changed",
    )
    require(landing.get("localized_field_order") == ["exact_language", "primary_language", "base"], "Landing language fallback changed")
    require(landing.get("marquee_pause") == "css_checkbox", "Landing pause contract changed")
    require(landing.get("marquee_duplicate") == ["aria-hidden", "inert"], "Landing duplicate isolation changed")
    require(landing.get("network_fetch") is False and landing.get("rss") == "strip", "Landing local-first/output boundary changed")
    require(
        contract.get("runtime_flags")
        == {"hasAssetList": "asset-list.js", "hasLanding": "landing.js"},
        "runtime flags changed",
    )
    require(contract.get("planned_tracks") == {"book": "0.6.0"}, "future Book milestone changed")
    matrix = contract.get("output_matrix", {})
    require(
        set(matrix) == {"pager", "release_card", "release_assets", "download", "eq_escape", "landing"},
        "0.5 output matrix component set changed",
    )
    require(all(set(row) == {"html", "print", "markdown", "rss"} for row in matrix.values()), "output matrix surfaces changed")


def validate_docs(contract: dict[str, object]) -> None:
    required = {
        "reading_release": (
            "# PRD 5 reading and release contract",
            "## 1. Sequential reading pager",
            "## 2. Mathematics passthrough",
            "## 3. Release primitives",
            "## 4. Release assets and download data",
            "hasAssetList",
            "{{< eq >}}...{{< /eq >}}",
        ),
        "landing": (
            "# PRD 5 landing contract",
            "## 1. Landing shell and data authority",
            "## 2. Section registry",
            "## 3. Language resolution",
            "## 4. Runtime and accessibility",
            "## 5. Output matrix",
            "## 6. Compatibility and non-goals",
            "hasLanding",
            "OinkSurfaceCoordinator",
        ),
    }
    assignments = contract["release_assignments"]
    for name, path in DOCS.items():
        source = path.read_text(encoding="utf-8")
        require(f"OINK {assignments[name]}" in source, f"{path.name} lacks its version")
        require("Status: frozen for implementation" in source, f"{path.name} is not frozen")
        require("Compatibility floor: Hugo Extended 0.160.1" in source, f"{path.name} lacks Hugo floor")
        require("tests/fixtures/prd5/contract.json" in source, f"{path.name} lacks machine companion")
        require("prd5-migration-guide.md" in source and "prd5-migration-guide.zh.md" in source, f"{path.name} lacks bilingual links")
        for literal in required[name]:
            require(literal in source, f"{path.name} lacks {literal}")


def main() -> int:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        require(isinstance(contract, dict), "PRD 5 contract must be a JSON object")
        validate_machine(contract)
        validate_docs(contract)
    except (OSError, json.JSONDecodeError, ContractError, TypeError, AttributeError) as exc:
        print(f"PRD 5 contract check failed: {exc}", file=sys.stderr)
        return 1
    print("PRD 5 0.4/0.5 contracts are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
