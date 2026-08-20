# Shell and navigation contract

## Authorities and navigation

| Concern | Authority |
| --- | --- |
| Global navigation | Hugo `menus.main` |
| Docs / Book sidebar and pager | content tree or `data/docs_nav.json` |
| Root switcher | resolved top-level content roots |
| Discovery | per-language local search index |
| Page and Palette actions | shared action registry |

No feature introduces another menu or page tree. One menu child level is
interactive; deeper levels warn and flatten beneath linked group headings.
External links use `target="_blank" rel="noopener noreferrer"`; internal links
remain language- and subpath-aware.

Navbar desktop and drawer views project one tree. Language links target the
page translation or that language's home, stay relative when languages share a
host/base path, and become absolute only for language-specific `baseURL`s;
`hreflang` stays absolute. `navbar_autohide` applies to fine pointers from
768px, never touch or drawer widths.

Menu children default to a single-column panel without descriptions. Values
2–4 enable the multi-column panel; any explicit `columns` value from 1 to 4
retains child descriptions. Invalid values warn and use the default
single-column form.

Sidebar and pager share root and order. `manual_link`, `build.render: link`,
dividers, hidden nodes, and placeholders retain their documented semantics.
`sidebar_icon_policy` is `all` (default), `groups`, or `none`; icons are one
Font Awesome class pair. Invalid policies follow the shared warning/fallback
contract.

## Immersive blog presentation

There is no article type or second shell. Immersive reading is four independent
keys on the ordinary blog shell, set on a page or section cascade; the section
index repeats values it also needs:

```yaml
featured_image: hero
toc_style: flow
toc_taxonomies: false
sidebar_enabled: false
```

The blog shell renders no breadcrumb by default -- an article reads as a
standalone piece -- so the recipe needs no key for it. `breadcrumb` remains an
ordinary key a page or cascade may still set either way, on any shell.

`hero` uses the shared featured image as a decorative full-bleed backdrop on
single pages and section indexes. With no image it renders the normal opening;
`banner` and `wash` remain single-page modes. The navbar overlays a hero on a
contrast scrim and scrolls with it.

`toc_style` is `fixed` or `flow`; flow places a wider rail beside the article
and pins it only after scrolling. Its resting place aligns with the article's
info line (or its description, where a page has no info line) -- docs-shell.js
measures the offset, because a title wraps to an unknown number of lines;
without JavaScript the rail starts where the article starts. `toc_taxonomies: false` removes term clouds;
a rail with neither TOC nor clouds renders nothing. `notoc` remains the
page-level TOC opt-out. These switches do not change bylines, tags, series,
pager order, feeds, or page-end composition, and the rail disappears below the
`xl` breakpoint.

## Search, actions, and runtime

`params.offline_search` opts into a local per-language index. When enabled it
also builds under `hugo server` by default; set `offline_search_on_serve: false`
for large edit loops. HTML search appears on Home, shell pages, and Landing when
`landing_search` is enabled. Other non-shell pages and Print omit the dialog,
Lunr, and Palette.

Search metadata is `search_keywords`, `search_boost` (default 1), and
`search_exclude`. The index carries URL, title, taxonomies, excerpt, headings,
description, body/summary, root, section, type, keywords, boost, breadcrumb,
and icon. Fixture budget is 2 MiB raw / 512 KiB gzip. Sites may return extra
strings from `hooks/search-keywords-extra.html`.

Built-in action IDs are `copy_markdown`, `copy_link`, `open_chatgpt`,
`open_claude`, `view_markdown`, `view_history`, `edit_page`,
`create_child_page`, `create_issue`, `create_project_issue`, `print_section`,
`print`, `switch_theme`, `switch_language`, `switch_version`, and
`open_github`. `copy_link` is Palette-only outside the share bar. Site commands
under `languages.<lang>.params.ui.command_palette.commands` may open a safe URL
or invoke this safe subset: `copy_markdown`, `copy_link`, `open_chatgpt`,
`open_claude`, `view_markdown`, `view_history`, `edit_page`, `create_issue`,
`print`, `switch_theme`, `switch_language`, `switch_version`, and
`open_github`. They never inject JavaScript.

The Palette has empty, text-search, and `>` command modes; quick links derive
from navigation. It has no history, semantic search, personalization, or remote
fallback. Search queries stay in-browser and no default telemetry is sent.

