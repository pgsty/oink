# Enhanced code blocks and code tabs

Status: accepted implementation design, adversarially reviewed; updated for the
OINK 0.5/0.6 component API v5 (code groups replaced by adjacent-fence tabs and
the `tabs`/`tab` shortcode)

Target: OINK theme and `oink.pgsty.com` regression site

Compatibility floor: Hugo Extended 0.160.1

## 1. Decision

OINK ships an enhanced shell around ordinary Chroma code blocks and one tabs
model shared by code and prose. The feature stays server-rendered and
local-first:

- Hugo and Chroma remain the only syntax-highlighting pipeline.
- The server emits the complete, readable code structure and all localized
  labels.
- CSS owns presentation and wrapping.
- JavaScript only enables copy, visual collapse, tab regrouping and
  switching, synchronization, persistence, and hash navigation.
- Pages without an interactive code block or tab set do not load either
  runtime.

Tabs are not a code-only feature any more: a fence or a table that carries a
`tab` attribute becomes a titled block, adjacent titled blocks of the same
kind become one tab set in the browser, and `{{< tabs >}}`/`{{< tab >}}` hold
Markdown bodies. The former `code-group`/`code-tab` shortcodes and the Docsy
`tabpane`/`tab` shortcodes are removed (component API v5, see
`docs/components.md`).

## 2. Problems to solve

The 0.3 implementation had six coupled limitations, all resolved by the
normalized pipeline described here:

1. `render-codeblock.html` only merged Chroma options and called
   `transform.Highlight`; it had no author-facing shell contract.
2. `click-to-copy.js` discovered code after render, injected controls,
   hard-coded English labels, and did not report clipboard failures correctly.
3. Its `.highlight > pre` selector missed Chroma's table line-number layout.
4. Two tab systems (`tabpane` with lenient parameters, `code-group` with a
   strict schema) coexisted with mixed delimiters and Bootstrap Tab.
5. The tab persistence runtime was loaded on every page and had no stable hash
   model.
6. Print revealed all tab panels but hid the tab labels, and long highlighted
   blocks were marked `break-inside: avoid-page`.

The implementation preserves these established contracts:

- class-based Chroma light and dark palettes;
- `params.highlight_classes`;
- `params.disable_click2copy_chroma`;
- the legacy Prism compatibility path;
- specialized render hooks for Mermaid, math, chemistry, Markmap, PlantUML,
  and the data fences (`echarts`, `infographic`, `checksums`);
- Hugo Extended 0.160.1 and 0.164.0 CI coverage;
- all 32 locale files having exactly the same key set.

## 3. Product outcome

After implementation, an unannotated fenced block still works without content
migration, but it gains OINK's standard code surface and localized Copy action.
Authors can opt into a filename, wrapping, or a visual line limit with fence
attributes. Adjacent fences with a `tab` attribute provide stable, shareable
code tabs without any shortcode; `{{< tabs >}}` provides the same tabs for
Markdown bodies.

The feature is complete only when all of these surfaces agree:

- normal HTML in light and dark themes;
- mobile and RTL layouts;
- browser behavior with and without clipboard permission;
- JavaScript-disabled ordinary code;
- section print output;
- Markdown output;
- RSS or other non-interactive HTML output;
- the minimum and current Hugo versions.

## 4. Scope and non-goals

The contract includes:

- an enhanced shell for ordinary fenced code blocks;
- filename or title display;
- localized Copy with `all`, `command`, and disabled modes;
- author-controlled wrapping;
- progressively enhanced long-code collapse;
- adjacent-fence (and adjacent-table) tabs through the `tab`, `group`, and
  `value` block attributes;
- the `tabs`/`tab` shortcode for Markdown tab bodies;
- hash activation, in-page synchronization, and cross-page persistence for
  grouped tab sets;
- the numbered Book example fence (`num` + `caption`, see
  `docs/prd5-book-contract.md`);
- complete print and Markdown representations.

It does not include:

- Shiki, Twoslash, or runtime syntax highlighting;
- executable playgrounds;
- arbitrary word-level transformers;
- Fumadocs or Nextra magic-comment parsing;
- a generic diff transformer;
- user-facing wrap toggles;
- Bootstrap Tab, the `tabpane`/`tab` (Docsy) and `code-group`/`code-tab`
  shortcodes, and their `td-tp-persist:*` / `td-code-group:v1:*` storage keys —
  all removed; `scripts/migrations/oink06.py` rewrites existing content.

Use a standard `diff` fence for diffs. Chroma's `.gi` and `.gd` tokens remain
the supported inserted/deleted treatment.

## 5. Author contract: ordinary fences

### 5.1 Recommended syntax

