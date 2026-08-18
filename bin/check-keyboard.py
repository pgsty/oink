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


ROOT = Path(__file__).resolve().parents[1]
ACTIONS_SCRIPT = ROOT / "bin" / "check-actions.py"

# Every key binds must appear in the runtime, and the runtime must not
# grow keys the contract table does not document. ArrowLeft/ArrowRight bind through
# the RTL swap ternary rather than a direct comparison.
KEYMAP = [
    "'w'", "'s'", "'a'", "'d'",
    "'j'", "'k'", "'n'", "'q'", "'e'",
    "'h'", "'l'", "'y'", "'t'", "'r'", "'f'",
    "'g'", "'c'", "' '", "'Escape'",
    "'ArrowUp'", "'ArrowDown'",
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
    sources = re.findall(r'<script\b[^>]*\bsrc="([^"]*?/js/page-[^"]+\.js)"', html)
    bundles: list[str] = []
    for source in sources:
        relative = re.sub(r"^https?://[^/]+", "", source).split("?", 1)[0]
        path = output / relative.lstrip("/")
        require(path.is_file(), f"referenced bundle is missing: {source}")
        bundles.append(path.read_text(encoding="utf-8"))
    require(bundles, "page references no feature bundle")
    return bundles


def check_sources() -> None:
    scripts = (ROOT / "layouts" / "_partials" / "scripts.html").read_text(encoding="utf-8")
    require(
        'resources.Get "js/keyboard-nav.js"' in scripts,
        "scripts.html does not assemble keyboard-nav.js",
    )
    require(
        "$hasKeyboardNav -}}" in scripts and 'range . }}{{ $bundleKey = printf "%s|%s" $bundleKey .Name }}' in scripts,
        "keyboard-nav is not appended under its flag into the derived bundle key",
    )
    require(
        "params.ui.keyboard_nav must be a boolean" in scripts,
        "scripts.html lost the keyboard_nav errorf validation",
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
    bound = set(re.findall(r"key === '([^']+)'", source))
    documented = {literal.strip("'") for literal in KEYMAP}
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
        and 'range . }}{{ $bundleKey = printf "%s|%s" $bundleKey .Name }}' in scripts,
        "scripts.html does not assemble or key the footer-collapse runtime",
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

            try:
                actions.build(helper, workspace, "kbd-invalid", invalid_value(config))
            except Exception as exc:  # noqa: BLE001 - the helper's error type is dynamic
                require(
                    "params.ui.keyboard_nav must be a boolean" in str(exc),
                    "invalid keyboard_nav value failed for the wrong reason",
                )
            else:
                raise RuntimeError("invalid keyboard_nav value did not fail the build")

        result = subprocess.run(
            ["node", str(ROOT / "tests" / "js" / "keyboard-nav.test.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        require(
            result.returncode == 0,
            "keyboard-nav.test.js failed:\n" + (result.stdout + result.stderr).strip(),
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"keyboard navigation check failed: {exc}", file=sys.stderr)
        return 1

    print("keyboard navigation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
