# OINK migration boundary

This is source and configuration guidance, not a release ledger. Local source,
commit, tag, push, consumer pin, deployment, and production parity remain
separate states.

## Toolkit scope

`bin/migrations/oink06.py` only scans and automatically rewrites Markdown files
under a site's content directory, including supported YAML front matter. It
does not rewrite Hugo configuration, data files, layouts, assets, modules, or
generated output. TOML/JSON front matter and ambiguous Markdown are reported
with positions for manual review.

Dry-run is the default and a completed migration is idempotent:

```sh
python3 bin/migrations/oink06.py report --sites <dir>... --md report.md --json report.json
python3 bin/migrations/oink06.py migrate --site <dir>
python3 bin/migrations/oink06.py migrate --site <dir> --write
python3 bin/migrations/oink06.py check --site <dir>
```

Code fences are not rewritten. `book_figures.py` retains narrow TPME, DDIA
v1/v2, and pg-internal profiles; it is not a generic parser.

## 0.4 content to current forms

| Removed form | Current form | Toolkit key |
| --- | --- | --- |
| `alert`, `details`, `pageinfo`, raw disclosure | `> [!TYPE]` callout | `callout` |
| `tabpane`, legacy `tab`, `code-group`, `code-tab` | adjacent `{tab=}` blocks or `tabs` / `tab` | `tabs` |
| FileTree shortcodes or `{.filetree}` list | `filetree` fence | `filetree` |
| Gallery shortcodes or `{.gallery}` list | `gallery` fence | `gallery` |
| ECharts / infographic shortcode | same-named data fence | `datafence` |
| Docsy card families | `.cards` list or `cards` / `card` | `cards` |
| `imgproc`, `image` | Markdown image + attributes | `image` |
| `readfile` | `include` | `include` |
| fence `filename=` | `title=` | `fencetitle` |
| `badge outline=` | remove `outline` | `badge` |
| leaf `example`, `book-figures kind=` | `eg`, explicit `book-*` index | `eg` |
| percent-delimited fields | angle-delimited `fields` / `field` | `fieldsdelim` |
| Docsy `_param` placeholders and `card header=` highlights | Font Awesome / `badge` / `param` or callout | `param_placeholders` |
| unsupported legacy shortcodes | manual review with source position | `reportonly` |

## Configuration and front matter

The following configuration changes are manual; the toolkit may report matching
front-matter keys but never edits site configuration.

| Old | Current |
| --- | --- |
| `offlineSearch*` | `offline_search*` |
| `disable_click2copy_chroma` | `ui.code_copy` (inverted) |
| `content_width` | `reading_width: slim | normal | wide` |
| `github_url` | `github_repo` |
| `ui.no_left_sidebar` | `ui.sidebar_enabled` (inverted) |
| breadcrumb aliases | `ui.breadcrumb` |
| `ui.scrollSpy` | `ui.scroll_spy` (inverted) |
| `ui.showLightDarkModeMenu` | `ui.dark_mode.show_menu` |
| `ui.readingtime` | `ui.reading_time` |
| `ui.ul_show` | `ui.sidebar_expand_levels` |
| `ui.docs_root` | `ui.docs_sidebar_root` |
| `ui.pager` | `ui.pager_types` |
| `{ enable: bool }` annotation/zoom/keyboard/reading maps | bare booleans |
| `ui.typography.preset` | `ui.typography` |
| `print.disable_toc` | `print.toc` (inverted) |

Prism, `rss_sections`, and `algolia_docsearch` are removed. Chroma is the only
highlighter; Algolia configuration is `search.algolia`. Page overrides drop the
`ui.` prefix. Legacy `hide_feedback`, `hide_readingtime`, `exclude_search`,
`content_width`, camelCase manual links, and nested front-matter `ui` maps are
reported with replacements.

## 0.5 to 0.6

- Replace `upstream_attribution` with `upstream_link` plus
  `upstream_name`, `upstream_copyright`, `upstream_license`, and
  `upstream_notice`; rename `downstream_modified` to `upstream_modified`.
- Replace the `release` map with one GitHub `release_url`; remove
  `release_products` and `release_group_by_product` from release indexes.
- Blog and default dates now default to ISO `2006-01-02`; retain explicit
  `time_format_blog` or `time_format_default` for prose dates.

Removed names warn and take the documented safe fallback or render nothing;
ordinary previews continue, while `--panicOnWarning` rejects them at a strict
gate. `blog_index_toggle`, `featured_image: hero`, `toc_style`, and
`toc_taxonomies` are additive opt-ins. They introduce no content type;
immersive reading stays on the ordinary blog shell.

## Prerequisites and validation

Enable Goldmark unsafe rendering, block attributes, and standalone block images
as shown in [components.md](components.md). Enable passthrough explicitly for
`\(...\)`, `\[...\]`, or `$$...$$`; Hugo does not merge theme markup config.

Run the smallest source and output checks for the changed contract, both
supported Hugo versions, JS tests when runtime changes, and strict root and
subpath builds. For maintained sites, inspect representative EN/ZH Docs and
Blog routes at desktop and narrow widths, then record pin, deployment, and
hosted parity separately.
