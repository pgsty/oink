#!/usr/bin/env python3
"""Verify the PRD 7 navigation, page-end, and feedback contracts."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_sources() -> list[str]:
    errors: list[str] = []
    root_entries = (ROOT / "layouts/_partials/shell/root-menu-entries.html").read_text()
    root_roots = (ROOT / "layouts/_partials/shell/root-menu-roots.html").read_text()
    root_menu = (ROOT / "layouts/_partials/shell/root-menu.html").read_text()
    generic_tree = (ROOT / "layouts/_partials/shell/sidebar-tree.html").read_text()
    docs_tree = (ROOT / "layouts/_partials/shell/docs-sidebar-tree.html").read_text()
    page_end = (ROOT / "layouts/_partials/page-end.html").read_text()
    annotation = (ROOT / "layouts/_partials/page-annotation.html").read_text()
    pager = (ROOT / "layouts/_partials/pager.html").read_text()
    pager_styles = (ROOT / "assets/scss/td/_pager.scss").read_text()
    content_styles = (ROOT / "assets/scss/td/_content.scss").read_text()
    comments_styles = (ROOT / "assets/scss/td/_giscus.scss").read_text()
    blog_styles = (ROOT / "assets/scss/td/shell/_blog.scss").read_text()
    page_context_styles = (ROOT / "assets/scss/td/shell/_page-context.scss").read_text()
    breadcrumb_state = (ROOT / "layouts/_partials/shell/breadcrumb-enabled.html").read_text()
    sidebar_panel = (ROOT / "layouts/_partials/shell/sidebar-panel.html").read_text()
    keyboard_help = (ROOT / "layouts/_partials/shell/keyboard-help.html").read_text()
    subnav = (ROOT / "layouts/_partials/shell/subnav.html").read_text()
    sidebar_styles = (ROOT / "assets/scss/td/shell/_sidebar.scss").read_text()
    keyboard_styles = (ROOT / "assets/scss/td/shell/_kbd-nav.scss").read_text()
    language_styles = (ROOT / "assets/scss/td/_language-selector.scss").read_text()
    layout_styles = (ROOT / "assets/scss/td/shell/_layout.scss").read_text()
    toc_styles = (ROOT / "assets/scss/td/shell/_toc.scss").read_text()
    toc_aside = (ROOT / "layouts/_partials/shell/toc-aside.html").read_text()
    navbar_styles = (ROOT / "assets/scss/td/_site-navbar.scss").read_text()
    footer_styles = (ROOT / "assets/scss/td/_footer.scss").read_text()
    navbar_item = (ROOT / "layouts/_partials/navbar-item.html").read_text()
    taxonomy = (ROOT / "layouts/_partials/navbar-taxonomy-tags.html").read_text()
    feedback = (ROOT / "layouts/_partials/feedback.html").read_text()
    feedback_js = (ROOT / "assets/js/feedback.js").read_text()
    giscus = (ROOT / "layouts/_partials/giscus.html").read_text()
    keyboard = (ROOT / "assets/js/keyboard-nav.js").read_text()
    base_js = (ROOT / "assets/js/base.js").read_text()
    navbar = (ROOT / "layouts/_partials/navbar.html").read_text()
    version = (ROOT / "layouts/_partials/navbar-version-selector.html").read_text()
    icons = (ROOT / "layouts/_partials/shell/icon.html").read_text()
    actions_context = (ROOT / "layouts/_partials/actions/context.html").read_text()
    shell_tokens = (ROOT / "assets/scss/td/shell/_tokens.scss").read_text()
    title_menu = (ROOT / "layouts/_partials/actions/title-menu.html").read_text()
    docs_layout = (ROOT / "layouts/docs/baseof.html").read_text()
    blog_layout = (ROOT / "layouts/blog/baseof.html").read_text()
    migration_en = (ROOT / "docs/prd7-migration-guide.md").read_text()
    migration_zh = (ROOT / "docs/prd7-migration-guide.zh.md").read_text()

    for marker in ("Home.Sections.ByWeight", 'Params.sidebar_root_for', "sidebar_root_menu"):
        require(marker in root_roots, f"root set lost {marker}", errors)
    require('partial "shell/sidebar-root.html"' in root_entries
            and 'partialCached "shell/root-menu-roots.html"' in root_entries,
            "root set lost page resolution or site-level caching", errors)
    require('eq (len $entries) 1' in root_menu and "td-shell-root--static" in root_menu,
            "one-root switcher is not a static link", errors)
    require("td-shell-tree__item--rootless" not in generic_tree,
            "generic sidebar still removes its root row", errors)
    require('isset $s.Params "sidebar_root_link_self"' in generic_tree
            and '"sidebar_root_link_self must be a boolean' in generic_tree
            and "$rootLinkSelf := true" in generic_tree,
            "self-root links do not default to their own landing with an explicit legacy escape", errors)
    require('"node" (dict "page" $sidebarRootURL' in docs_tree,
            "explicit docs sidebar does not prepend a missing root row", errors)
    require("continue" not in docs_tree.split('index $docsNav "sections"', 1)[1].split("template", 1)[0],
            "docs sidebar still skips its root row", errors)

    order = [
        page_end.index('partial "feedback.html"'),
        page_end.index('partial "page-annotation.html"'),
        page_end.index('partial "pager.html"'),
        page_end.index('partial "comments.html"'),
    ]
    require(order == sorted(order), "page-end component order drifted", errors)
    require('partial "page-meta-lastmod.html"' in annotation,
            "annotation lost the legacy consumer override", errors)
    for template in (
        "layouts/_td-content.html",
        "layouts/docs/list.html",
        "layouts/book/list.html",
        "layouts/swagger/list.html",
        "layouts/blog/_td-content.html",
        "layouts/blog/list.html",
    ):
        require('partial "page-end.html"' in (ROOT / template).read_text(),
                f"{template} bypasses page-end", errors)

    require("td-pager__summary" in pager and "&__card:only-child" in pager_styles,
            "pager lost its two-row or full-width boundary behavior", errors)
    require("with .Description }}{{ $description = . | markdownify" in pager
            and "$description := .Summary" in pager
            and 'replaceRE `\\s+` " "' in pager
            and "truncate 180" in pager,
            "pager descriptions no longer distinguish rendered summaries from Markdown metadata", errors)
    require("white-space: nowrap" in pager_styles
            and "&__card--next &__summary" in pager_styles
            and "font-family: var(--td-body-font-family)" in pager_styles,
            "pager descriptions no longer stay on one aligned line", errors)
    annotation_styles = content_styles.split(".td-page-annotation", 1)[1].split("}", 1)[0]
    require("font-family: var(--td-body-font-family)" in annotation_styles,
            "page annotation reverted to a code-like font", errors)
    feedback_styles = content_styles.split(".td-feedback", 1)[1].split(".td-page-annotation", 1)[0]
    require("border-block-start" in feedback_styles
            and "border-block:" not in feedback_styles
            and "flex-wrap: nowrap" in feedback_styles,
            "feedback prompt lost its compact single-divider row", errors)
    require(".td-pager + &" in comments_styles,
            "pager-to-discussion spacing is no longer compact", errors)
    require("display: table" in content_styles and "margin-block-end: $spacer" in content_styles,
            "Markdown tables no longer fill their viewport or separate following prose", errors)
    require("not $.IsPage" in breadcrumb_state and ".IsHome" in breadcrumb_state,
            "top-level nodes no longer suppress their redundant breadcrumb", errors)
    require("min-height: 29px" in page_context_styles,
            "page actions no longer keep a stable topline height", errors)
    require("td-shell-topline--actions-only" in page_context_styles
            and "height: 0" in page_context_styles
            and "td-shell-topline--actions-only" in docs_layout
            and "td-shell-topline--actions-only" in blog_layout,
            "breadcrumb-free roots no longer lift their title while pinning actions", errors)
    search_index = sidebar_panel.index('class="td-shell-iconbtn td-shell-sidebar__search"')
    collapse_index = sidebar_panel.index('class="td-shell-iconbtn td-shell-sidebar__collapse"')
    require(search_index < collapse_index,
            "desktop sidebar search no longer precedes the collapse action", errors)
    require("if and $navbar $localSearch" not in sidebar_panel,
            "desktop sidebar search is still coupled to navbar rendering", errors)
    require("td-shell-search-btn--drawer" in sidebar_panel
            and '<kbd>/</kbd>' in sidebar_panel,
            "mobile drawer no longer renders the full slash-hint search field", errors)
    require('"search" "subnav-search"' in subnav
            and '"menu" "subnav-menu"' in subnav
            and subnav.index('data-td-shell-search-open')
            < subnav.index('data-td-shell-drawer-open'),
            "navbar-off mobile bar lost its search-before-menu contract", errors)
    require('class="td-shell-subnav__menu"' in subnav
            and 'partial "navbar-entry-link.html"' in subnav,
            "navbar-off mobile bar lost its content-generated center menu", errors)
    footer = sidebar_panel.split('class="td-shell-sidebar__footer"', 1)[1].split(
        'class="td-shell-sidebar__resizer"', 1)[0]
    footer_order = [
        footer.index('partial "language-selector.html"'),
        footer.index('partial "navbar-version-selector.html"'),
        footer.index('partial "shell/keyboard-help.html"'),
        footer.index("td-shell-quick-theme"),
        footer.index('aria-label="GitHub"'),
    ]
    require(footer_order == sorted(footer_order),
            "sidebar footer order is not language/version/help/theme/GitHub", errors)
    require("td-shell-sidebar__footer-start" in footer
            and "td-shell-sidebar__footer-end" in footer
            and "justify-content: space-between" in sidebar_styles,
            "sidebar footer no longer splits language/version from theme/GitHub", errors)
    require("if not $navbar" not in footer
            and ".td-shell-sidebar__footer .td-language-selector--menu" in language_styles
            and "inset-inline-start: 0" in language_styles,
            "sidebar footer is no longer unconditional or its language menu lost dropup styling", errors)
    require("dropdown.show()" in base_js and "menu.addEventListener('pointerenter'" in base_js,
            "sidebar version menu no longer opens on pointer hover", errors)
    require(all(f'data-bs-theme-value="{value}"' in footer
                for value in ("light", "dark", "auto"))
            and "data-td-nav-hover" in footer
            and base_js.count("menu.closest('#td-shell-sidebar') ? ['drawer'] : []") >= 2,
            "sidebar theme trigger no longer exposes the three-mode hover menu", errors)
    require('data-td-nav-hover-open' in keyboard_help
            and 'class="td-kbd-sequence"' in keyboard_help
            and all(key in keyboard_help for key in ('<kbd>W</kbd>', '<kbd>/</kbd>', '<kbd>H</kbd>'))
            and ".td-shell-keyboard-help__row" in keyboard_styles
            and ".td-shell-sidebar__footer .td-shell-keyboard" in keyboard_styles
            and "position: static" in keyboard_styles
            and "inset-inline: 8px" in keyboard_styles,
            "sidebar shortcut help lost its hover trigger or KBD cheat sheet", errors)
    # One icon system in the shell chrome: shell/icon.html dispenses Font Awesome
    # glyphs under role-named classes, version controls take theirs from it, and
    # the page action menu takes action icons from the registry rather than a
    # second hand-written mapping. Glyph choices themselves are not contract.
    require('<i class="td-shell-icon td-shell-icon--{{ $name }}' in icons and "<svg" not in icons
            and "--td-shell-icon-size" in shell_tokens,
            "shell/icon.html no longer dispenses a single Font Awesome icon system", errors)
    require('shell/icon.html' in version and 'shell/icon.html' in navbar
            and 'class="fa-' not in version and '<i class="fa-solid fa-code' not in navbar,
            "version controls no longer take their icon from the shell dispenser", errors)
    require(all(f"$byID.{action}.icon" in title_menu for action in (
                "copy_markdown", "view_markdown", "view_history", "edit_page",
                "create_child_page", "create_issue", "create_project_issue", "print_section"))
            and 'shell/icon.html" "copy"' not in title_menu,
            "page action menu no longer takes action icons from the registry", errors)
    require("if not $hasToc" in toc_aside
            and "quickLinks" not in toc_aside
            and "td-shell-quick-theme" not in toc_aside
            and 'aria-label="GitHub"' not in toc_aside,
            "right TOC rail duplicated the sidebar utility controls", errors)
    alignment = "var(--td-shell-nav-h) + var(--td-shell-content-top, 2.5rem)"
    require(alignment in layout_styles and alignment in toc_styles,
            "collapsed rail controls no longer align with the article topline", errors)
    require("@media (min-width: 768px) and (hover: hover) and (pointer: fine)" in navbar_styles,
            "drawer-width viewports no longer disable auto-hide", errors)
    require("@media (max-width: 767.98px)" in navbar_styles
            and "html[data-td-kbd-zen] .td-navbar-autohide" in navbar_styles
            and "--td-shell-nav-h: #{$td-navbar-min-height}" in navbar_styles,
            "the phone tier no longer overrides every navbar hiding state", errors)
    require("html[data-td-kbd-zen] .td-shell-subnav" in keyboard_styles
            and "display: grid" in keyboard_styles,
            "navbar-off phone chrome can still disappear in reading mode", errors)
    require("grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr)" in navbar_styles
            and ".landing-header .nav-menu-zone" in navbar_styles
            and "margin-inline-start: 0" in navbar_styles,
            "phone navbar no longer true-centers its generated menu", errors)
    require("> .nav-version-menu" in navbar_styles
            and "> .nav-theme-menu" in navbar_styles
            and "> .nav-github" in navbar_styles
            and "> :not(.nav-search-box):not(.landing-mobile-menu-toggle)" in navbar_styles,
            "phone navbar no longer reduces its utility edge to search and menu", errors)
    require(".nav-alt-site > span" in navbar_styles
            and ".nav-github .nav-count" in navbar_styles
            and "white-space: nowrap" in navbar_styles,
            "compact navbar labels can wrap or crowd the icon tier", errors)
    require("html:not([data-td-shell-sidebar='collapsed'])" in navbar_styles
            and "body.td-shell-chrome--navbar:has(#td-shell-sidebar)" in navbar_styles
            and "visibility: hidden" in navbar_styles,
            "the sidebar-covered navbar Home link can remain in the desktop focus order", errors)
    require(".td-navbar-autohide::before" in navbar_styles
            and "--td-navbar-reveal-inset: 64px" in navbar_styles
            and "--td-navbar-reveal-height: 60%" in navbar_styles
            and "pointer-events: none" in navbar_styles,
            "navbar reveal strip no longer reserves its corner exclusion zones", errors)
    require('$taxonomyPage' in navbar_item and 'Kind "taxonomy"' in navbar_item
            and 'partialCached "navbar-taxonomy-tags.html"' in navbar_item
            and ".Site.LanguagePrefix" in navbar_item,
            "taxonomy entries are not promoted to navbar panels", errors)
    require(".ByCount" in taxonomy and "td-navbar-taxonomy-tag__count" in taxonomy,
            "taxonomy panel lost count-descending tag chips", errors)
    require("flex-wrap: wrap" in navbar_styles and "flex-wrap: wrap" in blog_styles,
            "navbar or right-rail taxonomy terms are no longer tag clouds", errors)
    require(".nav-menu__panel--taxonomy" in navbar_styles
            and "inset-inline: 16px" in navbar_styles,
            "compact taxonomy cloud is no longer constrained to the viewport", errors)
    require("&__column" in footer_styles and "padding-inline-start: 10px" in footer_styles,
            "fat-footer navigation columns lost their start padding", errors)
    require(all(marker in feedback for marker in (
                'data-td-feedback-choice="solved"',
                'data-td-feedback-choice="not_solved"',
                "data-td-feedback-reason",
                "data-td-feedback-change",
                'href="#td-comments"',
            )) and "textarea" not in feedback and "data-endpoint" not in feedback,
            "feedback is no longer the one-click structured contract", errors)
    require(all(marker in feedback_js for marker in (
                "docs_feedback",
                "page_path",
                "language",
                "refinement: true",
            )) and "fetch(" not in feedback_js and "message" not in feedback_js,
            "feedback runtime collects more than structured analytics", errors)
    require('id="td-comments"' in giscus,
            "detailed feedback no longer has a stable Giscus target", errors)
    require("key === 'l' || key === 'y'" in keyboard,
            "y is no longer the l language alias", errors)
    for marker in (
        "offlineSearchOnServe",
        "navbar_autohide",
        "docs_feedback",
        "page-annotation.html",
        "endpoint",
        "Giscus",
    ):
        require(marker in migration_en and marker in migration_zh,
                f"bilingual PRD 7 migration guidance lacks {marker}", errors)
    return errors


def build_example(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-prd7-") as temporary:
        public = Path(temporary) / "public"
        env = os.environ.copy()
        env.update({
            "HUGO_ENABLEGITINFO": "true",
            "HUGO_PARAMS_UI_FEEDBACK_ENABLE": "true",
        })
        result = subprocess.run(
            [hugo, "--source", str(ROOT / "exampleSite"), "--themesDir", str(ROOT.parent),
             "--destination", str(public), "--panicOnWarning"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            return ["PRD 7 fixture failed to build:\n" + result.stdout + result.stderr]
        page = public / "docs/content-primitives/index.html"
        require(page.is_file(), "feedback fixture page is missing", errors)
        if page.is_file():
            source = page.read_text()
            for marker in (
                'data-page-path="/docs/content-primitives/"',
                'data-language="en"',
                'data-td-feedback-choice="solved"',
                'data-td-feedback-choice="not_solved"',
                'data-td-feedback-reason="missing_info"',
                "data-td-feedback-result",
                "data-td-feedback-change",
                "data-td-page-annotation",
                "data-td-pager",
            ):
                require(marker in source, f"rendered PRD 7 page lacks {marker}", errors)
            require("data-td-feedback-message" not in source
                    and "data-td-feedback-submit" not in source
                    and "data-endpoint=" not in source,
                    "rendered feedback still exposes a form or endpoint", errors)
            rendered_order = [
                source.find("data-td-feedback"),
                source.find("data-td-page-annotation"),
                source.find("data-td-pager"),
            ]
            require(
                all(index >= 0 for index in rendered_order)
                and rendered_order == sorted(rendered_order),
                "rendered feedback/annotation/pager order drifted",
                errors,
            )
            scripts = re.findall(r'<script\b[^>]*\bsrc="([^"]+\.js)"', source)
            bundles = []
            for script in scripts:
                relative = re.sub(r"^https?://[^/]+", "", script).split("?", 1)[0]
                asset = public / relative.lstrip("/")
                if asset.is_file():
                    bundles.append(asset.read_text())
            require(any("OinkFeedback" in bundle for bundle in bundles),
                    "feedback runtime is absent from the rendered bundle", errors)
            tree_start = source.find('id="td-sidebar-menu"')
            tree_end = source.find("</nav>", tree_start)
            tree = source[tree_start:tree_end]
            first_tree_link = re.search(
                r'<a href="([^"]+)"[^>]*\bclass="td-shell-tree__link(?: active)?"',
                tree,
            )
            require(first_tree_link is not None and first_tree_link.group(1) == "/docs/",
                    "rendered Docs tree does not start with its root landing", errors)
            require('class="td-shell-sidebar__brand-row"' in source,
                    "rendered sidebar lost its identity row", errors)
            require('class="td-shell-iconbtn td-shell-sidebar__search"' in source
                    and 'class="td-shell-sidebar__footer"' in source
                    and 'class="td-shell-keyboard nav-hover-menu"' in source,
                    "rendered sidebar lost its search action or bottom utility dock", errors)
            require('aria-label="breadcrumb"' in source,
                    "nested documentation page lost its breadcrumb", errors)
            require('class="td-shell-root__item' in source and 'href="/blog/"' in source,
                    "rendered root switcher is not global", errors)

        blog = public / "blog/index.html"
        require(blog.is_file(), "blog root fixture is missing", errors)
        if blog.is_file():
            blog_source = blog.read_text()
            require('data-td-pager-next' in blog_source,
                    "blog root does not page to its first child", errors)
            require('data-td-page-annotation' in blog_source,
                    "blog root bypasses the page-end annotation", errors)
            require('aria-label="breadcrumb"' not in blog_source
                    and 'data-td-page-actions' in blog_source
                    and 'td-shell-topline--actions-only' in blog_source,
                    "blog root did not hide its breadcrumb while retaining actions", errors)

        docs = public / "docs/index.html"
        require(docs.is_file(), "docs root fixture is missing", errors)
        if docs.is_file():
            docs_source = docs.read_text()
            require('aria-label="breadcrumb"' not in docs_source
                    and 'data-td-page-actions' in docs_source
                    and 'td-shell-topline--actions-only' in docs_source,
                    "docs root did not hide its breadcrumb while retaining actions", errors)
    return errors


def build_self_root_fixture(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-prd7-self-root-") as temporary:
        root = Path(temporary)
        source = root / "site"
        public = root / "public"
        (source / "content/docs/manual").mkdir(parents=True)
        (source / "content/docs/legacy").mkdir(parents=True)
        (source / "hugo.yaml").write_text(
            f"""baseURL: https://example.org/
