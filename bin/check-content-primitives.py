#!/usr/bin/env python3
"""Validate everyday content primitive output and strict author failures.

Covers Badge, Kbd, Fields (shortcode and `{.fields}` table), the native list
forms (`{.steps}`, `{.cards}`), the `filetree` fence, the table family (`.matrix`,
`caption`, numbered `num`, class pass-through, attribute policy) and the
`include` / `param` leaves.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile

from test_site import build_fixture_public, fixture_config


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    page = (public / "fixtures/content-primitives/index.html").read_text()
    markdown = (public / "fixtures/content-primitives/index.md").read_text()
    print_page = (public / "_print/fixtures/index.html").read_text()
    lists = (public / "fixtures/lists/index.html").read_text()
    lists_markdown = (public / "fixtures/lists/index.md").read_text()
    steps = (public / "fixtures/steps/index.html").read_text()
    steps_markdown = (public / "fixtures/steps/index.md").read_text()
    tables = (public / "fixtures/tables/index.html").read_text()
    tables_markdown = (public / "fixtures/tables/index.md").read_text()
    bundle_match = re.search(r'<script src="([^"]*/page-[^"]+\.js)"', lists)
    require(bundle_match is not None, "lists fixture has no feature bundle", errors)
    lists_bundle = ""
    if bundle_match:
        bundle = public / bundle_match.group(1).lstrip("/")
        require(bundle.is_file(), "lists feature bundle is missing", errors)
        if bundle.is_file():
            lists_bundle = bundle.read_text(encoding="utf-8")

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
        '<code class="td-field__name">offline_search</code>',
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
        # FileTree fence: panel with title bar, native <details>, aligned comments.
        '<div class="td-filetree" style="--td-filetree-name-col:',
        '<p class="td-filetree__title" id="td-filetree-',
        '>Site tree</p>',
        '<li class="td-filetree__item td-filetree__item--dir td-filetree__item--parent"><details class="td-filetree__details" open><summary class="td-filetree__summary"><span class="td-filetree__row" style="--td-filetree-depth:0">',
        '<span class="td-filetree__name" title="content/">content/</span>',
        '<span class="td-filetree__comment" title="0755 docs-admin:writers · Site content &amp; templates"><span class="td-filetree__hash" aria-hidden="true">#</span><span class="td-filetree__comment-text">0755 docs-admin:writers · Site content &amp; templates</span></span>',
        '<span class="td-filetree__name" title="index.md"><a href="/docs/">index.md</a></span>',
        '<span class="td-filetree__name" title="configuration.md"><a href="/docs/configuration/">configuration.md</a></span>',
        '<span class="td-filetree__row" style="--td-filetree-depth:10"><span class="td-filetree__name-cell"><span class="td-filetree__icon td-filetree__icon--file" aria-hidden="true"><i class="fa-brands fa-markdown td-filetree__glyph"></i></span><span class="td-filetree__name" title="deeply-nested.md">deeply-nested.md</span></span>',
        '<i class="fa-regular fa-folder td-filetree__glyph td-filetree__glyph--closed"></i><i class="fa-regular fa-folder-open td-filetree__glyph td-filetree__glyph--open"></i>',
        '<span class="td-filetree__name" title="favicon.ico">favicon.ico</span>',
        '<i class="fa-solid fa-gear td-filetree__glyph"></i></span><span class="td-filetree__name" title="hugo.yaml">hugo.yaml</span>',
    ):
        require(marker in page, f"HTML fixture missing {marker}", errors)
    require("td-badge--outline" not in page and "td-badge--filled" not in page, "badge still emits the removed outline/filled variants", errors)
    require("javascript:" not in page, "HTML contains an unsafe URL", errors)
    require('<dl class="td-fields__list"' in page, "Fields no longer render as a definition list", errors)
    require(page.count('class="td-field"') == 9, "Fields lost author order or entries", errors)
    for legacy in ('<ul class="filetree">', 'role="tree"', "td-filetree__entry", "data-td-filetree-body", "td-filetree__comment-scroll"):
        require(legacy not in page, f"FileTree fixture still emits removed markup {legacy}", errors)
    require('data-td-filetree>' in page and page.count('<span class="td-filetree__divider" role="separator" aria-orientation="vertical" aria-valuemin="50" aria-valuemax="70" aria-valuenow="50" aria-label="Resize the file tree comment column" tabindex="0" data-td-filetree-divider></span>') == 1, "FileTree with comments did not render exactly one split divider", errors)
    filetree = re.search(r'<div class="td-filetree"[\s\S]*?</ul></div></div>', page)
    require(filetree is not None, "FileTree fence did not render a panel", errors)
    if filetree:
        block = filetree.group(0)
        require(block.count("<details") == 11 and block.count("</details>") == 11, "FileTree lost its nested directories", errors)
        require(block.count("<li ") == 17, "FileTree rendered a wrong number of entries", errors)
        require(block.count('<span class="td-filetree__comment"') == 17, "FileTree comment column is not present on every row", errors)
        require("</ul></details></li></ul></details></li>" in block, "FileTree nesting is not closed level by level", errors)
        require(block.count("<ul") == block.count("</ul>") and block.count("<li ") == block.count("</li>"), "FileTree markup is unbalanced", errors)

    for marker in (
        "**Beta**",
        "[**v0\\.3**](/release/)",
        "Ctrl + K",
        r"\[ + A\+B + \>",
        "- `offline_search` — `boolean`; required; default: `true`",
        "**Configuration fields**",
        "- `explicitFalse` — `boolean`; default: `false`",
        "- `zeroLimit` — `integer`; default: `0`",
        '- `emptyPrefix` — `string`; default: `""`',
        "- `resolverOutput` — `Array<string> | map[string]any`",
        "[documentation](/docs/)",
        "A second paragraph preserves multiline description Markdown and `inline code`.",
        # The fence is its own Markdown output (source = fallback).
        '```filetree {title="Site tree"}',
        "- content/                     # 0755 docs-admin:writers · Site content & templates",
        "  - _index.md                  # 0644 vonng:docs · Section landing page",
        "    - [configuration.md](/docs/configuration/)   # 0644 docs-admin · Runtime settings",
        "                    - deeply-nested.md",
        "- hugo.yaml                    # root:root 0644",
        "| Component | HTML behavior | Print behavior | Markdown behavior | Runtime |",
        "| Full table | 100% | Horizontal scroll | Complete table |",
        "{.full-width}",
    ):
        require(marker in markdown, f"Markdown fixture missing {marker}", errors)
    for marker in ("td-badge", "td-kbd-sequence", "td-field", "td-filetree", "{.filetree}", "<kbd", "<span", "<dl", "<details", "<ul"):
        require(marker not in markdown, f"Markdown contains runtime HTML {marker}", errors)

    for marker in (
        "Beta",
        "Deprecated",
        "<kbd>Ctrl</kbd>",
        "实验功能",
        "Configuration fields",
        "offline_search",
        "Array&lt;string&gt; | map[string]any",
        "<code>false</code>",
        "<code>0</code>",
        "<code>&#34;&#34;</code>",
        '<div class="td-filetree td-filetree--static"',
        '<li class="td-filetree__item td-filetree__item--dir td-filetree__item--parent"><span class="td-filetree__row" style="--td-filetree-depth:0">',
        "deeply-nested.md",
        "configuration.md",
        'class="td-fields"',
        '<table class="full-width">',
    ):
        require(marker in print_page, f"print fixture missing {marker}", errors)
    # The wrapper stays in print so the caption, matrix, and figure selectors keep
    # working, but it must be marked static and must never be a focusable viewport.
    require("td-table-scroll--static" in print_page, "print table wrapper is not marked static", errors)
    require(re.search(r'td-table-scroll[^>]*(tabindex|role=)', print_page) is None, "print kept an interactive table scroll viewport", errors)
    print_trees = re.findall(r'<div class="td-filetree td-filetree--static"[\s\S]*?</ul></div></div>', print_page)
    require(any(">Site tree</p>" in tree and "<details" not in tree and tree.count("<li ") == 17 for tree in print_trees), "print FileTree is not the static, fully expanded tree", errors)
    require(print_trees and all("<details" not in tree for tree in print_trees), "print FileTree still uses <details>", errors)

    # --- Native list forms: cards / gallery + filetree fences (lists fixture) --
    for marker in (
        '<ul class="cards">',
        '<li><a href="/docs/">Install</a> — Deploy from scratch in five minutes.</li>',
        '<li><a href="/fixtures/typography/">Reference</a></li>',
        '<li>\n<p><a href="/docs/">Install</a></p>\n<p>Deploy from scratch in five minutes.</p>\n</li>',
        '<ul class="td-gallery td-gallery--described">',
        '<input checked="" disabled="" type="checkbox"> Render the static status',
        '<input disabled="" type="checkbox"> Label the disabled checkbox at runtime',
        # 2-space bullets with title, comments, open=false, icon/tone override
        '>Repository layout</p>',
        '<li class="td-filetree__item td-filetree__item--dir td-filetree__item--parent"><details class="td-filetree__details"><summary class="td-filetree__summary"><span class="td-filetree__row" style="--td-filetree-depth:1"><span class="td-filetree__name-cell"><span class="td-filetree__icon td-filetree__icon--dir" aria-hidden="true">',
        '<li class="td-filetree__item td-filetree__item--dir"><span class="td-filetree__row" style="--td-filetree-depth:1"><span class="td-filetree__name-cell"><span class="td-filetree__icon td-filetree__icon--dir" aria-hidden="true"><i class="fa-regular fa-folder td-filetree__glyph td-filetree__glyph--closed"></i><i class="fa-regular fa-folder-open td-filetree__glyph td-filetree__glyph--open"></i></span><span class="td-filetree__name" title="logs/">logs/</span></span>',
        '<span class="td-filetree__icon td-filetree__icon--file td-filetree__icon--warning" aria-hidden="true"><i class="fa-solid fa-scale-balanced td-filetree__glyph"></i></span><span class="td-filetree__name" title="LICENSE">LICENSE</span>',
        # 4-space bare listing, no comments -> plain, type=dir override
        '<div class="td-filetree td-filetree--plain" style="--td-filetree-name-col:',
        '<span class="td-filetree__name" title="build">build</span></span></span></li>',
        '<i class="fa-brands fa-golang td-filetree__glyph"></i></span><span class="td-filetree__name" title="main.go">main.go</span>',
        # pasted `tree` output: root ".", connectors, summary line skipped
        '<span class="td-filetree__name" title=".">.</span>',
        '<span class="td-filetree__row" style="--td-filetree-depth:2"><span class="td-filetree__name-cell"><span class="td-filetree__icon td-filetree__icon--file" aria-hidden="true"><i class="fa-regular fa-file td-filetree__glyph"></i></span><span class="td-filetree__name" title="pig">pig</span>',
    ):
        require(marker in lists, f"lists fixture missing {marker}", errors)
    require(lists.count('<ul class="cards">') == 2, "cards fixture lost a list", errors)
    require('input[type="checkbox"]' in lists_bundle and 'i[class*="fa-"]' in lists_bundle,
            "lists task fixture did not load the authored accessibility runtime", errors)
    require(lists.count("--td-filetree-name-col:") == 3, "lists fixture lost a filetree fence", errors)
    require(lists.count("data-td-filetree-divider") == 1 and lists.count("data-td-filetree>") == 1, "only the commented filetree fence should carry the split divider", errors)
    require("data-td-filetree-divider" not in print_page, "print FileTree must not render the split divider", errors)
    require("2 directories, 3 files" not in lists, "filetree rendered the tree summary line", errors)
    require(lists.count("td-filetree__chrome") == 1, "filetree drew a title bar without a title", errors)
    for block in re.findall(r'<div class="td-filetree[\s\S]*?</ul></div></div>', lists):
        require(block.count("<ul") == block.count("</ul>") and block.count("<li ") == block.count("</li>") and block.count("<details") == block.count("</details>"), "filetree markup is unbalanced", errors)
    require('<span class="td-filetree__icon td-filetree__icon--dir" aria-hidden="true"><i class="fa-regular fa-folder td-filetree__glyph td-filetree__glyph--closed"></i><i class="fa-regular fa-folder-open td-filetree__glyph td-filetree__glyph--open"></i></span><span class="td-filetree__name" title="build">build</span>' in lists, "type=dir did not override the file kind", errors)
    for marker in ("- [Install](/docs/) — Deploy from scratch in five minutes.", "{.cards}", "- [x] Render the static status", "- [ ] Label the disabled checkbox at runtime", "```gallery", '```filetree {title="Repository layout"}', "├── bin", "    build {type=dir}"):
        require(marker in lists_markdown, f"lists Markdown missing {marker}", errors)
    require("<ul" not in lists_markdown and "td-" not in lists_markdown and "{.filetree}" not in lists_markdown, "lists Markdown contains HTML or the removed marker", errors)

    # --- Steps ---------------------------------------------------------------
    for marker in (
        '<ol class="steps">',
        '<ol start="3" class="steps">',
        '<h3 id="init-workspace">Initialise the workspace<a class="td-heading-self-link" href="#init-workspace"',
        'href="#init-workspace"',  # heading inside a step enters the TOC
        'class="td-callout td-callout--tip"',
        'data-td-tab="Homebrew" data-td-tab-group="install" data-td-tab-value="brew"',
        '<div class="td-steps td-max-width-on-larger-screens">',
        '<h3 id="create-the-content">Create the content<a class="td-heading-self-link"',
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
        '<code class="td-field__name">offline_search</code>',
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
        '<figure id="tab_iso" class="td-book-figure td-book-figure--tbl" data-td-book-kind="tbl" data-td-book-num="9-1">',
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
    require("offline_search_summary_length" in tables and tables.count('<span class="td-field__meta-label">默认值</span>') == 2, "empty middle cells were not omitted from the fields metadata", errors)
    for marker in ("| 参数 | 类型 | 默认值 | 说明 |", '{.fields caption="搜索参数"}', "{.matrix}", '{caption="Release facts"}', '{#tab_iso num="9-1" caption="Anomalies allowed by isolation level"}', '{tab="PG 17" group="pgver" value="pg17"}', "{.full-width}"):
        require(marker in tables_markdown, f"tables Markdown missing {marker}", errors)
    require("<table" not in tables_markdown and "td-" not in tables_markdown, "tables Markdown contains HTML", errors)
    return errors


def check_subpath(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-subpath-") as temp:
        destination = Path(temp) / "public"
        result = subprocess.run(
            [hugo, "--source", str(FIXTURE), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--config", fixture_config(), "--logLevel", "warn"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"subpath fixture failed to build: {result.stdout}{result.stderr}")
        else:
            page = (destination / "fixtures/content-primitives/index.html").read_text()
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
            "```filetree\n"
            "- closed/            # 0750 root:docs · Archived & stable\n"
            "  - [deep.md](/docs/deep/)   # 0440 reader · Read me\n"
            "- root.yml\n"
            "```\n"
        )
        (layouts / "single.rss.xml").write_text(
            '{{- .Store.Set "tdOutputFormat" "rss" -}}\n'
            "<fixture>{{ .RenderShortcodes }}</fixture>\n"
        )
        override = temp_path / "rss.yaml"
        override.write_text("disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML]\n  section: [HTML]\n  page: [RSS]\n")
        destination = temp_path / "public"
        result = subprocess.run(
            [hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--config", f"{FIXTURE / 'hugo.yaml'},{override}", "--logLevel", "warn"],
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
            # RenderShortcodes keeps the fence as source Markdown.
            "```filetree",
            "- closed/            # 0750 root:docs · Archived & stable",
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
            "```filetree\n- closed/\n  - nested.md\n```\n\n"
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
        for marker in ('&lt;pre class=&#34;td-filetree-source&#34;&gt;', "nested.md", '&lt;ol class=&#34;steps&#34;&gt;', "Example only"):
            require(marker in source, f"generic RSS primitive fixture missing {marker}", errors)
        for marker in ("td-filetree__row", "&lt;details"):
            require(marker not in source, f"generic RSS primitive fixture leaked interactive FileTree markup {marker}", errors)
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


FIELD_ENTRY = re.compile(r'<div class="td-field"(?P<id>[^>]*)>\s*<dt class="td-field__term">(?P<term>.*?)</dt>', re.S)
SELF_LINK = re.compile(r'<a class="td-heading-self-link td-field__self-link"[^>]*></a>')


def check_field_parity(html: str) -> list[str]:
    """A `{.fields meta=}` table and the shortcode must emit the same entry header.

    The two forms exist because only the shortcode can carry block-level
    descriptions; everything above the description is one shared renderer, and
    that is what this compares (oink.pgsty.com/docs/design/components/).
    """
    errors: list[str] = []
    terms: dict[str, list[str]] = {}
    for match in FIELD_ENTRY.finditer(html):
        term = match.group("term")
        name = re.search(r'class="td-field__name">([^<]*)<', term)
        if name:
            terms.setdefault(name.group(1), []).append(SELF_LINK.sub("", term).strip())
    for name in ("alpha", "beta"):
        rendered = terms.get(name, [])
        require(len(rendered) == 2, f"the parity fixture lost one {name} entry", errors)
        if len(rendered) == 2:
            require(rendered[0] == rendered[1], f"the table and shortcode forms disagree on {name}:\n  table: {rendered[0]}\n  shortcode: {rendered[1]}", errors)
    for marker in (
        '<span class="td-field__type"><span class="td-field__meta-value"><code>string</code></span></span>',
        '<span class="td-field__required">required</span>',
        '<span class="td-field__default"><span class="td-field__meta-label">default</span><span class="td-field__meta-value"><code>x</code></span></span>',
        '<span class="td-field__meta"><span class="td-field__meta-label">Note</span><span class="td-field__meta-value">备注</span></span>',
        '<div class="td-fields site-fields" id="sc-fields" data-fixture="shortcode">',
        '<div class="td-field" id="field-alpha">',
        '<div class="td-field" id="field-alpha-2">',
        '<a class="td-heading-self-link td-field__self-link" href="#field-alpha" aria-label="Link to this field"></a>',
    ):
        require(marker in html, f"fields parity fixture missing {marker}", errors)
    return errors


def check_field_anchors(html: str) -> list[str]:
    """A field anchor must be derivable from the field name by eye.

    Field names are identifiers, so Goldmark's heading rule is the wrong one:
    it deletes punctuation instead of converting it, and `params.ui.typography`
    becomes `paramsuitypography`, which nobody can link to without reading the
    generated HTML first. The rule is lowercase, then each run of punctuation
    collapses to one hyphen (oink.pgsty.com/docs/design/components/).
    """
    errors: list[str] = []
    for name, anchor in (
        ("params.ui.typography", "field-params-ui-typography"),
        ("--dry-run", "field-dry-run"),
        ("data-*", "field-data"),
        ("offline_search", "field-offline_search"),
        ("baseURL", "field-baseurl"),
        ("搜索模式", "field-搜索模式"),
    ):
        require(f'<div class="td-field" id="{anchor}">' in html, f"field {name!r} did not anchor as {anchor!r}", errors)
    return errors


CODE_BLOCK_ID = re.compile(r'id="(td-code-[^"]*)"')


def check_field_scopes(html: str) -> list[str]:
    """Each field description must render in a scope of its own.

    The scope prefixes every id a nested render hook generates, so it has to be
    unique per entry, and no slug of the name is: `a.b` collides with `ab` under
    Goldmark's heading rule and with `a-b` under the field rule. The anchor
    registry is what resolves those collisions, so the anchor is the scope
    (layouts/_shortcodes/fields.html). A name-derived scope puts the same id on
    two code blocks, which is a duplicate id in the document.
    """
    errors: list[str] = []
    for anchor in ("field-a-b", "field-ab", "field-a-b-2"):
        require(f'<div class="td-field" id="{anchor}">' in html, f"the scope fixture lost its {anchor} entry", errors)
    generated = CODE_BLOCK_ID.findall(html)
    duplicates = sorted({value for value in generated if generated.count(value) > 1})
    require(not duplicates, f"field descriptions generated duplicate ids: {duplicates}", errors)
    return errors


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
        (site / "content/docs/parity.md").write_text(
            "---\ntitle: Fields parity\n---\n\n"
            "## Semantic roles render exactly like the shortcode form\n\n"
            "| Field | Type | Required | Default | Description |\n| --- | --- | --- | --- | --- |\n"
            "| `alpha` | string | yes | `x` | First |\n| `beta` | | | | Second |\n"
            '{.fields meta="type required default"}\n\n'
            "{{< fields >}}\n"
            '{{< field name="alpha" type="string" required=true default="x" >}}First{{< /field >}}\n'
            '{{< field name="beta" >}}Second{{< /field >}}\n'
            "{{< /fields >}}\n\n"
            "## A `-` role keeps the column header as the chip label\n\n"
            "| Field | Type | Note | Description |\n| --- | --- | --- | --- |\n"
            "| `gamma` | string | 备注 | Third |\n"
            '{.fields meta="type -"}\n\n'
            "## Shortcode container attributes\n\n"
            '{{< fields label="Shortcode attributes" id="sc-fields" class="site-fields" data-fixture="shortcode" >}}\n'
            '{{< field name="delta" >}}Fourth{{< /field >}}\n'
            "{{< /fields >}}\n\n"
            "## Anchors stay derivable from identifier-shaped names\n\n"
            "| Field | Description |\n| --- | --- |\n"
            "| `params.ui.typography` | Dotted configuration key |\n"
            "| `--dry-run` | Command flag |\n"
            "| `data-*` | Attribute glob |\n"
            "| `offline_search` | Underscore is a word character |\n"
            "| `baseURL` | Case folds like a heading |\n"
            "| `搜索模式` | Non-Latin names keep their letters |\n"
            "{.fields}\n\n"
            "## Names that slug alike still render in distinct scopes\n\n"
            # `a.b` collides with `ab` under Goldmark's heading rule and with
            # `a-b` under the field rule, so one fixture covers both ways a
            # name-derived scope stops being unique.
            "{{< fields >}}\n"
            '{{< field name="a.b" >}}\n'
            "```text\nfirst\n```\n"
            "{{< /field >}}\n"
            '{{< field name="ab" >}}\n'
            "```text\nsecond\n```\n"
            "{{< /field >}}\n"
            '{{< field name="a-b" >}}\n'
            "```text\nthird\n```\n"
            "{{< /field >}}\n"
            "{{< /fields >}}\n",
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
            '<span class="nt">included</span><span class="p">:</span>',  # the yaml include, highlighted
            "Value 42 inline.",
        ):
            require(marker in html, f"table family fixture missing {marker}", errors)
        require("onclick" not in html, "an on* attribute reached the rendered table", errors)
        parity = (destination / "docs/parity/index.html").read_text(encoding="utf-8")
        errors += check_field_parity(parity)
        errors += check_field_anchors(parity)
        errors += check_field_scopes(parity)
        require(html.count('data-td-language="yaml"') == 2 and 'data-td-language="js"' in html, "include code=true did not highlight the included files", errors)
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
    ("fields-id-empty", '{{< fields id="" >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "id must not be empty"),
    ("fields-id-characters", '{{< fields id="a b" >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "contains unsupported characters"),
    ("fields-class-token", '{{< fields class="ok bad!" >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "class token"),
    ("fields-style", '{{< fields style="color:red" >}}{{< field name="x" >}}description{{< /field >}}{{< /fields >}}\n', "unsafe attribute"),
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
    ("table-fields-meta-unknown", TABLE + '{.fields meta="kind"}\n', "not one of type, required, default"),
    ("table-fields-meta-count", TABLE + '{.fields meta="type default"}\n', "meta lists 2 role(s)"),
    ("table-fields-meta-duplicate", "| F | T1 | T2 | D |\n| --- | --- | --- | --- |\n| `a` | x | y | z |\n" + '{.fields meta="type type"}\n', "listed twice"),
    ("table-meta-without-fields", TABLE + '{meta="type"}\n', "meta requires .fields"),
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
    # FileTree fence
    ("filetree-empty", "```filetree\n\n```\n", "requires tree entries"),
    ("filetree-unknown-attr", "```filetree {label=\"x\"}\n- a\n```\n", "unknown attribute"),
    ("filetree-empty-title", "```filetree {title=\"\"}\n- a\n```\n", "title must not be empty"),
    ("filetree-bad-dedent", "```filetree\n- a/\n    - b\n  - c\n```\n", "dedents to an indentation level that was never opened"),
    ("filetree-unknown-key", "```filetree\n- a {label=x}\n```\n", "unknown attribute \"label\""),
    ("filetree-malformed-attrs", "```filetree\n- a {icon}\n```\n", "malformed attributes"),
    ("filetree-bad-icon", "```filetree\n- a {icon=rocket}\n```\n", "icon must be one Font Awesome class pair"),
    ("filetree-bad-tone", "```filetree\n- a {tone=primary}\n```\n", "tone must be one of"),
    ("filetree-bad-type", "```filetree\n- a {type=folder}\n```\n", "type must be dir or file"),
    ("filetree-open-on-file", "```filetree\n- a.md {open=false}\n```\n", "open is only valid on directories"),
    ("filetree-open-value", "```filetree\n- a/ {open=no}\n```\n", "open must be true or false"),
    ("filetree-duplicate-key", "```filetree\n- a/ {open=false open=true}\n```\n", "is set twice"),
    ("filetree-empty-value", "```filetree\n- a {tone=\"\"}\n```\n", "must not be empty"),
    ("filetree-no-name", "```filetree\n- a/\n  - # only a comment\n```\n", "line 2 has no entry name"),
    ("filetree-bad-link", "```filetree\n- [a](javascript:alert)\n```\n", "unsupported link on line 1 scheme"),
    ("filetree-group-without-tab", "```filetree {group=\"g\"}\n- a\n```\n", "group/value require tab"),
    # Leaves
    ("param-missing", "{{< param does_not_exist >}}\n", "was not found"),
    ("include-missing-file", '{{< include file="nope.md" >}}\n', "was not found"),
    ("include-positional", '{{< include "nope.md" >}}\n', "requires named parameter file"),
    ("include-dotdot", '{{< include file="../secret.md" >}}\n', "must not contain .."),
    ("include-lang-without-code", '{{< include file="x.md" lang="md" >}}\n', "lang requires code=true"),
    ("include-unknown", '{{< include file="x.md" draft=true >}}\n', "unsupported parameter"),
)


UNBATCHED_INVALID_CASES = {"field-positional", "include-positional"}


def check_invalid_cases(hugo: str) -> list[str]:
    errors: list[str] = []
    batched = tuple(case for case in INVALID_CASES if case[0] not in UNBATCHED_INVALID_CASES)
    with tempfile.TemporaryDirectory(prefix="oink-primitives-invalid-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        content.mkdir(parents=True)
        for name, body, _ in batched:
            (content / f"{name}.md").write_text(f"---\ntitle: Invalid {name}\n---\n\n{body}")
        (content / "param-map.md").write_text("---\ntitle: Param map\nparams:\n  fixture_map:\n    a: 1\n---\n\n{{< param fixture_map >}}\n")
        command = [hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--logLevel", "warn"]
        result = subprocess.run(
            [*command, "--destination", str(temp_path / "public")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        output = result.stdout + result.stderr
        require(result.returncode == 0, f"batched invalid cases failed to render safely: {output.strip()}", errors)
        for name, _, expected in batched:
            case_output = "\n".join(line for line in output.splitlines() if f"content/docs/{name}.md:" in line)
            require(expected in case_output, f"invalid case {name} did not report {expected!r} at its position: {case_output or output.strip()}", errors)
            require((temp_path / f"public/docs/{name}/index.html").is_file(), f"invalid case {name} lost its safe output", errors)
        param_output = "\n".join(line for line in output.splitlines() if "content/docs/param-map.md:" in line)
        require("only scalar values" in param_output, f"param map did not report the scalar rule at its position: {param_output or output.strip()}", errors)
        param_page = temp_path / "public/docs/param-map/index.html"
        require(param_page.is_file(), "param map lost its safe output", errors)
        if param_page.is_file():
            require("fixture_map" not in param_page.read_text(), "param map value reached the rendered page", errors)
        strict = subprocess.run(
            [*command, "--destination", str(temp_path / "public-strict"), "--panicOnWarning"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        require(strict.returncode != 0, "batched invalid cases survived --panicOnWarning", errors)

    for name, body, expected in INVALID_CASES:
        if name not in UNBATCHED_INVALID_CASES:
            continue
        with tempfile.TemporaryDirectory(prefix=f"oink-primitives-{name}-") as temp:
            temp_path = Path(temp)
            content = temp_path / "content/docs"
            content.mkdir(parents=True)
            (content / "invalid.md").write_text(f"---\ntitle: Invalid {name}\n---\n\n{body}")
            command = [hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--logLevel", "warn"]
            result = subprocess.run(
                [*command, "--destination", str(temp_path / "public")],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            output = result.stdout + result.stderr
            case_output = "\n".join(line for line in output.splitlines() if "content/docs/invalid.md:" in line)
            require(expected in case_output, f"invalid case {name} did not report {expected!r} at its position: {case_output or output.strip()}", errors)
            page = temp_path / "public/docs/invalid/index.html"
            require(page.is_file() == (result.returncode == 0), f"invalid case {name} left partial output", errors)
            strict = subprocess.run(
                [*command, "--destination", str(temp_path / "public-strict"), "--panicOnWarning"],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            require(strict.returncode != 0, f"invalid case {name} survived --panicOnWarning", errors)
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

    # Hugo does not fall back to the base table hook for a custom output format,
    # so the implementation lives in a partial and every format gets a delegate.
    table = (ROOT / "layouts/_partials/content/table-render.html").read_text()
    for variant in ("render-table.html", "render-table.print.html", "render-table.rss.xml"):
        delegate = (ROOT / "layouts/_markup" / variant).read_text()
        require('partial "content/table-render.html"' in delegate, f"{variant} does not delegate to content/table-render.html", errors)
    table_body = (ROOT / "layouts/_partials/content/table-body.html").read_text()
    attributes = (ROOT / "layouts/_partials/content/attributes.html").read_text()
    for marker in ('partial "content/attributes.html"', '"fields"', '"matrix"', '"full-width"', "mutually exclusive", 'partial "content/fields-list.html"', 'partial "content/tab-block.html"', 'partial "book/register-target.html"', "td-book-figure--tbl"):
        require(marker in table, f"table-render.html lacks {marker}", errors)
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
    for marker in ("ol.steps", "ul.cards", "counter-reset: td-step", "ol.steps[start=", "@media print", "forced-colors", "prefers-reduced-motion"):
        require(marker in markers, f"_markers.scss lacks {marker}", errors)
    # FileTree and Gallery left the list-marker layer for data fences. Assert the
    # selectors are gone rather than the words: the file explains the move, and a
    # bare substring test would forbid documenting it.
    for selector in ("ul.filetree", "ul.gallery"):
        require(selector not in markers, f"_markers.scss keeps the removed {selector} list marker", errors)
    gallery_scss = (ROOT / "assets/scss/td/_gallery.scss").read_text()
    for marker in (".td-gallery", "&__item", "&__image", "&__description", "forced-colors", "@media print"):
        require(marker in gallery_scss, f"_gallery.scss lacks {marker}", errors)
    filetree_styles = (ROOT / "assets/scss/td/_filetree.scss").read_text()
    for marker in (".td-filetree", "--td-filetree-name-col", "--td-filetree-indent: 2.5ch", "clamp(50%, var(--td-filetree-name-col), 70%)", ".td-filetree__divider", ".td-filetree__details[open]", ".td-filetree--static", ".td-filetree--plain", "@media print", "@media (forced-colors: active)", "[dir='rtl']", "media-breakpoint-down(sm)"):
        require(marker in filetree_styles, f"_filetree.scss lacks {marker}", errors)
    filetree_hook = (ROOT / "layouts/_markup/render-codeblock-filetree.html").read_text()
    for marker in ('partial "content/attributes.html"', "$policy.generic", 'partial "content/filetree-parse.html"', 'partial "content/filetree-icon.html"', 'partial "content/tab-block.html"', "td-filetree--static", "td-filetree-source", "```filetree", '$page.Store.Set "hasFileTree" true', 'role="separator"', 'T "ui_filetree_divider"'):
        require(marker in filetree_hook, f"render-codeblock-filetree.html lacks {marker}", errors)
    scripts_html = (ROOT / "layouts/_partials/scripts.html").read_text()
    require('.Page.Store.Get "hasFileTree"' in scripts_html and 'resources.Get "js/filetree.js"' in scripts_html and "$hasFileTree -}}" in scripts_html and 'range . }}{{ $bundleKey = printf "%s|%s" $bundleKey .Name }}' in scripts_html, "scripts.html does not load filetree.js on hasFileTree (and key the bundle on it)", errors)
    filetree_runtime = (ROOT / "assets/js/filetree.js").read_text()
    for marker in ("OinkFileTree", "module.exports", "data-td-filetree-divider", "pointerdown", "'ArrowRight'", "'Home'", "'End'", "--td-filetree-name-col"):
        require(marker in filetree_runtime, f"filetree.js lacks {marker}", errors)
    filetree_parse = (ROOT / "layouts/_partials/content/filetree-parse.html").read_text()
    for marker in ("$indentCh := 2.5", '"icon" "tone" "open" "type"', "├──|└──", "director(?:y|ies)", 'partial "content/url.html"'):
        require(marker in filetree_parse, f"filetree-parse.html lacks {marker}", errors)
    styles = (ROOT / "assets/scss/td/shortcodes/_content-primitives.scss").read_text()
    require("@media print" in styles and "@media (forced-colors: active)" in styles, "content primitives lack print / forced-colors styles", errors)
    require(".td-filetree" not in styles and ".td-gallery" not in styles and ".td-imgproc" not in styles, "content primitives styles keep removed component selectors", errors)
    runtime = (ROOT / "assets/js/content-components.js").read_text()
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    require("initFileTree" not in runtime and "initCarousel" not in runtime, "content-components.js keeps removed runtimes", errors)
    require("hasDocCarousel" not in scripts, "scripts.html keeps removed runtime flags", errors)
    source = (ROOT / "layouts/_partials/print/page-content.html").read_text()
    store = source.find('.Store.Set "tdOutputFormat" "print"')
    content = source.find("$page.RawContent", store)
    require(store >= 0 and content > store, "print/page-content.html does not reset Page Store before rendering print content", errors)
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
