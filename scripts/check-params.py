#!/usr/bin/env python3
"""Enforce the configuration parameter contract.

Three rules shape every theme parameter (see CHANGELOG, 1.0):

1. A boolean switch is the bare feature name (`ui.annotation: true`), never a
   `*.enable` member or an `*_enabled` suffix. The only `_enabled` keys left
   are the ones whose bare name would collide with sibling keys.
2. A single-key map is flattened to a scalar. A map survives only for a
   feature that carries several settings, and that map also accepts a bare
   boolean.
3. A front matter key is the site key with its `ui.` prefix dropped.

Keys the theme invents are snake_case; camelCase survives only where a value
is passed straight through to an external runtime (giscus, mermaid) or is a
Docsy front matter key that predates OINK.

The script scans every parameter read point in ``layouts/`` and the templated
assets, checks the shapes above, checks that ``config-legacy.html`` and
``front-matter-legacy.html`` register every renamed key, and then builds a
minimal site once per legacy key to prove that the build fails and the error
names the replacement (``--source-only`` skips the builds).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CONFIG_LEGACY = ROOT / "layouts/_partials/config-legacy.html"
FRONT_MATTER_LEGACY = ROOT / "layouts/_partials/front-matter-legacy.html"

KEY_SHAPE = re.compile(r"^[a-z][a-z0-9_]*$")

# Maps that keep their nested shape because the feature has several settings.
# Everything else nested under params must be flat.
KEPT_MAPS = {
    "comments",
    "ui.feedback",
    "ui.page_context_menu",
    "ui.dark_mode",
    "ui.command_palette",
    "ui.alt_site",
    "taxonomy",
    "print",
    "search",
    "plantuml",
    "drawio",
    "mermaid",
    "copyright",
    "ui.taxonomy_icons",
}

# Values handed to an external runtime keep that runtime's key names.
PASSTHROUGH_PREFIXES = ("comments.giscus.", "mermaid.")

# The `_enabled` suffix is allowed only where the bare name is taken by a
# sibling family: navbar_* / sidebar_* / sidebar_root_*.
ENABLED_SUFFIX_ALLOWED = {
    "ui.navbar_enabled",
    "ui.sidebar_enabled",
    "ui.sidebar_root_enabled",
}

# Front matter overrides of a site key: the page key is the site key without
# its `ui.` prefix (`.Param`-style keys such as page_width and the ui-param
# helper's keys resolve the same way; the table pins the explicit resolvers).
PAGE_OVERRIDES = {
    "navbar_enabled": "ui.navbar_enabled",
    "navbar_autohide": "ui.navbar_autohide",
    "footer_style": "ui.footer_style",
    "annotation": "ui.annotation",
    "feedback": "ui.feedback",
    "image_zoom": "ui.image_zoom",
    "reading_time": "ui.reading_time",
    "page_context_menu": "ui.page_context_menu",
    "comments": "comments",
    "page_width": "page_width",
    "reading_width": "reading_width",
}

# Old page keys that must never be read again.
LEGACY_PAGE_KEYS = {
    "context_menu",
    "hide_readingtime",
    "hide_feedback",
    "exclude_search",
    "excludeSearch",
    "content_width",
    "assistant_links",
    "manualLink",
    "manualLinkTitle",
    "manualLinkTarget",
    "manualLinkRelref",
    "manuallink",
    "manuallinktitle",
    "manuallinktarget",
    "manuallinkrelref",
}

# Legacy site configuration: (YAML fragment under `params:`, expected message
# fragment naming the replacement).
LEGACY_SITE_CASES = [
    ("offlineSearch: true", "params.offline_search"),
    ("offlineSearchIndex: content", "params.offline_search_index"),
    ("offlineSearchMaxResults: 5", "params.offline_search_max_results"),
    ("offlineSearchOnServe: true", "params.offline_search_on_serve"),
    ("offlineSearchSummaryLength: 5", "params.offline_search_summary_length"),
    ("disable_click2copy_chroma: true", "params.ui.code_copy"),
    ("prism_syntax_highlighting: true", "params.prism_syntax_highlighting was removed"),
    ("content_width: norm", "params.reading_width"),
    ("rss_sections: [blog]", "params.rss_sections was removed"),
    ("algolia_docsearch: true", "params.search.algolia"),
    ("github_url: https://example.org/edit", "params.github_repo"),
    ("Taxonomy:\n  taxonomyCloud: [tags]", "params.taxonomy.cloud"),
    ("Taxonomy:\n  taxonomyCloudTitle: [Tags]", "params.taxonomy.cloud_title"),
    ("Taxonomy:\n  taxonomyPageHeader: [tags]", "params.taxonomy.page_header"),
    ("ui:\n  no_left_sidebar: true", "params.ui.sidebar_enabled"),
    ("ui:\n  breadcrumb_disable: true", "params.ui.breadcrumb"),
    ("ui:\n  breadcrumb_enabled: false", "params.ui.breadcrumb"),
    ("ui:\n  scrollSpy:\n    disable: true", "params.ui.scroll_spy"),
    ("ui:\n  scroll_spy_enabled: true", "params.ui.scroll_spy"),
    ("ui:\n  code_copy_enabled: false", "params.ui.code_copy"),
    ("ui:\n  showLightDarkModeMenu: true", "params.ui.dark_mode.show_menu"),
    ("ui:\n  readingtime:\n    enable: true", "params.ui.reading_time"),
    ("ui:\n  ul_show: 3", "params.ui.sidebar_expand_levels"),
    ("ui:\n  docs_root: home", "params.ui.docs_sidebar_root"),
    ("ui:\n  pager:\n    types: [docs]", "params.ui.pager_types"),
    ("ui:\n  annotation:\n    enable: true", "params.ui.annotation: true | false"),
    ("ui:\n  image_zoom:\n    enable: true", "params.ui.image_zoom: true | false"),
    ("ui:\n  keyboard_nav:\n    enable: true", "params.ui.keyboard_nav: true | false"),
    ("ui:\n  reading_time:\n    enable: true", "params.ui.reading_time: true | false"),
    ("ui:\n  typography:\n    preset: system", "params.ui.typography: technical | system"),
    ("markmap:\n  enable: true", "params.markmap: true | false"),
    ("print:\n  disable_toc: true", "params.print.toc"),
    ("print:\n  toc_enabled: false", "params.print.toc"),
]

# Legacy front matter: (front matter fragment, expected message fragment).
LEGACY_PAGE_CASES = [
    ("context_menu: false", "page_context_menu"),
    ("hide_readingtime: true", "reading_time: false"),
    ("hide_feedback: true", "feedback: false"),
    ("exclude_search: true", "search_exclude"),
    ("excludeSearch: true", "search_exclude"),
    ("content_width: slim", "reading_width"),
    ("annotation:\n  enable: false", "annotation: true | false"),
    ("params:\n  ui:\n    image_zoom:\n      enable: false", "image_zoom: true | false"),
    ("params:\n  ui:\n    image_zoom: false", "image_zoom: true | false"),
    ("params:\n  ui:\n    breadcrumb_disable: true", "breadcrumb: false"),
    ("params:\n  ui:\n    keyboard_nav:\n      enable: false", "keyboard_nav: true | false"),
    ("params:\n  ui:\n    reading_time: false", "reading_time: true | false"),
    ("params:\n  ui:\n    pager:\n      types: [docs]", "pager: false"),
    ("params:\n  ui:\n    section_index: cards", "section_index: <value> (the site key without ui.)"),
    ("params:\n  ui:\n    sidebar_menu_compact: false", "sidebar_menu_compact: <value> (the site key without ui.)"),
    ("params:\n  print:\n    disable_toc: true", "print.toc"),
    ("assistant_links: false", "page_context_menu: { assistant_links"),
    ("manualLink: https://example.org/", "manual_link"),
    ("manualLinkTitle: Example", "manual_link_title"),
    ("manualLinkTarget: _blank", "manual_link_target"),
    ("manualLinkRelref: /docs/", "manual_link_relref"),
    ("body_class: td-no-left-sidebar", "ui.sidebar_enabled: false"),
]

# The converged shapes must build; the bare-boolean shorthand of every kept
# on/off map is part of the contract.
ACCEPTED_SITE_CASES = [
    "ui:\n  annotation: false\n  image_zoom: true\n  keyboard_nav: false\n  reading_time: true\n  typography: system\n  pager_types: [docs]\n  breadcrumb: false\n  scroll_spy: true\n  code_copy: false\n  docs_sidebar_root: home",
    "reading_width: slim\nmarkmap: false\nplantuml: false\ndrawio: false\ncomments: false\nprint:\n  toc: false",
    "ui:\n  dark_mode: true\n  feedback: true\n  page_context_menu: false",
]
ACCEPTED_PAGE_CASES = [
    "image_zoom: true\nreading_time: false\nannotation: false\npage_context_menu: false\nreading_width: wide",
    "page_context_menu:\n  enable: true\n  assistant_links: false\nsection_index: cards\nsidebar_menu_compact: false\nkeyboard_nav: false\nbreadcrumb: false\nmanual_link: https://example.org/\nmanual_link_title: Example",
]


SITE_READ = re.compile(
    r"(?:\.Site\.Params|\bsite\.Params|\$\.Site\.Params|\$[A-Za-z]+\.Site\.Params)\.([A-Za-z_][A-Za-z0-9_.]*)"
)
PARAM_READ = re.compile(r'\.Param\s+"([^"]+)"')
UI_PARAM_READ = re.compile(r'partial "ui-param\.html" \(dict "page" [^ ]+ "key" "([a-z_]+)"')
SITE_MAP_READ = re.compile(
    r'(?:isset|index)\s+((?:\.Site\.Params|\bsite\.Params|\$[A-Za-z]+\.Site\.Params)(?:\.[A-Za-z0-9_]+)*)\s+"([^"]+)"'
)
PAGE_READ = re.compile(r"(?<![A-Za-z$.])(?:\$[A-Za-z]+|\.Page|)\.Params\.([A-Za-z_][A-Za-z0-9_.]*)")
PAGE_MAP_READ = re.compile(r'(?:isset|index)\s+((?:\$[A-Za-z]+|\.Page|)\.Params(?:\.[A-Za-z0-9_]+)*)\s+"([^"]+)"')


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def scan_read_points() -> tuple[dict[str, set[str]], dict[str, set[str]], set[str]]:
    """Return {site key: files}, {page key: files}, and the keys read through
    Hugo's `.Param` (page-then-site lookup, so the page key is the site key)."""
    site: dict[str, set[str]] = {}
    page: dict[str, set[str]] = {}
    param_reads: set[str] = set()
    files = (
        list(ROOT.glob("layouts/**/*.html"))
        + list(ROOT.glob("layouts/**/*.txt"))
        + list(ROOT.glob("layouts/**/*.xml"))
        + list(ROOT.glob("assets/js/*.js"))
        + list(ROOT.glob("assets/json/*.json"))
    )
    for path in sorted(files):
        rel = path.relative_to(ROOT).as_posix()
        if path in (CONFIG_LEGACY, FRONT_MATTER_LEGACY):
            continue
        text = path.read_text(encoding="utf-8")
        for match in SITE_READ.finditer(text):
            site.setdefault(match.group(1), set()).add(rel)
        for match in PARAM_READ.finditer(text):
            site.setdefault(match.group(1), set()).add(rel)
            param_reads.add(match.group(1))
        for match in UI_PARAM_READ.finditer(text):
            # ui-param.html resolves params.ui.<key> with the bare front matter key.
            site.setdefault(f"ui.{match.group(1)}", set()).add(rel)
            page.setdefault(match.group(1), set()).add(rel)
        for match in SITE_MAP_READ.finditer(text):
            base = re.sub(r"^(?:\.Site\.Params|site\.Params|\$[A-Za-z]+\.Site\.Params)\.?", "", match.group(1))
            key = f"{base}.{match.group(2)}".strip(".")
            site.setdefault(key, set()).add(rel)
        # Shortcodes and render hooks read their own arguments through
        # .Params; only page-context templates read front matter.
        if "/_shortcodes/" in rel or "/_markup/" in rel:
            continue
        for match in PAGE_READ.finditer(text):
            if "Site" in match.group(0):
                continue
            page.setdefault(match.group(1), set()).add(rel)
        for match in PAGE_MAP_READ.finditer(text):
            if "Site" in match.group(1):
                continue
            base = re.sub(r"^(?:\$[A-Za-z]+|\.Page|)\.Params\.?", "", match.group(1))
            key = f"{base}.{match.group(2)}".strip(".")
            page.setdefault(key, set()).add(rel)
    return site, page, param_reads


