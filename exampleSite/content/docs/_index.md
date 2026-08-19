---
title: Docs
linkTitle: Docs
description: Markdown Component Examples
icon: fa-solid fa-cubes
weight: 10
search_keywords: [components, cheatsheet, Markdown syntax, shortcode, native form]
cascade:
  type: docs
  # Every component page repeats the same section anchors (#minimal, #outputs,
  # #reference, #limits, #related). The section print aggregate concatenates
  # its pages without namespacing page-local IDs — unlike whole-Book print —
  # so the reference stays out of the aggregate instead of emitting 21
  # duplicate IDs.
  no_print: true
---

This section answers one question: how do I write this component in Markdown?
Every page has the same shape — the shortest example, progressively richer
examples, the output matrix, the parameter table, the limits. For syntax at a
glance, use the cheatsheet below.

## Two forms {#two-forms}

A component's first form is Markdown itself: blockquotes, lists, tables,
images, fences — plus a single `{…}` attribute line right after them. The
native form stays readable on GitHub and in any Markdown editor, and the
Markdown output keeps the source rather than the rendered HTML.

Whatever the native form cannot express is a shortcode: tabs in running text,
parameter tables with block-level descriptions, cards with icons and badges,
terminal recordings. Five rules cover them:

- Every shortcode is written `{{</* name */>}}`. Only `{{%/* steps */%}}` uses
  the `%` delimiter, because its body is page-level Markdown.
- Nested names (`tab`, `card`, `field`) are valid only inside their parent.
- A bad parameter never degrades silently. The build fails, and the error names
  the file and the line.
- Public string parameters (captions, labels, titles) are plain text and are
  not parsed as Markdown. Only bodies are Markdown: `tab`, `card` and `field`
  bodies, files pulled in by `include`, and the Book `fig` / `tbl` / `eg`
  bodies.
- A component the page never used ships no runtime. The scripts are
  concatenated from what this page actually used; print, Markdown and RSS
  output load nothing at all.

## Site prerequisites {#prerequisites}

Components depend on three Goldmark settings. This example site already has
them; copy the snippet when starting from scratch:

```yaml {title="hugo.yaml"}
markup:
  goldmark:
    renderer:
      unsafe: true # keep HTML that content emits
    parser:
      attribute:
        block: true # enable {…} attribute lines
      wrapStandAloneImageWithinParagraph: false # standalone images are not wrapped in <p>
```

- `renderer.unsafe: true` — Goldmark drops raw HTML in content by default;
  with it off, HTML nested inside component bodies disappears.
- `parser.attribute.block: true` — the master switch for attribute lines. With
  it off, `{.steps}` and `{caption="…"}` are just a line of text.
- `parser.wrapStandAloneImageWithinParagraph: false` — a standalone image is no
  longer wrapped in `<p>`, so it can become a captioned figure and an attribute
  line can follow it.

A few components have their own prerequisites: mathematics needs Goldmark
passthrough, PlantUML and Draw.io need a rendering server you run yourself.
Each page says so.

## Cheatsheet {#cheatsheet}

The *Shortest form* column gives each component's minimal syntax: an attribute
line after ordinary Markdown, a fenced block with a language tag, or a
shortcode. Tabs, Fields, Steps and Cards also have a shortcode spelling; the
column shows the native one.

| Component | In one line | Shortest form |
| --- | --- | --- |
| [Callouts](/docs/callout/) | Separate prerequisites, warnings and asides from the prose | `> [!NOTE]` |
| [Images](/docs/image/) | Captions, sizing, zoom, numbering and build-time processing | `![alt](oink.webp)` |
| [Code blocks](/docs/code/) | Highlighting, titles, copy, folding, linkable lines | ```` ```sh ```` |
| [Tabs](/docs/tabs/) | One thing, several platforms or languages | attribute `{tab="Linux"}` |
| [Tables](/docs/table/) | Plain tables plus full-width, matrix, caption and numbering | `{.full-width}` |
| [Fields](/docs/fields/) | Parameter lists with type / required / default chips | `{.fields meta="type default"}` |
| [Steps](/docs/steps/) | A procedure with an order | `{.steps}` |
| [Cards](/docs/cards/) | A set of parallel destinations | `{.cards}` |
| [File trees](/docs/filetree/) | Directory structure with an aligned comment column | ```` ```filetree ```` |
| [Mathematics](/docs/math/) | KaTeX inline and display formulas | `$$ … $$` |
| [Mermaid](/docs/mermaid/) | Flowcharts, sequence diagrams, Gantt charts | ```` ```mermaid ```` |
| [PlantUML](/docs/plantuml/) | UML diagrams; needs a rendering server | ```` ```plantuml ```` |
| [Markmap](/docs/markmap/) | A Markdown outline becomes a mind map | ```` ```markmap ```` |
| [Draw.io](/docs/drawio/) | Diagrams that stay editable; needs a server | `![alt](arch.drawio.svg)` |
| [ECharts](/docs/echarts/) | Declarative statistical charts | ```` ```echarts ```` |
| [Infographic](/docs/infographic/) | AntV infographics | ```` ```infographic ```` |
| [Galleries](/docs/gallery/) | A set of images sharing one zoom dialog | ```` ```gallery ```` |
| [Badges](/docs/badge/) | Inline status markers | `{{</* badge text="Beta" */>}}` |
| [Keys](/docs/kbd/) | Key names and chords | `{{</* kbd "Ctrl" "K" */>}}` |
| [Include](/docs/include/) | Pull in files, print site parameters, drop build-time notes | `{{</* include file="parts/x.md" */>}}` |
| [Asciinema](/docs/asciinema/) | Terminal recordings | `{{</* asciinema file="images/x.cast" */>}}` |

Four notes on when a runtime actually loads:

- A code block loads `code-block.js` only when a block on the page has a copy
  or fold control; a file tree loads `filetree.js` only when the tree has a
  comment column, which is the runtime that drags the split.
- Images and galleries share one zoom dialog runtime. It needs `ui.image_zoom`
  on for the site and at least one eligible image on the page.
- Mathematics is rendered to HTML and MathML by KaTeX at build time. The page
  gains a KaTeX stylesheet and its fonts, and no script.
- With `params.drawio.enable` on, the Draw.io runtime loads on every page
  whether or not this page uses it.

Every component has a defined shape in all four outputs — HTML, print, Markdown
and RSS. See the *Output* section on each page.
