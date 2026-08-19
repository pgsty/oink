#!/usr/bin/env python3
"""Enforce the configuration parameter contract.

Three rules shape every theme parameter (see CHANGELOG 0.5.0):

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
assets, checks the shapes above, and then builds a
minimal site once per invalid value to prove that the build warns and the message
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
    "featured_image": "ui.featured_image",
    "reading_time": "ui.reading_time",
    "page_context_menu": "ui.page_context_menu",
    "share": "ui.share",
    "translation_notice": "ui.translation_notice",
    "comments": "comments",
    "page_width": "page_width",
    "reading_width": "reading_width",
    "blog_index": "ui.blog_index",
    "blog_index_columns": "ui.blog_index_columns",
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
    "default_featured",
    "upstream_attribution",
    "downstream_modified",
}



# The converged shapes must build; the bare-boolean shorthand of every kept
# on/off map is part of the contract.
ACCEPTED_SITE_CASES = [
    "ui:\n  annotation: false\n  translation_notice: en\n  image_zoom: true\n  keyboard_nav: false\n  reading_time: true\n  typography: system\n  pager_types: [docs]\n  breadcrumb: false\n  scroll_spy: true\n  code_copy: false\n  docs_sidebar_root: home",
    "reading_width: slim\nmarkmap: false\nplantuml: false\ndrawio: false\ncomments: false\nprint:\n  toc: false",
    "ui:\n  dark_mode: true\n  feedback: true\n  page_context_menu: false",
    "ui:\n  share: [x, hackernews, email, copy]",
]
ACCEPTED_PAGE_CASES = [
    "image_zoom: true\nreading_time: false\nannotation: false\npage_context_menu: false\nreading_width: wide\ntranslation_notice: false",
    "page_context_menu:\n  enable: true\n  assistant_links: false\nsection_index: cards\nsidebar_menu_compact: false\nkeyboard_nav: false\nbreadcrumb: false\nmanual_link: https://example.org/\nmanual_link_title: Example",
    "body_class: product-td-no-left-sidebar-preview",
    "blog_index: cards\nblog_index_columns: 4",
    # The page key is the site key without ui.: a list replaces the site's,
    # and the bare boolean opts one page out of an inherited one.
    "share: [x, copy]",
    "share: false",
]

INVALID_SITE_CASES = [
    ("comments: definitely", "params.comments must be a boolean or a map"),
    ("ui:\n  share: [x, mastodon]", 'invalid params.ui.share entry "mastodon"'),
    ("ui:\n  share: true", "params.ui.share is the list of share targets, not a switch"),
    ("ui:\n  share: x", "params.ui.share must be a list of share targets"),
    ("comments:\n  enable: definitely", "params.comments.enable must be true or false"),
    ("comments:\n  type: true", "params.comments.type must be a string"),
]
INVALID_PAGE_CASES = [
    ("comments: definitely", "front matter comments must be a boolean"),
    ("share: [wechat]", 'invalid params.ui.share entry "wechat"'),
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




def site_config(params: str) -> str:
    indented = "\n".join(f"  {line}" if line else line for line in params.splitlines())
    return (
        "baseURL: https://example.org/\n"
        "title: Params fixture\n"
        f"theme: {ROOT.name}\n"
        "disableKinds: [RSS, sitemap, taxonomy, term]\n"
        + ("params:\n" + indented + "\n" if params.strip() else "")
    )


def build_case(hugo: str, name: str, params: str, front_matter: str,
               panic_on_warning: bool = False) -> tuple[int, str]:
    """Build a one-page site; return its exit code and combined output.

    An invalid parameter no longer stops a build: it warns and falls back, so a
    case is judged on what the output says rather than on whether Hugo exited.
    `panic_on_warning` reproduces what every publishing gate does, which is
    where a warning is still a hard failure."""
    with tempfile.TemporaryDirectory(prefix=f"oink-params-{name}-") as temp:
        source = Path(temp)
        (source / "content/docs").mkdir(parents=True)
        (source / "hugo.yaml").write_text(site_config(params), encoding="utf-8")
        (source / "content/docs/_index.md").write_text("---\ntitle: Docs\n---\n\nSection.\n", encoding="utf-8")
        (source / "content/docs/page.md").write_text(
            f"---\ntitle: Page\n{front_matter}\n---\n\nBody.\n", encoding="utf-8"
        )
        command = [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
                   "--destination", str(source / "public"), "--logLevel", "warn"]
        if panic_on_warning:
            command.append("--panicOnWarning")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, (result.stdout + result.stderr)


def check_builds(hugo: str) -> list[str]:
    errors: list[str] = []
    jobs: list[tuple[str, str, str, str | None]] = []
    for index, fragment in enumerate(ACCEPTED_SITE_CASES):
        jobs.append((f"ok-site-{index}", fragment, "", None))
    for index, fragment in enumerate(ACCEPTED_PAGE_CASES):
        jobs.append((f"ok-page-{index}", "", fragment, None))
    for index, (fragment, expected) in enumerate(INVALID_SITE_CASES):
        jobs.append((f"invalid-site-{index}", fragment, "", expected))
    for index, (fragment, expected) in enumerate(INVALID_PAGE_CASES):
        jobs.append((f"invalid-page-{index}", "", fragment, expected))

    def run(job: tuple[str, str, str, str | None]):
        name = job[0]
        code, output = build_case(hugo, name, job[1], job[2])
        # An invalid value must warn and keep building, and the same build must
        # still fail where warnings are fatal. Both halves are the contract.
        strict = None
        if name.startswith("invalid-"):
            strict = build_case(hugo, name + "-strict", job[1], job[2], panic_on_warning=True)[0]
        return job, code, output, strict

    with ThreadPoolExecutor(max_workers=4) as pool:
        for (name, params, front, expected), code, output, strict in pool.map(run, jobs):
            label = (params or front).replace("\n", " ")
            if expected is None:
                require(code == 0, f"accepted shape failed to build ({label}): {output[-400:]}", errors)
                continue
            if name.startswith("invalid-"):
                require(code == 0,
                        f"invalid value stopped the build instead of warning ({label}): {output[-400:]}", errors)
                require(expected in output,
                        f"invalid value {label!r} did not warn with {expected!r}: {output[-400:]}", errors)
                require(strict != 0,
                        f"invalid value {label!r} survived --panicOnWarning", errors)
                continue
    return errors


def check_blog_index_enum(hugo: str) -> list[str]:
    """A value outside `list | cards` fails the build and names the allowed set.

    `blog/list.html` is the only reader of the key, and the shared one-page
    fixture above has no blog section, so this case brings its own."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-params-blog-index-") as temp:
        source = Path(temp)
        (source / "content/blog").mkdir(parents=True)
        (source / "hugo.yaml").write_text(site_config("ui:\n  blog_index: grid"), encoding="utf-8")
        (source / "content/blog/_index.md").write_text(
            "---\ntitle: Blog\ntype: blog\ncascade:\n  type: blog\n---\n", encoding="utf-8")
        (source / "content/blog/post.md").write_text(
            "---\ntitle: Post\ndate: 2026-08-19\n---\n\nBody.\n", encoding="utf-8")
        command = [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
                   "--destination", str(source / "public"), "--logLevel", "warn"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        output = result.stdout + result.stderr
        strict = subprocess.run(command + ["--panicOnWarning"], capture_output=True, text=True, check=False)
        require(result.returncode == 0,
                f"a form outside the enum stopped the build instead of warning: {output[-400:]}", errors)
        require("invalid params.ui.blog_index" in output and "list | cards" in output
                and "list" in output,
                f"the blog index warning does not name the allowed forms and the fallback: {output[-400:]}", errors)
        require(strict.returncode != 0,
                "an invalid params.ui.blog_index survived --panicOnWarning", errors)
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
        + check_documented_defaults()
    )
    if not args.source_only:
        errors += check_builds(args.hugo) + check_blog_index_enum(args.hugo)

    if errors:
        print("Parameter contract check failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"Parameter contract check passed ({len(site)} site keys, {len(page)} front matter keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