title: Self-root fixture
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
params:
  offlineSearch: false
  ui:
    shell_types: [docs]
    sidebar_root_menu: true
""",
            encoding="utf-8",
        )
        (source / "content/docs/_index.md").write_text(
            "---\ntitle: Docs\ntype: docs\ncascade:\n  type: docs\n---\n",
            encoding="utf-8",
        )
        (source / "content/docs/manual/_index.md").write_text(
            "---\ntitle: Manual\nsidebar_root_for: self\n---\n\nManual root.\n",
            encoding="utf-8",
        )
        (source / "content/docs/manual/start.md").write_text(
            "---\ntitle: Start\n---\n\nStart.\n",
            encoding="utf-8",
        )
        (source / "content/docs/legacy/_index.md").write_text(
            "---\ntitle: Legacy\nsidebar_root_for: self\nsidebar_root_link_self: false\n---\n\nLegacy root.\n",
            encoding="utf-8",
        )
        (source / "content/docs/legacy/start.md").write_text(
            "---\ntitle: Legacy start\n---\n\nLegacy start.\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
             "--destination", str(public), "--panicOnWarning"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            return ["PRD 7 self-root fixture failed to build:\n" + result.stdout + result.stderr]

        cases = {
            "manual": "/docs/manual/",
            "legacy": "/docs/",
        }
        for name, expected in cases.items():
            output = public / f"docs/{name}/start/index.html"
            require(output.is_file(), f"{name} self-root fixture page is missing", errors)
            if not output.is_file():
                continue
            html = output.read_text(encoding="utf-8")
            tree_start = html.find('id="td-sidebar-menu"')
            tree_end = html.find("</nav>", tree_start)
            first = re.search(
                r'<a href="([^"]+)"[^>]*\bclass="td-shell-tree__link(?: active)?"',
                html[tree_start:tree_end],
            )
            require(first is not None and first.group(1) == expected,
                    f"{name} self-root first link is not {expected}", errors)
            if name == "manual":
                prev = re.search(r'<a class="td-pager__card td-pager__card--prev" href="([^"]+)"', html)
                require(prev is not None and prev.group(1) == expected,
                        "default self-root pager does not return to its own landing", errors)
    return errors


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()
    errors = check_sources() + build_example(args.hugo) + build_self_root_fixture(args.hugo)
    if errors:
        print("PRD 7 checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("PRD 7 navigation and page-end checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
