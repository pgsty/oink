# OINK components (API v5 authoring guide)

Status: normative summary of the OINK 0.5/0.6 component API; the frozen
contracts are `docs/content-primitives.md` (everyday components, contract v2),
`docs/enhanced-code-blocks.md` (fences and tabs), and
`docs/book-contract.md` (Book pack, contract v2). Design record:
`plan/design/components.md` v5.

Compatibility floor: Hugo Extended 0.160.1

## 1. Principle

Hugo has no parser extension point, so authors have exactly four channels:
shortcodes, render hooks (blockquote, code block, heading, image, link,
passthrough, table), Goldmark block attributes (`{...}` on the line after a
list, table, blockquote, standalone image, or `$$` block; on the same line
for headings and fences), and front matter/data. OINK components use them
this way:

- **Native form** = one ordinary Markdown block plus a marker (`{.steps}`) or
  an attribute line (`{tab="npm"}`, `{#fig_x num="2-1" caption="…"}`). Lists
  are styled by CSS alone; tables, images, math blocks, fences, and blockquotes
  are transformed by render hooks. The source reads the same on GitHub, in any
  Markdown reader, and in OINK's own Markdown output ("three-place
  equivalence"); the worst artifact elsewhere is one visible `{.steps}` line.
- **Full form** = a shortcode, kept only where a native block cannot express
  the content (compound bodies, arbitrary Markdown containers, processed
  images, special parameters). Every component has at most two forms and every
  shortcode uses one delimiter.
- **Delimiters**: `{{% steps %}}` is the only `{{% %}}` shortcode — its body
  is top-level page Markdown, so headings inside enter the table of contents.
  Every other shortcode is `{{< >}}`; containers (`tabs`/`tab`, `cards`/`card`,
  `fields`/`field`, `image`, `eg`, `tbl`, `fig`, `include`) render their
  Markdown bodies with `RenderString` inside a scoped `content/render-block.html`
  call. (A `%` shortcode nested in another shortcode receives already-rendered
  HTML on Hugo 0.160–0.164, so `%` collectors cannot exist; a `%` block inside a
  list item truncates the list. Both facts are verified and drive this rule.)
- Data fences (`mermaid`, `plantuml`, `markmap`, `math`, `chem`, `echarts`,
  `infographic`, `checksums`, `filetree`, `gallery`) are native because the fenced source
  *is* the content.
- Authors do not control presentation: no `class`, `style`, color, or `cols`
  parameters; icons are exactly one Font Awesome class pair; site CSS may still
  attach classes through block attributes (they pass through).

Site prerequisites: `markup.goldmark.renderer.unsafe: true`,
`markup.goldmark.parser.attribute.block: true`, and — for the block image
forms — `markup.goldmark.parser.wrapStandAloneImageWithinParagraph: false`.
Passthrough math needs the site's `passthrough` extension.

## 2. API table

| Component | Native form | Full form (shortcode) | Notes |
| --- | --- | --- | --- |
| Callout | `> [!TYPE]± Title` blockquote + optional `{icon="fa-solid fa-x"}` | — | types `note tip important warning caution success danger question example quote details`; `-`/`+` fold; unknown types stay visible |
| Tabs | adjacent fences / tables with `{tab= group= value=}` | `{{< tabs group= default= label= >}}` `{{< tab label= value= >}}…{{< /tab >}}` `{{< /tabs >}}` | runtime `assets/js/tabs.js`; hash `#<group>-<value>`, storage `td-tabs:v1:<group>` only with a group |
| Steps | `1.` list + `{.steps}` | `{{% steps %}}` + headings | list items hold any block except `%` containers |
| Cards | link list + `{.cards}` | `{{< cards >}}` `{{< card title= link= icon= badge= image= image_alt=\|decorative= >}}body{{< /card >}}` `{{< /cards >}}` | |
| Fields | table + `{.fields [caption=] [id=] [meta="type required default -"]}` (first column name, last column description, middle columns metadata) | `{{< fields label= id= class= data-*= >}}` `{{< field name= type= required= default= >}}…{{< /field >}}` `{{< /fields >}}` | same chips from either form; the shortcode is for block-level descriptions; entries get `#field-<name>` anchors |
| FileTree | ```` ```filetree {title=} ```` fence: `- name[/]  # comment  {icon= tone= open= type=}` per line; 2/4-space, tab, or `tree` indentation | — | CSS + native `<details>`; comment column aligned at build time, split clamped 50–70% and draggable (`hasFileTree` → `assets/js/filetree.js`) |
| Gallery | ```` ```gallery ```` fence, `![alt](src) # description {link= class=}` per line | — | alt required; per-item link; Zoom marked at emit time |
| Image | `![alt](src "title")` (render hook; block image + `{#id num= caption= width= height= link= command= options=}` → figure) | — | the `image` shortcode is retired; `link` needs a caption or num and is never zoomable; the resource `byline` rides in the figcaption |
| Table family | `{.full-width}` `{.fields}` `{.matrix}` `{caption=}` `{#id}` `{#id num= caption=}` `{tab= group= value=}` | — | site classes pass through; exclusivity: fields ⟂ matrix/full-width/num, num ⟂ tab |
| Fig / Tbl / Eq / Eg | image / table / `$$` block / fence + `{#id num= caption=}` | `{{< fig >}}` `{{< tbl >}}` `{{< eq >}}` `{{< eg >}}` | default IDs `fig- tbl- eq- eg-<num>`; `eg` caption required |
| Xref | plain Markdown links (kind-less) | `{{< xref fig\|tbl\|eq\|eg="…" [page=] [anchor=] >}}` | |
| Book indexes | — | `book-toc` `book-figures` `book-tables` `book-equations` `book-examples` | no `kind` parameter |
| Fences | `{title copy wrap collapse label id tab group value num caption lineNos hl_lines lineNoStart anchorLineNos tabWidth}` | — | Prism mode unchanged |
| Data fences | `mermaid plantuml markmap math chem echarts infographic checksums filetree gallery` | — | `echarts` declarative only, `$fn:<name>` callbacks via `window.OinkEchartsFunctions` |
| Leaves | raw `<kbd>` | `kbd` `badge` `param` `include` `comment` `contributors` `asciinema` | `badge` has no `outline`; `param` scalar only |
| Release / OpenAPI | `checksums` fence | `release-card` `release-assets` `download` / `swagger` `redoc` | |

