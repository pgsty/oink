# OINK PRD 5 reading and release migration reference

Version assignment: OINK 0.4.0

This guide covers the 0.4 Reading & Release source contract. Source state, a
validated checkout, an immutable signed tag, a consumer pin, and a hosted
deployment are separate evidence. The normative decisions live in the
[reading/release contract](prd5-reading-release-contract.md), with a
machine-readable companion at `tests/fixtures/prd5/contract.json`.

Compatibility floor: Hugo Extended 0.160.1.

## Release gates {#release-gates}

Record these states independently:

1. the source change is complete in the theme checkout;
2. both supported Hugo versions and the focused contracts pass;
3. an immutable signed OINK 0.4.0 tag resolves;
4. the consumer pins that exact tag in `go.mod`;
5. the hosted output passes URL, language, and browser smoke tests.

Do not use `@latest` as production policy and do not infer hosted delivery
from a local build.

## Reading navigation {#reading-navigation}

Pager is enabled for `docs`, `book`, and `blog`. A site can replace that set,
and a page can opt out:

```yaml
params:
  ui:
    pager:
      types: [docs, book, blog]
---
pager: false
```

Docs and generic book pages follow the same pre-order tree shown by the
sidebar. Blog pages retain time order. When `data/docs_nav.json` exists, its
visible page tree is authoritative; link-only pages and `sidebar_divider`
labels remain visible but are not reading destinations.

A manual rooted at the site home can share one tree between sidebar and pager:

```yaml
params:
  ui:
    sidebar_root_enabled: true
    docs_root: home
```

`docs_root` accepts only `section` or `home`. HTML emits pager cards and
same-origin `rel=prev` / `rel=next` links. Print, Markdown, and RSS strip them.

## Mathematics {#mathematics}

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

OINK supplies the render hook and local KaTeX CSS. `math: true` alone has no
meaning. If a site cannot enable passthrough yet, use the strict display-only
escape hatch:

```go-html-template
{{< eq >}}E = mc^2{{< /eq >}}
```

The 0.4 form accepts no parameters and creates no number, caption, anchor, or
Book target. HTML and print receive local KaTeX/MathML; Markdown and RSS keep a
plain `$$` TeX block.

## Release pages {#release-pages}

Release facts belong to page front matter:

```yaml
release:
  version: 1.7.0
  repo: pgsty/pig
  product: PIG
  tag: v1.7.0
  prev: v1.6.0
  checksums: SHA256SUMS
```

Use `{{< release-card >}}` to render repository, archive, checksum, and compare
links without a network request. Use
`{{< release-assets src="release/SHA256SUMS" >}}` for committed checksum data.
The asset table loads `asset-list.js` only in interactive HTML; print,
Markdown, and RSS expose full hashes without controls.

A release section may declare `layout: releases`; it orders releases by date
and SemVer rather than page weight. Product grouping and filtering are opt-in.

## Download data {#download-data}

Commit one `data/download/<key>.yaml` fact record:

```yaml
version: 1.7.0
published: true
channels:
  - id: source
    kind: rolling
    title: Source repository
    url: https://github.com/pgsty/pig
  - id: binary
    kind: pinned
    title: Versioned archive
    url: https://github.com/pgsty/pig/releases/download/${tag}/pig-${version}.tar.gz
```

Render it with `{{< download "key" >}}`. Rolling channels reject interpolation;
only pinned URLs and code steps may expand `${version}` and `${tag}`. A record
with `published: false` keeps rolling channels usable while rendering pinned
channels as pending, with no misleading link or command. RSS strips the
component; print and Markdown retain safe static instructions.

## Shared override removal {#shared-overrides}

Remove a consumer override only after comparing its real delta against the
pinned theme. OINK 0.4 includes the passthrough hook, production-aware
`robots.txt`, deterministic 404 output, last-commit modes, full-width table
rendering, card section indexes, sidebar dividers, explicit navigation-tree
support, and the search-keyword extension hook. Keep site policy and content
facts in the site repository.

## Validation checklist {#validation-checklist}

- [ ] `python3 scripts/check-prd5-contract.py` passes.
- [ ] `check-prd5-reading.py`, `check-release-assets.py`, `check-download.py`,
      and `check-prd5-misc.py` pass on Hugo Extended 0.160.1 and 0.164.0.
- [ ] `python3 scripts/check-content-primitives-contract.py` and
      `python3 scripts/check-i18n.py` pass.
- [ ] `node --test 'tests/js/**/*.test.js'` passes.
- [ ] Strict root and `/preview/` builds preserve their deployment prefix.
- [ ] HTML, print, Markdown, and RSS follow the frozen output matrix.
- [ ] The consumer pin, CI result, signed tag, and hosted deployment are each
      verified independently.
