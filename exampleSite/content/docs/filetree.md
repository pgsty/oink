---
title: File trees
linkTitle: File trees
description: A `filetree` fence draws an annotated directory structure — aligned comment column, per-entry icons, collapsible directories, a draggable split.
weight: 90
search_keywords: [FileTree, directory tree, tree, repository layout, fence, icon, tone, open]
---

A file tree is a `filetree` fence whose body is the listing itself: indentation
is depth, a trailing `/` marks a directory, and everything after `#` is a
comment. Use it to explain the part of a directory structure that concerns the
reader, one annotation at a time. When the reader has to copy the listing
verbatim, use an ordinary code block.

## Shortest form {#minimal}

````markdown {title="Source"}
```filetree
- content/
  - _index.md
  - docs/
  - blog/
- hugo.yaml
- go.mod
```
````

```filetree
- content/
  - _index.md
  - docs/
  - blog/
- hugo.yaml
- go.mod
```

Bullets (`-`, `*`, `+`) may be omitted; the result is the same. An entry with
children is a directory. Without children, a trailing `/` tells the theme it is
one.

## Adding comments {#comments}

Everything after the first whitespace-preceded `#` on a line is a comment,
rendered as an aligned right-hand column. Comments are plain text, so Markdown
inside them shows literally; for a literal hash write `\#`.

````markdown {title="Source"}
```filetree
- content/          # every page, both languages in one directory
  - docs/          # the documentation tree you are reading
  - blog/           # release notes and articles
- assets/scss/      # the site's own SCSS, overriding theme variables
- layouts/          # site-level template overrides, the fewer the better
- static/images/    # images that need no build-time processing
- hugo.yaml         # site configuration: languages, menus, params.ui
```
````

```filetree
- content/          # every page, both languages in one directory
  - docs/          # the documentation tree you are reading
  - blog/           # release notes and articles
- assets/scss/      # the site's own SCSS, overriding theme variables
- layouts/          # site-level template overrides, the fewer the better
- static/images/    # images that need no build-time processing
- hugo.yaml         # site configuration: languages, menus, params.ui
```

Where the comment column starts is computed at build time from the widest row,
so every `#` begins at the same column whether or not the source lines up. The
comment column takes at most the right half of the panel and at least three
tenths. The dashed rule between them is a splitter you can drag, or focus with
<kbd>Tab</kbd> and move with the arrow keys (<kbd>Home</kbd> / <kbd>End</kbd> go
to the extremes).

Overlong names and comments are truncated with an ellipsis inside their own
column, and hovering shows the full text through `title`. The splitter is the
file tree's only JavaScript, and only a tree **with comments** loads it.

## Title bars {#title}

The fence attribute `{title="…"}` renders a title bar above the tree; without it
there is none.

````markdown {title="Source"}
```filetree {title="the oink.pgsty.com repository root"}
- content/          # pages
- assets/           # resources that take part in the build
- data/             # data for the home page, landings and downloads
- layouts/          # template overrides
- static/           # files copied verbatim
- tests/            # Playwright and node --test
- hugo.yaml
- go.mod            # the theme, imported as a Hugo Module
- Makefile          # make d / make b / make c
```
````

```filetree {title="the oink.pgsty.com repository root"}
- content/          # pages
- assets/           # resources that take part in the build
- data/             # data for the home page, landings and downloads
- layouts/          # template overrides
- static/           # files copied verbatim
- tests/            # Playwright and node --test
- hugo.yaml
- go.mod            # the theme, imported as a Hugo Module
- Makefile          # make d / make b / make c
```

## Indentation and depth {#indent}

Depth comes from indentation. Two spaces, four spaces, or tabs (counted as four
columns) all work and need not be consistent within one tree, as long as every
level you return to has been opened before. Output from the `tree` command can
be pasted whole, root line and summary line included — the summary is dropped.

````markdown {title="Source"}
```filetree
content/docs
├── about
│   ├── _index.md
│   └── features.md
├── components
│   ├── filetree.md
│   └── image
│       └── index.md
└── _index.md

3 directories, 5 files
```
````

```filetree
content/docs
├── about
│   ├── _index.md
│   └── features.md
├── components
│   ├── filetree.md
│   └── image
│       └── index.md
└── _index.md

3 directories, 5 files
```

