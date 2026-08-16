#!/usr/bin/env python3
"""Validate PRD 5.6 shared scenario primitives and regression fixes."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def build(
    hugo: str,
    source: Path,
    destination: Path,
    *,
    environment: str = "production",
    layout_dir: Path | None = None,
    config: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        hugo,
        "--source",
        str(source),
        "--destination",
        str(destination),
        "--environment",
        environment,
        "--logLevel",
        "warn",
        "--themesDir",
        str(ROOT.parent),
    ]
    if layout_dir is not None:
        command.extend(["--layoutDir", str(layout_dir)])
    if config is not None:
        command.extend(["--config", f"{source / 'hugo.yaml'},{config}"])
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=process_env,
    )


def check_example(public: Path) -> list[str]:
    errors: list[str] = []
    page_path = public / "docs/content-primitives/index.html"
    print_path = public / "_print/docs/index.html"
    markdown_path = public / "docs/content-primitives/index.md"
    docs_path = public / "docs/index.html"
    not_found_path = public / "404.html"
    for path in (page_path, print_path, markdown_path, docs_path, not_found_path):
        require(path.exists(), f"misc fixture output is missing: {path}", errors)
    if not all(path.exists() for path in (page_path, print_path, markdown_path, docs_path, not_found_path)):
        return errors

    page = page_path.read_text(encoding="utf-8")
    print_page = print_path.read_text(encoding="utf-8")
    markdown = markdown_path.read_text(encoding="utf-8")
    docs = docs_path.read_text(encoding="utf-8")
    not_found = not_found_path.read_text(encoding="utf-8")

    for marker in (
        'class="td-table-scroll" tabindex="0" role="region"',
        'aria-label="Scrollable table"',
        'class="td-table-scroll td-table-scroll--full"',
        '<table class="full-width">',
    ):
        require(marker in page, f"table output lost {marker}", errors)
    require('<table class="full-width">' in print_page, "print output lost the full-width table", errors)
    require("td-table-scroll" not in print_page, "print table kept its scroll viewport", errors)
    require(
        "| Full table | 100% | Horizontal scroll | Complete table |" in markdown
        and "{.full-width}" in markdown,
        "Markdown output lost the full-width table source",
        errors,
    )

    require(
        'class="section-index section-index--cards td-content-cards"' in docs,
        "card section index did not render",
        errors,
    )
    section_index = re.search(r'<div class="section-index.*?</div>\s*</div>', docs, re.S)
    require(section_index is not None, "card section index boundary is missing", errors)
    if section_index:
        require("Reference group" not in section_index.group(0), "sidebar divider leaked into the section index", errors)

    divider_match = re.search(
        r'<li class="td-shell-tree__item td-shell-tree__heading" id="(?P<id>[^"]+)">\s*'
        r'<span class="td-shell-tree__heading-label"[^>]*><span>Reference group</span>',
        page,
    )
    require(divider_match is not None, "sidebar divider did not render as a heading", errors)
    if divider_match:
        require(divider_match.group("id") != "m--li", "sidebar divider has an empty DOM id", errors)
    require(
        not (public / "docs/guides/divider/index.html").exists(),
        "render-never sidebar divider emitted a page",
        errors,
    )
    pager_source = (public / "docs/guides/first/index.html").read_text(encoding="utf-8")
    pager = re.search(r'<nav class="td-pager.*?</nav>', pager_source, re.S)
    require(not pager or "Reference group" not in pager.group(0), "pager points at a sidebar divider", errors)
    require("Reference group" not in print_page, "sidebar divider leaked into print aggregation", errors)

    search_indexes = list(public.glob("offline-search-index.*.json"))
    require(len(search_indexes) == 1, "offline search fixture did not emit one language index", errors)
    if search_indexes:
        require(
            '"keywords":["scenario-hook-keyword"]' in search_indexes[0].read_text(encoding="utf-8"),
            "search keyword extension hook was not merged",
            errors,
        )

    for marker in ("<!doctype html>", "<html ", "<head>", '<body class="td-404">', "</html>"):
        require(marker in not_found, f"404 output is not a complete document: {marker}", errors)
    for marker in ("td-print-view", "_print/", "data-td-landing"):
        require(marker not in not_found, f"404 inherited another output shell: {marker}", errors)

    robots = public / "robots.txt"
    require(robots.exists(), "production robots.txt is missing", errors)
    if robots.exists():
        source = robots.read_text(encoding="utf-8")
        require("User-agent: *\nAllow: /" in source, "production robots.txt is not permissive", errors)
        require("Sitemap: https://example.org/sitemap.xml" in source, "robots.txt lost sitemap URL", errors)
        require("Disallow: /" not in source, "production robots.txt contains development policy", errors)
    return errors


def check_sources() -> list[str]:
    errors: list[str] = []
    sources = {
        "robots": (ROOT / "layouts/robots.txt").read_text(encoding="utf-8"),
        "table": (ROOT / "layouts/_markup/render-table.html").read_text(encoding="utf-8")
        + (ROOT / "layouts/_partials/content/table-body.html").read_text(encoding="utf-8"),
        "section": (ROOT / "layouts/_partials/section-index.html").read_text(encoding="utf-8"),
        "lastmod": (ROOT / "layouts/_partials/page-meta-lastmod.html").read_text(encoding="utf-8"),
        "page_end": (ROOT / "layouts/_partials/page-end.html").read_text(encoding="utf-8"),
        "annotation": (ROOT / "layouts/_partials/page-annotation.html").read_text(encoding="utf-8"),
        "docs_content": (ROOT / "layouts/_td-content.html").read_text(encoding="utf-8"),
        "docs_list": (ROOT / "layouts/docs/list.html").read_text(encoding="utf-8"),
        "book_list": (ROOT / "layouts/book/list.html").read_text(encoding="utf-8"),
        "swagger_list": (ROOT / "layouts/swagger/list.html").read_text(encoding="utf-8"),
        "blog_content": (ROOT / "layouts/blog/_td-content.html").read_text(encoding="utf-8"),
        "blog_list": (ROOT / "layouts/blog/list.html").read_text(encoding="utf-8"),
        "sidebar": (ROOT / "layouts/_partials/shell/sidebar-tree.html").read_text(encoding="utf-8"),
        "docs_sidebar": (ROOT / "layouts/_partials/shell/docs-sidebar-tree.html").read_text(encoding="utf-8"),
        "search": (ROOT / "layouts/_partials/search/metadata.html").read_text(encoding="utf-8"),
        "404": (ROOT / "layouts/404.html").read_text(encoding="utf-8"),
        "tokens": (ROOT / "assets/scss/td/shell/_tokens.scss").read_text(encoding="utf-8"),
        "content": (ROOT / "assets/scss/td/_content.scss").read_text(encoding="utf-8"),
        "navbar": (ROOT / "layouts/_partials/navbar.html").read_text(
            encoding="utf-8"
        ),
        "navbar_autohide": (
            ROOT / "layouts/_partials/shell/navbar-autohide.html"
        ).read_text(encoding="utf-8"),
        "navbar_styles": (ROOT / "assets/scss/td/_site-navbar.scss").read_text(
            encoding="utf-8"
        ),
        "variables": (ROOT / "assets/scss/td/_variables.scss").read_text(
            encoding="utf-8"
        ),
        "contract": (ROOT / "docs/prd5-reading-release-contract.md").read_text(encoding="utf-8"),
    }
    require("hugo.IsProduction" in sources["robots"], "robots policy is not environment-aware", errors)
    for marker in (".Attributes", "td-table-scroll--full", 'T "ui_table_scroll"'):
        require(marker in sources["table"], f"table hook lacks {marker}", errors)
    for marker in ("overflow-x: auto", "&--full", "@media print"):
        require(marker in sources["content"], f"table styles lack {marker}", errors)
    for marker in ("section_index", 'slice "list" "cards"', "td-content-card", "sidebar_divider"):
        require(marker in sources["section"], f"section index lacks {marker}", errors)
    for marker in ('slice "subject" "hash" "none"', "AbbreviatedHash", "GitInfo.Subject"):
        require(marker in sources["lastmod"], f"lastmod mode handling lacks {marker}", errors)
    for name in ("docs_content", "docs_list", "book_list", "swagger_list", "blog_content", "blog_list"):
        require(
            'partial "page-end.html"' in sources[name],
            f"{name} does not use the shared page-end composition",
            errors,
        )
    page_end = sources["page_end"]
    require(
        page_end.index('partial "feedback.html"')
        < page_end.index('partial "page-annotation.html"')
        < page_end.index('partial "pager.html"')
        < page_end.index('partial "comments.html"'),
        "page-end composition order drifted",
        errors,
    )
    require(
        'partial "page-meta-lastmod.html"' in sources["annotation"],
        "annotation no longer preserves the legacy lastmod override slot",
        errors,
    )
    for name in ("sidebar", "docs_sidebar"):
        require("sidebar_divider" in sources[name], f"{name} lacks sidebar_divider", errors)
        require("td-shell-tree__heading-label" in sources[name], f"{name} lacks divider semantics", errors)
        require("$s.Path" in sources[name], f"{name} lacks a render-never id fallback", errors)
    require(
        'partial "hooks/search-keywords-extra.html"' in sources["search"]
        and "reflect.IsSlice" in sources["search"],
        "search extension hook is missing or unvalidated",
        errors,
    )
    require("<!doctype html>" in sources["404"] and '<body class="td-404">' in sources["404"], "404 template is block-only", errors)
    require(
        "@media (max-width: 767.98px)" in sources["tokens"]
        and "scroll-padding-top: var(--td-scroll-padding-top)" in sources["tokens"],
        "narrow shell anchor offset fix is missing",
        errors,
    )
    require(
        "$td-navbar-min-height: 50px" in sources["variables"],
        "navbar height is not 50px",
        errors,
    )
    require(
        'partial "shell/navbar-autohide.html"' in sources["navbar"]
        and "data-td-navbar-autohide" in sources["navbar"],
        "navbar auto-hide wrapper is missing",
        errors,
    )
    for marker in (
        '.Site.Params.ui "navbar_autohide"',
        '.Params "navbar_autohide"',
        "navbar_autohide must be a boolean",
    ):
        require(
            marker in sources["navbar_autohide"],
            f"navbar auto-hide resolver lacks {marker}",
            errors,
        )
    for marker in (
        "(hover: hover) and (pointer: fine)",
        "height: $td-navbar-min-height",
        ".td-navbar-autohide:focus-within",
        "@media (prefers-reduced-motion: reduce)",
    ):
        require(
            marker in sources["navbar_styles"],
            f"navbar auto-hide styles lack {marker}",
            errors,
        )
    for marker in ("data/docs_nav.json", "manualLink", "build.render: link", "sidebar_divider"):
        require(marker in sources["contract"], f"reading contract lacks {marker}", errors)
    hook = ROOT / "layouts/_partials/hooks/search-keywords-extra.html"
    require(hook.exists() and "return (slice)" in hook.read_text(), "empty search hook default is missing", errors)
    return errors


def check_development_robots(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-prd5-robots-") as temp:
        public = Path(temp) / "public"
        result = build(hugo, EXAMPLE, public, environment="development")
        if result.returncode != 0:
            return [f"development robots fixture failed: {result.stdout}{result.stderr}"]
        source = (public / "robots.txt").read_text(encoding="utf-8")
        require("User-agent: *\nDisallow: /" in source, "development robots.txt allows crawling", errors)
        require("Allow: /" not in source, "development robots.txt contains production policy", errors)
        require("Sitemap:" not in source, "development robots.txt exposes a sitemap", errors)
    return errors


def check_invalid_config(hugo: str) -> list[str]:
    errors: list[str] = []
    cases = (
        ("section-index", "    section_index: tiles\n", "invalid params.ui.section_index"),
        ("lastmod", "    lastmod_commit: message\n", "invalid params.ui.lastmod_commit"),
        (
            "navbar-autohide",
            "    navbar_autohide: sometimes\n",
            "navbar_autohide must be a boolean",
        ),
        (
            "feedback-enable",
            "    feedback:\n      enable: sometimes\n",
            "feedback.enable must be a boolean",
        ),
        (
            "annotation-enable",
            "    annotation:\n      enable: sometimes\n",
            "annotation.enable must be a boolean",
        ),
    )
    for name, value, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-prd5-invalid-{name}-") as temp:
            temp_path = Path(temp)
            override = temp_path / "override.yaml"
            write(override, "params:\n  ui:\n" + value)
            result = build(hugo, EXAMPLE, temp_path / "public", config=override)
            output = result.stdout + result.stderr
            require(result.returncode != 0, f"invalid {name} config unexpectedly built", errors)
            require(expected in output, f"invalid {name} config did not report {expected!r}", errors)

    with tempfile.TemporaryDirectory(prefix="oink-prd5-invalid-search-serve-") as temp:
        temp_path = Path(temp)
        override = temp_path / "override.yaml"
        write(override, "params:\n  offlineSearchOnServe: 0\n")
        result = build(hugo, EXAMPLE, temp_path / "public", config=override)
        output = result.stdout + result.stderr
        expected = "params.offlineSearchOnServe must be a boolean"
        require(result.returncode != 0, "invalid offlineSearchOnServe config unexpectedly built", errors)
        require(expected in output, f"invalid offlineSearchOnServe config did not report {expected!r}", errors)

    with tempfile.TemporaryDirectory(prefix="oink-prd5-search-hook-") as temp:
        temp_path = Path(temp)
        source = temp_path / "site"
        write(
            source / "hugo.yaml",
            f"""baseURL: https://example.org/
