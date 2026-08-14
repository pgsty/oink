# Enhanced code blocks and code groups

Status: accepted implementation design, adversarially reviewed

Target: OINK theme and `oink.pgsty.com` regression site

Compatibility floor: Hugo Extended 0.160.1

## 1. Decision

OINK should add an enhanced shell around ordinary Chroma code blocks and a
purpose-built `code-group` shortcode. The feature stays server-rendered and
local-first:

- Hugo and Chroma remain the only syntax-highlighting pipeline.
- The server emits the complete, readable code structure and all localized
  labels.
- CSS owns presentation and wrapping.
- JavaScript only enables copy, visual collapse, tab synchronization,
  persistence, and hash navigation.
- Pages without an interactive code block or tab group do not load either code
  runtime.

This is a vertical product feature, not a cosmetic wrapper around the current
copy script. Ordinary fences, legacy `tabpane` code, line-number layouts,
non-HTML outputs, and print must use one normalized rendering contract.

## 2. Problems to solve

The current implementation has six coupled limitations:

1. `render-codeblock.html` only merges Chroma options and calls
   `transform.Highlight`; it has no author-facing shell contract.
2. `click-to-copy.js` discovers code after render, injects controls, hard-codes
   English labels, and does not report clipboard failures correctly.
3. Its `.highlight > pre` selector misses Chroma's table line-number layout.
4. The `tabpane` shortcode calls `highlight` directly, bypassing the code-block
   render hook. Removing the old copy injector without adapting `tabpane` would
   silently remove Copy from existing code tabs.
5. The tab persistence runtime is loaded on every page and has no stable hash
   model.
6. Print currently reveals all tab panels but hides the tab labels, and long
   highlighted blocks are marked `break-inside: avoid-page`.

The implementation must also preserve these established contracts:

- class-based Chroma light and dark palettes;
- `params.highlight_classes`;
- `params.disable_click2copy_chroma`;
- the legacy Prism compatibility path;
- existing `tabpane` parameters, DOM behavior, and `td-tp-persist:*` storage
  keys;
- specialized render hooks for Mermaid, math, chemistry, Markmap, and
  PlantUML;
- Hugo Extended 0.160.1 and 0.164.0 CI coverage;
- all 32 locale files having exactly the same key set.

## 3. Product outcome

After implementation, an unannotated fenced block still works without content
migration, but it gains OINK's standard code surface and localized Copy action.
Authors can opt into a filename, wrapping, or a visual line limit with fence
attributes. Code groups provide stable, shareable tabs without replacing the
general-purpose `tabpane` shortcode.

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

Version one includes:

- an enhanced shell for ordinary fenced code blocks;
- filename or title display;
- localized Copy with `all`, `command`, and disabled modes;
- author-controlled wrapping;
- progressively enhanced long-code collapse;
- a dedicated code-group author API;
- code-group hash activation, in-page synchronization, and optional
  cross-page persistence;
- complete print and Markdown representations;
- compatibility adaptation for legacy `tabpane` code.

Version one does not include:

- Shiki, Twoslash, or runtime syntax highlighting;
- executable playgrounds;
- arbitrary word-level transformers;
- Fumadocs or Nextra magic-comment parsing;
- a generic diff transformer;
- user-facing wrap toggles;
- filenames inside a code-group panel;
- changing the legacy `tabpane` hash or persistence contract.

Use a standard `diff` fence for diffs. Chroma's `.gi` and `.gd` tokens remain
the supported inserted/deleted treatment.

## 5. Author contract: ordinary fences

### 5.1 Recommended syntax

````markdown
```yaml {filename="hugo.yml" copy="all" lineNos="table" hl_lines="4 7-9" wrap=false collapse=18 label="Hugo configuration"}
params:
  offlineSearch: true
```
````

OINK-specific names are lower-case and case-sensitive. Chroma option names keep
Hugo's existing spelling and behavior.

### 5.2 OINK attributes