Shortcode inventory: 29 — core 14 (`tabs tab steps cards card fields field
include kbd badge param comment contributors asciinema`), Book 10 (`fig
tbl eq eg xref book-toc book-figures book-tables book-equations
book-examples`), Release 3, OpenAPI 2.

## 3. One example per component

Callout:

```markdown
> [!WARNING] Destructive
> The body is page-level Markdown; `> [!NOTE]-` collapses, `> [!DETAILS]` is a
> neutral disclosure block.
```

Tabs (adjacent fences and the shortcode):

````markdown
```bash {tab="Homebrew" group="install" value="brew"}
brew install pigsty
```
```bash {tab="APT" value="apt"}
sudo apt install pigsty
```

{{< tabs group="setting" default="conf" >}}
{{< tab label="Environment Variable" value="env" >}}…{{< /tab >}}
{{< tab label="Configuration Setting" value="conf" >}}…{{< /tab >}}
{{< /tabs >}}
````

Steps:

```markdown
1. Install
   ```bash
   brew install pigsty
   ```
1. ### Initialise {#init}
   Headings inside steps enter the TOC.
{.steps}
```

Cards, Fields:

```markdown
- [Install](/docs/install/) — Deploy from scratch.
- [Configure](/docs/configure/) — Tune the runtime.
{.cards}

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | Local search index |
{.fields caption="Search parameters"}

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `baseURL` | string | yes | | Site address, subpath included |
{.fields meta="type required default"}
```

`meta` names each middle column's role (`type`, `required`, `default`, or `-`
to keep the header as the chip label), which is what makes a table render the
same chips as the shortcode form. Reach for the shortcode only when a
description needs several paragraphs, a list, or a fence.

Tables and Book targets:

````markdown
| OS / PG | PG18 | PG17 |
| --- | :---: | :---: |
| EL 9 | ✅ | ✅ |
{.matrix}

