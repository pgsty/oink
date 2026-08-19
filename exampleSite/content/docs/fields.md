---
title: Fields
linkTitle: Fields
description: A plain table plus `{.fields}` documents configuration keys, command flags and API fields — name, type, default and description each in place, readable on a narrow screen, every entry individually linkable.
icon: fa-solid fa-sliders
weight: 60
search_keywords: [Fields, field, configuration key, parameter, API field, meta, type, required, default, definition list, anchor]
---

Fields render "a list of named values with metadata and a description" as a
responsive definition list: the name gets its own line, type / required /
default sit beside it as small chips, the description starts on the next line,
and every entry carries its own anchor. Use it for configuration keys, command
flags and API fields. When readers need to compare many rows across the same
columns, keep a plain table; when the content is a sequence of actions, use
steps.

There are two spellings: a plain table plus `{.fields}` (the default choice),
and the `fields`/`field` shortcode, for when a description needs several
paragraphs, a list or a code block. Both render the same entries.

## Shortest form {#minimal}

A pipe table with at least two columns and `{.fields}` on the next line. The
first column is the name, the last is the description, and every column in
between is metadata labelled with its own header text.

```markdown {title="Source"}
| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | Build the local search index and enable the command palette |
| `offline_search_max_results` | integer | `10` | Maximum number of search results |
| `page_width` | string | `normal` | Reading column width: `narrow` `normal` `wide` |
{.fields}
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | Build the local search index and enable the command palette |
| `offline_search_max_results` | integer | `10` | Maximum number of search results |
| `page_width` | string | `normal` | Reading column width: `narrow` `normal` `wide` |
{.fields}

Metadata here shows as "Header: value". The theme infers nothing from the header
— `Type` is only a label. The next section turns those into standard chips.
Cells accept inline Markdown (code, emphasis, links) and empty middle cells are
omitted.

## Semantic columns with `meta=` {#meta}

`meta` says, in order, what each middle column means: `type`, `required`,
`default`, or `-` to keep the header as a plain label. With it, the table form
renders the same chips as the shortcode form.

```markdown {title="Source"}
| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `baseURL` | string | yes | | Site address, subpath included |
| `title` | string | yes | | Site name, shown in the navbar and the tab |
| `defaultContentLanguage` | string | | `en` | Default language; decides which language unprefixed paths belong to |
{.fields meta="type required default"}
```

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `baseURL` | string | yes | | Site address, subpath included |
| `title` | string | yes | | Site name, shown in the navbar and the tab |
| `defaultContentLanguage` | string | | `en` | Default language; decides which language unprefixed paths belong to |
{.fields meta="type required default"}

The rules:

- `meta` must name a role for every middle column — exactly the column count
  minus two. Too many or too few fails the build.
- A `required` column is "non-empty means true": "yes", "是" or "✔" all read the
  same, and the rendered chip is the untranslated `required`. An empty cell
  shows nothing.
- `type` and `default` cells with no inline markup of their own are wrapped in
  code formatting, matching the shortcode form.
- The three semantic chips always display in the order `type`, `required`,
  `default`, whatever order the columns are in; `-` columns follow, in column
  order.

`-` mixes with semantic roles, which is how you keep one custom label:

```markdown {title="Source"}
| Environment variable | Type | Scope | Description |
| --- | --- | --- | --- |
| `HUGO_MODULE_WORKSPACE` | string | build | Points at `go.work` so the theme resolves from a local checkout |
| `HUGO_ENV` | string | build | Set to `production` to enable minification and fingerprinting |
{.fields meta="type -"}
```

| Environment variable | Type | Scope | Description |
| --- | --- | --- | --- |
| `HUGO_MODULE_WORKSPACE` | string | build | Points at `go.work` so the theme resolves from a local checkout |
| `HUGO_ENV` | string | build | Set to `production` to enable minification and fingerprinting |
{.fields meta="type -"}

## Labels and container IDs {#caption-id}

`caption` gives the whole list a visible label, which is also its accessible
name; `id` names the outer container so it can be linked to or styled.

```markdown {title="Source"}
| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `enable` | boolean | `false` | Turn image zoom on |
| `selector` | string | `.td-content` | Root selector scanned for candidate images |
{.fields caption="params.ui.image_zoom" id="zoom-params" meta="type default"}
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `enable` | boolean | `false` | Turn image zoom on |
| `selector` | string | `.td-content` | Root selector scanned for candidate images |
{.fields caption="params.ui.image_zoom" id="zoom-params" meta="type default"}

## Every entry is linkable {#anchors}

