---
title: Markmap
linkTitle: Markmap
description: A `markmap` fence turns a Markdown outline into an expandable, zoomable mind map — and the source stays a readable outline.
weight: 130
search_keywords: [Markmap, mind map, outline, tree diagram]
---

The body of a `markmap` fence is a plain Markdown outline: headings and lists
give the hierarchy, and the browser draws it as a tree you can expand and
collapse. It suits showing "what this section covers" at one glance. For flows
with direction and conditions, use [Mermaid](/docs/mermaid/).

## Shortest form {#minimal}

````markdown {title="Source"}
```markmap
# OINK
## Local-first
- every runtime ships with the theme
- no CDN involved
## Markdown-native
- components are fences and attribute lines
- usable without writing a shortcode
## Four output states
- HTML
- print
- Markdown
- RSS
```
````

```markmap
# OINK
## Local-first
- every runtime ships with the theme
- no CDN involved
## Markdown-native
- components are fences and attribute lines
- usable without writing a shortcode
## Four output states
- HTML
- print
- Markdown
- RSS
```

The first-level heading is the root; other headings and list items hang under it
by indentation. Click the dot on a node to fold or unfold that branch, scroll to
zoom, drag to pan. The toolbar at the bottom right offers zoom, fit-to-window
and download-as-SVG.

## Depth {#depth}

Deeper levels are set smaller and the canvas lays itself out. Below are the six
sections of this theme's documentation site and their page counts.

````markdown {title="Source"}
```markmap
# OINK documentation
## Introduction (4 pages)
### What it is
### Feature tour
### Showcase
### Licences
## Get started (3 pages)
### Fork this site
### Directory layout
### From scratch
## Authoring (8 pages)
### Organizing content
### Writing pages
### Front matter
### Blog
### Books
### Releases and downloads
### OpenAPI
## Components (22 pages)
### Callouts / tabs / steps / cards
### Images / galleries / tables / fields
### Diagrams: Mermaid / PlantUML / Markmap / ECharts
## Customization (15 pages)
### Branding / navigation / search / languages
### Landing / versions / taxonomies / print
## Operations (7 pages)
### Preview / deploy / upgrade
### Comments / analytics / troubleshooting
```
````

```markmap
# OINK documentation
## Introduction (4 pages)
### What it is
### Feature tour
### Showcase
### Licences
## Get started (3 pages)
### Fork this site
### Directory layout
### From scratch
## Authoring (8 pages)
### Organizing content
### Writing pages
### Front matter
### Blog
### Books
### Releases and downloads
### OpenAPI
## Components (22 pages)
### Callouts / tabs / steps / cards
### Images / galleries / tables / fields
### Diagrams: Mermaid / PlantUML / Markmap / ECharts
## Customization (15 pages)
### Branding / navigation / search / languages
### Landing / versions / taxonomies / print
## Operations (7 pages)
### Preview / deploy / upgrade
### Comments / analytics / troubleshooting
```

## Links, code and emphasis {#inline-markdown}

Nodes take inline Markdown: links are clickable, inline code is monospaced, bold
and italic behave as usual.

````markdown {title="Source"}
```markmap
# Everyday commands
## Preview
- `hugo server` — open [localhost:1313](http://localhost:1313/)
- `hugo server -D` — **including drafts**
## Build
- `hugo --printPathWarnings --panicOnWarning`
- `hugo --gc --minify` — for publishing
## Theme
- `hugo mod get -u github.com/pgsty/oink`
- [theme repository](https://github.com/pgsty/oink)
- [site source](https://github.com/pgsty/oink.pgsty.com)
```
````

```markmap
# Everyday commands
## Preview
- `hugo server` — open [localhost:1313](http://localhost:1313/)
- `hugo server -D` — **including drafts**
## Build
- `hugo --printPathWarnings --panicOnWarning`
- `hugo --gc --minify` — for publishing
## Theme
- `hugo mod get -u github.com/pgsty/oink`
- [theme repository](https://github.com/pgsty/oink)
- [site source](https://github.com/pgsty/oink.pgsty.com)
```

## Mathematics in nodes {#math}

The Markmap runtime carries a local KaTeX, so `$…$` inside a node renders as a
formula.

````markdown {title="Source"}
```markmap
# PostgreSQL metrics worth watching
## Cache hit ratio
- $\frac{blks\_hit}{blks\_hit + blks\_read}$
- below 0.99, look at shared_buffers
## Replication lag
- $lsn_{primary} - lsn_{replica}$
## Transaction throughput
- $TPS = \frac{\Delta xact\_commit}{\Delta t}$
```
````

```markmap
# PostgreSQL metrics worth watching
## Cache hit ratio
- $\frac{blks\_hit}{blks\_hit + blks\_read}$
- below 0.99, look at shared_buffers
## Replication lag
- $lsn_{primary} - lsn_{replica}$
## Transaction throughput
- $TPS = \frac{\Delta xact\_commit}{\Delta t}$
```