````markdown
```yaml {title="hugo.yml" copy="all" lineNos="table" hl_lines="4 7-9" wrap=false collapse=18 label="Hugo configuration"}
params:
  offlineSearch: true
```

```bash {tab="Homebrew" group="install" value="brew"}
brew install pigsty
```
```bash {tab="APT" value="apt"}
sudo apt install pigsty
```
````

OINK-specific names are lower-case and case-sensitive. Chroma option names keep
Hugo's existing spelling and behavior.

### 5.2 OINK attributes

| Attribute | Accepted values | Default | Contract |
| --- | --- | --- | --- |
| `title` | non-empty string | none | Visible filename or path in the block header. |
| `filename` | non-empty string | none | Historical alias for `title`; using both is a build error (content migrates to `title`). |
| `copy` | `all`, `command`, `false`, or `true` | language-dependent | `true` is an alias for `all`. |
| `wrap` | boolean | `false` | Enables source-preserving visual wrapping through CSS. |
| `collapse` | positive integer | none | Maximum source lines initially shown when JavaScript can measure the block. |
| `label` | non-empty string | derived | Accessible name; it is not additional visible chrome. |
| `id` | non-empty token | generated | Public stable root ID (or the Book example figure ID when `num` is present). |
| `tab` | non-empty string | none | Tab label; adjacent fences with `tab` become one tab set (section 6). Coexists with `title`. |
| `group` | `^[a-z][a-z0-9_-]*$` | none | Opt-in hash / sync / persistence for the run that starts with this fence; requires `tab`. |
| `value` | `^[a-z0-9][a-z0-9_-]*$` | none | Stable machine value; required on every fence of a grouped run, forbidden without a group; requires `tab`. |
| `num` | `[0-9A-Za-z.-]+` | none | Numbered Book example (`eg`); requires `caption`; mutually exclusive with `tab`. |
| `caption` | non-empty plain text | none | Book example caption; requires `num`. |

Invalid values fail the Hugo build with `errorf` including `.Position`. Silent
coercion is limited to quoted boolean values and `copy=true`.

### 5.3 Copy defaults

The default is deterministic:

1. If `params.disable_click2copy_chroma=true`, Copy is globally disabled,
   including explicit per-block values.
2. For the tested Chroma session lexers `console` and `shell-session`, omitted
   `copy` means `command`.
3. For every other language, omitted `copy` means `all`.

`copy=command` is only valid for the tested session-lexer allow-list. Using it
with a plain `bash`, `sh`, or other block is a build error because those lexers
cannot distinguish prompts, commands, and output.

`copy=all` on a console block deliberately includes prompts and output.

### 5.4 Hugo highlighting options

All values already classified by Hugo as highlighting options continue to the
highlighter. The regression matrix explicitly covers:

- `lineNos` (`false`, `inline`, and `table`);
- `lineNoStart`;
- `hl_lines`;
- `anchorLineNos`;
- `tabWidth`.

`style` is passed through for compatibility, but OINK must not promise a
per-block palette while `params.highlight_classes=true`: class-based Chroma
uses the theme's compiled light/dark palettes. A `style` value is meaningful
only in Hugo's inline-style mode.

`wrapperClass` is internal to the OINK shell and is not a public per-fence
option. All other existing options preserve Hugo's behavior.

`wrap=true` is incompatible with effective table line numbers because the
gutter and code live in separate table cells and wrapped visual rows cannot
stay aligned. The render-hook page facade does not expose the full site Markup
configuration on the supported Hugo versions, so configuration inference is
not reliable. Validate the actual Chroma result instead: after highlighting,
if wrapping is enabled and the output contains an `.lntable`, fail the build
with guidance to use `lineNos=inline` or disable wrapping. The Hugo-version
fixture must cover both explicit table mode and a site-default table layout
with per-block `wrap=true` and no per-block `lineNos`.

Wrapping and collapse may be combined. Collapse measures the bottom of the
Nth Chroma source-line node, so a wrapped source line is never cut in half.

### 5.5 Generic attributes

Hugo separates generic attributes into `.Attributes` and highlighting options
into `.Options`. After consuming the OINK names (`title`, `filename`, `copy`,
`wrap`, `collapse`, `label`, `id`, `class`, `role`, `tab`, `group`, `value`,
`num`, `caption`), the renderer forwards generic attributes to the outer
`.td-code` element:

- `class` is appended to OINK's classes;
- an author `id` becomes the root ID;
- `data-*` and `aria-*` attributes survive (same policy as the other render
  hooks, `content/attributes.html`);
- any other key — including `style`, `on*`, `srcdoc`, and typos of OINK names —
  is a build error that lists the allowed names.

