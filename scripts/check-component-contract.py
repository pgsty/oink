#!/usr/bin/env python3
"""Keep human and machine component contracts aligned."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests/fixtures/components/contract.json"
DOCS = {
    "reading_release": ROOT / "docs/reading-release-contract.md",
    "landing": ROOT / "docs/landing-contract.md",
    "book": ROOT / "docs/book-contract.md",
}


class ContractError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate_machine(contract: dict[str, object]) -> None:
    require(contract.get("version") == 2, "contract version must be 2 (Book contract v2)")
    require(contract.get("compatibility_floor") == "0.160.1", "Hugo floor changed")
    require(
        contract.get("release_assignments")
        == {"reading_release": "0.4.0", "landing": "0.4.0", "book": "0.4.0"},
        "consolidated release assignment changed",
    )
    require(
        contract.get("design_milestones")
        == {"reading_release": "0.4.0", "landing": "0.5.0", "book": "0.6.0"},
        "historical design milestones changed",
    )
    authority = contract.get("authority")
    require(
        authority
        == {
            "navigation": "existing_sidebar_tree",
            "landing_content": "local_data_or_inline_sections",
            "release_facts": "page_front_matter",
            "download_facts": "data_download_key",
            "book_structure": "content_tree_or_docs_nav",
        },
        "authority boundaries changed",
    )
    pager = contract.get("pager", {})
    require(pager.get("default_types") == ["docs", "book", "blog"], "pager type default changed")
    require(pager.get("docs_book_order") == "sidebar_preorder", "reading order changed")
    require(pager.get("docs_sidebar_root_values") == ["section", "home"], "docs sidebar root modes changed")
    mathematics = contract.get("mathematics", {})
    require(
        mathematics
        == {
            "passthrough_hook": True,
            "eq_escape_num_required": False,
            "eq_escape_registers_target": False,
            "runtime": False,
        },
        "mathematics escape-hatch contract changed",
    )
    release = contract.get("release", {})
    require(release.get("forge") == "github.com" and release.get("network_fetch") is False, "release local-first boundary changed")
    download = contract.get("download", {})
    require(download.get("channel_kinds") == ["rolling", "pinned"], "download channel kinds changed")
    require(download.get("rolling_interpolation") is False and download.get("rss") == "strip", "download safety/output changed")
    landing = contract.get("landing", {})
    require(landing.get("runtime_flag") == "hasLanding", "landing flag changed")
    require(
        landing.get("new_sections")
        == ["pricing", "pricing-compare", "command-box", "steps", "timeline", "code-plate", "case-study", "download", "bar-chart"],
        "landing section registry changed",
    )
    require(landing.get("network_fetch") is False and landing.get("rss") == "strip", "landing local-first/output changed")
    require(landing.get("marquee_pause") == "css_checkbox", "landing marquee pause contract changed")
    require(landing.get("marquee_duplicate") == ["aria-hidden", "inert"], "landing marquee duplicate isolation changed")
    book = contract.get("book", {})
    require(book.get("numbered_components") == ["fig", "tbl", "eq", "eg"], "Book numbered components changed")
    require(book.get("xref_kinds") == ["fig", "tbl", "eq", "eg"], "Book xref kinds changed")
    require(
        book.get("native_forms")
        == {
            "fig": "standalone_image_attribute_line",
            "tbl": "table_attribute_line",
            "eq": "passthrough_block_attribute_line",
            "eg": "fence_attributes",
        },
        "Book native forms changed",
    )
    require(
        book.get("book_indexes") == ["book-toc", "book-figures", "book-tables", "book-equations", "book-examples"],
        "Book index shortcodes changed",
    )
    require(book.get("registration_order") == "source_position", "Book registration order changed")
    require(book.get("removed") == ["example", "book-figures kind"], "Book removed forms changed")
    require(book.get("toc_depth") == [1, 2, 3], "Book ToC depth changed")
    require(book.get("automatic_numbering") is False and book.get("pdf_epub") is False, "Book non-goals changed")
    require(
        contract.get("runtime_flags")
        == {"hasAssetList": "asset-list.js", "hasLanding": "landing.js"},
        "runtime flags changed",
    )
    matrix = contract.get("output_matrix", {})
    require(set(matrix) == {"pager", "release_card", "release_assets", "download", "eq_escape", "landing", "fig_tbl_eq_eg", "xref", "book_toc", "book_index"}, "output matrix component set changed")
    require(all(set(row) == {"html", "print", "markdown", "rss"} for row in matrix.values()), "output matrix surfaces changed")
    require(
        contract.get("non_goals")
        == [
            "non_github_release_forge",
            "pricing_period_toggle",
            "remote_fact_fetch",
            "image_hotspots",
            "automatic_book_numbering",
            "pdf_epub_generation",
            "archive_shell",
            "glossary_component",
        ],
        "non-goals changed",
    )


def validate_docs(contract: dict[str, object]) -> None:
    release_assignments = contract["release_assignments"]
    required = {
        "reading_release": (
            "# Reading and release contract",
            "Status: frozen for OINK v0.4.0",
            "## 1. Sequential reading pager",
            "## 2. Mathematics passthrough",
            "## 3. Release primitives",
            "## 4. Release assets and download data",
            "## 5. Shared production-site compatibility",
            "hasAssetList",
            "{{< eq >}}...{{< /eq >}}",
            "data/docs_nav.json",
        ),
        "landing": (
            "# Landing contract",
            "Status: frozen for OINK v0.4.0",
            "## 1. Landing shell and data authority",
            "## 2. Section registry",
            "## 3. Language resolution",
            "## 4. Runtime and accessibility",
            "## 5. Output matrix",
            "## 6. Compatibility and non-goals",
            "hasLanding",
            "OinkSurfaceCoordinator",
            "pricing-compare",
        ),
        "book": (
            "# Book contract",
            "Contract version: 2",
            "Status: frozen for OINK v0.5.0",
            "`eg`",
            "book-tables",
            "book-equations",
            "book-examples",
            "wrapStandAloneImageWithinParagraph",
            "source position",
            "## 7. Version 2 changes",
            "## 1. Book type and navigation",
            "## 2. Numbered components",
            "## 3. Cross references and consistency",
            "## 4. Book tables of contents and figure lists",
            "## 5. Whole-Book print and output matrix",
            "## 6. Migration boundaries and non-goals",
            "scripts/check-book.py",
            "scripts/check-book-migrations.py",
            "scripts/migrations/book_figures.py",
            "data/docs_nav.json",
        ),
    }
    design_milestones = contract["design_milestones"]
    for name, path in DOCS.items():
        source = path.read_text(encoding="utf-8")
        version = release_assignments[name]
        milestone = design_milestones[name]
        require(
            f"Release assignment: OINK {version}" in source,
            f"{path.name} does not name consolidated OINK {version}",
        )
        require(
            f"Original design milestone: OINK {milestone}" in source,
            f"{path.name} does not preserve design milestone OINK {milestone}",
        )
        require("tests/fixtures/components/contract.json" in source, f"{path.name} does not name its companion")
        require("migration-components.md" in source and "migration-components.zh.md" in source, f"{path.name} lacks bilingual migration links")
        for literal in required[name]:
            require(literal in source, f"{path.name} lacks {literal}")


def main() -> int:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        require(isinstance(contract, dict), "contract must be a JSON object")
        validate_machine(contract)
        validate_docs(contract)
    except (OSError, json.JSONDecodeError, ContractError, TypeError, AttributeError) as exc:
        print(f"component contract check failed: {exc}", file=sys.stderr)
        return 1
    print("contracts are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
