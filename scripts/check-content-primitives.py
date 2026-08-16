#!/usr/bin/env python3
"""Validate everyday content primitive output and strict author failures.

Covers Badge, Kbd, Fields (shortcode and `{.fields}` table), the native list
forms (`{.steps}`, `{.cards}`, `{.filetree}`), the table family (`.matrix`,
`caption`, numbered `num`, class pass-through, attribute policy) and the
`include` / `param` leaves.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def temp_page_build(hugo: str, pages: dict[str, str], *, prefix: str, extra_config: str = "", extra_files: dict[str, str] | None = None) -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory]:
    """Build the example site with a replacement content directory (temp handle returned)."""
    temp = tempfile.TemporaryDirectory(prefix=prefix)
    temp_path = Path(temp.name)
    content = temp_path / "content"
    for relative, body in pages.items():
        target = content / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    for relative, body in (extra_files or {}).items():
        target = temp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    destination = temp_path / "public"
    command = [hugo, "--source", str(EXAMPLE), "--contentDir", str(content), "--destination", str(destination), "--logLevel", "warn"]
    if extra_config:
        override = temp_path / "override.yaml"
        override.write_text(extra_config, encoding="utf-8")
        command.extend(["--config", f"{EXAMPLE / 'hugo.yaml'},{override}"])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return result, destination, temp


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    page = (public / "docs/content-primitives/index.html").read_text()
    markdown = (public / "docs/content-primitives/index.md").read_text()
    print_page = (public / "_print/docs/index.html").read_text()
    lists = (public / "docs/components/lists/index.html").read_text()
    lists_markdown = (public / "docs/components/lists/index.md").read_text()
    steps = (public / "docs/components/steps/index.html").read_text()
    steps_markdown = (public / "docs/components/steps/index.md").read_text()
    tables = (public / "docs/components/tables/index.html").read_text()
    tables_markdown = (public / "docs/components/tables/index.md").read_text()

    # --- Badge / Kbd / Fields shortcode / full-width table -------------------
    for marker in (
        'class="td-badge td-badge--warning">Beta</span>',
        'class="td-badge td-badge--info" href="/release/">v0.3</a>',
        'class="td-badge td-badge--danger">Deprecated</span>',
        'R&amp;D &lt;Preview&gt;',
        'class="td-kbd-sequence"',
        '<kbd>Ctrl</kbd>',
        '<span class="td-kbd-sequence__separator" aria-hidden="true">+</span>',
        '<span class="visually-hidden"> with </span>',
        'class="td-fields"',
        'class="td-fields__label"',
        'class="td-fields__list" aria-labelledby=',
        '<dt class="td-field__term">',
        '<code class="td-field__name">offlineSearch</code>',
        '<span class="td-field__type"><span class="td-field__meta-value"><code>Array&lt;string&gt; | map[string]any</code></span></span>',
        '<span class="td-field__required">required</span>',
        '<span class="td-field__default"><span class="td-field__meta-label">default</span><span class="td-field__meta-value"><code>false</code></span></span>',
        '<span class="td-field__meta-value"><code>0</code></span>',
        '<span class="td-field__meta-value"><code>&#34;&#34;</code></span>',
        '<a href="/docs/">documentation</a>',
        'class="td-table-scroll" tabindex="0" role="region"',
        'aria-label="Scrollable table"',
        'class="td-table-scroll td-table-scroll--full"',
        '<table class="full-width">',
        # Native FileTree list: the marker is the class, nesting is the list.
        '<ul class="filetree">',
        '<li>content/ — 0755 docs-admin:writers · Site content &amp; templates\n<ul>',
        '<li><a href="/docs/">index.md</a></li>',
        '<li><a href="/docs/configuration/">configuration.md</a> — 0644 docs-admin · Runtime settings</li>',
        '<li>deeply-nested.md</li>',
        '<li><code>favicon.ico</code></li>',
        '<li>hugo.yaml — <em>root:root 0644</em></li>',
    ):
        require(marker in page, f"HTML fixture missing {marker}", errors)
    require("td-badge--outline" not in page and "td-badge--filled" not in page, "badge still emits the removed outline/filled variants", errors)
    require("javascript:" not in page, "HTML contains an unsafe URL", errors)
    require('<dl class="td-fields__list"' in page, "Fields no longer render as a definition list", errors)
    require(page.count('class="td-field"') == 9, "Fields lost author order or entries", errors)
    for legacy in ("td-filetree", "data-td-filetree", 'role="tree"', "<details"):
        require(legacy not in page, f"FileTree fixture still emits legacy markup {legacy}", errors)
    filetree = re.search(r'<ul class="filetree">[\s\S]*?</ul>\n</li>\n</ul>', page)
    require(filetree is not None, "FileTree list is not a nested list", errors)
    if filetree:
        require(filetree.group(0).count("<ul>") >= 10, "FileTree lost its nested folders", errors)

    for marker in (
        "**Beta**",
        "[**v0\\.3**](/release/)",
        "Ctrl + K",
        r"\[ + A\+B + \>",
        "- `offlineSearch` — `boolean`; required; default: `true`",
        "**Configuration fields**",
        "- `explicitFalse` — `boolean`; default: `false`",
        "- `zeroLimit` — `integer`; default: `0`",
        '- `emptyPrefix` — `string`; default: `""`',
        "- `resolverOutput` — `Array<string> | map[string]any`",
        "[documentation](/docs/)",
        "A second paragraph preserves multiline description Markdown and `inline code`.",
        # The native list is its own Markdown output (source = fallback).
        "- content/ — 0755 docs-admin:writers · Site content & templates",
        "  - _index.md — 0644 vonng:docs · Section landing page",
        "    - [configuration.md](/docs/configuration/) — 0644 docs-admin · Runtime settings",
        "                    - deeply-nested.md",
        "- hugo.yaml — *root:root 0644*",
        "{.filetree}",
        "| Component | HTML behavior | Print behavior | Markdown behavior | Runtime |",
        "| Full table | 100% | Horizontal scroll | Complete table |",
        "{.full-width}",
    ):
        require(marker in markdown, f"Markdown fixture missing {marker}", errors)
    for marker in ("td-badge", "td-kbd-sequence", "td-field", "td-filetree", "<kbd", "<span", "<dl", "<details", "<ul"):
        require(marker not in markdown, f"Markdown contains runtime HTML {marker}", errors)

    for marker in (
        "Beta",
        "Deprecated",
        "<kbd>Ctrl</kbd>",
        "实验功能",
        "Configuration fields",
        "offlineSearch",
        "Array&lt;string&gt; | map[string]any",
        "<code>false</code>",
        "<code>0</code>",
        "<code>&#34;&#34;</code>",
        '<ul class="filetree">',
        "deeply-nested.md",
        "configuration.md",
        'class="td-fields"',
        '<table class="full-width">',
    ):
        require(marker in print_page, f"print fixture missing {marker}", errors)
    require("td-table-scroll" not in print_page, "print kept a table scroll viewport", errors)

    # --- Native list forms: cards / filetree (lists fixture) -------------------
    for marker in (
        '<ul class="cards">',
        '<li><a href="/docs/">Install</a> — Deploy from scratch in five minutes.</li>',
        '<li><a href="/docs/typography/">Reference</a></li>',
        '<li>\n<p><a href="/docs/">Install</a></p>\n<p>Deploy from scratch in five minutes.</p>\n</li>',
        '<ul class="filetree">',
        '<li>logs/</li>',
        '<ul class="gallery">',
    ):
        require(marker in lists, f"lists fixture missing {marker}", errors)
    require(lists.count('<ul class="cards">') == 2, "cards fixture lost a list", errors)
    for marker in ("- [Install](/docs/) — Deploy from scratch in five minutes.", "{.cards}", "{.filetree}", "{.gallery}"):
        require(marker in lists_markdown, f"lists Markdown missing {marker}", errors)
    require("<ul" not in lists_markdown and "td-" not in lists_markdown, "lists Markdown contains HTML", errors)

    # --- Steps ---------------------------------------------------------------
    for marker in (
        '<ol class="steps">',
        '<ol start="3" class="steps">',
        '<h3 id="init-workspace">Initialise the workspace</h3>',
        'href="#init-workspace"',  # heading inside a step enters the TOC
        'class="td-callout td-callout--tip"',
        'data-td-tab="Homebrew" data-td-tab-group="install" data-td-tab-value="brew"',
        '<div class="td-steps td-max-width-on-larger-screens">',
        '<h3 id="create-the-content">Create the content</h3>',
    ):
        require(marker in steps, f"steps fixture missing {marker}", errors)
    for marker in ("1. Install the dependencies", "1. ### Initialise the workspace {#init-workspace}", "{.steps}", "3. third", "### Create the content"):
        require(marker in steps_markdown, f"steps Markdown missing {marker}", errors)
    require("td-steps" not in steps_markdown and "<div" not in steps_markdown, "steps Markdown leaked the shortcode wrapper", errors)

    # --- Table family ---------------------------------------------------------
    for marker in (
        # {.fields}: positional rule, header labels become metadata labels, caption = label
        '<p class="td-fields__label" id="td-fields-',
        '搜索参数</p>',
        '<code class="td-field__name">offlineSearch</code>',
        '<span class="td-field__meta"><span class="td-field__meta-label">类型</span><span class="td-field__meta-value">boolean</span></span>',
        '<span class="td-field__meta"><span class="td-field__meta-label">默认值</span><span class="td-field__meta-value"><code>false</code></span></span>',
        '<dd class="td-field__description">结果上限，<em>支持行内 Markdown</em> 与 <a href="/docs/">链接</a></dd>',
        '<code class="td-field__name">now()</code>',
        '<dd class="td-field__description">Current timestamp</dd>',
        # {.matrix}
        '<div class="td-table-scroll td-table-scroll--matrix"',
        '<table class="matrix td-table--matrix">',
        '<th scope="row">EL 9</th>',
        '<th scope="col" style="text-align: center">PG18</th>',
        # {caption=}
        '<caption class="td-table__caption">Release facts</caption>',
        # numbered Book table
        '<figure id="tab_iso" class="td-book-figure td-book-figure--tbl" data-book-kind="tbl" data-book-num="9-1">',
        '<span class="td-tbl-label">Table 9-1</span> <span class="td-tbl-caption">Anomalies allowed by isolation level</span>',
        'href="#tab_iso"',
        # adjacent tables with tab
        '<div class="td-tab-block td-tab-block--table" data-td-tab="PG 17" data-td-tab-group="pgver" data-td-tab-value="pg17" data-td-tab-kind="table">',
        '<div class="td-tab-block td-tab-block--table" data-td-tab="PG 16" data-td-tab-value="pg16" data-td-tab-kind="table">',
        # {.full-width}
        '<div class="td-table-scroll td-table-scroll--full"',
        '<table class="full-width">',
    ):
        require(marker in tables, f"tables fixture missing {marker}", errors)
    require("offlineSearchSummaryLength" in tables and tables.count('<span class="td-field__meta-label">默认值</span>') == 2, "empty middle cells were not omitted from the fields metadata", errors)
    for marker in ("| 参数 | 类型 | 默认值 | 说明 |", '{.fields caption="搜索参数"}', "{.matrix}", '{caption="Release facts"}', '{#tab_iso num="9-1" caption="Anomalies allowed by isolation level"}', '{tab="PG 17" group="pgver" value="pg17"}', "{.full-width}"):
        require(marker in tables_markdown, f"tables Markdown missing {marker}", errors)
    require("<table" not in tables_markdown and "td-" not in tables_markdown, "tables Markdown contains HTML", errors)
    return errors


def check_subpath(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-subpath-") as temp:
        destination = Path(temp) / "public"
        result = subprocess.run(
            [hugo, "--source", str(EXAMPLE), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--logLevel", "warn"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"subpath fixture failed to build: {result.stdout}{result.stderr}")
        else:
            page = (destination / "docs/content-primitives/index.html").read_text()
            require('href="/manual/release/"' in page, "Badge internal link is not subpath-safe", errors)
    return errors


def check_rss_output(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-rss-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        layouts = temp_path / "layouts/docs"
        content.mkdir(parents=True)
        layouts.mkdir(parents=True)
        (content / "rss.md").write_text(
            "---\ntitle: RSS primitives\noutputs: [RSS]\n---\n\n"
            'Status {{< badge text="Beta" tone="warning" >}} and '
            'shortcut {{< kbd "Ctrl" "K" >}}.\n\n'
            '{{< fields label="RSS fields" >}}\n'
            '  {{< field name="enabled" type="boolean" default=false required=true >}}\n'
            '  Static **RSS description**.\n'
            '  {{< /field >}}\n'
            '{{< /fields >}}\n\n'
            "- closed/ — 0750 root:docs · Archived & stable\n"
            "  - [deep.md](/docs/deep/) — 0440 reader · Read me\n"
            "- root.yml\n"
            "{.filetree}\n"
        )
        (layouts / "single.rss.xml").write_text(
            '{{- .Store.Set "tdOutputFormat" "rss" -}}\n'
            "<fixture>{{ .RenderShortcodes }}</fixture>\n"
        )
        override = temp_path / "rss.yaml"
        override.write_text("disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML]\n  section: [HTML]\n  page: [RSS]\n")
        destination = temp_path / "public"
        result = subprocess.run(
            [hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--config", f"{EXAMPLE / 'hugo.yaml'},{override}", "--logLevel", "warn"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"RSS fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        outputs = [path for path in destination.rglob("*.xml") if "rss" in path.parts]
        if not outputs:
            errors.append("RSS fixture did not produce an XML page output")
            return errors
        source = outputs[0].read_text()
        for marker in (
            'class="td-badge td-badge--warning">Beta</span>',
            '<kbd>Ctrl</kbd>',
            'aria-hidden="true">+</span>',
            '<dl class="td-fields__list"',
            '<code class="td-field__name">enabled</code>',
            '<span class="td-field__required">required</span>',
            '<code>false</code>',
            '<strong>RSS description</strong>',
            # RenderShortcodes keeps the native list as source Markdown.
            "- closed/ — 0750 root:docs · Archived & stable",
            "{.filetree}",
        ):
            require(marker in source, f"RSS fixture missing {marker}", errors)
        require("**Beta**" not in source, "RSS used the Markdown Badge fallback", errors)
        require("<script" not in source, "RSS contains a component runtime", errors)
    return errors


def check_generic_rss_output(hugo: str) -> list[str]:
    """Exercise the theme's ordinary section feed: native lists and escaped examples."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-generic-rss-") as temp:
        site = Path(temp)
        content = site / "content/docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "item.md").write_text(
            "---\ntitle: Primitive feed\ndate: 2026-08-11\n---\n\n"
            "- closed/\n  - nested.md\n{.filetree}\n\n"
            "1. first\n1. second\n{.steps}\n\n"
            "```go-html-template\n"
            '{{</* badge text="Example only" */>}}\n'
            "```\n"
        )
        nested = content / "nested"
        nested.mkdir()
        (nested / "_index.md").write_text("---\ntitle: Nested\n---\n")
        (nested / "child.md").write_text("---\ntitle: Nested child\ndate: 2026-08-10\n---\n\nNested child must not enter the direct section feed.\n")
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\n"
            "title: Generic primitive feed\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n  home: [HTML, RSS]\n  section: [HTML, RSS]\n  page: [HTML]\n"
            "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n    parser:\n      attribute:\n        block: true\n"
        )
        destination = site / "public"
        result = subprocess.run(
            [hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"generic RSS primitive fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        output = destination / "docs/index.xml"
        if not output.exists():
            errors.append("generic RSS primitive fixture did not produce docs/index.xml")
            return errors
        source = output.read_text()
        home_source = (destination / "index.xml").read_text()
        require("<title>Generic primitive feed</title>" in home_source, "generic RSS home title repeats the site title", errors)
        for marker in ('&lt;ul class=&#34;filetree&#34;&gt;', "nested.md", '&lt;ol class=&#34;steps&#34;&gt;', "Example only"):
            require(marker in source, f"generic RSS primitive fixture missing {marker}", errors)
        require("td-badge td-badge" not in source, "generic RSS primitive fixture rendered the escaped example", errors)
        require("Nested child must not enter" not in source, "generic section RSS recursively included a nested section page", errors)
    return errors


def check_rss_summary_contract(hugo: str) -> list[str]:
    """Keep RSS summary semantics isolated from a later HTML summary render."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-rss-summary-") as temp:
        site = Path(temp)
        content = site / "content/docs"
        layouts = site / "layouts/_default"
        content.mkdir(parents=True)
        layouts.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "manual.md").write_text(
            "---\ntitle: Manual\ndate: 2026-08-12\n---\n\n"
            'Manual before {{< badge text="Before" >}}.\n\n'
            "<!--more-->\n\n"
            'MANUAL_AFTER {{< badge text="After" >}}.\n'
        )
        (content / "front.md").write_text(
            "---\ntitle: Front\ndate: 2026-08-11\nsummary: Front summary must win.\n---\n\n"
            'FRONT_BODY {{< badge text="Body" >}}.\n'
        )
        (content / "automatic.md").write_text(
            "---\ntitle: Automatic\ndate: 2026-08-10\n---\n\n"
            'AUTO_BEFORE {{< badge text="Automatic badge" >}} '
            "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo "
            "lima mike november oscar papa quebec romeo sierra tango uniform victor "
            "whiskey xray yankee zulu amber birch cedar dogwood elm fir ginkgo hazel "
            "ivy juniper koa linden maple nutmeg oak pine quince redwood spruce teak "
            "umber violet willow yew zephyr.\n\n"
            "AUTO_AFTER must remain outside the automatic summary.\n"
        )
        (layouts / "rss.xml").write_text(
            "{{ range .RegularPages }}\n"
            '{{ .Store.Set "tdOutputFormat" "rss" }}\n'
            '{{ $description := partial "content/rss-description.html" . }}\n'
            '{{ .Store.Set "tdOutputFormat" "html" }}\n'
            '<article data-title="{{ .Title }}">\n'
            "<div data-rss>{{ $description }}</div>\n"
            "<div data-html>{{ .Summary }}</div>\n"
            "</article>\n"
            "{{ end }}\n"
        )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\ntitle: RSS summary contract\nsummaryLength: 5\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML]\n  section: [HTML, RSS]\n  page: [HTML]\n"
        )
        destination = site / "public"
        result = subprocess.run(
            [hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"RSS summary contract fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        source = (destination / "docs/index.xml").read_text()
        for marker in ("Manual before", ">Before</span>", "Front summary must win.", "AUTO_BEFORE", ">Automatic badge</span>"):
            require(marker in source, f"RSS summary contract missing {marker}", errors)
        for marker in ("MANUAL_AFTER", ">After</span>", "FRONT_BODY", ">Body</span>", "AUTO_AFTER"):
            require(marker not in source, f"RSS summary leaked {marker}", errors)
        require(source.count('data-title="') == source.count("data-html>"), "RSS-first rendering prevented a later HTML summary", errors)
        require(source.count("td-badge") >= 4, "RSS-first rendering lost output-aware shortcode HTML", errors)
    return errors


TABLE = "| Field | Type | Description |\n| --- | --- | --- |\n| `a` | string | First |\n| `b` | | Second |\n"


def check_table_family(hugo: str) -> list[str]:
    """Attribute policy, orphan attribute lines, class pass-through, include and param."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-table-family-") as temp:
        site = Path(temp)
        family = site / "content/docs/family"
        family.mkdir(parents=True)
        (site / "content/docs/_index.md").write_text("---\ntitle: Docs\n---\n", encoding="utf-8")
        (family / "index.md").write_text(
            "---\ntitle: Table family\noutputs: [HTML, markdown]\nparams:\n  fixture_scalar: 42\n---\n\n"
            "## Site classes pass through, data-* and aria-* survive, on* is dropped\n\n"
            + TABLE + '{.ext-table .stretch-last data-fixture="kept" aria-describedby="note" onclick="alert(1)"}\n\n'
            "## Fields with a class and a generic attribute\n\n"
            + TABLE + '{.fields .site-fields data-fixture="fields"}\n\n'
            "## Orphan attribute line (blank line in between) is not applied\n\n"
            + TABLE + "\n{.matrix}\n\n"
            "## Include\n\n"
            '{{< include file="snippet.md" >}}\n\n'
            '{{< include file="snippet.yaml" code=true lang="yaml" >}}\n\n'
            '{{< include file="/docs/family/snippet.yaml" code=true lang="yaml" >}}\n\n'
            '{{< include file="js/base.js" code=true lang="js" >}}\n\n'
            "## Param\n\n"
            "Value {{< param fixture_scalar >}} inline.\n",
            encoding="utf-8",
        )
        (family / "snippet.md").write_text("Included **Markdown** snippet.\n", encoding="utf-8")
        (family / "snippet.yaml").write_text("included: yes\n", encoding="utf-8")
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\n"
            "title: Table family fixture\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [RSS, sitemap, taxonomy, term]\n"
            "outputs:\n  page: [HTML, markdown]\n"
            "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n    parser:\n      attribute:\n        block: true\n",
            encoding="utf-8",
        )
        destination = site / "public"
        result = subprocess.run(
            [hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"table family fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/family/index.html").read_text(encoding="utf-8")
        for marker in (
            '<table class="ext-table stretch-last" aria-describedby="note" data-fixture="kept">',
            '<div class="td-fields site-fields" data-fixture="fields">',
            "Included <strong>Markdown</strong> snippet.",
            "included: yes",
            "Value 42 inline.",
        ):
            require(marker in html, f"table family fixture missing {marker}", errors)
        require("onclick" not in html, "an on* attribute reached the rendered table", errors)
        require(html.count('data-language="yaml"') == 2 and 'data-language="js"' in html, "include code=true did not highlight the included files", errors)
        require("td-table--matrix" not in html and "<p>{.matrix}</p>" not in html, "an orphan attribute line was applied or printed", errors)
        require(html.count("<table") == 2, "table family fixture rendered a wrong number of tables", errors)
    return errors


INVALID_CASES = (
    ("badge-no-params", '{{< badge >}}\n', "requires parameter text"),
    ("badge-missing-text", '{{< badge tone="info" >}}\n', "requires parameter text"),
    ("badge-empty-text", '{{< badge text="" >}}\n', "text must not be empty"),
    ("badge-text-type", '{{< badge text=true >}}\n', "text must be a string"),
    ("badge-positional", '{{< badge "Beta" >}}\n', "accepts named parameters only"),
    ("badge-tone", '{{< badge text="Beta" tone="loud" >}}\n', "tone must be one of"),
    ("badge-tone-type", '{{< badge text="Beta" tone=true >}}\n', "tone must be a string"),
    ("badge-outline-removed", '{{< badge text="Beta" outline=false >}}\n', "unsupported parameter"),
    ("badge-unknown", '{{< badge text="Beta" color="red" >}}\n', "unsupported parameter"),
    ("badge-scheme", '{{< badge text="Bad" link="javascript:alert(1)" >}}\n', "unsupported link scheme"),
    ("badge-link-type", '{{< badge text="Bad" link=true >}}\n', "link must be a string"),
    ("badge-link-host", '{{< badge text="Bad" link="https:" >}}\n', "requires a host"),
    ("badge-link-relative", '{{< badge text="Bad" link="//example.org/x" >}}\n', "protocol-relative URL"),
    ("badge-link-space", '{{< badge text="Bad" link="/bad path/" >}}\n', "whitespace or control characters"),
    ("kbd-empty", '{{< kbd >}}\n', "requires at least one key"),
    ("kbd-blank", '{{< kbd "" >}}\n', "keys must not be empty"),
    ("kbd-named", '{{< kbd key="K" >}}\n', "accepts positional parameters only"),
    ("kbd-type", '{{< kbd true >}}\n', "every key must be a string"),
    ("fields-empty", '{{< fields >}}{{< /fields >}}\n', "requires at least one field child"),
    ("fields-text", '{{< fields >}}not a field{{< /fields >}}\n', "accepts field children only"),
    ("fields-label-empty", '{{< fields label="" >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "label must not be empty"),
    ("fields-label-type", '{{< fields label=true >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "label must be a string"),
    ("fields-positional", '{{< fields "Label" >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "accepts named parameters only"),
    ("fields-unknown", '{{< fields kind="config" >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "unsupported parameter"),
    ("field-outside", '{{< field name="x" >}}description{{< /field >}}\n', "must be enclosed by fields"),
    ("field-missing-name", '{{< fields >}}{{< field >}}description{{< /field >}}{{< /fields >}}\n', "requires parameter name"),
    ("field-empty-name", '{{< fields >}}{{< field name="" >}}description{{< /field >}}{{< /fields >}}\n', "name must not be empty"),
    ("field-name-type", '{{< fields >}}{{< field name=true >}}description{{< /field >}}{{< /fields >}}\n', "name must be a string"),
    ("field-positional", '{{< fields >}}{{< field "x" >}}description{{< /field >}}{{< /fields >}}\n', "accepts named parameters only"),
    ("field-type-empty", '{{< fields >}}{{< field name="x" type="" >}}description{{< /field >}}{{< /fields >}}\n', "type must not be empty"),
    ("field-type-value", '{{< fields >}}{{< field name="x" type=true >}}description{{< /field >}}{{< /fields >}}\n', "type must be a string"),
    ("field-required", '{{< fields >}}{{< field name="x" required="true" >}}description{{< /field >}}{{< /fields >}}\n', "required must be boolean"),
    ("field-unknown", '{{< fields >}}{{< field name="x" since="v1" >}}description{{< /field >}}{{< /fields >}}\n', "unsupported parameter"),
    ("field-description", '{{< fields >}}{{< field name="x" >}}   {{< /field >}}{{< /fields >}}\n', "requires a non-empty description"),
    # Table hook attribute policy
    ("table-fields-matrix", TABLE + "{.fields .matrix}\n", "mutually exclusive"),
    ("table-fields-full-width", TABLE + "{.fields .full-width}\n", "cannot be combined with .full-width"),
    ("table-fields-one-column", "| Only |\n| --- |\n| x |\n{.fields}\n", "at least two columns"),
    ("table-fields-empty-name", "| Field | Description |\n| --- | --- |\n| | no name |\n{.fields}\n", "must not be empty"),
    ("table-fields-duplicate", "| Field | Description |\n| --- | --- |\n| `a` | one |\n| `a` | two |\n{.fields}\n", "duplicate field name"),
    ("table-fields-num", TABLE + '{.fields num="1"}\n', "cannot be a numbered Book table"),
    ("table-num-tab", TABLE + '{num="1" tab="x"}\n', "mutually exclusive"),
    ("table-num-bad", TABLE + '{num="1/2"}\n', "num must match"),
    ("table-group-without-tab", TABLE + '{group="g"}\n', "group/value require tab"),
    ("table-tab-empty", TABLE + '{tab=""}\n', "tab label must not be empty"),
    ("table-tab-bad-group", TABLE + '{tab="A" group="Bad Group" value="a"}\n', "group must match"),
    ("table-unknown-attr", TABLE + '{bogus="1"}\n', "unknown attribute"),
    ("table-style", TABLE + '{style="color:red"}\n', "unsafe attribute"),
    ("table-bad-class", TABLE + '{class="bad!"}\n', "unsupported characters"),
    ("table-id-bad", TABLE + '{#1bad num="1"}\n', "id must match"),
    # Leaves
    ("param-missing", "{{< param does_not_exist >}}\n", "was not found"),
    ("include-missing-file", '{{< include file="nope.md" >}}\n', "was not found"),
    ("include-positional", '{{< include "nope.md" >}}\n', "requires named parameter file"),
    ("include-dotdot", '{{< include file="../secret.md" >}}\n', "must not contain .."),
    ("include-lang-without-code", '{{< include file="x.md" lang="md" >}}\n', "lang requires code=true"),
    ("include-unknown", '{{< include file="x.md" draft=true >}}\n', "unsupported parameter"),
)


def check_invalid_cases(hugo: str) -> list[str]:
    errors: list[str] = []
    for name, body, expected in INVALID_CASES:
        with tempfile.TemporaryDirectory(prefix=f"oink-primitives-{name}-") as temp:
            temp_path = Path(temp)
            content = temp_path / "content/docs"
            content.mkdir(parents=True)
            (content / "invalid.md").write_text(f"---\ntitle: Invalid {name}\n---\n\n{body}")
            result = subprocess.run(
                [hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--destination", str(temp_path / "public"), "--logLevel", "warn"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                errors.append(f"invalid case {name} unexpectedly built")
            else:
                if expected not in output:
                    errors.append(f"invalid case {name} did not report {expected!r}: {output.strip()}")
                if "content/docs/invalid.md:" not in output:
                    errors.append(f"invalid case {name} did not report its position")
    # param with a map value needs front matter
    with tempfile.TemporaryDirectory(prefix="oink-primitives-param-map-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        content.mkdir(parents=True)
        (content / "invalid.md").write_text("---\ntitle: Param map\nparams:\n  fixture_map:\n    a: 1\n---\n\n{{< param fixture_map >}}\n")
        result = subprocess.run(
            [hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--destination", str(temp_path / "public"), "--logLevel", "warn"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        output = result.stdout + result.stderr
        require(result.returncode != 0, "param printed a map value", errors)
        require("only scalar values" in output, f"param map did not report the scalar rule: {output.strip()}", errors)
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    for relative in (
        "layouts/_shortcodes/badge.html",
        "layouts/_shortcodes/kbd.html",
        "layouts/_shortcodes/fields.html",
        "layouts/_shortcodes/field.html",
        "layouts/_shortcodes/include.html",
        "layouts/_shortcodes/param.html",
    ):
        source = (ROOT / relative).read_text()
        require("Page.Store.Set" not in source, f"{relative} sets a runtime flag", errors)
        if relative in ("layouts/_shortcodes/badge.html", "layouts/_shortcodes/kbd.html", "layouts/_shortcodes/fields.html"):
            require('eq $outputFormat "markdown"' in source, f"{relative} lacks Markdown output", errors)
    fields_source = (ROOT / "layouts/_shortcodes/fields.html").read_text()
    field_source = (ROOT / "layouts/_shortcodes/field.html").read_text()
    fields_list = (ROOT / "layouts/_partials/content/fields-list.html").read_text()
    require('partial "content/fields-list.html"' in fields_source, "Fields does not use the shared <dl> renderer", errors)
    require("<dl" in fields_list and "<table" not in fields_list and "display: contents" not in fields_list, "Fields renderer is not a plain definition list", errors)
    require(".InnerDeindent" in field_source, "Field does not normalize nested indentation", errors)
    require("render-block.html" in fields_source, "Fields does not render descriptions in a scoped RenderString", errors)
    badge = (ROOT / "layouts/_shortcodes/badge.html").read_text()
    require('"outline"' not in badge, "badge still declares the removed outline parameter", errors)
    param = (ROOT / "layouts/_shortcodes/param.html").read_text()
    require("only scalar values" in param and "htmlEscape" in param, "param is not scalar-only / escaped", errors)
    include = (ROOT / "layouts/_shortcodes/include.html").read_text()
    for marker in (".Page.Resources.Get", "resources.Get", "fileExists", "was not found", "must not contain ..", "code/normalize.html"):
        require(marker in include, f"include lacks {marker}", errors)
    require("draft" not in include.replace("no draft placeholder output", ""), "include kept the readfile draft placeholder", errors)

    table = (ROOT / "layouts/_markup/render-table.html").read_text()
    table_body = (ROOT / "layouts/_partials/content/table-body.html").read_text()
    attributes = (ROOT / "layouts/_partials/content/attributes.html").read_text()
    for marker in ('partial "content/attributes.html"', '"fields"', '"matrix"', '"full-width"', "mutually exclusive", 'partial "content/fields-list.html"', 'partial "content/tab-block.html"', 'partial "book/register-target.html"', "td-book-figure--tbl"):
        require(marker in table, f"render-table.html lacks {marker}", errors)
    for marker in ('<th scope="row"', '<th scope="col"', "td-table__caption", 'T "ui_table_scroll"'):
        require(marker in table_body, f"table-body.html lacks {marker}", errors)
    for marker in ("unsafe attribute", "unknown attribute", "data-", "aria-", "^[A-Za-z0-9_-]+$"):
        require(marker in attributes, f"attributes.html lacks {marker}", errors)
    for relative in (
        "layouts/_shortcodes/filetree.html",
        "layouts/_shortcodes/filetree/folder.html",
        "layouts/_shortcodes/filetree/file.html",
        "layouts/_partials/content/filetree-entry.html",
        "layouts/_shortcodes/readfile.html",
        "layouts/_shortcodes/_param.html",
    ):
        require(not (ROOT / relative).exists(), f"{relative} must stay deleted", errors)

    markers = (ROOT / "assets/scss/td/_markers.scss").read_text()
    for marker in ("ol.steps", "ul.cards", "ul.filetree", "ul.gallery", "counter-reset: td-step", "ol.steps[start=", ":has(> ul)", "@media print", "forced-colors", "prefers-reduced-motion"):
        require(marker in markers, f"_markers.scss lacks {marker}", errors)
    styles = (ROOT / "assets/scss/td/shortcodes/content-primitives.scss").read_text()
    require("@media print" in styles and "@media (forced-colors: active)" in styles, "content primitives lack print / forced-colors styles", errors)
    require(".td-filetree" not in styles and ".td-gallery" not in styles and ".td-imgproc" not in styles, "content primitives styles keep removed component selectors", errors)
    runtime = (ROOT / "assets/js/content-components.js").read_text()
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    require("initFileTree" not in runtime and "initCarousel" not in runtime, "content-components.js keeps removed runtimes", errors)
    require("hasFileTree" not in scripts and "hasDocCarousel" not in scripts, "scripts.html keeps removed runtime flags", errors)
    for relative, content_expr in (
        ("layouts/_partials/print/content.html", ".Page.RawContent"),
        ("layouts/_partials/print/render.html", ".RawContent"),
    ):
        source = (ROOT / relative).read_text()
        store = source.find('.Store.Set "tdOutputFormat" "print"')
        content = source.find(content_expr, store)
        require(store >= 0 and content > store, f"{relative} does not reset Page Store before rendering print content", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, default=EXAMPLE / "public")
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors = (
        check_outputs(args.public)
        + check_subpath(args.hugo)
        + check_rss_output(args.hugo)
        + check_generic_rss_output(args.hugo)
        + check_rss_summary_contract(args.hugo)
        + check_table_family(args.hugo)
        + check_invalid_cases(args.hugo)
        + check_template_contracts()
    )
    if errors:
        print("Content primitive checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Content primitive checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
