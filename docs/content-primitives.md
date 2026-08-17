# Everyday content primitives contract

Status: frozen for implementation

Tracking: [pgsty/oink#3](https://github.com/pgsty/oink/issues/3)

Contract issue: [pgsty/oink#4](https://github.com/pgsty/oink/issues/4)

Contract version: 2 (OINK 0.5/0.6 component API v5; version 1 shipped with
OINK 0.4)

Compatibility floor: Hugo Extended 0.160.1

## 1. Decision

OINK ships one small, closed set of content components for engineering
documentation without changing its Hugo-only consumer boundary. Version two of
this contract replaces the Docsy-heritage shortcode zoo (53 templates) with 30
shortcodes plus a family of **native forms**: ordinary Markdown blocks whose
meaning is selected by a Goldmark block-attribute line (a marker such as
`{.steps}` or an attribute such as `{tab="npm"}`) and rendered by a render hook
or by CSS alone.

The public interfaces in this document are the version-two contract for:

- inline leaves: Badge, Kbd, Param, Comment, Include;
- Fields (table form and shortcode form);
- the `filetree` and `gallery` data fences; Steps and Cards native list forms
  (+ the `cards`/`card` shortcode);
- the image render hook and the `image` shortcode; Image Zoom;
- Release Assets and the `checksums` fence;
- the table family (`full-width`, `fields`, `matrix`, `caption`, numbered,
  tabbed);
- Callouts (blockquote render hook);
- Tabs (adjacent blocks and the `tabs`/`tab` shortcode);
- data fences (`echarts`, `infographic`, `checksums`, `filetree`, `gallery`);
- the numbered Book components (`fig`, `tbl`, `eq`, `eg`, `xref`, Book
  indexes) in their shortcode and native forms.

Design principle ("three-place equivalence"): a native form must express the
same content on GitHub, in a plain Markdown reader, and in OINK's own Markdown
output. Content that is itself code or data (Mermaid, declarative ECharts
options, checksum lines) is native as a fenced block because the code block is
its equivalent presentation. Markdown wrapped in a fence, or an invented DSL
inside a fence, is not native and is not offered.

A standalone public Icon shortcode is deferred. Icon parameters (Callout
`icon`, Card `icon`) accept exactly one validated Font Awesome class pair, not
arbitrary markup or a reusable icon surface.

## 2. Shared authoring contract

### 2.1 Notation and nesting

Every component has at most two forms — a **native form** (one Markdown block
plus a marker or attribute line) and a **full form** (a shortcode) — and every
shortcode uses exactly one delimiter:

- `{{% steps %}}` is the only `{{% %}}` shortcode. Its body is top-level page
  Markdown, so headings inside it enter the table of contents. The template
  emits a blank line before and after `.Inner`; without those blank lines
  Goldmark would swallow the following Markdown into the opening HTML block.
- Every other shortcode uses standard notation (`{{< ... >}}`). Collector
  parents (`fields`, `tabs`, `cards`) evaluate `.Inner` so validated children
  register ordered data; the parent owns all rendering. Children keep raw
  Markdown bodies and the parent renders them with `.Page.RenderString` through
  `layouts/_partials/content/render-block.html`, which scopes generated IDs
  (section 2.6).
- Rationale (verified on Hugo 0.160.1 and 0.164.0): a `{{% %}}` shortcode nested
  inside another shortcode receives `.Inner` already rendered as HTML, so a `%`
  collector could neither re-render nor emit source Markdown. Angle-bracket
  children always receive source Markdown (with nested shortcodes already
  expanded, which `unsafe: true` keeps through `RenderString`).
- Consequence: a `{{% steps %}}` block must not be written inside a list item;
  its multi-line output is not re-indented and truncates the list silently. The
  native `1. … {.steps}` list form can hold any Markdown block except `%`
  containers.

Nested public names are stable and valid only inside their parent: `field` in
`fields`, `tab` in `tabs`, `card` in `cards`.

Hugo does not permit named and positional arguments in the same call. Kbd and
Param are positional-only; every other shortcode is named-only.

Native forms use Goldmark block attributes on the line **immediately after**
the block (lists, tables, blockquotes, standalone images, `$$` blocks) or on
the info string of a fence. An attribute line separated from its block by a
blank line attaches to nothing and disappears silently; the source linter
reports such orphan lines. Consumer sites therefore need
`markup.goldmark.parser.attribute.block: true`, `markup.goldmark.renderer.unsafe:
true` (for `%`/RenderString output and raw HTML), and, for the block image
forms, `markup.goldmark.parser.wrapStandAloneImageWithinParagraph: false`.

The public marker vocabulary is fixed and unprefixed: `{.steps}` (ordered
list), `{.cards}` (link list), `{.fields}`, `{.matrix}`, `{.full-width}`
(tables), and `> [!TYPE]` callouts. Because lists have no render hook, a list
marker is also the CSS selector (`ol.steps`, `ul.cards`); everything the theme
generates keeps the `td-` prefix. That limitation is why FileTree and Gallery
are data fences instead of list markers: a component whose items need
attributes, or which the theme must mark for a runtime, cannot be CSS-only.

### 2.2 Parameter validation

Public parameter names and enum values are case-sensitive.

- A named shortcode enumerates its allowed parameters and rejects every
  unknown parameter.
- Required strings must be actual strings and must remain non-empty after
  trimming surrounding whitespace. Integers and booleans are not coerced to
  strings.
- Booleans must be unquoted Hugo boolean values. The strings `"true"` and
  `"false"` are invalid.
- Integers must be unquoted integer values. Numeric strings and floats are
  invalid where an integer is required.
- Enums accept only their documented lower-case values.
- Optional parameters that are present but blank are invalid unless the
  component explicitly documents an empty-string value.
- Every author error uses `errorf`, names the shortcode and parameter, and
  includes `.Position`.

Shortcodes do not accept `class`, `style`, color, event-handler, or `cols`
parameters. Icons accept exactly one Font Awesome pair matching
`fa-(solid|regular|brands) fa-[a-z0-9-]+`. The Book components are the
documented exception: they accept a grammar-constrained semantic `id` and safe
`class` tokens so DDIA and O'Reilly anchors and site figure classes migrate
without breaking public links. Nothing accepts `style` or event handlers.

**Hook attribute policy** (`layouts/_partials/content/attributes.html`, shared
by the table, image, passthrough, blockquote, and data-fence render hooks):

- each hook consumes its own allowlist of keys (documented per component);
- `class` is validated token by token (`^[A-Za-z0-9_-]+$`) and passed through
  so site CSS keyed on author classes keeps working;
- `data-*` and `aria-*` attributes pass through unchanged;
- `style`, any `on*` handler, `srcdoc`, and every other unknown key fail the
  build with the position of the block.

Ordinary code fences follow the same policy through
`docs/enhanced-code-blocks.md` §5.5 (OINK names and Chroma options consumed;
`class`, `id`, `role`, `data-*`, `aria-*` reach the `.td-code` root; `style`,
`on*`, `srcdoc`, reserved `data-td-code*` names, and any other unknown key fail
the build).

### 2.3 Escaping and rendered content

Author text remains data in every output:

- HTML attributes and text use Go template contextual escaping.
- Author values must not be passed to `safeHTML`, `safeURL`, or `safeJS` to
  suppress validation or escaping.
- Theme-owned static markup may be returned as trusted template output only
  after every author value has been inserted through a safe context.
- Markdown bodies (Fields descriptions, Tab bodies, Card bodies, the `image`
  caption, `include` files, and Book Figure/Table/Example bodies) render through
  `content/render-block.html` (`.Page.RenderString`, block display) using the
  consuming site's Goldmark policy. Their Markdown fallback retains source
  Markdown and must not convert it to HTML first.
- Markdown fallbacks use context-specific escaping for plain text, code spans,
  emphasis, and link destinations. They do not reuse an HTML escape helper.
- A code span chooses a fence longer than any run of backticks in its value.

The Markdown output must contain no component classes, `data-*` runtime
attributes, `<dialog>`, `<details>`, `<dl>`, or other runtime HTML emitted by
these primitives. Native forms pass through OINK's Markdown output as their
source blocks because render hooks do not run under `.RenderShortcodes`; the
attribute line stays visible there by design.

### 2.4 URL policy

Badge `link`, Card `link`, image sources, Book Figure `link`, `checksums`/
Release Assets `base`, and shared media URLs use one internal URL helper.

For links:

- `#fragment`, query-only, relative, and root-relative site URLs are allowed.
- Relative and root-relative paths are site-relative and are passed through
  Hugo's subpath-safe URL handling. They are not resolved relative to the
  current content file.
- Explicit `http`, `https`, and `mailto` URLs are allowed.
- Protocol-relative URLs and every other scheme, including `javascript`,
  `data`, `vbscript`, and `file`, are rejected.
- ASCII control characters and whitespace inside a URL are rejected.
- Components do not force a new browsing context with `target="_blank"`;
  external card links receive `rel="noopener"`.

For image sources, only site URLs and explicit `http` or `https` URLs are
allowed. The theme never downloads a remote image during a normal build.

The helper returns both the HTML URL and the Markdown destination. Callers
must not parse or normalize the same author URL a second time.

### 2.5 Output-format state

The existing Page Store key `tdOutputFormat` is authoritative:

| Value | Meaning |
| --- | --- |
| `html` | Normal interactive HTML page. |
| `print` | Section print output. |
| `markdown` | Pure Markdown output such as Copy text. |
| `rss` | Static HTML embedded in a feed. |

Base templates set the key before rendering content. A shortcode may default
to `html` only as a defensive fallback when used by a custom consumer layout.
Components branch on this value within their shared template instead of
depending on output-specific shortcode lookup. Render hooks read it through
`.PageInner | default .Page`.

### 2.6 Page Store, repeated rendering, and IDs

Hugo may render a shortcode more than once for summaries, alternate outputs,
or repeated `.Content` access. All Page Store writes must therefore be
idempotent.

- Boolean feature flags use `Set true`; they are never counters. Flags used by
  this contract: `hasTabs`, `hasCodeBlock`, `hasCodeRuntime`, `hasImageZoom`,
  `hasAssetList`, `hasEcharts`, `hasInfographic`, `hasMath`.
- Ordered child data is scoped to the parent shortcode Scratch, not the Page
  Store.
- A duplicate check uses a stable owner. Seeing the same owner again is
  allowed; seeing a different owner for the same public value is an error.
- Bodies rendered through `content/render-block.html` run inside a named scope
  (`tdRenderScope`, nesting by concatenation). Generated code-block IDs
  (`td-code-<page>-<scope>-fence-<n>`) include the scope, so a fence inside a
  tab, card, field, or Book example cannot collide with the page's own fences.
- The everyday components do not expose author-supplied DOM IDs except through
  the documented `id` attribute of the table/image/passthrough/fence forms and
  the Book components. Numbered Book targets share one page registry
  (`tdBookTargets`) whose identity and ordering come from the source position
  (`file:line:col`), so shortcode targets and render-hook targets never
  collide and Book lists follow document order.
- Generated IDs use a component prefix, a page-derived digest where needed,
  and the shortcode ordinal (`td-tabs-<hash8>-<ordinal>`, `td-card-…`,
  `td-fields-…`). Interactive IDs must be registered before output.

Feature flags are set only after validation. Interactive flags are set only in
`html` output and only when the feature is enabled and the page has a usable
candidate.

### 2.7 Runtime loading

Badge, Kbd, Fields, Steps, Cards, Callouts, Tables, and the numbered Book
components never load JavaScript. FileTree folds natively and loads one local
runtime (`assets/js/filetree.js`, keyed by `hasFileTree`) only for the
draggable comment split of trees that have comments. Tabs (both forms) load one
local runtime (`assets/js/tabs.js`) keyed by `hasTabs`; it has no Bootstrap
dependency.
Image Zoom owns one opt-in dialog runtime and Gallery images may request that
same runtime without adding another bundle. Release Assets and the `checksums`
fence own a separate opt-in copy runtime keyed by `hasAssetList`. Data fences
request their vendored chart runtimes (`hasEcharts`, `hasInfographic`).
Runtimes are appended from `layouts/_partials/scripts.html` only after content
sets its Page Store flag; every flag is part of the bundle key. Print,
Markdown, and RSS never receive them.

The server-rendered HTML is complete before enhancement. If JavaScript is
disabled, blocked, or fails, every tab panel, image, caption, callout body,
and code block remains readable.

### 2.8 CSS and accessibility

Components consume semantic OINK/Bootstrap tokens and may define component
aliases. They must not embed arbitrary author colors or literal bundled font
families.

- Use logical properties so spacing and alignment work in RTL.
- Long names, types, paths, and captions must wrap or scroll within their own
  component without creating page-level horizontal overflow.
- Dark mode derives from semantic tokens.
- Print removes decorative color dependence, exposes complete content, and
  avoids hiding descendants of closed disclosure widgets: collapsible callouts
  and tab sets render as static, expanded blocks in the print output format.
- Forced-colors mode preserves visible boundaries and focus indicators with
  system colors or `currentColor`.
- Reduced motion disables non-essential transitions (Zoom, callout marker,
  cards hover, tab switch).
- Native semantics take precedence over ARIA. FileTree does not claim
  `role="tree"`; Fields remains a definition list; collapsible callouts are
  native `<details>`; Zoom uses a real dialog; Tabs use `role="tablist"`,
  `role="tab"`, `role="tabpanel"` with real buttons.

### 2.9 Visible strings, aliases, and deprecation

Author-provided labels, captions, names, keys, and alt text are rendered as
provided and are not looked up through i18n.

Every theme-owned visible or assistive string is an i18n key submitted to all
locale files in the same change (callout type labels `note tip important
warning caution success danger question example quote details`,
`ui_tabs_label`, `ui_table_scroll`, Book labels, Kbd separator, Zoom controls).
The Fields `required` and `default` metadata labels are a deliberate
exception: they are API vocabulary rendered untranslated in every locale.

An intentional historical alias:

1. renders the canonical behavior;
2. emits `warnf` with `.Position` and the replacement;
3. remains for at least one complete minor release after the warning first
   ships; and
4. is removed only with an explicit changelog entry.

Version two ships no aliases: the pre-1.0 in-house consumers migrate with
`scripts/migrations/oink06.py` in the same release train, and removed
shortcodes fail the build with Hugo's "template for shortcode … not found".

## 3. Public component APIs

### 3.1 Badge

```go-html-template
{{< badge text="Beta" tone="warning" >}}
{{< badge text="v0.3" tone="info" link="/release/" >}}
```

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `text` | yes | non-empty plain string | none |
| `tone` | no | `neutral`, `info`, `success`, `warning`, `danger` | `neutral` |
| `link` | no | URL allowed by section 2.4 | none |

HTML uses an inline `<span class="td-badge td-badge--<tone>">` when `link` is
absent and an `<a>` when it is present. Tone maps to semantic tokens and is not
the only carrier of meaning: the author-provided text remains visible in all
modes. The former `outline` parameter was a purely visual switch and is
removed; there is one badge appearance. The same five-value `tone` vocabulary
is used by FileTree (section 3.4).

There is no public Badge `icon`, `class`, or color parameter. Markdown
fallback:

```markdown
**Beta**
[**v0.3**](/release/)
```

### 3.2 Kbd

```go-html-template
{{< kbd "Ctrl" "K" >}}
{{< kbd "⌘" "Shift" "P" >}}
```

Kbd accepts one or more non-empty positional string arguments. Its public
argument list is closed: separator, label, platform, and styling options will
not be added to the shortcode because named and positional arguments cannot be
mixed in one call. A literal plus key is written as its own argument
(`{{< kbd "Ctrl" "+" >}}`). Raw `<kbd>` elements written in Markdown are styled
by the same CSS.

HTML emits a sequence wrapper with one nested `<kbd>` per key. Visible `+`
separators and a localized simultaneous-key separator produce an understandable
key sequence without repeating punctuation to screen readers.

Print and Markdown use the exact plain notation:

```text
Ctrl + K
⌘ + Shift + P
```

### 3.3 Fields and Field

Fields has a native table form and a shortcode form; both render through the
shared `<dl>` partial `layouts/_partials/content/fields-list.html`.

**Table form.** Any pipe table followed by `{.fields}`:

```markdown
| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offlineSearch` | boolean | `false` | 开启本地索引与命令面板 |
| `offlineSearchMaxResults` | integer | `10` | 结果上限，*支持行内 Markdown* |
{.fields caption="搜索参数"}
```

Positional rule, no header vocabulary and no synonym guessing:

- at least two columns; the **first column is the field name**, the **last
  column is the description**, every **middle column is metadata** whose label
  is the header text verbatim (any language) and whose value is the cell;
- an empty middle cell is omitted; a first cell written as a single code span
  keeps only its text (the `<dt>` supplies the code styling);
- the first cell must be non-empty and unique within the table (build error
  otherwise);
- cells are Goldmark inline HTML (links, code, emphasis); block content is not
  possible in a table cell — use the shortcode form;
- `caption` is the visible label (`.td-fields__label`, referenced by
  `aria-labelledby`); `id` names the wrapper; `.fields` cannot be combined with
  `.matrix`, `.full-width`, or a Book `num`; the table hook attribute policy of
  section 3.9 applies.

Markdown output keeps the source table (render hooks do not run there).

**Shortcode form** (unchanged notation from version one; strict typed
metadata and multi-paragraph descriptions):

```go-html-template
{{< fields label="Configuration fields" >}}
  {{< field name="offlineSearch" type="boolean" default=true required=true >}}
  Enables the local search index and command palette.
  {{< /field >}}

  {{< field name="offlineSearchMaxResults" type="integer" default=10 >}}
  Maximum number of visible results.
  {{< /field >}}
{{< /fields >}}
```

`fields` parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `label` | no | non-empty plain string | no visible label |

`field` parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `name` | yes | non-empty plain string | none |
| `type` | no | non-empty plain string | omitted |
| `required` | no | strict boolean | `false` |
| `default` | no | any shortcode scalar, including `false`, `0`, and `""` | omitted |

Every Field requires a non-empty inner description. After the child is
registered, the parent renders that description through
`content/render-block.html` for HTML, print, and RSS while retaining the source
Markdown in Markdown output. An explicit empty-string default is displayed as
`""`; an absent default emits no default metadata.

HTML is one `<dl>` (`.td-fields > .td-fields__list`) with HTML-valid wrappers
containing paired `<dt>` and `<dd>` elements. It must not use
`display: contents`. Each entry stacks two rows: the `<dt>` header row carries
the field name followed by metadata chips — `type` (`.td-field__type`),
`required` (`.td-field__required`), `default: value` (`.td-field__default`) in
the shortcode form; `label: value` (`.td-field__meta` with
`.td-field__meta-label` / `.td-field__meta-value`) in the table form — and the
`<dd>` below it carries the description. Entries are separated by hairline
dividers, not boxed cells or columns.

Markdown fallback of the shortcode form is an ordered author-preserving bullet
list:

```markdown
**Configuration fields**

- `offlineSearch` — `boolean`; required; default: `true`

  Enables the local search index and command palette.
```

The `required` and `default` metadata labels are untranslated API vocabulary
in every locale. Deferred parameters are `kind`, `location`, `since`,
`deprecated`, and `link`, along with nested schemas and compiler-driven type
extraction.

### 3.4 FileTree

FileTree has exactly one form: the `filetree` data fence. The body is a
directory listing; the code block render hook
(`layouts/_markup/render-codeblock-filetree.html`) parses it and renders the
panel. There is no list marker (`{.filetree}` was removed in 0.6) and no
shortcode.

````markdown
```filetree {title="Deployment filesystem"}
- /srv/atlas/                  # 0755 root:root · Application root   {icon="fa-solid fa-server" tone=info}
  - releases/                  # 0750 deploy:release · Immutable builds
    - 2026.08.16/              # 0750 deploy:release · Active release
      - atlas-server           # 0555 deploy:atlas · Executable
      - [app.toml](/docs/config/)   # 0640 root:atlas · Runtime configuration
  - secrets/                   # 0700 root:security · Restricted      {open=false tone=danger}
    - production.env           # 0600 root:security
```
````

Fence attributes (`content/attributes.html` policy: `class`, `data-*`, and
`aria-*` pass through; anything else fails the build):

| Attribute | Required | Accepted values | Effect |
| --- | --- | --- | --- |
| `title` | no | non-empty plain string | title bar above the tree; without it no bar is drawn |
| `tab`, `group`, `value` | no | as for code fences (section 3.13) | the tree becomes one adjacent-block tab of kind `code` |

Line grammar — every non-blank line is one entry:

```text
<indent> [- | * | + | ├── | └── | |-- | `--] name[/] [# comment] [{key=value …}]
```

- **Depth** comes from an indent stack: two spaces, four spaces, tabs (four
  columns), and the `│   `/`├── `/`└── ` drawing that `tree` prints all work,
  as long as a dedent returns to a level that is already open (otherwise the
  build fails with the fence line number). A bare first line (`.` or a path,
  as `tree` prints it) is an entry; the `N directories, M files` summary line
  is skipped. Bullets are optional.
- **Directory or file**: `type=dir` / `type=file` decides explicitly;
  otherwise an entry with children is a directory, an entry whose name ends
  in `/` is a directory, and everything else is a file. Names render as
  written (the trailing `/` is kept).
- **Link**: `[name](url)`; the URL goes through the section 2.4 policy.
- **Comment**: everything after the first whitespace-preceded `#`, plain
  text; `\#` is a literal hash. The comment is the second, aligned column.
- **Attributes** (trailing `{…}`, `key=value` pairs, bare or quoted values,
  unknown keys and empty values fail the build): `icon` = one Font Awesome
  class pair (`fa-solid fa-lock`); `tone` = `neutral | info | success |
  warning | danger` (the Badge vocabulary, section 3.1) and colours the icon;
  `open=false` collapses a directory (directories only; default open);
  `type` as above.
- **Default icons**: directories use `fa-regular fa-folder` /
  `fa-folder-open` (the disclosure state picks one; an authored `icon`
  replaces both). Files are matched by whole name (`LICENSE`, `Makefile`,
  `Dockerfile`, `.gitignore`, `go.mod`, `package.json`, …) then by extension
  (`md yml yaml toml json sh py go js rs sql html css png svg pdf zip tar gz
  lock env …`) in `content/filetree-icon.html`; anything else is
  `fa-regular fa-file`. The table is a rendering default, not a registry:
  every icon is still a Font Awesome class pair and `icon=` overrides it.

Rendering:

- HTML: `<div class="td-filetree">` with an optional `td-filetree__chrome`
  title bar (`role="group"` + `aria-labelledby` when a title is present) and
  a nested `<ul>`; a directory with children is `<li><details open?><summary>`
  (native disclosure, no JavaScript, keyboard-operable); each entry is a
  two-column `td-filetree__row` grid (name cell | comment cell). The comment
  column is aligned without JavaScript: the hook computes the widest
  `depth × 2.5ch + name + icon slot` and writes it as
  `--td-filetree-name-col`; CSS clamps the split to 50–70% of the row, so the
  comment column never takes more than the right half and is never squeezed
  below 30%. A fence with no comments gets `td-filetree--plain` (single
  column). Long names and comments truncate with an ellipsis and carry `title`
  tooltips; below the `sm` breakpoint the comment drops under the name and
  wraps.
- Draggable split: a fence with comments also renders
  `<span class="td-filetree__divider" role="separator" aria-orientation="vertical"
  aria-valuemin="50" aria-valuemax="70" tabindex="0" data-td-filetree-divider>`
  (label `ui_filetree_divider`) and sets `hasFileTree`; `assets/js/filetree.js`
  (`window.OinkFileTree`, in the page bundle only when the flag is set) makes it
  drag with pointer events and step with Left/Right/Home/End (RTL aware) by
  rewriting `--td-filetree-name-col` in pixels; nothing is persisted and the
  CSS clamp still bounds the value. Without JavaScript the tree is complete
  and the split stays at the build-time width.
- Print: the same tree with `td-filetree--static`, no `<details>`, no
  divider, every directory expanded, comments wrap. RSS: the source in
  `<pre class="td-filetree-source">`. Markdown: the fence itself (the
  Markdown output format renders shortcodes, not render hooks, so the fence
  reaches the reader verbatim; inside a shortcode body the hook re-emits it).
- Styles live in `assets/scss/td/_filetree.scss`; folding is native
  `<details>`; the only runtime is the optional divider above.

### 3.5 Shared images and the image shortcode

The shared image resolver is internal. It resolves an explicit `http` or
`https` source directly; otherwise it tries, in order:

1. a page resource;
2. a global Hugo asset; and
3. a static/public site path.

The result records the rendered URL, canonical full-size URL, media type,
intrinsic width and height when Hugo knows them, alt text, caption, and whether
the source can be processed. Missing page/global resources and invalid image
operations fail with the caller's position. A static or remote image may omit
dimensions when the build cannot know them without I/O. An SVG resolves as an
image resource but reports no intrinsic dimensions.

Every theme path that takes an image source uses this resolver: the image
render hook, the `image` shortcode, the `card` shortcode's `image`, and the
Book `fig` shortcode's `src`. Landing sections are the documented exception
and are tracked separately.

**Image render hook** (`layouts/_markup/render-image.html`). Every Markdown
image `![alt](src "title")` resolves through the shared resolver:

- inline images render a bare `<img src alt [title] loading="lazy"
  decoding="async" [width height]>`; they carry no attributes;
- a standalone image (its own paragraph; requires the site setting
  `wrapStandAloneImageWithinParagraph: false`, otherwise Goldmark wraps it and
  the hook sees an inline image) renders a bare block-level
  `<img class="td-image [classes]" [id] …>` with no wrapper element, because a
  wrapper around a linked standalone image would be invalid HTML;
- a standalone image followed by an attribute line with `caption` or `num`
  renders `<figure class="td-figure [td-book-figure td-book-figure--fig]
  [classes]" [id]>` with `<figcaption>`; `num` registers a Book `fig` target
  (section 3.10). The `fig` shortcode emits the same class set, so numbered
  figures are styled identically whichever form produced them;
- allowed attributes: `id`, `num`, `caption` (plain text), `width`, `height`
  (positive integers; they override the resource dimensions and give static
  or remote images their box), `link`, plus `class`, `data-*`, `aria-*`;
  anything else fails the build;
- `link` wraps the image in `<a class="td-figure__link">` *inside* the figure
  and requires `caption` or `num`. A linked image without a caption is written
  `[![alt](src)](href)`, which the hook cannot turn into a figure because
  Goldmark hands it only the image; offering `link` there as well would be a
  second spelling of a form that already works, so it fails the build with
  that advice. A linked image is never zoomable — the runtime skips images
  inside anchors — so it carries no Zoom marker;
- `title` keeps its Markdown meaning (advisory `title` attribute); it never
  becomes a caption; an empty alt marks the image decorative for Zoom;
- RSS uses absolute `src`.

**`image` shortcode** (processed images; replaces the removed positional
`imgproc` form implemented by [pgsty/oink#8](https://github.com/pgsty/oink/issues/8)):

```go-html-template
{{< image src="image.png" command="Fit" options="1200x800" alt="Architecture overview" >}}
Caption with Markdown.
{{< /image >}}

{{< image src="rule.png" command="Resize" options="600x" decorative=true >}}{{< /image >}}
```

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `src` | yes | exact page or global resource path | none |
| `command` | yes | `Fit`, `Resize`, `Fill`, `Crop` | none |
| `options` | yes | Hugo image-processing option string | none |
| `alt` | conditional | meaningful plain string; resource `params.alt` is honored | none |
| `decorative` | conditional | strict boolean; excludes `alt` | `false` |

Named parameters only; the body is the Markdown caption. Either meaningful
alt text (parameter or resource metadata) or `decorative=true` is required.
Static paths, SVG, and remote URLs resolve for other renderers but fail here
because they are not locally processable image resources. HTML renders
`<figure class="td-figure td-figure--processed">` with
`data-td-image-zoom="<full-size URL>"`, `data-no-zoom` when decorative
(a decorative image carries no marker), intrinsic `width`/`height`, and a
`<figcaption>` holding the rendered caption and the resource `byline`. The
figure caps itself at the rendered width through the `--td-figure-max` custom
property rather than an inline `max-width`, so site CSS can override it.
Markdown emits `![alt](src)`, the caption source, and `_byline_`.

### 3.6 Image Zoom

Image Zoom is disabled by default. Site configuration:

```yaml
params:
  ui:
    image_zoom:
      enable: true
```

Page front matter uses the same nested page parameter and overrides the site:

```yaml
---
params:
  ui:
    image_zoom:
      enable: false
---
```

The selected `params.ui.image_zoom.enable` value must be a boolean. An explicit
page `false` wins over a site `true`.

Zoom has one opt-in marker, `data-td-image-zoom`. Everything the theme renders
declares its own eligibility with it: the image render hook (block images and
figures), the `image` shortcode, Book `fig`, and the `gallery` fence. The
marker may carry a value, which is the URL Zoom opens — the `image` shortcode
puts the full-size original there so the dialog does not show the processed
derivative. Without a value the rendered image URL is used. `data-no-zoom`
remains the opt-out.

Zoom progressively enhances content images (`.td-content img`, top-level
`img`, `figure > img` and `p > img`). It skips images inside links or buttons,
images marked `data-no-zoom`, images without alt text, and images already
enhanced.

The build-time candidate scan tests for the marker first, which answers the
question for all theme-rendered content without restating the runtime's rules.
Only an image a site wrote as raw HTML falls back to a structural test, and
that fallback keeps the exclusions so a page of decorative images loads no
runtime. One over-approximation is accepted: a linked standalone image carries
the marker, because the render hook cannot see the wrapping anchor, and the
browser then skips it — such a page loads a runtime it never uses. The runtime
is the only authority on eligibility. Eligible images become real focusable
controls after enhancement. Enter, Space, pointer activation, Escape, the visible close
button, and backdrop activation follow the native dialog model. One dialog is
shared by the page; focus moves into it and returns to the originating control.

The runtime is local, CSP-safe, and loaded only for normal HTML when the
feature is enabled and a candidate exists. It adds no inline event handlers.
Print, Markdown, and RSS render only the underlying image and caption.

Drag, pan, wheel zoom, editing, annotations, image navigation, and third-party
lightbox runtimes are deferred.

### 3.7 Gallery

Gallery has exactly one form: a `gallery` data fence, one image per line.

````markdown
```gallery
![Overview page](overview.webp)
![Detail page](detail.webp) # Request details
![Metrics page](metrics.webp) # Live counters {link=/docs/metrics/}
```
````

Line grammar, mirroring the `filetree` fence:

    ![alt](src) [# description] [{key=value …}]

- The image is anchored at the start of the line, so alt text stays a
  first-class field rather than an attribute an author can forget. It doubles
  as the item's title. An empty alt marks the image decorative: never zoomed,
  no title.
- `#` starts the description. Because the image is parsed first, a `#` inside
  the alt text or the source needs no escaping; `\#` is a literal hash inside
  the description. The description is plain text, like every other public
  string parameter (section 2.3).
- Trailing attributes are `link` (the item becomes an anchor, and therefore is
  not zoomable) and `class` (site CSS tokens). Any other key fails the build,
  as does a line that does not start with an image or that carries text
  without the `#` marker.
- Fence attributes are `tab`, `group`, `value` (adjacent-block tabs) plus
  `class`. There is no `columns`: the grid is responsive.

Sources resolve through the shared image resolver (section 3.5), so page
resources, global assets, static paths and remote URLs behave exactly as they
do for `![alt](src)`, and local resources contribute intrinsic dimensions.

Because the theme renders the grid itself, every eligible image carries the
explicit Image Zoom marker at emit time; Zoom needs no gallery-shaped
structural exception in either the build-time scan or the runtime
(section 3.6).

HTML is `<ul class="td-gallery">` with one `<li class="td-gallery__item">` per
image. Markdown output is the fence source, as it is for every data fence,
because `layouts/all.md` emits `.RenderShortcodes` and therefore does not run
render hooks. Print and RSS render the same grid stacked and without the zoom
markers.

Gallery was an image list with a `{.gallery}` marker in contract version two's
first draft. A list marker is CSS-only — lists have no render hook — so the
theme could not see the items, and could give them neither per-item attributes
nor a Zoom marker. The cost of the fence is that the source no longer renders
as images on GitHub; the benefit is that all four outputs and Zoom are the
theme's to guarantee.

Reordering, uploads, filtering, fullscreen slideshows, carousels, and remote
build-time image fetching are deferred.

### 3.8 Release Assets

Release Assets turns exact `sha*sum` output into a verified download table.
It has a shortcode form and a native fence form:

````markdown
{{< release-assets group="auto" >}}
e3a339fefdd2203825d15438b52f18e729547eb88dae014212a46006a9bd47d1  pig-1.7.0-1.aarch64.rpm
34ce29d75ef9f669f3bf832cc812ae082abda7320ee2b2336ea61e701b9b67f8 *pig-1.7.0-1.x86_64.rpm
{{< /release-assets >}}

```checksums {base="https://downloads.example.org/releases/stable" algo="sha256"}
e3a339fefdd2203825d15438b52f18e729547eb88dae014212a46006a9bd47d1  pig-1.7.0-1.aarch64.rpm
```
````

The only accepted line forms are `<hex><two spaces><name>` and
`<hex><space>*<name>`. Blank lines and lines whose first non-space character is
`#` are ignored. Hash lengths identify MD5, SHA-1, SHA-256, or SHA-512. A block
must use exactly one algorithm; malformed lines, unsupported lengths, and
mixed algorithms fail with the source line. Filenames are one path segment,
remain visible text, and are path-segment escaped when OINK derives links.

Shortcode parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `algo` | no | `md5`, `sha1`, `sha256`, or `sha512`; must match hash length | inferred |
| `base` | conditional | non-empty local, `http`, or `https` URL prefix | derived from page `release` facts |
| `src` | no | exact page-bundle or global asset path | checksum lines in inner content |
| `group` | no | `auto` | author order in one table |

`src` and inner checksum lines are mutually exclusive. A page with `release`
front matter derives the GitHub asset base from its normalized repo and tag;
otherwise `base` is required. `base` is deliberately not a version input and
is rejected when release facts already exist. The `checksums` fence accepts
`base`, `algo`, and `group` as fence attributes with the same rules and no
`src`. The component performs no network request. Type, OS, and architecture
badges are filename-derived decoration and are omitted when inference is
uncertain.

HTML truncates the visible hash but retains the complete hash as the accessible
name and copy source. The local copy runtime (`hasAssetList`) exposes one-row
and whole-block copy buttons; without JavaScript those hidden buttons leave a
complete linked table. Print exposes full hashes without controls. Markdown
and RSS emit pure pipe tables with full hashes and download URLs (the fence
form stays a source fence in `.RenderShortcodes` Markdown output).

### 3.9 Tables and full-width tables

OINK wraps every Goldmark pipe table in a local scroll region
(`layouts/_markup/render-table.html` + `content/table-body.html`). In
interactive HTML the region is keyboard-focusable, uses the localized
accessible name `ui_table_scroll`, and contains horizontal overflow without
widening the page. The table formatting context fills at least the available
prose width. Tables have no runtime.

The table family is selected by the attribute line after the table:

| Attribute line | Meaning | Rendering |
| --- | --- | --- |
| `{.full-width}` | opt out of the prose measure | wrapper `td-table-scroll--full`; the `full-width` class stays on `<table>` |
| `{.fields}` | reference table | `<dl>` (section 3.3) |
| `{.matrix}` | compatibility/feature matrix | first column `<th scope="row">`, wrapper `td-table-scroll--matrix` with sticky header and first column, other cells centered unless the author aligns them |
| `{caption="…"}` | table caption | `<caption class="td-table__caption">`; on `.fields` the list label |
| `{#id}` | stable id | on `<table>` (or on the figure of a numbered table) |
| `{#id num="9-1" caption="…"}` | numbered Book table | `<figure class="td-book-figure td-book-figure--tbl" data-book-kind="tbl" data-book-num>` + `<figcaption>`; registers a `tbl` target (section 3.10) |
| `{tab="…" group="…" value="…"}` | adjacent tables become tabs | tab-block wrapper (section 3.13) |
| any other class | site CSS | passed through on `<table>` |

Exclusivity: `.fields` cannot combine with `.matrix`, `.full-width`, or `num`;
`num` and `tab` are mutually exclusive; `group`/`value` require `tab`. Allowed
keys are `id caption num tab group value` plus `class`, `data-*`, `aria-*`;
`style`, `on*`, and unknown keys fail the build (section 2.2).

Print removes the scroll viewport and renders the complete table at page
width; Markdown and RSS preserve the table data without interactive
attributes.

### 3.10 Numbered Figure, Table, and Equation

The Book components make a manual, language-aware number and stable target one
semantic unit. Every kind has a shortcode (full) form and a native form:

```go-html-template
{{< fig num="2-1" id="office_2003" src="/fig/word.png"
    caption="The Word 2003 interface" alt="Word 2003 with stacked toolbars" />}}

{{< tbl num="9-1" caption="Isolation-level behavior" >}}
| Anomaly | RC | RR | SER |
| --- | --- | --- | --- |
{{< /tbl >}}

{{< eq num="5.3" >}}X \approx \frac{C}{R+Z}{{< /eq >}}

{{< eg num="4-1" caption="Analytics query" >}}
```sql
SELECT date_trunc('day', ts) FROM events;
```
{{< /eg >}}
```

Native forms — one block plus an attribute line:

````markdown
![Word 2003 with stacked toolbars](/fig/word.png)
{#office_2003 num="2-1" caption="The Word 2003 interface" width=640 height=480}

| Anomaly | RC | RR | SER |
| --- | --- | --- | --- |
{#tab_iso num="9-1" caption="Isolation-level behavior"}

$$
X \approx \frac{C}{R+Z}
$$
{#eq_x num="5.3"}

```sql {num="4-1" caption="Analytics query" #example-query}
SELECT date_trunc('day', ts) FROM events;
```
````

The same `eq` name also has a deliberately smaller escape-hatch form:

```go-html-template
{{< eq >}}X \approx \frac{C}{R+Z}{{< /eq >}}
```

Without parameters it renders non-empty TeX as display math, registers no
numbered target, and emits a plain `$$` source block in Markdown and RSS.
`id`, `caption`, and `class` require `num`; they cannot create a partially
numbered equation.

Shared rules for all four kinds and both forms:

- `num` is a quoted string matching `[0-9A-Za-z.-]+`; default IDs are
  `fig-<num>`, `tbl-<num>`, `eq-<num>`, and `eg-<num>`; an explicit ID matching
  `[A-Za-z][A-Za-z0-9_.:-]*` is preserved without a prefix. In the native
  fence form the author `#id` names the `<figure>` (the Book target), not the
  code block root.
- The block type decides the kind (image → `fig`, table → `tbl`, `$$` block →
  `eq`, fence → `eg`). `caption` is plain text; it is optional for `fig`,
  `tbl`, and `eq` and required for `eg` (a fence `caption` without `num` and a
  fence `num` without `caption` are build errors). Alt text is never turned
  into a caption.
- The page registry (`tdBookTargets`) rejects duplicate IDs and two targets of
  the same kind/number that claim different IDs; identity and Book order come
  from the source position, so hook and shortcode targets share one namespace.
- Figure and Table shortcode bodies pass through `content/render-block.html`;
  Equation content passes directly through the local server-side KaTeX
  renderer. Table keeps its Markdown table, label, caption, and anchor inside
  one `<figure>`. Equation places its number at the right edge. Example places
  its caption bar above the body (O'Reilly convention).
- The `fig` shortcode additionally accepts the mechanical DDIA migration
  surface `src/id/caption/title/class/link/alt/width/height`. `title` aliases
  `caption` but cannot appear beside it; `src` and inner content are mutually
  exclusive; width and height are positive integers. Class tokens and links
  use strict grammars. A missing legacy `alt` falls back to the caption for
  compatibility; new authored figures should always supply explicit meaningful
  alternative text. `scripts/check-book.py` rejects empty alternatives beside
  numbered captions. Native figures accept `width`/`height` attributes for
  static or remote images and pass `class` tokens through.
- `eg` replaces the removed leaf `example` shortcode: it is a wrapper whose
  body is Markdown (usually one or more fences); its native form is a single
  fence with `num` and `caption`.

HTML and print use `<figure>` and `<figcaption>` with localized
Figure/Table/Equation/Example prefixes and stable IDs. Print removes an
interactive table's scroll wrapper. Markdown and RSS emit `**Figure 2-1.**
caption` followed by the original source body for the shortcode forms;
Equation emits the authored TeX delimiter block. Native forms pass through
Markdown output as their source block plus attribute line. No Book component
loads JavaScript.

### 3.11 Cross references and Book indexes

`xref` provides a current-language internal link and may appear before its
target:

```go-html-template
{{< xref fig="2-1" anchor="office_2003" >}}
{{< xref eg="4-1" >}}
{{< xref page="../replication" anchor="sync-mode" >}}synchronous mode{{< /xref >}}
```

Exactly one of `fig`, `tbl`, `eq`, or `eg` may supply a numbered localized
label. `anchor` overrides the derived target. `page` resolves through Hugo's
current language page lookup. With no kind, `anchor` and non-empty inner link
text are required. Rendering never reads a target registry; post-build
validation checks the target ID, kind, and number so forward references remain
legal.

Book indexes aggregate the registered targets in Book reading order:
`{{< book-figures >}}` (figures only), `{{< book-tables >}}`,
`{{< book-equations >}}`, and `{{< book-examples >}}`; they take no
parameters. `{{< book-toc depth=1..3 >}}` uses the same Book tree as the
sidebar; depth three includes Hugo fragment headings and `drafts=false`
filters draft rows. In whole-Book print, all of these links become local
document fragments. Markdown ToC is a nested list; RSS strips Book ToC.

### 3.12 Callouts

Callouts are GitHub/Obsidian-style blockquotes rendered by
`layouts/_markup/render-blockquote-alert.html`:

```markdown
> [!TIP] Title with `inline` Markdown
> Body: page-level Markdown — lists, fences, tables, nested callouts.

> [!NOTE]- Collapsed by default (`+` opens it initially)
> Body.

> [!DETAILS] Neutral disclosure block
> Body.
{icon="fa-solid fa-rocket"}
```

- Canonical types: `note tip important warning caution success danger
  question example quote` and `details`; each has a localized default title
  (`i18n <type>`) and, except `details`, a default icon. Unknown types render as a plain
  `<blockquote>` with the visible marker (`[!TYPE]±` and title) preserved so
  nothing is lost.
- `-` collapses (default closed), `+` collapses (default open); `details`
  collapses without a sign. Collapsible callouts are native `<details
  class="td-callout td-callout--<type> td-callout--collapsible">` with a
  `<summary class="td-callout__title">`; static callouts are `<div class="td-callout
  td-callout--<type>" role="note">` with `.td-callout__title` (icon +
  `.td-callout__label`) and `.td-callout__body`.
- Attribute line: `icon` (one Font Awesome pair) replaces the type icon;
  `class` passes through; every other key, `style`, and `on*` fail the build.
- The title is inline Markdown; the body is page-level Markdown.
- Print and RSS render a static, expanded `<div>` (collapsible ones carry
  `data-td-callout-collapsible`); Markdown output keeps the source blockquote.
  No runtime.

### 3.13 Tabs

Tabs have two forms and one runtime (`assets/js/tabs.js`, flag `hasTabs`,
no Bootstrap).

**Adjacent blocks.** Fences and tables that carry a `tab` attribute:

````markdown
```bash {tab="Homebrew" group="install" value="brew"}
brew install pigsty
```
```bash {tab="APT" value="apt"}
sudo apt install pigsty
```
````

- `tab` is the visible label (non-empty); `group` (first block of a run,
  `^[a-z][a-z0-9_-]*$`) opts into hash, sync, and persistence; `value`
  (`^[a-z0-9][a-z0-9_-]*$`) is required on every block when the run has a
  group and forbidden without one; `group`/`value` without `tab`, or `num`
  together with `tab`, fail the build. A fence `tab` coexists with `title`
  (the tab label goes to the tablist, the title stays the panel's filename
  header).
- Each block renders independently and completely as a titled block —
  `<div class="td-tab-block td-tab-block--code|table" data-td-tab="…"
  [data-td-tab-group] [data-td-tab-value] data-td-tab-kind="code|table">` with a
  `.td-tab-block__title` — so GitHub, print, and no-JS readers see consecutive
  titled blocks with nothing lost.
- At load the runtime regroups runs of **two or more adjacent siblings of the
  same kind** into the tabs DOM below (`td-tabs td-tabs--adjacent
  td-tabs--<kind>`); embedded code blocks receive `td-code--embedded`. A grouped
  run missing a value on some block, or a run with duplicate values, is left as
  titled blocks with a console warning. Panel IDs are `<group>-<value>` in a
  grouped run and generated (`td-tabs-run-<n>-<hash>-<value>`) otherwise.

**Shortcode form** (Markdown bodies):

```go-html-template
{{< tabs group="setting" default="conf" label="MinIO settings" >}}
{{< tab label="Environment Variable" value="env" >}}
Markdown body.
{{< /tab >}}
{{< tab label="Configuration Setting" value="conf" >}}
Markdown body.
{{< /tab >}}
{{< /tabs >}}
```

`tabs`: `group` (optional, same grammar), `default` (a child value; requires
`group`), `label` (accessible tablist name; default `ui_tabs_label`). `tab`:
`label` (required), `value` (required with a group, forbidden without;
ungrouped children get generated `tab<n>` values). Duplicate values, a `tabs`
without children, and stray content between children fail the build. Bodies
render through `content/render-block.html`.

DOM contract shared by both forms:

```html
<div class="td-tabs" data-td-tabs data-td-tabs-group="setting" data-td-tabs-default="conf">
  <div class="td-tabs__list" role="tablist" aria-label="…">
    <button class="td-tabs__tab" type="button" role="tab" id="setting-conf-tab"
            aria-controls="setting-conf" aria-selected="true" tabindex="0" data-td-tabs-value="conf">…</button>
  </div>
  <div class="td-tabs__panel" id="setting-conf" role="tabpanel"
           aria-labelledby="setting-conf-tab" tabindex="0" data-td-tabs-value="conf" data-td-tabs-active>
    <div class="td-tabs__panel-title" aria-hidden="true">…</div>
    <div class="td-tabs__panel-body">…</div>
  </section>
</div>
```

Server HTML hides nothing: until the runtime marks the set with
`data-td-tabs-ready`, CSS hides the tablist and shows every panel under its own
title; after enhancement inactive panels get `hidden`. Behaviour: roving
tabindex; Left/Right (RTL aware) and Home/End move and activate; focus stays on
the tab; only grouped sets write `history.replaceState` hash `#<group>-<value>`
and localStorage `td-tabs:v1:<group>` on user activation, synchronize every set
of the same group on the page (a peer lacking the value keeps its selection),
and read the stored value at load; a URL hash naming a panel wins over storage,
activates its set, and scrolls it into view (smooth unless
`prefers-reduced-motion`). Print and RSS render titled static sections
(shortcode form: no ARIA roles); Markdown output renders `**Label**` sections
followed by each body (fence tabs stay source fences).

### 3.14 Steps

```markdown
1. Install the dependencies

   Any block: paragraphs, fences (also `{tab=}` fences), callouts, nested lists.

1. ### Initialise {#init}
   A heading inside a step enters the table of contents.
1. Verify
{.steps}
```

- Native form: an ordered list followed by `{.steps}`; CSS counters draw the
  markers and honour `start` (`ol[start]` from 2 through 40). Write every item
  as `1.` so the content indent is a constant three spaces. Items may contain
  every block-level construct and `{{< >}}` shortcodes, but not `{{% steps
  %}}` or any other multi-line `%` output.
- Full form: `{{% steps %}}` wrapping direct child headings (`##`–`######`);
  each heading starts a step and the body needs no indentation. It is the only
  `%` shortcode and the only place where a `%` container may hold shortcodes
  such as `tabs`, `cards`, or `fields`.
- No runtime; Markdown output is the source; print keeps the numbering.

### 3.15 Cards

```markdown
- [Install](/docs/install/) — Deploy from scratch.
- [Configure](/docs/configure/) — Tune the runtime.
{.cards}
```

Native form: a link list followed by `{.cards}`. The link is the card title;
everything after it in the item is the description (tight form after ` — `,
or a second paragraph in a loose list). CSS grid, no runtime.

Full form for icons, badges, images, and Markdown bodies:

```go-html-template
{{< cards >}}
{{< card title="Install" link="/docs/install/" icon="fa-solid fa-rocket" badge="New"
        image="cover.png" image_alt="Installer screenshot" >}}
Deploy from scratch, *with Markdown*.
{{< /card >}}
{{< /cards >}}
```

`cards` takes no parameters. `card`: `title` (required), `link` (section 2.4;
external links get `rel="noopener"`), `icon` (one Font Awesome pair), `badge`
(plain text), `image` (shared resolver) with `image_alt` or `decorative=true`
(one is required, both is an error). The body is the Markdown description.
HTML: `.td-content-cards.td-content-cards--auto` grid of
`article.td-content-card` (image, head with icon/title/badge, description).
Markdown output: `- [Title](link) (badge) — description` per card.

### 3.16 Data fences

Fenced blocks whose language names a render hook are data fences; the fence
is their Markdown-native form and the code shell does not apply.

````markdown
```echarts {height="360px"}
series: [{type: bar, data: [1, 2, 3]}]
tooltip: {formatter: "$fn:bytesFormatter"}
```
```infographic {height="480px" full=true}
… infographic DSL …
```
```checksums {base="https://…/download/v1.7.0/" algo="sha256"}
e3a339fe…47d1  pig-1.7.0-1.aarch64.rpm
```
````

- `echarts`: declarative YAML/JSON options only (a non-mapping or invalid
  document fails the build); attributes `height` (safe CSS length, default
  `400px`), `theme`, `full=true`; callbacks stay the `"$fn:<name>"` bridge
  resolved from `window.tdEchartsFunctions` (unregistered names are ignored
  with a console warning); the fence cannot carry JavaScript. Sets
  `hasEcharts`.
- `infographic`: attributes `height` (`auto` or a safe CSS length), `full`;
  sets `hasInfographic`.
- `checksums`: section 3.8.
- `filetree`: section 3.4 (`hasFileTree` loads the divider runtime only when
  the tree has comments).
- Unknown attributes, `style`, and `on*` fail the build; `class` passes
  through. Print, Markdown, and RSS show the source in a `<pre>` (`echarts`,
  `infographic`), the static asset table (`checksums`), or the static tree
  (`filetree`, section 3.4).
- The existing `mermaid`, `plantuml`, `markmap`, `math`, and `chem` fences are
  unchanged.

### 3.17 Include, Param, and Comment

- `{{< include file="path" [code=true] [lang="yaml"] >}}` (named only) inlines
  a file resolved as a page resource, then a global asset, then a file under
  `content/` (a leading `/` is the content root, otherwise relative to the
  page's directory); `..` is rejected and a missing file fails the build.
  Without `code` the file is Markdown rendered in the page context (as
  `readfile` did, this rendered HTML also reaches the Markdown output); with
  `code=true` (and optional `lang`) it is a code block through the shared
  code pipeline, and the Markdown output emits a source fence.
- `{{< param name >}}` prints a page or site parameter: a missing value and a
  non-scalar value (map, list) fail the build; the output is HTML-escaped plain
  text usable in prose, tables, links, and fences.
- `{{< comment >}}…{{< /comment >}}` drops its content in every output.

## 4. Output matrix

| Component | HTML | Print | Markdown | RSS | JavaScript disabled | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| Badge | semantic `<span>` or `<a>` | monochrome inline badge | emphasized text or link | static inline HTML | identical content | none |
| Kbd | nested `<kbd>` sequence | visible key boundaries | `Ctrl + K` | static inline HTML | identical content | none |
| Fields | responsive semantic `<dl>` (both forms) | complete definition list | source table / metadata bullet list | complete static `<dl>` | identical content | none |
| FileTree | monospace panel, aligned `#` comment column, native `<details>` directories, draggable split | same panel, static and fully expanded | the `filetree` fence source | source in `<pre>` | identical content (disclosure is native; split stays at the build-time width) | one local split runtime, only with comments |
| Shared image | `<img>`, `<img class="td-image">`, or `<figure>` with caption | image/figure and caption | source image (+ attribute line) | absolute-URL image | identical content | none |
| Image Zoom | shared image plus eligible enhancement | shared image only | shared image only | shared image only | original image remains readable | one opt-in local dialog runtime |
| Gallery | responsive image grid | stacked grid | fence source | stacked grid | complete static grid | reuses Image Zoom only |
| Release Assets | linked table with copy controls | linked static table with full hashes | pipe table (shortcode) / source fence (`checksums`) | pipe table with full hashes | complete linked table | one opt-in local copy runtime |
| Table | keyboard-focusable contained scroll region; family markers | complete table at page width | source pipe table | static table | complete table remains readable | none |
| Eq escape | display KaTeX/MathML | static display KaTeX/MathML | plain `$$` TeX block | plain `$$` TeX block | identical static formula | none |
| Fig/Tbl/Eq/Eg | semantic numbered figure (both forms) | figure with stable ID | labeled source content (shortcode) / source block (native) | labeled source content | identical numbered content | none |
| Xref/Book index | current-language links and nested lists | document-local links and nested lists | relative links and nested lists | xref only; Book ToC stripped | identical links | none |
| Callout | `<div role="note">` or native `<details>` | static expanded block | source blockquote | static expanded block | identical content, native disclosure | none |
| Tabs | tablist + panels, nothing hidden server-side | titled static sections | `**Label**` sections / source fences | titled static sections | titled stacked panels | one opt-in local tabs runtime |
| Steps | numbered `ol.steps` / `.td-steps` | same numbering | source list / headings | static list | identical content | none |
| Cards | `ul.cards` grid / `.td-content-cards` | stacked cards | source list / link bullets | static list | identical content | none |
| Data fences | rendered chart / asset table | source `<pre>` / static table | source fence | source `<pre>` / pipe table | source fence readable | opt-in local chart runtimes |
| Include/Param | rendered file / escaped scalar | same | fence / escaped scalar | same | identical content | none |

## 5. Verification contract

Each implementation change adds the smallest focused fixture and checker that
proves its contract at Hugo Extended 0.160.1 and 0.164.0.

Theme-level checks (`scripts/check-content-primitives.py`,
`scripts/check-media-primitives.py`, `scripts/check-gallery.py`,
`scripts/check-image-zoom.py`, `scripts/check-code-blocks.py`,
`scripts/check-components.py`, `scripts/check-book.py`,
`scripts/check-release-assets.py`, `scripts/check-goldens.py`) cover:

- valid HTML, print, Markdown, and RSS output for both forms of each
  component;
- strict invalid-parameter and invalid-attribute failures with source
  positions, including the hook attribute policy and the exclusivity matrix;
- Page Store/runtime absence on unrelated pages and the bundle key;
- escaping, subpath URLs, repeat rendering, scoped ID behavior;
- semantic markup, RTL, dark mode, print, reduced motion, forced colors, long
  content, and CJK where relevant;
- Book xref target/kind/number consistency, image alternatives, fragment-tree
  ToC depth, and whole-Book duplicate-ID safety;
- `tests/js/tabs.test.js` for the tabs runtime contract.

The `oink.pgsty.com` regression site owns:

- English documentation and matching Simplified Chinese `.zh.md` pages;
- representative light/dark and desktop/mobile examples;
- generated Markdown goldens;
- Playwright interaction checks and axe coverage; and
- the released Hugo module pin and later hosted verification.

Theme source, a local sibling-checkout build, a tagged theme release, the
consumer-site module update, and hosted deployment are separate evidence
gates. Passing an earlier gate must not be recorded as completion of a later
one.

## 6. Contract changes

This document is normative for the everyday content components. A deliberate
change must update this document, its contract checker
(`scripts/check-content-primitives-contract.py`), the affected implementation,
the design record (`plan/design/components.md`), and any already-shipped
compatibility guidance in the same review. Additive parameters remain deferred
until their behavior is specified across the full output matrix.

Version two (OINK 0.5/0.6) changes from version one: Badge lost `outline`;
Fields gained the `{.fields}` table form;
FileTree and Gallery became the `filetree` and `gallery` data fences (the
`filetree`, `filetree/folder`, `filetree/file`, `gallery`, `gallery/image`
shortcodes and the interim `{.filetree}` / `{.gallery}` list markers were
removed); `imgproc`
became the named-only `image` shortcode and Markdown images gained a render
hook; the table family, Callouts, Tabs, Steps, Cards, data fences, `include`, strict `param`, and the
Book `eg`/native forms/`book-*` indexes were added; `alert`, `details`,
`pageinfo`, `tabpane`/`tab` (legacy), `code-group`/`code-tab`, the card family,
`doc-carousel`, `echarts`/`infographic` shortcodes, `readfile`, `iframe`,
`conditional-text`, `_param`, `blocks/*`, and the leaf `example` were removed.