Each entry gets an anchor of the form `field-<name>`, and a self-link icon
appears beside the name on hover. `page_width` in the first table above is
[#field-page_width](#field-page_width) — a link you can send on its own when
answering a question.

Duplicate names on one page get `-2`, `-3` suffixes, the same rule Goldmark uses
for duplicate headings. Anchors are generated in HTML only: print and RSS
assemble many pages into one document, where in-page anchors would collide.

## The shortcode form {#shortcode}

When the description needs several paragraphs, a list or a code block, a table
cell cannot hold it. Use `fields`/`field`:

````markdown {title="Source"}
{{</* fields label="Common pig flags" */>}}
{{</* field name="--config" type="path" required=true */>}}
Path to the configuration file. Relative paths resolve against the working
directory.

When `PIG_CONFIG` is also set, the command-line flag wins.
{{</* /field */>}}
{{</* field name="--log-level" type="string" default="info" */>}}
Log level, from low to high:

- `debug`: print every remote call
- `info`: the default
- `error`: output only on failure
{{</* /field */>}}
{{</* field name="--dry-run" type="boolean" default=false */>}}
Print what would happen and change nothing:

```bash
pig ext install pg_duckdb --dry-run
```
{{</* /field */>}}
{{</* /fields */>}}
````

{{< fields label="Common pig flags" >}}
{{< field name="--config" type="path" required=true >}}
Path to the configuration file. Relative paths resolve against the working
directory.

When `PIG_CONFIG` is also set, the command-line flag wins.
{{< /field >}}
{{< field name="--log-level" type="string" default="info" >}}
Log level, from low to high:

- `debug`: print every remote call
- `info`: the default
- `error`: output only on failure
{{< /field >}}
{{< field name="--dry-run" type="boolean" default=false >}}
Print what would happen and change nothing:

```bash
pig ext install pg_duckdb --dry-run
```
{{< /field >}}
{{< /fields >}}

`required=true` and `default=false` are booleans and take no quotes. `default`
accepts any scalar: `default=0` and `default=""` both display faithfully (the
empty string shows as `""`), and omitting `default` omits the chip. Every
`field` needs a non-empty body and must be a direct child of `fields`.

## Which form to use {#which}

| Situation | Use |
| --- | --- |
| One-sentence descriptions that fit in a table cell | table + `{.fields}` |
| Descriptions with paragraphs, lists or code blocks | the `fields`/`field` shortcode |
| Readers comparing many rows across the same columns | a plain table, not a field list |
| Content that is a sequence of actions | [Steps](/docs/steps/) |

The table form stays a readable table on GitHub, and OINK's Markdown output
keeps it as a table. That is why it is the default.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | `<div class="td-fields">` around a semantic `<dl>`; entries carry `#field-<name>` anchors and self-links |
| Print | The complete definition list, without entry anchors |
| Markdown | The table form keeps the source table; the shortcode form emits a bulleted list of "`name` — type; required; default: value" plus the indented description |
| RSS | The complete static `<dl>`, without entry anchors |

No script is loaded.

## Parameter reference {#reference}

The table attribute line, on the row below the table:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `.fields` | marker | none | Required; renders the table as a field list |
| `meta` | role list | none | Space-separated `type` `required` `default` `-`; one per middle column; semantic roles cannot repeat |
| `caption` | plain text | none | Visible label and the list's accessible name |
| `id` | identifier | none | ID of the outer container |
| `class` | class list | none | Passed through for site CSS |
| `data-*` / `aria-*` | string | none | Passed through |
{.fields meta="type default"}

The `fields` shortcode:

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `label` | non-empty string | no | Visible label; the same thing the table's `caption` does |
| `id` | identifier | no | Container ID; no whitespace, quotes, `<`, `>` or `&` |
| `class` / `data-*` / `aria-*` | string | no | The same policy as the table attribute line |
{.fields meta="type required"}

The `field` shortcode:

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | non-empty string | yes | The field name |
| `type` | non-empty string | no | Type label such as `boolean`, `string[]`, `duration` |
| `required` | boolean | no | `true` shows the untranslated `required` chip; defaults to `false` |
| `default` | scalar | no | String / boolean / integer / float; `false`, `0` and `""` all display |
{.fields meta="type required"}

## Limits {#limits}

- The first column must be non-empty and unique within one table; a duplicate or
  an empty name fails the build.
- `.fields` cannot combine with `.matrix`, `.full-width` or `num`, and `meta`
  cannot appear on a table without `.fields`.
- Block content does not fit in a table cell: paragraphs, lists and fences need
  the shortcode form.
- `required` and `default` are untranslated API vocabulary and stay in English
  in every language. They are contract words, not interface copy.
- No `kind`, `since`, `deprecated`, `location`, per-field links or nested
  structures, and nothing parses TypeScript or an OpenAPI schema at build time.

## Related {#related}

- [Tables](/docs/table/) — the rest of the attribute line and the exclusion rules
- [Configuration](https://oink.pgsty.com/docs/customize/config/) — the full site parameter table, itself a field list
- [Front matter](https://oink.pgsty.com/docs/write/frontmatter/) — the full front matter table
- [Steps](/docs/steps/) — ordered actions do not belong in a field list
