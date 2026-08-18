#!/usr/bin/env python3
"""Validate navigation contracts and characterize the current theme.

The script builds an isolated bilingual fixture with local search disabled and
enabled. It compares normalized navigation and runtime observations with a
checked-in snapshot. Use --write-current only when an intentional behavior
change is reviewed together with its owning issue.
"""

from __future__ import annotations

import argparse
import gzip
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


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "navigation"
CONTRACT_PATH = FIXTURE_ROOT / "contract.json"
CURRENT_PATH = FIXTURE_ROOT / "current.json"
SITE_FIXTURE_PATH = FIXTURE_ROOT / "site"

LANGUAGES = ("en", "zh")
VARIANTS = ("flat", "nested", "deep")
SURFACES = {
    "home": "{lang}/index.html",
    "docs": "{lang}/docs/guides/tutorial/index.html",
    "blog": "{lang}/blog/index.html",
    "plain": "{lang}/project/index.html",
    "print": "{lang}/_print/docs/index.html",
}

class ContractError(RuntimeError):
    """A deterministic contract or characterization failure."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-current",
        action="store_true",
        help="replace the checked-in current characterization snapshot",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"missing required file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(
            f"invalid JSON in {path.relative_to(ROOT)}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("version") == 1, "contract.version must be 1")

    authorities = contract.get("authorities", {})
    require(
        authorities
        == {
            "global_navigation": "hugo_menu",
            "sidebar": "hugo_content_tree",
            "root_switcher": "existing_root_switcher",
            "discovery_and_commands": "local_search_index",
        },
        "authority boundaries changed; update the contract in the same change",
    )

    navigation = contract.get("navigation", {})
    require(
        navigation.get("interactive_child_levels") == 1,
        "navigation supports exactly one interactive child level",
    )
    require(
        navigation.get("desktop_control") == "link_with_hover_panel"
        and "mobile_control" not in navigation,
        "parents open on hover/focus with a navigating link at every width; "
        "there is no separate mobile menu",
    )
    require(
        navigation.get("hover_required") is False,
        "reaching child pages must not require hover: the parent link navigates "
        "to the section landing and keyboard focus opens the panel",
    )
    require(
        "mobile_single_open" not in navigation,
        "the mobile accordion was retired with the two-state navbar",
    )
    require(
        navigation.get("external_rel") == ["noopener", "noreferrer"],
        "external-link rel contract changed",
    )
    deep_menu = navigation.get("deep_menu", {})
    require(
        deep_menu.get("warning") is True
        and deep_menu.get("rendering") == "flatten_under_group_heading"
        and deep_menu.get("third_level_flyout") is False,
        "deep menus must warn and degrade without a third-level flyout",
    )

    sidebar = contract.get("sidebar_icons", {})
    require(
        sidebar.get("parameter") == "params.ui.sidebar_icon_policy"
        and
        sidebar.get("values") == ["all", "groups", "none"],
        "sidebar icon policy values must be all, groups, none",
    )
    require(
        sidebar.get("compatibility_default") == "all"
        and sidebar.get("compatibility_default_change_earliest") == "1.0"
        and sidebar.get("starter_default") == "all",
        "sidebar compatibility and starter defaults must keep leaf icons visible",
    )

    search = contract.get("search", {})
    require(
        search.get("canonical_front_matter")
        == ["search_keywords", "search_boost", "search_exclude"],
        "canonical search front matter changed",
    )
    require(
        search.get("exclude_aliases") == []
        and search.get("removed_exclude_aliases") == ["exclude_search", "excludeSearch"],
        "search_exclude is the only exclusion flag; the 0.x aliases were removed in 1.0",
    )
    require(
        search.get("exclude_alias_status") == "removed_in_1.0_build_fails_with_replacement",
        "removed exclude aliases must fail the build with their replacement",
    )
    require(
        search.get("exclude_resolution") == "search_exclude_only",
        "search exclusion reads search_exclude only",
    )
    require(
        search.get("default_boost") == 1.0
        and search.get("invalid_boost") == "warn_and_use_default"
        and search.get("score_formula") == "text_score_times_search_boost",
        "search boost contract changed",
    )
    require(
        search.get("keywords_in_latin") is True
        and search.get("keywords_in_cjk") is True
        and search.get("language_separated_indexes") is True,
        "keyword or language-separated search contract changed",
    )
    size_budget = search.get("size_budget", {})
    require(
        isinstance(size_budget.get("uncompressed_bytes"), int)
        and size_budget["uncompressed_bytes"] == 2_097_152
        and isinstance(size_budget.get("gzip_bytes"), int)
        and size_budget["gzip_bytes"] == 524_288,
        "search index byte budgets changed",
    )
    require(
        search.get("index_fields")
        == [
            "ref",
            "title",
            "categories",
            "tags",
            "excerpt",
            "headings",
            "description",
            "body",
            "root",
            "section",
            "type",
            "keywords",
            "boost",
            "breadcrumb",
            "icon",
        ],
        "search index field contract changed",
    )

    commands = contract.get("commands", {})
    require(
        set(commands.get("site_command_kinds", []))
        == {"url", "builtin_action_id"},
        "configured commands may only use URLs or built-in action IDs",
    )
    require(
        commands.get("javascript_callbacks_allowed") is False,
        "configured JavaScript callbacks must remain forbidden",
    )
    require(
        commands.get("builtin_action_ids")
        == [
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
            "print",
            "switch_theme",
            "switch_language",
            "switch_version",
            "open_github",
        ],
        "built-in action ID contract changed",
    )
    require(
        commands.get("localized_parameter")
        == "languages.<lang>.params.ui.command_palette.commands",
        "localized command parameter contract changed",
    )

    palette = contract.get("palette", {})
    require(
        palette.get("dialog_owner") == "existing_local_search_dialog",
        "the Palette must extend the existing local-search dialog",
    )
    require(
        palette.get("modes") == ["empty", "text", "commands"]
        and palette.get("command_prefix") == ">",
        "Palette mode contract changed",
    )
    require(
        palette.get("first_version_scopes") == [],
        "first-version Palette scopes must remain empty",
    )
    require(
        palette.get("default_telemetry") is False,
        "default telemetry must remain disabled",
    )

    runtime = contract.get("runtime", {})
    expected_omissions = {"dialog", "local_index", "lunr", "palette_controller"}
    require(
        runtime.get("enabled_when")
        == ["params.offline_search", "home_or_shell_surface", "not_print"],
        "runtime capability predicate contract changed",
    )
    require(
        set(runtime.get("disabled_must_omit", [])) == expected_omissions,
        "disabled runtime omission contract changed",
    )
    require(
        set(runtime.get("print_must_omit", [])) == expected_omissions,
        "print runtime omission contract changed",
    )
    matrix = contract.get("characterization_matrix", {})
    require(
        matrix.get("menu_variants") == ["flat", "nested", "deep"]
        and matrix.get("search_states") == ["disabled", "enabled"]
        and matrix.get("languages") == ["en", "zh"]
        and matrix.get("deployments") == ["root", "subpath"]
        and matrix.get("surfaces") == list(SURFACES),
        "the required characterization matrix changed",
    )
    require(
        contract.get("non_goals")
        == [
            "ai_or_semantic_search",
            "remote_search_replacement",
            "recent_history",
            "personalized_recommendations",
            "arbitrary_depth_flyouts",
            "second_navigation_authority",
            "default_query_upload",
        ],
        "navigation non-goals changed",
    )


def config_text(
    variant: str, offline_search: bool, subpath: bool = True
) -> str:
    if variant not in VARIANTS:
        raise ContractError(f"unknown fixture variant: {variant}")

    lines = [
        (
            "baseURL: https://example.org/preview/"
            if subpath
            else "baseURL: https://example.org/"
        ),
        "title: Contract Fixture",
        f"theme: {ROOT.name}",
        "defaultContentLanguage: en",
        "defaultContentLanguageInSubdir: true",
        "disableKinds: [RSS, sitemap, taxonomy, term]",
        "params:",
        f"  offline_search: {'true' if offline_search else 'false'}",
        "  github_project_repo: https://github.com/pgsty/oink",
        "  ui:",
        "    shell_types: [docs, blog, swagger]",
        "    docs_section: docs",
        "    blog_section: blog",
        "    feedback:",
        "      enable: false",
        "languages:",
        "  en:",
        "    label: English",
        "    locale: en-US",
        "    weight: 1",
        "  zh:",
        "    label: 简体中文",
        "    locale: zh-CN",
        "    weight: 2",
        "menus:",
        "  main:",
        "    - identifier: docs",
        "      name: Docs",
        "      pageRef: /docs",
        "      weight: 10",
    ]
    if variant == "flat":
        lines.extend(
            [
                "    - identifier: blog",
                "      name: Blog",
                "      pageRef: /blog",
                "      weight: 20",
                "    - identifier: project",
                "      name: Project",
                "      pageRef: /project",
                "      weight: 30",
                "    - identifier: status",
                "      name: Status",
                "      url: https://status.example.com/",
                "      weight: 40",
                "      params:",
                "        icon: fa-solid fa-signal",
            ]
        )
    else:
        lines.extend(
            [
                "    - identifier: guides",
                "      parent: docs",
                "      name: Guides",
                "      pageRef: /docs/guides",
                "      weight: 10",
                "      params:",
                "        icon: fa-solid fa-route",
                "        description: Task-oriented tutorials",
                "    - identifier: tutorial",
                "      parent: docs",
                "      name: First Tutorial",
                "      pageRef: /docs/guides/tutorial",
                "      weight: 15",
                "    - identifier: reference",
                "      parent: docs",
                "      name: Reference",
                "      pageRef: /docs/reference",
                "      weight: 20",
                "    - identifier: blog",
                "      name: Blog",
                "      pageRef: /blog",
                "      weight: 20",
                "    - identifier: project",
                "      name: Project",
                "      pageRef: /project",
                "      weight: 30",
                "    - identifier: status",
                "      name: Status",
                "      url: https://status.example.com/",
                "      weight: 40",
                "      params:",
                "        icon: fa-solid fa-signal",
            ]
        )
        if variant == "deep":
            lines.extend(
                [
                    "    - identifier: advanced",
                    "      parent: tutorial",
                    "      name: Advanced Topic",
                    "      pageRef: /docs/guides/advanced",
                    "      weight: 10",
                ]
            )
    return "\n".join(lines) + "\n"


def copy_fixture_site(
    target: Path, variant: str, offline_search: bool, subpath: bool = True
) -> None:
    shutil.copytree(SITE_FIXTURE_PATH, target)
    (target / "hugo.yaml").write_text(
        config_text(variant, offline_search, subpath), encoding="utf-8"
    )


def run_hugo(site: Path, output: Path, cache: Path) -> str:
    command = [
        "hugo",
        "--source",
        str(site),
        "--themesDir",
        str(ROOT.parent),
        "--destination",
        str(output),
        "--cacheDir",
        str(cache),
        "--cleanDestinationDir",
        "--printPathWarnings",
    ]
    environment = dict(os.environ)
    environment["HUGO_ENVIRONMENT"] = "development"
    result = subprocess.run(
        command,
        cwd=site,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        raise ContractError(
            f"Hugo fixture build failed ({site.name}):\n{result.stdout.rstrip()}"
        )
    return result.stdout


def read_output(output: Path, pattern: str, lang: str) -> str:
    path = output / pattern.format(lang=lang)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContractError(
            f"fixture output is missing {path.relative_to(output)}"
        ) from exc


class NavigationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, Any]] = []
        self.controls: list[dict[str, str]] = []
        self.panels: list[str] = []
        self._current: dict[str, Any] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "a" and "data-td-navbar-region" in attributes:
            self._current = {"attrs": attributes, "text": []}
        elif tag == "button" and (
            "data-td-navbar-toggle" in attributes
            or "data-td-navbar-accordion-toggle" in attributes
        ):
            self.controls.append(attributes)
        elif (
            "data-td-navbar-panel" in attributes
            or "data-td-navbar-accordion-panel" in attributes
        ) and attributes.get("id"):
            self.panels.append(attributes["id"])

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current is not None:
            self.links.append(self._current)
            self._current = None


def normalize_navigation(html: str) -> dict[str, Any]:
    parser = NavigationParser()
    parser.feed(html)
    ignored = {
        "GitHub",
        "Language",
        "语言",
        "语言切换",
        "Theme",
        "主题",
        "Search",
        "搜索",
    }
    normalized: dict[str, Any] = {
        "desktop": [],
        "mobile": [],
        "controls": [],
        "panels": sorted(parser.panels),
    }
    for parsed in parser.links:
        attrs = parsed["attrs"]
        classes = set(attrs.get("class", "").split())
        region = attrs["data-td-navbar-region"]
        text = attrs.get("data-td-navbar-label") or " ".join(parsed["text"])
        text = " ".join(text.split())
        if text in ignored:
            continue
        normalized[region].append(
            {
                "href": attrs.get("href", ""),
                "active": "active" in classes,
                "current": attrs.get("aria-current", ""),
                "external": attrs.get("data-td-navbar-external") == "true",
                "kind": attrs.get("data-td-navbar-kind", ""),
                "level": int(attrs.get("data-td-navbar-level", "0")),
                "target": attrs.get("target", ""),
                "rel": sorted(attrs.get("rel", "").split()),
                "text": text,
                **(
                    {
                        "controls": attrs["aria-controls"],
                        "expanded": attrs.get("aria-expanded", ""),
                    }
                    if attrs.get("aria-controls")
                    else {}
                ),
            }
        )
    for attrs in parser.controls:
        normalized["controls"].append(
            {
                "controls": attrs.get("aria-controls", ""),
                "expanded": attrs.get("aria-expanded", ""),
                "mode": (
                    "desktop"
                    if "data-td-navbar-toggle" in attrs
                    else "mobile"
                ),
            }
        )
    normalized["controls"].sort(key=lambda item: (item["mode"], item["controls"]))
    return normalized


class RootMenuParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current = ""
        self._inside_current = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "span" and "td-shell-root__title" in attributes.get(
            "class", ""
        ).split():
            self._inside_current = True

    def handle_data(self, data: str) -> None:
        if self._inside_current:
            self.current += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._inside_current:
            self._inside_current = False


def current_root(html: str) -> str:
    parser = RootMenuParser()
    parser.feed(html)
    return " ".join(parser.current.split())


def runtime_markers(html: str, palette_controller_in_bundle: bool) -> dict[str, bool]:
    script_sources = re.findall(r'<script\b[^>]*\bsrc="([^"]+)"', html)
    return {
        "dialog": 'id="td-shell-search"' in html,
        "opener": "data-td-shell-search-open" in html,
        "lunr": any("lunr" in source for source in script_sources),
        "index_reference": "data-td-index-src=" in html,
        "palette_controller": palette_controller_in_bundle,
    }


def index_sizes(output: Path, lang: str) -> dict[str, int]:
    candidates = sorted(output.glob(f"offline-search-index.{lang}*.json"))
    if not candidates:
        return {"uncompressed_bytes": 0, "gzip_bytes": 0}
    payload = candidates[0].read_bytes()
    return {
        "uncompressed_bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, mtime=0)),
    }


def observe_variant(
    workspace: Path,
    variant: str,
    offline_search: bool,
    subpath: bool = True,
) -> tuple[dict[str, Any], str]:
    deployment = "subpath" if subpath else "root"
    site = workspace / (
        f"{variant}-{'on' if offline_search else 'off'}-{deployment}"
    )
    output = workspace / (
        f"public-{variant}-{'on' if offline_search else 'off'}-{deployment}"
    )
    cache = workspace / "cache"
    copy_fixture_site(site, variant, offline_search, subpath)
    log = run_hugo(site, output, cache)
    main_bundles = sorted(list((output / "js").glob("actions*.js")) + list((output / "js").glob("core*.js")) + list((output / "js").glob("page-*.js")))
    palette_bundles = {
        str(bundle.relative_to(output))
        for bundle in main_bundles
        if "td-shell-search" in bundle.read_text(encoding="utf-8")
    }

    observation: dict[str, Any] = {
        "navigation": {},
        "runtime": {},
        "indexes": {},
        "index_sizes": {},
    }
    for lang in LANGUAGES:
        navbar_html = read_output(output, SURFACES["plain"], lang)
        observation["navigation"][lang] = normalize_navigation(navbar_html)
        docs_html = read_output(
            output, "{lang}/docs/guides/nav-active/index.html", lang
        )
        observation["navigation"][lang]["docs_active"] = normalize_navigation(
            docs_html
        )
        docs_root_html = read_output(output, SURFACES["docs"], lang)
        product_root_html = read_output(
            output, "{lang}/product/index.html", lang
        )
        observation["navigation"][lang]["current_roots"] = {
            "docs": current_root(docs_root_html),
            "product": current_root(product_root_html),
        }
        observation["runtime"][lang] = {}
        observation["indexes"][lang] = any(
            output.glob(f"offline-search-index.{lang}*.json")
        )
        observation["index_sizes"][lang] = index_sizes(output, lang)
        for surface, pattern in SURFACES.items():
            html = read_output(output, pattern, lang)
            script_sources = re.findall(r'<script\b[^>]*\bsrc="([^"]+)"', html)
            palette_controller_in_bundle = any(
                any(source.endswith(bundle) for bundle in palette_bundles)
                for source in script_sources
            )
            observation["runtime"][lang][surface] = runtime_markers(
                html, palette_controller_in_bundle
            )
    return observation, log


def build_observation() -> dict[str, Any]:
    result: dict[str, Any] = {
        "version": 1,
        "deployments": {},
        "index_sizes": {},
    }
    with tempfile.TemporaryDirectory(prefix="td-landing-navigation-") as temp_dir:
        workspace = Path(temp_dir)
        for deployment, subpath in (("root", False), ("subpath", True)):
            result["deployments"][deployment] = {}
            for variant in VARIANTS:
                result["deployments"][deployment][variant] = {}
                for offline_search in (False, True):
                    state = "search_on" if offline_search else "search_off"
                    observation, log = observe_variant(
                        workspace, variant, offline_search, subpath=subpath
                    )
                    warnings = [line for line in log.splitlines() if "WARN" in line]
                    expected_warning_fragments = ["invalid search_boost"] if offline_search else []
                    if variant == "deep":
                        expected_warning_fragments.append(
                            "only one interactive child level is supported"
                        )
                    if expected_warning_fragments:
                        require(
                            warnings
                            and all(
                                any(
                                    fragment in warning
                                    for fragment in expected_warning_fragments
                                )
                                for warning in warnings
                            )
                            and all(
                                any(fragment in warning for warning in warnings)
                                for fragment in expected_warning_fragments
                            ),
                            f"current {deployment}/{variant}/{state} fixture "
                            f"did not emit exactly the expected navigation warning kinds:\n{log}",
                        )
                    else:
                        require(
                            not warnings,
                            f"current {deployment}/{variant}/{state} fixture "
                            f"emitted an unexpected warning:\n{log}",
                        )
                    result["deployments"][deployment][variant][state] = {
                        "navigation": observation["navigation"],
                        "runtime": observation["runtime"],
                        "indexes": observation["indexes"],
                    }
                    if (
                        deployment == "subpath"
                        and variant == "flat"
                        and offline_search
                    ):
                        result["index_sizes"] = observation["index_sizes"]
    return result


def validate_observation(
    observation: dict[str, Any], contract: dict[str, Any]
) -> None:
    deployments = observation["deployments"]
    flat_legacy = [
        {
            "text": "Docs",
            "href_suffix": "/docs/",
            "active": False,
            "target": "",
            "rel": [],
        },
        {
            "text": "Blog",
            "href_suffix": "/blog/",
            "active": False,
            "target": "",
            "rel": [],
        },
        {
            "text": "Project",
            "href_suffix": "/project/",
            "active": True,
            "target": "",
            "rel": [],
        },
        {
            "text": "Status",
            "href_suffix": "https://status.example.com/",
            "active": False,
            "target": "_blank",
            "rel": ["noopener", "noreferrer"],
        },
    ]
    for deployment in ("root", "subpath"):
        for variant in VARIANTS:
            for state in ("search_off", "search_on"):
                build = deployments[deployment][variant][state]
                for lang in LANGUAGES:
                    expected_text = {
                        "flat": ["Docs", "Blog", "Project", "Status"],
                        "nested": [
                            "Docs",
                            "Guides",
                            "First Tutorial",
                            "Reference",
                            "Blog",
                            "Project",
                            "Status",
                        ],
                        "deep": [
                            "Docs",
                            "Guides",
                            "First Tutorial",
                            "Advanced Topic",
                            "Reference",
                            "Blog",
                            "Project",
                            "Status",
                        ],
                    }[variant]
                    expected_levels = {
                        "flat": [0, 0, 0, 0],
                        "nested": [0, 1, 1, 1, 0, 0, 0],
                        "deep": [0, 1, 1, 2, 1, 0, 0, 0],
                    }[variant]
                    navigation = build["navigation"][lang]
                    require(
                        navigation["mobile"] == []
                        and navigation["docs_active"]["mobile"] == [],
                        f"{deployment}/{variant}/{state}/{lang} the retired "
                        "mobile menu reappeared",
                    )
                    for region in ("desktop",):
                        links = navigation[region]
                        require(
                            [link["text"] for link in links] == expected_text
                            and [link["level"] for link in links]
                            == expected_levels,
                            f"{deployment}/{variant}/{state}/{lang}/{region} "
                            "navigation hierarchy changed",
                        )
                        prefix = (
                            f"/preview/{lang}/"
                            if deployment == "subpath"
                            else f"/{lang}/"
                        )
                        require(
                            all(
                                link["href"].startswith(prefix)
                                for link in links[:-1]
                            ),
                            f"{deployment}/{variant}/{state}/{lang}/{region} "
                            "internal menu prefix changed",
                        )
                        external = links[-1]
                        require(
                            external["href"] == "https://status.example.com/"
                            and external["external"] is True
                            and external["target"] == "_blank"
                            and external["rel"] == ["noopener", "noreferrer"],
                            f"{deployment}/{variant}/{state}/{lang}/{region} "
                            "external-link safety changed",
                        )
                        project = next(
                            link for link in links if link["text"] == "Project"
                        )
                        require(
                            project["active"] is True
                            and project["current"] == "page",
                            f"{deployment}/{variant}/{state}/{lang}/{region} "
                            "current top-level item state changed",
                        )
                        if variant == "flat":
                            legacy_projection = [
                                {
                                    "text": link["text"],
                                    "href_suffix": (
                                        link["href"]
                                        if link["external"]
                                        else "/" + "/".join(
                                            link["href"].strip("/").split("/")[-1:]
                                        ) + "/"
                                    ),
                                    "active": link["active"],
                                    "target": link["target"],
                                    "rel": link["rel"],
                                }
                                for link in links
                            ]
                            require(
                                legacy_projection == flat_legacy,
                                f"{deployment}/{state}/{lang}/{region} flat "
                                "legacy link projection changed",
                            )
                        docs_parent = navigation["docs_active"][region][0]
                        require(
                            docs_parent["text"] == "Docs"
                            and docs_parent["active"] is True,
                            f"{deployment}/{variant}/{state}/{lang}/{region} "
                            "parent does not reflect its active descendant",
                        )
                    controls = navigation["controls"]
                    panels = navigation["panels"]
                    # Hover panels have no disclosure buttons. Their parent
                    # link owns the rendered accessibility relationship.
                    expected_panel_count = 0 if variant == "flat" else 1
                    require(
                        len(controls) == 0
                        and len(panels) == expected_panel_count
                        and len(panels) == len(set(panels)),
                        f"{deployment}/{variant}/{state}/{lang} disclosure "
                        "ARIA relationship changed",
                    )
                    parent_disclosures = [
                        link
                        for link in navigation["desktop"]
                        if link.get("controls")
                    ]
                    require(
                        len(parent_disclosures) == expected_panel_count
                        and all(
                            link["controls"] in panels
                            and link["expanded"] == "false"
                            for link in parent_disclosures
                        ),
                        f"{deployment}/{variant}/{state}/{lang} parent link "
                        "does not own its panel accessibility state",
                    )
                    require(
                        navigation["current_roots"]
                        == {
                            "docs": "文档" if lang == "zh" else "Docs",
                            "product": "Product",
                        },
                        f"{deployment}/{variant}/{state}/{lang} root switcher "
                        "confused product roots sharing one layout type",
                    )
                    if variant == "deep":
                        for region in ("desktop",):
                            links = navigation[region]
                            group = next(
                                link
                                for link in links
                                if link["text"] == "First Tutorial"
                            )
                            advanced = next(
                                link
                                for link in links
                                if link["text"] == "Advanced Topic"
                            )
                            require(
                                group["kind"] == "group"
                                and advanced["kind"] == "link"
                                and advanced["level"] == 2,
                                f"{deployment}/{state}/{lang}/{region} deep "
                                "menu did not flatten under a group heading",
                            )
                    require(
                        build["indexes"][lang] is (state == "search_on"),
                        f"{deployment}/{variant}/{state}/{lang} index emission changed",
                    )
                    for surface in SURFACES:
                        runtime = build["runtime"][lang][surface]
                        if state == "search_off":
                            require(
                                not runtime["dialog"]
                                and not runtime["opener"]
                                and not runtime["lunr"]
                                and not runtime["index_reference"]
                                and not runtime["palette_controller"],
                                f"{deployment}/{variant}/{lang}/{surface} emits "
                                "search runtime while disabled",
                            )
                        elif surface in ("home", "docs", "blog"):
                            require(
                                runtime["dialog"]
                                and runtime["opener"]
                                and runtime["lunr"]
                                and runtime["index_reference"],
                                f"{deployment}/{variant}/{lang}/{surface} "
                                "search-enabled characterization changed",
                            )
                            require(
                                runtime["palette_controller"] is True,
                                f"{deployment}/{variant}/{lang}/{surface} "
                                "Palette controller is missing",
                            )
                        else:
                            require(
                                not runtime["dialog"]
                                and not runtime["opener"]
                                and not runtime["lunr"]
                                and not runtime["index_reference"]
                                and not runtime["palette_controller"],
                                f"{deployment}/{variant}/{lang}/{surface} "
                                "emits Palette runtime outside its capability",
                            )

        flat_off = deployments[deployment]["flat"]["search_off"]["navigation"]
        flat_on = deployments[deployment]["flat"]["search_on"]["navigation"]
        require(
            flat_off == flat_on,
            f"{deployment} flat navigation changed with search capability",
        )

    for lang in LANGUAGES:
        sizes = observation["index_sizes"][lang]
        budget = contract["search"]["size_budget"]
        require(
            sizes["uncompressed_bytes"] <= budget["uncompressed_bytes"],
            f"{lang} local index exceeds the uncompressed byte budget",
        )
        require(
            sizes["gzip_bytes"] <= budget["gzip_bytes"],
            f"{lang} local index exceeds the gzip byte budget",
        )


def validate_runtime_source_contract() -> None:
    head = (ROOT / "layouts" / "_partials" / "head.html").read_text(
        encoding="utf-8"
    )
    scripts = (ROOT / "layouts" / "_partials" / "scripts.html").read_text(
        encoding="utf-8"
    )
    require(
        'resources.Get "js/third_party/lunr.min.js"' in head,
        "Lunr source marker changed",
    )
    require(
        'resources.Get "js/command-palette.js"' in scripts,
        "Palette controller source marker changed",
    )
    require(
        'resources.Get "js/search-engine.js"' in scripts,
        "search engine source marker changed",
    )
    require(
        'resources.Get "js/offline-search.js"' not in scripts,
        "legacy offline-search engine leaked into the shared bundle",
    )
    require(
        'resources.Get "js/surface-coordinator.js"' in scripts,
        "transient-surface coordinator source marker changed",
    )
    docs_shell = (ROOT / "assets" / "js" / "docs-shell.js").read_text(
        encoding="utf-8"
    )
    require(
        "function initSearch()" not in docs_shell
        and "td-shell-search" not in docs_shell,
        "Palette behavior leaked back into docs-shell.js",
    )
    coordinator = (ROOT / "assets" / "js" / "surface-coordinator.js").read_text(
        encoding="utf-8"
    )
    require(
        "OinkSurfaceCoordinator" in coordinator
        and "closeOthers" in coordinator
        and "register" in coordinator,
        "transient-surface coordinator contract changed",
    )


def format_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def compact_snapshot(observation: dict[str, Any]) -> dict[str, Any]:
    profiles: list[dict[str, Any]] = []
    assignments: dict[str, str] = {}
    for deployment, variants in observation["deployments"].items():
        for variant, states in variants.items():
            for state, build in states.items():
                runtime_patterns: dict[str, list[str]] = {}
                for surface, markers in build["runtime"][LANGUAGES[0]].items():
                    require(
                        all(
                            build["runtime"][lang][surface] == markers
                            for lang in LANGUAGES[1:]
                        ),
                        f"{deployment}/{variant}/{state}/{surface} runtime "
                        "markers differ by language",
                    )
                    key = json.dumps(markers, sort_keys=True)
                    runtime_patterns.setdefault(key, []).append(surface)
                navigation = build["navigation"][LANGUAGES[0]]
                for lang in LANGUAGES[1:]:
                    normalized = json.loads(format_json(build["navigation"][lang]))
                    if "current_roots" in normalized:
                        normalized["current_roots"] = navigation["current_roots"]
                    navigation_regions = [normalized]
                    if "docs_active" in normalized:
                        navigation_regions.append(normalized["docs_active"])
                    for navigation_region in navigation_regions:
                        for region in ("desktop", "mobile"):
                            for link in navigation_region[region]:
                                link["href"] = link["href"].replace(
                                    f"/{lang}/", f"/{LANGUAGES[0]}/"
                                )
                    require(
                        normalized == navigation,
                        f"{deployment}/{variant}/{state} navigation differs "
                        "beyond the expected language prefix",
                    )
                profile = {
                    "navigation_en": navigation,
                    "indexes": sorted(
                        lang for lang, present in build["indexes"].items() if present
                    ),
                    "runtime_patterns": runtime_patterns,
                }
                profile_text = json.dumps(profile, ensure_ascii=False, sort_keys=True)
                profile_id = ""
                for index, existing in enumerate(profiles, start=1):
                    if (
                        json.dumps(existing, ensure_ascii=False, sort_keys=True)
                        == profile_text
                    ):
                        profile_id = f"profile_{index}"
                        break
                if not profile_id:
                    profiles.append(profile)
                    profile_id = f"profile_{len(profiles)}"
                assignments[f"{deployment}/{variant}/{state}"] = profile_id
    return {
        "version": observation["version"],
        "profiles": {
            f"profile_{index}": profile
            for index, profile in enumerate(profiles, start=1)
        },
        "matrix": assignments,
    }


def compare_or_write(observation: dict[str, Any], write_current: bool) -> None:
    snapshot = compact_snapshot(observation)
    rendered = format_json(snapshot)
    if write_current:
        CURRENT_PATH.write_text(rendered, encoding="utf-8")
        print(f"updated {CURRENT_PATH.relative_to(ROOT)}")
        return

    current = load_json(CURRENT_PATH)
    if current != snapshot:
        raise ContractError(
            "navigation characterization changed.\n"
            "Review the rendered behavior, then run the check with "
            "--write-current only with the owning navigation implementation issue.\n\n"
            f"Observed:\n{rendered}"
        )


def main() -> int:
    args = parse_args()
    try:
        contract = load_json(CONTRACT_PATH)
        validate_contract(contract)
        validate_runtime_source_contract()
        observation = build_observation()
        validate_observation(observation, contract)
        compare_or_write(observation, args.write_current)
    except ContractError as exc:
        print(f"navigation contract check failed: {exc}", file=sys.stderr)
        return 1
    print("navigation contract and characterization checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