Returning to an indentation level that was never opened fails the build, and the
error carries the line number inside the fence.

## Folding and explicit types {#dir-file}

A directory with children is open by default; `{open=false}` starts it closed.
Directories render as native `<details>`, so they are keyboard-operable without
JavaScript. `open` is valid on directories only. An entry with no children whose
name does not end in `/` is treated as a file; `{type=dir}` overrides that, and
`{type=file}` the other way.

````markdown {title="Source"}
```filetree {title="the content directory"}
- content/
  - docs/                # the documentation tree
    - components/         # 22 component pages    {open=false}
      - callout.md
      - filetree.md
      - image/            # page bundle: body + images  {type=dir}
    - customize/          # site-level configuration    {open=false}
      - config.md
  - blog/
    - release.md
```
````

```filetree {title="the content directory"}
- content/
  - docs/                # the documentation tree
    - components/         # 22 component pages    {open=false}
      - callout.md
      - filetree.md
      - image/            # page bundle: body + images  {type=dir}
    - customize/          # site-level configuration    {open=false}
      - config.md
  - blog/
    - release.md
```

## Icons and tones {#icon-tone}

Icons are inferred from the name: directories get a folder icon that follows the
open state; files are matched first by full filename (`LICENSE`, `Makefile`,
`go.mod`, `package.json`, `.gitignore` …), then by extension (`md yml toml json
sh py go js sql css png svg pdf zip` …), and otherwise get a generic file icon.

`{icon=…}` overrides it and takes exactly one Font Awesome class pair.
`{tone=…}` colours the icon, using the same vocabulary as
[badges](/docs/badge/): `neutral` `info` `success` `warning`
`danger`.

````markdown {title="Source"}
```filetree {title="deployment layout: permissions and what matters"}
- /etc/pigsty/                 # 0755 root:root · configuration root        {icon="fa-solid fa-server" tone=info}
  - pigsty.yml                 # 0644 root:root · cluster inventory
  - ca/                        # 0700 root:root · self-signed CA, never commit  {icon="fa-solid fa-lock" tone=danger open=false}
    - ca.key                   # 0600 root:root
- /var/lib/pgsql/18/data/      # 0700 postgres:postgres · data directory    {tone=warning}
  - postgresql.conf            # 0600 postgres:postgres
- /usr/bin/pig                 # 0755 root:root · command-line tool         {icon="fa-solid fa-terminal" tone=success}
```
````

```filetree {title="deployment layout: permissions and what matters"}
- /etc/pigsty/                 # 0755 root:root · configuration root        {icon="fa-solid fa-server" tone=info}
  - pigsty.yml                 # 0644 root:root · cluster inventory
  - ca/                        # 0700 root:root · self-signed CA, never commit  {icon="fa-solid fa-lock" tone=danger open=false}
    - ca.key                   # 0600 root:root
- /var/lib/pgsql/18/data/      # 0700 postgres:postgres · data directory    {tone=warning}
  - postgresql.conf            # 0600 postgres:postgres
- /usr/bin/pig                 # 0755 root:root · command-line tool         {icon="fa-solid fa-terminal" tone=success}
```

`tone` colours the icon only, never the text. Colour is a supplement; the
meaning belongs in the name or the comment.

## Linked entries {#link}

Write an entry name as `[name](link)` to make it a link. Site paths, relative
paths and `http(s):` all work, under the same URL validation as every other
component.

````markdown {title="Source"}
```filetree {title="this site's component pages"}
- content/docs/
  - [callout.md](/docs/callout/)     # callouts
  - [filetree.md](/docs/filetree/)   # this page
  - [gallery.md](/docs/gallery/)     # galleries
  - image/                                      # page bundle
    - [index.md](/docs/image/)       # images
- [hugo.yaml](https://github.com/pgsty/oink/blob/main/exampleSite/hugo.yaml)   # site configuration on GitHub
```
````

```filetree {title="this site's component pages"}
- content/docs/
  - [callout.md](/docs/callout/)     # callouts
  - [filetree.md](/docs/filetree/)   # this page
  - [gallery.md](/docs/gallery/)     # galleries
  - image/                                      # page bundle
    - [index.md](/docs/image/)       # images
- [hugo.yaml](https://github.com/pgsty/oink/blob/main/exampleSite/hugo.yaml)   # site configuration on GitHub
```