title: Search hook fixture
theme: {ROOT.name}
disableKinds: [home, RSS, sitemap, taxonomy, term]
""",
        )
        write(source / "content/page.md", "---\ntitle: Page\n---\n")
        write(
            source / "layouts/_partials/hooks/search-keywords-extra.html",
            "{{ return (dict \"bad\" true) }}\n",
        )
        write(
            source / "layouts/_default/single.html",
            "{{ partial \"search/metadata.html\" . }}\n",
        )
        result = build(hugo, source, temp_path / "public")
        output = result.stdout + result.stderr
        require(result.returncode != 0, "non-array search hook unexpectedly built", errors)
        require(
            "must return an array" in output,
            f"non-array search hook lacks a focused error; Hugo reported: {output.strip()}",
            errors,
        )
    return errors


def check_navbar_autohide(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-navbar-autohide-") as temp:
        temp_path = Path(temp)
        source = temp_path / "site"
        public = temp_path / "public"
        write(
            source / "hugo.yaml",
            f"""baseURL: https://example.org/
title: Navbar auto-hide fixture
theme: {ROOT.name}
disableKinds: [home, RSS, sitemap, taxonomy, term]
params:
  offlineSearch: false
  ui:
    navbar_autohide: true
""",
        )
        write(
            source / "content/project.md",
            "---\ntitle: Project\n---\nGlobal policy.\n",
        )
        write(
            source / "content/docs/_index.md",
            "---\ntitle: Docs\ntype: docs\ncascade:\n  type: docs\n  navbar_autohide: false\n---\nSection policy.\n",
        )
        write(
            source / "content/docs/inherit.md",
            "---\ntitle: Inherit\n---\nSection override.\n",
        )
        write(
            source / "content/docs/override.md",
            "---\ntitle: Override\nnavbar_autohide: true\n---\nPage override.\n",
        )

        result = build(hugo, source, public)
        if result.returncode != 0:
            return [f"navbar auto-hide fixture failed: {result.stdout}{result.stderr}"]

        outputs = {
            "global": public / "project/index.html",
            "section": public / "docs/inherit/index.html",
            "page": public / "docs/override/index.html",
        }
        for name, path in outputs.items():
            require(path.exists(), f"navbar auto-hide {name} fixture is missing", errors)
        if not all(path.exists() for path in outputs.values()):
            return errors

        marker = 'class="td-navbar-autohide" data-td-navbar-autohide'
        global_page = outputs["global"].read_text(encoding="utf-8")
        section_page = outputs["section"].read_text(encoding="utf-8")
        page_override = outputs["page"].read_text(encoding="utf-8")
        require(marker in global_page, "global navbar auto-hide policy did not apply", errors)
        require(marker not in section_page, "section navbar auto-hide override did not apply", errors)
        require(marker in page_override, "page navbar auto-hide override did not win", errors)
    return errors


def create_git_site(root: Path) -> None:
    write(
        root / "hugo.yaml",
        f"""baseURL: https://example.org/