Root IDs must be unique within a page and must not collide with another code
component's generated viewport, tab, panel, title, or line-anchor IDs. Such a
collision is a build error because Copy targets, ARIA relationships, and line
anchors depend on a valid page-wide component namespace. Explicit IDs must not
contain ASCII whitespace or control characters because ARIA ID references are
space-separated tokens.
Names beginning with `data-td-code`, plus `data-language`, `data-line-count`,
and `data-collapse-lines`, are reserved and cause a build error. `label` or a
visible filename and a generic `aria-label` are mutually exclusive; use
`label` to override the filename-derived accessible name. Generated accessible
names also reject a conflicting generic `aria-labelledby`.
The implementation must escape attribute values and must not introduce a new
raw-HTML parser.

## 6. Author contract: tabs

### 6.1 Adjacent fences and tables

````markdown
```bash {tab="npm" group="package-manager" value="npm"}
npm install @example/client
```

```bash {tab="pnpm" value="pnpm"}
pnpm add @example/client
```
````

Every block renders on its own as a titled block:

```html
<div class="td-tab-block td-tab-block--code" data-td-tab="npm"
     data-td-tab-group="package-manager" data-td-tab-value="npm" data-td-tab-kind="code">
  <div class="td-tab-block__title" data-td-tab-title>npm</div>
  <div class="td-code …">…</div>
</div>
```

The runtime (`assets/js/tabs.js`) regroups every run of two or more adjacent
sibling `.td-tab-block` elements of the same `data-td-tab-kind` (`code` for
fences, `table` for pipe tables carrying `{tab=…}`) into one tab set. A single
titled block stays a titled block. Only whitespace and comments may separate
the blocks; a paragraph between two fences ends the run. Embedded code blocks
receive `td-code--embedded` and drop their own frame inside the tabs frame.

Rules:

- `tab` is the visible label and the block's title when it stands alone.
- `group` on the first block of a run opts the run into hash, sync, and
  persistence; then every block of the run needs a `value`. A grouped run
  missing a value on some block, or a run with duplicate values, is left as
  titled blocks with a console warning; `value` without any group is a build
  error, as is `group`/`value` without `tab`.
- `title` may accompany `tab`: the label goes to the tablist and the filename
  header stays inside the panel.
- `num` (Book example) and `tab` are mutually exclusive.

### 6.2 The `tabs`/`tab` shortcode

```go-html-template
{{< tabs group="package-manager" default="pnpm" label="Choose a package manager" >}}
{{< tab label="npm" value="npm" >}}
Markdown body, including fences, tables, and callouts.
{{< /tab >}}
{{< tab label="pnpm" value="pnpm" >}}
Markdown body.
{{< /tab >}}
{{< /tabs >}}
```

| Parameter | Shortcode | Required | Contract |
| --- | --- | --- | --- |
| `group` | `tabs` | no | `^[a-z][a-z0-9_-]*$`; enables hash, sync, and persistence for the set. |
| `default` | `tabs` | no | A child `value`; requires `group`. |
| `label` | `tabs` | no | Accessible tablist name; default `ui_tabs_label`. |
| `label` | `tab` | yes | Plain-text visible tab name. |
| `value` | `tab` | with a group | `^[a-z0-9][a-z0-9_-]*$`; required when the set has a group, forbidden otherwise (ungrouped children get generated `tab<n>` values). |

Duplicate values, a `tabs` without `tab` children, and content between the
children fail the build. Bodies are Markdown rendered through
`content/render-block.html`, so nested code blocks get scoped IDs and Copy.
Both delimiters use standard `{{< >}}` notation.

### 6.3 Shared DOM

```html
<div class="td-tabs" data-td-tabs data-td-tabs-group="package-manager" data-td-tabs-default="pnpm">
  <div class="td-tabs__list" role="tablist" aria-label="Choose a package manager">
    <button class="td-tabs__tab" type="button" role="tab" id="package-manager-npm-tab"
            aria-controls="package-manager-npm" aria-selected="false" tabindex="-1"
            data-td-tabs-value="npm">npm</button>
    …
  </div>
  <section class="td-tabs__panel" id="package-manager-npm" role="tabpanel"
           aria-labelledby="package-manager-npm-tab" tabindex="0" data-td-tabs-value="npm">
    <div class="td-tabs__panel-title" aria-hidden="true">npm</div>
    <div class="td-tabs__panel-body">…</div>
  </section>
</div>
```

Panel IDs are `<group>-<value>` in a grouped set and generated
(`td-tabs-<hash8>-<ordinal>-<value>` for the shortcode,
`td-tabs-run-<n>-<hash>-<value>` for a regrouped run) otherwise. Nothing is
hidden in server HTML: until the runtime marks the set with
`data-td-tabs-ready`, CSS hides the tablist and shows every panel under its
`.td-tabs__panel-title`; afterwards inactive panels get `hidden` and the titles
disappear.

