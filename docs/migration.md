# OINK 0.4 to 0.5 migration

This is the maintained source/configuration migration boundary. It is not a
release-state ledger; local source, commit, tag, push, consumer pin, deployment,
and production parity must be recorded separately.

## Content

| Removed form | Current form | Toolkit key |
| --- | --- | --- |
| `alert`, `details`, `pageinfo`, raw disclosure patterns | `> [!TYPE]` callout | `callout` |
| `tabpane`/legacy `tab`, `code-group`, `code-tab` | adjacent `{tab=}` blocks or `tabs`/`tab` | `tabs` |
| FileTree shortcodes or `{.filetree}` list | `filetree` fence | `filetree` |
| Gallery shortcodes or `{.gallery}` list | `gallery` fence | `gallery` |
| ECharts / infographic shortcode | same-named data fence | `datafence` |
| Docsy card families | `.cards` list or `cards`/`card` | `cards` |
| `imgproc`, `image` | Markdown image + attributes | `image` |
| `readfile` | `include` | `include` |
| fence `filename=` | `title=` | `fencetitle` |
| `badge outline=` | remove `outline` | `badge` |
| leaf `example`, `book-figures kind=` | `eg`, explicit `book-*` index | `eg` |
| percent-delimited fields | angle-delimited `fields`/`field` | `fieldsdelim` |

The standard toolkit is dry-run first and idempotent:

```sh
python3 scripts/migrations/oink06.py report --sites <dir>... --md report.md --json report.json
python3 scripts/migrations/oink06.py migrate --site <dir>
python3 scripts/migrations/oink06.py migrate --site <dir> --write
python3 scripts/migrations/oink06.py check --site <dir>
```

Ambiguous content is reported with its position and left unchanged. Text in
code fences is not rewritten. The separate `book_figures.py` profiles preserve
the known TPME, DDIA v1/v2, and pg-internal one-time migrations; they are not a
generic parser for unknown site conventions.

## Configuration

The build names replacements for stale keys. Main moves:

| Old | Current |
| --- | --- |
| `offlineSearch*` | `offline_search*` |
| `disable_click2copy_chroma` | `ui.code_copy` (inverted) |
| `content_width` | `reading_width: slim | normal | wide` |
| `github_url` | `github_repo` |
| `ui.no_left_sidebar` | `ui.sidebar_enabled` (inverted) |
| breadcrumb enable/disable aliases | `ui.breadcrumb` |
| `ui.scrollSpy` | `ui.scroll_spy` (inverted) |
| `ui.showLightDarkModeMenu` | `ui.dark_mode.show_menu` |
| `ui.readingtime` | `ui.reading_time` |
| `ui.ul_show` | `ui.sidebar_expand_levels` |
| `ui.docs_root` | `ui.docs_sidebar_root` |
| `ui.pager` | `ui.pager_types` |
| `{ enable: bool }` maps for annotation/zoom/keyboard/reading | bare booleans |
| `ui.typography.preset` | `ui.typography` |
| `print.disable_toc` | `print.toc` (inverted) |

Prism, `rss_sections`, and `algolia_docsearch` are removed. Chroma is the only
highlighter; Algolia configuration lives under `search.algolia`.

Page overrides drop the `ui.` prefix. For example:

```yaml
cascade:
  type: docs
  feedback: true
  comments: true
  navbar_autohide: true
  image_zoom: true
```

Legacy front matter such as `hide_feedback`, `hide_readingtime`,
`exclude_search`, `content_width`, camelCase manual-link fields, and a nested
`ui:` map fails with a replacement.

## Site prerequisites

Enable Goldmark unsafe rendering, block attributes, and standalone block images
as shown in [components.md](components.md). Enable passthrough explicitly when
using `\(...\)`, `\[...\]`, or `$$...$$`; Hugo does not merge theme markup
configuration into a consumer.

Local search remains off during `hugo server` unless
`offline_search_on_serve` is true. Feedback emits `docs_feedback` through an
existing analytics function, uses no submission endpoint, and does not replace
Giscus. Sites changing provenance should override `page-annotation.html`, not a
whole page template.

## Validation

Run the source checks, both supported Hugo versions, JS tests, strict root and
`/preview/` builds, and the output goldens. For a maintained site, also inspect
English/Chinese Docs and Blog roots/leaves at desktop and narrow widths, then
record consumer pin, deployment, and hosted parity separately.