`OinkSurfaceCoordinator` arbitrates Palette, drawer, root, language, and version
menus. Surfaces own focus restoration and Escape. Keyboard navigation ignores
editable controls and modals: `/`, `\`, `f`, `c` open search/commands; `j`/`k`
move headings; `q`/`e` move pages; `h` changes presentation; `l`/`y`, `t`, and
`r` cycle language, theme, and root routes. Sidebar WASD/Arrow navigation uses
real focus without rewriting Tab order.

The outline derives cursor and visible-heading range from one heading model and
the scroller's computed `scroll-padding-top`; its SVG line and dot share the
same animated values so they cannot drift. No speculative DOM repair pass is
allowed.

## Share

`params.ui.share` is empty by default and accepts any ordered subset of 16
targets: `x`, `bluesky`, `mastodon`, `facebook`, `linkedin`, `reddit`,
`hackernews`, `telegram`, `whatsapp`, `line`, `pinterest`, `weibo`, `chatgpt`,
`claude`, `email`, and `copy`. A page list replaces its inherited list;
`share: false` opts out. Unknown entries warn and are dropped. Only regular
pages render the bar; print, Markdown, and RSS omit it.

Targets are plain intent links carrying the page permalink/title, plus the
local `copy_link` button. Pinterest media comes from the shared featured-image
resolver. ChatGPT and Claude receive build-time permalink prompts and are
independent of page-menu assistant actions. Discord has no public intent target
and is deliberately absent.

The bar loads no platform SDK, iframe, script, stylesheet, counter, or campaign
parameter and makes no request until a reader activates a link. It is one
accessible labeled glyph row. `share/items.html` resolves targets and
`share/bar.html` renders them.

## Annotation

Page annotation resolves descriptors in `annotation-items.html` and renders
them through `page-meta-lastmod.html`; either may be overridden narrowly. Lines
appear in this order:

| Line | Condition |
| --- | --- |
| Last modified | `Lastmod` is set |
| Upstream | front matter `upstream_link` is non-empty |
| Translation | configured authoritative language has a translation and this page has authored text |

`upstream_link` is per-page (a cascade counts); `upstream_link: ""` opts out.
Other upstream facts resolve site params → `data/upstreams[upstream_source]` →
front matter: `upstream_name`, `upstream_copyright`, `upstream_license`,
`upstream_notice`, optional `upstream_ref`, and `upstream_modified`. The first
four are required with a link. Invalid or incomplete attribution warns and
emits no legal notice; unsupported URLs are refused. Publication gates reject
the warning with `--panicOnWarning`.

`upstream_modified` changes the credit verb and links commit history; it adds no
line. The notice page carries full license/warranty text. Translation notice is
opt-in through `params.ui.translation_notice`, cascades as the page key
`translation_notice`, skips generated or bodyless pages, and can be disabled on
a natively authored page with `translation_notice: false`.

## Authors and series

A blog article head is title, info line, term badges, byline, then the series
strip; the description leads the body below them. The info line
(`article-info.html`) always carries the date; with `reading_time` on it adds
the word count and the minutes; front matter `upstream_link` -- the same
per-page fact the annotation attributes -- adds a localized link to the
original, gated by the shared URL policy. Term rows are bare badge runs whose
taxonomy name lives on the group label, not as a visible prefix. The byline
carries the people alone -- portrait, name, and the profile's one-line bio --
with no label and no date. List rows, cards, and term archives share one
metadata line of the same shape: date, one localized author-and-section
phrase, then word count and minutes behind the same `reading_time` switch.

Authors activate only through `taxonomies: {author: authors}`. The profile term
page owns display name, summary, body, and featured-image avatar; an absent
profile falls back to link title, initial, and archive. `authors-resolve.html`
preserves front-matter order for article heads, list rows, and one RSS
`dc:creator` per author. Legacy `author` remains unchanged when `authors` is
absent; when both exist, `authors` wins without warning. Custom author taxonomy
plurals behave as ordinary taxonomies.

Series activate only through `taxonomies: {series: series}`. Term pages own the
introduction; no parameter, data file, cover model, or runtime is added. A page
uses `series: [name]` and optional `series_weight`. `series-pages.html` orders
weighted members first by weight, then unweighted members by ascending date,
with `Path` tie-breaks; strip and term page share it. The first named series
gets one HTML/print strip: a closed disclosure line -- series name, part M of
N -- that expands (and prints expanded) to the reading order, one member per
line; singleton series and non-HTML outputs omit it. Numbering, cross-references,
and aggregate output remain Book concerns.

The default article taxonomy chips omit reserved `authors` and `series` because
their dedicated surfaces already carry them. Explicit
`params.taxonomy.page_header` restores either.

## Blog indexes and page composition

Blog section indexes use `params.ui.blog_index`: `list` (default) and `cards`
are one flat run, newest first, sharing `blog_index_size` pagination -- the
metadata line's dates make year headings redundant; `table` shows the whole
section as date/title/tag rows without pagination. Cards use the
shared lead image, localized date/author/section metadata, tags, and a
three-line summary. Term and taxonomy pages stay row lists.

`params.ui.blog_index_toggle` renders all three forms for the current paginator
slice and lets readers cycle them. The configured form controls first paint,
local storage may override it, and hidden forms load no images. A front-matter
value or cascade overrides the site mode per section. A table published without
the toggle remains a complete, unpaginated archive.

`params.logo` is always the brand mark; `params.wordmark`, or the site title,
is the text half hidden at compact widths. Docs, Book, Blog, and Swagger share
one shell model. Page-end order is Share, Feedback, Annotation, Pager, Comments.
Docs/Book pager follows sidebar preorder; Blog uses weight then reverse date;
`pager: false` opts out. Static outputs omit pager UI.

There is no archive shell, arbitrary-depth flyout, second navigation authority,
query upload, or browser compatibility shim for removed config. Feedback emits
only `docs_feedback` through an existing `gtag`, stores the choice locally, and
does not replace Giscus.

## Verification

`bin/check-navigation-contract.py`, `bin/check-shell.py`, JS tests, output
goldens, and the consumer browser suite cover navigation, language/subpath
links, blog variants, page-end order, keyboard behavior, accessibility, and
responsive layout.
