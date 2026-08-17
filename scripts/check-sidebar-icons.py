#!/usr/bin/env python3
"""Build and verify every sidebar icon density policy."""

from __future__ import annotations

import importlib.util
import re
import shutil
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCRIPT = ROOT / "scripts" / "check-navigation-contract.py"


def load_contract_module() -> Any:
    spec = importlib.util.spec_from_file_location("navigation_contract", CONTRACT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the navigation fixture helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SidebarParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.policy = ""
        self.rows: dict[str, dict[str, Any]] = {}
        self._link: dict[str, Any] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {name: value or "" for name, value in attrs}
        classes = set(values.get("class", "").split())
        if tag == "nav" and "td-shell-tree" in classes:
            self.policy = values.get("data-td-sidebar-icon-policy", "")
        elif tag == "a" and "td-shell-tree__link" in classes:
            self._link = {"text": [], "icon": False, "current": values.get("aria-current")}
        elif tag == "i" and self._link is not None:
            self._link["icon"] = True

    def handle_data(self, data: str) -> None:
        if self._link is not None:
            self._link["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link is not None:
            text = " ".join("".join(self._link["text"]).split())
            self.rows[text] = {
                "icon": self._link["icon"],
                "current": self._link["current"],
            }
            self._link = None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_case(helper: Any, workspace: Path, name: str, value: str | None) -> tuple[dict[str, SidebarParser], str]:
    site = workspace / f"site-{name}"
    output = workspace / f"public-{name}"
    shutil.copytree(helper.SITE_FIXTURE_PATH, site)
    config = helper.config_text("flat", False, False)
    config = config.replace(
        "    docs_section: docs\n",
        "    docs_section: docs\n"
        "    sidebar_root_enabled: true\n"
        "    sidebar_root_menu: false\n"
        "    sidebar_menu_foldable: true\n",
    )
    if value is not None:
        config = config.replace(
            "    docs_section: docs\n",
            f"    docs_section: docs\n    sidebar_icon_policy: {value}\n",
        )
    (site / "hugo.yaml").write_text(config, encoding="utf-8")
    log = helper.run_hugo(site, output, workspace / "cache")
    parsed: dict[str, SidebarParser] = {}
    for lang in helper.LANGUAGES:
        html = (output / lang / "docs" / "guides" / "tutorial" / "index.html").read_text(
            encoding="utf-8"
        )
        parser = SidebarParser()
        parser.feed(html)
        parsed[lang] = parser
    return parsed, log


def main() -> int:
    try:
        helper = load_contract_module()
        with tempfile.TemporaryDirectory(prefix="oink-sidebar-icons-") as temp:
            workspace = Path(temp)
            cases = {
                "unset": None,
                "all": "all",
                "groups": "groups",
                "none": "none",
                "invalid": "dense",
            }
            observations: dict[str, dict[str, SidebarParser]] = {}
            logs: dict[str, str] = {}
            for name, value in cases.items():
                observations[name], logs[name] = build_case(
                    helper, workspace, name, value
                )

            require("WARN" not in logs["unset"], "unset policy emitted a warning")
            for name in ("all", "groups", "none"):
                require("WARN" not in logs[name], f"{name} policy emitted a warning")
            invalid_warnings = [
                line for line in logs["invalid"].splitlines() if "WARN" in line
            ]
            require(
                invalid_warnings
                and all(
                    "invalid params.ui.sidebar_icon_policy" in line
                    and "using all" in line
                    for line in invalid_warnings
                ),
                "invalid policy did not warn and fall back to all",
            )

            labels = {
                "en": {
                    "root": "Docs",
                    "active_group": "Guides",
                    "active_leaf": "First Tutorial",
                    "collapsed_group": "Admin",
                    "collapsed_leaf": "Configuration",
                    "leaf": "Reference",
                },
                "zh": {
                    "root": "文档",
                    "active_group": "指南",
                    "active_leaf": "第一个教程",
                    "collapsed_group": "管理",
                    "collapsed_leaf": "配置",
                    "leaf": "参考",
                },
            }
            for lang, names in labels.items():
                unset = observations["unset"][lang]
                all_case = observations["all"][lang]
                groups = observations["groups"][lang]
                none = observations["none"][lang]
                invalid = observations["invalid"][lang]
                require(unset.policy == "all", f"{lang} unset policy is not all")
                require(all_case.policy == "all", f"{lang} all policy marker changed")
                require(groups.policy == "groups", f"{lang} groups policy marker changed")
                require(none.policy == "none", f"{lang} none policy marker changed")
                require(invalid.policy == "all", f"{lang} invalid policy did not fall back")
                require(
                    unset.rows == all_case.rows == invalid.rows,
                    f"{lang} unset or invalid policy is not output-compatible with all",
                )
                require(
                    names["active_leaf"] in all_case.rows
                    and all_case.rows[names["active_leaf"]]["current"] == "page",
                    f"{lang} active leaf is missing",
                )
                for label in names.values():
                    require(label in all_case.rows, f"{lang} missing fixture row {label}")
                    require(all_case.rows[label]["icon"], f"all hides icon for {label}")
                    require(not none.rows[label]["icon"], f"none emits icon for {label}")
                for key in ("root", "active_group", "collapsed_group"):
                    require(
                        groups.rows[names[key]]["icon"],
                        f"groups hides structural icon for {names[key]}",
                    )
                for key in ("active_leaf", "collapsed_leaf", "leaf"):
                    require(
                        not groups.rows[names[key]]["icon"],
                        f"groups emits leaf icon for {names[key]}",
                    )

            for html_path in (workspace / "public-none").glob("*/docs/**/*.html"):
                html = html_path.read_text(encoding="utf-8")
                sidebar = re.search(
                    r'<nav class="td-shell-tree".*?</nav>', html, re.DOTALL
                )
                if sidebar:
                    # Entry icons only: the tree's own chrome (fold chevrons)
                    # is dispensed by shell/icon.html as td-shell-icon glyphs
                    # and is not governed by the icon policy.
                    require(
                        not re.search(r'<i class="(?!td-shell-icon\b)', sidebar.group(0)),
                        f"none policy emitted icon markup in {html_path}",
                    )
    except (OSError, RuntimeError) as exc:
        print(f"Sidebar icon policy check failed: {exc}", file=sys.stderr)
        return 1
    print("Sidebar icon policy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
