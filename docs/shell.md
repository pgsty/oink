# Shell, navigation, and actions contract

Status: current for OINK 0.5.0
Compatibility floor: Hugo Extended 0.160.1

## Authority boundaries

| Concern | Authority |
| --- | --- |
| Global navigation | Hugo `menus.main` |
| Docs and Book sidebar | content tree or `data/docs_nav.json` |
| Root switcher | resolved top-level content roots |
| Discovery | per-language local search index |
| Page and Palette actions | shared action registry |

No second menu or page tree is introduced.

## Navigation contract

One menu child level is interactive. A parent remains a navigating link; hover
or focus opens its panel. Deeper menus warn and flatten under a linked group
heading rather than create another flyout. External destinations use
`target="_blank" rel="noopener noreferrer"`; internal links remain language-
and subpath-aware.

The navbar has full and compact presentations, not separate desktop/mobile
trees. At drawer width, language, version, theme, and GitHub utilities move to
the drawer. `params.ui.navbar_autohide` applies only to fine pointers at 768px
and above; touch and drawer widths keep the bar visible.

The sidebar and pager use the same root and ordering. The content tree is the
default; `data/docs_nav.json` is an explicit alternative. `manual_link`,
`build.render: link`, `sidebar_divider`, hidden nodes, and non-rendered
placeholders participate only where their semantics allow. Root, section, and
page rows delegate to one renderer.

## Sidebar icon contract

`params.ui.sidebar_icon_policy` is `all`, `groups`, or `none`. The theme declares all as the default,
preserving authored leaf icons. A page icon is one
Font Awesome class pair. Unknown policies warn and use `all`.

## Search schema and ranking contract

`params.offline_search` enables a local, per-language index on home and shell
surfaces, under `hugo server` too unless `offline_search_on_serve` is false. Print
and plain non-shell pages omit the dialog, index reference, Lunr, and Palette.

Page metadata is `search_keywords`, `search_boost`, and `search_exclude`.
`search_boost` defaults to 1 and multiplies the text score. Invalid values warn
and use the default. `exclude_search` fails the build naming `search_exclude`;
the camelCase `excludeSearch` alias does the same.

The index carries URL, title, taxonomies, excerpt, headings, description, body,
root, section, type, keywords, boost, breadcrumb, and icon. The maintained
fixture budget is 2 MiB raw and 512 KiB gzip. Sites may override
`hooks/search-keywords-extra.html` and return an array of additional strings.

## Command registry contract

Built-in action IDs are `copy_markdown`, `open_chatgpt`, `open_claude`,
`view_markdown`, `view_history`, `edit_page`, `create_child_page`,
`create_issue`, `create_project_issue`, `print_section`, `print`,
`switch_theme`, `switch_language`, `switch_version`, and `open_github`.

Site commands are localized under
`languages.<lang>.params.ui.command_palette.commands`. They may open a safe URL
or invoke an existing built-in action ID; configuration cannot inject a
JavaScript callback. The registry still recognizes historical rail-only
compatibility actions, but the Palette does not claim that every action has a
page-menu placement.

## Palette modes

The local search dialog owns three modes: empty, text search, and commands.
`>` selects command mode. The Palette and page menu project the same action
facts and availability. Quick links derive from existing navigation. There is
no recent-history, personalization, semantic search, or remote fallback.

## Runtime contract

Search assets exist only when the site opt-in, supported surface, and output
format all permit them. No default telemetry request is made. Assistant links
are explicit actions; search queries stay in the browser.

Transient UI uses `OinkSurfaceCoordinator`: opening a Palette, drawer, root
menu, language menu, or version menu closes conflicting surfaces. Each surface
owns focus restoration and Escape behavior.

Keyboard navigation is disabled inside editable controls and modal surfaces.
The stable global bindings are:

| Keys | Action |
| --- | --- |
| `/`, `\` | search / command Palette |
| `f`, `c` | search / command Palette |
| `j`, `k` | next/previous visible heading or landing section |
| `q`, `e` | previous/next reading page |
| `h` | focus/zen presentation |
| `l`, `y` | language choice |
| `t` | theme choice |
| `r` | root navigation cycle |

The sidebar tree uses real focus and WASD/Arrow navigation without
rewriting the document Tab order.

## Compatibility and non-goals

The docs, Book, Blog, and Swagger shells share one layout model. Page-end order
is Feedback, Annotation, Pager, Comments. `page-annotation.html` preserves the
`page-meta-lastmod.html` override point. Feedback emits the structured
`docs_feedback` event through an existing `gtag` function, stores the choice
locally, sends no free text, and needs no endpoint. Giscus remains a separate
comment surface.

Pager order follows the sidebar preorder for Docs and Book. Blog keeps
explicitly weighted pages first and then reverse date. `pager: false` opts a
page out. Print, Markdown, and RSS omit pager UI.

There is no archive shell, arbitrary-depth flyout, second navigation authority,
default query upload, or browser-side compatibility shim for removed config.

## Characterization matrix

`bin/check-navigation-contract.py` builds flat, nested, and deep menus with
search on/off, English/Chinese, root/subpath deployment, and home/docs/blog/
plain/print surfaces. `tests/fixtures/navigation/current.json` is the normalized
output snapshot. `bin/check-shell.py`, JS tests, and the consumer browser
suite cover page-end order, keyboard behavior, accessibility, and responsive
layout.
