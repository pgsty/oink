---
title: Code blocks
linkTitle: Code blocks
description: A plain Markdown fence plus one attribute line gives you a filename title, exact copy, line numbers, highlighting, wrapping, folding and linkable lines.
icon: fa-solid fa-code
weight: 30
search_keywords: [Code Block, fence, copy, lineNos, hl-lines, collapse, wrap, Chroma, syntax highlighting]
---

A code block is an ordinary Markdown fence. Highlighting is done at build time
by Chroma, which Hugo embeds; there is no highlighter in the browser. Use it for
commands, configuration snippets and source. The `{…}` attributes on the fence's
info line decide the title bar, copy behaviour, line numbers and line anchors.
Diagram-style fences (`mermaid`, `echarts`, `filetree` and friends) never take
this path — each has its own render hook.

## Shortest form {#minimal}

````markdown {title="Source"}
```sql
SELECT datname, numbackends FROM pg_stat_database ORDER BY numbackends DESC;
```
````

```sql
SELECT datname, numbackends FROM pg_stat_database ORDER BY numbackends DESC;
```

A fence with no attributes still gets the full shell and a copy button. Without
a title there is no empty bar: the copy button floats at the top right and
appears on hover or when focus enters the block, and is always visible on touch
devices. The shell does not display the language; the lexer name goes into
`data-language` for stylesheets and tests.

The language tag is simply Chroma's lexer name. A `diff` fence renders a patch
with Chroma's added / removed line styling, no extra component involved:

````markdown {title="Source"}
```diff {title="a change to hugo.yaml"}
 params:
   ui:
-    sidebar_menu_compact: true
+    sidebar_menu_compact: false
     sidebar_menu_foldable: true
```
````

```diff {title="a change to hugo.yaml"}
 params:
   ui:
-    sidebar_menu_compact: true
+    sidebar_menu_compact: false
     sidebar_menu_foldable: true
```

## Filename titles {#title}

`title` gives the block a visible title bar, usually a filename or a path. It
also becomes the block's accessible name.

````markdown {title="Source"}
```yaml {title="hugo.yaml"}
markup:
  goldmark:
    parser:
      attribute:
        block: true
    renderer:
      unsafe: true
```
````

```yaml {title="hugo.yaml"}
markup:
  goldmark:
    parser:
      attribute:
        block: true
    renderer:
      unsafe: true
```

`filename` is a historical alias of `title`; writing both fails the build.

## Line numbers, start line and highlighting {#line-numbers}

`lineNos` takes `inline` (numbers in the same column as the code) or `table`
(numbers in their own column, selectable on their own and never copied).
`lineNoStart` changes the first displayed number. `hl_lines` marks lines to
emphasize, counted from 1 over the source lines inside the fence, independent of
`lineNoStart`.

````markdown {title="Source"}
```ini {title="postgresql.conf" lineNos="inline" lineNoStart=120 hl_lines="2 4-5"}
shared_buffers = 8GB
max_connections = 200
work_mem = 64MB
wal_level = replica
max_wal_senders = 10
```
````

```ini {title="postgresql.conf" lineNos="inline" lineNoStart=120 hl_lines="2 4-5"}
shared_buffers = 8GB
max_connections = 200
work_mem = 64MB
wal_level = replica
max_wal_senders = 10
```

`lineNos="table"` puts the numbers in a separate column — in both modes the
copy button strips them:

````markdown {title="Source"}
```bash {title="deployment in three commands" lineNos="table"}
./configure -c rich
./install.yml
pig ext install pg_duckdb
```
````

```bash {title="deployment in three commands" lineNos="table"}
./configure -c rich
./install.yml
pig ext install pg_duckdb
```

`tabWidth` decides how many spaces a tab expands to and, like `style`, is handed
straight to Chroma. This site uses class-based Chroma palettes (one for light,
one for dark), so `style` only takes effect when Hugo is switched back to inline
style mode.

## Wrapping long lines {#wrap}

`wrap=true` changes display only: the source is unchanged and so is the text you
copy. Without it, long lines scroll horizontally.

