#!/usr/bin/env python3
"""Validate Enhanced Code Block output, tabs, and strict author-contract failures."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def bundle_source(page: str, public: Path) -> str:
    match = re.search(r'<script src="(?P<src>/js/main-[^"]+\.js)"', page)
    if not match:
        return ""
    return (public / match.group("src").lstrip("/")).read_text()


def temp_build(hugo: str, pages: dict[str, str], *, prefix: str, extra_config: str = "") -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory]:
    """Build the example site with a replacement content directory.

    Returns the process, the destination directory and the temp handle (keep it
    alive while reading outputs).
    """
    temp = tempfile.TemporaryDirectory(prefix=prefix)
    temp_path = Path(temp.name)
    content = temp_path / "content"
    for relative, body in pages.items():
        target = content / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    destination = temp_path / "public"
    command = [
        hugo,
        "--source",
        str(EXAMPLE),
        "--contentDir",
        str(content),
        "--destination",
        str(destination),
        "--logLevel",
        "warn",
    ]
    if extra_config:
        override = temp_path / "override.yaml"
        override.write_text(extra_config, encoding="utf-8")
        command.extend(["--config", f"{EXAMPLE / 'hugo.yaml'},{override}"])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return result, destination, temp


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    code_html = (public / "docs/code-blocks/index.html").read_text()
    code_markdown = (public / "docs/code-blocks/index.md").read_text()
    typography_html = (public / "docs/typography/index.html").read_text()
    home_html = (public / "index.html").read_text()
    print_html = (public / "_print/docs/index.html").read_text()

    for marker in (
        'class="td-code td-code--titled"',
        'data-collapse-lines="4"',
        'data-copy-mode="command"',
        'class="td-code td-code--untitled code-fixture"',
        'data-note="a &#34;quoted&#34; &amp; value"',
        # Adjacent fences: one wrapper per fence, group only on the first block.
        '<div class="td-tab-block td-tab-block--code" data-td-tab="npm" data-td-tab-group="package-manager" data-td-tab-value="npm" data-td-tab-kind="code">',
        '<div class="td-tab-block td-tab-block--code" data-td-tab="pnpm" data-td-tab-value="pnpm" data-td-tab-kind="code">',
        '<div class="td-tab-block td-tab-block--code" data-td-tab="yarn" data-td-tab-value="yarn" data-td-tab-kind="code">',
        '<div class="td-tab-block__title" data-td-tab-title>npm</div>',
        # Local (ungrouped) blocks: no group / value attributes at all.
        '<div class="td-tab-block td-tab-block--code" data-td-tab="A **literal** [label]" data-td-tab-kind="code">',
        '<div class="td-tab-block td-tab-block--code" data-td-tab="YAML" data-td-tab-kind="code">',
        # tab and title coexist: the tab label is the wrapper title, title stays the code header.
        '<span class="td-code__filename" id="',
        'title="config.yaml">config.yaml</span>',
        # Full form: complete tablist + panels, ids <group>-<value>.
        'class="td-tabs td-tabs--shortcode" id="td-tabs-',
        'data-td-tabs data-td-tabs-group="setting" data-td-tabs-default="conf"',
        '<div class="td-tabs__list" role="tablist" aria-label="MinIO settings">',
        '<button class="td-tabs__tab" type="button" role="tab" id="setting-env-tab" aria-controls="setting-env" aria-selected="false" tabindex="-1" data-td-tabs-value="env">Environment Variable</button>',
        '<button class="td-tabs__tab" type="button" role="tab" id="setting-conf-tab" aria-controls="setting-conf" aria-selected="true" tabindex="0" data-td-tabs-value="conf">Configuration Setting</button>',
        '<div class="td-tabs__panel" id="setting-env" role="tabpanel" aria-labelledby="setting-env-tab" tabindex="0" data-td-tabs-value="env">',
        '<div class="td-tabs__panel" id="setting-conf" role="tabpanel" aria-labelledby="setting-conf-tab" tabindex="0" data-td-tabs-value="conf" data-td-tabs-active>',
        '<div class="td-tabs__panel-title" aria-hidden="true">Environment Variable</div>',
        # Headings inside a tab body keep their explicit IDs.
        'id="envvar-queue-dir"',
        'id="conf-queue-dir"',
        # A callout inside a tab renders through the blockquote hook.
        'class="td-callout td-callout--tip"',
        # Ungrouped full form: generated ids, default = first tab.
        'aria-label="Tabs"',
        'data-td-tabs-value="tab1">First</button>',
        'data-td-tabs-value="tab2">Second</button>',
    ):
        require(marker in code_html, f"HTML fixture missing {marker}", errors)

    require(re.search(r'<div class="td-tabs__panel"[^>]*\shidden(?:\s|>)', code_html) is None, "a tab panel is hidden before the runtime enhances the DOM", errors)
    require(
        re.search(
            r'data-language="sh"[\s\S]*?class="td-code__language">BASH</span>',
            code_html,
        )
        is not None,
        "shell lexer alias was not presented as Bash",
        errors,
    )
    require("td-code__copy-label" not in code_html, "Copy control still contains a visible text label", errors)
    require("data-td-tp-persist" not in code_html and "td-code-group" not in code_html and "nav-tabs" not in code_html, "legacy tabpane / code-group markup survived", errors)
    for legacy in ("data-bs-toggle", "tab-pane"):
        require(legacy not in code_html, f"Bootstrap tab markup {legacy} leaked into content tabs", errors)

    # Markdown output: fences with their attributes; the tabs shortcode degrades to labelled sections.
    for marker in (
        '```bash {tab="npm" group="package-manager" value="npm"}',
        '```bash {tab="pnpm" value="pnpm"}',
        "pnpm add @example/client",
        "**Environment Variable**",
        "**Configuration Setting**",
        "**First**",
        "**Second**",
        "###### `MINIO_LOGGER_WEBHOOK_QUEUE_DIR` {#envvar-queue-dir}",
        "> [!TIP]",
    ):
        require(marker in code_markdown, f"Markdown lost {marker}", errors)
    for marker in ("data-td-code", "td-tabs", "td-tab-block", "<button", "<section"):
        require(marker not in code_markdown, f"Markdown contains runtime HTML {marker}", errors)

    code_bundle = bundle_source(code_html, public)
    typography_bundle = bundle_source(typography_html, public)
    home_bundle = bundle_source(home_html, public)
    print_bundle = bundle_source(print_html, public)
    require("td-tabs:v1:" in code_bundle, "tabs runtime was not bundled on the tabs page", errors)
    require("data-td-code-copy" in code_bundle, "Copy runtime was not bundled", errors)
    require("data-td-code-copy" in typography_bundle, "ordinary code lacks Copy runtime", errors)
    require("td-tabs:v1:" not in typography_bundle, "ordinary code loaded the tabs runtime", errors)
    for name, source in (("home", home_bundle), ("print", print_bundle)):
        require("data-td-code-copy" not in source, f"{name} loaded Copy runtime", errors)
        require("td-tabs:v1:" not in source, f"{name} loaded the tabs runtime", errors)
    require("td-code-group:v1" not in code_bundle, "legacy Code Group runtime is still bundled", errors)

    # Print: adjacent fences stay titled blocks; the tabs shortcode renders every panel with its title.
    for marker in (
        '<div class="td-tab-block__title" data-td-tab-title>npm</div>',
        "npm install @example/client",
        '<div class="td-tabs__panel-title" aria-hidden="true">Environment Variable</div>',
        '<div class="td-tabs__panel-title" aria-hidden="true">Configuration Setting</div>',
        "mc admin config set",
    ):
        require(marker in print_html, f"print lost {marker}", errors)
    require('role="tablist"' not in print_html, "print rendered an interactive tablist", errors)
    require(re.search(r'\sdata-td-tabs(?:\s|>)', print_html) is None, "print rendered a runtime-enhanced tab set", errors)
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    token_selector = re.compile(r"\.chroma \.[A-Za-z0-9]+")
    light_palette = (ROOT / "assets/scss/td/chroma/_light.scss").read_text()
    dark_palette = (ROOT / "assets/scss/td/chroma/_dark.scss").read_text()
    light_tokens = set(token_selector.findall(light_palette))
    dark_tokens = set(token_selector.findall(dark_palette))
    missing_dark_tokens = sorted(light_tokens - dark_tokens)
    require(not missing_dark_tokens, f"dark Chroma palette leaks light-only tokens: {missing_dark_tokens}", errors)
    dark_error = re.search(r"\.chroma \.err \{(?P<body>[^}]*)\}", dark_palette)
    require(
        dark_error is not None and "background" not in dark_error.group("body"),
        "dark Chroma error token must not paint a light background",
        errors,
    )

    html_bases = (
        "layouts/baseof.html",
        "layouts/baseof.taxonomy.html",
        "layouts/baseof.term.html",
        "layouts/blog/baseof.html",
        "layouts/docs/baseof.html",
        "layouts/swagger/baseof.html",
    )
    for relative in html_bases:
        source = (ROOT / relative).read_text()
        require('.Store.Set "tdOutputFormat" "html"' in source, f"{relative} does not reset the HTML output context", errors)
        main = source.find('block "main"')
        scripts = source.find('partial "scripts.html"')
        require(main >= 0 and scripts > main, f"{relative} loads scripts before content sets Page Store flags", errors)

    namespace = (ROOT / "layouts/_partials/code/namespace-html.html").read_text()
    render = (ROOT / "layouts/_partials/code/render.html").read_text()
    normalize = (ROOT / "layouts/_partials/code/normalize.html").read_text()
    codeblock = (ROOT / "layouts/_markup/render-codeblock.html").read_text()
    tab_block = (ROOT / "layouts/_partials/content/tab-block.html").read_text()
    tabs = (ROOT / "layouts/_shortcodes/tabs.html").read_text()
    tab = (ROOT / "layouts/_shortcodes/tab.html").read_text()
    render_block = (ROOT / "layouts/_partials/content/render-block.html").read_text()
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    runtime = (ROOT / "assets/js/tabs.js").read_text()

    require("data-td-code-auto-id" in namespace and "data-td-code-auto-id" in render, "automatic code-ID namespace marker is missing", errors)
    require("tdRenderScope" in normalize and "tdRenderScope" in render_block, "nested-render code ID scoping is missing", errors)
    for marker in ('"tab" "group" "value" "num" "caption"',):
        require(marker in normalize, f"normalize.html does not reserve {marker}", errors)
    for marker in ('partial "content/tab-block.html"', "group/value require tab", "num (Book example) and tab (tabs) are mutually exclusive", "caption requires num", "requires caption", 'partial "book/register-target.html"'):
        require(marker in codeblock, f"render-codeblock.html lacks {marker}", errors)
    for marker in ('data-td-tab="', "data-td-tab-group", "data-td-tab-value", "data-td-tab-kind", "data-td-tab-title", '.Store.Set "hasTabs" true', "^[a-z][a-z0-9_-]*$", "^[a-z0-9][a-z0-9_-]*$"):
        require(marker in tab_block, f"tab-block.html lacks {marker}", errors)
    for marker in ('role="tablist"', 'role="tab"', 'role="tabpanel"', "aria-controls", "aria-labelledby", 'tabindex="{{ cond', "data-td-tabs-default", "td-tabs__panel-title", 'eq $format "markdown"', "render-block.html", 'T "ui_tabs_label"'):
        require(marker in tabs, f"tabs.html lacks {marker}", errors)
    require(re.search(r'<section[^>]*\shidden(?:\s|>)', tabs) is None, "tabs.html hides a panel before the runtime runs", errors)
    require('must be enclosed by tabs' in tab and 'Parent.Scratch.SetInMap "tabEntries"' in tab, "tab.html is not a tabs collector child", errors)
    require('.Page.Store.Get "hasTabs"' in scripts and 'resources.Get "js/tabs.js"' in scripts, "scripts.html does not load tabs.js on hasTabs", errors)
    require("code-tabs.js" not in scripts and not (ROOT / "assets/js/code-tabs.js").exists(), "legacy code-tabs runtime survived", errors)
    for marker in ("td-tabs:v1:", "data-td-tabs-ready", "ArrowLeft", "ArrowRight", "Home", "End", "replaceState", "groupAdjacentBlocks", "aria-selected", "tabindex"):
        require(marker in runtime, f"tabs runtime lacks {marker}", errors)
    require("bootstrap" not in runtime.lower(), "tabs runtime depends on Bootstrap", errors)
    for relative in ("layouts/_shortcodes/tabpane.html", "layouts/_shortcodes/code-group.html", "layouts/_shortcodes/code-tab.html", "layouts/_shortcodes/alert.html"):
        require(not (ROOT / relative).exists(), f"{relative} must stay deleted", errors)
    return errors


def check_generic_rss_output(hugo: str) -> list[str]:
    """Keep escaped shortcode examples literal after live tabs render in RSS."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-code-generic-rss-") as temp:
        site = Path(temp)
        content = site / "content/docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "rss.md").write_text(
            "---\ntitle: RSS code\ndate: 2026-08-11\n---\n\n"
            "Live tabs.\n\n"
            '```sh {tab="Shell" group="rss-live" value="shell"}\n'
            "echo rss-static\n"
            "```\n\n"
            '```sh {tab="Zsh" value="zsh"}\n'
            "echo rss-zsh\n"
            "```\n\n"
            '{{< tabs group="rss-full" >}}\n'
            '{{< tab label="One" value="one" >}}\nFirst **body**.\n{{< /tab >}}\n'
            '{{< tab label="Two" value="two" >}}\nSecond body.\n{{< /tab >}}\n'
            "{{< /tabs >}}\n\n"
            "Literal example.\n\n"
            "```go-html-template\n"
            '{{</* tabs group="sample" */>}}\n'
            "{{</* /tabs */>}}\n"
            "```\n"
        )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\n"
            "title: RSS code fixture\n"
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
            "    parser:\n"
            "      attribute:\n"
            "        block: true\n"
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
            errors.append(f"generic RSS code fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        output = destination / "docs/index.xml"
        if not output.exists():
            errors.append("generic RSS code fixture did not produce docs/index.xml")
            return errors
        source = output.read_text()
        for marker in ("rss-static", "rss-zsh", "Literal example.", "sample", "td-tab-block__title", "td-tabs__panel-title", "First &lt;strong&gt;body&lt;/strong&gt;"):
            require(marker in source, f"generic RSS code fixture missing {marker}", errors)
        for marker in ("data-bs-toggle", "role=&#34;tablist&#34;", "data-td-tabs=", "data-td-code-copy", '<button class="nav-link'):
            require(marker not in source, f"generic RSS code fixture contains {marker}", errors)
    return errors


def check_nested_render_ids(hugo: str) -> list[str]:
    """Fences rendered inside shortcode bodies (RenderString) must keep unique DOM IDs."""
    errors: list[str] = []
    result, destination, temp = temp_build(
        hugo,
        {
            "docs/_index.md": "---\ntitle: Docs\n---\n",
            "docs/nested.md": (
                "---\ntitle: Nested code IDs\n---\n\n"
                '{{< tabs group="nested" >}}\n'
                '{{< tab label="First" value="first" >}}\n'
                "> [!NOTE]\n> ```shell\n> echo repeated\n> ```\n"
                "{{< /tab >}}\n"
                '{{< tab label="Second" value="second" >}}\n'
                "```shell\necho repeated\n```\n"
                "{{< /tab >}}\n"
                "{{< /tabs >}}\n\n"
                '{{< eg num="1" caption="Nested example" >}}\n'
                "```shell\necho repeated\n```\n"
                "{{< /eg >}}\n\n"
                "{{< cards >}}\n"
                '{{< card title="Card" >}}\n'
                "```shell\necho repeated\n```\n"
                "{{< /card >}}\n"
                "{{< /cards >}}\n\n"
                "```shell\necho repeated\n```\n\n"
                "```shell\necho repeated again\n```\n"
            ),
        },
        prefix="oink-code-nested-ids-",
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"nested code-ID fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        source = (destination / "docs/nested/index.html").read_text(encoding="utf-8")
        roots = re.findall(r'id="(td-code-[^"]+)" data-td-code(?:\s|>)', source)
        require(len(roots) == 6, f"nested fixture rendered {len(roots)} code roots: {roots}", errors)
        require(len(roots) == len(set(roots)), f"nested RenderString code roots are not unique: {roots}", errors)
        for root in roots:
            require(source.count(f'id="{root}-viewport"') == 1, f"nested code root {root} lost its unique viewport target", errors)
        all_ids = re.findall(r'\sid="([^"]+)"', source)
        duplicates = sorted({value for value in all_ids if all_ids.count(value) > 1})
        require(not duplicates, f"nested fixture page contains duplicate ids: {duplicates}", errors)
    return errors


def check_tabs_behaviour(hugo: str) -> list[str]:
    """Adjacent fences and the tabs shortcode across output formats."""
    errors: list[str] = []
    result, destination, temp = temp_build(
        hugo,
        {
            "docs/_index.md": "---\ntitle: Docs\n---\n",
            "docs/tabs.md": (
                "---\ntitle: Tabs matrix\noutputs: [HTML, markdown]\n---\n\n"
                '```bash {tab="Homebrew" group="install" value="brew" title="install.sh"}\n'
                "brew install pigsty\n"
                "```\n\n"
                '```bash {tab="APT" value="apt"}\n'
                "sudo apt install pigsty\n"
                "```\n\n"
                "Paragraph between runs.\n\n"
                '```yaml {tab="环境变量"}\n'
                "a: 1\n"
                "```\n\n"
                '```yaml {tab="配置项"}\n'
                "b: 2\n"
                "```\n\n"
                '{{< tabs >}}\n'
                '{{< tab label="A **literal** [label]" >}}\n'
                "Body A with a list:\n\n- one\n- two\n"
                "{{< /tab >}}\n"
                '{{< tab label="B" >}}\n'
                "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
                "{{< /tab >}}\n"
                "{{< /tabs >}}\n"
            ),
        },
        prefix="oink-code-tabs-matrix-",
    )
    with temp:
        if result.returncode != 0:
            errors.append(f"tabs matrix fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/tabs/index.html").read_text(encoding="utf-8")
        markdown = (destination / "docs/tabs/index.md").read_text(encoding="utf-8")
        for marker in (
            'data-td-tab="Homebrew" data-td-tab-group="install" data-td-tab-value="brew"',
            'title="install.sh">install.sh</span>',
            '<div class="td-tab-block__title" data-td-tab-title>Homebrew</div>',
            'data-td-tab="APT" data-td-tab-value="apt"',
            'data-td-tab="环境变量" data-td-tab-kind="code"',
            'data-td-tab="配置项" data-td-tab-kind="code"',
            'data-td-tab="A **literal** [label]"' if False else '>A **literal** [label]</button>',
            '<div class="td-tabs__panel-title" aria-hidden="true">B</div>',
            "<td>1</td>",
            "<li>one</li>",
        ):
            require(marker in html, f"tabs matrix HTML missing {marker}", errors)
        require(html.count('class="td-tab-block td-tab-block--code"') == 4, "tabs matrix rendered a wrong number of tab blocks", errors)
        require(re.search(r'data-td-tabs-value="tab1">A \*\*literal\*\* \[label\]</button>', html) is not None, "ungrouped tabs did not use generated values", errors)
        for marker in ('```bash {tab="Homebrew" group="install" value="brew" title="install.sh"}', "brew install pigsty", "**A \\*\\*literal\\*\\* \\[label\\]**", "**B**", "| A | B |", "- one"):
            require(marker in markdown, f"tabs matrix Markdown missing {marker}", errors)
        for marker in ("<section", "td-tabs", "role="):
            require(marker not in markdown, f"tabs matrix Markdown contains {marker}", errors)
    return errors


INVALID_CASES = (
    ("filename-title", '```yaml {filename="a.yml" title="A"}\na: 1\n```\n', "filename and title are mutually exclusive", {}),
    ("command-language", '```bash {copy="command"}\necho no\n```\n', "copy=command requires language console or shell-session", {}),
    ("wrap-table", '```text {wrap=true lineNos="table"}\none\ntwo\n```\n', "wrap=true is incompatible", {}),
    ("collapse-zero", '```text {collapse=0}\none\n```\n', "collapse must be a positive integer", {}),
    ("duplicate-code-ids", '```text {id="same-code"}\none\n```\n\n```text {id="same-code"}\ntwo\n```\n', "duplicate id", {}),
    ("invalid-code-id", '```text {id="bad id"}\none\n```\n', "id must not contain ASCII whitespace or control characters", {}),
    ("generated-line-anchor-collision", '```text {id="anchored" lineNos="inline" anchorLineNos=true}\none\n```\n\n```text {id="anchored-1"}\ntwo\n```\n', "duplicate id", {}),
    ("filename-aria-label", '```text {filename="a.txt" aria-label="conflict"}\none\n```\n', "label/filename and aria-label are mutually exclusive", {}),
    ("reserved-data", '```text {data-line-count="999"}\none\n```\n', 'attribute "data-line-count" is reserved', {}),
    # Adjacent-fence tabs
    ("tab-group-without-value", '```bash {tab="A" group="g"}\none\n```\n', "value is required when group is declared", {}),
    ("tab-value-without-tab", '```bash {value="a"}\none\n```\n', "group/value require tab", {}),
    ("tab-group-without-tab", '```bash {group="g"}\none\n```\n', "group/value require tab", {}),
    ("tab-bad-group", '```bash {tab="A" group="Bad Group" value="a"}\none\n```\n', "group must match", {}),
    ("tab-bad-value", '```bash {tab="A" group="g" value="Bad Value"}\none\n```\n', "value must match", {}),
    ("tab-empty", '```bash {tab=""}\none\n```\n', "tab label must not be empty", {}),
    ("tab-and-num", '```bash {tab="A" num="1" caption="x"}\none\n```\n', "mutually exclusive", {}),
    # Native Book example fence
    ("eg-caption-without-num", '```sql {caption="orphan"}\nSELECT 1;\n```\n', "caption requires num", {}),
    ("eg-num-without-caption", '```sql {num="1"}\nSELECT 1;\n```\n', "requires caption", {}),
    ("eg-bad-num", '```sql {num="1/2" caption="x"}\nSELECT 1;\n```\n', "num must match", {}),
    ("eg-duplicate-num", '```sql {num="1" caption="x"}\nSELECT 1;\n```\n\n```sql {num="1" caption="y" #other}\nSELECT 2;\n```\n', "duplicate eg number", {}),
    # Tabs shortcode
    ("tabs-positional", '{{< tabs "x" >}}{{< tab label="A" >}}a{{< /tab >}}{{< /tabs >}}\n', "accepts named parameters only", {}),
    ("tabs-unknown", '{{< tabs cols=2 >}}{{< tab label="A" >}}a{{< /tab >}}{{< /tabs >}}\n', "unsupported parameter", {}),
    ("tabs-empty", '{{< tabs >}}{{< /tabs >}}\n', "requires at least one tab child", {}),
    ("tabs-text", '{{< tabs >}}not a tab{{< /tabs >}}\n', "accepts tab children only", {}),
    ("tabs-bad-group", '{{< tabs group="Bad" >}}{{< tab label="A" value="a" >}}a{{< /tab >}}{{< /tabs >}}\n', "group must match", {}),
    ("tabs-default-without-group", '{{< tabs default="a" >}}{{< tab label="A" >}}a{{< /tab >}}{{< /tabs >}}\n', "default requires group", {}),
    ("tabs-default-unknown", '{{< tabs group="g" default="zzz" >}}{{< tab label="A" value="a" >}}a{{< /tab >}}{{< /tabs >}}\n', "does not match a tab value", {}),
    ("tab-outside", '{{< tab label="A" >}}a{{< /tab >}}\n', "must be enclosed by tabs", {}),
    ("tab-missing-label", '{{< tabs >}}{{< tab >}}a{{< /tab >}}{{< /tabs >}}\n', "requires named parameter label", {}),
    ("tab-value-required", '{{< tabs group="g" >}}{{< tab label="A" >}}a{{< /tab >}}{{< /tabs >}}\n', "value is required because tabs declares group", {}),
    ("tab-value-forbidden", '{{< tabs >}}{{< tab label="A" value="a" >}}a{{< /tab >}}{{< /tabs >}}\n', "value is only allowed when tabs declares a group", {}),
    ("tab-duplicate-value", '{{< tabs group="g" >}}{{< tab label="A" value="a" >}}a{{< /tab >}}{{< tab label="B" value="a" >}}b{{< /tab >}}{{< /tabs >}}\n', "duplicate value", {}),
    ("tab-unknown", '{{< tabs >}}{{< tab label="A" lang="sh" >}}a{{< /tab >}}{{< /tabs >}}\n', "unsupported parameter", {}),
    ("prism-tabs", '```bash {tab="A"}\none\n```\n', "requires Hugo/Chroma", {"HUGO_PARAMS_PRISM_SYNTAX_HIGHLIGHTING": "true"}),
)


def check_invalid_cases(hugo: str) -> list[str]:
    errors: list[str] = []
    for name, body, expected, extra_env in INVALID_CASES:
        with tempfile.TemporaryDirectory(prefix=f"oink-code-{name}-") as temp:
            temp_path = Path(temp)
            content = temp_path / "content/docs"
            content.mkdir(parents=True)
            (content / "invalid.md").write_text(f"---\ntitle: Invalid {name}\n---\n\n{body}")
            destination = temp_path / "public"
            command = [hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--destination", str(destination), "--logLevel", "warn"]
            if extra_env:
                override = temp_path / "override.yaml"
                override.write_text("params:\n  prism_syntax_highlighting: true\n")
                command.extend(["--config", f"{EXAMPLE / 'hugo.yaml'},{override}"])
            result = subprocess.run(command, cwd=ROOT, env={**os.environ, **extra_env}, capture_output=True, text=True, check=False)
            output = result.stdout + result.stderr
            if result.returncode == 0:
                errors.append(f"invalid case {name} unexpectedly built")
            elif expected not in output:
                errors.append(f"invalid case {name} did not report {expected!r}: {output.strip()}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, default=EXAMPLE / "public")
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors = (
        check_outputs(args.public)
        + check_template_contracts()
        + check_generic_rss_output(args.hugo)
        + check_nested_render_ids(args.hugo)
        + check_tabs_behaviour(args.hugo)
        + check_invalid_cases(args.hugo)
    )
    if errors:
        print("Enhanced code-block checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Enhanced code-block checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
