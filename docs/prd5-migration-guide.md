# OINK PRD 5 migration and configuration reference

Consolidated release: OINK 0.4.0 (Reading & Release, Landing, and Book)

Original design milestones: OINK 0.4.0 (Reading & Release), OINK 0.5.0
(Landing), and OINK 0.6.0 (Book)

This guide covers the source frozen for the consolidated v0.4.0 release. A
consumer may call a feature released only after the signed tag resolves, the
site pins that tag, and its rendered output passes smoke tests. Normative
decisions live in the
[reading/release](prd5-reading-release-contract.md),
[landing](prd5-landing-contract.md), and
[Book](prd5-book-contract.md) contracts.

## Release gates {#release-gates}

Treat these as separate evidence states:

1. source complete in the theme checkout;
2. validated on Hugo Extended 0.160.1 and the current matrix version;
3. published as an immutable signed theme tag;
4. documented by a consumer pinned to that tag;
5. deployed and checked at the hosted URL.

Do not copy an example into a site pinned to an older version and infer that
the older theme supports it. Pin a concrete release in `go.mod`; do not use
`@latest` as production policy.

## Reading and release adoption {#reading-and-release-adoption}

Pager is on for `docs`, `book`, and `blog`; set a deliberate site list or opt a
page out:

```yaml
params:
  ui:
    pager:
      types: [docs, book, blog]
---
pager: false
```

Manuals normally live below the configured docs section. When docs pages are
deliberately rooted at `/` and `/docs/` is only an overview, make that
information architecture explicit instead of forking the sidebar:

```yaml
params:
  ui:
    sidebar_root_enabled: true
    docs_root: home
```

`docs_root` accepts only `section` (the default) or `home`; the same resolved
root drives both the visible tree and pager order.

When a site has `data/docs_nav.json`, that explicit tree is also pager order.
Keep `manualLink` link-only pages and `sidebar_divider` labels in the tree;
they remain visible navigation but are skipped as reading destinations.

Delimiter mathematics requires consumer Goldmark configuration because Hugo
does not merge theme `markup` settings:

```yaml
markup:
  goldmark:
    extensions:
      passthrough:
        enable: true
        delimiters:
          block: [['\[', '\]'], ['$$', '$$']]
          inline: [['\(', '\)']]
```

The theme supplies the render hook and local KaTeX CSS. `math: true` alone has
no meaning. Build at least one page containing inline and block delimiters and
confirm it contains rendered MathML rather than literal `$$`.

When a site cannot enable passthrough yet, use the strict display-only escape
hatch without changing site configuration:

```go-html-template
{{< eq >}}E = mc^2{{< /eq >}}
```

This parameter-free form has no number, anchor, caption, or Book registry
entry. Add `num="5.3"` only when adopting the numbered 0.6 Book component.

Release facts belong to page front matter:

```yaml
release:
  version: 1.7.0
  repo: pgsty/pig
  tag: v1.7.0
  prev: v1.6.0
  checksums: SHA256SUMS
```

Then author `{{< release-card >}}` and, on the same page,
`{{< release-assets src="release/SHA256SUMS" >}}`. For downloads, commit one
`data/download/<key>.yaml` record and consume it from both
`{{< download "key" >}}` and a landing `download` section. Keep rolling
channels version-free; only pinned channels interpolate `${version}` and
`${tag}`.

Site override removal checklist:

- delete local passthrough hooks only after the theme pin contains the hook;
- delete copied `robots.txt`, 404, lastmod, section-index, search-metadata, or
  sidebar-tree partials only after comparing their actual local deltas;
- replace decorative sidebar placeholders with `sidebar_divider: true` and
  `build.render: never` while retaining list visibility;
- enable Goldmark block attributes before relying on `{.full-width}`.

## Landing migration {#landing-migration}

Convert a standalone page shell to content plus local data:

```yaml
---
title: Pricing
layout: landing
landing: pricing
---
```

Put narrative data in `data/landing/pricing/<lang>.yaml`, or use one shared
fact file with suffixes such as `title_zh_cn`, `title_zh`, and `title`. Inline
`sections` are useful for a one-off page. Keep the homepage at `data/home/`;
it already uses the same internal dispatcher.

Map site templates to registry sections in this order:

1. migrate navbar/footer wrappers and remove duplicate page chrome;
2. migrate pricing, `pricing-compare`, commands, steps, timelines, code plates,
   case studies, downloads, and normalized bar charts to data;
3. replace copied reveal/count/copy/image/menu JavaScript with `hasLanding`;
4. convert hand-duplicated marquees to one item array;
5. test static content with JavaScript disabled and with reduced motion.

Do not put API fetches in a section. Refresh GitHub stars, pricing facts,
avatars, and screenshots in site CI, then commit or generate local data before
Hugo runs. The browser must not fetch mutable facts.

The old Docsy block shortcodes remain compatible but are deprecated. Migrate
new work to landing data; do not translate a page into another layer of custom
HTML partials.

## Book starter and stable anchors {#book-starter-and-stable-anchors}

