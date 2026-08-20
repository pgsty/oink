# Component contract

This is the maintainer contract; tutorials and exhaustive examples belong to
`oink.pgsty.com`.

## Authoring model

Use ordinary Markdown when one block plus attributes can express a component.
Use shortcodes for compound bodies or facts Markdown cannot carry. There is no
parallel component registry. Native forms require:

```yaml
markup:
  goldmark:
    renderer: { unsafe: true }
    parser:
      wrapStandAloneImageWithinParagraph: false
      attribute: { block: true }
```

Only `{{% steps %}}` uses percent delimiters because its body belongs to the
page outline; every other shortcode uses angle delimiters. Compound bodies pass
through `content/render-block.html` with a unique ID scope. Shortcode and
component parameter captions, labels, titles, and names are plain text;
Markdown belongs in bodies. Landing narrative fields follow their own contract.
An icon is one Font Awesome class pair. Components expose safe classes and
attributes, not arbitrary color or inline style.

## Public API

OINK has 29 shortcodes:

- core: `tabs`, `tab`, `steps`, `cards`, `card`, `fields`, `field`, `include`,
  `kbd`, `badge`, `param`, `comment`, `contributors`, `asciinema`;
- Book: `fig`, `tbl`, `eq`, `eg`, `xref`, `book-toc`, `book-figures`,
  `book-tables`, `book-equations`, `book-examples`;
- release: `release-card`, `release-assets`, `download`;
- OpenAPI: `swagger`, `redoc`.

| Component | Native form | Shortcode form | HTML runtime |
| --- | --- | --- | --- |
| Callout | `> [!TYPE]`, fold, `{icon=}` | none | none |
| Tabs | adjacent fences/tables with `{tab= group= value=}` | `tabs` / `tab` | tabs on used pages |
| Steps | ordered list + `{.steps}` | `steps` | none |
| Cards | link list + `{.cards}` | `cards` / `card` | none |
| Fields | table + `{.fields}` | `fields` / `field` | none |
| FileTree | `filetree` data fence | none | divider only with comments |
| Gallery | `gallery` data fence | none | shared Image Zoom when eligible |
| Image | Markdown image + block attributes | none | Image Zoom when eligible |
| Table | attributes, caption, number, or tabs | `tbl` for compound Book tables | tabs when tabbed |
| Book target | image/table/passthrough/fence + `{num=}` | `fig`, `tbl`, `eq`, `eg` | none |
| Release assets | `checksums` data fence | `release-assets` | copy in HTML |
| Diagram/data | `mermaid`, `plantuml`, `markmap`, `math`, `chem`, `echarts`, `infographic` fences | none | selected local runtime only |

## Validation

Invalid author input follows [architecture.md](architecture.md): warn, use the
documented safe fallback or omit the component, and let `--panicOnWarning` make
the same diagnostic fatal at publication gates. Named and positional forms are
not mixed. Book target IDs match `[A-Za-z][A-Za-z0-9_.:-]*`; Book numbers match
`[0-9A-Za-z.-]+`; classes are token-validated. Hook and shortcode targets share
one page registry, so collisions cannot produce duplicate output IDs.

URLs use `content/url.html`. Images resolve through page resources, section
resources, global assets, then static or explicit remote URLs. Local rasters
carry intrinsic dimensions; SVG, static, and remote sources remain valid but
cannot use Hugo image operations.

## Component behavior

### Callouts and tabs

Callout types are `note`, `tip`, `important`, `warning`, `caution`, `success`,
`danger`, `question`, `example`, `quote`, and `details`; `-` starts folded and
`+` expanded. Unknown types remain visible as neutral callouts without JS.

Adjacent tabs group only when consecutive and of the same block kind. `group`
enables hash `#<group>-<value>` and storage `td-tabs:v1:<group>`; ungrouped tabs
use neither. HTML exposes every panel before JS, print expands them, Markdown
retains authored source, and RSS receives the rendered text summary. The full form supports arbitrary Markdown;
`tab.label` is required, `value` is required exactly with a parent `group`, and
an orphan `tab` warns and renders nothing.

### Steps, cards, fields, and tables