### 6.4 Hash and activation model

The public hash of a grouped set is:

```text
#<group>-<value>
```

For the example above, the pnpm panel is `#package-manager-pnpm`. The runtime
resolves the hash by matching a real panel ID, not by splitting on hyphens.

Initial activation priority for a grouped set is:

1. a valid URL hash naming a panel of the set;
2. a stored value that exists in the set;
3. the shortcode `default` (or the first block of a run);
4. the first tab.

A hash-selected tab is applied to same-group peers on the current page but is
not written to localStorage. Visiting a shared link must not overwrite the
reader's durable preference. After a hash-driven activation the set is
scrolled into view with `block: 'nearest'`, smoothly unless
`prefers-reduced-motion` is set.

User activation (click, Left/Right, Home/End) updates the URL with
`history.replaceState`, writes the preference, and activates every other set
of the same group that contains that value. A peer without the value stays
unchanged. Ungrouped sets switch locally and never touch the URL or storage.
`hashchange` activates a matching panel without writing persistence.

### 6.5 Persistence namespace

```text
td-tabs:v1:<group>
```

The value is the tab `value` string. Storage errors are caught and leave tabs
functional. The historical `td-tp-persist:*` and `td-code-group:v1:*` keys are
no longer read or written.

## 7. Presentation design

OINK has three related surfaces, all using the same canvas, border, radius,
font, focus, and light/dark tokens.

### 7.1 Titled block

```text
┌──────────────────────────────────────────────────────────┐
│ hugo.yml                    YAML        [copy icon]      │
├──────────────────────────────────────────────────────────┤
│ params:                                                  │
│   offlineSearch: true                                    │
└──────────────────────────────────────────────────────────┘
```

The filename is left-aligned and truncates visually on narrow screens without
changing its accessible text. Language and actions occupy the inline end. The
header exists only when `filename` or `title` is present.

### 7.2 Untitled block

```text
┌──────────────────────────────────────────────────────────┐
│ params:                              YAML    [copy icon]  │
│   offlineSearch: true                                    │
└──────────────────────────────────────────────────────────┘
```

There is no empty full-width title bar. A compact utility cluster sits at the
upper inline end and the viewport reserves enough top/inline padding to prevent
overlap with code. On narrow screens the language text may hide, while the
localized icon button and accessible label remain.

### 7.3 Tab set

```text
┌──────────────────────────────────────────────────────────┐
│ [ npm ] [ pnpm ] [ yarn ]                                │
├──────────────────────────────────────────────────────────┤
│ pnpm add @example/client                  BASH [copy]    │
└──────────────────────────────────────────────────────────┘
```

The tab row is the set's only header. An embedded code panel keeps its own
compact utility cluster (language label and Copy) inside the panel and drops
its frame; prose panels get the standard panel padding. Long tab lists scroll
horizontally instead of wrapping into multiple ambiguous rows. Before the
runtime runs, the same set renders as stacked titled blocks with one visible
title per panel.

Copy is always an icon-only visual action. Its localized name remains available
through `aria-label`, `title`, the live status region, and the success/error
icon state; translated prose does not consume header width.

### 7.4 Collapse treatment

A collapsed viewport ends with a subtle canvas-colored fade. A full-width
footer button reads `Show all N lines`; expanded state reads `Collapse code`.
The control is outside the clipped viewport, uses `aria-expanded` and
`aria-controls`, and stays keyboard focused when the height changes.

`prefers-reduced-motion: reduce` disables height animation. Print never shows
the fade or controls.

### 7.5 Styling constraints

- Reuse `--td-pre-bg`, `--td-code-font-family`, Bootstrap surface, border,
  radius, focus, and text tokens.
- Keep code content LTR with `unicode-bidi: plaintext`; place outer controls
  with logical properties so RTL pages remain correct.
- Put the border and radius on the OINK root, not on each nested Chroma `pre`.
- Preserve horizontal scrolling in non-wrap mode.
- Preserve Chroma `.highlight`, `.chroma`, `.lntable`, `.ln`, `.lnt`, `.hl`,
  `.gi`, and `.gd` semantics.
- Pair the Friendly light palette with GitHub Dark. Because generated palettes
  omit roles that equal their default color, the dark layer explicitly resets
  every token defined only by the light palette. Never carry a light error
  token background into dark mode; `.err` uses text color only.
- Show highlighted lines with a quiet surface wash and leading accent, not a
  four-sided border that resembles an input control.
- Do not use color alone to communicate Copy success or expanded state.

