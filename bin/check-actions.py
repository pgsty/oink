#!/usr/bin/env python3
"""Build and verify action descriptors, registry, and command safety."""

from __future__ import annotations

import importlib.util
import html as html_module
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from test_site import TEST_SITE, fixture_config


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCRIPT = ROOT / "bin" / "check-navigation-contract.py"
# Order is part of the contract: the title menu renders these in sequence, so
# this list is also the reading order a visitor sees. The choice trio mirrors
# the navbar control order — version, language, theme (keyboard-nav contract).
BUILTINS = [
    "copy_markdown",
    "copy_link",
    "open_chatgpt",
    "open_claude",
    "view_markdown",
    "view_history",
    "edit_page",
    "create_child_page",
    "create_issue",
    "create_project_issue",
    "print_section",
    "print",
    "switch_version",
    "switch_language",
    "switch_theme",
    "open_github",
]
ACTION_FIELDS = {
    "id",
    "title",
    "description",
    "icon",
    "keywords",
    "kind",
    "available",
    "disabledReason",
    "url",
    "target",
    "placements",
    "options",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_contract_module() -> Any:
    spec = importlib.util.spec_from_file_location("navigation_contract", CONTRACT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the navigation fixture helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def action_config(helper: Any, subpath: bool, offline_search: bool = True) -> str:
    config = helper.config_text("flat", offline_search, subpath)
    config = config.replace(
        "  github_project_repo: https://github.com/pgsty/oink\n",
        "  github_project_repo: https://github.com/acme/project\n"
        "  github_repo: https://github.com/acme/docs\n"
        "  github_branch: release\n"
        "  github_subdir: website\n"
        "  version_menu: Version v1\n"
        "  version: v1\n"
        "  version_menu_pagelinks: true\n"
        "  versions:\n"
        "    - name: Version 1\n"
        "      version: v1\n"
        "      url: https://v1.example.com\n"
        "    - name: ---\n"
        "    - name: Future\n"
        "      version: v2\n",
    )
    config = config.replace(
        "    feedback:\n      enable: false\n",
        "    dark_mode:\n"
        "      show_menu: true\n"
        "    page_context_menu:\n"
        "      assistant_links: true\n"
        "    feedback:\n      enable: false\n",
    )
    en_commands = (
        "    params:\n"
        "      ui:\n"
        "        command_palette:\n"
        "          commands:\n"
        "            - id: status\n"
        "              title: Service status\n"
        "              description: Current service health\n"
        "              url: https://status.example.com/\n"
        "              icon: fa-solid fa-signal\n"
        "              keywords: [uptime, incident]\n"
        "            - id: print_now\n"
        "              title: Print now\n"
        "              action: print\n"
        "              keywords: [paper]\n"
        "            - id: theme_now\n"
        "              title: Choose theme\n"
        "              action: switch_theme\n"
        "            - id: language_now\n"
        "              title: Choose language\n"
        "              action: switch_language\n"
        "            - id: version_now\n"
        "              title: Choose version\n"
        "              action: switch_version\n"
        "            - id: escaped\n"
        "              title: '</script><script>alert(1)</script>'\n"
        "              url: /safe/\n"
    )
    zh_commands = (
        "    params:\n"
        "      ui:\n"
        "        command_palette:\n"
        "          commands:\n"
        "            - id: print_now\n"
        "              title: 立即打印\n"
        "              keywords: [纸张]\n"
        "            - id: status\n"
        "              title: 服务状态\n"
        "              description: 当前服务健康状态\n"
        "              keywords: [可用性, 事故]\n"
    )
    config = config.replace("    weight: 1\n  zh:\n", "    weight: 1\n" + en_commands + "  zh:\n")
    config = config.replace("    weight: 2\nmenus:\n", "    weight: 2\n" + zh_commands + "menus:\n")
    return config


def build(
    helper: Any,
    workspace: Path,
    name: str,
    config: str,
    page_front_matter: str = "",
) -> tuple[Path, str]:
    site = workspace / f"site-{name}"
    output = workspace / f"public-{name}"
    shutil.copytree(helper.SITE_FIXTURE_PATH, site)
    (site / "hugo.yaml").write_text(config, encoding="utf-8")
    if page_front_matter:
        page = site / "content" / "docs" / "guides" / "tutorial.md"
        source = page.read_text(encoding="utf-8")
        marker = "\n---\n\n"
        require(marker in source, "action fixture has no closing front matter marker")
        page.write_text(
            source.replace(
                marker,
                f"\n{page_front_matter.rstrip()}\n---\n\n",
                1,
            ),
            encoding="utf-8",
        )
    log = helper.run_hugo(site, output, workspace / "cache")
    return output, log


def validate_assistant_off(output: Path, label: str) -> None:
    html = (
        output / "en" / "docs" / "guides" / "tutorial" / "index.html"
    ).read_text(encoding="utf-8")
    actions = map_by_id(manifest_from(html)["actions"])
    for action_id in ("open_chatgpt", "open_claude"):
        action = actions[action_id]
        require(
            action["available"] is False
            and action["url"] == ""
            and action["placements"] == {"page": False, "palette": False},
            f"{label} still exposes {action_id}",
        )
        require(
            f'data-td-action="{action_id}"' not in html,
            f"{label} still renders {action_id}",
        )
    require(
        'data-td-action="copy_markdown"' in html,
        f"{label} removed unrelated page actions",
    )


def validate_external_mount_actions() -> None:
    """A mounted source outside WorkingDir must not leak its absolute path."""

    with tempfile.TemporaryDirectory(prefix="oink-external-actions-") as temp:
        public = Path(temp) / "public"
        result = subprocess.run(
            [
                "hugo",
                "--source",
                str(TEST_SITE),
                "--themesDir",
                str(ROOT.parent),
                "--destination",
                str(public),
                "--config",
                fixture_config(ROOT / "tests/fixtures/external-actions.yml"),
                "--printPathWarnings",
                "--panicOnWarning",
                "--quiet",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        require(
            result.returncode == 0,
            "external-mount action fixture failed:\n" + result.stdout + result.stderr,
        )
        html = (public / "blog/external-mount/index.html").read_text(encoding="utf-8")
    actions = map_by_id(manifest_from(html)["actions"])
    for action_id in ("view_history", "edit_page", "create_child_page"):
        require(
            actions[action_id]["available"] is False
            and actions[action_id]["url"] == "",
            f"external mount still exposes {action_id}: {actions[action_id]['url']}",
        )
    require(
        actions["create_issue"]["available"] is True
        and actions["create_issue"]["url"].startswith(
            "https://github.com/pgsty/oink/issues/new?"
        ),
        "external mount lost its repository issue action",
    )
    for marker in ("/Users/", "/home/runner/", "/private/tmp/", "/var/folders/"):
        require(marker not in html, f"external mount leaked machine path {marker}")


def manifest_from(html: str) -> dict[str, Any]:
    match = re.search(
        r'<script type="application/json" id="td-action-manifest">(.*?)</script>',
        html,
        re.DOTALL,
    )
    require(match is not None, "page omitted the action manifest")
    payload = match.group(1)
    require("</script" not in payload.lower(), "manifest contains an executable closing tag")
    value = json.loads(payload)
    require(isinstance(value, dict), "manifest is not a JSON object")
    return value


def map_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["id"]: record for record in records}


def attribute(html: str, action_id: str, name: str) -> str:
    match = re.search(
        rf'<a\b(?=[^>]*\bdata-td-action="{re.escape(action_id)}")([^>]*)>',
        html,
    )
    require(match is not None, f"missing anchor for {action_id}")
    value = re.search(rf'\b{name}="([^"]*)"', match.group(1))
    require(value is not None, f"{action_id} anchor omitted {name}")
    return html_module.unescape(value.group(1))


def validate_manifest(
    manifest: dict[str, Any], lang: str, prefix: str
) -> None:
    require(manifest.get("version") == 1, "manifest version changed")
    require(manifest.get("language") == lang, f"{lang} manifest language changed")
    actions = manifest.get("actions")
    require(isinstance(actions, list), f"{lang} actions are not an array")
    require([action.get("id") for action in actions] == BUILTINS, f"{lang} built-in order changed")
    for action in actions:
        require(ACTION_FIELDS <= set(action), f"{lang}/{action.get('id')} descriptor is incomplete")
        require(isinstance(action["available"], bool), f"{lang}/{action['id']} availability is not boolean")
        require(isinstance(action["keywords"], list), f"{lang}/{action['id']} keywords are not an array")
        require(isinstance(action["options"], list), f"{lang}/{action['id']} options are not an array")
        if not action["available"]:
            require(action["disabledReason"], f"{lang}/{action['id']} lacks an unavailable reason")

    by_id = map_by_id(actions)
    expected_assistant_icons = {
        "open_chatgpt": "fa-brands fa-openai",
        "open_claude": "fa-brands fa-claude",
    }
    for action_id, expected_icon in expected_assistant_icons.items():
        require(
            by_id[action_id]["icon"] == expected_icon,
            f"{lang}/{action_id} does not use the Font Awesome icon",
        )
    markdown = f"{prefix}{lang}/docs/guides/tutorial/index.md"
    require(by_id["copy_markdown"]["url"] == markdown, f"{lang} copy URL is not subpath safe")
    require(by_id["view_markdown"]["url"] == markdown, f"{lang} view URL diverges from copy")
    require(by_id["copy_markdown"]["available"] is True, f"{lang} copy is unavailable")
    for action_id, host in (("open_chatgpt", "chatgpt.com"), ("open_claude", "claude.ai")):
        require(
            by_id[action_id].get("promptTemplate", "").count("%s") == 1,
            f"{lang}/{action_id} omitted its runtime URL placeholder",
        )
        require(
            by_id[action_id]["url"].startswith(f"https://{host}/"),
            f"{lang}/{action_id} fallback URL changed",
        )
    require(
        by_id["edit_page"]["url"]
        == "https://github.com/acme/docs/edit/release/website/content/docs/guides/tutorial."
        + ("zh.md" if lang == "zh" else "md"),
        f"{lang} edit URL changed: {by_id['edit_page']['url']}",
    )
    require(
        by_id["view_history"]["url"]
        == "https://github.com/acme/docs/commits/release/website/content/docs/guides/tutorial."
        + ("zh.md" if lang == "zh" else "md"),
        f"{lang} history URL changed: {by_id['view_history']['url']}",
    )
    expected_title = "First+Tutorial" if lang == "en" else "%E7%AC%AC%E4%B8%80%E4%B8%AA%E6%95%99%E7%A8%8B"
    require(
        by_id["create_issue"]["url"]
        == f"https://github.com/acme/docs/issues/new?title={expected_title}",
        f"{lang} issue URL encoding changed: {by_id['create_issue']['url']}",
    )
    require(by_id["open_github"]["url"] == "https://github.com/acme/project", f"{lang} project URL changed")
    require(by_id["switch_theme"]["available"] is True, f"{lang} theme action unavailable")
    require(
        [option["id"] for option in by_id["switch_theme"]["options"]]
        == ["auto", "light", "dark"],
        f"{lang} theme choices changed",
    )
    language_options = by_id["switch_language"]["options"]
    require(len(language_options) == 2, f"{lang} language options changed")
    require(
        all(prefix in option["url"] for option in language_options),
        f"{lang} language target lost deployment prefix",
    )
    versions = by_id["switch_version"]["options"]
    require([option["id"] for option in versions] == ["v1", "v2"], f"{lang} version options changed")
    require(versions[0]["active"] is True and versions[0]["available"] is True, f"{lang} active version changed")
    require(versions[1]["available"] is False and versions[1]["disabledReason"], f"{lang} disabled version lacks reason")

    commands = map_by_id(manifest.get("commands", []))
    require(
        set(commands)
        == {
            "status",
            "print_now",
            "theme_now",
            "language_now",
            "version_now",
            "escaped",
        },
        f"{lang} command merge changed",
    )
    require(commands["status"]["kind"] == "url", f"{lang} URL command kind changed")
    require(commands["status"]["url"] == "https://status.example.com/", f"{lang} status URL fallback changed")
    require(
        commands["escaped"]["url"] == f"{prefix}{lang}/safe/",
        f"{lang} internal command URL is not language/subpath safe: {commands['escaped']['url']}",
    )
    require(commands["print_now"]["action"] == "print", f"{lang} built-in command changed")
    require(
        commands["theme_now"]["action"] == "switch_theme"
        and commands["language_now"]["action"] == "switch_language"
        and commands["version_now"]["action"] == "switch_version",
        f"{lang} choice command aliases changed",
    )
    if lang == "en":
        require(commands["status"]["title"] == "Service status", "EN title changed")
    else:
        require(commands["status"]["title"] == "服务状态", "ZH title did not localize by ID")
        require(commands["status"]["keywords"] == ["可用性", "事故"], "ZH keywords did not localize")
        require(commands["print_now"]["title"] == "立即打印", "out-of-order ZH merge failed")


def run_invalid_build(helper: Any, workspace: Path, name: str, command_yaml: str, expected: str) -> None:
    site = workspace / f"invalid-{name}"
    output = workspace / f"invalid-public-{name}"
    shutil.copytree(helper.SITE_FIXTURE_PATH, site)
    config = helper.config_text("flat", True, True)
    addition = (
        "    params:\n"
        "      ui:\n"
        "        command_palette:\n"
        "          commands:\n"
        + command_yaml
    )
    config = config.replace("    weight: 1\n  zh:\n", "    weight: 1\n" + addition + "  zh:\n")
    (site / "hugo.yaml").write_text(config, encoding="utf-8")
    result = subprocess.run(
        [
            "hugo",
            "--source",
            str(site),
            "--themesDir",
            str(ROOT.parent),
            "--destination",
            str(output),
            "--cacheDir",
            str(workspace / "cache-invalid"),
        ],
        cwd=site,
        env={**os.environ, "HUGO_ENVIRONMENT": "development"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    # Every invalid command warns and is dropped, unsafe URLs included: the
    # protection is refusing to emit the row, not stopping the build. A build
    # that dies takes every page of the site down with it over one bad config
    # entry, and --panicOnWarning below still fails where publishing happens.
    require(expected in result.stdout, f"invalid {name} build missed {expected!r}:\n{result.stdout}")
    require(result.returncode == 0,
            f"invalid {name} command stopped the build instead of warning:\n{result.stdout}")
    if "unsafe URL" in expected:
        # The dropped URL must not reach any rendered page -- that is the
        # whole point of refusing it.
        leaked = [
            path
            for path in output.rglob("*")
            if path.is_file() and "javascript:alert" in path.read_text(errors="ignore")
        ]
        require(not leaked, f"invalid {name} command leaked its unsafe URL into {leaked[:3]}")
    strict = subprocess.run(
        [
            "hugo", "--source", str(site), "--themesDir", str(ROOT.parent),
            "--destination", str(output) + "-strict",
            "--cacheDir", str(workspace / "cache-invalid-strict"),
            "--panicOnWarning",
        ],
        cwd=site,
        env={**os.environ, "HUGO_ENVIRONMENT": "development"},
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    require(strict.returncode != 0, f"invalid {name} command survived --panicOnWarning")


def main() -> int:
    try:
        helper = load_contract_module()
        validate_external_mount_actions()
        with tempfile.TemporaryDirectory(prefix="oink-actions-") as temp:
            workspace = Path(temp)
            for deployment, subpath, prefix in (
                ("root", False, "/"),
                ("subpath", True, "/preview/"),
            ):
                output, log = build(
                    helper,
                    workspace,
                    deployment,
                    action_config(helper, subpath),
                )
                require(
                    all("invalid search_boost" in line for line in log.splitlines() if "WARN" in line),
                    f"{deployment} action fixture emitted an unrelated warning",
                )
                stylesheets = sorted((output / "scss").glob("*.css"))
                require(stylesheets, f"{deployment} emitted no compiled stylesheet")
                compiled_css = "\n".join(
                    path.read_text(encoding="utf-8") for path in stylesheets
                )
                require(
                    ".fa-openai" in compiled_css and ".fa-claude" in compiled_css,
                    f"{deployment} stylesheet omitted Font Awesome assistant icons",
                )
                for lang in helper.LANGUAGES:
                    path = output / lang / "docs" / "guides" / "tutorial" / "index.html"
                    html = path.read_text(encoding="utf-8")
                    manifest = manifest_from(html)
                    validate_manifest(manifest, lang, prefix)
                    # The split button renders copy_markdown twice on purpose:
                    # once as the primary half, once as the first menu row.
                    # One partial owns both, so the URL-divergence hazard the
                    # old exactly-once rule guarded against cannot recur. Every
                    # other page-placed action renders once when available;
                    # `print` has no page placement at all (readers use ⌘P).
                    page_placed = map_by_id(manifest_from(html)["actions"])
                    for action_id in (
                        "copy_markdown",
                        "open_chatgpt",
                        "open_claude",
                        "view_markdown",
                        "view_history",
                        "edit_page",
                        "create_child_page",
                        "create_issue",
                        "create_project_issue",
                        "print_section",
                    ):
                        descriptor = page_placed[action_id]
                        expected = 0
                        if descriptor["available"] and descriptor["placements"]["page"]:
                            expected = 2 if action_id == "copy_markdown" else 1
                        require(
                            html.count(f'data-td-action="{action_id}"') == expected,
                            f"{deployment}/{lang} page action {action_id} is missing or duplicated",
                        )
                    require(
                        html.count('data-td-action="print"') == 0,
                        f"{deployment}/{lang} print action must not render on the page",
                    )
                    # copy_link is Palette-only: it renders on a page only
                    # where the share bar puts it, and this fixture has none.
                    require(
                        html.count('data-td-action="copy_link"') == 0,
                        f"{deployment}/{lang} copy_link action must not render without a share bar",
                    )
                    require(
                        page_placed["copy_link"]["url"].startswith("https://")
                        and page_placed["copy_link"]["url"].endswith(
                            f"{prefix}{lang}/docs/guides/tutorial/"
                        )
                        and page_placed["copy_link"]["placements"]
                        == {"page": False, "palette": True},
                        f"{deployment}/{lang} copy_link does not carry the page permalink for the Palette: "
                        + page_placed["copy_link"]["url"],
                    )
                    require(
                        html.count("data-td-page-actions-toggle") == 1,
                        f"{deployment}/{lang} title menu toggle is missing or duplicated",
                    )
                    require(
                        'id="td-shell-aside-actions"' not in html,
                        f"{deployment}/{lang} retired TOC-rail action group reappeared",
                    )
                    require("data-td-page-copy " not in html, "legacy copy controller remains")
                    require("data-td-page-print" not in html, "legacy print controller remains")
                    require("</script><script>alert(1)</script>" not in html, "command title escaped inert JSON")
                    by_id = map_by_id(manifest["actions"])
                    for action_id in ("open_chatgpt", "open_claude"):
                        require(
                            html.count(
                                f'<i class="{by_id[action_id]["icon"]}" aria-hidden="true"></i>'
                            )
                            == 1,
                            f"{deployment}/{lang} {action_id} icon is missing or duplicated",
                        )
                    for action_id in (
                        "open_chatgpt",
                        "open_claude",
                        "view_markdown",
                        "view_history",
                        "edit_page",
                        "create_child_page",
                        "create_issue",
                        "create_project_issue",
                    ):
                        if not by_id[action_id]["available"]:
                            continue
                        require(
                            attribute(html, action_id, "href") == by_id[action_id]["url"],
                            f"{deployment}/{lang} no-JS {action_id} link diverges from descriptor",
                        )
                        require(
                            attribute(html, action_id, "target") == "_blank",
                            f"{deployment}/{lang} {action_id} no longer opens externally",
                        )
                        require(
                            "noopener" in attribute(html, action_id, "rel").split(),
                            f"{deployment}/{lang} {action_id} lost opener protection",
                        )
                    # Print-entire-section stays a same-tab link.
                    if by_id["print_section"]["available"]:
                        require(
                            attribute(html, "print_section", "href")
                            == by_id["print_section"]["url"],
                            f"{deployment}/{lang} print_section link diverges from descriptor",
                        )

                    reference = (
                        output / lang / "docs" / "reference" / "index.html"
                    ).read_text(encoding="utf-8")
                    reference_actions = map_by_id(manifest_from(reference)["actions"])
                    require(
                        reference_actions["copy_markdown"]["available"] is False
                        and reference_actions["view_markdown"]["available"] is False,
                        f"{deployment}/{lang} page without Markdown advertises Markdown actions",
                    )
                    # Without a Markdown output the primary half is dropped and
                    # the caret degrades to a labeled dropdown-only button.
                    require(
                        reference.count('data-td-action="copy_markdown"') == 0,
                        f"{deployment}/{lang} page without Markdown renders a copy control",
                    )
                    require(
                        "data-td-page-actions-toggle" in reference,
                        f"{deployment}/{lang} page without Markdown lost the actions menu",
                    )

                bundles = sorted(list((output / "js").glob("actions*.js")) + list((output / "js").glob("core*.js")) + list((output / "js").glob("page-*.js")))
                require(bundles, f"{deployment} emitted no theme bundle")
                require(
                    any("OinkActionRegistry" in bundle.read_text(encoding="utf-8") for bundle in bundles),
                    f"{deployment} omitted the registry runtime",
                )
                require(
                    any("data-td-action" in bundle.read_text(encoding="utf-8") for bundle in bundles),
                    f"{deployment} omitted the page-action controller",
                )

                print_html = (output / "en" / "_print" / "docs" / "index.html").read_text(
                    encoding="utf-8"
                )
                print_manifest = manifest_from(print_html)
                require(
                    map_by_id(print_manifest["actions"])["print"]["available"] is True,
                    f"{deployment} print output omitted executable print data",
                )
                require(
                    print_html.count('data-td-action="print"') >= 1,
                    f"{deployment} print output lost its print control",
                )

            output, _ = build(
                helper,
                workspace,
                "search-off",
                action_config(helper, True, offline_search=False),
            )
            html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(encoding="utf-8")
            require("td-action-manifest" in html, "search-off page omitted action data")
            require('id="td-shell-search"' not in html, "search-off page gained Palette markup")
            search_off_bundles = [
                bundle.read_text(encoding="utf-8")
                for bundle in sorted(list((output / "js").glob("actions*.js")) + list((output / "js").glob("core*.js")) + list((output / "js").glob("page-*.js")))
            ]
            require(
                any("OinkActionRegistry" in source for source in search_off_bundles),
                "search-off page omitted the action registry runtime",
            )
            require(
                any("data-td-action" in source for source in search_off_bundles),
                "search-off page omitted the page-action controller",
            )

            assistant_off_config = action_config(helper, True).replace(
                "      assistant_links: true\n",
                "      assistant_links: false\n",
            )
            output, _ = build(
                helper,
                workspace,
                "assistant-off",
                assistant_off_config,
            )
            validate_assistant_off(output, "site assistant opt-out")

            output, _ = build(
                helper,
                workspace,
                "assistant-page-cannot-opt-in",
                assistant_off_config,
                "page_context_menu:\n  assistant_links: true",
            )
            validate_assistant_off(
                output,
                "page assistant override without site opt-in",
            )

            output, _ = build(
                helper,
                workspace,
                "assistant-page-opt-out",
                action_config(helper, True),
                "page_context_menu:\n  assistant_links: false",
            )
            validate_assistant_off(output, "page assistant opt-out")

            invalid_cases = {
                "unknown": (
                    "            - id: bad\n              action: not_real\n",
                    'references unsupported action "not_real"',
                ),
                "both": (
                    "            - id: bad\n              action: print\n              url: /bad/\n",
                    "must define exactly one of url or action",
                ),
                "callback": (
                    "            - id: bad\n              url: /bad/\n              callback: alert\n",
                    'uses unsupported key "callback"',
                ),
                "javascript": (
                    "            - id: bad\n              url: 'javascript:alert(1)'\n",
                    "uses unsafe URL",
                ),
                "data": (
                    "            - id: bad\n              url: 'data:text/html,boom'\n",
                    "uses unsafe URL",
                ),
                "protocol-relative": (
                    "            - id: bad\n              url: //evil.example/x\n",
                    "uses unsafe URL",
                ),
                "duplicate": (
                    "            - id: bad\n              url: /one/\n"
                    "            - id: bad\n              url: /two/\n",
                    'duplicate command id "bad"',
                ),
                "reserved": (
                    "            - id: print\n              url: /bad/\n",
                    'is reserved by a built-in action',
                ),
                "numeric-title": (
                    "            - id: bad\n              title: 42\n              url: /bad/\n",
                    'field "title" must be a string',
                ),
                "map-icon": (
                    "            - id: bad\n              icon: {class: bad}\n              url: /bad/\n",
                    'field "icon" must be a string',
                ),
                "scalar-keywords": (
                    "            - id: bad\n              keywords: bad\n              url: /bad/\n",
                    'field "keywords" must be an array of strings',
                ),
                "mixed-keywords": (
                    "            - id: bad\n              keywords: [good, 42]\n              url: /bad/\n",
                    'field "keywords" must be an array of strings',
                ),
            }
            for name, (yaml, expected) in invalid_cases.items():
                run_invalid_build(helper, workspace, name, yaml, expected)

        for script in (
            "action-registry.test.js",
            "page-actions.test.js",
            "dark-mode.test.js",
        ):
            behavior = subprocess.run(
                ["node", str(ROOT / "tests" / "js" / script)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            require(
                behavior.returncode == 0,
                f"{script} failed:\n" + (behavior.stdout + behavior.stderr).strip(),
            )

        docs_shell = (ROOT / "assets" / "js" / "docs-shell.js").read_text(encoding="utf-8")
        dark_mode = (ROOT / "assets" / "js" / "dark-mode.js").read_text(encoding="utf-8")
        require("fetchMarkdown" not in docs_shell, "Markdown executor remains duplicated in docs-shell")
        require(
            "registerExecutor('switch_theme'" in dark_mode
            and "apply(button.getAttribute('data-bs-theme-value'))" in dark_mode,
            "theme controls and registry do not share the same apply executor",
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"action registry check failed: {exc}", file=sys.stderr)
        return 1

    print("action registry and command manifest checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