| Attribute | Accepted values | Default | Contract |
| --- | --- | --- | --- |
| `filename` | non-empty string | none | Visible filename or path. |
| `title` | non-empty string | none | Compatibility alias for `filename`; using both is a build error. |
| `copy` | `all`, `command`, `false`, or `true` | language-dependent | `true` is an alias for `all`. |
| `wrap` | boolean | `false` | Enables source-preserving visual wrapping through CSS. |
| `collapse` | positive integer | none | Maximum source lines initially shown when JavaScript can measure the block. |
| `label` | non-empty string | derived | Accessible name; it is not additional visible chrome. |

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
into `.Options`. After consuming the OINK names, the renderer forwards generic
attributes to the outer `.td-code` element:

- `class` is appended to OINK's classes;
- an author `id` becomes the root ID;
- safe `data-*`, `aria-*`, and other Hugo-sanitized global attributes survive.

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

## 6. Author contract: code groups

### 6.1 Recommended syntax

```go-html-template
{{< code-group id="install-client" sync="package-manager" persist=true label="Choose a package manager" copy="all" >}}
  {{< code-tab title="npm" value="npm" lang="bash" >}}
npm install @example/client
  {{< /code-tab >}}

  {{< code-tab title="pnpm" value="pnpm" lang="bash" >}}
pnpm add @example/client
  {{< /code-tab >}}

  {{< code-tab title="yarn" value="yarn" lang="bash" >}}
yarn add @example/client
  {{< /code-tab >}}
{{< /code-group >}}
```

`code-tab` contains raw code, not Markdown. OINK removes the single framing
newline after the opening shortcode and the newline/indentation before the
closing shortcode; all other source whitespace is preserved.

### 6.2 Group parameters

| Parameter | Required | Default | Contract |
| --- | --- | --- | --- |
| `id` | yes | none | Page-unique stable group ID and hash prefix. |
| `sync` | no | none | Stable key for in-page synchronization and shared persistence. |
| `persist` | no | `true` | Enables localStorage read/write for this group or sync key. |
| `label` | no | localized "Code examples" | Accessible tab-list label. |
| `copy` | no | ordinary default | Default inherited by children. |
| `wrap` | no | `false` | Default inherited by children. |
| `collapse` | no | none | Default inherited by children. |

### 6.3 Child parameters

| Parameter | Required | Default | Contract |
| --- | --- | --- | --- |
| `title` | yes | none | Plain-text visible tab name. |
| `value` | yes | none | Stable machine value used in hashes, sync, and persistence. |
| `lang` | no | `text` | Chroma language. |
| `selected` | no | `false` | Server-selected fallback; at most one child may set it. |
| `copy` | no | inherited | Child override of group Copy behavior. |
| `wrap` | no | inherited | Child override of group wrapping. |
| `collapse` | no | inherited | Child override of group collapse. |

Children may also use the tested Hugo highlighting options from section 5.4.
`filename` and `title`-as-filename are not supported inside a code group because
the tab header already supplies the example identity.

`id`, `sync`, and `value` use lower-case ASCII slugs. Group IDs and sync keys
match `^[a-z][a-z0-9_-]*$`; child values match
`^[a-z0-9][a-z0-9_-]*$`. Duplicate group IDs, duplicate child values, no
children, or multiple selected children are build errors.

Requiring `value` is intentional. Deriving it from a translated title would
make shared URLs and saved preferences change when copy is edited or localized.

### 6.4 Hash and activation model

The public hash is:

```text
#<group-id>-<child-value>
```

For the example above, the pnpm panel is `#install-client-pnpm`. The runtime
resolves the hash by matching a real panel ID, not by splitting on hyphens.

Initial activation priority is:

1. a valid URL hash;
2. a stored value that exists in the group;
3. the single `selected=true` child;
4. the first child.

A hash-selected tab is applied to same-`sync` peers on the current page but is
not written to localStorage. Visiting a shared link must not overwrite the
reader's durable preference.

User tab activation updates the URL with `history.replaceState`, writes the
preference when persistence is enabled, and activates same-value peers that
contain that value. A peer without the value stays unchanged. Using Replace
State keeps the current URL shareable without creating one browser-history
entry per tab click.