| Isolation | Dirty read |
| --- | --- |
| Serializable | no |
{#tab_iso num="9-1" caption="Anomalies by isolation level"}

![Word 2003](/fig/word.png)
{#office_2003 num="2-1" caption="The Word 2003 interface"}

$$
X \approx \frac{C}{R+Z}
$$
{#eq_x num="5.3"}

```sql {num="4-1" caption="Analytics query" #ex_query}
SELECT 1;
```

See {{< xref fig="2-1" anchor="office_2003" />}} and {{< xref eg="4-1" anchor="ex_query" />}}.
````

Data fences and leaves:

````markdown
```filetree {title="Repository layout"}
- content/                        # site content
  - _index.md                     # site home
  - docs/                         # guides            {open=false}
    - [getting-started.md](/docs/getting-started/)
- hugo.yaml                       # root:root 0644
- LICENSE                         # {icon="fa-solid fa-scale-balanced" tone=warning}
```

```gallery
![Overview page](overview.webp) # The landing view
![Detail page](detail.webp) # Request details {link=/docs/requests/}
```

```echarts {height="320px"}
series: [{type: bar, data: [12, 9, 4]}]
```

```checksums {base="https://downloads.example.org/releases/stable" algo="sha256"}
<sha256>  pig-1.7.0-1.aarch64.rpm
```

{{< include file="yaml/slim.yml" code=true lang="yaml" >}}
{{< kbd "Ctrl" "K" >}} {{< badge text="Beta" tone="warning" >}} {{< param version >}}
````

## 4. Hook attribute policy

Every render hook that reads block attributes goes through
`layouts/_partials/content/attributes.html`:

| Key | table | image (block) | fence | `$$` block | blockquote |
| --- | --- | --- | --- | --- | --- |
| consumed | `id caption num tab group value` | `id num caption width height` | `title filename copy wrap collapse label id tab group value num caption` + Chroma options | `id num caption` | `icon` |
| `class` | pass-through (token-validated) | pass-through | appended to the root | pass-through | pass-through |
| `data-*`, `aria-*` | pass-through | pass-through | pass-through | pass-through | pass-through |
| `style`, `on*`, unknown | build error | build error | build error (`style`/`on*`/`srcdoc`/reserved `data-td-code*` and any unknown key; enhanced-code-blocks §5.5) | build error | build error |

The theme never accepts author `style` or event handlers anywhere. Markers
(`steps cards fields matrix full-width`) are fixed vocabulary;
any other class on a table, image, blockquote, or figure is site CSS and is
passed through untouched.

## 5. Source linter rules (preflight)

The theme validates what it can at build time (unknown parameters and
attributes, exclusivity, IDs, numbers, required alt/caption); a source linter
covers what Goldmark cannot report:

- an attribute line separated from its block by a blank line (it silently
  disappears);
- a marker on the wrong block type (`{.steps}` on a `ul`, `{.cards}` on an
  `ol`, `{.fields}`/`{.matrix}`/`{.full-width}` off a table), and the removed
  `{.filetree}` marker (write a `filetree` fence);
- `{{% … %}}` shortcodes written inside a list item (the list truncates);
- Gallery images without alt text;
- Font Awesome icon values that are not one `fa-<style> fa-<name>` pair;
- residual removed shortcodes (see section 6): `python3 scripts/migrations/oink06.py check --site <dir>`.

## 6. Migration from the 0.4 shortcodes

| Old | New | Toolkit key |
| --- | --- | --- |
| `{{% alert color=… title=… %}}`, `{{% details %}}`, `{{% td-page-notice %}}`, raw `<details><summary>` | `> [!TYPE] title` / `> [!DETAILS]-` | `callout` |
| `{{< tabpane >}}{{% tab header=… %}}`, `{{< code-group >}}{{< code-tab >}}` | adjacent fences `{tab= group= value=}` (code-only panes) or `{{< tabs >}}{{< tab >}}` | `tabs` |
| `{{< filetree >}}` `filetree/folder` `filetree/file`, interim `{.filetree}` lists | ```` ```filetree ```` fence (`label`→`title`, `open`/`icon`/`color`/`comment`/`link` kept) | `filetree` |
| `{{< gallery >}}` `gallery/image`, image list + `{.gallery}` | ```` ```gallery ```` fence | `gallery` |
| `{{< echarts >}}` `{{< infographic >}}` | same-named fences (`$fn:` unchanged; `js` sub-fences must move to `window.OinkEchartsFunctions`) | `datafence` |
| `doc-cards`/`doc-card`, `nav-cards`/`nav-card`, `card`/`cardpane`, `doc-carousel` | `{{< cards >}}{{< card >}}` or link list + `{.cards}` | `cards` |
| `{{< imgproc … >}}`, `{{< image … >}}` | `![alt](src)` + `{command= options= caption=}` | `image` |
| `{{< readfile file=… >}}` | `{{< include file=… >}}` | `include` |
| fence `{filename="x"}` | `{title="x"}` | `fencetitle` |
| `{{< badge … outline=… >}}` | drop `outline` | `badge` |
| `{{< example … />}}` + fence, `{{< book-figures kind="tbl" >}}` | `{{< eg >}}…{{< /eg >}}`, `{{< book-tables >}}` | `eg` |
| `{{% fields %}}`/`{{% field %}}` (never shipped) | `{{< fields >}}`/`{{< field >}}` | `fieldsdelim` |
| `{{% _param x %}}`, `iframe`, `conditional-text`, `blocks/*`, `netlify`, kind-less `xref` | report only (manual) | `reportonly`, `param_placeholders` |

Toolkit (`scripts/migrations/oink06.py`, stdlib only, tests in
`tests/migrations/`):

```sh
python3 scripts/migrations/oink06.py report --sites ~/pgsty/*.com ~/www/ddia --md report.md --json report.json
python3 scripts/migrations/oink06.py migrate --site ~/pgsty/pigsty.io            # dry run: diffs + counts
python3 scripts/migrations/oink06.py migrate --site ~/pgsty/pigsty.io --write    # atomic rewrite; second run reports zero changes
python3 scripts/migrations/oink06.py check   --site ~/pgsty/pigsty.io            # residual legacy syntax → exit 1
```

Text inside fences is never rewritten; ambiguous forms are left unchanged and
listed with `file:line` and a reason.
