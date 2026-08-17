# Book contract

Release assignment: OINK 0.4.0 (consolidated component release; contract version 1)

Original design milestone: OINK 0.6.0

Contract version: 2 (OINK 0.5/0.6 component API v5)

Status: frozen for OINK v0.5.0 (version 1 remains the record of OINK v0.4.0)

Compatibility floor: Hugo Extended 0.160.1

This document freezes the Book component track. Its machine-readable companion
is `tests/fixtures/components/contract.json`; `scripts/check-component-contract.py` keeps
the two aligned. Configuration and migration recipes are available in
[English](migration-components.md) and
[Simplified Chinese](migration-components.zh.md).

Version 2 changes from version 1 (see section 7 for the complete list): the
leaf `example` shortcode became the `eg` wrapper; every numbered kind gained a
native form (one Markdown block plus an attribute line); `xref` accepts `eg`;
`book-figures` lost its `kind` parameter in favour of `book-tables`,
`book-equations`, and `book-examples`; target registration is ordered by
source position so render-hook and shortcode targets share one namespace.

## 1. Book type and navigation

`book` is a default shell type. It extends the docs shell rather than creating
a parallel shell: the content tree or existing `data/docs_nav.json` remains
the navigation authority, breadcrumbs remain enabled, and the shared pager is
enabled by default. The Book root is always the current first section even
when a site-wide root switcher is enabled, so a Book table of contents cannot
leak into sibling docs or blog trees.

OINK recognizes the established `book_kind`, `book_number`, `book_part`, and
`book_status` namespace. `book_number` appears beside titles in the page,
sidebar, and generated Book table of contents. `book_status: draft` is a
visible sidebar label; `params.ui.book_draft_banner: true` additionally emits
a localized page notice. Both settings are presentation only and never change
Hugo publication state.

`params.ui.sidebar_headings` accepts `false`, `true` (h2), or a maximum heading
level from 2 through 4. On the active Book page it projects Hugo's fragment
tree below the sidebar row. Authors who cite headings must use explicit stable
IDs (`{#anchor}`); derived heading IDs are not a durable cross-reference API.

## 2. Numbered components

Four numbered kinds exist: `fig` (figure), `tbl` (table), `eq` (equation),
and `eg` (example). Each has a shortcode form and a native form:

| Kind | Shortcode form | Native form (block + attribute line) | Default ID |
| --- | --- | --- | --- |
| `fig` | `{{< fig num id caption class src link alt width height >}}…{{< /fig >}}` | standalone `![alt](src)` + `{#id num="2-1" caption="…" width= height= .class}` | `fig-<num>` |
| `tbl` | `{{< tbl num id caption class >}}table{{< /tbl >}}` | pipe table + `{#id num="9-1" caption="…"}` | `tbl-<num>` |
| `eq` | `{{< eq num id caption class >}}TeX{{< /eq >}}` | `$$…$$` block + `{#id num="5.3" caption="…"}` | `eq-<num>` |
| `eg` | `{{< eg num id caption class >}}Markdown{{< /eg >}}` | fence with `{num="4-1" caption="…" #id}` | `eg-<num>` |

The numbered forms require a `num` matching `[0-9A-Za-z.-]+`. An explicit ID
matching `[A-Za-z][A-Za-z0-9_.:-]*` is preserved byte-for-byte; in the native
fence form the author `#id` names the `<figure>` (the target), not the code
block root. Number and ID are intentionally independent. A page rejects a
duplicate ID and rejects two components of one kind that claim the same number
with different IDs. Registration (`layouts/_partials/book/register-target.html`)
identifies each target by its source position (`file:line:col`) and orders
Book lists by it, so shortcode and render-hook targets share one registry
(`tdBookTargets`) and mixed pages keep document order.

OINK 0.4 already defines parameter-free `{{< eq >}}` as an unnumbered
display-math escape hatch. It registers no target and therefore cannot be an
`xref` destination or appear in `book-equations`. Adding `num` selects the Book
form described here; `id`, `caption`, and `class` require that number.