Native steps accept ordinary block content. Use the shortcode only when a step
must contain a percent-delimited container. Native cards are link lists; the
full form adds bodies, badges, icons, and images. Native fields map the first
column to the name, the last to the description, and middle columns through
`meta=` or headings; the full form allows block descriptions. `card` and
`field` are valid only inside their parents.

Field anchors are `field-<name>` with lowercase punctuation runs collapsed to
hyphens, so `params.ui.typography` becomes `field-params-ui-typography`.
Duplicate anchors receive positional suffixes.

The table hook owns responsive wrapping and captions. `.matrix` makes the first
column row headers; `.full-width` widens normal or matrix tables. `.fields`
cannot combine with matrix, full-width, numbering, or tabs; numbering and tabs
are also mutually exclusive.

### Images, Gallery, FileTree, and fences

The Markdown image hook is the ordinary image API. Inline images stay inline;
block images become figures with `caption` or `num`. Allowed image attributes
are `id`, `num`, `caption`, `width`, `height`, `link`, `command`, and `options`
plus shared safe attributes. `command` and `options` appear together and use
Hugo `Fit`, `Resize`, `Fill`, or `Crop` on processable local resources. A plain
linked image uses Markdown syntax; the `link` attribute therefore requires a
caption or number. Linked and decorative images do not load Zoom.

Gallery accepts one Markdown image per line with optional description, link,
and class. FileTree accepts indentation, `- name`, optional `/`, comments, and
validated icon/tone/open/type attributes. Markdown preserves authored source;
print renders expanded static figures and trees.

All code highlighting uses Chroma. Common fence attributes include `title`,
`copy`, `wrap`, `collapse`, `label`, `id`, line options, tabs, and Book
`num`/`caption`. Copy returns authored source. ECharts input is declarative
JSON/YAML; callbacks use `$fn:<name>` from `window.OinkEchartsFunctions`, never
embedded script execution.

### Book

The `book` type extends the docs shell and follows the content tree or
`data/docs_nav.json`. `book_number`, `book_part`, `book_kind`, and `book_status`
are presentation metadata; they do not change Hugo publication state.

Numbered kinds are `fig`, `tbl`, `eq`, and `eg`, with default ID
`<kind>-<num>`. `eg` needs a caption; `eq` without `num` is an unnumbered display
formula. `xref` names exactly one kind plus optional `page`/`anchor`, or an
anchor with explicit text. A numbered example is one framed body and caption.

Footnotes belong to the page document. Native numbered tables and fences keep
them there. A shortcode body is a separate Goldmark document, so footnote
references in `tbl`, `eg`, `fig`, `card`, `tab`, `field`, or `include` warn and
remain literal; code-shaped text is ignored by that check.

`book-toc` follows navigation order at depth 1–3; the four `book-*` indexes
collect one target kind each. Whole-Book print rewrites cross-page links and
namespaces ordinary headings and footnotes while preserving explicit target
IDs. Consumers opt into that potentially expensive output.

### Release and download

Release front matter is one `release_url` in the form
`https://github.com/<owner>/<repo>/releases/tag/<tag>`; owner, project, and tag
come from the URL and date from the page. No remote release state is fetched.
The removed `release` map, `release_products`, and
`release_group_by_product` warn with their replacement and are not compatibility
paths. The section index lists every page, using parsed `project tag` when
available and the page title otherwise.

Checksums accept canonical lines or one source resource, never both; filenames
cannot be paths. HTML adds local copy, while static outputs expose full hashes.

Downloads use `data/download/<key>.yaml`. Channels are `rolling` or `pinned`;
only pinned URLs and commands interpolate `${version}` and `${tag}`. Before
publication, rolling channels remain usable and pinned channels show pending.
Markdown renders the complete channel list; RSS omits the component.

## Verification

Shared output rules live in [architecture.md](architecture.md); exceptions are
defined with their components above. Markdown and RSS set no browser runtime
flags; Print retains only flags required by rendered print features. Source checks cover
parameters, hook policy, runtime isolation, and migration; output checks compare
HTML, print, Markdown, RSS, and LLMS goldens; browser tests cover interactive
surfaces. Migration is documented in [migration.md](migration.md).