## 8. Server rendering architecture

### 8.1 One normalized pipeline

Create three internal layers:

1. `code/normalize.html` parses defaults, validates values, separates OINK
   attributes from Chroma options, counts source lines, and returns a map.
2. The caller invokes the existing `transform.Highlight` path with normalized
   source, language, and options.
3. `code/render.html` emits the common shell around the highlighted HTML;
   `code/actions.html` emits reusable localized controls.

The ordinary render hook and `{{< include code=true >}}` use these layers;
tab bodies and Book example bodies reach them through Markdown rendering.
Specialized language render hooks (Mermaid, math, chemistry, Markmap,
PlantUML, `echarts`, `infographic`, `checksums`) remain outside the pipeline.

Continue using `transform.Highlight` for this release. Although newer Hugo
versions offer richer `transform.HighlightCodeBlock` results, changing the
highlighter API and the UI contract in one step would unnecessarily widen the
0.160.1/0.164.0 compatibility matrix.

### 8.2 Stable ordinary-block DOM

The semantic contract is:

```html
<div class="td-code" id="td-code-..." data-td-code data-language="yaml"
     data-line-count="42">
  <div class="td-code__header">
    <span class="td-code__filename" id="td-code-...-title">hugo.yml</span>
    <div class="td-code__utilities">
      <span class="td-code__language">YAML</span>
      <button type="button" hidden data-td-code-copy>...</button>
    </div>
  </div>
  <div class="td-code__viewport" id="td-code-...-viewport"
       data-td-code-viewport>
    <!-- transform.Highlight output, including .highlight and .chroma -->
  </div>
  <button type="button" hidden data-td-code-expand
          aria-controls="td-code-...-viewport">Show all 42 lines</button>
  <span class="visually-hidden" role="status" aria-live="polite"
        data-td-code-status></span>
</div>
```

The header is omitted for an untitled block; the same utility partial is then
placed as an overlay within the root. Elements that do not apply are omitted,
not emitted empty. In particular, the live status region exists only when Copy
is enabled; static outputs and `copy=false` blocks do not carry inert
interactive semantics.

All interactive controls carry `hidden` in server HTML. `code-block.js` only
reveals a Copy control after finding a valid source, and only reveals an expand
control after successfully measuring a genuinely collapsible block. With
JavaScript unavailable, code is complete and no dead buttons are visible.

### 8.3 IDs and line anchors

An author `id` is public and stable. Otherwise the renderer generates a
page-scoped ID from the page and block ordinal; generated IDs are implementation
details and are not documented as permalinks.

Bodies rendered through `.Page.RenderString` (tab bodies, card and field
descriptions, `include`, Book figure/table/example bodies) restart Hugo's
render-hook ordinal at zero. `content/render-block.html` therefore runs every
such body inside a named scope stored in `tdRenderScope`; the generated root ID
becomes `td-code-<page>-<scope>-fence-<n>` so sibling fragments never collide
in one DOM. Explicit author IDs are never rewritten. A fence that carries `num`
uses its author `id` for the Book `<figure>` and keeps a generated code root ID.

When `anchorLineNos` is enabled, the renderer supplies a block-unique line
anchor prefix. Ordinary line anchors are stable across content edits only when
the author supplies an explicit fence `id`; generated ordinal-based IDs may
change when blocks are inserted or reordered, and the author documentation
must say so.

### 8.4 Page-store flags and bundles

Use three flags:

- `hasCodeBlock` records that code was rendered.
- `hasCodeRuntime` is set whenever the shared presenter emits an enabled Copy
  or potentially measurable collapse control, regardless of the caller.
- `hasTabs` is set by `content/tab-block.html` (a block with `tab`) and by the
  `tabs` shortcode, in interactive HTML only.

Append `assets/js/code-block.js` to the normal Hugo asset bundle only for
`hasCodeRuntime` and `assets/js/tabs.js` only for `hasTabs`. Both booleans are
part of the `printf ... | md5` bundle-key input in `scripts.html`, and that
hash is used in the `js/main-<hash>.js` target path. Hugo must never call
`resources.Concat` with the same target path and different resource arrays.

Gate both runtimes on the normal interactive HTML output name as well as the
Page Store flags. Print, RSS, Markdown, and other static representations never
load `code-block.js` or `tabs.js`, even when they contain code or tabs.

The render-hook page facade does not expose the current output format on the
supported Hugo versions, so every base layout declares it in
`tdOutputFormat` before content renders. All normal HTML bases must explicitly
reset the value to `html` on every render; otherwise a prior Markdown, print,
or RSS pass can pollute a later `hugo server` incremental rebuild and remove
interactive controls from HTML.