## Controlling the initial depth {#options}

The top of a fence body may carry Markmap's own YAML header — not Hugo front
matter. `initialExpandLevel` expands only the first few levels and leaves the
rest for the reader; `colorFreezeLevel` says from which level a branch keeps one
colour.

````markdown {title="Source"}
```markmap
---
markmap:
  initialExpandLevel: 2
  colorFreezeLevel: 2
---

# Check scripts in the theme repository
## Source-level contracts
### check-i18n.py
### check-taxonomy.py
### check-font-tokens.py
## Output-level checks
### check-output.py
### check-goldens.py
### check-code-blocks.py
### check-content-primitives.py
### check-media-primitives.py
## Browser runtimes
### node --test tests/js/**/*.test.js
```
````

```markmap
---
markmap:
  initialExpandLevel: 2
  colorFreezeLevel: 2
---

# Check scripts in the theme repository
## Source-level contracts
### check-i18n.py
### check-taxonomy.py
### check-font-tokens.py
## Output-level checks
### check-output.py
### check-goldens.py
### check-code-blocks.py
### check-content-primitives.py
### check-media-primitives.py
## Browser runtimes
### node --test tests/js/**/*.test.js
```

## Folded into a disclosure {#in-details}

Every map is a fixed 300 pixels tall, so three in a row eat a lot of page. Fold
a panoramic one into `> [!DETAILS]` and let the reader open it. Every line
inside the disclosure starts with `>`, fences included.

````markdown {title="Source"}
> [!DETAILS] What the theme repository looks like
> ```markmap
> # pgsty/oink
> ## layouts/
> - baseof.html and the per-type shells
> - _partials/shell/
> - _markup/ render hooks
> - _shortcodes/
> ## assets/
> - scss/ tokens and component styles
> - js/ browser runtimes
> - third_party/ libraries shipped with the theme
> ## i18n/
> - 32 locale files with identical keys
> ## docs/
> - maintainer contracts
> ```
````

> [!DETAILS] What the theme repository looks like
> ```markmap
> # pgsty/oink
> ## layouts/
> - baseof.html and the per-type shells
> - _partials/shell/
> - _markup/ render hooks
> - _shortcodes/
> ## assets/
> - scss/ tokens and component styles
> - js/ browser runtimes
> - third_party/ libraries shipped with the theme
> ## i18n/
> - 32 locale files with identical keys
> ## docs/
> - maintainer contracts
> ```

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | `<pre><code class="language-markmap">` first; the runtime replaces it with `<div class="markmap">` and draws the SVG |
| Print | Same as HTML: the print view loads the runtime too |
| Markdown | The `markmap` fence and its outline, kept as written |
| RSS | The outline source only — a readable outline for subscribers |

The outline is the content: wherever JavaScript does not reach, the full
hierarchy is still legible.

## Parameter reference {#reference}

Fence attributes: none. A `markmap` fence reads no attribute line; the height is
fixed by the theme at 300px (`.markmap > svg`) and the width fills the reading
column.

Site parameters (`hugo.yaml`):

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `params.markmap` | bool | `false` | With it off, the fence stays a code block and no runtime loads |
{.fields meta="type default"}

The key is defined in
[Configuration](https://oink.pgsty.com/docs/customize/config/). Per-map
behaviour goes in the `markmap:` YAML header at the top of the fence body
(`initialExpandLevel`, `colorFreezeLevel`, `maxWidth` …), which is Markmap
syntax; the accepted keys are in the
[Markmap documentation](https://markmap.js.org/docs/json-options).

## Limits {#limits}

- The output is an inline SVG fixed at 300px tall: one `.markmap > svg` rule
  decides it and the fence cannot change it. When a map has too many levels, use
  `initialExpandLevel` or split it in two. Inline SVG also means `{#id num=}`
  numbering and image zoom do not apply.
- No colour-scheme awareness: link colours come from Markmap's own palette, so
  check contrast in both modes.
- Without `params.markmap` it is only a code block: sites that do not use the
  component load no runtime.
- "Download SVG" in the toolbar is a browser action and exports a snapshot of
  the current expansion state.
- Avoid `<`, `>`, `&` and `"` in the outline: the current theme version
  double-escapes them and nodes show literal `&gt;` or `&#34;`. Write links as
  `[text](URL)` rather than as autolinks in angle brackets.

## Related {#related}

- [Mermaid](/docs/mermaid/) — diagrams with direction and conditions
- [File trees](/docs/filetree/) — more precise for directory structure
- [Callouts](/docs/callout/) — everything `[!DETAILS]` can do
- [Configuration](https://oink.pgsty.com/docs/customize/config/) — `params.markmap`