`hashchange` and Back/Forward navigation activate a matching panel without
writing persistence. After a hash-driven activation, skip scrolling when the
group is already fully inside the visual viewport. Otherwise call
`scrollIntoView` with `block: 'nearest'` and use smooth behavior only when
`prefers-reduced-motion` is not set.

### 6.5 Persistence namespace

Code groups use a versioned namespace distinct from legacy `tabpane`:

```text
td-code-group:v1:sync:<sync-key>
td-code-group:v1:group:<group-id>
```

The value is the child `value` string. Storage errors are caught and leave tabs
functional. `persist=false` disables both reads and writes but does not disable
in-page `sync`.

Legacy `tabpane` retains its `td-tp-persist:*` keys and timestamp semantics.
The new runtime must not migrate, rewrite, or reinterpret them.

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

### 7.3 Code group

```text
┌──────────────────────────────────────────────────────────┐
│ [ npm ] [ pnpm ] [ yarn ]         BASH   [copy icon]     │
├──────────────────────────────────────────────────────────┤
│ pnpm add @example/client                                 │
└──────────────────────────────────────────────────────────┘
```

The tab row is the group's only header. The active panel's language and Copy
action appear in an action slot at the inline end; individual panels do not
draw a second frame or header. Long tab lists scroll horizontally instead of
wrapping into multiple ambiguous rows.

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

The ordinary render hook, legacy non-text `tabpane` panels, and HTML code-tab
panels all use these layers. Specialized language render hooks remain outside
the pipeline.

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

Markdown-rendering `alert` and text `tabpane` fragments can each restart
Hugo's render-hook ordinal at zero. OINK marks only generated IDs and namespaces
their root, viewport, control references, and default line anchors with the
enclosing alert/tab identity before sibling fragments enter the same DOM.
Explicit author IDs and component-owned IDs are never rewritten.

When `anchorLineNos` is enabled, the renderer supplies a block-unique line
anchor prefix. Code-tab prefixes derive from the stable group and child IDs so
multiple panels cannot emit duplicate line anchors. Ordinary line anchors are
stable across content edits only when the author supplies an explicit fence
`id`; generated ordinal-based IDs may change when blocks are inserted or
reordered, and the author documentation must say so.

### 8.4 Page-store flags and bundles

Use two code flags:

- `hasCodeBlock` records that ordinary or grouped code was rendered.
- `hasCodeRuntime` is set whenever the shared presenter emits an enabled Copy
  or potentially measurable collapse control, regardless of whether the
  caller is an ordinary fence, a legacy `tabpane`, or a code-group child.

`hasTabpane` already exists. Add `hasCodeGroup` for the new shortcode. Set the
code flags inside the shared render/action partials rather than in the ordinary
render hook; a page containing only a legacy code tab must still load Copy.

Append `assets/js/code-block.js` to the normal Hugo asset bundle only for
`hasCodeRuntime`. Append `assets/js/code-tabs.js` only for `hasTabpane` or
`hasCodeGroup`; call this combined boolean `hasTabRuntime`. Extend the existing
`printf ... | md5` bundle-key input in `scripts.html` with both
`hasCodeRuntime` and `hasTabRuntime`, and continue using that hash in the
`js/main-<hash>.js` target path. Hugo must never call `resources.Concat` with
the same target path and different resource arrays.

Gate both runtimes on the normal interactive HTML output name as well as the
Page Store flags. Print, RSS, Markdown, and other static representations never
load `code-block.js` or `code-tabs.js`, even when they contain code.

The render-hook page facade does not expose the current output format on the
supported Hugo versions, so every base layout declares it in
`tdOutputFormat` before content renders. All normal HTML bases must explicitly
reset the value to `html` on every render; otherwise a prior Markdown, print,
or RSS pass can pollute a later `hugo server` incremental rebuild and remove
interactive controls from HTML.

Every HTML base layout must invoke `scripts.html` after its `main` block has
evaluated `.Content`, because render hooks and shortcodes populate Page Store
while content renders. Do not read these flags from `head.html`. Preserve this
ordering in a template-structure test and an output test whose page contains
only a legacy code tab. A consuming site that overrides a base layout inherits
the same ordering requirement.

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