Every HTML base layout must invoke `scripts.html` after its `main` block has
evaluated `.Content`, because render hooks and shortcodes populate Page Store
while content renders. Do not read these flags from `head.html`. A consuming
site that overrides a base layout inherits the same ordering requirement.

Do not emit a second stand-alone Copy script tag. Localized strings live in
server-rendered text and data attributes, so the static JS bundle is identical
across languages.

## 9. Client behavior

### 9.1 Copy state machine

Use one delegated click listener for `[data-td-code-copy]`.

1. Resolve the target `.td-code` and its actual language-bearing `<code>` node.
   In table line-number mode, ignore the gutter code node.
2. Clone the code node so the rendered document is never mutated.
3. Remove `.ln` and `.lnt` nodes so inline or table line numbers are never
   copied.
4. For `all`, read the clone's `textContent`.
5. For `command`, retain source lines containing Chroma `.gp`, remove `.gp` and
   `.go`, and remove the single separator space after each prompt. If a tested
   lexer produces no prompt tokens, copy nothing, announce
   `ui_code_copy_error`, and log a diagnostic. Never silently fall back to
   `all`, which could copy prompts or sensitive command output against the
   author's stated mode. Multi-line commands must include the session lexer's
   continuation prompt (for example, `>`); an unprompted line is
   indistinguishable from command output and is therefore excluded.
6. Preserve leading indentation and internal blank lines, remove only trailing
   newline characters, and append exactly one final newline.
7. Try `navigator.clipboard.writeText`. If unavailable or rejected, use a
   short-lived off-screen textarea and `document.execCommand('copy')` fallback.
8. Announce localized success or failure in the block's live region. Reflect
   the same state in the icon plus accessible label/title for approximately
   1.5 seconds, then reset.

Do not use computed `user-select` as the data model. Explicit Chroma token
classes are deterministic and testable.

### 9.2 Wrap behavior

Wrap is server-selected CSS, not JavaScript. `.td-code--wrap` applies
`white-space: pre-wrap` and `overflow-wrap: anywhere` to the code canvas while
preserving source and copy text. Non-wrap mode keeps horizontal scrolling.

### 9.3 Collapse state machine

The server provides `data-line-count` and `data-collapse-lines`; it does not
set a clipping height.

On initialization or when a hidden tab panel becomes visible:

1. If total lines are not greater than the requested limit, leave the full
   block and keep the control hidden.
2. Find the Nth source `.line` in the actual code column and measure its bottom
   relative to the viewport.
3. If no reliable line node or non-zero measurement exists, leave the full
   block and keep the control hidden.
4. Store the measured pixel height in `--td-code-collapsed-height`, add
   `is-collapsed`, set `aria-expanded=false`, and reveal the control.
5. Recalculate when the visible viewport width changes and after document
   fonts are ready. A `ResizeObserver` tracks width only to avoid feedback
   loops from the height transition.

Expanding removes the clipping height after the transition. Collapsing measures
from the current full height back to the saved limit. If the URL targets a line
inside a collapsed block, expand that block before scrolling to the target.

### 9.4 Tab runtime

`tabs.js` has no Bootstrap dependency and exports `OinkTabs` (also
`module.exports` for `tests/js/tabs.test.js`). On start it (1) regroups
adjacent `.td-tab-block` runs into `.td-tabs` sets, (2) enhances every
`.td-tabs[data-td-tabs]` set — click and keyboard listeners on the tablist,
initial activation by hash → storage → default, `data-td-tabs-ready` — and
(3) applies the current hash, listening for `hashchange`. Activation sets
`aria-selected`/`tabindex` on tabs and `hidden`/`data-td-tabs-active` on
panels; a set that lacks the requested value is left untouched so a peer sync
can never leave a set with no selected tab. Origins (`click`, `keyboard`,
`hash`, `sync`) decide whether storage and the URL are written.

## 10. Accessibility and security

- Every action is a native `button` with `type="button"` and a visible focus
  indicator.
- Icon-only mobile controls retain localized `aria-label` text.
- Copy status uses a nearby polite live region; failures are never announced as
  success.
- Expand uses `aria-expanded` and `aria-controls`.
- Tab/button/panel relationships use unique `id`, `aria-controls`, and
  `aria-labelledby` values; tabs form a roving-tabindex group with Left/Right
  (RTL aware) and Home/End activation, and focus stays on the tab.
- The tablist receives the author label or the localized `ui_tabs_label`
  default.
- Collapsed code remains present in the DOM and accessible to assistive
  technology; collapse is a visual reading aid, not content deletion.
- Attribute values and titles are HTML-escaped. Tab labels are plain text.
- No code source is evaluated, reparsed as HTML, sent over the network, or
  duplicated into executable script data.