title: Lastmod fixture
theme: {ROOT.name}
enableGitInfo: true
disableKinds: [home, RSS, sitemap, taxonomy, term]
params:
  github_repo: https://github.com/example/project
  ui:
    shell_types: [docs]
    lastmod_commit: hash
""",
    )
    write(root / "content/docs/_index.md", "---\ntitle: Docs\ntype: docs\n---\n")
    write(root / "content/docs/page.md", "---\ntitle: Git page\ntype: docs\n---\n\nBody.\n")
    git_env = os.environ.copy()
    git_env.update(
        {
            "GIT_AUTHOR_NAME": "OINK Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.org",
            "GIT_COMMITTER_NAME": "OINK Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.org",
        }
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=git_env)
    subprocess.run(["git", "add", "."], cwd=root, check=True, env=git_env)
    subprocess.run(["git", "commit", "-q", "-m", "Fixture subject"], cwd=root, check=True, env=git_env)


def check_lastmod_output(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-prd5-lastmod-") as temp:
        source = Path(temp)
        create_git_site(source)
        public = source / "public"
        result = build(hugo, source, public)
        if result.returncode != 0:
            return [f"Git lastmod fixture failed: {result.stdout}{result.stderr}"]
        page = (public / "docs/page/index.html").read_text(encoding="utf-8")
        require(re.search(r">commit [0-9a-f]{7,}</a>", page) is not None, "hash mode did not render the abbreviated hash", errors)
        require("Fixture subject" not in page, "hash mode leaked the commit subject", errors)

        override = source / "none.yaml"
        write(override, "params:\n  ui:\n    lastmod_commit: none\n")
        result = build(hugo, source, public, config=override)
        if result.returncode != 0:
            errors.append(f"lastmod none fixture failed: {result.stdout}{result.stderr}")
        else:
            page = (public / "docs/page/index.html").read_text(encoding="utf-8")
            require("/commit/" not in page, "none mode kept a commit link", errors)
            require("Last modified" in page, "none mode removed the last-modified date", errors)
    return errors


def check_stable_404(hugo: str) -> list[str]:
    errors: list[str] = []
    digests: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="oink-prd5-404-") as temp:
        source = Path(temp) / "site"
        write(
            source / "hugo.yaml",
            f"""baseURL: https://example.org/
