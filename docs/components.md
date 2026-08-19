# Component contract

Status: current API for OINK 0.5.0
Compatibility floor: Hugo Extended 0.160.1

This file is the maintainer contract. Tutorials and exhaustive examples belong
to `oink.pgsty.com`.

## Authoring model

OINK uses ordinary Markdown when one block plus an attribute can express the
component. Shortcodes remain for compound bodies or facts Markdown cannot
carry. There is no parallel component registry.

Required consumer settings for native forms:

```yaml
markup:
  goldmark:
    renderer:
      unsafe: true
    parser:
      wrapStandAloneImageWithinParagraph: false
      attribute:
        block: true
```

Only `{{% steps %}}` uses the percent delimiter; its body is page Markdown and
headings enter the page outline. Every other shortcode uses angle delimiters.
Container bodies pass through `content/render-block.html`, which scopes IDs
created by nested render hooks.

Public captions, labels, titles, and names are plain text. Markdown belongs in
component bodies. Icons are one Font Awesome class pair. A component may expose
site classes through the shared attribute policy, but it does not add visual
parameters such as arbitrary color or inline style.

## Public API

There are 29 shortcodes:

- core: `tabs`, `tab`, `steps`, `cards`, `card`, `fields`, `field`, `include`,
  `kbd`, `badge`, `param`, `comment`, `contributors`, `asciinema`;
- Book: `fig`, `tbl`, `eq`, `eg`, `xref`, `book-toc`, `book-figures`,
  `book-tables`, `book-equations`, `book-examples`;
- release: `release-card`, `release-assets`, `download`;
- OpenAPI: `swagger`, `redoc`.

| Component | Native form | Shortcode form | Runtime |
| --- | --- | --- | --- |
| Callout | `> [!TYPE]`, optional fold and `{icon=}` | none | none |
| Tabs | adjacent fences or tables with `{tab= group= value=}` | `tabs` / `tab` | `tabs.js` per used page |
| Steps | ordered list + `{.steps}` | `steps` | none |
| Cards | link list + `{.cards}` | `cards` / `card` | none |
| Fields | table + `{.fields}` | `fields` / `field` | none |
| FileTree | `filetree` data fence | none | divider runtime only when comments exist |
| Gallery | `gallery` data fence | none | reuses Image Zoom when eligible |
| Image | Markdown image + block attributes | none | Image Zoom when enabled and eligible |
| Table | `.full-width`, `.matrix`, caption, number, or tab attributes | `tbl` for compound Book tables | tabs only when tabbed |
| Book targets | image, table, passthrough block, or fence + `{num=}` | `fig`, `tbl`, `eq`, `eg` | none |
| Release assets | `checksums` data fence | `release-assets` | copy runtime in HTML |
| Diagram/data | `mermaid`, `plantuml`, `markmap`, `math`, `chem`, `echarts`, `infographic` fences | none | only the selected local runtime |

## Shared validation

Unknown shortcode parameters fail the build. Named/positional forms are not
silently mixed. IDs match `[A-Za-z][A-Za-z0-9_.:-]*`; Book numbers match
`[0-9A-Za-z.-]+`. Class values are token validated. Repeated render-hook and
shortcode targets share one page registry and reject collisions.

URL parameters use `content/url.html`. Image sources use
`content/image-resolve.html`: page resource, enclosing-section resource,
global asset, then static or explicit remote URL. Local raster resources carry
intrinsic dimensions. SVG, static, and remote sources remain valid but cannot
be processed by Hugo.

## Component details

### Callouts

Types are `note`, `tip`, `important`, `warning`, `caution`, `success`,
`danger`, `question`, `example`, `quote`, and `details`. `-` starts folded and
`+` expanded. Unknown types remain visible as neutral callouts. Callouts are
native `<aside>` or `<details>` structures and need no JavaScript.

### Tabs

Adjacent tabbed blocks form one run only when they are consecutive and of the
same block kind. `group` enables URL hash `#<group>-<value>` and storage key
`td-tabs:v1:<group>`; ungrouped tabs do neither. Server output exposes every
panel before JavaScript. Print expands panels with titles; Markdown and RSS
retain the source blocks.

The full form is for arbitrary Markdown panels. `tab.label` is required;
`value` is required exactly when the parent has a `group`. Nested `tab` outside
`tabs` fails.

### Steps, cards, and fields

An ordered `.steps` list supports normal block content. Use `{{% steps %}}`
when a step must contain a percent-delimited container; such a container inside
a list item truncates the list in supported Hugo versions.

Native cards are link lists. The full form adds compound bodies, badges, icons,
and images. `card` is valid only inside `cards`.

Native fields use the first column as the field name and the last as its
description. Middle columns map through `meta="type required default -"` or
their headings. The full form is for block descriptions. `field` is valid only
inside `fields`; every field gets a stable `field-<name>` anchor.

### Tables

