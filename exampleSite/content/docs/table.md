---
title: Tables
linkTitle: Tables
description: A plain GFM table plus one attribute line becomes a captioned table, a compatibility matrix, a field list, a numbered table or a tab set; wide tables scroll on their own.
weight: 50
search_keywords: [Table, matrix, full-width, caption, numbered table, horizontal scroll, GFM]
---

A table is an ordinary GFM pipe table. The theme's table render hook wraps every
one in a horizontally scrollable region, and the `{…}` attribute line underneath
decides which kind of table it is: captioned, a compatibility matrix, a field
list, a numbered table, or a tab set. Merged cells, sorting and filtering are
out of scope; when you need them, change how the data is presented.

## Shortest form {#minimal}

Without an attribute line it is just a table. Alignment still comes from the
delimiter row, and header cells are `th scope="col"`.

```markdown {title="Source"}
| Component | Port | Purpose |
| --- | :---: | --- |
| PostgreSQL | 5432 | Database |
| Pgbouncer | 6432 | Connection pool |
| Patroni | 8008 | High-availability orchestration |
```

| Component | Port | Purpose |
| --- | :---: | --- |
| PostgreSQL | 5432 | Database |
| Pgbouncer | 6432 | Connection pool |
| Patroni | 8008 | High-availability orchestration |

## Wide tables scroll themselves {#scroll}

A table with too many columns never widens the page; it scrolls inside its own
region. That region is focusable: Tab into it and the arrow keys scroll, and its
accessible name is the localized "Scrollable table".

```markdown {title="Source"}
| Cluster | Role | Version | State | Lag | Connections | Size | Backup |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pg-meta | primary | 18.1 | running | — | 42 | 12 GB | 2026-08-17 |
| pg-test | replica | 18.1 | streaming | 12 ms | 8 | 12 GB | 2026-08-17 |
```

| Cluster | Role | Version | State | Lag | Connections | Size | Backup |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pg-meta | primary | 18.1 | running | — | 42 | 12 GB | 2026-08-17 |
| pg-test | replica | 18.1 | streaming | 12 ms | 8 | 12 GB | 2026-08-17 |

## Captions {#caption}

`{caption="…"}` adds a visible `<caption>`. It is plain text and it does not
number the table.

```markdown {title="Source"}
| Item | Value |
| --- | --- |
| Theme version | v0.5.0 |
| Hugo floor | 0.160.1 Extended |
| Licence | Apache-2.0 |
{caption="Theme facts this site currently builds against"}
```

| Item | Value |
| --- | --- |
| Theme version | v0.5.0 |
| Hugo floor | 0.160.1 Extended |
| Licence | Apache-2.0 |
{caption="Theme facts this site currently builds against"}

## Compatibility matrices {#matrix}

`{.matrix}` is for "row × column = supported or not" tables: the first column
becomes a row header (`th scope="row"`), the header row and the first column
stay pinned while scrolling, and the remaining cells are centred unless the
delimiter row says otherwise. ✅ and ❌ are characters the author writes; the
theme does not interpret them.

```markdown {title="Source"}
| OS / PG | PG18 | PG17 | PG16 | PG15 | PG14 |
| --- | :---: | :---: | :---: | :---: | :---: |
| EL 9 | ✅ | ✅ | ✅ | ✅ | ✅ |
| EL 8 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Debian 13 | ✅ | ✅ | ✅ | ❌ | ❌ |
| Ubuntu 24.04 | ✅ | ✅ | ✅ | ✅ | ❌ |
{.matrix}
```

| OS / PG | PG18 | PG17 | PG16 | PG15 | PG14 |
| --- | :---: | :---: | :---: | :---: | :---: |
| EL 9 | ✅ | ✅ | ✅ | ✅ | ✅ |
| EL 8 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Debian 13 | ✅ | ✅ | ✅ | ❌ | ❌ |
| Ubuntu 24.04 | ✅ | ✅ | ✅ | ✅ | ❌ |
{.matrix}

## Using the whole canvas {#full-width}

`{.full-width}` lets a table exceed the reading column and take the full width
the article has. It suits tables with many short columns.

```markdown {title="Source"}
| Language | Code | Sidebar | Search | TOC | Print | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 简体中文 | `zh` | ✅ | ✅ | ✅ | ✅ | Reviewed |
| English | `en` | ✅ | ✅ | ✅ | ✅ | Reviewed |
{.full-width}
```

| Language | Code | Sidebar | Search | TOC | Print | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 简体中文 | `zh` | ✅ | ✅ | ✅ | ✅ | Reviewed |
| English | `en` | ✅ | ✅ | ✅ | ✅ | Reviewed |
{.full-width}

## Field lists {#fields}

`{.fields}` turns a table into a definition list: the first column is the name,
the last is the description, and the columns in between are metadata. It is the
shape for configuration keys, command flags and API fields; the full syntax is
on the [Fields](/docs/fields/) page.