- Clipboard writes occur only on a user gesture.
- localStorage contains only non-sensitive stable tab values, and all access is
  exception-safe.

## 11. Output formats and degradation

### 11.1 Normal HTML

Server HTML is complete. Ordinary code is fully readable with JavaScript off;
Copy and collapse controls remain hidden. Tab sets keep every panel visible
under its own title until the runtime enhances them; hash, synchronization,
and persistence are enhancements.

### 11.2 Print

The print output format renders adjacent tabbed blocks as consecutive titled
blocks and the `tabs` shortcode as titled static sections without ARIA roles.
Print CSS must additionally:

- hide tab rows, utility controls, fades, and status nodes;
- force every viewport to full height and visible overflow;
- wrap long lines to page width;
- override `break-inside: avoid-page` for `.td-code`, its `.highlight`, and
  long `pre` elements so long listings can span pages;
- retain filename and language text when present.

The result is a sequence such as `npm`, its complete code, `pnpm`, its complete
code, and so on.

### 11.3 Markdown

Ordinary fences — including fences that carry `tab`, `group`, `value`, `num`,
or `caption` — remain ordinary source fences because OINK's Markdown output
uses `.RenderShortcodes` and render hooks do not run there. The `tabs`
shortcode branches on the output format and emits every child as a bold label
followed by its body:

````markdown
**npm**

```bash
npm install @example/client
```

**pnpm**

```bash
pnpm add @example/client
```
````

Interactive classes, buttons, data attributes, and storage metadata never
appear in Markdown output.

### 11.4 RSS and other non-interactive outputs

RSS emits tab sets as stacked, titled sections without tabs, Copy, or
collapse. Unknown non-interactive formats prefer complete readable content over
the interactive HTML shell.

Set `tdOutputFormat=rss` before evaluating each item summary. Hugo may return a
summary cached from an earlier HTML render, so a summary containing
`data-td-code` or `data-td-tabs` must be rerendered with `.RenderShortcodes`
and `.RenderString` under the RSS context. Do not pass a cached server Copy
button or live region into the feed.

## 12. Localization

Add these semantic keys:

```text
ui_code_copy
ui_code_copy_label
ui_code_copied
ui_code_copy_error
ui_code_show_all
ui_code_collapse
ui_tabs_label
```

`ui_code_show_all` receives the total source-line count. English, Simplified
Chinese (`zh-cn` and `zh`), and Traditional Chinese receive reviewed text.
Every other bundled locale receives an explicit English fallback through the
existing i18n synchronization workflow, and `scripts/check-i18n.py` must report
exact parity across all 32 files.

Language identifiers such as `YAML`, `BASH`, and `SQL` are technical labels,
not localized prose. Display the token in upper case, with the common
`bash`/`sh`/`shell` lexer aliases presented consistently as `BASH`; this changes
only the UI label, not the language passed to Chroma or stored in
`data-language`. Omit the visual label when the token is empty.

## 13. Compatibility decisions

### 13.1 Existing fences

No Markdown migration is required. Highlighted content, language classes, and
supported Chroma options remain. The new `.td-code` parent deliberately changes
the HTML tree, but the nested `.highlight` and `.chroma` classes remain for
reasonable site overrides. Byte-for-byte HTML compatibility is not an
acceptance criterion; semantic and visual compatibility is.

Document the DOM change for sites with direct-child selectors such as
`.td-content > .highlight`.

### 13.2 Removed tab shortcodes

`tabpane`/`tab` (Docsy) and `code-group`/`code-tab` are removed together with
their Bootstrap Tab runtime, `td-tp-persist:*` and `td-code-group:v1:*`
storage, `persist=header|lang|disabled`, `text`, `right`, `disabled`, and
`selected`. `scripts/migrations/oink06.py migrate --only tabs` rewrites
existing content: tab panes that contain exactly one fence each become
adjacent fences with `{tab= group= value=}` (the group is derived from the
header set unless `persist=disabled`), every other pane becomes
`{{< tabs >}}`/`{{< tab >}}`, and code groups keep their `sync` key as the
group and their child values.

### 13.3 Prism and specialized blocks

`params.prism_syntax_highlighting=true` remains an unchanged legacy mode and is
not enhanced; tab attributes are Chroma-only.

Language-specific hooks for `mermaid`, `math`, `chem`, `markmap`, `plantuml`,
`echarts`, `infographic`, and `checksums` continue to win Hugo's template
lookup and do not receive the code shell or runtime.

## 14. Implementation history

- Theme PR C1 (0.3): normalized renderer, enhanced fence shell, localized
  controls, `code-block.js`, page-store flags.