A Book root declares the type and cascades it to descendants. A consumer must
also request print and Markdown outputs where desired:

```yaml
---
title: Systems Handbook
type: book
book_kind: book
book_number: B
outputs: [HTML, print, markdown]
cascade:
  type: book
---
```

Site configuration:

```yaml
outputs:
  # Use home instead when the Book root is the site root.
  section: [HTML, print]
params:
  ui:
    shell_types: [docs, book, blog, swagger]
    sidebar_headings: 3
    book_draft_banner: true
```

Add `book_number`, `book_kind`, and optional `book_status: draft` to chapters.
Use explicit heading anchors before replacing existing cross-page URLs:

```markdown
## Synchronous replication {#sec_replication_sync}

See {{< xref page="../replication" anchor="sec_replication_sync" >}}synchronous replication{{< /xref >}}.
```

Never rely on generated heading IDs for a public glossary/index/reference.
Run `python3 scripts/check-book.py` after every numbered-reference rewrite.
Whole-Book print namespaces Markdown heading IDs by source page so repeated
names remain valid in one document. Book ToC, `xref`, and figure-list links
become document-local; ordinary Markdown cross-page URLs intentionally remain
site URLs, so migrate citations that must work inside the aggregate to
`xref`.

## Figure migration recipes {#figure-migration-recipes}

DDIA v2 calls can be migrated mechanically because `fig` accepts the existing
`src/id/caption/title/class/link/alt/width/height` surface. Add quoted `num`
from the existing caption and prefer an explicit meaningful `alt`:

```markdown
{{< fig num="2-1" id="office_2003" src="/fig/tpme_0201.png"
    caption="The cluttered Word 2003 interface" alt="Word 2003 interface with stacked toolbars" />}}
```

For DDIA v1, design a one-time site script that:

1. inventories each bare image and its following caption paragraph;
2. derives a proposed number without changing paths;
3. rewrites image links that masquerade as references into `xref` calls;
4. stops on missing/ambiguous captions rather than guessing;
5. runs the Book checker and compares rendered anchor counts before commit.

For pg-internal, inventory the four caption forms and 90 plain-text mentions.
Wrap each table/image and replace only unambiguous `Figure N`/`Table N`
mentions; report the three missing captions and two empty alternatives for
manual repair. For tpme, convert each fake h6 caption plus image to one `fig`,
preserve its semantic O'Reilly ID, then turn `/en/...#anchor` links into
language-relative `xref page=... anchor=...` calls.

These are script designs, not theme commands: content naming and ambiguity are
site facts. Always run them on a branch, retain a machine-readable before/after
inventory, and review every skipped record.

OINK now ships one dry-run-first executable with three observed-site recipes:

- [TPME](prd5-migrate-tpme.md): fake h6 captions, numbered tables, and all
  Simplified Chinese `/en/` fragment leaks;
- [DDIA](prd5-migrate-ddia.md): v2 figure/table/example disambiguation and v1
  bare-image pairing;
- [pg-internal](prd5-migrate-pg-internal.md): adjacent caption/image pairs,
  tables, and order-independent numbered prose references.

Each recipe records its clean-checkout inventory, exact command line, skipped
forms, temporary-clone strict-build evidence, and the required zero-change
second run. The shared tool is
`scripts/migrations/prd5_book_migrate.py`; its safety contract is covered by
`scripts/check-prd5-migrations.py` in both Hugo matrix jobs.

## Part hierarchy and whole-Book output {#part-hierarchy-and-whole-book-output}

Use directories for natural hierarchy or an existing `data/docs_nav.json` to
place parts and chapters without moving URLs. Do not recreate a parallel
`chapters.yaml` model solely for templates. `{{< book-toc depth=3 >}}` consumes
the same tree and Hugo fragment data; `{{< book-figures >}}` aggregates stable
numbered targets.

The Book root print URL is the whole-book HTML surface. It preserves anchors
and makes cross-chapter links local. PDF/EPUB pagination remains site-owned;
do not restore network `pandoc --webtex` merely to render equations already
available as local KaTeX/MathML.

## Validation checklist {#validation-checklist}

- [ ] `python3 scripts/check-prd5-contract.py` passes.
- [ ] `check-prd5-reading.py`, `check-release-assets.py`,
      `check-download.py`, `check-landing.py`, `check-book.py`, and
      `check-prd5-misc.py` pass on both supported Hugo versions.
- [ ] `python3 scripts/check-content-primitives-contract.py` and
      `python3 scripts/check-i18n.py` pass.
- [ ] `node --test 'tests/js/**/*.test.js'` passes.
- [ ] Root and `/preview/` builds retain internal URL prefixes.
- [ ] HTML, print, Markdown, and RSS match the component output matrix.
- [ ] Landing works without JavaScript and under reduced motion/forced colors.
- [ ] Book xrefs, target numbers, image alternatives, and whole-book IDs pass.
- [ ] English/Chinese docs and stable anchors have parity.
- [ ] Consumer CI, hosted smoke tests, and public release state are recorded
      separately from local theme validation.