Captions are plain text and, for `eg`, required (a fence `caption` without
`num` and a fence `num` without `caption` are build errors). Inner Figure,
Table, and Example content is rendered through the page's Markdown policy
inside a scoped `content/render-block.html` call, so generated code-block IDs
inside a Book example cannot collide with the page's own fences. Equation
inner content is sent directly to the local server-side KaTeX renderer, so
`eq` works even when a consumer has not enabled Goldmark passthrough; the
native `$$` form requires passthrough. Native figures require the site setting
`markup.goldmark.parser.wrapStandAloneImageWithinParagraph: false` (otherwise
the attribute line attaches to the paragraph and is ignored).

`fig` accepts the DDIA compatibility parameter superset
`src`, `id`, `caption`, `title`, `class`, `link`, `alt`, `width`, and
`height`, in addition to `num`. `title` is a caption alias for mechanical
migration and is mutually exclusive with `caption`. `src` and inner content
are mutually exclusive. Width and height are positive integers; class tokens
and every URL are validated.

`fig` renders `<figure class="td-figure td-book-figure td-book-figure--fig">`,
the same class set as the native numbered form. `.td-figure` is the shared
image-figure base; `.td-book-figure` is the numbered variant and overrides its
spacing. `tbl`, `eq`, and `eg` carry only `.td-book-figure`, which therefore
stays self-sufficient rather than becoming a `.td-figure` modifier.

`src` resolves through the shared image resolver (contract
`content-primitives.md` section 3.5), so a Book figure has the same source
precedence as `![alt](src)` and the `image` shortcode: page resource, then
enclosing-section resource, then global asset, then static or remote path. A
resolved raster resource supplies intrinsic `width`/`height`; explicit `width`
and `height` parameters still win. An SVG resource resolves without error but
carries no intrinsic size, so such figures state their box explicitly or go
without one. A `src` that resolves to a non-image resource fails the build.

Alt precedence is: an explicit `alt` parameter (including an explicit empty
one), then the resource's `params.alt` metadata, then the plain caption as the
migration fallback for legacy source. New content should state a meaningful
`alt` explicitly. The resource's `params.byline` is resolved but not rendered
by `fig`; only the `image` shortcode emits a byline. The native figure takes
its alt text from the
Markdown image, accepts `width`/`height` attributes for static or remote
images (they never turn alt text into a caption), and passes `class` tokens
through; a `link` needs the shortcode form.

