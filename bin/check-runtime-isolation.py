#!/usr/bin/env python3
"""Check runtime isolation and transient-surface wiring."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    try:
        search_enabled = read("layouts/_partials/shell/search-enabled.html")
        head = read("layouts/_partials/head.html")
        scripts = read("layouts/_partials/scripts.html")
        content = read("layouts/_partials/content/render.html")
        derived = read("layouts/_partials/content/register-derived.html")
        search_input = read("layouts/_partials/search-input.html")
        docs_shell = read("assets/js/docs-shell.js")
        palette = read("assets/js/command-palette.js")
        coordinator = read("assets/js/surface-coordinator.js")
        base = read("assets/js/base.js")

        # The predicate must combine the site opt-in, the shell surface, and a
        # print exclusion, reading the active format from the tdOutputFormat
        # page-store key that every baseof template sets.
        resolves_format = '"tdOutputFormat"' in search_enabled
        require(
            '.Site.Params.offline_search' in search_enabled
            and '.Site.Params.offline_search_on_serve' in search_enabled
            and 'hugo.IsServer' in search_enabled
            and 'printf "%T" $serveSearch' in search_enabled
            and 'partial "shell/chrome-enabled.html"' in search_enabled
            and resolves_format
            and '(ne $format "print")' in search_enabled,
            "search-enabled.html is not the complete build/surface capability predicate",
        )
        require(
            '{{ if partial "shell/search-enabled.html" . -}}' in head,
            "Lunr is not gated by the canonical capability",
        )
        require(
            '{{ if $localSearch -}}' in scripts
            and all(
                f'resources.Get "js/{name}.js"' in scripts
                for name in ("search-engine", "palette-model", "command-palette")
            ),
            "Palette controller is not gated by the canonical capability",
        )
        require(
            'resources.Get "js/offline-search.js"' not in scripts,
            "legacy offline-search runtime remains in the shared bundle",
        )
        require(
            'partial "content/register-derived.html"' in content
            and '.Store.Set "hasAuthoredA11y" true' in derived
            and 'type="checkbox"' in derived
            and "\\bfa-" in derived
            and '.Page.Store.Get "hasAuthoredA11y"' in scripts
            and 'resources.Get "js/authored-a11y.js"' in scripts,
            "authored accessibility repair is not isolated to pages that need it",
        )
        require(
            'partial "shell/search-enabled.html"' in search_input
            and "data-td-shell-search-open" in search_input
            and "data-offline-search" not in search_input,
            "legacy search-input partial does not delegate to the Palette",
        )
        require(
            "$hasGoogleSearch" in scripts and ".Site.Language.Lang" in scripts,
            "bundle key is missing search or language discriminators",
        )
        require(
            "function initSearch()" not in docs_shell
            and "td-shell-search" not in docs_shell,
            "search controller remains coupled to docs-shell.js",
        )
        require(
            "function initSearch(" in palette
            and "searchApi.create" in palette
            and "searchApi.group" in palette
            and "metaKey || event.ctrlKey" in palette
            and "tabTrap(panel, isOpen)" in palette,
            "extracted Palette lost search or keyboard behavior",
        )
        require(
            all(
                token in coordinator
                for token in ("register", "closeOthers", "closeAll", "keepNames")
            ),
            "surface coordinator API is incomplete",
        )
        for surface in (
            "palette",
            "drawer",
            "root-menu",
            "language-menu-",
            "version-menu-",
        ):
            require(
                surface in palette + docs_shell + base,
                f"surface coordinator is missing {surface}",
            )
        require(
            not re.search(r"\x1b|\r", palette + coordinator),
            "runtime source contains terminal/control characters",
        )
        require(
            "closest('#td-shell-sidebar')" in palette
            and "data-td-shell-drawer-open" in palette,
            "Palette does not promote a hidden drawer opener",
        )
        behavior = subprocess.run(
            ["node", str(ROOT / "tests/js/surfaces.test.js")],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        require(
            behavior.returncode == 0,
            "surface behavior test failed:\n"
            + (behavior.stdout + behavior.stderr).strip(),
        )
    except (OSError, RuntimeError) as exc:
        print(f"runtime check failed: {exc}", file=sys.stderr)
        return 1
    print("runtime isolation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