- Theme PR C2/C3 (0.3): Bootstrap-based tab runtime and the `code-group`
  shortcode.
- OINK 0.5/0.6 (component API v5): `code-group`, `code-tab`, `tabpane`, and
  `tab` (Docsy) removed; `tab`/`group`/`value` fence and table attributes,
  `content/tab-block.html`, the `tabs`/`tab` shortcode, `assets/js/tabs.js`,
  the `hasTabs` flag, `content/render-block.html` ID scoping, and the `num`/
  `caption` Book example fence added; content migrated with
  `scripts/migrations/oink06.py`.

## 15. Verification matrix

### 15.1 Theme build tests

Run under Hugo Extended 0.160.1 and 0.164.0:

- unannotated fence;
- filename and title alias;
- generic root ID/class/data attributes;
- every Copy mode and global Copy disable;
- console, shell-session, bash, YAML, text, and diff;
- no line numbers, inline line numbers, table line numbers, non-one start;
- highlighted lines and anchored line numbers;
- wrap, collapse, and wrap plus collapse;
- invalid booleans, invalid enum, invalid collapse, duplicate attributes, and
  wrap plus table line-number failure;
- the same wrap failure when table line numbers come only from site Highlight
  configuration and the fence omits `lineNos`;
- legacy Prism build;
- adjacent-fence tabs (grouped and local), `tab` + `title`, tab attributes on
  tables, invalid `group`/`value`/`num` combinations;
- `tabs`/`tab` shortcode HTML, print, Markdown, and RSS forms;
- scoped code IDs inside tabs, cards, fields, and Book examples;
- i18n key parity.

Do not add Node.js as a theme build dependency. Theme-side assertions should
inspect generated HTML and build failures with the existing Hugo/Python CI
toolchain.

### 15.2 Browser tests in the consumer site

- Copy preserves indentation, blank lines, Unicode, and exactly one final
  newline.
- Inline/table line numbers are not copied.
- Console command mode excludes prompt and output; all mode includes them.
- A forced session-lexer fixture with no `.gp` token copies nothing and reports
  localized failure instead of silently switching to all mode.
- Clipboard rejection takes the fallback or reports localized failure.
- Copy buttons are keyboard reachable and status is announced.
- Collapse is absent below the threshold, measures wrapped lines, expands,
  collapses, and responds to width changes.
- Reduced-motion mode has no height animation.
- A line-anchor hash expands its containing block.
- Author documentation distinguishes stable explicit-ID line anchors from
  generated ordinal anchors.
- Direct `#<group>-<value>` hashes activate and scroll to the right set.
- Sync only changes peers containing the same value.
- A hash visit does not overwrite storage.
- Clicks persist and use Replace State; Back/Forward hash navigation activates
  without persisting.
- A page without interactive code or tabs does not request either runtime.
- Print and RSS outputs do not request either runtime.
- Print shows complete ordinary blocks and every titled panel.
- Markdown goldens contain all examples and no interactive HTML.
- Axe reports no new violations in normal and grouped examples.

### 15.3 Manual visual review

Review at least:

- desktop and 375 px widths;
- light and dark palettes;
- a long filename;
- a long unbroken source line;
- 50+ tabs or a realistically overflowing tab row;
- English, Simplified Chinese, and an RTL locale;
- inline and table line-number gutters;
- a multi-page printed long listing.

## 16. Acceptance criteria

The feature is ready when:

- existing fence source requires no migration; removed tab shortcodes are
  rewritten by the migration toolkit;
- Hugo highlighting behavior is preserved for the tested option matrix;
- no visible interactive control is dead when its runtime is unavailable;
- Copy is localized, exact, line-number-free, and reports real failure;
- console defaults to commands while explicit all mode remains available;
- wrapping never silently misaligns a table line-number gutter;
- collapse is visual-only, measured, responsive, and fully removed in print;
- grouped tab links are stable and shareable;
- hash, persistence, and sync follow the documented priority without feeding
  back into one another;
- every tab example survives Markdown, RSS, and print output;
- pages without an applicable feature do not load its runtime;
- all 32 locale files pass parity checks;
- both supported Hugo versions and the consumer browser suite pass.

## 17. References

- [Hugo code-block render hooks](https://gohugo.io/render-hooks/code-blocks/)
- [Hugo Markdown attributes](https://gohugo.io/content-management/markdown-attributes/)
- [Hugo syntax highlighting](https://gohugo.io/content-management/syntax-highlighting/)
- [Hugo `transform.HighlightCodeBlock`](https://gohugo.io/functions/transform/highlightcodeblock/)
- [Nextra syntax highlighting](https://nextra.site/docs/guide/syntax-highlighting)