`code-tabs.js` has two adapters over shared Bootstrap Tab helpers:

- the legacy adapter preserves current `data-td-tp-persist` behavior and
  storage keys;
- the code-group adapter implements stable values, hash, synchronization, and
  the new namespace.

Use Bootstrap's `shown.bs.tab` event as the state-change boundary. Listening
only for clicks misses keyboard and programmatic activation. Initialization and
hash-driven changes carry an internal origin flag so they do not write storage
or recursively update the URL.

When a panel is shown, update the code-group action slot and notify the collapse
initializer. Basic tab switching still works through Bootstrap's existing
`data-bs-toggle="tab"` behavior if the OINK synchronization runtime fails.

## 10. Accessibility and security

- Every action is a native `button` with `type="button"` and a visible focus
  indicator.
- Icon-only mobile controls retain localized `aria-label` text.
- Copy status uses a nearby polite live region; failures are never announced as
  success.
- Expand uses `aria-expanded` and `aria-controls`.
- Code-group tab/button/panel relationships use unique `id`, `aria-controls`,
  and `aria-labelledby` values.
- The tablist receives the author label or a localized default.
- Collapsed code remains present in the DOM and accessible to assistive
  technology; collapse is a visual reading aid, not content deletion.
- Attribute values and titles are HTML-escaped. Code-tab titles are plain text.
- No code source is evaluated, reparsed as HTML, sent over the network, or
  duplicated into executable script data.
- Clipboard writes occur only on a user gesture.
- localStorage contains only non-sensitive stable tab values, and all access is
  exception-safe.

## 11. Output formats and degradation

### 11.1 Normal HTML

Server HTML is complete. Ordinary code is fully readable with JavaScript off;
Copy and collapse controls remain hidden. A code group keeps its server-selected
panel and basic Bootstrap switching; hash, synchronization, and persistence are
enhancements.

### 11.2 Print

Print CSS must:

- show every code-group panel;
- hide interactive tab rows, utility controls, fades, and status nodes;
- show a print-only plain-text title before every panel;
- force every viewport to full height and visible overflow;
- wrap long lines to page width;
- override `break-inside: avoid-page` for `.td-code`, its `.highlight`, and
  long `pre` elements so long listings can span pages;
- retain filename and language text when present.

The result is a sequence such as `npm`, its complete code, `pnpm`, its complete
code, and so on.

### 11.3 Markdown

Ordinary fences remain ordinary source fences because OINK's Markdown output
uses `.RenderShortcodes`. `code-group` must explicitly branch on the output
format and emit every child as readable Markdown:

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

The renderer finds every contiguous backtick run with the RE2 pattern
`\x60+`, takes the longest match length (zero when absent), and emits
`max(3, longest + 1)` backticks as both fence delimiters. Interactive classes,
buttons, data attributes, and storage metadata never appear in Markdown
output.

### 11.4 RSS and other non-interactive outputs

RSS emits code-group children as stacked, titled code examples without tabs,
Copy, or collapse. Unknown non-interactive formats prefer complete readable
content over the interactive HTML shell.

Set `tdOutputFormat=rss` before evaluating each item summary. Hugo may return a
summary cached from an earlier HTML render, so a summary containing
`data-td-code` or a page containing a raw `code-group` must be rerendered with
`.RenderShortcodes` and `.RenderString` under the RSS context. Do not pass a
cached server Copy button or live region into the feed.

## 12. Localization

Add these semantic keys:

