# PRD 5 reading and release contract

Release assignment: OINK 0.4.0 (consolidated PRD 5 release)

Original design milestone: OINK 0.4.0

Contract version: 1

Status: frozen for OINK v0.4.0

Compatibility floor: Hugo Extended 0.160.1

This document freezes the 0.4 track of PRD 5. Its machine-readable companion
is `tests/fixtures/prd5/contract.json`; `scripts/check-prd5-contract.py` keeps
the two aligned. Configuration and migration recipes are available in
[English](prd5-migration-guide.md) and
[Simplified Chinese](prd5-migration-guide.zh.md).

## 1. Sequential reading pager

OINK enables sequential navigation by default for the `docs`, `book`, and
`blog` content types. A site can replace that set with
`params.ui.pager.types`; only those three type names are valid. A page or
section can opt out with the boolean front matter value `pager: false`.

Reading order is the pre-order traversal of the same navigation root used by
the sidebar: each section index precedes its visible children, ordinary Docs
and Book children use weight order, and a `data/docs_nav.json` tree is
authoritative when the docs sidebar uses one. Blog children share the sidebar's
ordering helper: explicitly weighted entries come first, then unweighted
entries in reverse chronological order. Pages hidden with `toc_hide`, link-only
placeholders using `manualLink`/`manualLinkRelref`, and `sidebar_divider` rows
are not pager destinations.

The docs navigation root defaults to the configured docs section. A site whose
manual pages intentionally live at the content root may set
`params.ui.docs_root: home`; the sidebar and pager then traverse the same home
tree, while top-level `toc_root: true` overview sections remain excluded. Any
value other than `home` or `section` is a build error.

Interactive HTML renders only the sides that exist and emits matching
`<link rel="prev">` / `<link rel="next">` elements in the document head.
These relations use `RelPermalink`, keeping client-side paging on the current
origin even when a development server overrides the configured base URL.
Print, Markdown, and RSS contain no pager markup or relations.

## 2. Mathematics passthrough

The theme owns `layouts/_markup/render-passthrough.html` and delegates it to
the existing server-side KaTeX renderer. Consuming sites remain responsible
for enabling Goldmark passthrough delimiters because Hugo does not merge theme
markup configuration. Formula pages load local KaTeX CSS conditionally; pages
without formulae do not. Long display formulae scroll within the document
column in screen output and remain static in print.

`{{< eq >}}...{{< /eq >}}` is the explicit display-math escape hatch for a
page whose consuming site cannot enable Goldmark passthrough. With no
parameters it sends non-empty TeX through the same local renderer, registers
no Book target, and emits a plain `$$` block in Markdown and RSS. The numbered
OINK 0.6 form adds `num`; `id`, `caption`, and `class` are rejected without
that number so an unnumbered equation cannot accidentally present a partial
Book identity. Neither form loads JavaScript.

## 3. Release primitives

`release` is a page-owned fact record. It is either a strict map with
`version` and `repo`, or the exact shorthand
`https://github.com/<owner>/<repo>/releases/tag/<tag>`. The map may also carry
`product`, `tag`, `date`, `prev`, and `checksums`; unknown keys and wrong types
are build errors. Missing `tag` becomes `v{version}`, and missing `date` uses
the page date. OINK derives every release, archive, checksum, compare, and
repository URL locally and never fetches release state.

`{{< release-card >}}` accepts no parameters. HTML receives a semantic link
card with no runtime; print and RSS receive a static link list; Markdown
receives pure Markdown links. Author-supplied release facts never appear in
the shortcode invocation.

A section opting into `layout: releases` ignores page weight and orders pages
by normalized release date descending, then valid SemVer precedence descending,
with deterministic lexical fallback for real-world non-SemVer release labels.
The default is one global time sequence. `release_group_by_product: true`
creates product subsections and requires every selected page to name a product.
`release_products` accepts one product string or an array and filters before
sorting/grouping. Invalid filters fail the build rather than yielding a
misleading empty release page.

## 4. Release assets and download data

`release-assets` accepts exact `sha*sum` lines or one `src` resource. It rejects
malformed lines with their line number, mixed checksum algorithms, an explicit
algorithm that disagrees with hash length, path-like filenames, and ambiguous
input sources. HTML gets linked assets and conditionally loaded copy controls;
print exposes full hashes without controls; Markdown and RSS receive full-hash
pipe tables. See `content-primitives.md` for the complete authoring contract.
Interactive HTML sets the Page Store flag `hasAssetList`, which is part of the
shared bundle key and loads only the local `asset-list.js` copy runtime. No
other component reads that flag, and non-HTML outputs never set it.

Download facts live in `data/download/<key>.yaml`. A record requires a string
version directly or through `site.Params.version`, and a non-empty channel
array. Every channel has a unique anchor-safe `id`, exactly one kind (`rolling`
or `pinned`), and a localized title. Localized fact fields resolve in this
order: `<field>_<exact language>`, `<field>_<primary language>`, `<field>`.
Only pinned `url` and `steps[].code` fields may expand `${version}` and `${tag}`;
rolling channels reject every interpolation token, and unknown or malformed
tokens fail in all channels. Other fields never interpolate.

`{{< download "key" >}}` accepts exactly one positional data key. HTML renders
an anchor-chip index and static-first channel sections. Code steps reuse OINK's
enhanced Chroma renderer and conditional copy runtime; checksum channels reuse
Release Assets. A record with `published: false` keeps rolling channels usable
but renders pinned channels as non-linking pending-release states, omits pinned
commands, and disables asset links and controls. Print statically expands the
same safe content, Markdown emits headings, source fences, and full hashes,
and RSS emits no download component.

## 5. Shared production-site compatibility

The theme supplies a production-safe `robots.txt`: production builds allow
all crawlers and publish the sitemap URL, while non-production builds disallow
all crawling. A site may still replace the template as one unit.

`params.ui.lastmod_commit` accepts `subject` (the compatibility default),
`hash`, or `none`. The first two link to the full commit when GitInfo and
`github_repo` are available; `none` keeps the last-modified date but omits the
commit link. Unknown values fail the build.

`sidebar_divider: true` turns a content placeholder into a non-link,
non-focusable sidebar grouping label. Sites normally combine it with
`build.render: never`; the page must remain listable so the sidebar can place
the label in weight order. Divider pages never enter the flattened pager chain.

`params.ui.section_index` accepts `list` (the compatibility default) or
`cards`. Cards reuse the content-card visual contract and derive their title,
description, icon, and destination from each visible child. `simple_list: true`
remains an explicit page-level compatibility override.

`data/docs_nav.json` is an authoritative explicit docs tree. Every node names
a Hugo page and may provide children; missing pages fail the build. Front
matter `manualLink` or `manualLinkRelref` creates a visible link-only ghost
page, normally paired with `build.render: link`, whose title remains in the
sidebar but whose content page is not a pager destination. `manualLinkTitle`
and `manualLinkTarget` customize link metadata.

Sites may override `hooks/search-keywords-extra.html` and return an array of
page-specific strings. OINK appends, trims, and filters those strings through
the same normalization as `search_keywords`; a non-array return is a build
error. This lets sites add issue numbers, aliases, or archive labels without
forking the search metadata partial.

Markdown tables are wrapped in a keyboard-focusable contained scroll region;
`{.full-width}` expands that region to the article canvas. See
`content-primitives.md` for the normative table output contract. The 404 page
is a complete interactive document rather than a block definition, making its
base deterministic in multilingual multi-output builds. Narrow shell pages
reserve the sticky subnav height through `--td-scroll-padding-top`, so deep
anchors remain visible below the chrome.
