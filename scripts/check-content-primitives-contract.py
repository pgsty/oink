#!/usr/bin/env python3
"""Keep the everyday content-primitives contract complete and explicit."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "content-primitives.md"

REQUIRED_HEADINGS = (
    "## 1. Decision",
    "## 2. Shared authoring contract",
    "### 2.1 Notation and nesting",
    "### 2.2 Parameter validation",
    "### 2.3 Escaping and rendered content",
    "### 2.4 URL policy",
    "### 2.5 Output-format state",
    "### 2.6 Page Store, repeated rendering, and IDs",
    "### 2.7 Runtime loading",
    "### 2.8 CSS and accessibility",
    "### 2.9 Visible strings, aliases, and deprecation",
    "## 3. Public component APIs",
    "### 3.1 Badge",
    "### 3.2 Kbd",
    "### 3.3 Fields and Field",
    "### 3.4 FileTree",
    "### 3.5 Shared images and the image shortcode",
    "### 3.6 Image Zoom",
    "### 3.7 Gallery",
    "### 3.8 Release Assets",
    "### 3.9 Tables and full-width tables",
    "### 3.10 Numbered Figure, Table, and Equation",
    "### 3.11 Cross references and Book indexes",
    "### 3.12 Callouts",
    "### 3.13 Tabs",
    "### 3.14 Steps",
    "### 3.15 Cards",
    "### 3.16 Data fences",
    "### 3.17 Include, Param, and Comment",
    "## 4. Output matrix",
    "## 5. Verification contract",
    "## 6. Contract changes",
)

REQUIRED_LITERALS = (
    "Compatibility floor: Hugo Extended 0.160.1",
    "Contract version: 2",
    "`neutral`, `info`, `success`, `warning`, `danger`",
    '{{< kbd "Ctrl" "K" >}}',
    '| `required` | no | strict boolean | `false` |',
    "{.fields caption=",
    "first column is the field name",
    "```filetree {title=",
    "`--td-filetree-name-col`",
    "{.gallery}",
    "{.steps}",
    "{.cards}",
    "{.matrix}",
    "{.full-width}",
    "> [!TIP]",
    "> [!DETAILS]",
    "{icon=\"fa-solid fa-rocket\"}",
    "wrapStandAloneImageWithinParagraph: false",
    "`{{% steps %}}` is the only `{{% %}}` shortcode",
    "content/render-block.html",
    "`tdRenderScope`",
    "`hasTabs`",
    "td-tabs:v1:<group>",
    "#<group>-<value>",
    "data-td-tabs-ready",
    # The `image` shortcode is retired; its processing parameters live on the
    # block-image attribute line, and the contract must still pin their grammar.
    "| `command` | yes | `Fit`, `Resize`, `Fill`, `Crop` | none |",
    "The `image` shortcode is retired.",
    "A standalone public Icon shortcode is deferred.",
    "`params.ui.image_zoom.enable`",
    "The Markdown output must contain no component classes",
    "Their Markdown fallback retains source",
    "remains for at least one complete minor release",
    "`<hex><two spaces><name>`",
    "`src` and inner checksum lines are mutually exclusive.",
    "```checksums {base=",
    "`td-table-scroll--full`",
    "`ui_table_scroll`",
    "first column `<th scope=\"row\">`",
    "`[0-9A-Za-z.-]+`",
    "`src/id/caption/title/class/link/alt/width/height`",
    "{{< eq >}}X \\approx \\frac{C}{R+Z}{{< /eq >}}",
    "{{< eg num=",
    "`{{< book-toc depth=1..3 >}}`",
    "`{{< book-figures >}}` (figures only), `{{< book-tables >}}`",
    "`scripts/check-book.py` rejects empty alternatives",
    "`style`, any `on*` handler, `srcdoc`, and every other unknown key fail the",
    "$fn:<name>",
    "window.tdEchartsFunctions",
    "{{< include file=",
)

EXPECTED_RUNTIMES = {
    "Badge": "none",
    "Kbd": "none",
    "Fields": "none",
    "FileTree": "one local split runtime, only with comments",
    "Shared image": "none",
    "Image Zoom": "one opt-in local dialog runtime",
    "Gallery": "reuses Image Zoom only",
    "Release Assets": "one opt-in local copy runtime",
    "Table": "none",
    "Eq escape": "none",
    "Fig/Tbl/Eq/Eg": "none",
    "Xref/Book index": "none",
    "Callout": "none",
    "Tabs": "one opt-in local tabs runtime",
    "Steps": "none",
    "Cards": "none",
    "Data fences": "opt-in local chart runtimes",
    "Include/Param": "none",
}


def table_rows(source: str, heading: str) -> dict[str, list[str]]:
    start = source.find(heading)
    if start < 0:
        return {}
    end = source.find("\n## ", start + len(heading))
    section = source[start:] if end < 0 else source[start:end]
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"Component", "---"}:
            continue
        rows[cells[0]] = cells
    return rows


def main() -> int:
    errors: list[str] = []
    source = CONTRACT.read_text()

    if not source.startswith("# Everyday content primitives contract\n"):
        errors.append("contract title is missing or changed")
    if "Status: frozen for implementation" not in source:
        errors.append("contract status is not frozen for implementation")

    headings = set(re.findall(r"^#{2,3} .+$", source, re.MULTILINE))
    for heading in REQUIRED_HEADINGS:
        if heading not in headings:
            errors.append(f"missing required heading: {heading}")

    for literal in REQUIRED_LITERALS:
        if literal not in source:
            errors.append(f"missing frozen contract value: {literal}")

    matrix = table_rows(source, "## 4. Output matrix")
    for component, runtime in EXPECTED_RUNTIMES.items():
        row = matrix.get(component)
        if row is None:
            errors.append(f"output matrix is missing {component}")
            continue
        if len(row) != 7:
            errors.append(
                f"output matrix row {component} has {len(row)} cells, expected 7"
            )
            continue
        if row[-1] != runtime:
            errors.append(
                f"output matrix runtime for {component} is {row[-1]!r}, "
                f"expected {runtime!r}"
            )

    if re.search(r"^### 3\.\d+ (?:Public )?Icon$", source, re.MULTILINE):
        errors.append("standalone Icon must remain deferred in the MVP contract")

    issue_links = set(re.findall(r"https://github\.com/pgsty/oink/issues/(\d+)", source))
    for number in ("3", "4", "8"):
        if number not in issue_links:
            errors.append(f"contract is missing issue link #{number}")

    if errors:
        print("Content primitive contract check failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print("Content primitive contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