def check_shapes(site: dict[str, set[str]], page: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for key, files in sorted(site.items()):
        if key.startswith(PASSTHROUGH_PREFIXES):
            continue
        for segment in key.split("."):
            require(
                KEY_SHAPE.match(segment) is not None,
                f"site key params.{key} is not snake_case (read in {sorted(files)[0]})",
                errors,
            )
        if key.endswith("_enabled"):
            require(
                key in ENABLED_SUFFIX_ALLOWED,
                f"params.{key}: a boolean switch is the bare feature name; `_enabled` is reserved for keys with sibling families",
                errors,
            )
        # Rule 2: nested keys live only inside a kept map.
        segments = key.split(".")
        if len(segments) >= 2:
            head = ".".join(segments[:2]) if segments[0] == "ui" else segments[0]
            if segments[0] == "ui" and len(segments) == 2:
                continue  # params.ui.<flat key>
            require(
                head in KEPT_MAPS,
                f"params.{key}: {head} is not a kept map — flatten it (rule 2) or add it to KEPT_MAPS with a reason",
                errors,
            )
            require(
                segments[-1] not in {"enable", "enabled"} or head in KEPT_MAPS,
                f"params.{key}: `.enable` members belong to kept maps only",
                errors,
            )
    for key, files in sorted(page.items()):
        first = key.split(".")[0]
        for segment in key.split("."):
            require(
                KEY_SHAPE.match(segment) is not None,
                f"front matter key {key} is not snake_case (read in {sorted(files)[0]})",
                errors,
            )
        require(
            first not in LEGACY_PAGE_KEYS,
            f"front matter key {key} was removed; it is still read in {sorted(files)[0]}",
            errors,
        )
        require(
            first != "ui",
            f"front matter must not need a ui. prefix; {key} is read explicitly in {sorted(files)[0]} (use .Param, or the bare key)",
            errors,
        )
    return errors


def check_page_parity(site: dict[str, set[str]], page: dict[str, set[str]], param_reads: set[str]) -> list[str]:
    errors: list[str] = []
    for page_key, site_key in sorted(PAGE_OVERRIDES.items()):
        expected = site_key[3:] if site_key.startswith("ui.") else site_key
        require(page_key == expected, f"front matter {page_key} must be the site key without ui.: {site_key}", errors)
        require(
            page_key in page or site_key in param_reads,
            f"front matter {page_key} is documented as a page override but no template reads it",
            errors,
        )
        require(site_key in site, f"params.{site_key} is documented as page-overridable but no template reads it", errors)
    return errors


GENERIC_MEMBERS = {"enable", "disable", "preset", "types", "params"}


def legacy_key(fragment: str) -> str:
    """The renamed key in a YAML fragment: the deepest key that is not a generic member."""
    keys = re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*):", fragment, re.MULTILINE)
    for key in reversed(keys):
        if key not in GENERIC_MEMBERS:
            return key
    return keys[-1]


