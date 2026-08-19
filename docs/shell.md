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

Built-in action IDs are `copy_markdown`, `copy_link`, `open_chatgpt`,
`open_claude`, `view_markdown`, `view_history`, `edit_page`,
`create_child_page`, `create_issue`, `create_project_issue`, `print_section`,
`print`, `switch_theme`, `switch_language`, `switch_version`, and
`open_github`. `copy_link` copies the page's canonical URL; it is Palette-only,
because the surface that renders it on the page is the share bar.

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

## Share bar

`params.ui.share` is a list drawn from the sixteen targets below. It is empty by
default, the page key is `share`, a page's own list replaces an inherited one,
and `share: false` opts one page out. An unknown entry warns and is dropped.
Only a regular page renders the bar; lists, terms, and the home page never do,
and it is absent from print, Markdown, and RSS.

| Entry | Intent endpoint | Carries |
| --- | --- | --- |
| `x` | `x.com/intent/post` | `url`, `text` |
| `bluesky` | `bsky.app/intent/compose` | `text` (title + URL) |
| `mastodon` | `share.joinmastodon.org/#text=` | title + URL; the widget asks which server |
| `facebook` | `facebook.com/sharer/sharer.php` | `u` |
| `linkedin` | `linkedin.com/sharing/share-offsite/` | `url` |
| `reddit` | `reddit.com/submit` | `url`, `title` |
| `hackernews` | `news.ycombinator.com/submitlink` | `u`, `t` |
| `telegram` | `t.me/share/url` | `url`, `text` |
| `whatsapp` | `wa.me/?text=` | title + URL |
| `line` | `social-plugins.line.me/lineit/share` | `url`, `text` |
| `pinterest` | `pinterest.com/pin/create/button/` | `url`, `description`, `media` |
| `weibo` | `service.weibo.com/share/share.php` | `url`, `title` |
| `chatgpt` | `chatgpt.com/?hints=search` | `prompt` naming the permalink |
| `claude` | `claude.ai/new` | `q` naming the permalink |
| `email` | `mailto:` | `subject`, `body` |
| `copy` | none — the local `copy_link` action | — |

`media` is Pinterest's pin image, resolved through `featured-image-resolve.html`
so a pin and the page's own social card cannot disagree; a page with no
representative image simply omits it and Pinterest asks the reader to pick one.
**Discord is absent on purpose**: it publishes no share-intent URL, and `copy`
is the honest equivalent. `chatgpt` and `claude` are the build-time permalink
inside an assistant prompt, not the `open_chatgpt` / `open_claude` actions the
runtime rewrites to the live browser URL, so they are not gated by
`page_context_menu.assistant_links` — naming them in the list is the opt-in.

The bar is one centred row of glyphs and nothing else: no visible heading, since
a row of platform marks needs no label to be read, and no rule of its own, since
whatever follows it -- feedback, the annotation -- already draws the hairline
that closes the article. The name it does not show lives on the group's
`aria-label`, so assistive technology still announces it as Share.

Everything the bar emits is a plain `<a href>` intent link carrying the page's
own permalink and title, plus one local `copy_link` button: no share count, no
platform SDK, no iframe, no third-party script or stylesheet, and no campaign
parameters. Nothing is requested when the site builds or when the page loads,
so a build passes `bin/check-output-security.py` without `--third-party`.
`share/items.html` resolves the targets and `share/bar.html` renders them, the
same split the annotation uses; the `form` field there names the URL shape
(`u`, `ut`, `tu`, `m`, `pin`, `p`) so a site overriding the resolver adds a
platform by adding one catalog row.

## Page annotation

The annotation is the block of provenance lines under the article. It is split
in two so a site can replace either half: `annotation-items.html` resolves the
lines and returns descriptors (`key`, `icon`, `html`), and
`page-meta-lastmod.html` renders them. Override the resolver to change which
lines appear; override the renderer to change the markup. `bin/check-annotation.py`
is the executable contract.

Three lines ship, in this order:

| Line | Rendered when |
| --- | --- |
| Last modified | `Lastmod` is set; the commit link follows `params.ui.lastmod_commit` |
| Upstream attribution | front matter `upstream_link` is non-empty |
| Translated | `params.ui.translation_notice` names another language, this page has a translation in it, and this page has authored text of its own |

