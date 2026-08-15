# Everyday content primitives contract

Status: frozen for implementation

Tracking: [pgsty/oink#3](https://github.com/pgsty/oink/issues/3)

Contract issue: [pgsty/oink#4](https://github.com/pgsty/oink/issues/4)

Compatibility floor: Hugo Extended 0.160.1

## 1. Decision

OINK will add a small set of high-frequency content primitives for engineering
documentation without changing its Hugo-only consumer boundary. The public
interfaces in this document are the version-one contract for Badge, Kbd,
Fields, FileTree, Image Zoom, Gallery, Release Assets, and PRD 5 numbered Book
components.

The implementation order is intentional:

1. Badge, Kbd, Fields, and FileTree establish the non-interactive contract.
2. A shared image resolver and an accessible `imgproc` migration establish the
   media contract.
3. Image Zoom progressively enhances eligible images.
4. Gallery reuses the image resolver and the Zoom runtime.
5. Release Assets adds a strict checksum parser and one conditional copy runtime.

A standalone public Icon shortcode is deferred. A component may use a small,
private, allowlisted icon registry for its own decoration, but that registry is
not a content authoring API.

## 2. Shared authoring contract

### 2.1 Notation and nesting

All new shortcodes use standard notation (`{{< ... >}}`). This keeps their
generated markup out of the surrounding Markdown parse and makes non-HTML
fallbacks explicit.

- Badge and Kbd are inline shortcodes.
- Fields and Gallery are collector shortcodes. Evaluating the parent's
  `.Inner` lets validated children register ordered data; the parent owns all
  final rendering.
- FileTree renders recursively through `.Inner`. Folder and file children own
  their nested list fragments instead of flattening the tree into Scratch.
- Among the everyday components in sections 3.1 through 3.9, Fields alone
  accepts Markdown in a field description. After the child has registered its
  raw inner content, the parent uses `.Page.RenderString` for HTML, print, and
  RSS; Markdown output preserves and indents the validated source Markdown
  instead. Book Figure/Table bodies in section 3.10 are the second documented
  Markdown surface. Public string parameters, including captions, remain
  plain text.

Nested public names are stable:

- `field` is valid only inside `fields`.
- `filetree/folder` and `filetree/file` are valid only inside `filetree` or a
  `filetree/folder` ancestor, as appropriate.
- `gallery/image` is valid only inside `gallery`.

Hugo supports shortcode templates in subdirectories at the compatibility
floor, so the slash-separated FileTree and Gallery names are part of the
public API. Flat aliases are not created preemptively.

Hugo does not permit named and positional arguments in the same call. Each
OINK shortcode therefore chooses one form permanently:

- Kbd is positional-only.
- Every other primitive is named-only.

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

The everyday components in sections 3.1 through 3.9 do not accept arbitrary
`class`, `style`, color, event-handler, or public `id` parameters. The Book
Figure compatibility surface in section 3.10 is the explicit exception: it
accepts a grammar-constrained semantic `id` and safe class tokens so DDIA and
O'Reilly anchors can migrate without breaking public links. It never accepts
`style`, color, or event handlers.

### 2.3 Escaping and rendered content

Author text remains data in every output:

- HTML attributes and text use Go template contextual escaping.
- Author values must not be passed to `safeHTML`, `safeURL`, or `safeJS` to
  suppress validation or escaping.
- Theme-owned static markup may be returned as trusted template output only
  after every author value has been inserted through a safe context.
- Fields descriptions and Book Figure/Table bodies are the documented
  arbitrary Markdown surfaces. HTML and print render them through
  `.Page.RenderString`, using the consuming site's Goldmark security policy.
  Their Markdown fallback retains source Markdown and must not convert it to
  HTML first.
- Markdown fallbacks use context-specific escaping for plain text, code spans,
  emphasis, and link destinations. They do not reuse an HTML escape helper.
- A code span chooses a fence longer than any run of backticks in its value.

The Markdown output must contain no component classes, `data-*` runtime
attributes, `<dialog>`, `<details>`, `<dl>`, or other runtime HTML emitted by
these primitives.

### 2.4 URL policy

Badge `link`, FileTree file `link`, Gallery/Book Figure image `src`, Book Figure
`link`, and shared media URLs use one internal URL helper.

For links:

- `#fragment`, query-only, relative, and root-relative site URLs are allowed.
- Relative and root-relative paths are site-relative and are passed through
  Hugo's subpath-safe URL handling. They are not resolved relative to the
  current content file.
- Explicit `http`, `https`, and `mailto` URLs are allowed.
- Protocol-relative URLs and every other scheme, including `javascript`,
  `data`, `vbscript`, and `file`, are rejected.
- ASCII control characters and whitespace inside a URL are rejected.
- Components do not force a new browsing context with `target="_blank"`.

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
New components branch on this value within their shared template instead of
depending on output-specific shortcode lookup.

### 2.6 Page Store, repeated rendering, and IDs

Hugo may render a shortcode more than once for summaries, alternate outputs,
or repeated `.Content` access. All Page Store writes must therefore be
idempotent.

- Boolean feature flags use `Set true`; they are never counters.
- Ordered child data is scoped to the parent shortcode Scratch, not the Page
  Store.
- A duplicate check uses a stable owner composed from shortcode name and
  ordinal. Seeing the same owner again is allowed; seeing a different owner for
  the same public value is an error.
- The everyday MVP does not expose author-supplied DOM IDs. Book numbered
  components are the documented exception and use a separate page registry.
- Generated IDs use a component prefix, a page-derived digest where needed,
  and the shortcode ordinal. Interactive IDs must be registered before output.
- A future public ID must share a page-wide registry with existing code
  components so ARIA references cannot collide across component families.

Feature flags are set only after validation. Interactive flags are set only in
`html` output and only when the feature is enabled and the page has a usable
candidate.

### 2.7 Runtime loading

Badge, Kbd, Fields, FileTree, Tables, and the numbered Book components never
load JavaScript. Image Zoom owns one opt-in dialog runtime and Gallery may
request that same runtime without adding another bundle. Release Assets owns a
separate opt-in copy runtime keyed by `hasAssetList`; it never reads the Image
Zoom flag. Both are appended from `layouts/_partials/scripts.html` only after
content sets its own Page Store flag. Print, Markdown, and RSS never receive
either runtime.

The server-rendered HTML is complete before enhancement. If JavaScript is
disabled, blocked, fails, or `HTMLDialogElement` is unavailable, all original
images and captions remain readable.

### 2.8 CSS and accessibility

Components consume semantic OINK/Bootstrap tokens and may define component
aliases. They must not embed author colors or literal bundled font families.

- Use logical properties so spacing and alignment work in RTL.
- Long names, types, paths, and captions must wrap or scroll within their own
  component without creating page-level horizontal overflow.
- Dark mode derives from semantic tokens.
- Print removes decorative color dependence, exposes complete content, and
  avoids hiding descendants of closed disclosure widgets.
- Forced-colors mode preserves visible boundaries and focus indicators with
  system colors or `currentColor`.
- Reduced motion disables non-essential Zoom transitions.
- Native semantics take precedence over ARIA. FileTree does not claim
  `role="tree"`; Fields remains a definition list; Zoom uses a real dialog and
  real buttons.

### 2.9 Visible strings, aliases, and deprecation

Author-provided labels, captions, names, keys, and alt text are rendered as
provided and are not looked up through i18n.

Every theme-owned visible or assistive string is an i18n key submitted to all
locale files in the same change. Initial examples include the Kbd spoken
separator and Image Zoom dialog controls. The Fields `required` and `default`
metadata labels are a deliberate exception: they are API vocabulary rendered
untranslated in every locale.

An intentional historical alias:

1. renders the canonical behavior;
2. emits `warnf` with `.Position` and the replacement;
3. remains for at least one complete minor release after the warning first
   ships; and
4. is removed only with an explicit changelog entry.

No aliases are introduced for parameters that have not shipped publicly.

## 3. Public component APIs

### 3.1 Badge

```go-html-template
{{< badge text="Beta" tone="warning" >}}
{{< badge text="Deprecated" tone="danger" outline=false >}}
{{< badge text="v0.3" tone="info" link="/release/" >}}
```

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `text` | yes | non-empty plain string | none |
| `tone` | no | `neutral`, `info`, `success`, `warning`, `danger` | `neutral` |
| `link` | no | URL allowed by section 2.4 | none |
| `outline` | no | strict boolean | `true` |

HTML uses an inline `<span>` when `link` is absent and an `<a>` when it is
present. Tone and outline map to semantic tokens. Tone is not the only carrier
of meaning: the author-provided text remains visible in all modes.

There is no public Badge `icon`, `class`, or color parameter in version one.
Adding an allowlisted Badge icon later is backwards compatible.

Markdown fallback:

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
mixed in one call.

HTML emits a sequence wrapper with one nested `<kbd>` per key. Visible `+`
separators and a localized simultaneous-key separator produce an understandable key
sequence without repeating punctuation to screen readers.

Print and Markdown use the exact plain notation:

```text
Ctrl + K
⌘ + Shift + P
```

### 3.3 Fields and Field

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
registered, the parent renders that description for HTML, print, and RSS while
retaining the source Markdown in Markdown output. An explicit empty-string
default is displayed as `""`; an absent default emits no default metadata.

HTML is one `<dl>` with HTML-valid wrappers containing paired `<dt>` and
`<dd>` elements. It must not use `display: contents`. Each entry stacks two
rows: the `<dt>` header row carries the field name followed by the inline
`type`, `required`, and `default` metadata in that order, and the `<dd>` below
it carries the description. Entries are separated by hairline dividers, not
boxed cells or columns. An optional label is visible and associated with the
list without inventing a fixed heading level.

Markdown fallback is an ordered author-preserving bullet list:

```markdown
**Configuration fields**

- `offlineSearch` — `boolean`; required; default: `true`

  Enables the local search index and command palette.
```

When supplied, the author-provided label precedes the list as emphasized plain
text so it remains visible outside HTML.

The `required` and `default` metadata labels are untranslated API vocabulary:
every locale renders the literal words `required` and `default` in HTML,
print, Markdown, and RSS output alike. They are not i18n keys. The deferred
parameters are `kind`, `location`, `since`, `deprecated`, and `link`, along
with nested schemas and compiler-driven type extraction.

### 3.4 FileTree

```go-html-template
{{< filetree label="Repository structure" >}}
  {{< filetree/folder name="content" open=true >}}
    {{< filetree/file name="_index.md" >}}
    {{< filetree/folder name="docs" open=true >}}
      {{< filetree/file name="getting-started.md" >}}
      {{< filetree/file name="configuration.md" link="/docs/configuration/" >}}
    {{< /filetree/folder >}}
  {{< /filetree/folder >}}
  {{< filetree/file name="hugo.yml" >}}
{{< /filetree >}}
```

`filetree` parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `label` | no | non-empty plain string | no visible label |

`filetree/folder` parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `name` | yes | non-empty plain string | none |
| `open` | no | strict boolean | `false` |

`filetree/file` parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `name` | yes | non-empty plain string | none |
| `link` | no | URL allowed by section 2.4 | none |

HTML uses nested lists. A folder contains native `<details>` and `<summary>`;
`open` affects only its initial HTML state. FileTree does not use JavaScript or
`role="tree"`.

Print and RSS expose every descendant regardless of `open`. Markdown uses a
nested list, appends `/` to folder names, and preserves file links:

```markdown
- content/
  - _index.md
  - docs/
    - getting-started.md
    - [configuration.md](/docs/configuration/)
- hugo.yml
```

Author-selected icons, badges, status metadata, sorting, filesystem reads,
file metadata, selection, and direction-key navigation are deferred.

### 3.5 Shared images and imgproc compatibility

The shared image resolver is internal. It resolves an explicit `http` or
`https` source directly; otherwise it tries, in order:

1. a page resource;
2. a global Hugo asset; and
3. a static/public site path.

The result records the rendered URL, canonical full-size URL, media type,
intrinsic width and height when Hugo knows them, alt text, caption, and whether
the source can be processed. Missing page/global resources and invalid image
operations fail with the caller's position. A static or remote image may omit
dimensions when the build cannot know them without I/O.

New image APIs require meaningful alt text unless they expose an explicit
decorative mode. Gallery version one always requires meaningful alt text.

The accessible named `imgproc` form implemented by
[pgsty/oink#8](https://github.com/pgsty/oink/issues/8) resolves exact page or
global resources and requires either meaningful alternative text or explicit
decorative intent:

```go-html-template
{{< imgproc src="image.png" command="Fit" options="1200x800" alt="Architecture overview" >}}
Caption with Markdown.
{{< /imgproc >}}

{{< imgproc src="rule.png" command="Resize" options="600x" decorative=true >}}{{< /imgproc >}}
```

`command` is exactly one of `Fit`, `Resize`, `Fill`, or `Crop`; `options` uses
Hugo image-processing syntax. Static paths, SVG, and remote URLs resolve for
shared renderers but fail when passed to `imgproc` because they are not locally
processable image resources.

The existing positional `imgproc` call remains a compatibility boundary:

```go-html-template
{{< imgproc "image.png" "Fit" "1200x800" >}}Caption{{< /imgproc >}}
```

It retains the historical fuzzy page-resource lookup and does not emit a
deprecation warning in this release. Resource `params.alt` and `params.byline`
are honored when present; otherwise the legacy image receives `alt=""` while
its caption remains visible. Zoom and Gallery must use the shared resolver
rather than copying `imgproc` lookup behavior.

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

The MVP progressively enhances an image only when it is standalone content or
an explicit Gallery image. It skips images inside links or buttons, images
marked `data-no-zoom`, and inline decorative images. `data-zoom-src` from the
shared renderer wins; otherwise the rendered image URL is used.

The build-time candidate scan recognizes direct paragraph/figure images and
theme-owned Gallery markers; the browser repeats the same structural checks
before mutation. A standalone legacy image with `alt=""` remains eligible and
its trigger is named by the localized action text. Images explicitly authored
with `decorative=true` receive `data-no-zoom`, so that intentional declaration
is never turned into a control.

Eligible images become real focusable controls after enhancement. Enter,
Space, pointer activation, Escape, the visible close button, and backdrop
activation follow the native dialog model. One dialog is shared by the page;
focus moves into it and returns to the originating control.

The runtime is local, CSP-safe, and loaded only for normal HTML when the
feature is enabled and a candidate exists. It adds no inline event handlers.
Print, Markdown, and RSS render only the underlying image and caption.

Drag, pan, wheel zoom, editing, annotations, image navigation, and third-party
lightbox runtimes are deferred.

### 3.7 Gallery and Gallery Image

```go-html-template
{{< gallery columns=2 label="Console screenshots" >}}
  {{< gallery/image src="overview.webp" alt="Overview page" >}}
  {{< gallery/image src="detail.webp" alt="Detail page" caption="Request details" >}}
{{< /gallery >}}
```

`gallery` parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `columns` | no | strict integer from `1` through `4` | `2` |
| `label` | no | non-empty plain string | no visible label |

`gallery/image` parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `src` | yes | image URL allowed by section 2.4 | none |
| `alt` | yes | non-empty meaningful plain string | none |
| `caption` | no | non-empty plain string | none |

Gallery preserves author order and renders one semantic figure per image.
HTML is a responsive grid with intrinsic dimensions when known,
`loading="lazy"`, and captions that do not break the page width. Narrow
viewports may reduce the effective column count without changing the requested
desktop maximum.

Gallery reuses the shared image resolver and Image Zoom eligibility. It never
adds a carousel, second lightbox, second dialog, or separate runtime.

Markdown emits ordinary images in author order, with an italic caption
paragraph when supplied:

```markdown
![Overview page](overview.webp)

![Detail page](detail.webp)

_Request details_
```

Print and RSS render static sequential figures. Reordering, uploads,
filtering, fullscreen slideshows, decorative Gallery images, and remote
build-time image fetching are deferred.

### 3.8 Release Assets

Release Assets turns exact `sha*sum` output into a verified download table:

```go-html-template
{{< release-assets group="auto" >}}
e3a339fefdd2203825d15438b52f18e729547eb88dae014212a46006a9bd47d1  pig-1.7.0-1.aarch64.rpm
34ce29d75ef9f669f3bf832cc812ae082abda7320ee2b2336ea61e701b9b67f8 *pig-1.7.0-1.x86_64.rpm
{{< /release-assets >}}
```

The only accepted line forms are `<hex><two spaces><name>` and
`<hex><space>*<name>`. Blank lines and lines whose first non-space character is
`#` are ignored. Hash lengths identify MD5, SHA-1, SHA-256, or SHA-512. A block
must use exactly one algorithm; malformed lines, unsupported lengths, and
mixed algorithms fail with the source line. Filenames are one path segment,
remain visible text, and are path-segment escaped when OINK derives links.

Parameters:

| Parameter | Required | Accepted values | Default |
| --- | --- | --- | --- |
| `algo` | no | `md5`, `sha1`, `sha256`, or `sha512`; must match hash length | inferred |
| `base` | conditional | non-empty local, `http`, or `https` URL prefix | derived from page `release` facts |
| `src` | no | exact page-bundle or global asset path | checksum lines in inner content |
| `group` | no | `auto` | author order in one table |

`src` and inner checksum lines are mutually exclusive. A page with `release`
front matter derives the GitHub asset base from its normalized repo and tag;
otherwise `base` is required. `base` is deliberately not a version input and
is rejected when release facts already exist. The component performs no
network request. Type, OS, and architecture badges are filename-derived
decoration and are omitted when inference is uncertain.

HTML truncates the visible hash but retains the complete hash as the accessible
name and copy source. The local copy runtime exposes one-row and whole-block
copy buttons; without JavaScript those hidden buttons leave a complete linked
table. Print exposes full hashes without controls. Markdown and RSS emit pure
pipe tables with full hashes and download URLs.

### 3.9 Tables and full-width tables

OINK wraps every Goldmark pipe table in a local scroll region. In interactive
HTML the region is keyboard-focusable, uses the localized accessible name
`ui_table_scroll`, and contains horizontal overflow without widening the page.
The table formatting context fills at least the available prose width, and the
scroll region adds a bottom spacer before following content. The table remains
fully visible when JavaScript is absent because tables have no runtime.

Sites that enable Goldmark block attributes can opt a table out of the prose
measure while keeping the same contained overflow policy:

```markdown
| Feature | Community | Professional |
| --- | --- | --- |
| Support | Forum | Priority |

{.full-width}
```

The `full-width` class is applied to the table and the theme gives its wrapper
the `td-table-scroll--full` modifier. Normal, `wide`, and `full` page widths
therefore share one predictable API. Print removes the scroll viewport and
renders the complete table at page width; Markdown and RSS preserve the table
data without interactive attributes.

### 3.10 Numbered Figure, Table, and Equation

The Book components make a manual, language-aware number and stable target one
semantic unit:

```go-html-template
{{< fig num="2-1" id="office_2003" src="/fig/word.png"
    caption="The Word 2003 interface" alt="Word 2003 with stacked toolbars" />}}

{{< tbl num="9-1" caption="Isolation-level behavior" >}}
| Anomaly | RC | RR | SER |
| --- | --- | --- | --- |
{{< /tbl >}}

{{< eq num="5.3" >}}X \approx \frac{C}{R+Z}{{< /eq >}}
```

The same `eq` name also has a deliberately smaller 0.4 escape-hatch form:

```go-html-template
{{< eq >}}X \approx \frac{C}{R+Z}{{< /eq >}}
```

Without parameters it renders non-empty TeX as display math, registers no
numbered target, and emits a plain `$$` source block in Markdown and RSS.
`id`, `caption`, and `class` require `num`; they cannot create a partially
numbered equation. This lets a site author one isolated formula without first
enabling Goldmark passthrough while keeping Book identities explicit.

The numbered forms of all three components require a quoted `num` matching
`[0-9A-Za-z.-]+`. Their default IDs
are `fig-<num>`, `tbl-<num>`, and `eq-<num>`. An explicit ID matching
`[A-Za-z][A-Za-z0-9_.:-]*` is preserved without a prefix. The Page Store
registry rejects duplicate IDs and two targets of the same kind/number that
claim different IDs. Repeated rendering of the same shortcode owner remains
idempotent.

Captions are plain text. Figure and Table inner content passes through
`.Page.RenderString`; Equation inner content passes directly through the local
server-side KaTeX renderer. Table keeps its Markdown table, label, caption, and
anchor inside one `<figure>`. Equation places its number at the right edge.

Figure additionally accepts the mechanical DDIA migration surface
`src/id/caption/title/class/link/alt/width/height`. `title` aliases `caption`
but cannot appear beside it; `src` and inner content are mutually exclusive;
width and height are positive integers. Class tokens and links use strict
grammars. A missing legacy `alt` falls back to the caption for compatibility;
new authored figures should always supply explicit meaningful alternative
text. `scripts/check-book.py` rejects empty alternatives beside numbered
captions.

HTML and print use `<figure>` and `<figcaption>` with localized Figure/Table/
Equation prefixes and stable IDs. Print removes an interactive table's scroll
wrapper. Markdown and RSS emit `**Figure 2-1.** caption` followed by the
original source body; Equation emits the authored TeX delimiter block. No Book
component loads JavaScript.

### 3.11 Cross references and Book indexes

`xref` provides a current-language internal link and may appear before its
target:

```go-html-template
{{< xref fig="2-1" anchor="office_2003" >}}
{{< xref page="../replication" anchor="sync-mode" >}}synchronous mode{{< /xref >}}
```

Exactly one of `fig`, `tbl`, or `eq` may supply a numbered localized label.
`anchor` overrides the derived target. `page` resolves through Hugo's current
language page lookup. With no kind, `anchor` and non-empty inner link text are
required. Rendering never reads a target registry; post-build validation
checks the target ID, kind, and number so forward references remain legal.

`{{< book-figures >}}` accepts an optional `kind="fig|tbl|eq"` and aggregates
the registered targets in Book reading order. `{{< book-toc depth=1..3 >}}`
uses the same Book tree as the sidebar; depth three includes Hugo fragment
headings and `drafts=false` filters draft rows. In whole-Book print, all of
these links become local document fragments. Markdown ToC is a nested list;
RSS strips Book ToC.

## 4. Output matrix

| Component | HTML | Print | Markdown | RSS | JavaScript disabled | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| Badge | semantic `<span>` or `<a>` | monochrome inline badge | emphasized text or link | static inline HTML | identical content | none |
| Kbd | nested `<kbd>` sequence | visible key boundaries | `Ctrl + K` | static inline HTML | identical content | none |
| Fields | responsive semantic `<dl>` | complete definition list | metadata bullet list | complete static `<dl>` | identical content | none |
| FileTree | nested lists and native `<details>` | fully expanded tree | nested list | fully expanded nested list | native disclosure remains usable | none |
| Shared image | image/figure and caption | image/figure and caption | ordinary image and caption | static figure | identical content | none |
| Image Zoom | shared image plus eligible enhancement | shared image only | shared image only | shared image only | original image remains readable | one opt-in local dialog runtime |
| Gallery | responsive figure grid | sequential figures | sequential images and captions | sequential figures | complete static grid | reuses Image Zoom only |
| Release Assets | linked table with copy controls | linked static table with full hashes | pipe table with full hashes | pipe table with full hashes | complete linked table | one opt-in local copy runtime |
| Table | keyboard-focusable contained scroll region | complete table at page width | source pipe table | static table | complete table remains readable | none |
| Eq escape | display KaTeX/MathML | static display KaTeX/MathML | plain `$$` TeX block | plain `$$` TeX block | identical static formula | none |
| Fig/Tbl/Eq | semantic numbered figure | figure with stable ID | labeled source content | labeled source content | identical numbered content | none |
| Xref/Book index | current-language links and nested lists | document-local links and nested lists | relative links and nested lists | xref only; Book ToC stripped | identical links | none |

## 5. Verification contract

Each implementation issue adds the smallest focused fixture and checker that
proves its contract at Hugo Extended 0.160.1 and 0.164.0.

Theme-level checks cover:

- valid HTML, print, Markdown, and RSS output;
- strict invalid-parameter failures with source positions;
- Page Store/runtime absence on unrelated pages;
- escaping, subpath URLs, repeat rendering, and ID behavior;
- semantic markup, RTL, dark mode, print, reduced motion, forced colors, long
  content, and CJK where relevant;
- Book xref target/kind/number consistency, image alternatives, fragment-tree
  ToC depth, and whole-Book duplicate-ID safety.

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

This document is normative for issues #5 through #10. A deliberate change must
update this document, its contract checker, the affected implementation issue,
and any already-shipped compatibility guidance in the same review. Additive
parameters remain deferred until their behavior is specified across the full
output matrix.