title: 404 fixture
theme: {ROOT.name}
defaultContentLanguage: en
defaultContentLanguageInSubdir: true
languages:
  en: {{ label: English, weight: 1 }}
  zh: {{ label: 简体中文, weight: 2 }}
outputs:
  home: [HTML, print]
disableKinds: [RSS, sitemap, taxonomy, term]
""",
        )
        write(source / "data/home/en.yaml", "sections: []\n")
        write(source / "data/home/zh.yaml", "sections: []\n")
        for index in range(10):
            public = Path(temp) / f"public-{index}"
            result = build(hugo, source, public)
            if result.returncode != 0:
                errors.append(f"multilingual 404 build {index + 1} failed: {result.stdout}{result.stderr}")
                break
            outputs = sorted(public.rglob("404.html"))
            require(bool(outputs), f"multilingual 404 build {index + 1} emitted no 404", errors)
            for output in outputs:
                body = output.read_bytes()
                require(b"<!doctype html>" in body and b'<body class="td-404">' in body, f"{output} is not interactive HTML", errors)
                require(b"td-print-view" not in body, f"{output} inherited the print shell", errors)
                digests.add(hashlib.sha256(body).hexdigest())
        # One stable document per language is expected; repeat builds must not
        # introduce additional variants through base-template selection.
        require(len(digests) <= 2, f"404 output changed across repeated builds ({len(digests)} variants)", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    args = parser.parse_args()

    if args.public is None:
        with tempfile.TemporaryDirectory(prefix="oink-prd5-misc-") as temp:
            public = Path(temp) / "public"
            result = build(args.hugo, EXAMPLE, public)
            if result.returncode != 0:
                print("PRD 5 misc fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_example(public)
    else:
        errors = check_example(args.public)

    errors += (
        check_sources()
        + check_development_robots(args.hugo)
        + check_invalid_config(args.hugo)
        + check_navbar_autohide(args.hugo)
        + check_lastmod_output(args.hugo)
        + check_stable_404(args.hugo)
    )
    if errors:
        print("PRD 5 misc checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("PRD 5 misc checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