`upstream_modified` does not add a line. The licence asks for an indication
that the material was changed, not a second sentence, so the verb carries it --
unmodified material is credited, modified material is *adapted from* its
source -- and the credit gains a second link to the page's commit history,
which stands as the record of what changed. One line, one obligation
discharged.

The attribution line exists to discharge a licence obligation, so its rules are
strict rather than forgiving. `upstream_link` — the URL of the material the
page is derived from — is read from front matter only; a cascade counts,
site params do not, because a site-wide value would make every page claim the
same source. Any other `upstream_*` key present without it fails the build, so
cascading the constants over a vendored tree also makes every page in that tree
that forgot its own source URL fail. `upstream_link: ""` is the per-page opt-out.

The constants resolve site params → the `data/upstreams` entry named by
`upstream_source` → front matter, most specific last: `upstream_name`,
`upstream_copyright` (retained verbatim, rendered as text), `upstream_license`
(an SPDX identifier resolved through `data/licenses`, which the theme mounts
and a site merges over), `upstream_notice` (the page carrying the full notice),
and the optional `upstream_ref`. All four of the first are required once
`upstream_link` is set: a partial attribution reads like a complete one, so the
build fails instead.

The translation notice is the annotation's one *inferred* line: the site names
the authoritative language and the theme infers that everything else is a
translation of it. Inference gets a guard that declarations do not need: a
page with no authored text of its own has nothing to be a translation of, so a
generated taxonomy or term list, and a section index that is only a title and
a child list, never carry the notice however the site is configured. Beyond that the theme
does not guess: no language name appears in the string, and because
`translation_notice` is a page key it cascades, so a partly translated site
scopes the claim to the trees where it holds rather than declaring it
site-wide. A page authored natively in this language opts out with
`translation_notice: false`.

The line carries only what a reader needs in place — the work, the copyright,
the licence, whether it changed — and links to `upstream_notice` for the
licence text, warranty disclaimer, upstream NOTICE, and snapshot pin. The
theme does not model those per-licence differences because they do not belong
in a footer line. Whether that notice page exists is the site's to check; the
theme validates the values, not the destination.

## Author bylines

A site activates authors by declaring the taxonomy and nothing else:

```yaml
taxonomies:
  author: authors
```

The theme adds no parameter for this. A site that never declares it keeps the
0.4 behaviour exactly, including any `authors:` it already wrote in front
matter, which stays an ordinary unread page parameter.

`authors` is a reserved plural, in the same way `tags` and `categories` are
names `taxonomy-label.html` already knows. A site is free to call its author
taxonomy something else -- `author: writers` -- and it then behaves as an
ordinary taxonomy: chips, generic term heading, no profile, no byline.

The author profile is the term page, not a data file. `title` is the display
name, `description` is the one-line introduction, the body is the long one, and
the avatar is whatever `featured-image-resolve.html` selects for that page, so
`images:` and a bundled `**featured*` / `*feature*` / `{*cover*,*thumbnail*}`
resource work exactly as they do for an article. A bilingual profile is an
`_index.zh.md` beside it. A term used by a post but never given a profile page
still works: the name falls back to Hugo's link title, the avatar to an
initial, and the link to the archive page that exists either way.

`authors-resolve.html` is the one place that answers who wrote a page;
`byline.html` renders it on the article head (portraits, names, date) and in a
list row (names only -- the row has no space for portraits). Order comes from
`GetTerms`, which preserves the front matter sequence, so `authors:` is both
the set and the order and no weight key is involved. Names are separated by
CSS gap, never by rendered punctuation, because a comma-and-`and` list needs a
connector word in each of 32 locales.

Where both are present, `authors` wins and `author` is ignored. Neither warns.
853 pages across the family sites carry the 0.4 `author:` string and 180 put
Markdown in it; that branch renders byte for byte as it did, and
`tests/site/content/blog/legacy-byline.md` is the pin that proves it.

The article byline is the author surface, so the generic taxonomy chip row
skips the reserved plurals `authors` and `series` by default. A site that
names either one in `params.taxonomy.page_header` gets the chips anyway --
explicit configuration outranks a default exclusion.

