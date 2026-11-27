#!/usr/bin/env python3
"""Validate everyday content primitive output and author diagnostics and safe fallbacks.

Covers Badge, Kbd, Fields (shortcode and `{.fields}` table), the native list
forms (`{.steps}`, `{.cards}`), the `filetree` fence, the table family (`.matrix`,
`caption`, numbered `num`, class pass-through, attribute policy) and the
`include` / `param` leaves.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from html import escape, unescape
from pathlib import Path
import re
import tempfile

from runtime_assets import combined_source, referenced_chunks
from test_site import build_fixture_public, fixture_config, run_hugo_process


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
    chunks = referenced_chunks(public, lists)
    require(bool(chunks), "lists fixture has no runtime chunks", errors)
    require(all(item.path.is_file() for item in chunks), "lists runtime chunk is missing", errors)
    lists_bundle = combined_source(public, lists)

    # The explicit width marker survives HTML rendering; Markdown preserves
    # authored GFM and its attribute lines. Actual cell sizes and scroll behavior are tested in the site.
    for prefix in ("", "zh/"):
        technical = (public / f"{prefix}fixtures/table-layout-policy/index.html").read_text()
        technical_md = (public / f"{prefix}fixtures/table-layout-policy/index.md").read_text()
        require('<table id="wide-technical-table" class="wide td-table--wide">' in technical,
                f"{prefix} technical table lost its short width marker or style class", errors)
        require('<table id="configuration-keys-table" class="td-table--wide">' in technical,
                f"{prefix} technical table lost legacy width-marker compatibility", errors)
        require('class="matrix full-width wide td-table--wide td-table--matrix"' in technical,
                f"{prefix} wide marker displaced existing table modifiers", errors)
        require("HG_PD_GRPC_HOST" in technical_md and "{#wide-technical-table .wide}" in technical_md
                and "{#configuration-keys-table .td-table--wide}" in technical_md and "<table" not in technical_md,
                f"{prefix} technical table Markdown lost authored content or acquired HTML", errors)

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
    # Print remains a browser document before printing. Keep complete static
    # content and a labelled keyboard scroll region for the on-screen preview.
    require("td-table-scroll--static" in print_page, "print table wrapper is not marked static", errors)
    print_tables = re.findall(r'<div class="td-table-scroll[^>]*>', print_page)
    require(bool(print_tables) and all('tabindex="0"' in wrapper and 'role="region"' in wrapper and 'aria-label=' in wrapper for wrapper in print_tables), "Print preview lost its accessible table scroll regions", errors)
    print_trees = re.findall(r'<div class="td-filetree td-filetree--static"[\s\S]*?</ul></div></div>', print_page)
    require(any(">Site tree</p>" in tree and "<details" not in tree and tree.count("<li ") == 17 for tree in print_trees), "print FileTree is not the static, fully expanded tree", errors)
    require(print_trees and all("<details" not in tree for tree in print_trees), "print FileTree still uses <details>", errors)

    # Keep full descriptions in the actual row text in every output, including
    # CJK and unbroken tokens. Layout/resize checks live in the sibling site's
    # FileTree browser suite; text presence alone cannot detect CSS clipping.
    for language, suffix in (("", ""), ("zh/", ".zh")):
        source = (FIXTURE / f"content/fixtures/filetree-comments{suffix}.md").read_text()
        comments = re.findall(r" # (.+)$", source, re.MULTILINE)
        comment_page = (public / language / "fixtures/filetree-comments/index.html").read_text()
        comment_markdown = (public / language / "fixtures/filetree-comments/index.md").read_text()
        comment_print = (public / language / "_print/fixtures/index.html").read_text()
        rendered = re.findall(r'<span class="td-filetree__comment-text">([^<]*)</span>', comment_page)
        require(len(comments) == 8 and rendered == [escape(text) for text in comments],
                f"{language}FileTree long comments are missing from row text", errors)
        require(comment_page.count('data-td-filetree-divider') == 4,
                f"{language}FileTree long-comment fixtures lost their native dividers", errors)
        require(comment_page.count('class="td-filetree td-filetree--wrap"') == 2,
                f"{language}FileTree wrap must opt in only the two wrap=true trees", errors)
        require(comment_page.count('class="td-filetree"') == 2,
                f"{language}FileTree missing/false wrap must retain compact markup", errors)
        require(comment_markdown.count('wrap=true}') == 2 and comment_markdown.count('wrap=false}') == 1,
                f"{language}FileTree Markdown lost explicit wrap values", errors)
        require("td-filetree--wrap" not in comment_print,
                f"{language}FileTree screen wrapping must not change static Print markup", errors)
        for text in comments:
            require(text in comment_markdown,
                    f"{language}FileTree Markdown lost long comment {text}", errors)
            require(f'<span class="td-filetree__comment-text">{escape(text)}</span>' in comment_print,
                    f"{language}FileTree Print lost long comment {text}", errors)

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

    # --- Update headings (timeline-update fixture) ---------------------------
    updates_html = (public / "fixtures/timeline-update/index.html").read_text()
    updates_md = (public / "fixtures/timeline-update/index.md").read_text()
    require(
        '<div class="td-update-meta"><time datetime="2026-11-23">2026-11-23</time><span class="td-update-sep">, </span><span class="td-update-tag">Breaking</span><span class="td-update-sep">, </span><span class="td-update-tag">Performance</span></div>' in updates_html,
        "timeline-update HTML missing separated update metadata",
        errors,
    )
    require(
        re.search(r'<h2 id="pg-[0-9a-f]+--v160--plain-css-stylesheets" class="update">', print_page) is not None,
        "multi-page Print did not namespace the .update heading ID",
        errors,
    )
    require(
        '## v1.6.0 — Plain CSS stylesheets {.update date="2026-11-23" tags="Breaking, Performance"}' in updates_md
        and "td-update-meta" not in updates_md
        and "<time" not in updates_md,
        "timeline-update Markdown lost authored update syntax or leaked HTML",
        errors,
    )
    return errors


def check_subpath(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-subpath-") as temp:
        destination = Path(temp) / "public"
        result = run_hugo_process(
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
        result = run_hugo_process(
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
            "---\ntitle: Primitive feed\ndate: 2026-08-11\nweight: -100\n---\n\n"
            "| Key | Value |\n| --- | --- |\n| Feed table | Complete static content |\n\n"
            "```filetree\n- closed/\n  - nested.md\n```\n\n"
            "1. first\n1. second\n{.steps}\n\n"
            "```go-html-template\n"
            '{{</* badge text="Example only" */>}}\n'
            "```\n"
        )
        (content / "newest.md").write_text("---\ntitle: Newest\ndate: 2026-08-12\nweight: 1000\n---\nNewest entry.\n")
        (content / "undated.md").write_text("---\ntitle: Undated\nweight: -1000\n---\nUndated entry.\n")
        blog = site / "content/blog"
        blog.mkdir()
        for page in ("_index.md", "item.md", "newest.md", "undated.md"):
            (blog / page).write_text((content / page).read_text())
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
        result = run_hugo_process(
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
        rss_tables = re.findall(r'<div class="td-table-scroll[^>]*>', unescape(source))
        require(bool(rss_tables) and all('td-table-scroll--static' in wrapper and 'tabindex=' not in wrapper and 'role=' not in wrapper for wrapper in rss_tables), "RSS table acquired browser scroll focus semantics", errors)
        home_source = (destination / "index.xml").read_text()
        require("<title>Generic primitive feed</title>" in home_source, "generic RSS home title repeats the site title", errors)
        for marker in ('&lt;pre class=&#34;td-filetree-source&#34;&gt;', "nested.md", '&lt;ol class=&#34;steps&#34;&gt;', "Example only"):
            require(marker in source, f"generic RSS primitive fixture missing {marker}", errors)
        for marker in ("td-filetree__row", "&lt;details"):
            require(marker not in source, f"generic RSS primitive fixture leaked interactive FileTree markup {marker}", errors)
        require("td-badge td-badge" not in source, "generic RSS primitive fixture rendered the escaped example", errors)
        require("Nested child must not enter" not in source, "generic section RSS recursively included a nested section page", errors)
        for feed_path in ("docs/index.xml", "blog/index.xml"):
            feed = ET.fromstring((destination / feed_path).read_text())
            items = feed.findall("channel/item")
            require(items[0].findtext("title") == "Newest", f"{feed_path}: feed order followed weights instead of dates", errors)
            undated = next(item for item in items if item.findtext("title") == "Undated")
            require(undated.find("pubDate") is None, f"{feed_path}: undated item has a fabricated date", errors)
        with (site / "hugo.yaml").open("a") as config:
            config.write("services:\n  rss:\n    limit: 1\n")
        limited = run_hugo_process([hugo, "--source", str(site), "--themesDir", str(ROOT.parent),
                                   "--destination", str(destination), "--logLevel", "warn"],
                                  cwd=ROOT, capture_output=True, text=True, check=False)
        require(limited.returncode == 0, f"limited feed build failed: {limited.stdout}{limited.stderr}", errors)
        if limited.returncode == 0:
            for feed_path in ("docs/index.xml", "blog/index.xml"):
                items = ET.fromstring((destination / feed_path).read_text()).findall("channel/item")
                require([item.findtext("title") for item in items] == ["Newest"],
                        f"{feed_path}: limit dropped the latest entry", errors)
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
        result = run_hugo_process(
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
        '<div class="td-field" id="field-alpha" data-td-search-entry="alpha">',
        '<div class="td-field" id="field-alpha-2" data-td-search-entry="alpha">',
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
        # An anchored field names itself, so local search can open it by name.
        require(f'<div class="td-field" id="{anchor}" data-td-search-entry="{name}">' in html,
                f"field {name!r} did not anchor as {anchor!r} or lost its search-entry name", errors)
    return errors


def check_field_ids(html: str, log: str) -> list[str]:
    """An author-chosen field id is used as written; a bad one falls back."""
    errors: list[str] = []
    for marker in (
        '<div class="td-field" id="guc-work-mem" data-td-search-entry="work_mem">',
        'href="#guc-work-mem" aria-label="Link to this field"',
        '<div class="td-field" id="field-copy" data-td-search-entry="copy">',
        '<div class="td-field" id="field-spaced" data-td-search-entry="spaced">',
        '<div class="td-field" id="field-leading" data-td-search-entry="leading">',
        '<div class="td-field" id="field-trailing" data-td-search-entry="trailing">',
        '<div class="td-field" id="field-unicode" data-td-search-entry="unicode">',
        '<div class="td-field" id="字段-id" data-td-search-entry="valid">',
    ):
        require(marker in html, f"explicit field id fixture missing {marker}", errors)
    require(html.count('id="guc-work-mem"') == 1, "a repeated field id reached the page twice", errors)
    for warning in ('id "guc-work-mem" is already used', 'id "has space" contains unsupported characters',
                    'id " leading" contains unsupported characters', 'id "trailing " contains unsupported characters',
                    r'id "em\u2003space" contains unsupported characters'):
        require(warning in log, f"explicit field id fixture did not warn: {warning}", errors)
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
        require(re.search(rf'<div class="td-field" id="{anchor}" data-td-search-entry="[^"]+">', html) is not None,
                f"the scope fixture lost its {anchor} entry", errors)
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
            + TABLE + '{.fields .wide .site-fields data-fixture="fields"}\n\n'
            "## Short and legacy width markers can coexist\n\n"
            + TABLE + '{#wide-both .wide .td-table--wide}\n\n'
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
            "{{< /fields >}}\n\n"
            "## An author may choose a field's anchor\n\n"
            "{{< fields >}}\n"
            '{{< field name="work_mem" type="integer" id="guc-work-mem" >}}Chosen{{< /field >}}\n'
            '{{< field name="copy" id="guc-work-mem" >}}Repeated{{< /field >}}\n'
            '{{< field name="spaced" id="has space" >}}Unsupported{{< /field >}}\n'
            '{{< field name="leading" id=" leading" >}}Leading space{{< /field >}}\n'
            '{{< field name="trailing" id="trailing " >}}Trailing space{{< /field >}}\n'
            '{{< field name="unicode" id="em\u2003space" >}}Unicode space{{< /field >}}\n'
            '{{< field name="valid" id="字段-id" >}}Unicode letters{{< /field >}}\n'
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
        result = run_hugo_process(
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
            '<div class="td-fields wide site-fields" data-fixture="fields">',
            '<table id="wide-both" class="wide td-table--wide">',
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
        errors += check_field_ids(parity, result.stdout + result.stderr)
        require(html.count('data-td-language="yaml"') == 2 and 'data-td-language="js"' in html, "include code=true did not highlight the included files", errors)
        require("td-table--matrix" not in html and "<p>{.matrix}</p>" not in html, "an orphan attribute line was applied or printed", errors)
        require(html.count("<table") == 3, "table family fixture rendered a wrong number of tables", errors)
    return errors


def check_table_reader(hugo: str) -> list[str]:
    """Explicit opt-in, class composition, localization and static degradation."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-table-reader-") as temp:
        site = Path(temp)
        content = site / "content/docs"
        content.mkdir(parents=True)
        attributes = (
            '{#reader-alone .expand}',
            '{#reader-wide .wide .expand}',
            '{#reader-classes class="wide expand"}',
            '{#reader-matrix .matrix .full-width .expand caption="Matrix caption"}',
            '{#reader-numbered .expand num="7-1" caption="Numbered caption"}',
            '{#reader-tab .expand tab="Table tab"}',
        )
        for suffix in ("", ".zh"):
            (content / f"_index{suffix}.md").write_text("---\ntitle: Reader fixtures\n---\n")
            (content / f"reader{suffix}.md").write_text(
                "---\ntitle: Table reader\noutputs: [HTML, markdown, print]\n---\n\n"
                + "\n".join(TABLE + attrs + "\n" for attrs in attributes)
            )
            (content / f"plain{suffix}.md").write_text("---\ntitle: Plain table\n---\n\n" + TABLE + "{.wide}\n")
            (content / f"fields{suffix}.md").write_text("---\ntitle: Field list\n---\n\n" + TABLE + "{.fields .expand}\n")
        destination = site / "public"
        result = run_hugo_process(
            [hugo, "--source", str(FIXTURE), "--themesDir", str(ROOT.parent),
             "--contentDir", str(site / "content"), "--destination", str(destination), "--logLevel", "warn"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        if result.returncode:
            return [f"table reader fixture failed: {result.stdout}{result.stderr}"]
        require(".fields cannot be combined with .expand" in result.stdout + result.stderr,
                "fields/expand conflict did not warn", errors)
        for prefix, label in (("", "Expand table"), ("zh/", "展开表格")):
            html = (destination / f"{prefix}docs/reader/index.html").read_text()
            require(html.count('data-td-table-expand>') == len(attributes), "reader opt-ins lost wrappers", errors)
            require(html.count('data-td-table-reader aria-labelledby=') == 1 and label in html,
                    f"{prefix} reader lost its single localized dialog", errors)
            require('<table id="reader-wide" class="wide expand td-table--wide">' in html
                    and '<table id="reader-classes" class="wide expand td-table--wide">' in html,
                    "multiple classes changed table sizing/reader semantics", errors)
            require('scope="row"' in html and 'Numbered caption' in html and 'data-td-tab="Table tab"' in html,
                    "reader displaced matrix, numbered or tab semantics", errors)
            chunks = [item for item in referenced_chunks(destination, html) if item.name == "table-reader"]
            require(len(chunks) == 1 and chunks[0].path.is_file(), "reader runtime missing or duplicated", errors)
            for name in ("plain", "fields"):
                plain = (destination / f"{prefix}docs/{name}/index.html").read_text()
                require("data-td-table-reader" not in plain and "js/chunks/table-reader" not in plain,
                        f"{name} table loaded the reader without an eligible opt-in", errors)
            markdown = (destination / f"{prefix}docs/reader/index.md").read_text()
            require(all(attrs in markdown for attrs in attributes), "Markdown lost authored reader classes", errors)
            static_outputs = (
                (destination / f"{prefix}_print/docs/reader/index.html").read_text(),
                unescape((destination / f"{prefix}docs/index.xml").read_text()),
                markdown,
            )
            for output in static_outputs:
                require("reader-wide" in output and "Numbered caption" in output,
                        "reader static output lost content", errors)
                require("data-td-table-reader" not in output and "data-td-table-expand" not in output
                        and "js/chunks/table-reader" not in output, "reader leaked into static output", errors)
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
    ("filetree-wrap-bad", "```filetree {wrap=yes}\n- a # comment\n```\n", "wrap must be true or false"),
    ("filetree-wrap-empty", "```filetree {wrap=\"\"}\n- a # comment\n```\n", "wrap must be true or false"),
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
    # Offline social posts: every invalid input warns at its position and keeps
    # the quoted words whenever a body exists.
    ("social-platform", '{{< social author="A" platform="myspace" >}}Hi{{< /social >}}\n', "platform must be one of"),
    ("social-platform-empty", '{{< social author="A" platform="" >}}Hi{{< /social >}}\n', "platform must be one of"),
    ("social-platform-type", '{{< social author="A" platform=true >}}Hi{{< /social >}}\n', "platform must be a string"),
    ("social-author-type", '{{< social author=true handle="@a" >}}Hi{{< /social >}}\n', "author must be a string"),
    ("social-handle-type", '{{< social author="A" handle=123 >}}Hi{{< /social >}}\n', "handle must be a string"),
    ("social-date-type", '{{< social author="A" date=2026 >}}Hi{{< /social >}}\n', "date must be a string"),
    ("social-empty", '{{< social author="A" />}}\n', "has no body and no url"),
    ("social-empty-link", '{{< social author="A" url="https://x.com/a/status/1" />}}\n', "rendering a link to the original post"),
    ("social-anonymous", '{{< social >}}Hi{{< /social >}}\n', "requires author or handle"),
    ("social-anon-empty-link", '{{< social url="https://example.com/1" />}}\n', "requires author or handle and has no body"),
    ("social-url", '{{< social author="A" url="javascript:alert(1)" >}}Hi{{< /social >}}\n', "unsupported url scheme"),
    ("social-avatar-scheme", '{{< social author="A" avatar="javascript:alert(1)" >}}Hi{{< /social >}}\n', "unsupported avatar scheme"),
    ("social-avatar-missing", '{{< social author="A" avatar="/images/does-not-exist-social.png" >}}Hi{{< /social >}}\n', "was not found as a page/assets resource or under static/"),
    ("social-avatar-missing-dotdot", '{{< social author="A" avatar="/images/../images/does-not-exist-social.png" >}}Hi{{< /social >}}\n', "was not found as a page/assets resource or under static/"),
    ("social-avatar-parent", '{{< social author="A" avatar="../images/oink.webp" >}}Hi{{< /social >}}\n', "climbs above the site root"),
    ("social-deep-nesting", '{{< social author="A" >}}L1\n{{< social author="B" >}}L2\n{{< social author="C" >}}L3{{< /social >}}{{< /social >}}{{< /social >}}\n', "nested deeper than one quoted post"),
    ("social-unknown", '{{< social author="A" likes="1K" >}}Hi{{< /social >}}\n', "unsupported parameter"),
    # Map fences: invalid places are skipped with a warning; valid siblings stay.
    ("map-empty", '```map\n```\n', "requires a list of places"),
    ("map-not-list", '```map\nname: A\n```\n', "must hold a list of places"),
    ("map-no-name", '```map\n- {lat: 1, lng: 2}\n- {name: B, lat: 1, lng: 2}\n```\n', "requires a name"),
    ("map-non-string-name", '```map\n- {name: [A, B], lat: 1, lng: 2}\n- {name: OK, lat: 1, lng: 2, link: "https://example.org/ok"}\n```\n', "name must be a string"),
    ("map-non-string-text", '```map\n- {name: A, lat: 1, lng: 2, text: {k: v}}\n```\n', "text must be a string"),
    ("map-range", '```map\n- {name: A, lat: 95, lng: 2}\n```\n', "outside -90..90"),
    ("map-nan", '```map\n- {name: A, lat: .nan, lng: 2}\n- {name: B, lat: 0.00001, lng: -0.00002}\n```\n', "outside -90..90"),
    ("map-inf", '```map\n- {name: A, lat: .inf, lng: 2}\n```\n', "outside -90..90"),
    ("map-string-lat", '```map\n- {name: A, lat: "1", lng: 2}\n```\n', "requires numeric lat and lng"),
    ("map-bad-link", '```map\n- {name: A, lat: 1, lng: 2, link: "javascript:alert(1)"}\n```\n', "unsupported place 1 link scheme"),
    ("map-unknown-field", '```map\n- {name: A, lat: 1, lng: 2, icon: x}\n```\n', "unknown field"),
    ("map-zoom", '```map {zoom=40}\n- {name: A, lat: 1, lng: 2}\n```\n', "zoom must be a whole number"),
    ("map-zoom-leading-zero", '```map {zoom="08"}\n- {name: A, lat: 1, lng: 2}\n```\n', "zoom must be a whole number"),
    ("map-route", '```map {route=maybe}\n- {name: A, lat: 1, lng: 2}\n```\n', "route must be true or false"),
)


def check_timeline(hugo: str) -> list[str]:
    """Native `{.timeline}` definition lists: static four-format output with zero
    runtime, plus build-time warnings and safe fallbacks for detached markers,
    non-<dl> targets, disabled definitionList, and callout-header collisions."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-timeline-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "valid.md").write_text(
            "---\ntitle: Valid timeline\noutputs: [HTML, print, markdown]\n---\n\n"
            "2024-05\n: **First.** Opening event.\n\n"
            "2025-08\n: **Second.** First paragraph.\n\n  Second paragraph.\n: Same marker follow-up.\n"
            "{.timeline}\n\n"
            "> [!NOTE] Timeline in callout\n>\n> 2026-01\n> : Safe with a blank quote line.\n> {.timeline}\n\n"
            "````markdown\n2026-02\n: Fenced example.\n\n```sh\necho ok\n```\n\n{.timeline}\n````\n\n"
            "Indented code block:\n\n"
            "    2026-03\n    : Indented example.\n\n    {.timeline}\n\n"
            "Literal JSON:\n\n"
            '{"class": ".timeline"}\n\n'
            "Project styling.\n{.release-timeline}\n\n"
            "Project metadata.\n{data-class=\"timeline\"}\n\n"
            + "~" * 1001 + "markdown\n~~~\n\n{.timeline}\n" + "~" * 1002 + "\n"
        )
        (content / "detached.md").write_text(
            "---\ntitle: Detached timeline\n---\n\n2024-05\n: Event.\n\n{.timeline}\n"
        )
        (content / "detached-quoted.md").write_text(
            '---\ntitle: Detached quoted timeline\n---\n\n'
            'Indented lone fence:\n\n'
            '    ```markdown\n\n'
            '2024-05\n: Event.\n\n{data-x="1" .timeline}\n'
        )
        (content / "wrong-block.md").write_text(
            "---\ntitle: Wrong block timeline\n---\n\n- **2024-05.** Bullet item.\n{.timeline}\n"
        )
        (content / "callout-swallow.md").write_text(
            "---\ntitle: Callout swallow\n---\n\n> [!NOTE] Swallowed\n> 2026-01\n> : Missing blank quote line.\n> {.timeline}\n"
        )
        result = run_hugo_process(
            [hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--logLevel", "warn",
             "--destination", str(temp_path / "public")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        output = result.stdout + result.stderr
        require(result.returncode == 0, f"timeline probe failed to build: {output.strip()[-400:]}", errors)
        require("/docs/valid" not in output, f"valid timeline (with 4-backtick fence and callout) emitted a false warning: {output.strip()[-400:]}", errors)
        require("preceded by a blank line" in output and "/docs/detached" in output,
                f"detached {{.timeline}} did not warn with the page path: {output.strip()[-400:]}", errors)
        require("preceded by a blank line" in output and "/docs/detached-quoted" in output,
                f"detached quoted {{data-x=\"1\" .timeline}} did not warn with the page path: {output.strip()[-400:]}", errors)
        require("applies only to a Markdown definition list (<dl>), not <ul>" in output and "/docs/wrong-block" in output,
                f"bullet-list {{.timeline}} did not warn with the page path: {output.strip()[-400:]}", errors)
        require("callout header (> [!TYPE]) was parsed as a definition-list term" in output and "/docs/callout-swallow" in output,
                f"callout-swallowed timeline did not warn with the page path: {output.strip()[-400:]}", errors)

        valid_html = (temp_path / "public/docs/valid/index.html").read_text()
        valid_md = (temp_path / "public/docs/valid/index.md").read_text()
        valid_print = (temp_path / "public/_print/docs/valid/index.html").read_text()
        valid_rss = unescape((temp_path / "public/docs/index.xml").read_text())
        require(valid_html.count('<dl class="timeline">') == 2, "valid timeline HTML missing main or callout <dl class=\"timeline\">", errors)
        require('class="td-callout td-callout--note"' in valid_html, "callout with blank '>' line failed to stay a callout", errors)
        require(valid_print.count('<dl class="timeline">') == 2, "valid timeline Print lost <dl class=\"timeline\">", errors)
        require('{.timeline}' in valid_md and '<dl' not in valid_md, "valid timeline Markdown lost source or leaked HTML", errors)
        require('<dl class="timeline">' in valid_rss, "valid timeline RSS lost <dl class=\"timeline\">", errors)
        require((temp_path / "public/docs/detached/index.html").is_file()
                and (temp_path / "public/docs/wrong-block/index.html").is_file()
                and (temp_path / "public/docs/callout-swallow/index.html").is_file(),
                "invalid timeline cases lost their safe fallback HTML", errors)

        # Also verify check-site-markup.py rejects definitionList: false.
        no_dl = temp_path / "no-dl"
        (no_dl / "content/docs").mkdir(parents=True)
        (no_dl / "hugo.yaml").write_text(
            "baseURL: https://example.org/\n"
            "title: No DL\n"
            f"theme: {ROOT.name}\n"
            f"themesDir: {ROOT.parent}\n"
            "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n"
            "    parser:\n      wrapStandAloneImageWithinParagraph: false\n"
            "      attribute:\n        block: true\n"
            "    extensions:\n      definitionList: false\n"
        )
        (no_dl / "content/docs/page.md").write_text("---\ntitle: P\n---\n\n2024-05\n: Event.\n{.timeline}\n")
        preflight = run_hugo_process(
            ["python3", str(ROOT / "bin/check-site-markup.py"), "--site", str(no_dl), "--hugo", hugo],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        require(preflight.returncode == 1 and "definitionList: true" in (preflight.stdout + preflight.stderr),
                f"check-site-markup.py did not reject definitionList: false: {preflight.stdout}{preflight.stderr}", errors)
        no_dl_build = run_hugo_process(
            [hugo, "--source", str(no_dl), "--logLevel", "warn", "--destination", str(no_dl / "public")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        no_dl_out = no_dl_build.stdout + no_dl_build.stderr
        require(no_dl_build.returncode == 0 and "not <p>" in no_dl_out and "definitionList" in no_dl_out,
                f"definitionList: false page build did not warn cleanly: {no_dl_out}", errors)
    return errors


def check_social_posts(hugo: str) -> list[str]:
    """Social shortcode: platforms, nested symmetry, grapheme initials, dates,
    internal URLs, degraded outputs, and context-aware Markdown/RSS escaping."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-social-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Social tests\n---\n")
        (content / "cases.md").write_text(
            "---\n"
            "title: Social edge cases\n"
            "date: 2026-11-26\n"
            "outputs: [HTML, print, markdown]\n"
            "---\n\n"
            '{{< social author="Lin Shu" handle="@linshu" platform="zhihu" date="2026-02" url="/docs/cases/" >}}\n'
            "Internal link and year-month date.\n"
            "{{< /social >}}\n\n"
            '{{< social author="Maya" handle="@maya_dev" platform="telegram" date="2026-02-15T08:30+08:00" >}}\n'
            "Timezone offset datetime.\n"
            "{{< /social >}}\n\n"
            '{{< social author="Nadia" handle="@nadia" platform="none" date="Feb 15, 2026" >}}\n'
            "No platform icon and non-ISO date.\n"
            "{{< /social >}}\n\n"
            '{{< social author="Leap" date="2026-02-29" >}}Invalid calendar date.{{< /social >}}\n\n'
            '{{< social author="👩‍💻 Dev" handle="@dev" >}}ZWJ grapheme initial.{{< /social >}}\n\n'
            '{{< social author="🇨🇳 Lab" handle="@lab" >}}Flag grapheme initial.{{< /social >}}\n\n'
            '{{< social handle="@" >}}Bare at-sign fallback.{{< /social >}}\n\n'
            '{{< social handle="@@double" >}}Double at-sign initial.{{< /social >}}\n\n'
            '{{< social author="Outer" handle="@outer" platform="mastodon" >}}\n'
            "Quoting two posts.\n\n"
            '{{< social author="Implicit" handle="@imp" >}}No platform set.{{< /social >}}\n\n'
            '{{< social author="Explicit" handle="@exp" platform="bluesky" >}}Cross-platform quote.{{< /social >}}\n'
            "{{< /social >}}\n\n"
            '{{< social author="A *B* [C](x) <img src=x> &lt; a@b.co https://e.co" handle="@u`1" date="2026-11-26" url="https://example.com/1" >}}\n'
            "Markdown escaping stress test.\n"
            "{{< /social >}}\n\n"
            '{{< social author="Link Only" url="/docs/cases/" />}}\n\n'
            '## Station {#station}\n\n'
            '{{< social author="Local" url="#station" >}}Station notes.{{< /social >}}\n\n'
            '```map\n- {name: Station, lat: 1, lng: 2, link: "?layer=3#station"}\n```\n\n'
            '{{< social url="https://example.com/anon" />}}\n\n'
            # Invisible leading characters never become the drawn initial.
            '{{< social handle="@\u200bghost" >}}Zero-width space after the at-sign.{{< /social >}}\n\n'
            '{{< social author="\ufeff\u2066Zed\u2069" >}}BOM and bidi isolate before the name.{{< /social >}}\n\n'
            '{{< social handle="@\u3000\u00a0\u200b" >}}Only invisible characters after the at-sign.{{< /social >}}\n\n'
            # Static avatars are checked by their decoded, cleaned path.
            '{{< social author="Encoded" avatar="/images/%6Fink.webp?v=2" >}}Percent-encoded static avatar.{{< /social >}}\n\n'
            '{{< social author="Dotted" avatar="/images/../images/oink.webp" >}}Dot segments in a static avatar.{{< /social >}}\n\n'
            '{{< social author="Missing" avatar="/images/missing-social-avatar.png" >}}Missing static avatar.{{< /social >}}\n\n'
            # Cards on consecutive lines stay separate quotations in Markdown.
            '{{< social author="Adjacent One" >}}First adjacent post.{{< /social >}}\n'
            '{{< social author="Adjacent Two" >}}Second adjacent post.{{< /social >}}\n'
            "\n<!--more-->\n"
        )
        result = run_hugo_process(
            [hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"),
             "--logLevel", "warn", "--destination", str(temp_path / "public")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        output = result.stdout + result.stderr
        require(result.returncode == 0, f"social edge cases failed to build: {output.strip()[-400:]}", errors)
        # Anonymous empty+url must emit one unified warning, not two contradictory ones.
        anon_lines = [line for line in output.splitlines() if "requires author or handle and has no body" in line]
        require(len(anon_lines) >= 1, "anonymous empty+url did not emit unified warning", errors)
        html = unescape((temp_path / "public/docs/cases/index.html").read_text())
        print_html = unescape((temp_path / "public/_print/docs/cases/index.html").read_text())
        md = (temp_path / "public/docs/cases/index.md").read_text()
        rss = unescape((temp_path / "public/docs/index.xml").read_text())

        # Platforms: zhihu, telegram, none, and nested platform symmetry.
        require("fa-brands fa-zhihu" in html and " · Zhihu" in html, "zhihu platform icon or label missing", errors)
        require("fa-brands fa-telegram" in html and " · Telegram" in html, "telegram platform icon or label missing", errors)
        require("td-social--none" in html, "platform=none class missing", errors)
        # Nested quote without platform must not fabricate X; explicit nested platform must render icon + label.
        require('<figure class="td-social td-social--none td-social--nested">' in html, "nested quote without platform did not default to none", errors)
        require('<figure class="td-social td-social--bluesky td-social--nested">' in html
                and 'fa-brands fa-bluesky' in html, "nested explicit cross-platform quote lost icon/class", errors)
        # Dates: valid YYYY-MM and offset datetime get <time datetime>; non-ISO and invalid calendar date get <span class="td-social__date">.
        require('<time datetime="2026-02">2026-02</time>' in html, "YYYY-MM date lost <time datetime>", errors)
        require('<time datetime="2026-02-15T08:30+08:00">2026-02-15T08:30+08:00</time>' in html, "offset datetime lost <time datetime>", errors)
        require('<span class="td-social__date">Feb 15, 2026</span>' in html and '<time>Feb 15, 2026</time>' not in html,
                "non-ISO date emitted invalid <time> without datetime", errors)
        require('<span class="td-social__date">2026-02-29</span>' in html and 'datetime="2026-02-29"' not in html,
                "impossible calendar date emitted <time datetime>", errors)
        # Grapheme initials & fallback icon.
        require('>👩‍💻</span>' in html, "ZWJ emoji initial was split", errors)
        require('>🇨🇳</span>' in html, "flag emoji initial was split", errors)
        require('><i class="fa-solid fa-user" aria-hidden="true"></i></span>' in html, "bare @ handle did not fall back to user icon", errors)
        require('>D</span>' in html, "double @@ handle did not strip all leading @", errors)
        require('aria-hidden="true">G</span>' in html and 'aria-hidden="true">\u200b</span>' not in html,
                "zero-width space after @ became an invisible initial", errors)
        require('aria-hidden="true">Z</span>' in html, "BOM/bidi isolate before the name became the initial", errors)
        require(html.count('><i class="fa-solid fa-user" aria-hidden="true"></i></span>') >= 2,
                "space-only handle did not fall back to the user icon", errors)
        # Static avatar check: decoded and cleaned paths resolve; a missing file
        # warns with an ID that a site using mounts or staticDir can ignore.
        static_warnings = [line for line in output.splitlines() if "was not found as a page/assets resource or under static/" in line]
        require(not any("%6Fink" in line or "/images/../images/oink" in line for line in static_warnings),
                f"existing static avatar reported missing: {static_warnings}", errors)
        require(any("missing-social-avatar.png" in line for line in static_warnings),
                "missing static avatar did not warn", errors)
        require("ignoreLogs = ['social:avatar-static']" in output,
                "missing static avatar warning is not suppressible by ID", errors)
        # Markdown: a card on the next line starts a new quotation.
        require("> — Adjacent One · X\n\n> Second adjacent post." in md,
                "adjacent cards merged into one Markdown blockquote", errors)
        # Accessible spacing, RTL bidi attributes, link author context, and internal URL rel="external" policy.
        require('<span class="td-social__name" dir="auto">Lin Shu</span> <span class="td-social__handle" dir="ltr">@linshu</span>' in html,
                "name/handle spacing or dir attributes missing", errors)
        require('<a href="/docs/cases/">' in html and '<a href="/docs/cases/" rel="external">' not in html,
                "internal url incorrectly emitted rel=external", errors)
        require('<span class="visually-hidden"> — Lin Shu</span></a>' in html, "meta link missing author context for screen readers", errors)
        # Anonymous empty+url renders a link in HTML, Print, RSS, and Markdown.
        anon_link = '<blockquote class="td-social-quote" cite="https://example.com/anon"><p><a href="https://example.com/anon" rel="external">View original</a></p></blockquote>'
        require(anon_link in html and anon_link in print_html, "anonymous empty+url lost link in HTML/Print", errors)
        require('<blockquote class="td-social-quote" cite="https://example.com/anon"><p><a href="https://example.com/anon">View original</a></p></blockquote>' in rss,
                "anonymous empty+url lost link in RSS", errors)
        require('> [View original](https://example.com/anon)' in md, "anonymous empty+url lost link in Markdown", errors)
        # RSS: no empty <blockquote> on link-only card, and internal URL is absolute.
        require('<figure class="td-social"><figcaption>— Link Only · X · <a href="https://example.org/docs/cases/">View original</a></figcaption></figure>' in rss,
                "RSS link-only card emitted empty blockquote or relative URL", errors)
        require('cite="https://example.org/docs/cases/"' in rss, "RSS internal cite URL was not absolutized", errors)
        require('cite="https://example.org/docs/cases/#station"' in rss
                and 'href="https://example.org/docs/cases/#station"' in rss
                and 'href="https://example.org/docs/cases/?layer=3#station"' in rss,
                "RSS citations and place links must resolve against the source article", errors)
        require('cite="#station"' in html and 'href="?layer=3#station"' in html,
                "HTML should retain page-local citation and place links", errors)
        # Markdown: clean readable attribution without backslash spam, while escaping dangerous syntax.
        require('> — Lin Shu (`@linshu`) · Zhihu · 2026-02 · [View original](/docs/cases/)' in md,
                f"Markdown attribution format mismatch: {md}", errors)
        require('> — Nadia (`@nadia`) · Feb 15, 2026' in md, "platform=none leaked platform into Markdown", errors)
        require('> > — Implicit (`@imp`)' in md and 'Implicit (`@imp`) · X' not in md,
                "nested implicit quote fabricated X in Markdown", errors)
        require('> > — Explicit (`@exp`) · Bluesky' in md, "nested explicit quote lost platform in Markdown", errors)
        require(r'A \*B\* \[C\](x) \<img src=x\> \&lt; a\@b.co https\://e.co (\@u\`1)' in md
                or r'A \*B\* \[C\](x) \<img src=x\> \&lt; a\@b.co https\://e.co (@u\`1)' in md,
                f"Markdown inline escape failed on adversarial attribution: {md}", errors)
    return errors


def check_update_headings(hugo: str) -> list[str]:
    """`.update` headings: valid metadata renders with accessible/search separators,
    invalid dates or non-string attributes warn and drop safely while keeping the
    entry and remaining valid metadata, and date/tags without the marker stay
    unsupported attributes. The heading hook has no source position, so it names
    the page path."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-update-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "updates.md").write_text(
            "---\ntitle: Updates\n---\n\n"
            '## v2 {#v2 .update date="2026-11" tags="Added, , Fixed"}\n\nBody.\n\n'
            '## Year only {#y2026 .update date="2026"}\n\nBody.\n\n'
            '## Leap day {#leap .update date="2024-02-29" tags="修复，性能， , 安全"}\n\nBody.\n\n'
            '## Tags only {#tags-only .update tags="Alpha, Beta"}\n\nBody.\n\n'
            '## Bad month {#bad-month .update date="2026-13-01"}\n\nBody.\n\n'
            '## Bad calendar {#bad-cal .update date="2026-02-30" tags="Kept"}\n\nBody.\n\n'
            '## Non-leap {#non-leap .update date="2025-02-29"}\n\nBody.\n\n'
            '## Timestamp {#bad-ts .update date="2026-11-23T12:00:00Z"}\n\nBody.\n\n'
            '## Numeric date {#num-date .update date=2026 tags=true}\n\nBody.\n\n'
            '## Escaped tags {#escaped .update tags="A&B, <script>x</script>, **bold**"}\n\nBody.\n\n'
            '## No marker date {date="2026-01-01"}\n\nBody.\n\n'
            '## No marker tags {tags="Breaking"}\n\nBody.\n'
        )
        override_cfg = temp_path / "update-search.yaml"
        override_cfg.write_text("params:\n  offline_search_index: content\n")
        result = run_hugo_process(
            [hugo, "--source", str(FIXTURE), "--config", f"{FIXTURE / 'hugo.yaml'},{override_cfg}",
             "--contentDir", str(temp_path / "content"), "--logLevel", "warn",
             "--destination", str(temp_path / "public")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        output = result.stdout + result.stderr
        require(result.returncode == 0, f"update headings failed to build: {output.strip()[-400:]}", errors)
        for snippet, label in (
            ('got "2026-13-01" in /docs/updates', "invalid month"),
            ('got "2026-02-30" in /docs/updates', "invalid calendar date 2026-02-30"),
            ('got "2025-02-29" in /docs/updates', "non-leap date 2025-02-29"),
            ('got "2026-11-23T12:00:00Z" in /docs/updates', "timestamp date"),
            ("update date must be YYYY, YYYY-MM or YYYY-MM-DD (string)", "non-string date"),
            ("update tags must be a string", "non-string tags"),
            ('unknown attribute "date"', "orphan date without .update"),
            ('unknown attribute "tags"', "orphan tags without .update"),
        ):
            require(snippet in output, f"update headings missing warning for {label}: {output.strip()[-600:]}", errors)
        page = temp_path / "public/docs/updates/index.html"
        if page.is_file():
            html = page.read_text()
            for expected, label in (
                ('<div class="td-update-meta"><time datetime="2026-11">2026-11</time><span class="td-update-sep">, </span><span class="td-update-tag">Added</span><span class="td-update-sep">, </span><span class="td-update-tag">Fixed</span></div>', "date + tags with separators"),
                ('<div class="td-update-meta"><time datetime="2026">2026</time></div>', "year-only date without stray comma"),
                ('<div class="td-update-meta"><time datetime="2024-02-29">2024-02-29</time><span class="td-update-sep">, </span><span class="td-update-tag">修复</span><span class="td-update-sep">, </span><span class="td-update-tag">性能</span><span class="td-update-sep">, </span><span class="td-update-tag">安全</span></div>', "leap day and full-width Chinese comma tags"),
                ('<div class="td-update-meta"><span class="td-update-tag">Alpha</span><span class="td-update-sep">, </span><span class="td-update-tag">Beta</span></div>', "tags-only without leading comma"),
                ('<div class="td-update-meta"><span class="td-update-tag">Kept</span></div>', "invalid calendar date drops date while keeping valid tags"),
                ('<div class="td-update-meta"><span class="td-update-tag">A&amp;B</span><span class="td-update-sep">, </span><span class="td-update-tag">&lt;script&gt;x&lt;/script&gt;</span><span class="td-update-sep">, </span><span class="td-update-tag">**bold**</span></div>', "plain-text escaping in tags"),
            ):
                require(expected in html, f"update metadata mismatch for {label}", errors)
            require('id="bad-month" class="update"' in html and 'id="non-leap" class="update"' in html and 'id="num-date" class="update"' in html,
                    "invalid metadata dropped the update heading itself", errors)
            require(html.count('class="td-update-meta"') == 6,
                    f"expected 6 update metadata rows, found {html.count('class=\"td-update-meta\"')}", errors)
            require("<script>x</script>" not in html and "<strong>bold</strong>" not in html,
                    "update tags did not stay escaped plain text", errors)
        else:
            errors.append("update headings lost their safe output")

        # Verify offline search index keeps date and tags separated instead of glued.
        search_indices = sorted((temp_path / "public").glob("offline-search-index*.json"))
        if search_indices:
            records = json.loads(search_indices[0].read_text())
            updates_rec = next((r for r in records if r.get("ref") == "/docs/updates/"), None)
            require(updates_rec is not None, "updates page missing from offline search index", errors)
            if updates_rec:
                body = updates_rec.get("body", "")
                require("2026-11, Added, Fixed" in body and "2026-11AddedFixed" not in body,
                        f"offline search index glued update metadata: {body[:200]!r}", errors)
                require("2024-02-29, 修复, 性能, 安全" in body,
                        f"offline search index lost separated CJK update tags: {body[:300]!r}", errors)
        else:
            errors.append("offline search index missing for update headings check")

        # Verify RSS keeps separated metadata so feed readers do not glue tokens.
        rss_path = temp_path / "public/docs/index.xml"
        if rss_path.is_file():
            rss = rss_path.read_text()
            require("2026-11&lt;/time&gt;&lt;span class=&#34;td-update-sep&#34;&gt;, &lt;/span&gt;&lt;span class=&#34;td-update-tag&#34;&gt;Added" in rss,
                    "RSS output missing update metadata separator", errors)
    return errors


def check_invalid_cases(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-invalid-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        content.mkdir(parents=True)
        for name, body, _ in INVALID_CASES:
            (content / f"{name}.md").write_text(f"---\ntitle: Invalid {name}\n---\n\n{body}")
        (content / "param-map.md").write_text("---\ntitle: Param map\nparams:\n  fixture_map:\n    a: 1\n---\n\n{{< param fixture_map >}}\n")
        command = [hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--logLevel", "warn"]
        result = run_hugo_process(
            [*command, "--destination", str(temp_path / "public")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        output = result.stdout + result.stderr
        require(result.returncode == 0, f"batched invalid cases failed to render safely: {output.strip()}", errors)
        for name, _, expected in INVALID_CASES:
            case_output = "\n".join(line for line in output.splitlines() if f"content/docs/{name}.md:" in line)
            require(expected in case_output, f"invalid case {name} did not report {expected!r} at its position: {case_output or output.strip()}", errors)
            require((temp_path / f"public/docs/{name}/index.html").is_file(), f"invalid case {name} lost its safe output", errors)
        for name in ("filetree-wrap-bad", "filetree-wrap-empty"):
            rendered = (temp_path / f"public/docs/{name}/index.html").read_text()
            require("td-filetree--wrap" not in rendered,
                    f"{name} must fall back to compact comments", errors)
        map_no_name_html = (temp_path / "public/docs/map-no-name/index.html").read_text()
        require(
            'class="td-map__name">B</span>' in map_no_name_html
            and map_no_name_html.count('class="td-map__coords"') == 1,
            "map-no-name must skip only the nameless entry and keep valid sibling B",
            errors,
        )
        map_nan_html = (temp_path / "public/docs/map-nan/index.html").read_text()
        require(
            'class="td-map__name">B</span>' in map_nan_html
            and '0.00001, -0.00002' in map_nan_html
            and '1e-05' not in map_nan_html,
            "map-nan must skip NaN without failing the build and format small decimal coordinates cleanly",
            errors,
        )
        for empty_map in ("map-empty", "map-not-list", "map-range", "map-inf", "map-string-lat"):
            empty_html = (temp_path / f"public/docs/{empty_map}/index.html").read_text()
            require("td-map__places" not in empty_html, f"{empty_map} must render no map figure", errors)
        map_non_string_name_html = (temp_path / "public/docs/map-non-string-name/index.html").read_text()
        require(
            '<a href="https://example.org/ok" rel="external">OK</a></span> <a class="td-map__coords"' in map_non_string_name_html
            and map_non_string_name_html.count('class="td-map__coords"') == 1,
            "map-non-string-name must skip non-string name, preserve rel=external on sibling OK, and separate name from coords",
            errors,
        )
        map_non_string_text_html = (temp_path / "public/docs/map-non-string-text/index.html").read_text()
        require(
            'class="td-map__name">A</span>' in map_non_string_text_html and "map[k:v]" not in map_non_string_text_html,
            "map-non-string-text must ignore non-string text instead of stringifying it",
            errors,
        )
        map_bad_link_html = (temp_path / "public/docs/map-bad-link/index.html").read_text()
        require(
            "javascript:" not in map_bad_link_html and 'class="td-map__name">A</span>' in map_bad_link_html,
            "map-bad-link must drop unsafe href while keeping the place",
            errors,
        )
        param_output = "\n".join(line for line in output.splitlines() if "content/docs/param-map.md:" in line)
        require("only scalar values" in param_output, f"param map did not report the scalar rule at its position: {param_output or output.strip()}", errors)
        param_page = temp_path / "public/docs/param-map/index.html"
        require(param_page.is_file(), "param map lost its safe output", errors)
        if param_page.is_file():
            require("fixture_map" not in param_page.read_text(), "param map value reached the rendered page", errors)

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

    markers = (ROOT / "assets/css/td/markers.css").read_text()
    for marker in ("ol.steps", "ul.cards", "counter-reset: td-step", "ol.steps[start=", "@media print", "forced-colors", "prefers-reduced-motion"):
        require(marker in markers, f"markers.css lacks {marker}", errors)
    # FileTree and Gallery left the list-marker layer for data fences. Assert the
    # selectors are gone rather than the words: the file explains the move, and a
    # bare substring test would forbid documenting it.
    for selector in ("ul.filetree", "ul.gallery"):
        require(selector not in markers, f"markers.css keeps the removed {selector} list marker", errors)
    gallery_styles = (ROOT / "assets/css/td/gallery.css").read_text()
    for marker in (".td-gallery", ".td-gallery__item", ".td-gallery__image", ".td-gallery__description", "forced-colors", "@media print"):
        require(marker in gallery_styles, f"gallery.css lacks {marker}", errors)
    filetree_styles = (ROOT / "assets/css/td/filetree.css").read_text()
    for marker in (".td-filetree", "--td-filetree-name-col", "--td-filetree-indent: 2.5ch", "clamp(50%, var(--td-filetree-name-col), 70%)", ".td-filetree__divider", ".td-filetree__details[open]", ".td-filetree--static", ".td-filetree--plain", "@media print", "@media (forced-colors: active)", "[dir='rtl']", "@media (max-width: 575.98px)"):
        require(marker in filetree_styles, f"filetree.css lacks {marker}", errors)
    filetree_hook = (ROOT / "layouts/_markup/render-codeblock-filetree.html").read_text()
    for marker in ('partial "content/attributes.html"', "$policy.generic", 'partial "content/filetree-parse.html"', 'partial "content/filetree-icon.html"', 'partial "content/tab-block.html"', "td-filetree--static", "td-filetree-source", "```filetree", '$page.Store.Set "hasFileTree" true', 'role="separator"', 'T "ui_filetree_divider"'):
        require(marker in filetree_hook, f"render-codeblock-filetree.html lacks {marker}", errors)
    scripts_html = (ROOT / "layouts/_partials/scripts.html").read_text()
    require('.Page.Store.Get "hasFileTree"' in scripts_html
            and 'resources.Get "js/filetree.js"' in scripts_html
            and "$hasFileTree -}}" in scripts_html
            and '"target" "js/chunks/filetree.js"' in scripts_html,
            "scripts.html does not gate filetree.js as its stable capability chunk", errors)
    filetree_runtime = (ROOT / "assets/js/filetree.js").read_text()
    for marker in ("OinkFileTree", "module.exports", "data-td-filetree-divider", "pointerdown", "'ArrowRight'", "'Home'", "'End'", "--td-filetree-name-col"):
        require(marker in filetree_runtime, f"filetree.js lacks {marker}", errors)
    filetree_parse = (ROOT / "layouts/_partials/content/filetree-parse.html").read_text()
    for marker in ("$indentCh := 2.5", '"icon" "tone" "open" "type"', "├──|└──", "director(?:y|ies)", 'partial "content/url.html"'):
        require(marker in filetree_parse, f"filetree-parse.html lacks {marker}", errors)
    styles = (ROOT / "assets/css/td/shortcodes/content-primitives.css").read_text()
    require("@media print" in styles and "@media (forced-colors: active)" in styles, "content primitives lack print / forced-colors styles", errors)
    require(".td-filetree" not in styles and ".td-gallery" not in styles and ".td-imgproc" not in styles, "content primitives styles keep removed component selectors", errors)
    update_styles = (ROOT / "assets/css/td/update.css").read_text()
    for marker in (".td-content :where(h1, h2, h3, h4, h5, h6).update", ":has(+ .td-update-meta)", ".td-update-meta", ".td-update-tag", ".td-update-sep", "font-size: 0", "unicode-bidi: isolate", "@media (forced-colors: active)", "@media print", "--td-print-line", "--td-print-strong", "border-block-end: 0"):
        require(marker in update_styles, f"update.css lacks {marker}", errors)
    # Flex items are blockified and user-select: none drops text, so either one
    # makes a browser copy the metadata line as glued or broken tokens.
    require("display: flex" not in update_styles and "inline-flex" not in update_styles and "user-select" not in update_styles,
            "update.css must keep the metadata line inline so plain-text copy keeps its separators", errors)
    heading_hook = (ROOT / "layouts/_markup/render-heading.html").read_text()
    for marker in ('(eq (len .Attributes) 1) (eq (index .Attributes "id") .Anchor)', 'printf "%T"', "time.AsTime", "td-update-sep"):
        require(marker in heading_hook, f"render-heading.html lacks {marker}", errors)
    timeline_styles = (ROOT / "assets/css/td/timeline.css").read_text()
    for marker in (
        "isolation: isolate",
        "--td-timeline-surface:",
        "--td-timeline-line: var(--td-brand-line-strong",
        "z-index: 1",
        "dd > p",
        "dd:has(+ dd)",
        ".td-content-card dl.timeline",
        "break-after: avoid-page",
        "break-inside: avoid-page",
        "--td-print-ink",
        "--td-print-meta",
        "forced-colors: active",
    ):
        require(marker in timeline_styles, f"timeline.css lacks {marker}", errors)
    runtime = (ROOT / "assets/js/content-components.js").read_text()
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    require("initFileTree" not in runtime and "initCarousel" not in runtime, "content-components.js keeps removed runtimes", errors)
    require("hasDocCarousel" not in scripts, "scripts.html keeps removed runtime flags", errors)
    social = (ROOT / "layouts/_shortcodes/social.html").read_text()
    for marker in (
        "Page.Store.Set",
    ):
        require(marker not in social, f"social.html sets a runtime flag ({marker})", errors)
    for marker in (
        'partial "content/shortcode-params.html"',
        'partial "content/url.html"',
        'partial "content/image-resolve.html"',
        'partial "content/render-block.html"',
        'partial "content/markdown-escape-inline.html"',
        '"zhihu"',
        '"telegram"',
        '"none"',
        "time.AsTime",
        'class="td-social__date"',
        'dir="auto"',
        'dir="ltr"',
    ):
        require(marker in social, f"social.html lacks {marker}", errors)
    social_styles = (ROOT / "assets/css/td/social.css").read_text()
    for marker in (
        ".td-social",
        ".td-social__avatar--initial",
        "unicode-bidi: isolate",
        "figure:not(.td-social)",
        ".td-social .td-gallery",
        "@media (forced-colors: active)",
        "@media print",
        "var(--td-print-ink)",
        "var(--td-print-line)",
    ):
        require(marker in social_styles, f"social.css lacks {marker}", errors)
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
        + check_table_reader(args.hugo)
        + check_invalid_cases(args.hugo)
        + check_social_posts(args.hugo)
        + check_timeline(args.hugo)
        + check_update_headings(args.hugo)
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
