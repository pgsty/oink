---
title: Infographic
linkTitle: Infographic
description: An `infographic` fence picks an AntV template and renders a title plus a list of items as a flow, timeline, funnel, grid or hierarchy.
icon: fa-solid fa-shapes
weight: 160
search_keywords: [Infographic, AntV, flow, timeline, funnel, template]
---

An `infographic` fence picks an AntV template and renders "a title plus a list
of items" as an infographic. Use it for structure: order, hierarchy, comparison.
When you need axes and numeric precision use
[ECharts](/docs/echarts/); when you need a flow with conditional
branches use [Mermaid](/docs/mermaid/). The fence body is data, and
it stays readable text on GitHub.

## Shortest form {#minimal}

The first line is `infographic <template>`, followed by a `data` block: `title`
is the title and every entry under `items` needs at least a `label`.

````markdown {title="Source"}
```infographic
infographic list-row-simple-horizontal-arrow
data
  title Three steps in one documentation change
  items
    - label Write
      desc Start with the source language
    - label Check
      desc Zero build warnings, every example really rendered
    - label Ship
      desc Add the translated peer, open the PR
```
````

```infographic
infographic list-row-simple-horizontal-arrow
data
  title Three steps in one documentation change
  items
    - label Write
      desc Start with the source language
    - label Check
      desc Zero build warnings, every example really rendered
    - label Ship
      desc Add the translated peer, open the PR
```

Indentation decides the structure, two spaces per level. Keep labels short and
put the explanation in `desc`.

## Timelines {#timeline}

The `sequence-timeline-*` family lays the items out on a time axis, with `label`
as the point in time and `desc` as the event.

````markdown {title="Source"}
```infographic {height="420px"}
infographic sequence-timeline-simple
data
  title The last five PostgreSQL major versions
  items
    - label 2021
      desc 14: another round of parallel query and logical replication work
    - label 2022
      desc 15: the MERGE statement
    - label 2023
      desc 16: logical replication from a standby
    - label 2024
      desc 17: incremental backup and JSON_TABLE
    - label 2025
      desc 18: the asynchronous IO subsystem
```
````

```infographic {height="420px"}
infographic sequence-timeline-simple
data
  title The last five PostgreSQL major versions
  items
    - label 2021
      desc 14: another round of parallel query and logical replication work
    - label 2022
      desc 15: the MERGE statement
    - label 2023
      desc 16: logical replication from a standby
    - label 2024
      desc 17: incremental backup and JSON_TABLE
    - label 2025
      desc 18: the asynchronous IO subsystem
```

## Funnels {#funnel}

`sequence-funnel-simple` draws stages that narrow. Below are the theme's five
release states: they are not interchangeable, and only the last one is live.

````markdown {title="Source"}
```infographic {height="420px"}
infographic sequence-funnel-simple
data
  title The five states a theme release passes through
  items
    - label Source complete
      desc The code is written, and that is all
    - label Validated
      desc Theme checks and the site suite are green
    - label Published
      desc An immutable signed tag, resolvable through the Go proxy
    - label Documented
      desc The documentation site pins that tag
    - label Deployed
      desc Production runs this version
```
````

```infographic {height="420px"}
infographic sequence-funnel-simple
data
  title The five states a theme release passes through
  items
    - label Source complete
      desc The code is written, and that is all
    - label Validated
      desc Theme checks and the site suite are green
    - label Published
      desc An immutable signed tag, resolvable through the Go proxy
    - label Documented
      desc The documentation site pins that tag
    - label Deployed
      desc Production runs this version
```

## Grid cards {#grid}

When items have no order between them, `list-grid-*` arranges them in a grid
rather than a queue.

````markdown {title="Source"}
```infographic {height="380px"}
infographic list-grid-compact-card
data
  title One page, four outputs
  desc Every content component has to produce something usable in all four
  items
    - label HTML
      desc Interactive, runtimes loaded on demand
    - label Print
      desc Disclosures expanded, zoom and copy removed
    - label Markdown
      desc Plain text, compared byte for byte against goldens
    - label RSS
      desc Static, from the same source as print
```
````

```infographic {height="380px"}
infographic list-grid-compact-card
data
  title One page, four outputs
  desc Every content component has to produce something usable in all four
  items
    - label HTML
      desc Interactive, runtimes loaded on demand
    - label Print
      desc Disclosures expanded, zoom and copy removed
    - label Markdown
      desc Plain text, compared byte for byte against goldens
    - label RSS
      desc Static, from the same source as print
```

## Items with values {#values}

Add `value` to an item and templates that express proportion — pies, doughnuts,
progress — will use it.

````markdown {title="Source"}
```infographic {height="400px"}
infographic chart-pie-donut-plain-text
data
  title How the 29 shortcodes break down
  items
    - label Core components
      value 14
    - label Book numbering and indexes
      value 10
    - label Releases and downloads
      value 3
    - label OpenAPI
      value 2
```
````

```infographic {height="400px"}
infographic chart-pie-donut-plain-text
data
  title How the 29 shortcodes break down
  items
    - label Core components
      value 14
    - label Book numbering and indexes
      value 10
    - label Releases and downloads
      value 3
    - label OpenAPI
      value 2
```

## Hierarchy and hand-drawn style {#hierarchy-and-theme}

Items can nest through `children`, and `hierarchy-mindmap-*` draws two levels of
structure. A top-level `theme` block changes the whole look; `type` takes
`light`, `dark` or `hand-drawn`.

