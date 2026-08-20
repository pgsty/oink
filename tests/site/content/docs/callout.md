---
title: Callouts
linkTitle: Callouts
description: Write notes, warnings and collapsible asides — with colour, icon and title — as `> [!NOTE]` blockquotes, no shortcode involved.
icon: fa-solid fa-circle-info
weight: 10
search_keywords: [Callout, Alert, Admonition, note, tip, warning, caution, details, collapsible]
---

A callout is a GitHub / Obsidian style blockquote: `> [!TYPE]` on the first
line, the body underneath. Use it to lift a prerequisite, a warning or an aside
out of the running text; if a sentence in the prose says it, a callout is not
needed.

## Shortest form {#minimal}

```markdown {title="Source"}
> [!NOTE]
> Hugo Modules need Go on the machine; an offline archive does not.
```

> [!NOTE]
> Hugo Modules need Go on the machine; an offline archive does not.

Without a title the localized type name is used ("Note" on an English site,
「注意」 on a Chinese one). The source renders as a GitHub callout on GitHub and
as a plain blockquote in any other Markdown reader — nothing is ever lost.

## Ten types {#types}

The first five match GitHub; the other five are semantic types OINK adds. Every
type has a default icon and accent colour.

```markdown {title="Source"}
> [!TIP]
> `hugo server -D` previews drafts.

> [!IMPORTANT]
> The floor is Hugo Extended 0.160.1; anything older fails the build outright.

> [!WARNING]
> `hugo --cleanDestinationDir` empties `public/`.

> [!CAUTION]
> The first build after deleting `resources/_gen` is much slower.

> [!SUCCESS]
> Build passed with zero warnings — ship it.

> [!DANGER]
> Never commit `go.work`.

> [!QUESTION]
> Should the site have comments? See [enabling comments](https://oink.pgsty.com/docs/admin/comments/).

> [!EXAMPLE]
> `pgsty.com` is a documentation site built from callouts and tables alone.

> [!QUOTE]
> Documentation is a love letter that you write to your future self.
```

> [!TIP]
> `hugo server -D` previews drafts.

> [!IMPORTANT]
> The floor is Hugo Extended 0.160.1; anything older fails the build outright.

> [!WARNING]
> `hugo --cleanDestinationDir` empties `public/`.

> [!CAUTION]
> The first build after deleting `resources/_gen` is much slower.

> [!SUCCESS]
> Build passed with zero warnings — ship it.

> [!DANGER]
> Never commit `go.work`.