```text
ui_code_copy
ui_code_copy_label
ui_code_copied
ui_code_copy_error
ui_code_show_all
ui_code_collapse
ui_code_group_label
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

### 13.2 Legacy tabpane

- Existing shortcode syntax remains valid.
- Existing ordinal-based IDs remain.
- `persist=header|lang|disabled`, deprecated `persistLang`, selected, disabled,
  text, right, and language inference remain.
- Existing localStorage names and selection semantics remain.
- Non-text panels move to the shared code renderer so server Copy survives the
  removal of client DOM injection.
- Legacy tabpanes do not gain public code-group hashes.

### 13.3 Prism and specialized blocks

`params.prism_syntax_highlighting=true` remains an unchanged legacy mode and is
not enhanced in version one. The new code-group shortcode is Chroma-only and
must fail with a clear build error under Prism mode.

Language-specific hooks for `mermaid`, `math`, `chem`, `markmap`, and
`plantuml` continue to win Hugo's template lookup and do not receive the code
shell or runtime.

## 14. Implementation plan

Each pull request must be independently shippable; no PR may leave visible dead
buttons or remove Copy from legacy tabs.

### Theme PR C1: normalized renderer and enhanced fence vertical slice

- Add code normalization, highlighting, action, and presentation partials.
- Replace the ordinary render hook with the normalized pipeline.
- Adapt non-text legacy tabpane panels to the same presenter in this PR.
- Add the titled, untitled, wrap, line-number, collapse, and responsive styles.
- Add localized server controls and all locale keys.
- Replace `click-to-copy.js` with conditional `code-block.js`.
- Add page-store flags and include them in the bundle key.
- Update RTL and print rules needed by ordinary blocks.
- Add example-site fixtures and Hugo-version contract assertions.

### Theme PR C2: tab runtime foundation and legacy preservation

- Move legacy persistence into `assets/js/code-tabs.js` without changing its
  storage contract.
- Load tab code only when `hasTabpane` or `hasCodeGroup` is set.
- Use `shown.bs.tab` as the shared event boundary.
- Remove the unconditional `static/js/tabpane-persist.js` path.
- Add regression fixtures for every legacy `tabpane` mode.

### Theme PR C3: code group

- Add `code-group.html` and `code-tab.html` with strict validation.
- Add integrated header/action and embedded-panel presentation modes.
- Implement initial priority, hash, Replace State, hashchange, sync, and the
  versioned storage namespace.
- Add HTML, print, Markdown, RSS, and unknown-format branches.
- Add duplicate-ID/value and invalid-combination build-failure fixtures.

### Site PR C4: documentation and browser acceptance

- Add English and Simplified-Chinese author documentation.
- Add a single regression page covering untitled, titled, console, YAML, diff,
  line numbers, highlighted lines, wrap, collapse, and code groups.
- Add Playwright interaction tests, axe checks, print assertions, and Markdown
  goldens in `oink.pgsty.com`.
- Verify desktop, narrow mobile, light, dark, and RTL examples.

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
- every legacy tabpane mode;
- code-group HTML, print, Markdown, and RSS forms;
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
- Direct code-group hashes activate and scroll to the right panel.
- Sync only changes peers containing the same value.
- A hash visit does not overwrite storage.
- Clicks persist and use Replace State; Back/Forward hash navigation activates
  without persisting.
- The old `td-tp-persist:*` keys still control legacy tabpanes.
- A page without interactive code does not request either code runtime.
- Print and RSS outputs do not request either code runtime.
- Print shows complete ordinary blocks and every titled group panel.
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

- existing fence and `tabpane` source requires no migration;
- Hugo highlighting behavior is preserved for the tested option matrix;
- no visible interactive control is dead when its runtime is unavailable;
- Copy is localized, exact, line-number-free, and reports real failure;
- console defaults to commands while explicit all mode remains available;
- wrapping never silently misaligns a table line-number gutter;
- collapse is visual-only, measured, responsive, and fully removed in print;
- code-group links are stable and shareable;
- hash, persistence, and sync follow the documented priority without feeding
  back into one another;
- legacy tab storage remains compatible;
- every group example survives Markdown, RSS, and print output;
- pages without an applicable feature do not load its runtime;
- all 32 locale files pass parity checks;
- both supported Hugo versions and the consumer browser suite pass.

## 17. References

- [Hugo code-block render hooks](https://gohugo.io/render-hooks/code-blocks/)
- [Hugo Markdown attributes](https://gohugo.io/content-management/markdown-attributes/)
- [Hugo syntax highlighting](https://gohugo.io/content-management/syntax-highlighting/)
- [Hugo `transform.HighlightCodeBlock`](https://gohugo.io/functions/transform/highlightcodeblock/)
- [Nextra syntax highlighting](https://nextra.site/docs/guide/syntax-highlighting)
