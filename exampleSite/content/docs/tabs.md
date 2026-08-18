---
title: Tabs
linkTitle: Tabs
description: A `{tab=}` attribute on adjacent fences or tables makes a tab set; add a group and it becomes linkable, synchronized and remembered.
weight: 40
search_keywords: [Tabs, tab, group, value, sync, persistence, localStorage, hash]
---

Tabs put equivalent alternatives side by side: package managers, distributions,
YAML / TOML / JSON, an environment variable versus a configuration key. Ordered
steps and unrelated content do not belong in tabs — the reader sees only one
panel at a time.

The native form is a `tab` attribute on adjacent blocks. Reach for the
`tabs`/`tab` shortcode only when the panels hold running text: several
paragraphs, lists, callouts. Both forms share one runtime, one DOM and the same
keyboard behaviour.

## Shortest form {#minimal}

Write two fences carrying `tab` back to back, separated by a blank line only.

````markdown {title="Source"}
```bash {tab="Homebrew"}
brew install hugo
```
```bash {tab="Debian / Ubuntu"}
sudo apt install hugo
```
````

```bash {tab="Homebrew"}
brew install hugo
```
```bash {tab="Debian / Ubuntu"}
sudo apt install hugo
```

The server emits two titled code blocks with no panel hidden; after the page
loads, the runtime regroups adjacent blocks of the same kind into a tab set. On
GitHub, in print, and with JavaScript off, the reader sees two complete blocks
one after the other.

## Groups: links, sync and memory {#group}

Write `group` on the first block only and the set gains a public URL hash
`#<group>-<value>`, in-page synchronization and browser persistence. Every block
in a group must carry `value`.

````markdown {title="Source"}
```bash {tab="npm" group="pkgmgr" value="npm"}
npm create hugo-site@latest
```
```bash {tab="pnpm" value="pnpm"}
pnpm create hugo-site
```
```bash {tab="Yarn" value="yarn"}
yarn create hugo-site
```
````

```bash {tab="npm" group="pkgmgr" value="npm"}
npm create hugo-site@latest
```
```bash {tab="pnpm" value="pnpm"}
pnpm create hugo-site
```
```bash {tab="Yarn" value="yarn"}
yarn create hugo-site
```

`value` is the machine value (`^[a-z0-9][a-z0-9_-]*$`), `tab` is the human
label; the two are independent. The pnpm panel above answers to
`#pkgmgr-pnpm`, and visiting this page with that hash selects it.

## Groups move together {#sync}

The set below reuses `group="pkgmgr"`. Switch the package manager above and this
one follows; switch it here and the one above follows. The choice is written to
`localStorage` under the key `td-tabs:v1:pkgmgr` and still applies to
same-group tabs on other pages.

````markdown {title="Source"}
```bash {tab="npm" group="pkgmgr" value="npm"}
npm run build
```
```bash {tab="pnpm" value="pnpm"}
pnpm build
```
````

```bash {tab="npm" group="pkgmgr" value="npm"}
npm run build
```
```bash {tab="pnpm" value="pnpm"}
pnpm build
```

This set has no `yarn` panel. When a value is missing, that set simply stays
where it is; a set is never left with nothing selected. The initial selection is
decided in this order: URL hash, stored value, the shortcode's `default` or the
first block, the first tab. Opening the page with a hash switches the set
without overwriting a preference the reader already stored.

## Tables can be tabs too {#tables}

The same attributes on a table's attribute line group adjacent tables into a tab
set.

```markdown {title="Source"}
| Parameter | Default |
| --- | --- |
| `shared_buffers` | 25% RAM |
| `max_connections` | 100 |
{tab="PostgreSQL 18" group="pgver" value="pg18"}

| Parameter | Default |
| --- | --- |
| `shared_buffers` | 128MB |
| `max_connections` | 100 |
{tab="PostgreSQL 13" value="pg13"}
```

| Parameter | Default |
| --- | --- |
| `shared_buffers` | 25% RAM |
| `max_connections` | 100 |
{tab="PostgreSQL 18" group="pgver" value="pg18"}

| Parameter | Default |
| --- | --- |
| `shared_buffers` | 128MB |
| `max_connections` | 100 |
{tab="PostgreSQL 13" value="pg13"}

Fences and tables are two block kinds and never merge into one set even when
adjacent: a tab set is all fences or all tables. To mix them, use the shortcode
form below.

## A label and a filename together {#tab-with-title}

A fence can carry both `tab` and `title`: the label goes in the tab bar, the
filename title bar stays inside the panel.

````markdown {title="Source"}
```yaml {tab="YAML" title="hugo.yaml" group="conffmt" value="yaml"}
params:
  ui:
    sidebar_menu_foldable: true
```
```toml {tab="TOML" title="hugo.toml" value="toml"}
[params.ui]
sidebar_menu_foldable = true
```
````

```yaml {tab="YAML" title="hugo.yaml" group="conffmt" value="yaml"}
params:
  ui:
    sidebar_menu_foldable: true
```
```toml {tab="TOML" title="hugo.toml" value="toml"}
[params.ui]
sidebar_menu_foldable = true
```

## A lone block is just a titled block {#single-block}

A block needs a neighbour of the same kind to become a tab set. On its own it
keeps its title rather than becoming a tab bar with one tab.