`tbl` wraps a Markdown table inside one semantic figure, keeping the label,
body, caption, and anchor together; the shortcode form remains for compound
bodies (several tables under one number). `eq` presents the number on the
right in screen and print layouts. `eg` presents its caption bar above the
body (O'Reilly convention); its body is Markdown, usually one or more fences.
All four expose a semantic `<figure>` with `data-td-book-kind` and
`data-td-book-num` and a `<figcaption>`, and do not use fake h6 captions.

## 3. Cross references and consistency

`xref` accepts exactly one optional kind key (`fig`, `tbl`, `eq`, or `eg`),
optional `page`, and optional `anchor`. A kind supplies the localized default
label and derives the anchor when one is absent. An anchor-only reference
requires inner link text. `page` resolves through Hugo's current-language page
lookup, so the same source does not hard-code an `/en/` destination.

Rendering is order-independent: an xref may appear before its target and never
reads a target registration table to decide its output. The companion
`scripts/check-book.py` validates rendered pages after the build: every target
anchor exists, a kind/number reference matches the numbered target, IDs are
unique within a page and across whole-Book aggregation, and numbered figure
images have caption-compatible alternative text.

## 4. Book tables of contents and figure lists

`{{< book-toc depth=1..3 drafts=true|false >}}` traverses the same ordered
Book tree as the sidebar. Depth one lists chapters, depth two includes nested
sections, and depth three also projects each page's Hugo `.Fragments` heading
tree. Draft filtering only affects this generated list; it does not hide the
underlying page.

`{{< book-figures >}}`, `{{< book-tables >}}`, `{{< book-equations >}}`, and
`{{< book-examples >}}` render ordered Book-wide lists of one kind each by
triggering descendant content, then aggregating the idempotent Page Store
registration. They take no parameters (the version-1 `kind` parameter of
`book-figures` is removed). The lists link to stable public IDs and remain
correct regardless of which alternate output Hugo renders first.

## 5. Whole-Book print and output matrix

A Book root with the `print` output traverses the flattened visible Book tree
and emits a cover, a local print table of contents, then the root and each
descendant in reading order. Pages marked `no_print: true`, link-only nodes,
dividers, and hidden navigation placeholders do not become print chapters.
The theme does not add `print` to a consumer's output configuration: a section
Book opts in with `outputs.section`, while a site-root Book opts in with
`outputs.home`. This keeps the cost of a large aggregate explicit.
Cross-page xrefs, Book-ToC entries, and figure-list links become document-local
fragments. Numbered component IDs are preserved byte-for-byte. Markdown heading
IDs remain byte-stable on standalone pages, while whole-Book print prefixes
them with the source page identity so common page-local names such as
`summary` or `references` remain unique; every generated heading link is
rewritten to that prefixed ID.

On the 2026-08-14 pg36g scale fixture (301 Book pages, 300 generated ToC
entries), Hugo Extended 0.164.0 built the existing site in 7.855/12.323 seconds
and the Book variant in 13.288/13.936 seconds in alternating warm-cache runs.
The whole-Book document was 11,511,220 bytes; the generated depth-three ToC was
658,951 bytes of HTML and 560,163 bytes of Markdown. The aggregate contained
18,847 IDs with zero duplicates and 1,862 local fragment links with zero
missing decoded targets. These figures justify the explicit output opt-in;
they do not add a second `print_book` switch.

HTML renders semantic numbered figures, linked xrefs, the interactive shell,
and contained table overflow. Print keeps figures, captions, equations, IDs,
and complete tables but removes controls, pager, and scroll wrappers.
Markdown/LLMS emits `**Figure 2-1.** caption` (localized label), the original
body, and relative Markdown links for the shortcode forms; native forms pass
through as their source block plus attribute line because render hooks do not
run under `.RenderShortcodes`; Book ToC becomes a nested list. RSS uses the
same plain fallback for figures/tables/equations/examples/xrefs and strips Book
ToC.

## 6. Migration boundaries and non-goals

Part/chapter hierarchy remains content-tree or `data/docs_nav.json` data; OINK
does not synthesize a second chapter model. Theme output stops at print HTML.
PDF and EPUB pagination, font embedding, index generation, automatic figure
numbering, automatic heading numbering, glossary components, and Pandoc
network `--webtex` are outside this contract.

Source completion, the dual-Hugo matrix, a released immutable theme tag,
consumer pin updates, and hosted deployment are separate release states. This
contract records source behavior only.

The site-specific rewrites use
`scripts/migrations/book_figures.py`. Dry-run is the default; `--write`
is explicit, every run may emit a JSON inventory and diff digest, unknown
forms remain unchanged, and a second run must report zero changed files.
`scripts/check-book-migrations.py` freezes these safety properties for all
four profiles (`tpme`, `ddia-v2`, `ddia-v1`, and `pg-internal`). The version-2
rewrites (`example` → `eg`, `book-figures kind="tbl"` → `book-tables`) are
transformations of `scripts/migrations/oink06.py` (`eg`), which follows the
same dry-run / `--write` / idempotency rules.

## 7. Version 2 changes

- `example` (leaf, caption line only, not a target of `xref` or a Book list)
  is removed; `eg` is a wrapper with a required caption, a registered `eg`
  target, `xref eg=` support, and a `book-examples` list.
- Native forms for `fig`, `tbl`, `eq`, and `eg` (section 2) render through the
  image, table, passthrough, and code-block render hooks and register targets
  through the same partial as the shortcodes.
- `book-figures kind=` is removed; `book-tables`, `book-equations`, and
  `book-examples` are added.
- Target identity and Book-list order come from the source position instead
  of the shortcode ordinal.
- The `eq` label set gained `book_example` for `eg` (i18n key existed since
  0.4.1).
