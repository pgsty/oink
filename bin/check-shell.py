#!/usr/bin/env python3
"""Verify the navigation, page-end, and feedback contracts."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

from test_site import fixture_config_args
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
    sidebar_node = (ROOT / "layouts/_partials/shell/sidebar-node.html").read_text()
    page_end = (ROOT / "layouts/_partials/page-end.html").read_text()
    annotation = (ROOT / "layouts/_partials/page-annotation.html").read_text()
    pager = (ROOT / "layouts/_partials/pager.html").read_text()
    pager_styles = (ROOT / "assets/scss/td/_pager.scss").read_text()
    content_styles = (ROOT / "assets/scss/td/_content.scss").read_text()
    comments_styles = (ROOT / "assets/scss/td/_giscus.scss").read_text()
    blog_list = (ROOT / "layouts/blog/list.html").read_text()
    blog_card = (ROOT / "layouts/_partials/shell/blog-card.html").read_text()
    blog_styles = (ROOT / "assets/scss/td/shell/_blog.scss").read_text()
    page_context_styles = (ROOT / "assets/scss/td/shell/_page-context.scss").read_text()
    breadcrumb_state = (ROOT / "layouts/_partials/shell/breadcrumb-enabled.html").read_text()
    sidebar_panel = (ROOT / "layouts/_partials/shell/sidebar-panel.html").read_text()
    footer_line = (ROOT / "layouts/_partials/shell/footer-line.html").read_text()
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
    navbar_groups = (ROOT / "layouts/_partials/navbar-group-items.html").read_text()
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

    for marker in ("Home.Sections.ByWeight", 'Params.sidebar_root_for', "sidebar_root_menu"):
        require(marker in root_roots, f"root set lost {marker}", errors)
    require('partial "shell/sidebar-root.html"' in root_entries
            and 'partialCached "shell/root-menu-roots.html"' in root_entries,
            "root set lost page resolution or site-level caching", errors)
    require('eq (len $entries) 1' in root_menu and "td-shell-root--static" in root_menu,
            "one-root switcher is not a static link", errors)
    require("td-shell-tree__item--rootless" not in sidebar_node,
            "generic sidebar still removes its root row", errors)
    require('isset $s.Params "sidebar_root_link_self"' in sidebar_node
            and '"front matter sidebar_root_link_self must be a boolean' in sidebar_node
            and "$rootLinkSelf := true" in sidebar_node,
            "self-root links do not default to their own landing with an explicit legacy escape", errors)
    require('"node" (dict "page" $sidebarRootURL' in docs_tree,
            "explicit docs sidebar does not prepend a missing root row", errors)
    require("continue" not in docs_tree.split('index $docsNav "sections"', 1)[1].split("partial", 1)[0],
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

    # Two text links, title only: "← previous" at the start, "next →" at the
    # end, each capped at half the row and truncated with an ellipsis.
    require("td-pager__summary" not in pager and "td-pager__card" not in pager,
            "pager regressed to description cards", errors)
    require('class="td-pager__link td-pager__link--prev"' in pager
            and 'class="td-pager__link td-pager__link--next"' in pager
            and 'title="{{ .LinkTitle }}"' in pager
            and pager.count("td-pager__arrow") == 2,
            "pager links lost their arrow/title/full-title structure", errors)
    require("max-width: calc(50% - 0.5rem)" in pager_styles
            and "text-overflow: ellipsis" in pager_styles
            and "white-space: nowrap" in pager_styles
            and "&__link--prev {\n    margin-inline-end: auto;" in pager_styles
            and "&__link--next {\n    margin-inline-start: auto;" in pager_styles
            and "font-family: var(--td-body-font-family)" in pager_styles,
            "pager links no longer cap at half width, truncate, or keep their own edge", errors)
    require(".td-page-end > .td-pager:first-child" in pager_styles,
            "a pager that opens the page end lost its separating rule", errors)
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
    footer_order = [
        footer_line.index('partial "navbar-version-selector.html"'),
        footer_line.index('partial "language-selector.html"'),
        footer_line.index("td-shell-footline__theme"),
        footer_line.index('partial "shell/keyboard-help.html"'),
        footer_line.index("td-shell-footline__toggle"),
    ]
    require(footer_order == sorted(footer_order),
            "bottom bar order is not version/language/theme/help/collapse", errors)
    require("td-shell-sidebar__footer" not in sidebar_panel
            and "td-shell-sidebar__footer" not in sidebar_styles
            and 'aria-label="GitHub"' not in footer_line,
            "sidebar or bottom bar still carries the retired utility/GitHub dock", errors)
    require('"dropup" true "iconOnly" true' in footer_line
            and "td-version-menu--icon-only" in version
            and "if not $iconOnly" in version
            and ".td-version-menu--icon-only" in (ROOT / "assets/scss/td/_version-selector.scss").read_text(),
            "bottom-bar version switcher exposes text or lost its dropup", errors)
    require('"icon" "shell"' in footer_line
            and '"mode" "list"' not in footer_line
            and ".td-shell-footline .td-language-selector--menu" in language_styles
            and "inset-inline-end: 0" in language_styles,
            "bottom-bar language control is expanded or no longer opens upward", errors)
    require("dropdown.show()" in base_js and "menu.addEventListener('pointerenter'" in base_js,
            "bottom-bar version menu no longer opens on pointer hover", errors)
    require(all(f'data-bs-theme-value="{value}"' in footer_line
                for value in ("light", "dark", "auto"))
            and "data-td-nav-hover" in footer_line
            and ".td-shell-footline__right" in footer_styles
            and "bottom: calc(100% + 8px)" in footer_styles,
            "bottom-bar theme trigger no longer exposes its upward three-mode menu", errors)
    stacked_footline = layout_styles.split(".td-shell-footline", 1)[1].split(
        "/* --------------------------------------------------------- mobile subnav */", 1
    )[0].split("@include media-breakpoint-down(lg)", 1)
    require(len(stacked_footline) == 2
            and "&__right" in stacked_footline[1]
            and "justify-content: center" in stacked_footline[1],
            "stacked bottom bar no longer centers its rows below lg", errors)
    require('data-td-nav-hover-open' in keyboard_help
            and 'class="td-kbd-sequence"' in keyboard_help
            and all(key in keyboard_help for key in ('<kbd>W</kbd>', '<kbd>/</kbd>', '<kbd>H</kbd>'))
            and ".td-shell-keyboard-help__row" in keyboard_styles
            and ".td-shell-footline .td-shell-keyboard" in keyboard_styles
            and "position: static" in keyboard_styles
            and "width: unquote('min(21rem, calc(100vw - 2rem))')" in keyboard_styles
            and "inset-inline-start: auto" in keyboard_styles
            and "inset-inline-end: 1rem" in keyboard_styles,
            "bottom-bar shortcut help lost its compact viewport-bound card or KBD cheat sheet", errors)
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
            and ".td-site-header .td-nav-menu-zone" in navbar_styles
            and "margin-inline-start: auto" not in navbar_styles,
            "compact navbar no longer true-centers its generated menu", errors)
    require("> .td-nav-version-menu" in navbar_styles
            and "> .td-nav-theme-menu" in navbar_styles
            and "> .td-nav-github" in navbar_styles
            and ".td-site-header .td-site-drawer-toggle {\n    display: inline-flex;\n  }"
            in navbar_styles,
            "phone navbar no longer reduces its utility edge to search and a drawer entry", errors)
    require(".td-nav-alt-site > span" in navbar_styles
            and ".td-nav-github .td-nav-count" in navbar_styles
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
    entry_link = (ROOT / "layouts/_partials/navbar-entry-link.html").read_text()
    require("columns must be an integer from 1 to 4" in navbar_item
            and "td-nav-menu__panel--mega" in navbar_item
            and "data-td-navbar-columns" in navbar_item,
            "configured navbar columns no longer render a validated mega panel", errors)
    require("showDescription" in entry_link
            and "td-navbar-entry__description" in entry_link
            and "showDescription" in navbar_groups,
            "configured navbar columns no longer project child descriptions", errors)
    require(".td-nav-menu__panel--mega" in navbar_styles
            and ".td-navbar-entry__description" in navbar_styles,
            "navbar mega-panel styles are missing", errors)
    require(".ByCount" in taxonomy and "td-navbar-taxonomy-tag__count" in taxonomy,
            "taxonomy panel lost count-descending tag chips", errors)
    require("flex-wrap: wrap" in navbar_styles and "flex-wrap: wrap" in blog_styles,
            "navbar or right-rail taxonomy terms are no longer tag clouds", errors)
    require(".td-nav-menu__panel--taxonomy" in navbar_styles
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
    # Blog form and width remain page-overridable parameters.
    require('partial "ui-param.html" (dict "page" . "key" "blog_index")' in blog_list
            and 'partial "ui-param.html" (dict "page" . "key" "blog_index_columns")' in blog_list,
            "blog index form or column count is not a ui-param with a front matter override", errors)
    require('"allowed" (slice "list" "cards" "table")' in blog_list
            and '"key" "params.ui.blog_index"' in blog_list
            and '"fallback" "list"' in blog_list,
            "blog index form is not validated against its enum with a documented fallback", errors)

    # The switch renders every form and records the published default.
    gate = (ROOT / "layouts/_partials/shell/blog-index-toggle.html").read_text()
    title_menu_source = (ROOT / "layouts/_partials/actions/title-menu.html").read_text()
    prepaint = (ROOT / "layouts/_partials/shell/prepaint.html").read_text()
    shell_js = (ROOT / "assets/js/docs-shell.js").read_text()
    require('"key" "params.ui.blog_index_toggle"' in gate and '"fallback" false' in gate,
            "the index switch is not an opt-in parameter with a documented fallback", errors)
    require('eq $page.Kind "section"' in gate and "not $page.Layout" in gate,
            "the index switch is offered where blog/list.html does not render", errors)
    require('data-td-blog-form="cards"' in blog_list and 'data-td-blog-form="list"' in blog_list
            and 'data-td-blog-form="table"' in blog_list
            and 'data-td-blog-default="{{ $mode }}"' in blog_list
            and 'or (eq $mode "cards") $toggle' in blog_list
            and 'or (eq $mode "list") $toggle' in blog_list
            and 'or (eq $mode "table") $toggle' in blog_list
            and 'or (ne $mode "table") $toggle' in blog_list,
            "the index does not render every form for the switch, or lost its published default", errors)
    require("$tablePages = $pager.Pages" in blog_list
            and "PageGroups" not in blog_list,
            "toggle mode no longer limits the table to the current pager slice, "
            "or the flat list regrew year groups", errors)
    require(title_menu_source.index("data-td-blog-index-toggle")
            < title_menu_source.index('title="RSS"'),
            "the index switch is no longer left of the feed button", errors)
    require("hidden" in title_menu_source.split("data-td-blog-index-toggle")[0].rsplit("<button", 1)[-1],
            "the index switch is not hidden until the runtime reveals it", errors)
    require("td-blog-index" in prepaint,
            "the reader's index form is not restored before the first paint", errors)
    require("data-td-blog-index-toggle" in shell_js and "toggle.hidden = false" in shell_js
            and "['list', 'cards', 'table']" in shell_js,
            "the shell runtime does not claim the index switch or lost its cycle order", errors)
    require('class="td-content-cards td-blog-cards"' in blog_list
            and "--td-card-columns:" in blog_list,
            "blog card index does not reuse the shared card grid", errors)
    require('.Fill "640x360 Center"' in blog_card
            and "reflect.IsImageResourceProcessable" in blog_card,
            "blog card does not put a processable lead image through Hugo", errors)
    require('target="_blank"' in blog_card and 'rel="noopener"' in blog_card
            and "fa-arrow-up-right-from-square" in blog_card,
            "blog card lost the external semantics of manual_link", errors)
    require("figcaption" not in blog_card and 'alt=""' in blog_card,
            "blog card carries a byline or names an image the title already names", errors)
    # A card reads the meta sentence -- date, author, word count, minutes --
    # then terms, then the description, in that order.
    require('"authors" false' not in blog_card,
            "the card meta line no longer names the author", errors)
    require('"length" false' not in blog_card,
            "the card meta line dropped the word count and minutes", errors)
    # Terms cover every taxonomy except authors, whom the sentence above the
    # badges already names.
    require('shell/blog-terms.html' in blog_card
            and '"exclude" (slice "authors")' in blog_card
            and "td-blog-card__tags" in blog_card,
            "the card no longer offers every taxonomy's terms minus authors", errors)
    require(0 <= blog_card.find('shell/blog-meta.html')
            < blog_card.find("td-blog-card__tags")
            < blog_card.find("td-blog-card__summary"),
            "the card order is no longer date, tags, description", errors)
    require(".Description | default" in blog_card,
            "the card summarises the body where the author wrote a description", errors)
    require("min-block-size: calc(3 * 1.55em)" in blog_styles
            and "-webkit-line-clamp: 3" in blog_styles,
            "the card description no longer reserves its three lines", errors)
    require('"key" "blog_index_size"' in blog_list
            and "$blogPages.ByDate.Reverse) $size" in blog_list,
            "the blog index no longer passes its own pager size, which Hugo ignores from a theme", errors)
    require("td-blog-cards" in blog_styles
            and "aspect-ratio: 16 / 9" in blog_styles
            and "-webkit-line-clamp: 3" in blog_styles
            and "overflow-wrap: anywhere" in blog_styles
            and "forced-colors: active" in blog_styles,
            "blog card styles lost the grid, the 16:9 frame, the clamp, or forced colours", errors)

    # The legacy author string remains Markdown-capable.
    byline = (ROOT / "layouts/_partials/byline.html").read_text()
    article = (ROOT / "layouts/blog/_td-content.html").read_text()
    resolve = (ROOT / "layouts/_partials/authors-resolve.html").read_text()
    rss = (ROOT / "layouts/blog/rss.xml").read_text()
    chips = (ROOT / "layouts/_partials/taxonomy-terms-article-wrapper.html").read_text()
    label = (ROOT / "layouts/_partials/taxonomy-label.html").read_text()
    require('{{- partial "byline.html" (dict "page" .) }}' in article
            and "td-byline" not in article,
            "the blog article head no longer routes its byline through one renderer", errors)
    require('{{- with $page.Params.author }}' in byline
            and '<b>{{ . | markdownify }}</b>' in byline
            and '<div class="td-byline mb-4">' in byline,
            "the 0.4 author string branch is no longer reproduced verbatim", errors)
    # The article head is title, description, one line of facts, then the
    # people: the date lives in the info line, so the byline carries none.
    info = (ROOT / "layouts/_partials/article-info.html").read_text()
    require('{{- partial "article-info.html" (dict "page" .) }}' in article
            and article.index('partial "article-info.html"')
            < article.index("</header>")
            < article.index('partial "byline.html"')
            < article.index('partial "series-strip.html"')
            < article.index('"lead"'),
            "the article head lost its info line, chips, byline, series, lead order", errors)
    require("<time" not in byline,
            "the byline repeats the date the info line already carries", errors)
    require('partial "reading-time-enabled.html"' in info
            and "post_word_count" in info and "post_read_original" in info,
            "the info line's length segments are not behind the reading_time switch", errors)
    require('partial "content/url.html"' in info
            and 'target="_blank" rel="noopener noreferrer"' in info,
            "the info line's original link bypasses the shared URL policy "
            "or its external-link attributes", errors)
    require('isset .Site.Taxonomies "authors"' in resolve
            and '.GetTerms "authors"' in resolve,
            "author resolution is not gated on the site's own taxonomy declaration", errors)
    body = resolve.split("*/ -}}", 1)[-1]
    require('ui-param.html' not in body and ".Params." not in body,
            "author resolution grew a theme parameter; the taxonomy is the whole switch", errors)
    explicit = chips.split("page_header -}}", 1)[-1].split("{{ else -}}", 1)[0]
    require('$reserved := slice "authors" "series"' in chips
            and chips.count("if not (in $reserved $taxo)") == 2
            and "$reserved" not in explicit,
            "the reserved plurals are not excluded from exactly the two default chip paths "
            "(an explicitly configured page_header must still render them)",
            errors)
    require('"author" "ui_author_title"' in label and '"authors" "ui_authors_title"' in label,
            "the taxonomy label dictionary lost its author entries", errors)
    require('xmlns:dc="http://purl.org/dc/elements/1.1/"' in rss
            and "<dc:creator>" in rss
            and "managingEditor" in rss,
            "the blog feed lost per-item dc:creator or its site-level editor", errors)
    share_items = (ROOT / "layouts/_partials/share/items.html").read_text()
    share_bar = (ROOT / "layouts/_partials/share/bar.html").read_text()
    share_styles = (ROOT / "assets/scss/td/_share.scss").read_text()
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

    for marker in ("Home.Sections.ByWeight", 'Params.sidebar_root_for', "sidebar_root_menu"):
        require(marker in root_roots, f"root set lost {marker}", errors)
    require('partial "shell/sidebar-root.html"' in root_entries
            and 'partialCached "shell/root-menu-roots.html"' in root_entries,
            "root set lost page resolution or site-level caching", errors)
    require('eq (len $entries) 1' in root_menu and "td-shell-root--static" in root_menu,
            "one-root switcher is not a static link", errors)
    require("td-shell-tree__item--rootless" not in sidebar_node,
            "generic sidebar still removes its root row", errors)
    require('isset $s.Params "sidebar_root_link_self"' in sidebar_node
            and '"front matter sidebar_root_link_self must be a boolean' in sidebar_node
            and "$rootLinkSelf := true" in sidebar_node,
            "self-root links do not default to their own landing with an explicit legacy escape", errors)
    require('"node" (dict "page" $sidebarRootURL' in docs_tree,
            "explicit docs sidebar does not prepend a missing root row", errors)
    require("continue" not in docs_tree.split('index $docsNav "sections"', 1)[1].split("partial", 1)[0],
            "docs sidebar still skips its root row", errors)

    order = [
        page_end.index('partial "share/bar.html"'),
        page_end.index('partial "feedback.html"'),
        page_end.index('partial "page-annotation.html"'),
        page_end.index('partial "pager.html"'),
        page_end.index('partial "comments.html"'),
    ]
    require(order == sorted(order), "page-end component order drifted", errors)

    # The share bar is the one page-end block that points outward, so its
    # contract is what it may *not* do: it emits plain links and one local
    # copy button, and it leaves every non-HTML output alone.
    require('partial "share/items.html"' in share_bar,
            "share bar no longer renders the resolved descriptors", errors)
    require('$page.IsPage' in share_items and 'reflect.IsSlice' in share_items
            and 'warnf "invalid params.ui.share entry %q' in share_items
            and "dropping it" in share_items,
            "share targets are no longer a validated list on regular pages only", errors)
    for marker in ("<iframe", "<script", "<img", "<link", "resources.GetRemote"):
        require(marker.lower() not in (share_items + share_bar).lower(),
                f"share bar emits or fetches {marker}", errors)
    templates = re.findall(r'"template" "([^"]*)"', share_items)
    require(len(templates) == 16 and all(
                target.startswith(("https://", "mailto:")) or target == ""
                for target in templates),
            "a share target is not a plain https/mailto intent link", errors)
    # Discord has no share-intent endpoint. Anything claiming to be one would be
    # a guess at a private scheme, so the absence is part of the contract.
    require('"discord"' not in share_items,
            "the share catalog gained a Discord target, which has no intent URL", errors)
    require('target="_blank" rel="noopener noreferrer"' in share_bar,
            "share links lost their external-link attributes", errors)
    require(share_bar.count('aria-label="{{ .label }}"') == 2
            and 'aria-hidden="true"' in share_bar,
            "share controls no longer name themselves for assistive technology", errors)
    # The row is glyphs alone: no visible heading, and the name it drops lives
    # on the group instead, so the bar is still announced as Share.
    require("td-share__label" not in share_bar and "<h2" not in share_bar
            and 'role="group" aria-label="{{ T "ui_share" }}"' in share_bar,
            "the share row grew a visible heading or lost its group name", errors)
    require("justify-content: center" in share_styles
            and "border-block-start" not in share_styles,
            "the share row is no longer a centred row without a rule of its own", errors)
    require('class="td-share d-print-none"' in share_bar
            and 'eq $format "html"' in share_bar,
            "share bar is no longer confined to the interactive HTML output", errors)
    require('data-td-action="{{ .action }}"' in share_bar
            and "data-td-page-context" in share_bar
            and "data-td-page-context-status" in share_bar,
            "share copy control is no longer a registry action with its own live region", errors)
    require("min-height: 44px" in share_styles and "forced-colors" in share_styles
            and "margin-inline" not in share_styles and "padding-left" not in share_styles,
            "share controls lost their touch target, forced-colors, or logical properties", errors)
    errors += check_featured_image_sources()
    errors.extend(check_series_sources())
    return errors


def check_featured_image_sources() -> list[str]:
    """The article-level featured image: one caller set, one resolver, no runtime."""
    errors: list[str] = []
    mode = (ROOT / "layouts/_partials/featured-image-mode.html").read_text()
    article = (ROOT / "layouts/_partials/featured-image-article.html").read_text()
    styles = (ROOT / "assets/scss/td/shell/_featured.scss").read_text()
    config = (ROOT / "hugo.yaml").read_text()

    require("featured_image: none" in config,
            "hugo.yaml no longer declares the params.ui.featured_image default", errors)
    require('partial "ui-param.html" (dict "page" . "key" "featured_image")' in mode,
            "featured_image no longer resolves through ui-param.html, so front matter cannot override it", errors)
    require('"allowed" (slice "none" "banner" "wash" "hero")' in mode
            and '"key" "params.ui.featured_image"' in mode
            and '"fallback" "none"' in mode,
            "an invalid featured_image mode no longer warns and falls back to none", errors)
    require('.Store.Get "tdOutputFormat"' in mode and '"html"' in mode,
            "the featured image is no longer guarded to HTML output", errors)
    require('partialCached "featured-image-resolve.html"' in mode
            and 'partialCached "featured-image-resolve.html"' in article,
            "the article image no longer comes from the shared resolver", errors)

    # One caller set. The partials render blog-family pages and nothing else;
    # a docs or Book page reaching them would make the parameter mean two
    # things. The blog baseof is in the set because the hero is the shell's
    # backdrop -- painted for single pages and section indexes alike --
    # rather than part of the content column.
    callers = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.glob("layouts/**/*.html")
        for name in ("featured-image-mode.html", "featured-image-article.html")
        if f'partial "{name}"' in path.read_text()
    }
    require(callers == {"layouts/blog/_td-content.html",
                        "layouts/blog/baseof.html"},
            f"the featured image is called from {sorted(callers)}, "
            "not the blog content template and the blog baseof", errors)
    td_content = (ROOT / "layouts/blog/_td-content.html").read_text()
    require(0 <= td_content.find('partial "featured-image-mode.html"')
            < td_content.find('partial "featured-image-article.html"')
            < td_content.find('partial "page-title.html"'),
            "the featured image no longer resolves and renders before the page title", errors)
    require('<div class="td-article-header td-article-header--wash">' in td_content
            and td_content.count('{{ if eq $featured "wash" }}') == 2,
            "the wash header wrapper is no longer emitted only in wash mode", errors)
    baseof = (ROOT / "layouts/blog/baseof.html").read_text()
    require('"mode" "hero"' in baseof
            and '{{ $hero := eq $featured "hero" -}}' in baseof
            and "td-shell-chrome--hero" in baseof
            and "and $navbar (not $hero)" in baseof,
            "the blog baseof no longer paints the hero as the height-free immersive backdrop", errors)
    require("td-shell-layout--hero" in baseof
            and "td-shell-layout--toc-flow" in baseof,
            "the blog baseof no longer emits the immersive layout modifiers", errors)
    # The immersive rail is parameters, not a shell: the clouds opt-out can
    # empty the rail entirely, and the flow style is a validated enum that is
    # deliberately independent of whether a page carries an image.
    rail = (ROOT / "layouts/_partials/shell/toc-aside.html").read_text()
    require('"key" "params.ui.toc_taxonomies"' in rail
            and "if or $hasToc $clouds" in rail,
            "the taxonomy clouds are no longer an opt-out that can empty the rail", errors)
    toc_style = (ROOT / "layouts/_partials/shell/toc-style.html").read_text()
    require('"allowed" (slice "fixed" "flow")' in toc_style
            and '"fallback" "fixed"' in toc_style
            and '"key" "params.ui.toc_style"' in toc_style,
            "toc_style is not a validated fixed|flow enum", errors)

    require('class="td-featured-banner"' in article and 'class="td-featured-wash"' in article
            and 'class="td-featured-hero"' in article,
            "the article featured image lost one of its three modes", errors)
    require(article.count('aria-hidden="true"') == 2,
            "the wash or the hero is no longer hidden from assistive technology", errors)
    require(article.count('alt=""') == 3 and "loading=" not in article,
            "the article featured image is no longer decorative, or defers its own LCP element", errors)
    require('.Fill "1600x900 Center"' in article and '.Resize "1200x q60"' in article
            and '.Resize "1800x q70"' in article
            and "reflect.IsImageResourceProcessable" in article,
            "the article featured image no longer crops what Hugo can process", errors)
    require("hasImageZoom" not in article and "Store.Set" not in article
            and "Store.Set" not in mode,
            "the article featured image writes a Page Store flag", errors)

    require("--td-featured-wash-opacity" in styles and "aspect-ratio: 16 / 9" in styles
            and "--td-featured-hero-opacity" in styles,
            "the featured image styles lost an opacity token or the fixed banner frame", errors)
    require("@media (forced-colors: active)" in styles and "@media print" in styles
            and styles.count("display: none") >= 4,
            "the wash and the hero are not dropped in forced colors and in print", errors)
    # The overlay navbar cannot ask arbitrary artwork for text contrast: it
    # sits on a header-coloured scrim that fades out before the opening.
    require("var(--td-brand-header-bg) 58%" in styles
            and "transparent 100%" in styles,
            "the hero navbar overlay lost its readability scrim", errors)
    require("margin-inline" in styles and "padding-inline" in styles
            and "margin-left" not in styles and "padding-left" not in styles,
            "the featured image styles use physical instead of logical properties", errors)
    return errors


def check_series_sources() -> list[str]:
    """The series strip is one placement, one resolver, and no runtime."""

    errors: list[str] = []
    strip = (ROOT / "layouts/_partials/series-strip.html").read_text()
    order = (ROOT / "layouts/_partials/series-pages.html").read_text()
    article = (ROOT / "layouts/blog/_td-content.html").read_text()
    wrapper = (ROOT / "layouts/_partials/taxonomy-terms-article-wrapper.html").read_text()
    print_styles = (ROOT / "assets/scss/td/_print.scss").read_text()
    blog_styles = (ROOT / "assets/scss/td/shell/_blog.scss").read_text()

    # The strip belongs between the article's metadata row and its first
    # paragraph: after the meta header closes, before the content renders.
    placement = [
        article.index("</header>"),
        article.index('partial "series-strip.html"'),
        article.index('partial "content/render.html"'),
    ]
    require(placement == sorted(placement),
            "the series strip is no longer between the article meta row and the content", errors)

    # One resolver decides reading order; the strip and both term templates read
    # it, so they can never disagree about which article is part 2.
    require('partial "series-pages.html"' in strip,
            "the series strip resolves its own order instead of reusing series-pages.html", errors)
    for template in ("layouts/blog/term.html", "layouts/term.html"):
        source = (ROOT / template).read_text()
        require('partial "series-pages.html"' in source
                and 'eq .Data.Plural "series"' in source
                and ".Pages.ByDate.Reverse" in source,
                f"{template} no longer switches a series term to reading order", errors)
    require('where $pages "Params.series_weight"' in order
            and ".GroupByParam" not in order,
            "series reading order stopped reading the taxonomy weight from .Params", errors)

    # Zero JavaScript: a disclosure, not a widget. No page-store flag, no
    # bundle member, no behaviour attribute for a runtime to bind to.
    require("<details" in strip and "<summary" in strip,
            "the series list is no longer a plain disclosure", errors)
    require('<div class="td-series-strip__line">' in strip
            and strip.index('class="td-series-strip__name"') < strip.index("<details")
            and "<a " not in strip.split("<summary", 1)[1].split("</summary>", 1)[0],
            "the series term link is no longer a sibling of the disclosure", errors)
    require("data-td-" not in strip and "<script" not in strip and "Store.Set" not in strip,
            "the series strip grew a runtime hook", errors)
    require('aria-current="page"' in strip,
            "the series list no longer marks the reader's own place", errors)
    # Print keeps the strip and opens the disclosure through the existing rule.
    require("details:not([open]) > :not(summary)" in print_styles,
            "print no longer expands closed disclosures, so the series list would print collapsed", errors)
    require("d-print-none" not in strip,
            "the series strip hides itself from print", errors)
    require(".td-series-strip {" in blog_styles
            and "margin-block" in blog_styles
            and "padding-inline" in blog_styles
            and blog_styles.count("min-block-size: 24px") >= 2,
            "the series strip lost its own styles, logical properties, or minimum target sizes", errors)

    # Both taxonomies that carry a surface of their own stay out of the default
    # chips row; naming one in params.taxonomy.page_header still opts back in.
    require('$reserved := slice "authors" "series"' in wrapper
            and wrapper.count("in $reserved $taxo") == 2
            and "page_header" in wrapper,
            "the article chips row no longer reserves authors and series", errors)
    return errors


def build_example(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-shell-") as temporary:
        public = Path(temporary) / "public"
        env = os.environ.copy()
        env.update({
            "HUGO_ENABLEGITINFO": "true",
            # The regression fixture sets the boolean shorthand `ui.feedback: false`;
            # the override flips that scalar.
            "HUGO_PARAMS_UI_FEEDBACK": "true",
        })
        result = subprocess.run(
            [hugo, "--source", str(ROOT / "tests/site"), "--themesDir", str(ROOT.parent),
             "--destination", str(public), *fixture_config_args(), "--panicOnWarning"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            return ["fixture failed to build:\n" + result.stdout + result.stderr]
        page = public / "fixtures/content-primitives/index.html"
        require(page.is_file(), "feedback fixture page is missing", errors)
        if page.is_file():
            source = page.read_text()
            for marker in (
                'data-td-page-path="/fixtures/content-primitives/"',
                'data-td-language="en"',
                'data-td-feedback-choice="solved"',
                'data-td-feedback-choice="not_solved"',
                'data-td-feedback-reason="missing_info"',
                "data-td-feedback-result",
                "data-td-feedback-change",
                "data-td-page-annotation",
                "data-td-pager",
            ):
                require(marker in source, f"rendered page lacks {marker}", errors)
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
            require(first_tree_link is not None and first_tree_link.group(1) == "/fixtures/",
                    "rendered tree does not start with its root landing", errors)
            require('class="td-shell-sidebar__brand-row"' in source,
                    "rendered sidebar lost its identity row", errors)
            require('class="td-shell-iconbtn td-shell-sidebar__search"' in source
                    and 'class="td-shell-sidebar__footer"' not in source,
                    "rendered sidebar kept its utility dock or lost its search action", errors)
            footline = source.find('class="td-shell-footline d-print-none"')
            require(footline >= 0
                    and source.find("td-shell-footline__language", footline) >= 0
                    and source.find('class="td-shell-footline__theme', footline) >= 0
                    and source.find('class="td-shell-keyboard td-nav-hover-menu"', footline) >= 0,
                    "rendered bottom bar lost its language/theme/help controls", errors)
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
            require('td-byline' not in blog_source,
                    "the card index grew a byline it has no room for: image, title, "
                    "room for", errors)

        # The 0.4 string byline, rendered against a site that *does* declare the
        # taxonomy. Compared as an exact block, tabs included: the whole point
        # of the fixture is that this markup cannot drift.
        legacy = public / "blog/legacy-byline/index.html"
        require(legacy.is_file(), "legacy byline fixture page is missing", errors)
        if legacy.is_file():
            legacy_source = legacy.read_text()
            require(
                '\t<div class="td-byline mb-4">\n'
                '\t\t<b><a href="https://vonng.com">Ruohang Feng</a> '
                '(<a href="https://github.com/Vonng">@Vonng</a>) | '
                '<a href="https://vonng.com/wechat">WeChat</a></b>\n'
                '\t</div>' in legacy_source,
                "the 0.4 `author` string byline changed shape", errors)
            require("td-byline--authors" not in legacy_source,
                    "a page with no `authors` fell into the taxonomy byline", errors)

        # The info line's link to the original, from the same upstream_link the
        # annotation attributes; a page that names no upstream renders none.
        syndicated = public / "blog/upstream-info/index.html"
        require(syndicated.is_file(), "the syndicated info-line fixture is missing", errors)
        if syndicated.is_file():
            syndicated_source = syndicated.read_text()
            require('<a class="td-article-info__original" '
                    'href="https://example.org/original/" '
                    'target="_blank" rel="noopener noreferrer">' in syndicated_source
                    and "An upstream essay" in syndicated_source,
                    "upstream_link no longer renders both the info-line link "
                    "and the annotation attribution", errors)

        article = public / "blog/typography/index.html"
        require(article.is_file(), "authors byline fixture page is missing", errors)
        if article.is_file():
            article_source = article.read_text()
            # `authors: [oink, vonng]` -- GetTerms keeps the front matter
            # sequence, so the project author bylines first because the page
            # says so, not because of any sort.
            order = [article_source.find('href="/authors/oink/"'),
                     article_source.find('href="/authors/vonng/"')]
            require(all(index >= 0 for index in order) and order == sorted(order),
                    "the article byline does not follow the front matter author order", errors)
            require("taxo-authors" not in article_source,
                    "the reserved `authors` plural still renders a generic chip row", errors)

        # The avatar contract has two branches. Both public authors carry a
        # bundled portrait -- the person a processable JPEG, the project the
        # theme's own SVG mark -- and the initial fallback is pinned by the
        # fixture-only no-portrait author below.
        for slug, label in (("vonng", "Ruohang Feng"), ("oink", "Oink")):
            portrait = public / f"authors/{slug}/index.html"
            require(portrait.is_file(), f"author profile page is missing: {slug}", errors)
            if portrait.is_file():
                portrait_source = portrait.read_text()
                require(f'<h1 class="td-author-profile__name">{label}</h1>' in portrait_source
                        and 'class="td-author-profile__avatar"' in portrait_source
                        and "td-author-profile__avatar--placeholder" not in portrait_source
                        and 'class="td-blog-posts-list' in portrait_source,
                        f"the {slug} term page is not a portrait profile above its archive", errors)

        fallback = public / "authors/no-portrait/index.html"
        require(fallback.is_file(), "the no-portrait fixture profile is missing", errors)
        if fallback.is_file():
            fallback_source = fallback.read_text()
            require('td-author-profile__avatar--placeholder' in fallback_source,
                    "a profile without images lost the initial fallback", errors)

        feed = public / "blog/index.xml"
        require(feed.is_file(), "blog feed fixture is missing", errors)
        if feed.is_file():
            feed_source = feed.read_text()
            require('xmlns:dc="http://purl.org/dc/elements/1.1/"' in feed_source
                    and "<dc:creator>Ruohang Feng</dc:creator>" in feed_source
                    and "<dc:creator>Oink</dc:creator>" in feed_source,
                    "the blog feed lost its per-item dc:creator", errors)

        docs = public / "docs/index.html"
        require(docs.is_file(), "docs root fixture is missing", errors)
        if docs.is_file():
            docs_source = docs.read_text()
            require('aria-label="breadcrumb"' not in docs_source
                    and 'data-td-page-actions' in docs_source
                    and 'td-shell-topline--actions-only' in docs_source,
                    "docs root did not hide its breadcrumb while retaining actions", errors)

        errors += check_featured_image_output(public)
        errors += check_immersive_output(public)
    return errors


def build_footer_utilities_fixture(hugo: str) -> list[str]:
    """The slim footer owns the icon dock and the sidebar owns none of it."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-shell-footer-") as temporary:
        root = Path(temporary)
        source = root / "site"
        public = root / "public"
        (source / "content/docs").mkdir(parents=True)
        (source / "hugo.yaml").write_text(
            f"""baseURL: https://example.org/
title: Footer utilities fixture
theme: {ROOT.name}
defaultContentLanguage: en
disableKinds: [RSS, sitemap, taxonomy, term]
params:
  offline_search: false
  version: v1
  version_menu: Version 1
  versions:
    - {{name: Version 1, version: v1, url: https://v1.example.org}}
    - {{name: Version 2, version: v2, url: https://v2.example.org}}
  ui:
    footer_style: slim
    dark_mode: true
    shell_types: [docs]
languages:
  en:
    label: English
    weight: 1
  zh:
    label: 简体中文
    weight: 2
""",
            encoding="utf-8",
        )
        (source / "content/docs/_index.md").write_text(
            "---\ntitle: Docs\ntype: docs\n---\n\nBody.\n", encoding="utf-8"
        )
        (source / "content/docs/_index.zh.md").write_text(
            "---\ntitle: 文档\ntype: docs\n---\n\n正文。\n", encoding="utf-8"
        )

        result = subprocess.run(
            [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
             "--destination", str(public), "--panicOnWarning"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            return ["footer utilities fixture failed to build:\n" + result.stdout + result.stderr]

        output = public / "docs/index.html"
        require(output.is_file(), "footer utilities fixture page is missing", errors)
        if not output.is_file():
            return errors
        html = output.read_text(encoding="utf-8")
        require('class="td-shell-sidebar__footer"' not in html,
                "rendered sidebar still owns a utility dock", errors)
        start = html.find('class="td-shell-footline d-print-none"')
        end = html.find("</footer>", start)
        footline = html[start:end]
        markers = [
            "td-shell-footline__version",
            "td-shell-footline__language",
            "td-shell-footline__theme",
            "td-shell-keyboard td-nav-hover-menu",
        ]
        order = [footline.find(marker) for marker in markers]
        require(start >= 0 and end >= 0 and all(index >= 0 for index in order)
                and order == sorted(order),
                "rendered slim footer order is not version/language/theme/help", errors)
        version_start = footline.find("td-version-menu--icon-only")
        version_end = footline.find("</button>", version_start)
        version_trigger = footline[version_start:version_end]
        require("td-shell-icon--code-branch" in version_trigger
                and "td-version-menu__title-text" not in version_trigger,
                "rendered footer version trigger is not icon-only", errors)
        require('aria-label="GitHub"' not in footline
                and "td-shell-footline__toggle" not in footline,
                "slim footer gained GitHub or the fat-footer chevron", errors)
    return errors


def check_featured_image_output(public: Path) -> list[str]:
    """banner and wash render in HTML only, and only where they are asked for."""
    errors: list[str] = []
    surfaces = {
        "banner": public / "blog/featured-banner/index.html",
        "wash": public / "blog/featured-wash/index.html",
    }
    for mode, path in surfaces.items():
        require(path.is_file(), f"the {mode} featured-image fixture is missing", errors)
    if not all(path.is_file() for path in surfaces.values()):
        return errors

    banner = surfaces["banner"].read_text()
    wash = surfaces["wash"].read_text()
    require('<figure class="td-featured-banner">' in banner
            and 'alt="" width="1600" height="900"' in banner
            and "td-featured-banner__byline" in banner,
            "the banner fixture lost its framed decorative figure or its resource byline", errors)
    require("td-featured-wash" not in banner and "td-article-header--wash" not in banner,
            "the banner fixture also rendered a wash", errors)
    require(banner.find("td-featured-banner") < banner.find("td-page-heading"),
            "the banner does not precede the article title", errors)
    require('<div class="td-article-header td-article-header--wash">' in wash
            and '<div class="td-featured-wash" aria-hidden="true">' in wash
            and wash.find("td-featured-wash") < wash.find("td-page-heading"),
            "the wash fixture lost its hidden header layer", errors)
    require("td-featured-banner" not in wash,
            "the wash fixture also rendered a banner", errors)

    # An article that names no mode is exactly what it was before the feature.
    plain = public / "blog/typography/index.html"
    require(plain.is_file(), "the unset-parameter blog fixture is missing", errors)
    if plain.is_file():
        plain_source = plain.read_text()
        require("td-featured-" not in plain_source and "td-article-header" not in plain_source,
                "an article that sets no mode still renders a featured image", errors)

    # Print reaches the article through its own template and carries neither.
    for mode in surfaces:
        printed = public / f"_print/blog/featured-{mode}/index.html"
        require(printed.is_file(), f"the {mode} print surface is missing", errors)
        if printed.is_file():
            printed_source = printed.read_text()
            require("td-featured-" not in printed_source and "td-article-header" not in printed_source,
                    f"the {mode} print surface carries the article featured image", errors)
    return errors


def check_immersive_output(public: Path) -> list[str]:
    """The immersive blog recipe: hero opening, overlay navbar, bare rail."""
    errors: list[str] = []
    surfaces = {
        "hero": public / "blog/immersive-hero/index.html",
        "plain": public / "blog/immersive-plain/index.html",
    }
    for name, path in surfaces.items():
        require(path.is_file(), f"the immersive {name} fixture is missing", errors)
    if not all(path.is_file() for path in surfaces.values()):
        return errors

    hero = surfaces["hero"].read_text()
    plain = surfaces["plain"].read_text()

    # `featured_image: hero` paints the shell's own backdrop, before the main
    # column and processed by Hugo where it can be.
    require("td-shell-chrome--hero" in hero
            and '<div class="td-featured-hero" aria-hidden="true">' in hero
            and re.search(r'class="td-featured-hero"[^>]*><img src="[^"]*_hu[^"]*"', hero),
            "the immersive hero fixture lost its processed full-bleed backdrop", errors)
    require(hero.find("td-featured-hero") < hero.find("td-shell-main"),
            "the hero is no longer the shell's backdrop before the main column", errors)
    require("td-featured-banner" not in hero and "td-featured-wash" not in hero,
            "the immersive hero fixture also rendered a banner or a wash", errors)
    require("td-shell-layout--hero" in hero,
            "a hero page no longer reserves the breathing space above the opening", errors)
    # Over a hero the navbar is the transparent overlay: it renders, but the
    # body must not reserve height for a bar that scrolls away.
    require('class="td-site-header' in hero and "td-shell-chrome--navbar" not in hero,
            "the navbar over a hero is no longer the height-free overlay", errors)

    # No image, same recipe: the ordinary opening returns, the navbar goes
    # back to its sticky self, and the other keys hold on their own.
    require("td-shell-chrome--hero" not in plain and "td-featured-" not in plain
            and "td-shell-layout--hero" not in plain
            and "td-article-header" not in plain,
            "a recipe page with no image still renders a hero", errors)
    require('class="td-site-header' in plain and "td-shell-chrome--navbar" in plain,
            "a recipe page with no hero lost its ordinary sticky navbar", errors)
    for source_name, source in (("hero", hero), ("plain", plain)):
        require('id="td-shell-sidebar"' not in source
                and "td-shell-drawer-backdrop" not in source,
                f"the immersive {source_name} fixture grew a sidebar", errors)
        require("td-shell-tags-cloud" not in source,
                f"the immersive {source_name} fixture's rail carries taxonomy clouds", errors)
        require('aria-label="breadcrumb"' not in source
                and "td-shell-topline--actions-only" in source,
                f"the immersive {source_name} fixture regrew a breadcrumb "
                "over the blog shell's breadcrumb-free default", errors)
        require("td-shell-layout--toc-flow" in source
                and 'id="td-shell-aside-toc"' in source,
                f"the immersive {source_name} fixture lost its flow outline rail", errors)
        require("data-td-page-annotation" in source and "td-share" in source,
                f"the immersive {source_name} fixture bypasses the page end", errors)

    # The same recipe on a section index: the releases list opens under its
    # own hero, with neither sidebar nor clouds beside it.
    index = public / "blog/release/index.html"
    require(index.is_file(), "the immersive release index is missing", errors)
    if index.is_file():
        index_source = index.read_text()
        require("td-shell-chrome--hero" in index_source
                and "td-featured-hero" in index_source
                and 'id="td-shell-sidebar"' not in index_source
                and "td-shell-tags-cloud" not in index_source,
                "the release index no longer opens its list under the immersive hero", errors)

    # Print reaches these pages through their own template: no hero markers.
    for name in surfaces:
        printed = public / f"_print/blog/immersive-{name}/index.html"
        require(printed.is_file(), f"the immersive {name} print surface is missing", errors)
        if printed.is_file():
            printed_source = printed.read_text()
            require("td-featured-" not in printed_source
                    and "td-shell-chrome--hero" not in printed_source,
                    f"the immersive {name} print surface carries the hero", errors)
    return errors


def build_self_root_fixture(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-shell-self-root-") as temporary:
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
  offline_search: false
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
            return ["self-root fixture failed to build:\n" + result.stdout + result.stderr]

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
                prev = re.search(r'<a class="td-pager__link td-pager__link--prev" href="([^"]+)"', html)
                require(prev is not None and prev.group(1) == expected,
                        "default self-root pager does not return to its own landing", errors)
    return errors


def build_featured_image_rejection(hugo: str) -> list[str]:
    """An unknown mode warns, uses `none`, and fails strict publication."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-shell-featured-") as temporary:
        root = Path(temporary)
        source = root / "site"
        (source / "content/blog").mkdir(parents=True)
        (source / "hugo.yaml").write_text(
            f"""baseURL: https://example.org/
title: Featured image fixture
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
params:
  images: [/card.png]
  offline_search: false
  ui:
    featured_image: sideways
""",
            encoding="utf-8",
        )
        (source / "content/blog/_index.md").write_text(
            "---\ntitle: Blog\ntype: blog\ncascade:\n  type: blog\n  images: [/card.png]\n---\n",
            encoding="utf-8",
        )
        (source / "content/blog/post.md").write_text(
            "---\ntitle: Post\ndate: 2026-01-01\n---\n\nPost.\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
             "--destination", str(root / "public"), "--logLevel", "warn"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        output = result.stdout + result.stderr
        strict = subprocess.run(
            [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
             "--destination", str(root / "strict"), "--logLevel", "warn", "--panicOnWarning"],
            cwd=ROOT, text=True, capture_output=True,
        )
        require(result.returncode == 0,
                f"an invalid params.ui.featured_image stopped the build instead of warning: {output[-400:]}", errors)
        require("invalid params.ui.featured_image" in output
                and "none | banner | wash | hero" in output
                and "none" in output,
                f"the featured_image warning does not name the allowed modes and the fallback: {output[-400:]}", errors)
        require(strict.returncode != 0,
                "an invalid params.ui.featured_image survived --panicOnWarning", errors)
    return errors


def build_navbar_menu_columns(hugo: str) -> list[str]:
    """Explicit columns retain the multi-column panel and descriptions."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-shell-navbar-") as temporary:
        root = Path(temporary)
        source = root / "site"
        (source / "content/docs").mkdir(parents=True)
        (source / "hugo.yaml").write_text(
            f"""baseURL: https://example.org/
title: Navbar menu fixture
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
params:
  offline_search: false
menus:
  main:
    - identifier: docs
      name: Docs
      pageRef: /docs
      weight: 10
      params:
        columns: 2
    - identifier: docs-child
      parent: docs
      name: Child
      pageRef: /docs/child
      weight: 10
      params:
        icon: fa-solid fa-book
        description: A retained mega-menu description
""",
            encoding="utf-8",
        )
        (source / "content/docs/_index.md").write_text(
            "---\ntitle: Docs\n---\n", encoding="utf-8")
        (source / "content/docs/child.md").write_text(
            "---\ntitle: Child\ndate: 2026-01-01\n---\n\nChild.\n", encoding="utf-8")
        result = subprocess.run(
            [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
             "--destination", str(root / "public"), "--panicOnWarning"],
            cwd=ROOT, text=True, capture_output=True,
        )
        output = result.stdout + result.stderr
        require(result.returncode == 0,
                f"a valid menu columns value failed strict build: {output[-400:]}", errors)
        home = root / "public/index.html"
        if home.is_file():
            html = home.read_text(encoding="utf-8")
            require('class="td-nav-menu__panel td-nav-menu__panel--mega"' in html
                    and 'data-td-navbar-columns="2"' in html
                    and 'class="td-navbar-entry__description"' in html
                    and "A retained mega-menu description" in html,
                    "configured columns lost the mega panel or child description", errors)
    return errors


def build_blog_index_forms(hugo: str) -> list[str]:
    """Compare the three published forms and the paged reader toggle."""

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-blog-index-") as temporary:
        root = Path(temporary)
        rows_overlay = root / "rows.yaml"
        rows_overlay.write_text(
            "params:\n  ui:\n    blog_index: list\n    blog_index_toggle: false\n",
            encoding="utf-8",
        )
        overlay = root / "cards.yaml"
        overlay.write_text(
            "params:\n  ui:\n    blog_index: cards\n    blog_index_columns: 4\n"
            "    blog_index_toggle: false\n",
            encoding="utf-8",
        )
        table_overlay = root / "table.yaml"
        table_overlay.write_text(
            "params:\n  ui:\n    blog_index: table\n    blog_index_toggle: false\n",
            encoding="utf-8",
        )
        toggle_overlay = root / "toggle.yaml"
        toggle_overlay.write_text(
            "params:\n  ui:\n    blog_index: list\n    blog_index_size: 2\n"
            "    blog_index_toggle: true\n",
            encoding="utf-8",
        )
        rendered: dict[str, str] = {}
        for name, extra in (("rows", (rows_overlay,)), ("cards", (overlay,)),
                            ("table", (table_overlay,)), ("toggle", (toggle_overlay,))):
            public = root / name
            result = subprocess.run(
                [hugo, "--source", str(ROOT / "tests/site"), "--themesDir", str(ROOT.parent),
                 "--destination", str(public), *fixture_config_args(*extra), "--panicOnWarning"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            if result.returncode:
                return [f"blog index {name} form failed to build:\n" + result.stdout + result.stderr]
            index = public / "blog/oink/index.html"
            if not index.is_file():
                return [f"blog index {name} form did not render blog/oink/index.html"]
            rendered[name] = index.read_text(encoding="utf-8")

        rows, cards = rendered["rows"], rendered["cards"]
        row_links = re.findall(
            r'<li class="td-blog-posts-list__item">.*?<a href="([^"]+)"', rows, re.S)
        card_links = re.findall(
            r'<article class="td-content-card td-blog-card">.*?'
            r'<a class="td-content-card__title" href="([^"]+)"', cards, re.S)
        require(len(row_links) > 1, "the blog fixture no longer has posts to compare", errors)
        require(row_links == card_links,
                f"the cards index does not list the posts the row index lists: {row_links} vs {card_links}",
                errors)
        # The list is one flat run: no year headings in either form, in the
        # order the metadata line's own dates already tell. (The footer's own
        # bare <h2> column titles are not the posts region's.)
        year_heading = re.compile(r"<h2>[^<]*20\d\d</h2>")
        require(not year_heading.search(rows) and not year_heading.search(cards),
                "an index form regrew year headings", errors)
        require('class="td-content-cards td-blog-cards"' in cards
                and 'style="--td-card-columns: 4"' in cards,
                "the cards index does not reuse the shared grid at the configured width", errors)
        require("td-blog-posts-list__item" not in cards, "the cards index still renders rows", errors)
        require("td-blog-card" not in rows, "the row index leaked the card form", errors)
        require(('td-blog-posts__pagination' in rows) == ('td-blog-posts__pagination' in cards),
                "the two index forms disagree about pagination", errors)
        require('src=""' not in cards, "the cards index emitted an empty image source", errors)

        # A standalone table remains an unpaginated archive.
        table = rendered["table"]
        table_links = re.findall(
            r'<td class="td-blog-table__title"><a href="([^"]+)"', table)
        require(table_links == row_links,
                f"the table index does not list the posts the row index lists: {table_links}",
                errors)
        require("td-blog-posts__paged" not in table
                and "td-blog-posts__pagination" not in table
                and not year_heading.search(table),
                "the table form still carries year groups or pagination", errors)
        require('class="td-blog-table"' in table and "td-badge" in table,
                "the table form lost its structure or its tag badges", errors)
        require(not (root / "table/blog/oink/page").exists(),
                "a table-only index still generated pager pages", errors)

        # Toggle mode must not repeat the complete table on every pager page.
        toggle = rendered["toggle"]
        toggle_rows = re.findall(
            r'<li class="td-blog-posts-list__item">.*?<a href="([^"]+)"', toggle, re.S)
        toggle_cards = re.findall(
            r'<article class="td-content-card td-blog-card">.*?'
            r'<a class="td-content-card__title" href="([^"]+)"', toggle, re.S)
        toggle_table = re.findall(
            r'<td class="td-blog-table__title"><a href="([^"]+)"', toggle)
        require(toggle_rows == toggle_cards == toggle_table,
                "toggle forms do not share the first pager slice", errors)
        second_path = root / "toggle/blog/oink/page/2/index.html"
        require(second_path.is_file(), "toggle fixture did not generate a second page", errors)
        if second_path.is_file():
            second = second_path.read_text(encoding="utf-8")
            second_rows = re.findall(
                r'<li class="td-blog-posts-list__item">.*?<a href="([^"]+)"', second, re.S)
            second_table = re.findall(
                r'<td class="td-blog-table__title"><a href="([^"]+)"', second)
            require(second_rows == second_table,
                    "toggle forms do not share the second pager slice", errors)
            require(set(toggle_table).isdisjoint(second_table),
                    "toggle table repeats first-page posts on page two", errors)
    return errors


def build_blog_card_fixture(hugo: str) -> list[str]:
    """A card processes a bundled image, links out, and survives having none."""

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-blog-card-") as temporary:
        root = Path(temporary)
        source = root / "site"
        public = root / "public"
        (source / "content/blog/bundled").mkdir(parents=True)
        (source / "hugo.yaml").write_text(
            f"""baseURL: https://example.org/
title: Blog card fixture
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
params:
  offline_search: false
  ui:
    blog_index: cards
    blog_index_toggle: true
""",
            encoding="utf-8",
        )
        (source / "content/blog/_index.md").write_text(
            "---\ntitle: Blog\ntype: blog\ncascade:\n  type: blog\n---\n", encoding="utf-8")
        (source / "content/blog/bundled/index.md").write_text(
            "---\ntitle: Bundled\ndate: 2026-08-13\n---\n\nA post with its image beside it.\n",
            encoding="utf-8")
        shutil.copyfile(
            ROOT / "tests/site/content/fixtures/lists/shot-a.png",
            source / "content/blog/bundled/featured.png",
        )
        (source / "content/blog/external.md").write_text(
            "---\ntitle: External\ndate: 2026-08-12\n"
            "description: A post that lives somewhere else.\n"
            "manual_link: https://example.net/post/\n---\n\nBody.\n",
            encoding="utf-8")
        (source / "content/blog/plain.md").write_text(
            "---\ntitle: Plain\ndate: 2026-08-11\n---\n\nA post with no image at all.\n",
            encoding="utf-8")
        # The other way to have no image: a section cascades one and a page
        # turns it off. `images` is Hugo's key at every level, so an empty
        # list is the only opt-out a page has.
        (source / "content/blog/cleared").mkdir()
        (source / "content/blog/cleared/_index.md").write_text(
            "---\ntitle: Cleared\ncascade:\n  images: [/images/cascaded.png]\n---\n",
            encoding="utf-8")
        (source / "content/blog/cleared/post.md").write_text(
            "---\ntitle: Opted out\ndate: 2026-08-10\nimages: []\n---\n\nA post that turned its inherited image off.\n",
            encoding="utf-8")

        result = subprocess.run(
            [hugo, "--source", str(source), "--themesDir", str(ROOT.parent),
             "--destination", str(public), "--panicOnWarning"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            return ["blog card fixture failed to build:\n" + result.stdout + result.stderr]
        index = public / "blog/index.html"
        if not index.is_file():
            return ["blog card fixture did not render blog/index.html"]

        cards = [
            item.split("</article>", 1)[0]
            for item in index.read_text(encoding="utf-8").split(
                '<article class="td-content-card td-blog-card">')[1:]
        ]
        require(len(cards) == 4, f"the card fixture rendered {len(cards)} cards, not 4", errors)
        by_title = {
            match.group(1): card
            for card in cards
            if (match := re.search(r'class="td-content-card__title"[^>]*>([^<]+)<', card))
        }
        require(set(by_title) == {"Bundled", "External", "Plain", "Opted out"},
                f"the card fixture titles drifted: {sorted(by_title)}", errors)

        bundled = by_title.get("Bundled", "")
        # Hugo names a processed image differently across the supported
        # versions; what has to hold is that the card points at one, not at
        # the original the row form still emits.
        processed = re.search(r'<img class="td-blog-card__image" src="([^"]+)"', bundled)
        require(processed is not None
                and "_hu" in processed.group(1)
                and 'width="640" height="360"' in bundled,
                f"a bundled lead image is not cropped to 16:9 by Hugo: {bundled[:200]}", errors)

        external = by_title.get("External", "")
        require('href="https://example.net/post/"' in external
                and 'target="_blank"' in external
                and 'rel="noopener"' in external
                and "fa-arrow-up-right-from-square" in external,
                "the external card lost its target, rel, or affordance", errors)
        require("A post that lives somewhere else." in external,
                "the external card summarises the local body instead of its description", errors)

        rows = [
            item.split("</li>", 1)[0]
            for item in index.read_text(encoding="utf-8").split(
                '<li class="td-blog-posts-list__item">')[1:]
        ]
        external_row = next((row for row in rows if ">External<" in row), "")
        require('href="https://example.net/post/"' in external_row
                and 'target="_blank"' in external_row
                and 'rel="noopener"' in external_row
                and "A post that lives somewhere else." in external_row,
                "the external list row drifted from the card link or summary contract", errors)

        plain = by_title.get("Plain", "")
        require("<img" not in plain, "a post with no image still renders an image slot", errors)
        require("A post with no image at all." in plain,
                "a card without an image lost its summary too", errors)

        cleared = by_title.get("Opted out", "")
        require("<img" not in cleared and "cascaded.png" not in cleared,
                "`images: []` no longer turns off an inherited lead image", errors)
    return errors


def build_share_fixture(hugo: str) -> list[str]:
    """The share bar, end to end, on a site that opts every target in.

    One assertion per URL shape, because the shapes are what a platform's own
    documentation dictates and what a typo in the catalog would silently break:
    `url`+`text`, `url` alone, a `mailto:` whose subject precedes its body, one
    merged "Title URL" string, Pinterest's pin with its `media` image, and an
    assistant prompt naming the permalink.

    The last assertion is the feature's premise rather than a detail of it:
    a build carrying every share target on every page still passes the
    product-level trust check *without* --third-party, because everything the
    bar emits is a plain link the reader may choose to follow.
    """

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-shell-share-") as temporary:
        root = Path(temporary)
        source = root / "site"
        public = root / "public"
        (source / "content/blog").mkdir(parents=True)
        (source / "hugo.yaml").write_text(
            f"""baseURL: https://example.org/
title: Share fixture
theme: {ROOT.name}
disableKinds: [sitemap, taxonomy, term]
params:
  offline_search: false
  ui:
    feedback: true
    share: [x, bluesky, mastodon, facebook, linkedin, reddit, hackernews,
            telegram, whatsapp, line, pinterest, weibo, chatgpt, claude,
            email, copy]
""",
            encoding="utf-8",
        )
        (source / "content/blog/_index.md").write_text(
            "---\ntitle: Blog\ncascade:\n  type: blog\n---\n\nList.\n",
            encoding="utf-8",
        )
        (source / "content/blog/shared.md").write_text(
            "---\ntitle: Shared & titled\ndate: 2026-08-19\n---\n\nBody.\n",
            encoding="utf-8",
        )
        (source / "content/blog/quiet.md").write_text(
            "---\ntitle: Quiet\ndate: 2026-08-18\nshare: false\n---\n\nBody.\n",
            encoding="utf-8",
        )
        (source / "content/blog/pinned.md").write_text(
            "---\ntitle: Pinned\ndate: 2026-08-17\n"
            "images: [/images/pin.png]\nshare: [pinterest]\n---\n\nBody.\n",
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
            return ["share fixture failed to build:\n" + result.stdout + result.stderr]

        shared = (public / "blog/shared/index.html").read_text(encoding="utf-8")
        for marker in (
            'class="td-share d-print-none"',
            'href="https://x.com/intent/post?url=https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F'
            '&amp;text=Shared%20%26%20titled"',
            'href="mailto:?subject=Shared%20%26%20titled'
            '&amp;body=https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F"',
            'href="https://www.facebook.com/sharer/sharer.php'
            '?u=https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F"',
            'href="https://bsky.app/intent/compose?text=Shared%20%26%20titled'
            '%20https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F"',
            'href="https://wa.me/?text=Shared%20%26%20titled'
            '%20https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F"',
            'href="https://share.joinmastodon.org/#text=Shared%20%26%20titled'
            '%20https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F"',
            'href="https://social-plugins.line.me/lineit/share'
            '?url=https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F'
            '&amp;text=Shared%20%26%20titled"',
            'href="https://claude.ai/new?q=Read%20from'
            '%20https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F'
            '%20so%20I%20can%20ask%20questions%20about%20it."',
            'data-td-action="copy_link" data-td-url="https://example.org/blog/shared/"',
        ):
            require(marker in shared, f"share fixture page lacks {marker}", errors)
        require(shared.count('class="td-share__item td-share__item--') == 16,
                "share fixture page did not render one control per target", errors)
        # A page with no representative image leaves `media` off rather than
        # sending Pinterest an empty one.
        require('?url=https%3A%2F%2Fexample.org%2Fblog%2Fshared%2F'
                '&amp;description=Shared%20%26%20titled"' in shared,
                "Pinterest gained an empty media parameter", errors)

        pinned = (public / "blog/pinned/index.html").read_text(encoding="utf-8")
        require('href="https://www.pinterest.com/pin/create/button/'
                '?url=https%3A%2F%2Fexample.org%2Fblog%2Fpinned%2F'
                '&amp;description=Pinned'
                '&amp;media=https%3A%2F%2Fexample.org%2Fimages%2Fpin.png"' in pinned,
                "a pin no longer carries the page's own representative image", errors)
        rendered_order = [
            shared.find("data-td-share"),
            shared.find("data-td-feedback"),
            shared.find("data-td-page-annotation"),
            shared.find("data-td-pager"),
        ]
        require(all(index >= 0 for index in rendered_order)
                and rendered_order == sorted(rendered_order),
                "rendered share/feedback/annotation/pager order drifted", errors)

        quiet = (public / "blog/quiet/index.html").read_text(encoding="utf-8")
        require("td-share" not in quiet, "share: false still rendered a bar", errors)
        for kind, relative in (("list", "blog/index.html"), ("home", "index.html")):
            page = (public / relative).read_text(encoding="utf-8")
            require("td-share" not in page, f"share bar leaked onto the {kind} page", errors)
        feed = (public / "blog/index.xml").read_text(encoding="utf-8")
        require("td-share" not in feed, "share bar leaked into the feed", errors)

        trust = subprocess.run(
            [sys.executable, str(ROOT / "bin/check-output-security.py"),
             "--public", str(public), "--base-url", "https://example.org/"],
            capture_output=True,
            text=True,
            check=False,
        )
        require(trust.returncode == 0,
                "a site with every share target on no longer passes the trust check "
                "without --third-party:\n" + trust.stdout.strip(), errors)
    return errors


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()
    errors = (check_sources() + build_example(args.hugo) + build_footer_utilities_fixture(args.hugo)
              + build_self_root_fixture(args.hugo)
              + build_featured_image_rejection(args.hugo)
              + build_navbar_menu_columns(args.hugo)
              + build_blog_index_forms(args.hugo) + build_blog_card_fixture(args.hugo)
              + build_share_fixture(args.hugo))
    if errors:
        print("shell and page-end checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("navigation and page-end checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