```markdown {title="Source"}
| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | Build the local search index |
| `page_width` | string | `normal` | Width of the reading column |
{.fields meta="type default"}
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | Build the local search index |
| `page_width` | string | `normal` | Width of the reading column |
{.fields meta="type default"}

## Numbered tables {#numbered}

In a book or a long manual, number the tables: `num` plus an optional `#id` and
`caption`. The table is wrapped in a `<figure>` labelled with a localized
"Table N." and registered as a Book target, so `xref` can reference it and it
appears in the book-wide list of tables. The number is written by the author —
the theme never counts — and `id` defaults to `tbl-<num>`.

```markdown {title="Source"}
| Isolation level | Dirty read | Non-repeatable read | Phantom read |
| --- | --- | --- | --- |
| Read committed | no | yes | yes |
| Repeatable read | no | no | yes |
| Serializable | no | no | no |
{#tbl-iso num="9-1" caption="Anomalies each PostgreSQL isolation level permits"}

See {{</* xref tbl="9-1" anchor="tbl-iso" */>}}.
```

| Isolation level | Dirty read | Non-repeatable read | Phantom read |
| --- | --- | --- | --- |
| Read committed | no | yes | yes |
| Repeatable read | no | no | yes |
| Serializable | no | no | no |
{#tbl-iso num="9-1" caption="Anomalies each PostgreSQL isolation level permits"}

See {{< xref tbl="9-1" anchor="tbl-iso" />}}.

## Tables as tabs {#tabs}

Adjacent tables carrying `{tab="…"}` form a tab set under the same rules as
adjacent fences: `group` on the first table enables hash, sync and persistence,
and every table after it needs `value`. The complete rules are on the
[Tabs](/docs/tabs/) page.

```markdown {title="Source"}
| Directory | Contents |
| --- | --- |
| `content/` | Pages |
| `data/` | Landing and release data |
{tab="Content" group="repo-layout" value="content"}

| Directory | Contents |
| --- | --- |
| `assets/` | SCSS and image resources |
| `static/` | Files copied verbatim |
{tab="Assets" value="assets"}
```

| Directory | Contents |
| --- | --- |
| `content/` | Pages |
| `data/` | Landing and release data |
{tab="Content" group="repo-layout" value="content"}

| Directory | Contents |
| --- | --- |
| `assets/` | SCSS and image resources |
| `static/` | Files copied verbatim |
{tab="Assets" value="assets"}

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | A focusable `<div class="td-table-scroll">` around the `<table>`; matrix and full-width are modifier classes on that wrapper |
| Print | The complete table laid out to the page width; the wrapper stays but is marked `td-table-scroll--static` and is no longer a focusable viewport |
| Markdown | The source table and its attribute line, emitted as written |
| RSS | The complete static table |

Tables load no script.

## Parameter reference {#reference}

The attribute line on the row below the table:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `.full-width` | marker | none | Exceed the reading column and use the article canvas |
| `.matrix` | marker | none | First column as row header, header and first column pinned, other cells centred |
| `.fields` | marker | none | Render as a definition list, see [Fields](/docs/fields/) |
| `caption` | plain text | none | Visible table caption; on `.fields` it labels the list |
| `meta` | role list | none | Names the meaning of the middle `.fields` columns: `type` `required` `default` `-`; requires `.fields` |
| `#id` | identifier | `tbl-<num>` when `num` is set | `[A-Za-z][A-Za-z0-9_.:-]*`; lands on the `<table>`, or on the `<figure>` for a numbered table |
| `num` | string | none | `[0-9A-Za-z.-]+`; registers a Book table target and prefixes the caption with "Table N." |
| `tab` / `group` / `value` | see [Tabs](/docs/tabs/) | none | Adjacent tables become a tab set |
| `class` | class list | none | Left on the `<table>` for site CSS |
| `data-*` / `aria-*` | string | none | Passed through |
{.fields meta="type default"}

`style`, `on*` and any other key fail the build.

## Limits {#limits}

- Mutual exclusions: `.fields` cannot combine with `.matrix`, `.full-width` or
  `num`; `num` and `tab` are exclusive; `group`/`value` require `tab`; `meta`
  requires `.fields`.
- The attribute line must touch the table: leave a blank line and it becomes a
  visible line of braces. Markdown formatters like to move it — wrap it in
  `<!-- prettier-ignore-start -->` / `<!-- prettier-ignore-end -->`.
- No merged cells, no sorting, no filtering: what a GFM pipe table can express
  is all there is. Split a complex table with a merged header into two tables,
  or turn it into a matrix.
- Block content does not fit in a cell: multi-paragraph descriptions, lists and
  fences need the `fields`/`field` shortcode.
- `.matrix` centring is CSS: an explicit alignment in the delimiter row wins.

## Related {#related}

- [Fields](/docs/fields/) — everything `{.fields}` can do
- [Tabs](/docs/tabs/) — adjacent tables as a tab set
- [Publishing books](https://oink.pgsty.com/docs/write/book/) — numbered tables, cross references, the list of tables
- [Code blocks](/docs/code/) — where attributes go on the info line instead of the next line