Output states: HTML renders the byline, the row names, and the profile head;
the blog feed declares `xmlns:dc` and emits one `<dc:creator>` per author per
item, beside the untouched site-level `managingEditor`; print and Markdown
carry no byline, as they did not before.

## Brand lockup

`params.logo` is the mark and `params.wordmark` is the optional text half.
The navbar, the docs sidebar brand row, and the mobile subnav render the mark
always and put the wordmark beside it, falling back to the site title when no
wordmark is configured. The text half is the part that collapses in the
icon-mode range and at drawer widths; the mark does not, so the brand is
present at every width.

## Compatibility and non-goals

The docs, Book, Blog, and Swagger shells share one layout model. Page-end order
is Share, Feedback, Annotation, Pager, Comments. `page-annotation.html` preserves the
`page-meta-lastmod.html` override point. Feedback emits the structured
`docs_feedback` event through an existing `gtag` function, stores the choice
locally, sends no free text, and needs no endpoint. Giscus remains a separate
comment surface.

Pager order follows the sidebar preorder for Docs and Book. Blog keeps
explicitly weighted pages first and then reverse date. `pager: false` opts a
page out. Print, Markdown, and RSS omit pager UI.

Blog section list pages take one of two forms, chosen by the site:
`params.ui.blog_index: list` (default) keeps the row list, `cards` renders the
same year groups as a grid of shared content cards, `params.ui.blog_index_columns`
wide. Front matter on the blog root, or its cascade, overrides it per section.
The two forms group, paginate, and link identically — a card carries the lead
image, title, date, section, and summary, and nothing else. Term and taxonomy
pages keep the row form: they are filtered views, where a row and a count are
the right shape. There is no reader-side switch between the forms, for the same
reason the Palette keeps no history: a remembered view preference is
personalization, and the form is the site's decision.

There is no archive shell, arbitrary-depth flyout, second navigation authority,
default query upload, or browser-side compatibility shim for removed config.

## Characterization matrix

`bin/check-navigation-contract.py` builds flat, nested, and deep menus with
search on/off, English/Chinese, root/subpath deployment, and home/docs/blog/
plain/print surfaces. `tests/fixtures/navigation/current.json` is the normalized
output snapshot. `bin/check-shell.py`, JS tests, and the consumer browser
suite cover page-end order, keyboard behavior, accessibility, and responsive
layout.

## Series contract

A site activates article series by declaring the taxonomy, and that is the
whole switch:

```yaml
taxonomies:
  series: series
```

There is no `params.ui.series`, no per-series metadata file, and no cover
model: the term page `content/series/<name>/_index.md` already holds the
display name, the one-line description, and the long introduction, and a
`_index.zh.md` beside it makes the pair bilingual. A term with no `_index.md`
still works; it just falls back to the humanized term name. Where the taxonomy
is not declared, `series:` in front matter stays an ordinary page parameter
that no template reads.

An article names its series and, optionally, its position:

```yaml
series: [pg-internals]
series_weight: 2
```

**Reading order is the theme's, not Hugo's.** `series-pages.html` is the single
resolver, and both the strip and the term page read it: members that declare
`series_weight` come first in ascending order, the rest follow by ascending
date, and `Path` breaks a tie. Hugo's own term order cannot be used for this --
an unweighted term arrives newest first, a mixed term puts unweighted members
*before* weight 1, `Page.Weight` never carries the taxonomy weight, and
`GroupByParam` cannot see `series_weight` at all. Declare a weight on every
member of a series or on none of them; the mixed form is defined, not
recommended.

`series-strip.html` renders above the article body, between the metadata row
and the first paragraph: the series name, `Part N of M`, the next part, and the
whole list behind a `<details>`. It has no JavaScript, no page-store flag, and
no bundle member. A member of several series gets one strip, for the first term
it names. A series of one gets none. The `series` term is kept out of the
default taxonomy chips row -- along with `authors` -- because the strip already
carries it; a site that names `series` in `params.taxonomy.page_header` opts
back in.

Output matrix: HTML renders the strip; printing keeps it and the existing print
rule opens the disclosure; the Markdown and RSS outputs never see it, because
it is a template product and not part of the page content.

A series is a reading path through articles that stand on their own. Numbering,
cross-references, and aggregate output are Book's: when a work needs those, it
is a Book, not a series.
