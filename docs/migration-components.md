# Component migration and configuration reference

Base consolidated release: OINK 0.4.0 (Reading & Release, Landing, and Book)

Presentation update: OINK 0.4.1 (`reading_width`, `example`, `contributors`,
and Landing Hero `title_size`); component API v5 (OINK 0.5/0.6): `example`
became the `eg` wrapper with a native fence form, `book-figures kind=` became
`book-tables` / `book-equations` / `book-examples`, and every numbered kind
gained a native form (see `docs/book-contract.md` version 2)

Original design milestones: OINK 0.4.0 (Reading & Release), OINK 0.5.0
(Landing), and OINK 0.6.0 (Book)

This guide covers the source frozen for the consolidated v0.4.0 release and
the backward-compatible presentation additions in v0.4.1. A consumer may call
a feature released only after the signed tag resolves, the site pins that tag,
and its rendered output passes smoke tests. Normative decisions live in the
[reading/release](reading-release-contract.md),
[landing](landing-contract.md), and
[Book](book-contract.md) contracts.

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
    pager_types: [docs, book, blog]
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
    docs_sidebar_root: home
```

`docs_sidebar_root` accepts only `section` (the default) or `home`; the same
resolved root drives both the visible tree and pager order.

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
- delete copied `robots.txt`, 404, lastmod, td-section-index, search-metadata, or
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

Hero data may set `title_size` to a CSS length in `rem`, `em`, or `px`. It
caps the large-screen display title without replacing OINK's smaller
responsive breakpoints:

```yaml
hero:
  title: A deliberately long landing title
  title_size: 4.45rem
```

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
  # slim | normal | wide; Book defaults to normal.
  reading_width: normal
  ui:
    shell_types: [docs, book, blog, swagger]
    # Keep false when the right outline already carries page headings.
    sidebar_headings: false
    book_draft_banner: true
```

`reading_width` controls only the inner Book measure: `slim` is a compact
prose column, `normal` aligns prose with normal figures and code, and `wide`
fills the article canvas. It is independent from the outer `page_width` shell
and can be overridden in page front matter with the same key.

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

Code and data samples that need a visible label but must stay out of Hugo's
heading outline use `eg` (a numbered example wrapper, or the native
single-fence form) instead of a fake h4/h6 caption:

````markdown
{{< eg num="2-1" id="example-query" caption="Querying the current snapshot" >}}
```sql
SELECT * FROM snapshot;
```
{{< /eg >}}

```sql {num="2-2" caption="The same example as one fence" #example-native}
SELECT * FROM snapshot;
```
````

The `eg` target is referenced with `{{< xref eg="2-1" >}}` and listed by
`{{< book-examples >}}`; `scripts/migrations/oink06.py migrate --only eg` rewrites
the removed leaf `example` form.

For a content-page contributor wall, create `data/contributors.yaml` with an
`items` list of GitHub handles and render it with
`{{< contributors data="contributors" >}}`. Optional `name`, `role`, `url`,
and `avatar` fields stay local to the data file; no runtime API is required.
An omitted avatar becomes a local initial placeholder. Prefer committed,
root-relative avatar paths when a portrait is required.

When a Book's legacy convention is not one of the shapes below, design a
one-time site script that:

1. inventories each legacy target and the caption text attached to it;
2. derives a proposed number without changing paths;
3. rewrites prose links that masquerade as references into `xref` calls;
4. stops on missing or ambiguous captions rather than guessing;
5. runs the Book checker and compares rendered anchor counts before commit.

These are script designs, not theme commands: content naming and ambiguity are
site facts. Always run them on a branch, retain a machine-readable before/after
inventory, and review every skipped record.

OINK ships one dry-run-first executable, `scripts/migrations/book_figures.py`.
Its profiles are named after the corpora they were derived from; each
recognizes one family of pre-Book conventions and reports anything it cannot
resolve instead of guessing:

| Profile | Legacy shape it recognizes |
| --- | --- |
| `tpme` | fake h6 captions above an image, numbered tables, and cross-language `/en/…#anchor` fragment leaks |
| `ddia-v2` | one site-local `figure` shortcode that conflates figures, numbered tables, and code examples |
| `ddia-v1` | a bare image followed by a caption paragraph, plus image links that stand in for references |
| `pg-internal` | adjacent caption/image pairs, numbered tables, and order-independent numbered prose references |

The tool defaults to a report; `--write` is explicit, and a second run over the
same tree must change nothing. Its safety contract is covered by
`scripts/check-book-migrations.py` in both Hugo matrix jobs.

## Part hierarchy and whole-Book output {#part-hierarchy-and-whole-book-output}

Use directories for natural hierarchy or an existing `data/docs_nav.json` to
place parts and chapters without moving URLs. Do not recreate a parallel
`chapters.yaml` model solely for templates. `{{< book-toc depth=3 >}}` consumes
the same tree and Hugo fragment data; `{{< book-figures >}}`, `{{< book-tables >}}`,
`{{< book-equations >}}`, and `{{< book-examples >}}` aggregate stable numbered
targets (one kind each).

The Book root print URL is the whole-book HTML surface. It preserves anchors
and makes cross-chapter links local. PDF/EPUB pagination remains site-owned;
do not restore network `pandoc --webtex` merely to render equations already
available as local KaTeX/MathML.

## Validation checklist {#validation-checklist}

- [ ] `python3 scripts/check-component-contract.py` passes.
- [ ] `check-reading.py`, `check-release-assets.py`,
      `check-download.py`, `check-landing.py`, `check-book.py`, and
      `check-shared-scenarios.py` pass on both supported Hugo versions.
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
