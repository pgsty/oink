---
title: Include
linkTitle: Include
description: Pull an external file in with include, print a site parameter with param, and write a note that reaches no output at all with comment.
weight: 200
search_keywords: [include, file, snippet, reuse, readfile, param, interpolation, comment]
params:
  pigsty_pg_major: 18
---

Three shortcodes, one job each: `include` puts another file's contents into this
page, `param` prints a page or site parameter, and `comment` discards a passage.
They are for fragments reused across pages and constants scattered over many:
one set of install steps that appears on three pages is an `include`, a version
number that appears on dozens is a `param`, and either way you edit one place.
Content that appears on one page belongs on that page.

## Shortest form {#minimal}

`include` takes one required parameter, `file`:

```markdown {title="Source"}
{{</* include file="parts/install-oink.md" */>}}
```

The file it pulls in is ordinary Markdown living under `assets/`:

````markdown {title="assets/parts/install-oink.md"}
Installing OINK into an existing Hugo site takes three commands:

```sh
hugo mod init github.com/you/your-site
hugo mod get github.com/pgsty/oink
hugo server
```

> [!NOTE]
> `hugo mod get` needs Go on the machine; an offline archive or a submodule does not.

The current release is {{</* param version */>}}.
````

The result is what you would get by writing it here: the code block has its copy
button and the callout is a callout.

{{< include file="parts/install-oink.md" >}}

The file that gets included is not a page of its own: it is absent from the
sidebar, it takes no part in translation pairing, and it has no URL.

## Where the file comes from {#sources}

`file` resolves in this order, first match wins:

| Order | Looked up as | Written as |
| --- | --- | --- |
| 1 | A page resource — a file in this page's bundle | `file="config.yaml"` |
| 2 | A global resource under `assets/` | `file="snippets/dsn.txt"` |
| 3 | A file under `content/`: a leading `/` is the content root, otherwise relative to the page's directory | `file="notes/caveat.md"`, `file="/shared/notice.md"` |

Missing in all three, the build fails; nothing is emitted as a placeholder. A
`..` in the path fails the build too: include reads from `content/` and
`assets/` and nowhere else.

A Markdown fragment is read as source, so write the file's real name on disk.
One trap belongs to step 1 alone: Hugo attaches a language-suffixed page
resource such as `notice.zh.md` under its stripped name, so asking a bundle for
`notice.md` hands `include` already-rendered HTML instead of the source, and
`<div class="td-code">` turns up in the Markdown output. Under `assets/` and
`content/` the name you write is the file you get. Non-Markdown files
(`.yaml`, `.sh`, `.txt`) never have this distinction.

## Including code files {#code}

`code=true` renders the file as a code block, and `lang=` sets the highlighting
language. Point it at a real file in the repository and the documentation cannot
drift from it.

```markdown {title="Source"}
{{</* include file="parts/module.yml" code=true lang="yaml" */>}}
```

{{< include file="parts/module.yml" code=true lang="yaml" >}}

Code blocks and fences share one pipeline: highlighting, line numbers and the
copy button all work. Fence attributes (`title=`, `collapse`, `hl_lines=`)
cannot be passed through; when you need them, write the content as an ordinary
[code block](/docs/code/).

## What a fragment can contain {#snippet-content}

A fragment is page-level Markdown rendered in the current page's context:
callouts, tables, lists, images, steps and shortcodes all work. The last line of
the fragment above — "The current release is v0.5.0" — is its
`{{</* param version */>}}` expanded on this page.

When two pages include one fragment, each renders it separately and each
generates its own heading anchors and code-block IDs. They do not collide.

> [!TIP] What makes a good fragment
> Install commands, connection strings, support matrices, legal notices:
> content that changes, and that must change everywhere at once. Content that
> appears on one page belongs on that page.

## Printing a site parameter {#param}

`param` prints one parameter: this page's front matter first, then the site
configuration — Hugo's `.Param` rule.

```markdown {title="Source"}
This site publishes {{</* param version */>}}, copyright from {{</* param copyright.from_year */>}},
and this page's front matter says `pigsty_pg_major: 18`, which reads back as {{</* param pigsty_pg_major */>}}.
```

This site publishes {{< param version >}}, copyright from {{< param copyright.from_year >}},
and this page's front matter says `pigsty_pg_major: 18`, which reads back as {{< param pigsty_pg_major >}}.

Nested keys join with `.`, so `copyright.from_year` reads
`params.copyright.from_year`. A parameter that does not exist, or whose value is
a map or a list rather than a scalar, fails the build instead of leaving a gap.

## Parameters inside commands, tables and links {#param-in-place}

`param` emits escaped plain text, so it can sit in a code fence, a table cell or
a link target. A version number in an install command is the obvious case:

