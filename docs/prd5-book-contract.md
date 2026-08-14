# PRD 5 Book contract

Release assignment: OINK 0.4.0 (consolidated PRD 5 release)

Original design milestone: OINK 0.6.0

Contract version: 1

Status: frozen for OINK v0.4.0

Compatibility floor: Hugo Extended 0.160.1

This document freezes the originally planned 0.6 track of PRD 5, consolidated
into the v0.4.0 release. Its machine-readable companion
is `tests/fixtures/prd5/contract.json`; `scripts/check-prd5-contract.py` keeps
the two aligned. Configuration and migration recipes are available in
[English](prd5-migration-guide.md) and
[Simplified Chinese](prd5-migration-guide.zh.md).
The executable consumer recipes are frozen separately for
[TPME](prd5-migrate-tpme.md), [DDIA](prd5-migrate-ddia.md), and
[pg-internal](prd5-migrate-pg-internal.md).

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

The numbered forms of `fig`, `tbl`, and `eq` require a quoted `num` matching
`[0-9A-Za-z.-]+`. The default IDs are `fig-<num>`, `tbl-<num>`, and
`eq-<num>`; an explicit ID matching `[A-Za-z][A-Za-z0-9_.:-]*` is preserved
byte-for-byte. Number and ID are intentionally independent. A page rejects a
duplicate ID and rejects two components of one kind that claim the same
number with different IDs.

OINK 0.4 already defines parameter-free `{{< eq >}}` as an unnumbered
display-math escape hatch. It registers no target and therefore cannot be an
`xref` destination or appear in `book-figures`. Adding `num` selects the Book
form described here; `id`, `caption`, and `class` require that number.

Captions are plain text. Inner Figure and Table content is rendered through
the page's Markdown policy. Equation inner content is sent directly to the
local server-side KaTeX renderer, so `eq` works even when a consumer has not
enabled Goldmark passthrough delimiters.

`fig` accepts the DDIA compatibility parameter superset
`src`, `id`, `caption`, `title`, `class`, `link`, `alt`, `width`, and
`height`, in addition to `num`. `title` is a caption alias for mechanical
migration and is mutually exclusive with `caption`. `src` and inner content
are mutually exclusive. Width and height are positive integers; class tokens
and every URL are validated. When legacy source has no explicit `alt`, the
plain caption becomes its migration fallback. New content should state a
meaningful `alt` explicitly.

`tbl` wraps a Markdown table inside one semantic figure, keeping the label,
body, caption, and anchor together. `eq` presents the number on the right in
screen and print layouts. All three expose a semantic `<figure>` and
`<figcaption>` and do not use fake h6 captions.

## 3. Cross references and consistency

`xref` accepts exactly one optional kind key (`fig`, `tbl`, or `eq`), optional
`page`, and optional `anchor`. A kind supplies the localized default label and
derives the anchor when one is absent. An anchor-only reference requires inner
link text. `page` resolves through Hugo's current-language page lookup, so the
same source does not hard-code an `/en/` destination.

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

`{{< book-figures >}}` and `{{< book-figures kind="tbl" >}}` render ordered
Book-wide lists by triggering descendant content, then aggregating the
idempotent Page Store registration. The allowed kinds are `fig`, `tbl`, and
`eq`. The list links to stable public IDs and remains correct regardless of
which alternate output Hugo renders first.

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
body, and relative Markdown links; Book ToC becomes a nested list. RSS uses the
same plain fallback for figures/tables/equations/xrefs and strips Book ToC.

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
`scripts/migrations/prd5_book_migrate.py`. Dry-run is the default; `--write`
is explicit, every run may emit a JSON inventory and diff digest, unknown
forms remain unchanged, and a second run must report zero changed files.
`scripts/check-prd5-migrations.py` freezes these safety properties for all
four profiles (`tpme`, `ddia-v2`, `ddia-v1`, and `pg-internal`).
