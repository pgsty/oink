#!/usr/bin/env python3
"""Build and verify PRD 6 keyboard navigation gating, assembly, and runtime."""

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
ACTIONS_SCRIPT = ROOT / "scripts" / "check-prd4-actions.py"

# Every key PRD 6 binds must appear in the runtime, and the runtime must not
# grow keys the PRD table does not document. ArrowLeft/ArrowRight bind through
# the RTL swap ternary rather than a direct comparison.
KEYMAP = [
    "'w'", "'s'", "'a'", "'d'",
    "'j'", "'k'", "'q'", "'e'",
    "'h'", "'l'", "'t'", "'f'",
    "'g'", "'c'", "' '", "'Escape'",
    "'ArrowUp'", "'ArrowDown'",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_actions() -> Any:
    spec = importlib.util.spec_from_file_location("prd4_actions", ACTIONS_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PRD 4 action fixture helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def referenced_bundles(output: Path, html: str) -> list[str]:
    sources = re.findall(r'<script\b[^>]*\bsrc="([^"]*?/js/main-[^"]+\.js)"', html)
    bundles: list[str] = []
    for source in sources:
        relative = re.sub(r"^https?://[^/]+", "", source).split("?", 1)[0]
        path = output / relative.lstrip("/")
        require(path.is_file(), f"referenced bundle is missing: {source}")
        bundles.append(path.read_text(encoding="utf-8"))
    require(bundles, "page references no main bundle")
    return bundles


def check_sources() -> None:
    scripts = (ROOT / "layouts" / "_partials" / "scripts.html").read_text(encoding="utf-8")
    require(
        'resources.Get "js/keyboard-nav.js"' in scripts,
        "scripts.html does not assemble keyboard-nav.js",
    )
    require(
        "$hasKeyboardNav" in scripts.split("$bundleKey := ", 1)[1].split("| md5", 1)[0],
        "keyboard-nav gate is missing from the bundle key",
    )
    require(
        "params.ui.keyboard_nav.enable must be a boolean" in scripts,
        "scripts.html lost the keyboard_nav errorf validation",
    )

    defaults = (ROOT / "hugo.yaml").read_text(encoding="utf-8")
    require(
        re.search(r"keyboard_nav:\n\s+enable: true", defaults) is not None,
        "hugo.yaml no longer defaults keyboard_nav.enable to true",
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
    require(
        "data-td-kbd-zen" in source and "sessionStorage" in source,
        "keyboard-nav lost the zen-mode toggle or its persistence",
    )
    require(
        "data-td-shell-sidebar" in source and "data-td-shell-sidebar-toggle" in source,
        "keyboard-nav lost collapsed-sidebar restoration",
    )
    require(
        "#TableOfContents" in source,
        "keyboard-nav lost the outline source for j/k",
    )
    require(
        "SCROLL_DURATION = 100" in source
        and "Math.pow(1 - progress, 3)" in source
        and "outlineCursor" in source,
        "j/k lost the fast fixed-duration glide or queued outline cursor",
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
        and "$hasFooterCollapse" in scripts.split("$bundleKey := ", 1)[1].split("| md5", 1)[0],
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


def toggle_off(config: str) -> str:
    marker = "    feedback:\n      enable: false\n"
    require(marker in config, "fixture config lost the ui.feedback marker")
    return config.replace(
        marker,
        "    keyboard_nav:\n      enable: false\n" + marker,
    )


def invalid_value(config: str) -> str:
    marker = "    feedback:\n      enable: false\n"
    return config.replace(
        marker,
        "    keyboard_nav:\n      enable: definitely\n" + marker,
    )


def main() -> int:
    try:
        check_sources()
        actions = load_actions()
        helper = actions.load_contract_module()
        with tempfile.TemporaryDirectory(prefix="oink-prd6-keyboard-") as temporary:
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

            output, _ = actions.build(helper, workspace, "kbd-off", toggle_off(config))
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(
                encoding="utf-8"
            )
            for bundle in referenced_bundles(output, html):
                require(
                    "OinkKeyboardNav" not in bundle,
                    "disabled site still bundles the keyboard-nav runtime",
                )

            output, _ = actions.build(
                helper,
                workspace,
                "kbd-page-off",
                config,
                page_front_matter="ui:\n  keyboard_nav:\n    enable: false",
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
                    "params.ui.keyboard_nav.enable must be a boolean" in str(exc),
                    "invalid keyboard_nav value failed for the wrong reason",
                )
            else:
                raise RuntimeError("invalid keyboard_nav value did not fail the build")

        result = subprocess.run(
            ["node", str(ROOT / "tests" / "js" / "prd6-keyboard-nav.test.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        require(
            result.returncode == 0,
            "prd6-keyboard-nav.test.js failed:\n" + (result.stdout + result.stderr).strip(),
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"PRD 6 keyboard navigation check failed: {exc}", file=sys.stderr)
        return 1

    print("PRD 6 keyboard navigation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