````markdown {title="Source"}
```sh
hugo mod get github.com/pgsty/oink@{{</* param tdVersion.latest */>}}
```

| Item | Value |
| --- | --- |
| Current version | {{</* param version */>}} |
| Hugo floor | {{</* param hugoMinVersion */>}} |

[Release notes](https://github.com/pgsty/oink/releases/tag/{{</* param tdVersion.latest */>}})
````

```sh
hugo mod get github.com/pgsty/oink@{{< param tdVersion.latest >}}
```

| Item | Value |
| --- | --- |
| Current version | {{< param version >}} |
| Hugo floor | {{< param hugoMinVersion >}} |

[Release notes](https://github.com/pgsty/oink/releases/tag/{{< param tdVersion.latest >}})

Where site parameters are defined and which exist is in
[Configuration](https://oink.pgsty.com/docs/customize/config/); page parameters
are in [front matter](https://oink.pgsty.com/docs/write/frontmatter/).

## Notes deleted at build time {#comment}

A `comment` body appears in none of the four outputs — HTML, print, Markdown,
RSS. An HTML comment is different: it stays in the page source and reaches
`llms.txt`.

```markdown {title="Source"}
Since PostgreSQL 18, `pg_stat_io` breaks out WAL statistics.

{{</* comment */>}}
TODO: after v0.5 ships, bump the version above to 19 and add a pg_stat_io screenshot.
This text reaches no output at all, llms.txt included.
{{</* /comment */>}}

Verify the dashboards on a test database before upgrading.
```

Since PostgreSQL 18, `pg_stat_io` breaks out WAL statistics.

{{< comment >}}
TODO: after v0.5 ships, bump the version above to 19 and add a pg_stat_io screenshot.
This text reaches no output at all, llms.txt included.
{{< /comment >}}

Verify the dashboards on a test database before upgrading.

There is a comment between those two paragraphs, and viewing the page source
will not find it.

## Output {#outputs}

| Output | `include` (Markdown) | `include code=true` | `param` | `comment` |
| --- | --- | --- | --- | --- |
| HTML | The fragment renders as normal content | Highlighted code block + copy button | Escaped plain text | nothing |
| Print | As HTML | As HTML, without the copy button | As HTML | nothing |
| Markdown | The fragment's source, as written | A source fence | The value itself | nothing |
| RSS | As HTML | As HTML | As HTML | nothing |

In Markdown output a fragment is source rather than HTML, and shortcodes inside
it stay as `{{</* param version */>}}`. That is consistent with "Markdown output
keeps the source"; it is not a missed render. None of the three shortcodes loads
a script.

## Parameter reference {#reference}

`include` (named parameters only):

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `file` | path (required) | — | Resolution order in [Where the file comes from](#sources); a `..`, a missing file and an empty value all fail the build |
| `code` | boolean | `false` | `true` renders as a code block; it must be `code=true` — a quoted `code="true"` is a string and fails |
| `lang` | string | — | Code language; valid only with `code=true`, and fails on its own |
{.fields meta="type default"}

Any other parameter name fails the build, with the file and line in the error.

`param` (one positional parameter):

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| parameter name | string (required) | — | Nested keys join with `.`; page front matter first, then site `params`; missing or non-scalar (map / list) fails the build |
{.fields meta="type default"}

`comment` takes no parameters. It is used in pairs, and everything between
`{{</* comment */>}}` and `{{</* /comment */>}}` is discarded.

## Limits {#limits}

- `include` is not a template: you cannot pass variables to a fragment, include
  conditionally, or give the included code block fence attributes (`title=`,
  `collapse`). For per-platform variants, write two fragments and use
  [tabs](/docs/tabs/).
- Fragment languages are yours to maintain: `include` does no language
  fallback and takes the exact path you write. Share one fragment across
  languages — this page's Chinese translation includes the same English file —
  or write one per language and point each page at its own.
- `param` prints scalars only: structured data — version matrices, download
  lists — belongs in `data/` and is rendered by the matching component.
- `comment` is not "unpublish for now": the content is discarded on every build.
  To take a whole page down temporarily, use `draft: true`.
- Do not use `include` to build an index page: a page that pulls in ten
  fragments is a page where the reader wanted ten links.

## Related {#related}

- [Code blocks](/docs/code/) — every fence attribute, and the pipeline `include code=true` reuses
- [Tabs](/docs/tabs/) — per-platform or per-language fragments
- [Configuration](https://oink.pgsty.com/docs/customize/config/) — the site parameters `param` can reach
- [Front matter](https://oink.pgsty.com/docs/write/frontmatter/) — page parameters, which win over site configuration