````markdown {title="Source"}
```text {title="config/artifacts.env" wrap=true}
ARTIFACT_URL=https://repo.pigsty.io/pkg/infra/v3.6.0/infra-pkg-v3.6.0.el9.x86_64.tgz
CHECKSUM=sha256:6d3dce4f7acb18f586469adcb80ab35f3e859f9837786e151cfbc2b3c0f587b2
```
````

```text {title="config/artifacts.env" wrap=true}
ARTIFACT_URL=https://repo.pigsty.io/pkg/infra/v3.6.0/infra-pkg-v3.6.0.el9.x86_64.tgz
CHECKSUM=sha256:6d3dce4f7acb18f586469adcb80ab35f3e859f9837786e151cfbc2b3c0f587b2
```

`wrap=true` cannot coexist with table line numbers: the number column and the
code column are two table cells, and wrapping puts them out of step. Writing
both fails the build, and the error suggests `lineNos="inline"` or dropping the
wrap.

## Folding long code {#collapse}

`collapse=N` shows the first N lines with a "show all N lines" button at the
bottom. The server emits the complete code; folding is a visual clip applied
after the browser measures where line N ends. Without JavaScript, in a screen
reader, and in print, the code is complete.

````markdown {title="Source"}
```yaml {title="hugo.yaml" collapse=8}
baseURL: https://oink.pgsty.com/
title: OINK
defaultContentLanguage: en
languages:
  en:
    languageName: English
    weight: 1
  zh:
    languageName: 简体中文
    weight: 2
params:
  offline_search: true
  ui:
    sidebar_menu_foldable: true
```
````

```yaml {title="hugo.yaml" collapse=8}
baseURL: https://oink.pgsty.com/
title: OINK
defaultContentLanguage: en
languages:
  en:
    languageName: English
    weight: 1
  zh:
    languageName: 简体中文
    weight: 2
params:
  offline_search: true
  ui:
    sidebar_menu_foldable: true
```

When the block is no longer than `collapse`, no button appears. Wrapping and
folding work together: folding measures the bottom edge of the Nth source line
node, so a wrapped line is never cut in half.

## What gets copied {#copy}

By default the whole source is copied. Terminal sessions — the `console` and
`shell-session` lexers — copy the commands only: prompted lines survive, the
prompts themselves and the output lines are dropped. Copying the block below
gives two commands, with no `$` and no output.

````markdown {title="Source"}
```console
$ pig ext list duckdb
name       version  category
pg_duckdb  1.0.0    OLAP
$ pig ext install pg_duckdb
INFO installing pg_duckdb
```
````

```console
$ pig ext list duckdb
name       version  category
pg_duckdb  1.0.0    OLAP
$ pig ext install pg_duckdb
INFO installing pg_duckdb
```

To copy prompts and output too, write `copy="all"`. Using `copy="command"` on an
ordinary lexer such as `bash` or `sh` fails the build, because those cannot tell
prompt, command and output apart. For multi-line commands, write the
continuation prompt (usually `>`) on the continuation lines, or they are treated
as output and excluded.

When a session-lexer block contains no prompt at all, the copy button reports
failure: the icon turns to its error state, an error is logged to the console,
and the clipboard is untouched. It never falls back to copying everything.

`copy=false` removes the copy button from one block — useful for a
counter-example nobody should paste:

````markdown {title="Source"}
```yaml {title="counter-example: the attribute line left its block" copy=false}
params:
  ui:
    image_zoom: true   # wrong: image_zoom is a table, not a boolean
```
````

```yaml {title="counter-example: the attribute line left its block" copy=false}
params:
  ui:
    image_zoom: true   # wrong: image_zoom is a table, not a boolean
```