The render hook owns the responsive wrapper and caption. `.matrix` makes the
first column row headers and keeps headings visible while scrolling.
`.full-width` applies to default and matrix tables. `.fields` is mutually
exclusive with `.matrix`, `.full-width`, numbering, and tabs. A numbered table
is mutually exclusive with a tabbed table.

### Images, Gallery, and Zoom

The Markdown image hook is the only ordinary image API. Inline images stay
inline. A standalone image is a block image; `caption` or `num` promotes it to
a figure. Allowed block attributes are `id`, `num`, `caption`, `width`,
`height`, `link`, `command`, and `options`, plus safe classes and generic
attributes. `command` and `options` must appear together and accept Hugo `Fit`,
`Resize`, `Fill`, or `Crop` operations on processable local resources.

`link` requires a caption or number because a plain linked image already has
native Markdown syntax. Linked and decorative images do not load Zoom. A
resource byline appears only when the image is already a figure; metadata does
not silently change a plain image's structure.

Gallery is a `gallery` fence with one Markdown image per line, optional
description, link, and class. FileTree is a `filetree` fence with indentation,
`- name`, optional trailing `/`, comments, and validated icon/tone/open/type
attributes. Both preserve their source in non-interactive output.

### Code and data fences

All code highlighting uses Chroma. Common fence attributes include `title`,
`copy`, `wrap`, `collapse`, `label`, `id`, line-number/highlight options, tab
attributes, and Book `num`/`caption`. A copied block returns authored source,
not rendered line-number markup.

ECharts input is declarative JSON. Callback references use `$fn:<name>` and
resolve through `window.OinkEchartsFunctions`; arbitrary script embedded in
the data is not executed.

### Book

The `book` type extends the docs shell and uses the same content tree or
`data/docs_nav.json`. `book_number`, `book_part`, `book_kind`, and
`book_status` are presentation metadata. Draft labels do not change Hugo
publication state.

Numbered kinds are `fig`, `tbl`, `eq`, and `eg`. Their default IDs are
`<kind>-<num>`. `eg` requires a caption. `eq` without `num` is an unnumbered
display-math escape hatch and registers no target. `xref` accepts exactly one
kind plus optional `page`/`anchor`, or an anchor with explicit body text. A
numbered example renders as one framed block: the caption is its header and the
body sits inside the frame.

Footnotes belong to the page document. A table or fence carrying `{num=…}`
keeps its cells in that document, so `[^label]` resolves there with the page's
own numbering and backlinks. A shortcode body is rendered as a separate
document and cannot: a reference to a page definition would print literally and
a body-level definition would build a second, colliding footnote list, so a
footnote reference in any Markdown body a shortcode renders (`tbl`, `eg`,
`fig`, `card`, `tab`, `field`, `include`) fails the build. Footnote-shaped text
in code -- `[^0-9]` in a listing or a code span -- is left alone.

`book-toc` follows navigation order at depth 1 to 3. `book-figures`,
`book-tables`, `book-equations`, and `book-examples` aggregate one registered
kind each. Whole-Book print rewrites cross-page links to local fragments and
namespaces ordinary heading IDs -- and footnote IDs, which Goldmark numbers per
page -- while preserving explicit numbered target IDs. It is enabled only by
the consumer's output configuration.

### Release and download

Release facts live in page front matter. A release map requires `version` and
`repo`; it may add `product`, `tag`, `date`, `prev`, and `checksums`. The exact
GitHub release URL shorthand is also accepted. No release state is fetched.

Checksums accept canonical checksum lines or one source resource, never both.
Filenames cannot be paths. HTML adds local copy controls; other outputs expose
full hashes.

Download facts live in `data/download/<key>.yaml`. Channels are `rolling` or
`pinned`; only pinned URLs and commands interpolate `${version}` and `${tag}`.
An unpublished record leaves rolling channels usable and renders pinned ones
as pending. RSS omits the component.

## Output and runtime matrix

| Family | HTML | Print | Markdown / RSS |
| --- | --- | --- | --- |
| Static primitives | semantic component | same content, expanded | source-shaped Markdown |
| Tabs / FileTree | progressive enhancement | all content visible | original source |
| Images / Gallery | optional local Zoom | static figures | image source |
| Book targets/indexes | linked semantic figures/lists | document-local links | labeled source and links |
| Release assets | copy controls | full static hashes | pipe table |
| Download | channels and state | expanded channels | Markdown source / RSS omitted |

No Markdown output contains `td-` component markup. Non-HTML output does not set
interactive Page Store flags.

## Verification

Source checks validate parameters, hook policy, runtime isolation, and
migrations. Output checks build the fixture and compare HTML, print, Markdown,
RSS, and LLMS goldens. Browser runtime tests cover tabs, FileTree, copy, search,
palette, keyboard navigation, themes, feedback, and page actions.

Migration from 0.4 is documented in [migration.md](migration.md).
