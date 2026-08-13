#!/usr/bin/env python3
"""Validate everyday content primitive output and strict author failures."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    page = (public / "docs/content-primitives/index.html").read_text()
    markdown = (public / "docs/content-primitives/index.md").read_text()
    print_page = (public / "_print/docs/index.html").read_text()

    for marker in (
        'class="td-badge td-badge--warning td-badge--outline">Beta</span>',
        'class="td-badge td-badge--info td-badge--outline" href="/release/">v0.3</a>',
        'class="td-badge td-badge--danger td-badge--filled">Deprecated</span>',
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
        '<span class="td-field__type"><code>Array&lt;string&gt; | map[string]any</code></span>',
        '<span class="td-field__required">required</span>',
        '<span class="td-field__default">default: <code>false</code></span>',
        '<span class="td-field__default">default: <code>0</code></span>',
        '<span class="td-field__default">default: <code>&#34;&#34;</code></span>',
        '<a href="/docs/">documentation</a>',
        'class="td-filetree"',
        'class="td-filetree__label"',
        'class="td-filetree__list td-filetree__list--root" aria-labelledby=',
        '<details class="td-filetree__details" open>',
        '<details class="td-filetree__details">',
        '<summary class="td-filetree__summary">',
        '<a class="td-filetree__link" href="/docs/configuration/">',
        '<span class="td-filetree__name" dir="auto">本地化</span>',
        '<span class="td-filetree__name" dir="auto">واجهة</span>',
        'a-deliberately-long-unbroken-filename-that-must-wrap-within-a-narrow-content-column.example.json',
    ):
        require(marker in page, f"HTML fixture missing {marker}", errors)

    require("javascript:" not in page, "HTML contains an unsafe URL", errors)
    require("<table" not in page, "Fields rendered as a table", errors)
    require(page.count('class="td-field"') == 9, "Fields lost author order or entries", errors)
    require(
        page.count('class="td-filetree__details"') == 13,
        "FileTree lost nested folders",
        errors,
    )
    require(
        page.count('<details class="td-filetree__details" open>') == 6,
        "FileTree did not preserve mixed initial disclosure states",
        errors,
    )
    require(
        page.count('class="td-filetree__item td-filetree__item--file"') == 9,
        "FileTree lost files or duplicate names",
        errors,
    )
    require('role="tree"' not in page, "FileTree declares an incomplete ARIA tree", errors)
    require(
        "td-filetree-child:" not in page,
        "FileTree leaked an internal child marker into HTML",
        errors,
    )
    require("**Beta**" in markdown, "Markdown lost Badge text", errors)
    require(
        "[**v0\\.3**](/release/)" in markdown,
        "Markdown lost linked Badge fallback",
        errors,
    )
    require("Ctrl + K" in markdown, "Markdown lost Kbd sequence", errors)
    require(
        r"\[ + A\+B + \>" in markdown,
        "Markdown did not escape Kbd punctuation",
        errors,
    )
    require(
        "- `offlineSearch` — `boolean`; required; default: `true`" in markdown,
        "Markdown lost required/default field metadata",
        errors,
    )
    require(
        "**Configuration fields**" in markdown,
        "Markdown lost the author-provided Fields label",
        errors,
    )
    for marker in (
        "- `explicitFalse` — `boolean`; default: `false`",
        "- `zeroLimit` — `integer`; default: `0`",
        '- `emptyPrefix` — `string`; default: `""`',
        "- `resolverOutput` — `Array<string> | map[string]any`",
        "[documentation](/docs/)",
        "A second paragraph preserves multiline description Markdown and `inline code`.",
        "**Repository structure**",
        "- content/",
        "  - \\_index\\.md",
        "  - docs/",
        "    - [configuration\\.md](/docs/configuration/)",
        "    - level1/",
        "                  - level8/",
        "                    - deeply\\-nested\\.md",
        "- static/",
        "  - index\\.md",
        "- 本地化/",
        "  - 配置\\.md",
        "- واجهة/",
        "  - دليل\\-الإعداد\\.md",
        "- hugo\\.yml",
    ):
        require(marker in markdown, f"Markdown fixture missing {marker}", errors)
    for marker in (
        "td-badge",
        "td-kbd-sequence",
        "td-field",
        "td-filetree",
        "<kbd",
        "<span",
        "<dl",
        "<details",
        "<ul",
    ):
        require(marker not in markdown, f"Markdown contains runtime HTML {marker}", errors)
    require(
        "td-filetree-child:" not in markdown,
        "FileTree leaked an internal child marker into Markdown",
        errors,
    )

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
        "Repository structure",
        "deeply-nested.md",
        "configuration.md",
        "配置.md",
        "دليل-الإعداد.md",
        'class="td-fields"',
        'class="td-filetree td-filetree--static"',
    ):
        require(marker in print_page, f"print fixture missing {marker}", errors)
    require("**Repository structure**" not in print_page, "print used the FileTree Markdown fallback", errors)

    return errors


def check_subpath(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-subpath-") as temp:
        destination = Path(temp) / "public"
        result = subprocess.run(
            [
                hugo,
                "--source",
                str(EXAMPLE),
                "--destination",
                str(destination),
                "--baseURL",
                "https://example.org/manual/",
                "--logLevel",
                "warn",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"subpath fixture failed to build: {result.stdout}{result.stderr}")
        else:
            page = (destination / "docs/content-primitives/index.html").read_text()
            require(
                'href="/manual/release/"' in page,
                "Badge internal link is not subpath-safe",
                errors,
            )
            require(
                'href="/manual/docs/configuration/"' in page,
                "FileTree internal link is not subpath-safe",
                errors,
            )
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
            '{{< filetree label="RSS tree" >}}\n'
            '  {{< filetree/folder name="closed" >}}\n'
            '    {{< filetree/file name="deep.md" link="/docs/deep/" >}}\n'
            '  {{< /filetree/folder >}}\n'
            '  {{< filetree/file name="root.yml" >}}\n'
            '{{< /filetree >}}\n'
        )
        (layouts / "single.rss.xml").write_text(
            '{{- .Store.Set "tdOutputFormat" "rss" -}}\n'
            "<fixture>{{ .RenderShortcodes }}</fixture>\n"
        )
        override = temp_path / "rss.yaml"
        override.write_text(
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n"
            "  home: [HTML]\n"
            "  section: [HTML]\n"
            "  page: [RSS]\n"
        )
        destination = temp_path / "public"
        result = subprocess.run(
            [
                hugo,
                "--source",
                str(EXAMPLE),
                "--contentDir",
                str(temp_path / "content"),
                "--layoutDir",
                str(temp_path / "layouts"),
                "--destination",
                str(destination),
                "--config",
                f"{EXAMPLE / 'hugo.yaml'},{override}",
                "--logLevel",
                "warn",
            ],
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
            'class="td-badge td-badge--warning td-badge--outline">Beta</span>',
            '<kbd>Ctrl</kbd>',
            'aria-hidden="true">+</span>',
            '<dl class="td-fields__list"',
            '<code class="td-field__name">enabled</code>',
            '<span class="td-field__required">required</span>',
            '<code>false</code>',
            '<strong>RSS description</strong>',
            'class="td-filetree td-filetree--static"',
            '>RSS tree</p>',
            '>closed</span>',
            'href="/docs/deep/"',
            '>deep.md</span>',
            '>root.yml</span>',
        ):
            require(marker in source, f"RSS fixture missing {marker}", errors)
        require("**Beta**" not in source, "RSS used the Markdown Badge fallback", errors)
        require(
            'class="td-filetree__details"' not in source,
            "RSS kept interactive FileTree disclosure markup",
            errors,
        )
        require(
            "td-filetree-child:" not in source,
            "FileTree leaked an internal child marker into RSS",
            errors,
        )
        require("<script" not in source, "RSS contains a component runtime", errors)
    return errors


def check_generic_rss_output(hugo: str) -> list[str]:
    """Exercise the theme's ordinary section feed without a Code Group trigger."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-primitives-generic-rss-") as temp:
        site = Path(temp)
        content = site / "content/docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "item.md").write_text(
            "---\ntitle: Primitive feed\ndate: 2026-08-11\n---\n\n"
            '{{< filetree label="Generic RSS tree" >}}\n'
            '  {{< filetree/folder name="closed" >}}\n'
            '    {{< filetree/file name="nested.md" >}}\n'
            '  {{< /filetree/folder >}}\n'
            "{{< /filetree >}}\n\n"
            "```go-html-template\n"
            '{{</* badge text="Example only" */>}}\n'
            "```\n"
        )
        nested = content / "nested"
        nested.mkdir()
        (nested / "_index.md").write_text("---\ntitle: Nested\n---\n")
        (nested / "child.md").write_text(
            "---\ntitle: Nested child\ndate: 2026-08-10\n---\n\n"
            "Nested child must not enter the direct section feed.\n"
        )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\n"
            "title: Generic primitive feed\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n"
            "  home: [HTML, RSS]\n"
            "  section: [HTML, RSS]\n"
            "  page: [HTML]\n"
            "markup:\n"
            "  goldmark:\n"
            "    renderer:\n"
            "      unsafe: true\n"
        )
        destination = site / "public"
        result = subprocess.run(
            [
                hugo,
                "--source",
                str(site),
                "--themesDir",
                str(ROOT.parent),
                "--destination",
                str(destination),
                "--logLevel",
                "warn",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(
                "generic RSS primitive fixture failed to build: "
                f"{result.stdout}{result.stderr}"
            )
            return errors
        output = destination / "docs/index.xml"
        if not output.exists():
            errors.append("generic RSS primitive fixture did not produce docs/index.xml")
            return errors
        source = output.read_text()
        home_source = (destination / "index.xml").read_text()
        require(
            "<title>Generic primitive feed</title>" in home_source,
            "generic RSS home title repeats the site title",
            errors,
        )
        for marker in (
            "td-filetree--static",
            "Generic RSS tree",
            "nested.md",
            "Example only",
        ):
            require(marker in source, f"generic RSS primitive fixture missing {marker}", errors)
        for marker in (
            "td-filetree__details",
            "td-filetree__summary",
            "td-badge td-badge",
        ):
            require(marker not in source, f"generic RSS primitive fixture contains {marker}", errors)
        require(
            "Nested child must not enter" not in source,
            "generic section RSS recursively included a nested section page",
            errors,
        )
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
            "---\ntitle: Front\ndate: 2026-08-11\n"
            "summary: Front summary must win.\n---\n\n"
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
            "baseURL: https://example.org/\n"
            "title: RSS summary contract\n"
            "summaryLength: 5\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n"
            "  home: [HTML]\n"
            "  section: [HTML, RSS]\n"
            "  page: [HTML]\n"
        )
        destination = site / "public"
        result = subprocess.run(
            [
                hugo,
                "--source",
                str(site),
                "--themesDir",
                str(ROOT.parent),
                "--destination",
                str(destination),
                "--logLevel",
                "warn",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(
                "RSS summary contract fixture failed to build: "
                f"{result.stdout}{result.stderr}"
            )
            return errors
        source = (destination / "docs/index.xml").read_text()
        for marker in (
            "Manual before",
            ">Before</span>",
            "Front summary must win.",
            "AUTO_BEFORE",
            ">Automatic badge</span>",
        ):
            require(marker in source, f"RSS summary contract missing {marker}", errors)
        for marker in ("MANUAL_AFTER", ">After</span>", "FRONT_BODY", ">Body</span>", "AUTO_AFTER"):
            require(marker not in source, f"RSS summary leaked {marker}", errors)
        require(
            source.count('data-title="') == source.count("data-html>"),
            "RSS-first rendering prevented a later HTML summary",
            errors,
        )
        require(
            source.count("td-badge") >= 4,
            "RSS-first rendering lost output-aware shortcode HTML",
            errors,
        )
    return errors


INVALID_CASES = (
    ("badge-no-params", '{{< badge >}}\n', "requires parameter text"),
    ("badge-missing-text", '{{< badge tone="info" >}}\n', "requires parameter text"),
    ("badge-empty-text", '{{< badge text="" >}}\n', "text must not be empty"),
    ("badge-text-type", '{{< badge text=true >}}\n', "text must be a string"),
    ("badge-positional", '{{< badge "Beta" >}}\n', "accepts named parameters only"),
    ("badge-tone", '{{< badge text="Beta" tone="loud" >}}\n', "tone must be one of"),
    ("badge-tone-type", '{{< badge text="Beta" tone=true >}}\n', "tone must be a string"),
    ("badge-bool", '{{< badge text="Beta" outline="true" >}}\n', "outline must be boolean"),
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
    ("filetree-text", '{{< filetree >}}not a tree entry{{< /filetree >}}\n', "accepts filetree/folder and filetree/file children only"),
    ("filetree-child", '{{< filetree >}}{{< badge text="Beta" >}}{{< /filetree >}}\n', "accepts filetree/folder and filetree/file children only"),
    ("filetree-label-empty", '{{< filetree label="" >}}{{< /filetree >}}\n', "label must not be empty"),
    ("filetree-label-type", '{{< filetree label=true >}}{{< /filetree >}}\n', "label must be a string"),
    ("filetree-positional", '{{< filetree "Tree" >}}{{< /filetree >}}\n', "accepts named parameters only"),
    ("filetree-unknown", '{{< filetree depth=3 >}}{{< /filetree >}}\n', "unsupported parameter"),
    ("folder-outside", '{{< filetree/folder name="x" >}}{{< /filetree/folder >}}\n', "must be enclosed by filetree or filetree/folder"),
    ("folder-parent", '{{< fields >}}{{< filetree/folder name="x" >}}{{< /filetree/folder >}}{{< /fields >}}\n', "must be enclosed by filetree or filetree/folder"),
    ("folder-missing-name", '{{< filetree >}}{{< filetree/folder >}}{{< /filetree/folder >}}{{< /filetree >}}\n', "requires parameter name"),
    ("folder-empty-name", '{{< filetree >}}{{< filetree/folder name="" >}}{{< /filetree/folder >}}{{< /filetree >}}\n', "name must not be empty"),
    ("folder-name-type", '{{< filetree >}}{{< filetree/folder name=true >}}{{< /filetree/folder >}}{{< /filetree >}}\n', "name must be a string"),
    ("folder-positional", '{{< filetree >}}{{< filetree/folder "x" >}}{{< /filetree/folder >}}{{< /filetree >}}\n', "accepts named parameters only"),
    ("folder-open", '{{< filetree >}}{{< filetree/folder name="x" open="true" >}}{{< /filetree/folder >}}{{< /filetree >}}\n', "open must be boolean"),
    ("folder-unknown", '{{< filetree >}}{{< filetree/folder name="x" icon="folder" >}}{{< /filetree/folder >}}{{< /filetree >}}\n', "unsupported parameter"),
    ("folder-text", '{{< filetree >}}{{< filetree/folder name="x" >}}not an entry{{< /filetree/folder >}}{{< /filetree >}}\n', "accepts filetree/folder and filetree/file children only"),
    ("file-outside", '{{< filetree/file name="x" >}}\n', "must be enclosed by filetree or filetree/folder"),
    ("file-parent", '{{< fields >}}{{< filetree/file name="x" >}}{{< /fields >}}\n', "must be enclosed by filetree or filetree/folder"),
    ("file-missing-name", '{{< filetree >}}{{< filetree/file >}}{{< /filetree >}}\n', "requires parameter name"),
    ("file-empty-name", '{{< filetree >}}{{< filetree/file name="" >}}{{< /filetree >}}\n', "name must not be empty"),
    ("file-name-type", '{{< filetree >}}{{< filetree/file name=true >}}{{< /filetree >}}\n', "name must be a string"),
    ("file-positional", '{{< filetree >}}{{< filetree/file "x" >}}{{< /filetree >}}\n', "accepts named parameters only"),
    ("file-link-scheme", '{{< filetree >}}{{< filetree/file name="x" link="javascript:alert(1)" >}}{{< /filetree >}}\n', "unsupported link scheme"),
    ("file-link-type", '{{< filetree >}}{{< filetree/file name="x" link=true >}}{{< /filetree >}}\n', "link must be a string"),
    ("file-link-empty", '{{< filetree >}}{{< filetree/file name="x" link="" >}}{{< /filetree >}}\n', "link must not be empty"),
    ("file-unknown", '{{< filetree >}}{{< filetree/file name="x" badge="new" >}}{{< /filetree >}}\n', "unsupported parameter"),
)


def check_invalid_cases(hugo: str) -> list[str]:
    errors: list[str] = []
    for name, body, expected in INVALID_CASES:
        with tempfile.TemporaryDirectory(prefix=f"oink-primitives-{name}-") as temp:
            temp_path = Path(temp)
            content = temp_path / "content/docs"
            content.mkdir(parents=True)
            (content / "invalid.md").write_text(
                f"---\ntitle: Invalid {name}\n---\n\n{body}"
            )
            result = subprocess.run(
                [
                    hugo,
                    "--source",
                    str(EXAMPLE),
                    "--contentDir",
                    str(temp_path / "content"),
                    "--destination",
                    str(temp_path / "public"),
                    "--logLevel",
                    "warn",
                ],
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
                    errors.append(
                        f"invalid case {name} did not report {expected!r}: "
                        f"{output.strip()}"
                    )
                if "content/docs/invalid.md:" not in output:
                    errors.append(f"invalid case {name} did not report its position")
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    for relative in (
        "layouts/_shortcodes/badge.html",
        "layouts/_shortcodes/kbd.html",
        "layouts/_shortcodes/fields.html",
        "layouts/_shortcodes/field.html",
        "layouts/_shortcodes/filetree.html",
        "layouts/_shortcodes/filetree/folder.html",
        "layouts/_shortcodes/filetree/file.html",
    ):
        source = (ROOT / relative).read_text()
        require("Page.Store.Set" not in source, f"{relative} sets a runtime flag", errors)
        if relative not in (
            "layouts/_shortcodes/field.html",
            "layouts/_shortcodes/filetree/file.html",
        ):
            require('eq $outputFormat "markdown"' in source, f"{relative} lacks Markdown output", errors)
    fields_source = (ROOT / "layouts/_shortcodes/fields.html").read_text()
    field_source = (ROOT / "layouts/_shortcodes/field.html").read_text()
    require("<dl" in fields_source, "Fields lacks a definition list", errors)
    require("<table" not in fields_source, "Fields contains a table", errors)
    require("display: contents" not in fields_source, "Fields removes list semantics", errors)
    require(".InnerDeindent" in field_source, "Field does not normalize nested indentation", errors)
    filetree_source = (ROOT / "layouts/_shortcodes/filetree.html").read_text()
    folder_source = (ROOT / "layouts/_shortcodes/filetree/folder.html").read_text()
    file_source = (ROOT / "layouts/_shortcodes/filetree/file.html").read_text()
    require("<ul" in filetree_source, "FileTree root lacks a list", errors)
    require("<details" in folder_source, "FileTree folder lacks native disclosure", errors)
    require("<summary" in folder_source, "FileTree folder lacks a native summary", errors)
    require(
        'role="tree"' not in filetree_source + folder_source + file_source,
        "FileTree declares role=tree",
        errors,
    )
    require(
        "Page.Store.Set" not in filetree_source + folder_source + file_source,
        "FileTree sets a runtime flag",
        errors,
    )
    require(
        "filetree-icon.html" in folder_source + file_source,
        "FileTree lacks internal decoration",
        errors,
    )
    styles = (ROOT / "assets/scss/td/shortcodes/content-primitives.scss").read_text()
    require("@media print" in styles, "content primitives lack print styles", errors)
    require(
        "@media (forced-colors: active)" in styles,
        "content primitives lack forced-colors styles",
        errors,
    )
    require(
        ".td-filetree__details > .td-filetree__list" in styles
        and "display: block !important" in styles,
        "closed FileTree folders are not forced open for print",
        errors,
    )
    for relative, content_expr in (
        ("layouts/_partials/print/content.html", ".Page.RawContent"),
        ("layouts/_partials/print/render.html", ".RawContent"),
    ):
        source = (ROOT / relative).read_text()
        store = source.find('.Store.Set "tdOutputFormat" "print"')
        content = source.find(content_expr, store)
        require(
            store >= 0 and content > store,
            f"{relative} does not reset Page Store before rendering print content",
            errors,
        )
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
