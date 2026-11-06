#!/usr/bin/env python3
"""Validate the v5 component layer that no other checker owns.

Covers Callout v2 (blockquote render hook), the data fences (echarts,
infographic, checksums), the `{{% steps %}}` container rules, the i18n keys
the new templates use, and the removal of the legacy shortcodes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import tempfile

from runtime_assets import combined_source, referenced_chunks
from test_site import build_fixture_public, run_hugo_process


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"
CANONICAL_TYPES = ("note", "tip", "important", "warning", "caution", "success", "danger", "question", "example", "quote")
REMOVED_SHORTCODES = (
    "blocks/cover", "blocks/feature", "blocks/lead", "blocks/link-down", "blocks/section",
    "td-page-notice", "conditional-text", "_param", "alert", "details", "iframe",
    "tabpane", "code-group", "code-tab", "filetree", "filetree/folder", "filetree/file",
    "gallery", "gallery/image", "echarts", "infographic", "example", "imgproc", "readfile",
    "cardpane", "nav-card", "nav-cards", "doc-card", "doc-cards", "doc-carousel",
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_site(hugo: str, pages: dict[str, str], *, prefix: str, base_url: str = "https://example.org/", extra_files: dict[str, str] | None = None, config: str = "") -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory]:
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
        f"baseURL: {base_url}\n"
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
    command = [hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn"]
    result = run_hugo_process(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return result, destination, temp


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    callouts = (public / "fixtures/callouts/index.html").read_text()
    callouts_md = (public / "fixtures/callouts/index.md").read_text()
    fences = (public / "fixtures/data-fences/index.html").read_text()
    fences_md = (public / "fixtures/data-fences/index.md").read_text()
    print_page = (public / "_print/fixtures/index.html").read_text()

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
    require(bool(referenced_chunks(public, fences)), "data-fence page lacks runtime chunks", errors)
    source = combined_source(public, fences)
    require("OinkEchartsFunctions" in source and "data-td-echarts" in source, "data-fence chunks lack the ECharts runtime", errors)
    for marker in ('```echarts {height="320px"}', 'formatter: "$fn:bytesFormatter"', '```checksums {base="https://downloads.example.org/releases/stable" algo="sha256"}'):
        require(marker in fences_md, f"data-fence Markdown output lost {marker}", errors)
    require("data-td-echarts" not in fences_md and "td-asset-list" not in fences_md, "data-fence Markdown output contains HTML", errors)
    require('<pre class="td-echarts-source"><code class="language-echarts">' in print_page, "print output lost the ECharts source fallback", errors)
    require("data-td-echarts" not in print_page, "print output kept the ECharts runtime container", errors)
    # Print never reached a Mermaid runtime -- every first-party chunk there is
    # gated on interactive output -- so it prints the source like its siblings.
    require('<pre class="td-mermaid-source"><code class="language-mermaid">' in print_page, "print output lost the Mermaid source fallback", errors)
    require("data-td-diagram" not in print_page, "print output kept the Mermaid runtime container", errors)
    require('<figure class="td-diagram td-diagram--mermaid" data-td-diagram>' in fences, "data-fence fixture lost the Mermaid figure", errors)
    require("mermaid" in source, "data-fence chunks lack the Mermaid runtime", errors)
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
                "> [!tip] lowercase marker\n> still a tip\n\n"
                "> [!MYSTERY] Unknown attributes\n> body\n"
                '{data-fixture="unknown-callout" aria-label="Unknown callout"}\n'
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
            '<blockquote aria-label="Unknown callout" data-fixture="unknown-callout">',
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
                "```echarts {height=\"240px\" theme=\"dark\" full=true class=\"site-chart\" data-fixture=\"chart\" aria-label=\"Chart\"}\n"
                '{"series": [{"type": "line", "data": [1, 2]}]}\n'
                "```\n\n"
                "```infographic {height=\"300px\" data-fixture=\"infographic\" aria-label=\"Infographic\"}\n"
                "infographic list-row-simple-horizontal-arrow\n"
                "```\n\n"
                '```checksums {base="https://example.org/downloads" class="site-assets" data-fixture="assets" aria-label="Checksums"}\n'
                + "a" * 64 + "  package.rpm\n"
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
            'data-td-echarts data-theme="dark" aria-label="Chart" data-fixture="chart">',
            '<div data-td-echarts-canvas style="height: 240px"></div>',
            '<script type="application/json" data-td-echarts-options>{"series":[{"data":[1,2],"type":"line"}]}</script>',
            'class="td-infographic td-max-width-on-larger-screens"',
            'data-td-infographic data-td-height="300px" aria-label="Infographic" data-fixture="infographic">',
            '<script type="application/json" data-td-infographic-syntax>"infographic list-row-simple-horizontal-arrow"</script>',
            'class="td-asset-list site-assets" data-td-asset-list aria-label="Checksums" data-fixture="assets">',
            '<figure class="td-diagram td-diagram--mermaid" data-td-diagram>',
            '<div class="td-diagram__stage" data-td-diagram-stage></div>',
            '<pre class="td-mermaid-source" tabindex="0"><code class="language-mermaid">graph TD; A--&gt;B;</code></pre>',
            'data-td-mermaid-config',
            'data-td-diagram-source-toggle',
            'data-td-diagram-download',
            '<script type="application/json" data-td-diagram-source>"graph TD; A--\\u003eB;"</script>',
            'data-td-diagram-expand aria-haspopup="dialog"',
        ):
            require(marker in html, f"data fence HTML missing {marker}", errors)
        require(
            '<pre class="mermaid">' not in html,
            "mermaid still hands Mermaid a <pre> to consume in place",
            errors,
        )
        require("td-max-width-on-larger-screens" not in html.split("td-infographic")[0].split("td-echarts")[-1], "echarts full=true still constrains the width", errors)
        for marker in (
            '<pre class="td-echarts-source"><code class="language-echarts">',
            '<pre class="td-infographic-source"><code class="language-infographic">',
            '<pre class="td-mermaid-source"><code class="language-mermaid">',
        ):
            require(marker in rss, f"data fence RSS lost {marker}", errors)
        require(
            "data-td-echarts" not in rss
            and "data-td-infographic" not in rss
            and "data-td-diagram" not in rss,
            "RSS rendered a chart runtime container",
            errors,
        )
        require('```echarts {height="240px" theme="dark" full=true class="site-chart" data-fixture="chart" aria-label="Chart"}' in markdown and "```infographic" in markdown, "data fence Markdown lost the source fences", errors)

    invalid = (
        ("echarts-invalid-yaml", '```echarts\n{"series": [\n```\n', "not valid JSON/YAML"),
        # A JSON array, not a YAML sequence: Hugo cannot sniff a bare `- x`
        # list and reports it as an unknown format, which never reaches the
        # mapping check this case exists to exercise.
        ("echarts-not-a-map", "```echarts\n[1, 2]\n```\n", "options must be a mapping"),
        ("echarts-unparseable", "```echarts\n- 1\n- 2\n```\n", "options are not valid JSON/YAML"),
        ("echarts-empty", "```echarts\n\n```\n", "requires JSON or YAML options"),
        ("echarts-unknown-attr", '```echarts {width="10px"}\nseries: []\n```\n', "unknown attribute"),
        ("echarts-height", '```echarts {height="wide"}\nseries: []\n```\n', "not a safe CSS length"),
        ("echarts-full", '```echarts {full="yes"}\nseries: []\n```\n', "full must be true or false"),
        ("infographic-empty", "```infographic\n\n```\n", "requires DSL content"),
        # Both fences validate the length through `validate.html` now, so they
        # report it the same way; the message names `auto` as the fallback.
        ("infographic-height", '```infographic {height="tall"}\nx\n```\n', 'is not a safe CSS length'),
        ("infographic-height-fallback", '```infographic {height="tall"}\nx\n```\n', 'using "auto"'),
        ("infographic-full", '```infographic {full="yes"}\nx\n```\n', "full must be true or false"),
        ("checksums-no-base", "```checksums\n" + "a" * 64 + "  file.rpm\n```\n", "base is required unless the page has release_url front matter"),
        ("checksums-bad-algo", '```checksums {base="https://example.org/dl/" algo="crc"}\n' + "a" * 64 + "  file.rpm\n```\n", "algo must be md5, sha1, sha256, or sha512"),
        ("checksums-bad-group", '```checksums {base="https://example.org/dl/" group="yes"}\n' + "a" * 64 + "  file.rpm\n```\n", "group must be auto"),
        ("checksums-empty", '```checksums {base="https://example.org/dl/"}\n\n```\n', "requires checksum lines"),
        ("checksums-scheme", '```checksums {base="ftp://example.org/dl/"}\n' + "a" * 64 + "  file.rpm\n```\n", "must use http or https"),
    )
    for name, body, expected in invalid:
        result, destination, temp = build_site(hugo, {"docs/_index.md": "---\ntitle: Docs\n---\n", "docs/bad.md": f"---\ntitle: {name}\n---\n\n{body}"}, prefix=f"oink-components-{name}-")
        with temp:
            output = result.stdout + result.stderr
            require(result.returncode == 0, f"invalid data fence {name} stopped the ordinary build: {output.strip()[-400:]}", errors)
            require(expected in output, f"invalid data fence {name} did not report {expected!r}: {output.strip()[-400:]}", errors)
            require((destination / "docs/bad/index.html").is_file(), f"invalid data fence {name} emitted no safe page output", errors)
    return errors


def check_presentation_variants(hugo: str) -> list[str]:
    """Opt-in presentation must preserve content, list semantics, and fallback."""
    errors: list[str] = []
    body = '''---
title: Presentation
---

- [Native resource](/docs/)
{.cards .td-cards-list}

3. Native third step
1. Native fourth step
{.steps .td-steps-compact}

{{< cards variant="list" >}}
{{< card title="Full resource" link="/docs/" >}}Full description.{{< /card >}}
{{< /cards >}}

{{% steps variant="compact" %}}
### Compact heading {#compact-heading}

Compact body.
{{% /steps %}}

{{< cards variant=42 >}}
{{< card title="Fallback resource" >}}Fallback card body.{{< /card >}}
{{< /cards >}}

{{< cards >}}
{{< card "Positional title" >}}Positional card body.{{< /card >}}
{{< card title="Kept sibling" >}}Valid sibling body.{{< /card >}}
{{< /cards >}}

{{% steps variant="invalid" %}}
### Fallback heading {#fallback-heading}

Fallback step body.
{{% /steps %}}
'''
    result, destination, temp = build_site(hugo, {
        "docs/_index.md": "---\ntitle: Docs\n---\n",
        "docs/presentation.md": body,
    }, prefix="oink-component-presentation-")
    with temp:
        output = result.stdout + result.stderr
        require(result.returncode == 0, f"presentation build failed: {output}", errors)
        if result.returncode:
            return errors
        for diagnostic in ("variant must be list", "variant must be compact", "accepts named parameters only"):
            require(diagnostic in output, f"missing {diagnostic}", errors)
        html = (destination / "docs/presentation/index.html").read_text()
        for marker in ('<ul class="cards td-cards-list">', '<ol start="3" class="steps td-steps-compact">',
                       'class="td-content-cards td-content-cards--auto td-cards-list"',
                       'class="td-steps td-max-width-on-larger-screens td-steps-compact"',
                       'class="td-content-cards td-content-cards--auto"',
                       'class="td-steps td-max-width-on-larger-screens"',
                       '<h3 id="compact-heading">', '<h3 id="fallback-heading">'):
            require(marker in html, f"presentation lost {marker}", errors)
        for filename in ("index.html", "index.md", "index.xml"):
            rendered = (destination / f"docs/presentation/{filename}").read_text()
            for text in ("Native resource", "Native third step", "Full description.", "Compact body.", "Fallback card body.", "Valid sibling body.", "Fallback step body."):
                require(text in rendered, f"{filename} lost {text}", errors)
            require("Positional card body." not in rendered,
                    f"{filename} did not omit the invalid card", errors)
        markdown = (destination / "docs/presentation/index.md").read_text()
        require('<div' not in markdown and '{{<' not in markdown and '{{%' not in markdown,
                "presentation wrappers leaked into Markdown", errors)
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
        for marker in ('<div class="td-steps td-max-width-on-larger-screens">', '<h3 id="first-step">First step<a class="td-heading-self-link"', '<h3 id="second-step">Second step<a class="td-heading-self-link"', "<li>nested</li>", '<ol class="steps">\n<li>native</li>'):
            require(marker in html, f"steps container HTML missing {marker}", errors)
        require("{{%" not in html and "### First step" not in html, "steps container swallowed its Markdown body into the HTML block", errors)
        require(html.count('<ol class="steps">') == 2, "the list inside the steps container was not rendered", errors)
        require("### First step" in markdown and "td-steps" not in markdown and "<div" not in markdown, "steps Markdown output is not the plain body", errors)
    steps_source = (ROOT / "layouts/_shortcodes/steps.html").read_text()
    require("\n\n{{ .Inner }}\n\n" in steps_source, "steps.html does not surround .Inner with blank lines", errors)
    require('eq $format "markdown"' in steps_source, "steps.html lacks a Markdown output branch", errors)
    return errors


def check_openapi(hugo: str) -> list[str]:
    """Multiple Swagger/ReDoc instances stay isolated and reject old raw options."""
    errors: list[str] = []
    result, destination, temp = build_site(
        hugo,
        {
            "docs/_index.md": "---\ntitle: Docs\n---\n",
            "docs/openapi.md": (
                "---\ntitle: OpenAPI\n---\n\n"
                '{{< swagger src="/spec-a.yaml" >}}\n'
                '{{< swagger src="/spec-b.yaml" >}}\n'
                '{{< redoc "openapi/spec.yaml" >}}\n'
                '{{< redoc "/openapi/spec.yaml" >}}\n'
                '{{< redoc "https://spec.example.org/openapi.yaml" >}}\n'
            ),
        },
        prefix="oink-components-openapi-",
        extra_files={"static/openapi/spec.yaml": "openapi: 3.1.0\n"},
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"OpenAPI fixture failed to build: {result.stdout}{result.stderr}")
        else:
            html = (destination / "docs/openapi/index.html").read_text()
            ids = re.findall(r'id="(td-(?:swagger|redoc)-[^"]+)"', html)
            require(len(ids) == 5 and len(set(ids)) == 5, f"OpenAPI instance IDs are not unique: {ids}", errors)
            require("window.onload" not in html and "window.ui" not in html, "Swagger replaces global page state", errors)
            require("SwaggerUIBundle({" not in html,
                    "Swagger still initializes through an inline shortcode script instead of the chunk", errors)
            require(html.count('data-td-spec-url="/spec-a.yaml"') == 1 and html.count('data-td-spec-url="/spec-b.yaml"') == 1,
                    "each Swagger container does not carry its own spec URL", errors)
            require(len(re.findall(r'src="[^"]*js/chunks/swagger-init[^"]*"', html)) == 1,
                    "the Swagger initializer chunk is not loaded exactly once", errors)
            chunks = sorted(destination.glob("js/chunks/swagger-init*.js"))
            require(bool(chunks) and re.search(r"validatorUrl\s*:\s*null", chunks[0].read_text()) is not None,
                    "the Swagger initializer chunk does not pin validatorUrl to null", errors)
            require(".td-redoc input" not in html,
                    "the ReDoc overrides are still inlined in the shortcode instead of the standalone stylesheet", errors)
            require(re.search(r'href="[^"]*redoc[^"]*\.css[^"]*"', html) is not None,
                    "the ReDoc standalone stylesheet is not loaded beside the runtime", errors)
            require(html.count('spec-url="https://example.org/openapi/spec.yaml"') == 2,
                    "leading and non-leading Redoc paths differ at the site root", errors)
            require('spec-url="https://spec.example.org/openapi.yaml"' in html,
                    "Redoc rewrote a valid remote specification URL", errors)

    subpath_page = (
        "---\ntitle: Redoc paths\noutputs: [HTML, print, markdown, RSS]\n---\n\n"
        '{{< redoc "openapi/spec.yaml" >}}\n\n'
        '{{< redoc "/openapi/spec.yaml" >}}\n'
    )
    result, destination, temp = build_site(
        hugo,
        {"docs/_index.md": "---\ntitle: Docs\n---\n", "docs/redoc.md": subpath_page},
        prefix="oink-components-redoc-subpath-",
        base_url="https://example.org/preview/",
        extra_files={"static/openapi/spec.yaml": "openapi: 3.1.0\n"},
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"Redoc subpath fixture failed to build: {result.stdout}{result.stderr}")
        else:
            expected = "https://example.org/preview/openapi/spec.yaml"
            outputs = {
                "HTML": (destination / "docs/redoc/index.html").read_text(),
                "Print": (destination / "_print/docs/redoc/index.html").read_text(),
                "Markdown": (destination / "docs/redoc/index.md").read_text(),
                "RSS": (destination / "docs/redoc/index.xml").read_text(),
            }
            require(outputs["HTML"].count(f'spec-url="{expected}"') == 2,
                    "leading and non-leading Redoc paths differ under a subpath", errors)
            require(outputs["Print"].count(f'href="{expected}"') == 2,
                    "Redoc Print fallback lost the normalized subpath URL", errors)
            require(outputs["Markdown"].count(f"]({expected})") == 2,
                    "Redoc Markdown fallback lost the normalized subpath URL", errors)
            require(outputs["RSS"].count(f'href="{expected}"') == 2,
                    "Redoc RSS fallback lost the normalized subpath URL", errors)
            for name in ("Print", "Markdown", "RSS"):
                require("<redoc" not in outputs[name] and "redoc.standalone" not in outputs[name],
                        f"Redoc {name} fallback regained an interactive runtime", errors)
            require((destination / "openapi/spec.yaml").is_file(),
                    "the static-root Redoc specification was not published", errors)

    redoc_source = (ROOT / "layouts/_shortcodes/redoc.html").read_text()
    require("fileExists" not in redoc_source, "Redoc retained its ineffective content-file branch", errors)
    require("urls.JoinPath" in redoc_source, "Redoc does not join local paths with the site base URL", errors)

    invalid = (
        ("swagger-missing-src", "{{< swagger >}}", "requires named parameter src"),
        ("swagger-unsafe-src", '{{< swagger src="javascript:alert(1)" >}}', "unsupported src scheme"),
        ("redoc-extra-options", '{{< redoc "/spec.yaml" `theme="dark"` >}}', "requires exactly one positional"),
        ("redoc-unsafe-spec", '{{< redoc "javascript:alert(1)" >}}', "unsupported spec scheme"),
        ("asciinema-bad-speed", '{{< asciinema file="x.cast" speed="fast" >}}', "speed must be a positive number"),
        ("asciinema-bad-cols", '{{< asciinema file="x.cast" cols="1.5" >}}', "cols must be a positive whole number"),
        ("asciinema-bad-marker", '{{< asciinema file="x.cast" markers="abc:Nope" >}}', "needs a numeric time"),
        ("asciinema-unsafe-file", '{{< asciinema file="javascript:alert(1)" >}}', "unsupported file scheme"),
    )
    for name, body, expected in invalid:
        result, destination, temp = build_site(
            hugo,
            {"docs/_index.md": "---\ntitle: Docs\n---\n", "docs/bad.md": f"---\ntitle: {name}\n---\n\n{body}\n"},
            prefix=f"oink-components-{name}-",
        )
        with temp:
            output = result.stdout + result.stderr
            require(result.returncode == 0, f"invalid OpenAPI case {name} stopped the ordinary build: {output[-400:]}", errors)
            require(expected in output, f"invalid OpenAPI case {name} did not report {expected!r}: {output[-400:]}", errors)
            require((destination / "docs/bad/index.html").is_file(), f"invalid OpenAPI case {name} emitted no safe page output", errors)
    return errors


def check_media_output_states(hugo: str) -> list[str]:
    """asciinema/redoc/swagger are interactive-HTML-only: print gets a static
    link and loads no runtime, Markdown and RSS get a pure link line with no
    component markup, and every runtime still loads in the HTML output."""
    errors: list[str] = []
    page = (
        "---\ntitle: Media states\noutputs: [HTML, print, markdown, RSS]\n---\n\n"
        '{{< asciinema file="images/install.cast" title="Walkthrough" speed="2" markers="10:Boot" >}}\n\n'
        '{{< redoc "/spec-a.yaml" >}}\n\n'
        '{{< swagger src="/spec-a.yaml" >}}\n'
    )
    result, destination, temp = build_site(
        hugo,
        {"docs/_index.md": "---\ntitle: Docs\n---\n", "docs/media.md": page},
        prefix="oink-components-media-states-",
        extra_files={"static/images/install.cast": "{}\n"},
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"media states fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/media/index.html").read_text()
        markdown = (destination / "docs/media/index.md").read_text()
        printed = (destination / "_print/docs/media/index.html").read_text()
        rss = (destination / "docs/media/index.xml").read_text()
        require("data-td-asciinema" in html and "data-td-swagger" in html and "<redoc" in html,
                "the HTML output lost its interactive components", errors)
        require("asciinema-player" in html and "swagger-ui-bundle" in html and "redoc.standalone" in html,
                "the HTML output does not load the three runtimes", errors)
        for name, text in (("markdown", markdown), ("rss", rss)):
            require("<script" not in text and 'class="td-' not in text
                    and "data-td-asciinema" not in text and "<redoc" not in text,
                    f"the {name} output still carries component markup", errors)
        require("[Walkthrough](/images/install.cast)" in markdown,
                "the markdown output lost the asciinema link line", errors)
        for runtime in ("asciinema-player", "swagger-ui-bundle", "redoc.standalone", "swagger-init"):
            require(runtime not in printed, f"the print output still loads {runtime}", errors)
        require("data-td-asciinema" not in printed and "data-td-swagger" not in printed and "<redoc" not in printed,
                "the print output still renders interactive containers", errors)
        require(printed.count('-print"') >= 3 and 'href="/spec-a.yaml"' in printed,
                "the print output lacks the static fallback links", errors)
    return errors


def check_empty_tabs(hugo: str) -> list[str]:
    errors: list[str] = []
    pages = {
        "docs/_index.md": "---\ntitle: Docs\n---\n",
        "docs/empty.md": '---\ntitle: Empty tabs\noutputs: [HTML, PRINT, MARKDOWN, RSS]\n---\n\nBefore.\n\n{{< tabs >}}{{< /tabs >}}\n\nAfter.\n',
    }
    result, destination, temp = build_site(
        hugo, pages, prefix="oink-empty-tabs-",
    )
    with temp:
        output = result.stdout + result.stderr
        require('requires at least one tab child' in output, "empty tabs lost its diagnostic", errors)
        require(result.returncode == 0, "empty tabs violated the warning policy", errors)
        for relative in ('docs/empty/index.html', '_print/docs/empty/index.html',
                         'docs/empty/index.md', 'docs/empty/index.xml'):
            rendered = (destination / relative).read_text()
            require('Before.' in rendered and 'After.' in rendered,
                    f"{relative} lost content around empty tabs", errors)
            require('td-tabs' not in rendered and 'role="tablist"' not in rendered,
                    f"{relative} rendered an empty tabs container", errors)
    return errors


def check_print_tab_namespaces(hugo: str) -> list[str]:
    """Grouped tabs stay page-local in HTML/plain Print and unique in aggregates."""
    class Anchors(HTMLParser):
        def __init__(self, source: str):
            super().__init__(convert_charrefs=True)
            self.ids: list[str] = []
            self.links: list[str] = []
            self.tab_links: list[dict[str, str]] = []
            self.feed(source)

        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            if attrs.get("id"):
                self.ids.append(attrs["id"])
            if tag == "a" and attrs.get("href"):
                self.links.append(attrs["href"])
                if attrs.get("data-test-tab-link"):
                    self.tab_links.append(attrs)

    errors: list[str] = []
    tabs = '''{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}Example.{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
Syntax.

{{< tabs group="platform" >}}
{{< tab label="Unix" value="unix" >}}Unix syntax.{{< /tab >}}
{{< tab label="Windows" value="windows" >}}Windows syntax.{{< /tab >}}
{{< /tabs >}}
{{< /tab >}}
{{< /tabs >}}'''
    pages: dict[str, str] = {}
    for lang in ("", ".zh"):
        for kind in ("docs", "book"):
            pages[f"{kind}/_index{lang}.md"] = (
                f"---\ntitle: {kind}\ntype: {kind}\noutputs: [HTML, PRINT]\n---\n"
            )
            for chapter in ("a", "b"):
                pages[f"{kind}/{chapter}{lang}.md"] = (
                    f"---\ntitle: Chapter {chapter}\ntype: {kind}\noutputs: [HTML, PRINT]\n---\n"
                    '<a href="#example-syntax-syntax">Own syntax</a>\n\n'
                    '<a data-test-tab-link="single" title="fake href=\'#example-syntax-syntax\'" href=\'#example-syntax-syntax\'>Single quote</a>\n\n'
                    '<a data-test-tab-link="bare" title="fake href=#example-syntax-syntax > text" HREF = #example-syntax-syntax>Bare href</a>\n\n'
                    '<a data-test-tab-link="double" title=\'fake href="#example-syntax-syntax"\' href="#example-syntax-syntax">Double quote</a>\n\n'
                    '<a data-test-tab-link="entity" title="encoded fragment" href=\'&#35;example-syntax-syntax\'>Entity fragment</a>\n\n'
                    f'<a data-test-tab-link="self" title="same page" href=\'__BASE__{"zh/" if lang else ""}{kind}/{chapter}/#example-syntax-syntax\'>Same page</a>\n\n'
                    "[Own second example](#example-syntax-2-example)\n\n"
                    "[Other chapter](../a/#example-syntax-syntax)\n\n"
                    f'<span id="authored-{kind}-{chapter}"></span>\n\n'
                    f"{tabs}\n\n{tabs}\n"
                )
    for base_url in ("https://example.org/", "https://example.org/manual/"):
        base_path = "/manual/" if base_url.endswith("/manual/") else "/"
        result, destination, temp = build_site(
            hugo, {name: body.replace("__BASE__", base_path) for name, body in pages.items()},
            prefix="oink-print-tabs-", base_url=base_url,
            config="languages:\n  en:\n    weight: 1\n  zh:\n    weight: 2\n    locale: zh-CN\n",
        )
        try:
            require(result.returncode == 0, f"Print tabs fixture failed: {result.stdout}{result.stderr}", errors)
            if result.returncode != 0:
                continue
            for language in ("", "zh/"):
                for kind in ("docs", "book"):
                    expected_ids = {"example-syntax-example", "example-syntax-syntax",
                                    "example-syntax-2-example", "example-syntax-2-syntax",
                                    "platform-unix", "platform-windows",
                                    "platform-2-unix", "platform-2-windows"}
                    aggregate = Anchors((destination / language / "_print" / kind / "index.html").read_text())
                    duplicates = [key for key, count in Counter(aggregate.ids).items() if count > 1]
                    require(not duplicates, f"{language}{kind} Print has duplicate IDs: {duplicates}", errors)
                    require(not expected_ids.intersection(aggregate.ids),
                            f"{language}{kind} aggregate kept unscoped tab IDs", errors)
                    require(len(aggregate.tab_links) == 10,
                            f"{language}{kind} lost authored fragment links", errors)
                    for link in aggregate.tab_links:
                        require(link["href"].startswith("#pg-") and link["href"][1:] in aggregate.ids,
                                f"{language}{kind} left an authored fragment unresolved: {link}", errors)
                        expected_title = {
                            "single": "fake href='#example-syntax-syntax'",
                            "bare": "fake href=#example-syntax-syntax > text",
                            "double": 'fake href="#example-syntax-syntax"',
                            "entity": "encoded fragment",
                            "self": "same page",
                        }[link["data-test-tab-link"]]
                        require(link["title"] == expected_title,
                                f"{language}{kind} rewrote href text inside title: {link}", errors)
                    for suffix in expected_ids:
                        targets = [key for key in aggregate.ids if key.endswith("--" + suffix)]
                        require(len(targets) == 2, f"{language}{kind} lost a namespaced {suffix}", errors)
                    for chapter in ("a", "b"):
                        html = Anchors((destination / language / kind / chapter / "index.html").read_text())
                        plain = Anchors((destination / language / "_print" / kind / chapter / "index.html").read_text())
                        for name, document in (("HTML", html), ("single-page Print", plain)):
                            duplicates = [key for key, count in Counter(document.ids).items() if count > 1]
                            require(not duplicates, f"{language}{kind}/{chapter} {name} has duplicate IDs: {duplicates}", errors)
                            require(expected_ids.issubset(document.ids),
                                    f"{language}{kind}/{chapter} {name} changed grouped tab deep links", errors)
                            require("#example-syntax-syntax" in document.links and
                                    f"{base_path}{language}{kind}/{chapter}/#example-syntax-2-example" in document.links,
                                    f"{language}{kind}/{chapter} {name} changed local tab links", errors)
                            require(len(document.tab_links) == 5 and all(
                                link["href"] == (
                                    f"{base_path}{language}{kind}/{chapter}/#example-syntax-syntax"
                                    if link["data-test-tab-link"] == "self" else "#example-syntax-syntax"
                                ) for link in document.tab_links),
                                f"{language}{kind}/{chapter} {name} changed authored fragment links", errors)
                        require(f"authored-{kind}-{chapter}" in aggregate.ids,
                                f"{language}{kind} rewrote an authored anchor", errors)
                    for href in aggregate.links:
                        if href.startswith("#") and "example-syntax" in href:
                            require(href[1:] in aggregate.ids, f"{language}{kind} tab link has no target: {href}", errors)
                    # Cross-page links continue to use the ordinary HTML destination.
                    require(f"{base_path}{language}{kind}/a/#example-syntax-syntax" in aggregate.links,
                            f"{language}{kind} changed a cross-page tab link", errors)
                    local_links = [href for href in aggregate.links if href.startswith("#") and "example-syntax" in href]
                    require(len(set(local_links)) == 4, f"{language}{kind} tab links share another chapter's target", errors)
        finally:
            temp.cleanup()
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
    # Callout labels are namespaced (`callout_note`, …): the theme must not
    # claim bare top-level keys such as `note` or `example` that a consuming
    # site is just as likely to want.
    keys = ["ui_tabs_label", "ui_table_scroll", "ui_field_self_link", "book_example", "book_figure", "book_table", "book_equation"]
    keys += [f"callout_{t}" for t in CANONICAL_TYPES]
    keys += ["callout_details"]
    for path in sorted((ROOT / "i18n").glob("*.yaml")):
        source = path.read_text(encoding="utf-8")
        for key in keys:
            require(re.search(rf"^{re.escape(key)}:", source, re.M) is not None, f"{path.name} lacks i18n key {key}", errors)
        for removed in ("ui_code_group_label", "ui_doc_carousel", "ui_carousel_previous", "ui_carousel_next",
                        "ui_language", "ui_theme", "ui_code_copy", "ui_release_compare", "ui_release_checksums",
                        "note", "tip", "important", "warning", "caution", "success", "danger",
                        "question", "example", "quote", "details"):
            require(re.search(rf"^{re.escape(removed)}:", source, re.M) is None, f"{path.name} keeps removed i18n key {removed}", errors)
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    hook = (ROOT / "layouts/_markup/render-blockquote-alert.html").read_text()
    for marker in ('"note" "tip" "important" "warning" "caution" "success" "danger" "question" "example" "quote" "details"', 'partial "content/attributes.html"', '(slice "icon")', "fa-(solid|regular|brands) fa-[a-z0-9-]+", 'eq $sign "-"', 'eq $sign "+"', 'eq $type "details"', "td-callout--collapsible", "<details", "<summary", 'role="note"', "data-td-callout-collapsible", 'i18n (printf "callout_%s" $type)'):
        require(marker in hook, f"render-blockquote-alert.html lacks {marker}", errors)
    require("nb" not in re.sub(r'\{\{-?\s*/\*.*?\*/\s*-?\}\}', "", hook, flags=re.S), "the nb callout special case survived", errors)
    for name, markers in {
        "render-codeblock-echarts.html": ('partial "content/attributes.html"', '(slice "height" "theme" "full")', "$policy.generic", "full must be true or false", "transform.Unmarshal", "reflect.IsMap", "td-echarts-source", 'Store.Set "hasEcharts" true'),
        "render-codeblock-infographic.html": ('(slice "height" "full")', "$policy.generic", "full must be true or false", "td-infographic-source", 'Store.Set "hasInfographic" true'),
        "render-codeblock-checksums.html": ('(slice "base" "algo" "group")', '"generic" $policy.generic', 'partial "release/assets-parse.html"', 'partial "release/assets-table.html"', 'partial "release/assets-markdown.html"', "base is required unless the page has release_url front matter"),
    }.items():
        source = (ROOT / "layouts/_markup" / name).read_text()
        for marker in markers:
            require(marker in source, f"{name} lacks {marker}", errors)
    runtime = (ROOT / "assets/js/content-components.js").read_text()
    diagram = (ROOT / "assets/js/diagram.js").read_text()
    diagram_styles = (ROOT / "assets/scss/td/_diagram.scss").read_text()
    require("entry.printOpen" in diagram and "entry.kind === 'mermaid' && entry.theme === 'dark'" in diagram
            and 'data-td-diagram-theme="dark"' in diagram_styles and "color: #111 !important" in diagram_styles,
            "browser print must provide readable dark Mermaid source and restore its disclosure state", errors)
    require("target.offsetWidth ||" not in runtime and "width: '100%'" in runtime,
            "Infographic must retain container-relative width rather than a mount-time pixel width", errors)
    require("event.node.style.backgroundColor || '#fff'" in runtime,
            "Infographic must keep authored backgrounds ahead of its neutral canvas fallback", errors)
    require("$fn:" in runtime and "OinkEchartsFunctions" in runtime, "ECharts callback bridge ($fn: / OinkEchartsFunctions) changed", errors)
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
        require(re.search(r"(?m)^\s*" + re.escape(removed) + r"\s*:", config.lower()) is None,
                f"theme hugo.yaml still configures the removed {removed} feature", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path)
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    public = args.public
    if public is None:
        public, result = build_fixture_public(args.hugo)
        if result.returncode != 0:
            print(f"private fixture build failed: {result.stdout}{result.stderr}")
            return 1

    errors = (
        check_outputs(public)
        + check_callout_matrix(args.hugo)
        + check_data_fences(args.hugo)
        + check_steps_container(args.hugo)
        + check_presentation_variants(args.hugo)
        + check_openapi(args.hugo)
        + check_media_output_states(args.hugo)
        + check_empty_tabs(args.hugo)
        + check_print_tab_namespaces(args.hugo)
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