> [!QUESTION]
> Should the site have comments? See [enabling comments](https://oink.pgsty.com/docs/admin/comments/).

> [!EXAMPLE]
> `pgsty.com` is a documentation site built from callouts and tables alone.

> [!QUOTE]
> Documentation is a love letter that you write to your future self.

Type names are case-insensitive.

## Custom title {#title}

Text after the marker on the same line becomes the title and accepts inline
Markdown — code, bold, links.

```markdown {title="Source"}
> [!WARNING] Rewrites `public/`
> Check that `baseURL` points at the production domain before a production
> build, or every absolute link will be wrong.
```

> [!WARNING] Rewrites `public/`
> Check that `baseURL` points at the production domain before a production
> build, or every absolute link will be wrong.

## Body content {#body}

The body is page-level Markdown: lists, fenced code, tables, images, nested
callouts. Every line starts with `>`, fences included.

````markdown {title="Source"}
> [!TIP] Three commands to a live preview
>
> 1. Clone: `git clone https://github.com/pgsty/oink.pgsty.com my-docs`
> 2. Enter the directory and preview:
>    ```bash
>    cd my-docs && hugo server
>    ```
> 3. Open <http://localhost:1313/>
>
> | Port | Purpose |
> | --- | --- |
> | 1313 | Hugo development server |
````

> [!TIP] Three commands to a live preview
>
> 1. Clone: `git clone https://github.com/pgsty/oink.pgsty.com my-docs`
> 2. Enter the directory and preview:
>    ```bash
>    cd my-docs && hugo server
>    ```
> 3. Open <http://localhost:1313/>
>
> | Port | Purpose |
> | --- | --- |
> | 1313 | Hugo development server |

## Collapsing {#collapsible}

A `-` after the type starts the callout closed, a `+` starts it open. Both
render as a native `<details>`; no JavaScript is loaded. Use them for full
command output, alternatives, background — anything that need not be visible by
default.

```markdown {title="Source"}
> [!NOTE]- Why is Go needed?
> Hugo downloads themes through Go's module system (`hugo mod get`). A submodule
> or an offline archive works without Go installed.

> [!TIP]+ Open by default, but the reader can close it
> The closed state is not remembered; a reload returns to the default.
```

> [!NOTE]- Why is Go needed?
> Hugo downloads themes through Go's module system (`hugo mod get`). A submodule
> or an offline archive works without Go installed.

> [!TIP]+ Open by default, but the reader can close it
> The closed state is not remembered; a reload returns to the default.

## The neutral disclosure, DETAILS {#details}

`[!DETAILS]` is a disclosure without a semantic colour: closed by default,
`[!DETAILS]+` open. Use it for long output, whole configuration files, anything
that has to be foldable.

````markdown {title="Source"}
> [!DETAILS] Full `hugo version` output
> ```text
> hugo v0.164.0+extended+withdeploy darwin/arm64 BuildDate=2026-07-06T16:39:30Z VendorInfo=Homebrew
> ```
````

> [!DETAILS] Full `hugo version` output
> ```text
> hugo v0.164.0+extended+withdeploy darwin/arm64 BuildDate=2026-07-06T16:39:30Z VendorInfo=Homebrew
> ```

## Custom icon {#icon}

The line right after the blockquote can carry `{icon="fa-solid fa-xxx"}` — one
Font Awesome class pair — replacing the type's default icon. The attribute line
must follow the blockquote immediately, with no blank line between them.

```markdown {title="Source"}
> [!TIP] PostgreSQL 18 is supported
> Pigsty v4 installs PostgreSQL 18 by default.
{icon="fa-solid fa-database"}
```

> [!TIP] PostgreSQL 18 is supported
> Pigsty v4 installs PostgreSQL 18 by default.
{icon="fa-solid fa-database"}

## Nesting {#nesting}

Callouts nest (one more `>` per level) and can sit inside list items or steps.
One level of nesting is plenty.

```markdown {title="Source"}
> [!WARNING] Back up before upgrading
> A theme version bump can change how a page renders.
>
> > [!TIP]- How to back up
> > `git tag pre-upgrade` is enough — rolling back is `git checkout pre-upgrade`.
```

> [!WARNING] Back up before upgrading
> A theme version bump can change how a page renders.
>
> > [!TIP]- How to back up
> > `git tag pre-upgrade` is enough — rolling back is `git checkout pre-upgrade`.

## Unknown types and common slips {#pitfalls}

An unknown type name neither fails the build nor loses content: the block
renders as an ordinary blockquote with the `[!TYPE]` marker still visible.

```markdown {title="Source"}
> [!NOTICE] Not a valid type
> The marker stays on the page to tell you so.
```

> [!NOTICE] Not a valid type
> The marker stays on the page to tell you so.

Other things that bite:

- Title merged into the body. In files that pass through Prettier and friends,
  keep an empty `>` line under the title line, or the formatter folds the title
  into the body.
- Attribute line moved by a formatter. Wrap marker lines such as `{icon=…}` in
  `<!-- prettier-ignore-start -->` / `<!-- prettier-ignore-end -->`.
- `style`, `onclick` and friends fail the build: the attribute line accepts
  `icon` and `class` only (see the table below).

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | Static types are `<div class="td-callout" role="note">`; collapsible types are a native `<details>` + `<summary>` |
| Print | All static and expanded; disclosures carry a `data-td-callout-collapsible` marker |
| Markdown | The source blockquote is preserved, `[!TYPE]` marker and title included |
| RSS | Same as print — static and expanded |

Callouts load no script.

## Parameter reference {#reference}

The marker line `> [!TYPE]±  Title`:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `TYPE` | enum | — | `NOTE` `TIP` `IMPORTANT` `WARNING` `CAUTION` `SUCCESS` `DANGER` `QUESTION` `EXAMPLE` `QUOTE` `DETAILS`; case-insensitive; an unknown value renders as a plain blockquote |
| `±` | `-` / `+` / none | none | `-` collapses closed, `+` collapses open; bare `DETAILS` is closed |
| Title | inline Markdown | the localized type name | On the same line as the marker |
{.fields meta="type default"}

The attribute line `{…}`, immediately after the blockquote:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `icon` | Font Awesome class pair | the type's icon | For example `fa-solid fa-database`; `DETAILS` has no default icon |
| `class` | space-separated classes | — | Passed through verbatim for site CSS |
{.fields meta="type default"}

`style`, `on*` and any other key fail the build.

## Limits {#limits}

- Colours cannot be customized: the type decides. When you need a new meaning,
  pick the closest type and write your own title.
- The collapsed state is not persisted.
- Callouts work inside `{.steps}` list items and `{{%/* steps */%}}` steps (see
  [Steps](/docs/steps/)); every line of the blockquote starts with
  `>` and lines up with the list item's indent.

## Related {#related}

- [Steps](/docs/steps/) — callouts inside a procedure
- [Tabs](/docs/tabs/) — the same note split per platform
- [Writing pages](https://oink.pgsty.com/docs/write/pages/) — when to use a callout and when to use prose