def hugo_yaml_values() -> dict[str, str]:
    """Dotted key -> scalar/inline-list text of the theme's hugo.yaml (params only).

    The file is flat enough for an indentation walk; block lists and block maps
    are not needed for the keys the docs quote."""
    values: dict[str, str] = {}
    stack: list[tuple[int, str]] = []
    for raw in (ROOT / "hugo.yaml").read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(":")
        if not _ or not KEY_SHAPE.match(key.replace("-", "_")):
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        path = ".".join([k for _, k in stack] + [key])
        if value.strip():
            values[path] = value.strip()
        stack.append((indent, key))
    return values


DOCUMENTED_DEFAULT = re.compile(r"`params\.([a-z0-9_.]+)`\s*\(default:?\s*`([^`]+)`\)")


def check_documented_defaults() -> list[str]:
    """`params.X` (default `V`) in CLAUDE.md / README.md must match hugo.yaml."""
    errors: list[str] = []
    values = hugo_yaml_values()
    for name in ("CLAUDE.md", "README.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for key, documented in DOCUMENTED_DEFAULT.findall(text):
            declared = values.get(f"params.{key}")
            require(declared is not None, f"{name} documents a default for params.{key} that hugo.yaml does not declare", errors)
            if declared is None:
                continue
            normalise = lambda v: re.sub(r"[\[\]\s'\"]", "", v)  # noqa: E731
            require(
                normalise(declared) == normalise(documented),
                f"{name}: params.{key} documented default {documented!r} != hugo.yaml {declared!r}",
                errors,
            )
    return errors


def check_legacy_registries() -> list[str]:
    errors: list[str] = []
    site_registry = CONFIG_LEGACY.read_text(encoding="utf-8")
    page_registry = FRONT_MATTER_LEGACY.read_text(encoding="utf-8")
    for fragment, _expected in LEGACY_SITE_CASES:
        key = legacy_key(fragment)
        require(re.search(rf"\b{key}\b", site_registry) is not None, f"config-legacy.html does not register {key}", errors)
    for fragment, _expected in LEGACY_PAGE_CASES:
        if re.search(r"^\s*ui:", fragment, re.MULTILINE):
            continue  # every ui.* front matter key is rejected generically
        key = legacy_key(fragment)
        require(re.search(rf"\b{key}\b", page_registry) is not None, f"front-matter-legacy.html does not register {key}", errors)
    require('partialCached "config-legacy.html"' in (ROOT / "layouts/_partials/head.html").read_text(), "head.html no longer runs config-legacy.html", errors)
    require('partial "front-matter-legacy.html"' in (ROOT / "layouts/_partials/head.html").read_text(), "head.html no longer runs front-matter-legacy.html", errors)
    require(
        'partialCached "config-legacy.html"' in (ROOT / "layouts/_partials/typography-preset.html").read_text(),
        "typography-preset.html runs before head.html and must trigger config-legacy.html first",
        errors,
    )
    return errors


def site_config(params: str) -> str:
    indented = "\n".join(f"  {line}" if line else line for line in params.splitlines())
    return (
        "baseURL: https://example.org/\n"
        "title: Params fixture\n"
        f"theme: {ROOT.name}\n"
        "disableKinds: [RSS, sitemap, taxonomy, term]\n"
        + ("params:\n" + indented + "\n" if params.strip() else "")
    )


def build_case(hugo: str, name: str, params: str, front_matter: str) -> str:
    """Build a one-page site; return the combined output ("" on success)."""
    with tempfile.TemporaryDirectory(prefix=f"oink-params-{name}-") as temp:
        source = Path(temp)
        (source / "content/docs").mkdir(parents=True)
        (source / "hugo.yaml").write_text(site_config(params), encoding="utf-8")
        (source / "content/docs/_index.md").write_text("---\ntitle: Docs\n---\n\nSection.\n", encoding="utf-8")
        (source / "content/docs/page.md").write_text(
            f"---\ntitle: Page\n{front_matter}\n---\n\nBody.\n", encoding="utf-8"
        )
        result = subprocess.run(
            [hugo, "--source", str(source), "--themesDir", str(ROOT.parent), "--destination", str(source / "public"), "--logLevel", "warn"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "" if result.returncode == 0 else (result.stdout + result.stderr) or "build failed without output"


def check_builds(hugo: str) -> list[str]:
    errors: list[str] = []
    jobs: list[tuple[str, str, str, str | None]] = []
    for index, (fragment, expected) in enumerate(LEGACY_SITE_CASES):
        jobs.append((f"site-{index}", fragment, "", expected))
    for index, (fragment, expected) in enumerate(LEGACY_PAGE_CASES):
        jobs.append((f"page-{index}", "", fragment, expected))
    for index, fragment in enumerate(ACCEPTED_SITE_CASES):
        jobs.append((f"ok-site-{index}", fragment, "", None))
    for index, fragment in enumerate(ACCEPTED_PAGE_CASES):
        jobs.append((f"ok-page-{index}", "", fragment, None))

    def run(job: tuple[str, str, str, str | None]) -> tuple[tuple[str, str, str, str | None], str]:
        return job, build_case(hugo, job[0], job[1], job[2])

    with ThreadPoolExecutor(max_workers=4) as pool:
        for (name, params, front, expected), output in pool.map(run, jobs):
            label = (params or front).replace("\n", " ")
            if expected is None:
                require(output == "", f"accepted shape failed to build ({label}): {output[-400:]}", errors)
                continue
            require(output != "", f"legacy key built without an error ({label})", errors)
            require(expected in output, f"legacy key {label!r} did not name its replacement {expected!r}: {output[-400:]}", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--source-only", action="store_true", help="skip the legacy-key build matrix")
    args = parser.parse_args()

    site, page, param_reads = scan_read_points()
    errors = (
        check_shapes(site, page)
        + check_page_parity(site, page, param_reads)
        + check_legacy_registries()
        + check_documented_defaults()
    )
    if not args.source_only:
        errors += check_builds(args.hugo)

    if errors:
        print("Parameter contract check failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"Parameter contract check passed ({len(site)} site keys, {len(page)} front matter keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