````markdown {title="Source"}
```ini {tab="on its own"}
listen_addresses = '*'
```
````

```ini {tab="on its own"}
listen_addresses = '*'
```

Only blank lines may sit between blocks. Three things break a set: running text
in between (a paragraph, a heading or a list all count); an HTML comment in
between, of which `<!-- prettier-ignore-end -->` is the common one; a later
block writing its own `group`, since only the first block of a set may carry it.

## Tabs around running text {#shortcode}

When a panel holds paragraphs, lists, callouts, or several blocks, use the
`tabs`/`tab` shortcode. The body is full Markdown.

`````markdown {title="Source"}
{{</* tabs group="deploy" default="pages" label="Deployment target" */>}}
{{</* tab label="GitHub Pages" value="pages" */>}}
The repository ships `.github/workflows/`; a push to `main` builds and publishes.

> [!NOTE]
> `baseURL` has to be the repository's Pages address.
{{</* /tab */>}}
{{</* tab label="Cloudflare Pages" value="cloudflare" */>}}
Connect the repository in the Cloudflare dashboard; the build command is:

```bash
hugo --gc --minify
```
{{</* /tab */>}}
{{</* /tabs */>}}
`````

{{< tabs group="deploy" default="pages" label="Deployment target" >}}
{{< tab label="GitHub Pages" value="pages" >}}
The repository ships `.github/workflows/`; a push to `main` builds and publishes.

> [!NOTE]
> `baseURL` has to be the repository's Pages address.
{{< /tab >}}
{{< tab label="Cloudflare Pages" value="cloudflare" >}}
Connect the repository in the Cloudflare dashboard; the build command is:

```bash
hugo --gc --minify
```
{{< /tab >}}
{{< /tabs >}}

`default` names the initially selected panel; it must equal a child's `value`
and it requires `group`. Without `group`, `value` is forbidden and the theme
generates `tab1`, `tab2` and so on — such a set switches locally and touches
neither the URL nor storage. The shortcode form is stricter than the attribute
form: a mistake is reported at build time instead of in the browser.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | `<div class="td-tabs">` with `role="tablist"` buttons and panels; every panel is visible until the runtime takes over |
| Print | Consecutive titled static sections, no tab bar |
| Markdown | The fence form keeps the source fence, `{tab=}` included; the shortcode form emits `**Label**` plus the body |
| RSS | Same as print — stacked titled sections |

Only a page that uses tabs loads `tabs.js`; print, Markdown and RSS never do.

## Parameter reference {#reference}

Attributes on a fence info line or a table attribute line:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `tab` | non-empty string | none | The visible label; on a lone block it is simply that block's title |
| `group` | `^[a-z][a-z0-9_-]*$` | none | On the first block of a set; enables hash, in-page sync and persistence; requires `tab` |
| `value` | `^[a-z0-9][a-z0-9_-]*$` | none | Required on every block of a group, forbidden without one; requires `tab` |
{.fields meta="type default"}

The `tabs` shortcode:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `group` | `^[a-z][a-z0-9_-]*$` | none | As above: hash, sync and persistence |
| `default` | a child's `value` | the first child | The initially selected panel; requires `group` |
| `label` | plain text | localized "Tabs" | Accessible name for the tab bar; not displayed |
{.fields meta="type default"}

The `tab` shortcode:

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `label` | plain text | yes | The visible label |
| `value` | `^[a-z0-9][a-z0-9_-]*$` | when `group` is set | Forbidden without a group, where `tab1`, `tab2` … are generated |
{.fields meta="type required"}

Behavioural contract: in a group the panel ID is `<group>-<value>`; when the
same `group` name appears a second time on one page, later sets get a `-2`,
`-3` suffix and the deep-link target stays the first set. Ungrouped sets get
theme-generated IDs. The storage key is `td-tabs:v1:<group>`. A click or a key
press updates the hash with `replaceState` and writes storage; arriving with a
hash only switches. Left and right arrows (RTL-aware) plus Home/End move and
activate, and focus stays on the tab.

## Limits {#limits}

- Build failures: in the attribute form, `value` without `group`, `group` or
  `value` without `tab`, `tab` together with the numbering attribute `num`; in
  the shortcode form, a duplicate `value` in one set, a `tabs` with no `tab`
  child, running text between children, or a `default` that matches no child.
- Grouping mistakes in the attribute form do not stop the build; they leave a
  warning in the browser console. A missing `value` drops `group` from the whole
  set, which degrades to a locally switching tab set with no hash, sync or
  persistence. A duplicate `value` skips the set entirely and those blocks stay
  titled blocks.
- Fences and tables never merge into one set. To mix prose with code, use the
  shortcode form.
- Tabs are not a disclosure. To fold away long output use `> [!DETAILS]` (see
  [Callouts](/docs/callout/)).
- A `group` name is shared site-wide: a reader who picks pnpm on page A gets
  pnpm in the same group on page B. That is the point — and it means `group`
  names should mean something, not be `tabs1`.

## Related {#related}

- [Code blocks](/docs/code/) — the rest of the fence attributes (title, copy, line numbers, folding)
- [Tables](/docs/table/) — the rest of the table attribute line
- [Callouts](/docs/callout/) — for folding rather than juxtaposing
- [Steps](/docs/steps/) — tabs inside a procedure