## One tree per platform {#tabs}

A fence carrying `tab=` (and `group=` / `value=`) becomes one panel of a
[tab set](/docs/tabs/) and can sit alongside code fences.

````markdown {title="Source"}
```filetree {tab="Linux" group="platform" value="linux"}
- /etc/pigsty/          # configuration
- /var/lib/pgsql/       # data
- /usr/bin/pig          # executable
```
```filetree {tab="macOS" value="macos"}
- ~/Library/Application Support/pigsty/   # configuration
- /opt/homebrew/bin/pig                   # executable
```
````

```filetree {tab="Linux" group="platform" value="linux"}
- /etc/pigsty/          # configuration
- /var/lib/pgsql/       # data
- /usr/bin/pig          # executable
```
```filetree {tab="macOS" value="macos"}
- ~/Library/Application Support/pigsty/   # configuration
- /opt/homebrew/bin/pig                   # executable
```

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | `<div class="td-filetree">`, an optional title bar, directories as native `<details>`; a tree with comments also gets the draggable splitter, its only runtime |
| Print | The same tree, fully expanded, no splitter, comments wrapped instead of truncated |
| Markdown | The `filetree` fence, emitted as written |
| RSS | The fence source inside a `<pre>` |

Below the `sm` breakpoint the layout collapses to a single column: comments move
under the name, stop being truncated, and the splitter is hidden. A tree without
comments is single-column and loads no script at all.

## Parameter reference {#reference}

Fence attributes, after ```` ```filetree ````:

| Attribute | Type | Default | Description |
| --- | --- | --- | --- |
| `title` | plain text | — | Title bar above the tree; omitted when absent; must not be empty |
| `tab` | plain text | — | Makes this tree one panel of a tab set |
| `group` / `value` | string | — | Tab group and sync value; must appear with `tab` |
| `class` | class list | — | Passed through for site CSS |
{.fields meta="type default"}

Entry attributes, in the `{…}` at the end of a line:

| Attribute | Type | Default | Description |
| --- | --- | --- | --- |
| `icon` | Font Awesome class pair | matched by name / extension | For example `fa-solid fa-lock`; a malformed value fails the build |
| `tone` | enum | `neutral` | `neutral` `info` `success` `warning` `danger`; colours the icon only |
| `open` | boolean | `true` | Directories only; `false` starts it closed |
| `type` | enum | inferred | `dir` or `file`, overriding the inference |
{.fields meta="type default"}

The line syntax itself:

| Element | Description |
| --- | --- |
| Indentation | Two spaces / four spaces / tabs / the `│ ├── └──` drawing from `tree` |
| `- name` | The bullet is optional; `-`, `*` and `+` are equivalent |
| `name/` | A trailing slash marks a directory; the name renders as written, slash kept |
| `[name](url)` | A linked entry |
| `# comment` | Everything after the first whitespace-preceded `#`; `\#` is a literal hash |
| `N directories, M files` | The `tree` summary line, dropped automatically |
{.fields}

Unknown attributes, unknown values, `open` on a file, a malformed `{…}`, and
returning to an indentation level that was never opened all fail the build with
the line number inside the fence.

## Limits {#limits}

- The `filetree` fence is the only form: there is no `{.filetree}` list marker
  and no shortcode.
- Names and comments are plain text: `**bold**` shows literally, so the fence
  source reads correctly anywhere.
- Nothing is read from disk: the tree is static content you write or paste, and
  it does not follow the repository.
- No search, no multi-select, no copy-the-whole-tree: when the reader has to
  copy it verbatim, use a code block.
- The split position is not persisted: after a reload it returns to the width
  computed at build time.

## Related {#related}

- [Code blocks](/docs/code/) — listings meant to be copied verbatim
- [Tabs](/docs/tabs/) — one tree per platform, side by side
- [Badges](/docs/badge/) — `tone` uses the same vocabulary
- [Organizing content](https://oink.pgsty.com/docs/write/organize/) — how a real content directory is laid out
