#!/usr/bin/env python3
"""Build and verify Command Palette modes, data, and runtime gates."""

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
ACTIONS_SCRIPT = ROOT / "scripts" / "check-actions.py"


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
        relative = re.sub(r"^/preview/", "/", relative).lstrip("/")
        path = output / relative
        require(path.is_file(), f"referenced Palette bundle is missing: {source}")
        bundles.append(path.read_text(encoding="utf-8"))
    require(bundles, "page references no feature bundle")
    return bundles


def main() -> int:
    try:
        actions = load_actions()
        helper = actions.load_contract_module()
        with tempfile.TemporaryDirectory(prefix="oink-palette-") as temporary:
            workspace = Path(temporary)
            for deployment, subpath, prefix in (
                ("root", False, "/"),
                ("subpath", True, "/preview/"),
            ):
                output, log = actions.build(
                    helper,
                    workspace,
                    f"palette-{deployment}",
                    actions.action_config(helper, subpath),
                )
                require(
                    all("invalid search_boost" in line for line in log.splitlines() if "WARN" in line),
                    f"{deployment} Palette fixture emitted an unrelated warning",
                )
                for lang in helper.LANGUAGES:
                    html = (output / lang / "docs" / "guides" / "tutorial" / "index.html").read_text(
                        encoding="utf-8"
                    )
                    manifest = actions.manifest_from(html)
                    quick = manifest.get("quickLinks")
                    require(isinstance(quick, list) and len(quick) == 2, f"{deployment}/{lang} quick links changed")
                    require(
                        [entry["id"] for entry in quick] == ["quick_docs", "quick_blog"],
                        f"{deployment}/{lang} quick links stopped following Hugo Menu order",
                    )
                    require(
                        quick[0]["url"] == f"{prefix}{lang}/docs/"
                        and quick[1]["url"] == f"{prefix}{lang}/blog/",
                        f"{deployment}/{lang} quick links are not deployment safe",
                    )
                    require(
                        manifest.get("rootOrder", [])[:3] == ["docs", "blog", "project"],
                        f"{deployment}/{lang} page group order changed",
                    )
                    require(
                        all(token in html for token in (
                            'role="combobox"', 'role="listbox"',
                            'data-td-t-quick-links=', 'data-td-t-page-actions=',
                            'data-td-t-preferences=', 'data-td-t-commands=',
                            'data-td-t-no-commands=', 'enterkeyhint="go"',
                        )),
                        f"{deployment}/{lang} Palette markup or localization is incomplete",
                    )
                    bundles = referenced_bundles(output, html)
                    require(
                        any("OinkPaletteModel" in bundle for bundle in bundles),
                        f"{deployment}/{lang} referenced bundle omitted the result model",
                    )
                    require(
                        any("OinkCommandPalette =" in bundle for bundle in bundles),
                        f"{deployment}/{lang} referenced bundle omitted the controller",
                    )

            output, _ = actions.build(
                helper,
                workspace,
                "palette-off",
                actions.action_config(helper, True, offline_search=False),
            )
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(
                encoding="utf-8"
            )
            require('id="td-shell-search"' not in html, "search-off page emitted Palette markup")
            require("lunr.min.js" not in html, "search-off page emitted Lunr")
            for bundle in referenced_bundles(output, html):
                require("OinkPaletteModel =" not in bundle, "search-off page loaded Palette model")
                # keyboard-nav.js may *reference* the palette global as a
                # consumer; only the controller's own definition is barred.
                require(
                    "OinkCommandPalette =" not in bundle,
                    "search-off page loaded Palette controller",
                )

        for script in (
            "palette-model.test.js",
            "command-palette.test.js",
        ):
            result = subprocess.run(
                ["node", str(ROOT / "tests" / "js" / script)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            require(
                result.returncode == 0,
                f"{script} failed:\n" + (result.stdout + result.stderr).strip(),
            )

        source = (ROOT / "assets" / "js" / "command-palette.js").read_text(encoding="utf-8")
        require(
            "if (normalQuery(input.value)) ensureIndex();" in source
            and "event.isComposing || composing || event.keyCode === 229" in source
            and "registry.safeUrl" in source,
            "Palette lost lazy index, IME, or URL protection",
        )
        require("@docs" not in source and "@blog" not in source, "Palette gained a v1-excluded scope")
        require(
            not re.search(r"sendBeacon|analytics|telemetry|XMLHttpRequest", source, re.IGNORECASE),
            "Palette introduced telemetry",
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Command Palette check failed: {exc}", file=sys.stderr)
        return 1

    print("Command Palette checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