To turn copying off site-wide use `params.ui.code_copy: false`, which overrides
whatever a block writes in `copy` (see
[Configuration](https://oink.pgsty.com/docs/customize/config/)). The copy button
is icon-only; success and failure swap the icon and announce a localized status.
What is copied keeps indentation, blank lines and Unicode, drops line numbers,
and ends with exactly one newline.

## Line links and stable IDs {#line-links}

Turning "see line 3" into a link takes two steps: give the fence an explicit
`id`, then enable `anchorLineNos=true`. The line numbers become anchor links of
the form `#<id>-<line>`.

````markdown {title="Source"}
```sql {id="ex-explain" title="explain.sql" lineNos="table" anchorLineNos=true}
EXPLAIN (ANALYZE, BUFFERS)
SELECT relname, n_live_tup
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
ORDER BY n_live_tup DESC;
```

Jump to [line 4](#ex-explain-4).
````

```sql {id="ex-explain" title="explain.sql" lineNos="table" anchorLineNos=true}
EXPLAIN (ANALYZE, BUFFERS)
SELECT relname, n_live_tup
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
ORDER BY n_live_tup DESC;
```

Jump to [line 4](#ex-explain-4).

Without an `id` the theme still generates one that is unique on the page, but it
depends on where the fence sits in the page — insert another fence above it and
the ID changes. Only an author-written `id` is a permanent link. IDs must not
contain whitespace or control characters, and must not collide with any other
viewport, tab, panel, title or line-anchor ID on the page; a collision fails the
build.

## Numbered examples {#numbered}

In a book or a long manual, number the snippets: `num` plus `caption` turns the
fence into a Book "example" target that `xref` can reference and that appears in
the book-wide list of examples. The number is written by the author — the theme
never counts — and `id` defaults to `eg-<num>`.

````markdown {title="Source"}
```sql {num="4-1" caption="Bloat ratio per table" #eg-bloat}
SELECT schemaname, relname, n_dead_tup, n_live_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > n_live_tup * 0.2;
```

See {{</* xref eg="4-1" anchor="eg-bloat" */>}}.
````

```sql {num="4-1" caption="Bloat ratio per table" #eg-bloat}
SELECT schemaname, relname, n_dead_tup, n_live_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > n_live_tup * 0.2;
```

See {{< xref eg="4-1" anchor="eg-bloat" />}}.

`num` and `caption` must appear together; one without the other fails the build.
`num` is mutually exclusive with the tab attribute `tab`. For numbering and
indexing figures, tables and equations, see
[publishing books](https://oink.pgsty.com/docs/write/book/).

## A set of fences as tabs {#tabs}

Consecutive fences carrying `tab` are assembled into one tab set in the browser.
A `group` on the first fence makes the set shareable, synchronized and
remembered.

````markdown {title="Source"}
```bash {tab="Homebrew" group="oink-install" value="brew"}
brew install hugo
```
```bash {tab="APT" value="apt"}
sudo apt install hugo
```
````

```bash {tab="Homebrew" group="oink-install" value="brew"}
brew install hugo
```
```bash {tab="APT" value="apt"}
sudo apt install hugo
```

The complete rules — group syntax, URL hash, cross-group synchronization, tabs
in running text — are on the [Tabs](/docs/tabs/) page.

## Things that bite {#pitfalls}

- Showing a shortcode in the docs: a fence does not stop Hugo from parsing, so a
  `{{</* tabs */>}}` written inside a code block still executes. To display it
  verbatim, add a comment marker inside each delimiter —
  <code>&#123;&#123;&lt;/&#42; tabs &#42;/&gt;&#125;&#125;</code>, and
  <code>&#123;&#123;%/&#42; steps &#42;/%&#125;&#125;</code> for the percent
  form. Every shortcode shown on this page is written that way.
- Fences inside fences: four backticks outside, three inside — every "Source"
  block on this page does it. Add another backtick when the inner block has
  fences of its own.
- Attributes go on the info line: a fence's attributes follow the language on
  the opening line. Only tables and images take their attributes on the line
  below. Put them on the next line and you get a visible line of braces.
- Unknown attributes fail rather than being ignored, and the error lists the
  allowed names. `style`, `srcdoc` and `on*` are rejected; the `data-td-code*`
  prefix plus `data-language`, `data-line-count` and `data-collapse-lines` are
  reserved by the theme and fail the build too.
- Fences in list items: indent them to line up with the item's content (three
  spaces after `1.`), or the fence leaves the list.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | A `<div class="td-code">` shell around Chroma's `.highlight`/`.chroma`; copy and fold buttons ship `hidden` and appear once the script confirms it can run |
| Print | Complete code; copy, fold and the fade are removed; long blocks may break across pages; the title bar stays |
| Markdown | The source fence, `{…}` attributes and all, emitted as written |
| RSS | A static code block with no buttons |

A page with no copy or fold control never loads `code-block.js`; print, Markdown
and RSS never load it.

## Parameter reference {#reference}

Inside the `{…}` after the language on the opening line, OINK's own attributes:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `title` | non-empty string | none | The visible title bar (usually a filename) and the accessible name |
| `filename` | non-empty string | none | Historical alias of `title`; both together fail the build |
| `copy` | `all` `command` `true` `false` | `command` for session lexers, `all` otherwise | `true` is `all`; `command` is allowed only on `console`/`shell-session` |
| `wrap` | boolean | `false` | Visual wrapping, source unchanged; mutually exclusive with table line numbers |
| `collapse` | positive integer | none | Lines shown initially; ignored when the block is shorter |
| `label` | non-empty string | derived from the title | Accessible name, not displayed; mutually exclusive with `aria-label` |
| `id` | non-empty token | generated | Stable block ID and line-anchor prefix; no whitespace |
| `tab` | non-empty string | none | Tab label, see [Tabs](/docs/tabs/); mutually exclusive with `num` |
| `group` | `^[a-z][a-z0-9_-]*$` | none | On the first fence of a set; enables hash / sync / persistence; requires `tab` |
| `value` | `^[a-z0-9][a-z0-9_-]*$` | none | Required on every fence of a group, forbidden without one; requires `tab` |
| `num` | `[0-9A-Za-z.-]+` | none | Numbered example (Book `eg`); must appear with `caption` |
| `caption` | plain text | none | The numbered example's caption; must appear with `num` |
| `class` | class list | none | Appended to the `.td-code` root element |
| `data-*` / `aria-*` / `role` | string | none | Passed through to the root element |
{.fields meta="type default"}

`title`, `filename` and `label` already give the block an accessible name and
`role="group"`. Any of them together with `aria-label`, `aria-labelledby` or
`role` fails the build; those three attributes pass through only when the block
has neither a title nor a `label`.

The same line also takes Chroma options, which the theme hands to Hugo unchanged:

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `lineNos` | `false` `inline` `table` | `false` | Line-number style; `table` is mutually exclusive with `wrap=true` |
| `lineNoStart` | positive integer | `1` | First displayed number; does not affect how `hl_lines` counts |
| `hl_lines` | lines and ranges | none | For example `"2 4-5"`, counted over the source lines in the fence |
| `anchorLineNos` | boolean | `false` | Line numbers become anchor links prefixed with the block's `id` |
| `tabWidth` | positive integer | Hugo's default | Spaces a tab expands to |
{.fields meta="type default"}

## Limits {#limits}

- No swapping the highlighter: there is no Shiki, no Twoslash, no
  browser-side highlighting and no runnable playground. For patches use a `diff`
  fence — Chroma's `.gi`/`.gd` are the added / removed line styles.
- `copy="command"` recognizes session lexers only: on any other language it is a
  build error, never a silent fallback to copying everything.
- A generated ID is not a permanent link: write `id` when you intend to share
  one.
- `mermaid`, `math`, `chem`, `markmap`, `plantuml`, `echarts`, `infographic`,
  `checksums`, `filetree` and `gallery` are not code blocks: each has its own
  render hook, no shell around it and no copy button.

## Related {#related}

- [Tabs](/docs/tabs/) — the full rules for assembling adjacent fences
- [Include](/docs/include/) — pull a real file from the repository in as a code block
- [Publishing books](https://oink.pgsty.com/docs/write/book/) — numbered examples, cross references, the list of examples
- [Print](https://oink.pgsty.com/docs/customize/print/) — what long code looks like on paper
