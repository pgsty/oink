#!/usr/bin/env python3
"""Validate the v5 component layer that no other checker owns.

Covers Callout v2 (blockquote render hook), the data fences (echarts,
infographic, checksums), the `{{% steps %}}` container rules, the i18n keys
the new templates use, and the removal of the legacy shortcodes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
CANONICAL_TYPES = ("note", "tip", "important", "warning", "caution", "success", "danger", "question", "example", "quote")
REMOVED_SHORTCODES = (
    "blocks/cover", "blocks/feature", "blocks/lead", "blocks/link-down", "blocks/section",
    "pageinfo", "conditional-text", "_param", "alert", "details", "iframe",
    "tabpane", "code-group", "code-tab", "filetree", "filetree/folder", "filetree/file",
    "gallery", "gallery/image", "echarts", "infographic", "example", "imgproc", "readfile",
    "cardpane", "nav-card", "nav-cards", "doc-card", "doc-cards", "doc-carousel",
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_site(hugo: str, pages: dict[str, str], *, prefix: str, extra_files: dict[str, str] | None = None, config: str = "") -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory]:
    """Build a self-contained temp site against this theme; keep the temp handle alive."""
    temp = tempfile.TemporaryDirectory(prefix=prefix)
    site = Path(temp.name)
    for relative, body in pages.items():
        target = site / "content" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    for relative, body in (extra_files or {}).items():
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    (site / "hugo.yaml").write_text(
        "baseURL: https://example.org/\n"
        "title: Component fixture\n"
        f"theme: {ROOT.name}\n"
        "disableKinds: [sitemap, taxonomy, term]\n"
        "outputs:\n  home: [HTML]\n  section: [HTML, RSS]\n  page: [HTML, markdown, RSS]\n"
        "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n    parser:\n      wrapStandAloneImageWithinParagraph: false\n      attribute:\n        block: true\n"
        + config,
        encoding="utf-8",
    )
    layouts = site / "layouts/docs"
    layouts.mkdir(parents=True, exist_ok=True)
    # A scoped render (as content/rss-description.html does) re-runs the hooks with the RSS store flag.
    (layouts / "single.rss.xml").write_text('{{- .Store.Set "tdOutputFormat" "rss" -}}\n<fixture>{{ (.Markup "td-rss-check").Render.Content }}</fixture>\n', encoding="utf-8")
    destination = site / "public"
    result = subprocess.run(
        [hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    return result, destination, temp


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    callouts = (public / "docs/components/callouts/index.html").read_text()
    callouts_md = (public / "docs/components/callouts/index.md").read_text()
    fences = (public / "docs/components/data-fences/index.html").read_text()
    fences_md = (public / "docs/components/data-fences/index.md").read_text()
    print_page = (public / "_print/docs/index.html").read_text()

    for kind in CANONICAL_TYPES:
        require(f'<div class="td-callout td-callout--{kind}" role="note">' in callouts, f"callout fixture lacks the {kind} type", errors)
    for marker in (
        '<i class="td-callout__icon fa-solid fa-circle-info" aria-hidden="true"></i><span class="td-callout__label">Note</span>',
        '<span class="td-callout__label">Tip with a title</span>',
        # inline Markdown in the title and body
        "<code>code</code>, <em>emphasis</em>, <a href=\"/docs/\">links</a>",
        # folding
        '<details class="td-callout td-callout--note td-callout--collapsible">',
        '<details class="td-callout td-callout--tip td-callout--collapsible" open>',
        '<summary class="td-callout__title"><i class="td-callout__icon fa-solid fa-lightbulb" aria-hidden="true"></i><span class="td-callout__label">Expanded by default</span><i class="td-callout__marker fa-solid fa-chevron-down" aria-hidden="true"></i></summary>',
        '<details class="td-callout td-callout--details td-callout--collapsible">',
        '<details class="td-callout td-callout--details td-callout--collapsible" open>',
        # icon override
        '<i class="td-callout__icon fa-solid fa-rocket" aria-hidden="true"></i><span class="td-callout__label">Open details with an icon</span>',
        # nested callout and blocks inside a callout
        '<div class="td-callout td-callout--warning" role="note">',
        "<li>An ordered list</li>",
        # unknown type: plain blockquote, marker preserved
        "<blockquote>\n<p>[!FOO]- Unknown types stay visible</p>",
        # example callout with a fenced block
        'class="td-callout td-callout--example"',
    ):
        require(marker in callouts, f"callout fixture missing {marker}", errors)
    require(callouts.count('<details class="td-callout') == 4, "callout fixture folded a wrong number of callouts", errors)
    require("td-alert" not in callouts and "alert alert-" not in callouts, "legacy alert markup survived", errors)
    require("[!DETAILS]" not in callouts.split("Unknown type")[0], "a canonical callout leaked its marker", errors)
    for marker in ("> [!NOTE]", "> [!TIP] Tip with a title", "> [!NOTE]- Collapsed by default", "> [!TIP]+ Expanded by default", "> [!DETAILS] Neutral disclosure block", '{icon="fa-solid fa-rocket"}', "> [!FOO]- Unknown types stay visible", "> > [!NOTE]"):
        require(marker in callouts_md, f"callout Markdown output lost {marker}", errors)
    require("td-callout" not in callouts_md and '<details class="td-callout' not in callouts_md, "callout Markdown output contains HTML", errors)
    require("<details class=\"td-callout" not in print_page, "print output kept a collapsible <details> callout", errors)
    require('<div class="td-callout td-callout--note td-callout--collapsible" role="note" data-td-callout-collapsible>' in print_page, "print output lost the static expanded callout", errors)
    require("Click the title to expand." in print_page, "print output lost a folded callout body", errors)

    for marker in (
        'class="td-echarts td-max-width-on-larger-screens"',
        "data-td-echarts>",
        '<div data-td-echarts-canvas style="height: 320px"></div>',
        '<script type="application/json" data-td-echarts-options>{"series":[{"data":[12,9,4],"type":"bar"}],"tooltip":{"formatter":"$fn:bytesFormatter"},"xAxis":{"data":["Draft","Review","Published"],"type":"category"},"yAxis":{"type":"value"}}</script>',
        'class="td-asset-list"',
        "pig-1.7.0-1.aarch64.rpm",
        "SHA-256",
    ):
        require(marker in fences, f"data-fence fixture missing {marker}", errors)
    require(re.search(r'<script src="[^"]*js/main-[^"]+"', fences) is not None, "data-fence page lacks its bundle", errors)
    bundle = re.search(r'<script src="(/js/main-[^"]+)"', fences)
    if bundle:
        source = (public / bundle.group(1).lstrip("/")).read_text()
        require("tdEchartsFunctions" in source and "data-td-echarts" in source, "data-fence bundle lacks the ECharts runtime", errors)
    for marker in ('```echarts {height="320px"}', 'formatter: "$fn:bytesFormatter"', '```checksums {base="https://downloads.example.org/releases/stable" algo="sha256"}'):
        require(marker in fences_md, f"data-fence Markdown output lost {marker}", errors)
    require("data-td-echarts" not in fences_md and "td-asset-list" not in fences_md, "data-fence Markdown output contains HTML", errors)
    require('<pre class="td-echarts-source"><code class="language-echarts">' in print_page, "print output lost the ECharts source fallback", errors)
    require("data-td-echarts" not in print_page, "print output kept the ECharts runtime container", errors)
    return errors


def check_callout_matrix(hugo: str) -> list[str]:
    errors: list[str] = []
    result, destination, temp = build_site(
        hugo,
        {
            "docs/_index.md": "---\ntitle: Docs\n---\n",
            "docs/matrix.md": (
                "---\ntitle: Callout matrix\n---\n\n"
                "> [!NOTE] Site class and data attribute\n> body\n"
                '{class="site-note" data-fixture="kept"}\n\n'
                "> [!QUOTE]\n> quoted body\n\n"
                "> [!DETAILS]+ Open details\n> - item\n\n"
                "> [!WARNING]- Folded warning\n> hidden body\n\n"
                "> plain quote without a marker\n\n"
                "> [!tip] lowercase marker\n> still a tip\n"
            ),
        },
        prefix="oink-components-callouts-",
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"callout matrix failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/matrix/index.html").read_text()
        rss = (destination / "docs/matrix/index.xml").read_text()
        markdown = (destination / "docs/matrix/index.md").read_text()
        for marker in (
            '<div class="td-callout td-callout--note site-note" role="note" data-fixture="kept">',
            '<div class="td-callout td-callout--quote" role="note">',
            '<details class="td-callout td-callout--details td-callout--collapsible" open>',
            '<details class="td-callout td-callout--warning td-callout--collapsible">',
            "<blockquote>\n<p>plain quote without a marker</p>\n</blockquote>",
            '<div class="td-callout td-callout--tip" role="note">',
        ):
            require(marker in html, f"callout matrix HTML missing {marker}", errors)
        for marker in (
            '<div class="td-callout td-callout--warning td-callout--collapsible" role="note" data-td-callout-collapsible>',
            "hidden body",
            '<div class="td-callout td-callout--details td-callout--collapsible" role="note" data-td-callout-collapsible>',
        ):
            require(marker in rss, f"callout matrix RSS missing {marker}", errors)
        require("<details" not in rss and "<summary" not in rss, "RSS rendered an interactive <details> callout", errors)
        require('{class="site-note" data-fixture="kept"}' in markdown and "> [!WARNING]- Folded warning" in markdown, "callout matrix Markdown lost its source", errors)
    return errors


def check_data_fences(hugo: str) -> list[str]:
    errors: list[str] = []
    result, destination, temp = build_site(
        hugo,
        {
            "docs/_index.md": "---\ntitle: Docs\n---\n",
            "docs/fences.md": (
                "---\ntitle: Data fences\n---\n\n"
                "```echarts {height=\"240px\" theme=\"dark\" full=true class=\"site-chart\"}\n"
                '{"series": [{"type": "line", "data": [1, 2]}]}\n'
                "```\n\n"
                "```infographic {height=\"300px\"}\n"
                "infographic list-row-simple-horizontal-arrow\n"
                "```\n\n"
                "```mermaid\ngraph TD; A-->B;\n```\n"
            ),
            "blog/_index.md": "---\ntitle: Blog\n---\n",
            "blog/release/_index.md": "---\ntitle: Releases\n---\n",
        },
        prefix="oink-components-fences-",
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"data fence fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/fences/index.html").read_text()
        rss = (destination / "docs/fences/index.xml").read_text()
        markdown = (destination / "docs/fences/index.md").read_text()
        for marker in (
            'class="td-echarts site-chart"',
            'data-td-echarts data-theme="dark">',
            '<div data-td-echarts-canvas style="height: 240px"></div>',
            '<script type="application/json" data-td-echarts-options>{"series":[{"data":[1,2],"type":"line"}]}</script>',
            'class="td-infographic td-max-width-on-larger-screens"',
            'data-td-infographic data-height="300px">',
            '<script type="application/json" data-td-infographic-syntax>"infographic list-row-simple-horizontal-arrow"</script>',
            '<pre class="mermaid">',
        ):
            require(marker in html, f"data fence HTML missing {marker}", errors)
        require("td-max-width-on-larger-screens" not in html.split("td-infographic")[0].split("td-echarts")[-1], "echarts full=true still constrains the width", errors)
        for marker in ('<pre class="td-echarts-source"><code class="language-echarts">', '<pre class="td-infographic-source"><code class="language-infographic">'):
            require(marker in rss, f"data fence RSS lost {marker}", errors)
        require("data-td-echarts" not in rss and "data-td-infographic" not in rss, "RSS rendered a chart runtime container", errors)
        require('```echarts {height="240px" theme="dark" full=true class="site-chart"}' in markdown and "```infographic" in markdown, "data fence Markdown lost the source fences", errors)

    invalid = (
        ("echarts-invalid-yaml", '```echarts\n{"series": [\n```\n', "not valid JSON/YAML"),
        ("echarts-not-a-map", "```echarts\n- 1\n- 2\n```\n", "options must be a mapping"),
        ("echarts-empty", "```echarts\n\n```\n", "requires JSON or YAML options"),
        ("echarts-unknown-attr", '```echarts {width="10px"}\nseries: []\n```\n', "unknown attribute"),
        ("echarts-height", '```echarts {height="wide"}\nseries: []\n```\n', "not a safe CSS length"),
        ("infographic-empty", "```infographic\n\n```\n", "requires DSL content"),
        ("infographic-height", '```infographic {height="tall"}\nx\n```\n', "not auto or a safe CSS length"),
        ("checksums-no-base", "```checksums\n" + "a" * 64 + "  file.rpm\n```\n", "base is required unless the page has release front matter"),
        ("checksums-bad-algo", '```checksums {base="https://example.org/dl/" algo="crc"}\n' + "a" * 64 + "  file.rpm\n```\n", "algo must be md5, sha1, sha256, or sha512"),
        ("checksums-bad-group", '```checksums {base="https://example.org/dl/" group="yes"}\n' + "a" * 64 + "  file.rpm\n```\n", "group must be auto"),
        ("checksums-empty", '```checksums {base="https://example.org/dl/"}\n\n```\n', "requires checksum lines"),
        ("checksums-scheme", '```checksums {base="ftp://example.org/dl/"}\n' + "a" * 64 + "  file.rpm\n```\n", "must use http or https"),
    )
    for name, body, expected in invalid:
        result, destination, temp = build_site(hugo, {"docs/_index.md": "---\ntitle: Docs\n---\n", "docs/bad.md": f"---\ntitle: {name}\n---\n\n{body}"}, prefix=f"oink-components-{name}-")
        with temp:
            output = result.stdout + result.stderr
            require(result.returncode != 0, f"invalid data fence {name} unexpectedly built", errors)
            require(expected in output, f"invalid data fence {name} did not report {expected!r}: {output.strip()[-400:]}", errors)
    return errors


def check_steps_container(hugo: str) -> list[str]:
    """`{{% steps %}}` must render Markdown even when the body hugs the tags."""
    errors: list[str] = []
    result, destination, temp = build_site(
        hugo,
        {
            "docs/_index.md": "---\ntitle: Docs\n---\n",
            "docs/steps.md": (
                "---\ntitle: Steps container\n---\n\n"
                "{{% steps %}}\n"
                "### First step\n\n"
                "Body one.\n\n"
                "### Second step\n"
                "1. nested\n2. list\n{.steps}\n"
                "{{% /steps %}}\n\n"
                "1. native\n1. list\n{.steps}\n"
            ),
        },
        prefix="oink-components-steps-",
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"steps container fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/steps/index.html").read_text()
        markdown = (destination / "docs/steps/index.md").read_text()
        for marker in ('<div class="td-steps td-max-width-on-larger-screens">', '<h3 id="first-step">First step</h3>', '<h3 id="second-step">Second step</h3>', "<li>nested</li>", '<ol class="steps">\n<li>native</li>'):
            require(marker in html, f"steps container HTML missing {marker}", errors)
        require("{{%" not in html and "### First step" not in html, "steps container swallowed its Markdown body into the HTML block", errors)
        require(html.count('<ol class="steps">') == 2, "the list inside the steps container was not rendered", errors)
        require("### First step" in markdown and "td-steps" not in markdown and "<div" not in markdown, "steps Markdown output is not the plain body", errors)
    steps_source = (ROOT / "layouts/_shortcodes/steps.html").read_text()
    require("\n\n{{ .Inner }}\n\n" in steps_source, "steps.html does not surround .Inner with blank lines", errors)
    require('eq $format "markdown"' in steps_source, "steps.html lacks a Markdown output branch", errors)
    return errors


def check_removed_shortcodes(hugo: str) -> list[str]:
    errors: list[str] = []
    for name in REMOVED_SHORTCODES:
        require(not (ROOT / f"layouts/_shortcodes/{name}.html").exists(), f"layouts/_shortcodes/{name}.html must stay deleted", errors)
    for name in ("alert", "tabpane", "filetree", "readfile", "imgproc", "example", "doc-cards"):
        result, _destination, temp = build_site(hugo, {"docs/_index.md": "---\ntitle: Docs\n---\n", "docs/legacy.md": f"---\ntitle: Legacy {name}\n---\n\n{{{{< {name} >}}}}\n"}, prefix=f"oink-components-legacy-{name}-")
        with temp:
            output = result.stdout + result.stderr
            require(result.returncode != 0, f"legacy shortcode {name} unexpectedly built", errors)
            require(f'template for shortcode "{name}" not found' in output, f"legacy shortcode {name} did not fail as missing: {output.strip()[-300:]}", errors)
    return errors


def check_i18n() -> list[str]:
    errors: list[str] = []
    keys = ["ui_tabs_label", "ui_table_scroll", "book_example", "book_figure", "book_table", "book_equation", "details"] + list(CANONICAL_TYPES)
    for path in sorted((ROOT / "i18n").glob("*.yaml")):
        source = path.read_text(encoding="utf-8")
        for key in keys:
            require(re.search(rf"^{re.escape(key)}:", source, re.M) is not None, f"{path.name} lacks i18n key {key}", errors)
        for removed in ("ui_code_group_label", "ui_doc_carousel", "ui_carousel_previous", "ui_carousel_next"):
            require(re.search(rf"^{re.escape(removed)}:", source, re.M) is None, f"{path.name} keeps removed i18n key {removed}", errors)
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    hook = (ROOT / "layouts/_markup/render-blockquote-alert.html").read_text()
    for marker in ('"note" "tip" "important" "warning" "caution" "success" "danger" "question" "example" "quote" "details"', 'partial "content/attributes.html"', '(slice "icon")', "fa-(solid|regular|brands) fa-[a-z0-9-]+", 'eq $sign "-"', 'eq $sign "+"', 'eq $type "details"', "td-callout--collapsible", "<details", "<summary", 'role="note"', "data-td-callout-collapsible", 'i18n $type'):
        require(marker in hook, f"render-blockquote-alert.html lacks {marker}", errors)
    require("nb" not in re.sub(r'\{\{-?\s*/\*.*?\*/\s*-?\}\}', "", hook, flags=re.S), "the nb callout special case survived", errors)
    for name, markers in {
        "render-codeblock-echarts.html": ('partial "content/attributes.html"', '(slice "height" "theme" "full")', "transform.Unmarshal", "reflect.IsMap", "td-echarts-source", 'Store.Set "hasEcharts" true'),
        "render-codeblock-infographic.html": ('(slice "height" "full")', "td-infographic-source", 'Store.Set "hasInfographic" true'),
        "render-codeblock-checksums.html": ('(slice "base" "algo" "group")', 'partial "release/assets-parse.html"', 'partial "release/assets-table.html"', 'partial "release/assets-markdown.html"', "base is required unless the page has release front matter"),
    }.items():
        source = (ROOT / "layouts/_markup" / name).read_text()
        for marker in markers:
            require(marker in source, f"{name} lacks {marker}", errors)
    runtime = (ROOT / "assets/js/content-components.js").read_text()
    require("$fn:" in runtime and "tdEchartsFunctions" in runtime, "ECharts callback bridge ($fn: / tdEchartsFunctions) changed", errors)
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    require("or $hasAsciinema $hasEcharts $hasInfographic" in scripts, "scripts.html no longer loads content-components.js for data fences", errors)
    styles = (ROOT / "assets/scss/td/_alerts.scss").read_text()
    for marker in (".td-callout", "&--collapsible", "@media print", "forced-colors", "prefers-reduced-motion"):
        require(marker in styles, f"callout styles lack {marker}", errors)
    for kind in CANONICAL_TYPES:
        require(f"--{kind}" in styles, f"callout styles lack the {kind} accent", errors)
    config = (ROOT / "hugo.yaml").read_text()
    require("oink:" not in config, "theme hugo.yaml declares a params.oink tree", errors)
    for removed in ("filetree", "gallery", "carousel", "tabpane", "readfile", "imgproc"):
        require(removed not in config.lower(), f"theme hugo.yaml still configures the removed {removed} feature", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, default=EXAMPLE / "public")
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors = (
        check_outputs(args.public)
        + check_callout_matrix(args.hugo)
        + check_data_fences(args.hugo)
        + check_steps_container(args.hugo)
        + check_removed_shortcodes(args.hugo)
        + check_i18n()
        + check_template_contracts()
    )
    if errors:
        print("Component checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Component checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
