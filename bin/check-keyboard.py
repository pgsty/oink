#!/usr/bin/env python3
"""Build and verify keyboard navigation gating, assembly, and runtime."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from runtime_assets import referenced_chunks

ROOT = Path(__file__).resolve().parents[1]
ACTIONS_SCRIPT = ROOT / "bin" / "check-actions.py"

# Every key binds must appear in the runtime, and the runtime must not
# grow keys the contract table does not document. ArrowLeft/ArrowRight bind through
# the RTL swap ternary rather than a direct comparison. The three groups mirror
# the 3 x 10 shortcut sheet; the Command Palette owns "/", "`" and "~".
KEYMAP = [
    # Navigation
    "'w'", "'s'", "'a'", "'d'", "' '", "'q'", "'e'", "'k'", "'j'",
    "'x'", "'r'", "'v'", "'h'", "'g'",
    # Actions
    "'f'", "'c'", "'u'", "'n'", "'i'", "'o'", "'p'", "'['", "']'", "'\\\\'",
    # View
    "'b'", "'z'", "'m'", "'t'", "'y'", "'l'", "';'", "','", "'<'", "'.'", "'>'",
    "'-'", "'='", "'+'", "\"'\"",
    # Tree and dialog control
    "'Escape'", "'ArrowUp'", "'ArrowDown'",
]
SHEET_ROWS = [
    "tree-move", "tree-toggle", "tree-open", "page-move", "heading-move",
    "language", "route", "version", "history", "home",
    "search", "commands", "edit", "new-page", "issue",
    "expand-all", "print", "chatgpt", "claude", "gemini",
    "duo", "zen", "markdown", "style", "theme",
    "layout", "gallery", "image-size", "page-width", "help",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_actions() -> Any:
    spec = importlib.util.spec_from_file_location("actions_check", ACTIONS_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load action fixture helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def referenced_bundles(output: Path, html: str) -> list[str]:
    chunks = referenced_chunks(output, html)
    for item in chunks:
        require(item.path.is_file(), f"referenced runtime chunk is missing: {item.src}")
    require(chunks, "page references no runtime chunks")
    return [item.path.read_text(encoding="utf-8") for item in chunks]


def check_sources() -> None:
    reading_focus = (ROOT / "assets/js/base.js").read_text(encoding="utf-8")
    reading_styles = (ROOT / "assets/css/td/content.css").read_text(encoding="utf-8")
    require("function initReadingFocus()" in reading_focus
            and "data-td-pointer-focus" in reading_focus
            and "event.key === 'Tab'" in reading_focus
            and "#td-main-content:focus-visible:not([data-td-pointer-focus]):has(h1, .h1)" in reading_styles,
            "reading focus lost pointer scoping or the keyboard skip-link indicator")
    scripts = (ROOT / "layouts" / "_partials" / "scripts.html").read_text(encoding="utf-8")
    require(
        'resources.Get "js/keyboard-nav.js"' in scripts,
        "scripts.html does not assemble keyboard-nav.js",
    )
    require(
        "$hasKeyboardNav -}}" in scripts
        and '"target" "js/chunks/keyboard.js"' in scripts,
        "keyboard-nav is not gated as its stable capability chunk",
    )
    require(
        "params.ui.keyboard_nav must be a boolean" in scripts,
        "scripts.html lost the keyboard_nav warning/fallback validation",
    )
    require(
        "$hasKeyboardNav := and $interactiveOutput" in scripts,
        "keyboard-nav is still restricted to shell layouts",
    )

    defaults = (ROOT / "hugo.yaml").read_text(encoding="utf-8")
    require(
        re.search(r"^    keyboard_nav: true$", defaults, re.MULTILINE) is not None,
        "hugo.yaml no longer defaults ui.keyboard_nav to true",
    )

    source = (ROOT / "assets" / "js" / "keyboard-nav.js").read_text(encoding="utf-8")
    require(
        "event.isComposing || event.keyCode === 229" in source
        and "isTypingTarget" in source
        and "data-td-shell-lock" in source
        and "dialog[open]" in source,
        "keyboard-nav lost an IME, typing, or overlay guard",
    )
    require(
        "event.shiftKey" in source and "[role=\"dialog\"]" in source,
        "keyboard-nav lost the Shift or ARIA-dialog guard",
    )
    for key in KEYMAP:
        require(f"key === {key}" in source, f"keyboard-nav lost the {key} binding")
    require(
        "rtl ? 'ArrowRight' : 'ArrowLeft'" in source
        and "rtl ? 'ArrowLeft' : 'ArrowRight'" in source,
        "keyboard-nav lost the RTL-aware ArrowLeft/ArrowRight bindings",
    )
    bound = set(re.findall(r"key === '((?:\\\\|[^'])+)'", source))
    bound |= set(re.findall(r'key === "([^"]+)"', source))
    documented = {literal[1:-1] for literal in KEYMAP}
    require(
        bound == documented,
        f"keyboard-nav binds undocumented keys: {sorted(bound - documented)}",
    )
    require(
        "data-td-pager-" in source and 'link[rel="' in source,
        "keyboard-nav lost a paging source",
    )
    paging = source.partition("function pageTarget(direction)")[2].partition(
        "function goPage(direction)"
    )[0]
    require(
        "visibleTreeLinks(menu())" in paging
        and "[data-td-pager]" in paging
        and paging.index("visibleTreeLinks(menu())") < paging.index("[data-td-pager]"),
        "keyboard-nav must keep the rendered sidebar ahead of pager fallbacks",
    )
    require(
        "data-td-kbd-zen" in source and "sessionStorage" in source,
        "keyboard-nav lost the zen-mode toggle or its persistence",
    )
    require(
        "data-td-keyboard-dialog" in source
        and "data-td-keyboard-help-source" in source
        and "OinkSurfaceCoordinator" in source
        and "beforeprint" in source,
        "keyboard-nav lost the ' shortcut help dialog, its template, or surface coordination",
    )
    require(
        "data-td-blog-index-toggle" in source
        and "data-td-expo-mode" in source
        and "data-td-expo-size" in source
        and "data-td-blog-gallery" in source
        and "data-gallery-mode" in source
        and "data-gallery-size" in source,
        "keyboard-nav lost the L blog layout toggle or Expo / blog gallery ; / < > controls",
    )
    shortcuts = source.partition("var SHORTCUTS = {")[2].partition("};")[0]
    declared = set(re.findall(r"^\s*'?([a-z-]+)'?:", shortcuts, re.MULTILINE))
    require(
        declared == set(SHEET_ROWS),
        f"keyboard-nav availability table drifted from the sheet: {sorted(declared ^ set(SHEET_ROWS))}",
    )
    help_source = (ROOT / "layouts" / "_partials" / "shell" / "keyboard-help.html").read_text(
        encoding="utf-8"
    )
    sheet_rows = re.findall(r'\(dict "id" "([a-z-]+)" "keys"', help_source)
    require(
        sheet_rows == SHEET_ROWS,
        f"the shortcut sheet is no longer the 3 x 10 grid in contract order: {sheet_rows}",
    )
    for action in ("edit_page", "create_child_page", "create_issue", "print", "open_chatgpt",
                   "open_claude", "open_gemini", "view_markdown", "switch_version"):
        require(f"'{action}'" in source, f"keyboard-nav no longer reaches the {action} action")
    require(
        "td-shell-article-w" in source and "WIDTH_STEP = 100" in source
        and "WIDTH_MIN = 600" in source and "clearWidth()" in source,
        "keyboard-nav lost the - / = reading width, its bounds, or its return to the page width",
    )
    require(
        "source: 'api'" in source and "data-td-kbd-instant" in source
        and "data-td-code-expand" in source and "querySelectorAll('details')" in source,
        "keyboard-nav lost O fold-all coverage or its active-path-safe commit",
    )
    history = (ROOT / "assets" / "js" / "history.js").read_text(encoding="utf-8")
    require(
        "'td-history:'" in history and "LIMIT = 100" in history
        and "data-td-history-scope" in history and "browse_history" in history
        and "localStorage" in history,
        "history.js lost its site-scoped key, entry cap, or Command Palette executor",
    )
    require(
        not re.search(r"sendBeacon|fetch\(|XMLHttpRequest|analytics", history),
        "browsing history must never leave the browser",
    )
    require(
        'resources.Get "js/history.js") (resources.Get "js/keyboard-nav.js")' in scripts
        and 'shell/history-dialog.html' in scripts,
        "scripts.html no longer ships history.js before keyboard-nav.js or the history overlay",
    )
    require(
        '"mode" "template"' in scripts and 'footer-style.html' in scripts,
        "scripts.html no longer provides a keyboard-help template when footer_style is none",
    )
    require(
        "data-td-shell-sidebar" in source and "data-td-shell-sidebar-toggle" in source,
        "keyboard-nav lost collapsed-sidebar restoration",
    )
    require(
        "#TableOfContents" in source
        and "[data-td-landing]" in source
        and "hasReadingShortcuts()" in source,
        "keyboard-nav lost the shell outline or homepage section source for j/k",
    )
    prepaint = (ROOT / "layouts" / "_partials" / "shell" / "prepaint.html").read_text(
        encoding="utf-8"
    )
    require(
        ".IsHome" in prepaint and "td-kbd-zen" in prepaint,
        "homepage focus mode is not restored before paint",
    )
    require(
        "td-shell-article-w" in prepaint and "data-td-shell-article-w" in prepaint
        and "articlePixels >= 600" in prepaint,
        "the reader's reading width is not restored before paint with the minimum bound",
    )
    layout = (ROOT / "assets" / "css" / "td" / "shell" / "layout.css").read_text(encoding="utf-8")
    require(
        "html[data-td-shell-article-w] .td-shell-layout .td-shell-article" in layout
        and "var(--td-shell-article-w" in layout,
        "shell/layout.css no longer applies the reader's reading width",
    )
    require(
        "SCROLL_DURATION = 100" in source
        and "Math.pow(1 - progress, 3)" in source
        and "outlineCursor" in source,
        "j/k lost the fast fixed-duration glide or queued outline cursor",
    )
    require(
        "getPropertyValue('scroll-padding-top')" in source
        and "getPropertyValue('scroll-margin-block-start')" in source,
        "j/k no longer shares the native TOC anchor offset",
    )
    require(
        "style.scrollBehavior = 'auto'" in source,
        "j/k no longer bypasses the root smooth-scroll rule during animation",
    )

    footer = (ROOT / "assets" / "js" / "footer-collapse.js").read_text(encoding="utf-8")
    require(
        "td-footer-collapsed" in footer and "localStorage" in footer,
        "footer-collapse lost its persistence key",
    )
    footer_line = (ROOT / "layouts" / "_partials" / "shell" / "footer-line.html").read_text(
        encoding="utf-8"
    )
    require(
        "data-td-footer-toggle" in footer_line
        and 'T "ui_footer_collapse"' in footer_line
        and 'T "ui_footer_expand"' in footer_line,
        "footer-line lost the localized collapse toggle",
    )
    require(
        'resources.Get "js/footer-collapse.js"' in scripts
        and "$hasFooterCollapse -}}" in scripts
        and '"target" "js/chunks/footer-collapse.js"' in scripts,
        "scripts.html does not gate the stable footer-collapse runtime",
    )
    require(
        '$hasFooterCollapse := and $interactiveOutput (or $footerData.brand $footerData.columns)'
        in scripts,
        "footer-collapse is not gated on rendered fat-footer data",
    )
    require(
        not re.search(r"sendBeacon|analytics|telemetry|XMLHttpRequest", source, re.IGNORECASE),
        "keyboard-nav introduced telemetry",
    )

    pager = (ROOT / "layouts" / "_partials" / "pager.html").read_text(encoding="utf-8")
    require(
        "data-td-pager-prev" in pager and "data-td-pager-next" in pager,
        "pager.html lost its keyboard-nav hooks",
    )
    navbar = (ROOT / "layouts" / "_partials" / "navbar.html").read_text(encoding="utf-8")
    navbar_link = (ROOT / "layouts" / "_partials" / "navbar-entry-link.html").read_text(
        encoding="utf-8"
    )
    require(
        "data-td-navbar-route" in navbar and "data-td-navbar-route" in navbar_link,
        "navbar lost the internal route-cycle hooks",
    )


def toggle_off(config: str) -> str:
    marker = "    feedback:\n      enable: false\n"
    require(marker in config, "fixture config lost the ui.feedback marker")
    return config.replace(
        marker,
        "    keyboard_nav: false\n" + marker,
    )


def footer_none(config: str) -> str:
    marker = "    feedback:\n      enable: false\n"
    require(marker in config, "fixture config lost the ui.feedback marker")
    return config.replace(
        marker,
        "    footer_style: none\n" + marker,
    )


def invalid_value(config: str) -> str:
    marker = "    feedback:\n      enable: false\n"
    return config.replace(
        marker,
        "    keyboard_nav: definitely\n" + marker,
    )


def main() -> int:
    try:
        check_sources()
        actions = load_actions()
        helper = actions.load_contract_module()
        with tempfile.TemporaryDirectory(prefix="oink-keyboard-") as temporary:
            workspace = Path(temporary)
            config = actions.action_config(helper, False)

            output, _ = actions.build(helper, workspace, "kbd-on", config)
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(
                encoding="utf-8"
            )
            require(
                any("OinkKeyboardNav" in bundle for bundle in referenced_bundles(output, html)),
                "default bundle omitted the keyboard-nav runtime",
            )
            home_html = (output / "en" / "index.html").read_text(encoding="utf-8")
            require('data-td-history-scope="/"' in home_html, "root site lost its history scope")
            require(
                any(
                    "OinkKeyboardNav" in bundle
                    for bundle in referenced_bundles(output, home_html)
                ),
                "homepage bundle omitted the keyboard-nav runtime",
            )
            require(
                "data-td-navbar-route" in home_html,
                "homepage omitted the navbar route-cycle hooks",
            )

            subpath_config = actions.action_config(helper, True)
            for label, path in (("subpath", "/preview/"), ("unicode", "/%E7%8C%AA/")):
                output, _ = actions.build(helper, workspace, f"kbd-{label}", subpath_config.replace(
                    "baseURL: https://example.org/preview/", f"baseURL: https://example.org{path}"
                ))
                for lang in ("en", "zh"):
                    page = (output / lang / "index.html").read_text(encoding="utf-8")
                    require(f'data-td-history-scope="{path}"' in page,
                            f"{lang} history should use the site's encoded base path {path}")
                    require(f'data-td-shortcut-preference="{path}"' in page,
                            f"{lang} shortcut preference should use the site's base path {path}")

            output, _ = actions.build(helper, workspace, "kbd-off", toggle_off(config))
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(
                encoding="utf-8"
            )
            for bundle in referenced_bundles(output, html):
                require(
                    "OinkKeyboardNav" not in bundle,
                    "disabled site still bundles the keyboard-nav runtime",
                )
            home_html = (output / "en" / "index.html").read_text(encoding="utf-8")
            for bundle in referenced_bundles(output, home_html):
                require(
                    "OinkKeyboardNav" not in bundle,
                    "disabled site still bundles keyboard-nav on the homepage",
                )

            output, _ = actions.build(
                helper,
                workspace,
                "kbd-page-off",
                config,
                page_front_matter="keyboard_nav: false",
            )
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(
                encoding="utf-8"
            )
            for bundle in referenced_bundles(output, html):
                require(
                    "OinkKeyboardNav" not in bundle,
                    "front matter opt-out still bundles the runtime",
                )

            output, _ = actions.build(
                helper,
                workspace,
                "kbd-footer-none",
                footer_none(config),
            )
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(
                encoding="utf-8"
            )
            require(
                "data-td-keyboard-help-source" in html,
                "footer_style: none with keyboard_nav on omitted the ' shortcut help source template",
            )
            require('data-td-shortcut-preference="/"' in html,
                    "a footerless page must still let the reader turn single-key shortcuts back on")
            require(
                html.count('class="td-shell-keyboard-help__row" data-td-shortcut=') == 30,
                "the shortcut help template no longer carries thirty rows",
            )
            require(
                'id="td-shell-history"' in html and "data-td-history-scope=" in html,
                "a keyboard page omitted the browsing history overlay",
            )
            output, _ = actions.build(
                helper,
                workspace,
                "kbd-footer-none-off",
                toggle_off(footer_none(config)),
            )
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(
                encoding="utf-8"
            )
            require(
                "data-td-keyboard-help-source" not in html,
                "footer_style: none with keyboard_nav off still emitted the shortcut help template",
            )
            require('data-td-shortcut-preference="/"' in html,
                    "local search alone should let the reader disable the palette's character shortcuts")
            require(
                'id="td-shell-history"' not in html,
                "keyboard_nav off still emitted the browsing history overlay",
            )

            try:
                actions.build(helper, workspace, "kbd-invalid", invalid_value(config))
            except Exception as exc:  # noqa: BLE001 - the helper's error type is dynamic
                require(
                    "params.ui.keyboard_nav must be a boolean" in str(exc),
                    "invalid keyboard_nav value failed for the wrong reason",
                )
            else:
                raise RuntimeError("invalid keyboard_nav value did not fail the build")

        for test in ("keyboard-nav.test.js", "history.test.js"):
            result = subprocess.run(
                ["node", str(ROOT / "tests" / "js" / test)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            require(
                result.returncode == 0,
                f"{test} failed:\n" + (result.stdout + result.stderr).strip(),
            )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"keyboard navigation check failed: {exc}", file=sys.stderr)
        return 1

    print("keyboard navigation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