````markdown {title="Source"}
```infographic {height="320px"}
infographic hierarchy-mindmap-level-gradient-compact-card
theme
  type hand-drawn
data
  root
    label Theme repository
    children
      - label layouts
        desc templates
        children
          - label _markup
            desc render hooks
          - label _partials
            desc shell and helpers
      - label assets
        desc resources
        children
          - label scss
            desc tokens and component styles
          - label js
            desc browser runtimes
          - label third_party
            desc libraries shipped with the theme
```
````

```infographic {height="320px"}
infographic hierarchy-mindmap-level-gradient-compact-card
theme
  type hand-drawn
data
  root
    label Theme repository
    children
      - label layouts
        desc templates
        children
          - label _markup
            desc render hooks
          - label _partials
            desc shell and helpers
      - label assets
        desc resources
        children
          - label scss
            desc tokens and component styles
          - label js
            desc browser runtimes
          - label third_party
            desc libraries shipped with the theme
```

`theme` belongs to the DSL, not to the fence attributes, and it does not follow
the site's colour scheme: a diagram with `type dark` stays dark on a light page.
Check contrast in both modes.

## Picking a template {#templates}

Template names are `structure-variant`, and one structure has several visual
variants. The common families:

| Structure prefix | What it expresses | Example |
| --- | --- | --- |
| `list-row-*` `list-column-*` | Items in a row or a column | `list-row-simple-horizontal-arrow` |
| `list-grid-*` | A grid, no order between items | `list-grid-compact-card` `list-grid-badge-card` |
| `list-pyramid-*` `sequence-funnel-*` | Narrowing stages | `sequence-funnel-simple` |
| `sequence-timeline-*` `sequence-roadmap-vertical-*` | Timelines and roadmaps | `sequence-timeline-simple` |
| `sequence-steps-*` `sequence-snake-steps-*` | Ordered steps | `sequence-steps-simple` |
| `compare-binary-horizontal-*` `compare-quadrant-*` | Binary comparison and quadrants | `compare-binary-horizontal-simple-vs` |
| `hierarchy-mindmap-*` `hierarchy-structure-*` | Hierarchy, with `children` | `hierarchy-mindmap-level-gradient-compact-card` |
| `chart-pie-*` `chart-bar-*` `chart-column-*` | Illustrative charts, with `value` | `chart-pie-donut-plain-text` |
| `relation-network-*` `relation-dagre-flow` | Networks and flows, with `relations` | `relation-dagre-flow` |

Choose the smallest form that makes the relationship clear. The full gallery is
at [AntV Infographic](https://infographic.antv.vision/gallery), and the template
names match the version shipped with the theme.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | A canvas container inside `<div class="td-infographic">` plus the DSL; the local AntV runtime draws the SVG |
| Print | No diagram; the DSL source inside `<pre class="td-infographic-source">` |
| Markdown | The `infographic` fence and its DSL, kept as written |
| RSS | Same as print — source only |

Whatever the diagram says, say it in the prose too: print and RSS carry the DSL
and nothing else.

## Parameter reference {#reference}

The fence attribute line (```` ```infographic {…} ````):

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `height` | `auto` or a CSS length | `auto` | A non-negative number plus `px` `rem` `em` `vh` `vw` `%`; anything else fails the build |
| `full` | bool | `false` | `true` drops the reading-column limit |
| `class` | space-separated classes | — | Passed through to the container |
{.fields meta="type default"}

`style`, `on*` and unknown attributes fail the build, and so does an empty DSL
body.

The DSL's top-level keys (AntV's, not the theme's):

| Key | Description |
| --- | --- |
| `infographic` / `template` | The template name, on the first line |
| `data` | `title`, `desc`, `items` (or `sequences`, `compares`, `nodes`, `values`, `relations`, `root`, depending on the structure), `order` |
| `theme` | `type` (`light` / `dark` / `hand-drawn`), `palette`, `colorPrimary`, `stylize` … |
| `width` / `height` | Canvas size at the DSL level; usually left to the fence's `height` |
| `design` | Per-part tuning; rarely needed |
{.fields}

Each entry under `items` accepts `label`, `desc`, `value`, `icon`, `children`,
`group` and `id`. The DSL is defined by the
[AntV Infographic documentation](https://infographic.antv.vision/learn); the
version shipped with the theme and its checksum are recorded in the theme's
`VENDOR.json`.

## Limits {#limits}

- A wrong template name does not fail the build: Hugo checks the fence
  attributes only, the DSL is parsed by the browser runtime, and a missing
  template shows a line of error text in the container. Check the page after
  changing a template name.
- No colour-scheme awareness: `theme` lives in the DSL, so check contrast in
  both modes.
- Print and RSS carry the DSL only, so the conclusion belongs in the prose.
- SVG is not a semantic structure: the order a screen reader gets is not
  necessarily the visual order. Prefer headings, lists and tables when they can
  say it.
- Keep labels short: long text is truncated or squeezed on a narrow screen, so
  check at phone width after editing.

## Related {#related}

- [ECharts](/docs/echarts/) — when you need axes and exact numbers
- [Steps](/docs/steps/) — when the reader has to follow the procedure
- [Cards](/docs/cards/) — a grid of clickable entry points
- [Mermaid](/docs/mermaid/) — flows with branches and conditions
