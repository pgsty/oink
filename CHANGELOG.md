# Changelog

All notable changes to OINK are documented here. The project follows
[Semantic Versioning](https://semver.org/) for published tags.

## Unreleased

### Added

- Upstream attribution in the page annotation. A site that vendors third-party
  documentation had to reimplement the notice itself: the two keys OINK
  shipped, `upstream_attribution` and `downstream_modified`, rendered a bare
  link and a fixed sentence, so every consumer wrote its own partial with the
  project name, copyright, and licence hard-coded and untranslatable. The
  annotation now resolves its lines from front matter through
  `annotation-items.html` and renders one attribution line that names the work,
  the copyright, the licence, and whether the page was changed, each linked and
  each translated. `upstream_modified` adds no second line: the verb carries
  the indication the licence asks for -- material is credited, or *adapted
  from* its source -- and the credit gains a link to the page's commit history.
  `upstream_link` is the one per-page fact; `upstream_name`,
  `upstream_copyright`, `upstream_license` (an SPDX identifier resolved
  through the new `data/licenses` table), `upstream_notice`, `upstream_ref`,
  and `upstream_modified` resolve from site params, the `data/upstreams` entry
  named by `upstream_source`, or the page, most specific last -- so a vendored
  tree declares its constants once in a cascade and each page adds a line.
  Because the constants normally cascade, a page inside such a tree that
  carries no `upstream_link` fails the build instead of publishing an
  unattributed copy; `upstream_link: ""` is the deliberate opt-out. An
  incomplete attribution, an unknown SPDX identifier, and a non-boolean
  `upstream_modified` all fail the build for the same reason: a partial notice
  reads exactly like a complete one.
- A translation notice. `params.ui.translation_notice` takes the language code
  of the authoritative version; a page in another language that has a
  translation there says so and links to it, and `translation_notice: false`
  opts out a page written natively in this language. No front matter is needed
  for the common case. It is the annotation's one inferred line, so it is the
  one that carries a guard: a page with no authored text of its own -- a
  generated taxonomy or term list, a section index that is only a title and a
  child list -- has nothing to be a translation of and never shows it. The theme names no language in the
  string, and the switch cascades, so a partly translated site scopes the
  claim to the trees where it holds instead of asserting it site-wide.
- A card form for the blog index. `params.ui.blog_index: cards` renders a blog
  section's list page as a grid of the shared content cards --
  `params.ui.blog_index_columns` wide, two between the md and xl breakpoints,
  one below md -- instead of the row list, which stays the default. A site
  whose posts lead with an image had no way to show it at more than
  250x125 px; a card gives it a 16:9 crop above the title, the date and
  section line, and a three-line summary, and nothing else. Year grouping,
  pagination, and `manual_link` external semantics are the same in both forms,
  so the choice is presentational: the row output is unchanged to the byte.
  Front matter `blog_index` on the blog root, or its cascade, overrides the
  site value per section. The card's lead image goes through Hugo's `.Fill`
  whenever the resource can be processed, so a grid of posts does not download
  a full-size original per card. There is no reader-side switch between the
  forms, and term and taxonomy pages keep the row list.

### Changed

- `upstream_attribution` is now `upstream_link` and needs the companion keys
  above; `downstream_modified` is now `upstream_modified`. Both old names fail
  the build and name their replacement.
- The theme mounts `data/`, which it did not before, so the licence table
  reaches consuming sites. A site's own `data/licenses.yaml` merges over it.

### Fixed

- Show the brand mark beside a wordmark. A site that set `params.wordmark`
  rendered the wordmark *instead of* its logo in the navbar, the docs sidebar
  brand row, and the mobile subnav, with the mark demoted to a fallback that
  only appeared in the icon-mode range -- so a site whose wordmark is set in
  type, as wordmarks usually are, showed no mark at all at reading widths. The
  lockup is now the other way round, which is how a lockup degrades: the mark
  is the constant half and always renders, and the text half -- the wordmark,
  or the site title when there is none -- is what collapses when the row runs
  out of room. `td-nav-logo--fallback` and `td-shell-subnav__logo-fallback`
  are gone with the behaviour they named.
- Numbered examples frame their body. `eg` drew a caption bar and then left the
  listing outside it, so an example read as two unrelated blocks; the figure is
  now one framed unit whose caption is the header and whose body sits inside,
  with a single code block flush against the frame instead of drawing a second
  border.
- Refuse footnotes that cannot resolve. Hugo renders a shortcode body as its own
  Goldmark document, so `[^25]` in a `tbl`, `eg`, `card`, `tab`, `field`, or
  `include` body printed literally when the definition sat on the page, and
  built a second footnote list with colliding `fn:N` ids when it sat in the
  body. Both now fail the build and name the native form -- a table, image, or
  fence carrying `{num=… caption=…}` keeps its content in the page document,
  where footnotes number and link like any other page footnote. Footnote-shaped
  text inside code is untouched.
- List numbered Book objects in document order. The order key was derived from
  each target's source position, but Hugo renders a position as a quoted
  string, so the `file:line:col` match never fired and every target fell back
  to its ordinal -- which counts shortcodes and render hooks separately. A
  chapter that wrote one figure as `fig` and the next in native `{num=…}` form
  therefore listed Figure 1-2 before Figure 1-1 in the list of figures. The
  quotes now come off before matching. Identity stays keyed on the ordinal,
  which is what a print aggregate -- rendering the page from a string, with
  line numbers short by the front matter -- can still match.
- Namespace footnote IDs in whole-Book print. Goldmark numbers footnotes per
  page, so `fn:1` and `fnref:1` were emitted once per chapter into the single
  print document: a book whose chapters each carry references produced
  duplicate IDs, and every backlink resolved to whichever chapter happened to
  render first. The aggregate now prefixes them with the page the way it
  already prefixed heading IDs, leaving numbered `fig`/`tbl`/`eq`/`eg` anchors
  byte-stable.

## [0.5.0] - 2026-08-18

The component API v5 release. Content written for 0.4 needs migration:
`bin/migrations/oink06.py report --sites <dir>` inventories a site and
`… migrate --site <dir> --write` rewrites it. Configuration keys renamed here
fail the build with the new name rather than being silently ignored.

### Fixed

- Keep a landing FAQ question on one line of its own. The `<summary>` is a flex
  row holding the question and the toggle glyph, so a question carrying inline
  Markdown -- code, a link, emphasis -- spread each fragment across the row as a
  separate flex item. The question is now wrapped in one element that grows and
  wraps as text. In the navbar, text that sits beside a utility icon (the GitHub
  star count, the alternate-site label) took the 1rem icon box instead of the
  menu label's size and weight, and the alternate-site label had no gap after
  its icon. The sun glyph also carried the regular weight while the moon it
  swaps with carried the solid one.
- Share the featured image a page actually shows. Hugo's `opengraph.html`,
  `twitter_cards.html`, and `schema.html` resolve their images through the
  embedded `_partials/_funcs/get-page-images.html`, which the theme never
  reached -- so a post whose image came from the theme's own resolver rendered
  a thumbnail, emitted no `og:image`, and degraded to `twitter:card: summary`,
  the small text-only card on X and no preview on LinkedIn. The theme now
  overrides that one helper, so all three metadata templates stay Hugo's while
  `featured-image-resolve.html` decides for them: one precedence, one URL
  policy, one resource lookup, consumed by the blog list, the blog row, and the
  card metadata alike. A site deployed under a subpath is fixed with it -- Hugo
  reads a leading slash as the host root and the theme reads it as the site
  root, so the rendered image and the card used to disagree, and
  `featured-image.html` re-resolved an already-resolved href into a doubled
  prefix. `bin/check-output.py` now requires a card URL to name a file the build
  shipped and `og:image`, `twitter:image`, and `twitter:card` to agree. The card
  contract is one representative image, so every source kind consistently uses
  the first `images` entry. SVG and other non-processable Resources are framed
  without calling Hugo's raster-only `Fill` operation.
- Reach the dark palettes the vendored runtimes already ship. Swagger UI keys
  its own 256-rule dark theme on `html.dark-mode`, and Algolia DocSearch
  redefines its whole `--docsearch-*` token set under `html[data-theme='dark']`;
  the theme set neither, so both stayed on their light palettes over a dark
  page -- and because `.swagger-ui` paints no canvas of its own, that left its
  body text at 1.86:1. The resolved colour mode is now mirrored onto both
  switches, at first paint and on every later toggle, rather than forking
  either vendored stylesheet. Markmap has no such palette to reach: it
  highlights fenced code with highlight.js' light-only `default.min.css` and
  renders bare token spans without the `.hljs` wrapper, so the stylesheet's own
  background never lands and eight of its ten token groups sat below AA on the
  dark canvas, the worst at 1.85:1. Those roles are mapped onto the same
  github-dark values the code blocks use, so a snippet reads the same inside a
  mind map as in a fence. `bin/check-namespace.py` records both vendor switches
  next to the asciinema `--term-*` exception and fails if either mirror is
  dropped.
- Restore readable blockquote text inside highlighted Markdown in dark mode:
  the light Chroma palette is emitted at the root so code stays legible on
  sites without dark mode, and GitHub's dark style declares `GenericEmph`
  (`.ge`) with a font style but no colour, so the light near-black `#1f2328`
  survived onto the dark code canvas at a 1.22:1 contrast ratio. The dark
  palette now carries an explicit layer reset, and `bin/check-code-blocks.py`
  compares the two palettes property by property instead of only comparing
  which selectors exist.
- Scope the landing code plate to the dark palette. The plate keeps a dark
  canvas in both site themes, but carried no `data-bs-theme`, so in light mode
  the root Chroma palette painted light-mode token colours onto it -- YAML keys
  at 2.53:1 and punctuation at 1.22:1. `bin/check-landing.py` now requires every
  always-dark landing surface to declare its colour scheme locally.
- Restore the asciinema player's palette: the 1.0 namespace sweep renamed the
  player's own `--term-*` custom properties to `--td-term-*`, so
  `asciinema-player.css` fell back to its built-in black terminal inside the
  theme's light window chrome. These properties are the runtime's API, like
  Giscus' `data-*` attributes, and `bin/check-namespace.py` now records the
  exception and fails if the theme stops setting them.

### Changed

- Build the local search index and runtime under `hugo server` by default
  (`offline_search_on_serve`), so a preview behaves like the deployed site. Set
  it false on a site large enough for the indexing cost to slow the preview.
- Move repository checks, migration utilities, and measurement tools from
  `scripts/` to `bin/`; this is a tooling-path change and does not alter the
  Hugo Module surface.
- Consolidate the theme's local implementation notes into six current
  contracts and remove prose-only contract checks that duplicated behavioral
  tests and rendered goldens.
- Load authored task-list and raw-icon accessibility repair only on pages whose
  rendered content needs it; theme-generated icons carry their own semantics.
- Keep Draw.io configuration in `#td-drawio-config`, scan content images only,
  and fetch each distinct PNG/SVG source once per page.
- Make corpus/site build tools ignore only a vendored OINK copy while retaining
  other vendored dependencies, and tolerate Git fsmonitor sockets in worktree
  snapshots.
- Keep the published `exampleSite` focused on Docs, Blog, and a three-chapter
  bilingual Book example. Regression-only pages, media, and layout overrides
  now live under `tests/site/` and are mounted only by the check suite; shared
  public demonstrations use `static/images/oink.webp` and
  `static/images/releasenote.webp`.

### Removed

- **Breaking.** `default_featured`, in every position it was accepted: site
  params, a section `_index.md`, and a page's own front matter. Hugo's `images`
  already spans all three levels -- on the page, through a section `cascade`,
  and site-wide as `params.images` -- so the theme kept a second vocabulary for
  a question Hugo answers. Two of the old entry points also collided with each
  other: `params.default_featured` and `params.images` were both site-wide
  defaults, but only the first quietly gave every blog row a thumbnail. Replace
  a section default with `cascade: { images: [<path>] }` on its `_index.md`, a
  page default with `images: [<path>]`, and a site default with
  `params.images`; `default_featured: false` becomes `images: []`, which drops
  the inherited default for a page or a whole section. A bundled featured
  resource still applies, and without one the site card remains the metadata
  fallback. Both legacy registries fail the build and name the replacement.
- Drop the unused `code/namespace-html.html` partial and unemitted styles for
  retired Docsy taxonomy demos/pages and article teasers, the old `.td-sidebar`
  Algolia result layout, and the superseded `.td-main` flex shell.

- **Breaking.** The `image` shortcode. Every image is now the Markdown image
  `![alt](src)`, optionally followed by an attribute line carrying `#id`,
  `num`, `caption`, `width`, `height`, `link`, `command`, and `options`. One
  render hook resolves page resources, section resources, global assets, and
  static or remote paths for markdown images, `fig`, and configuration image
  sources alike. `bin/migrations/oink06.py migrate --only image` rewrites
  existing calls.
- **Breaking.** The Prism highlighting path, `params.prism_syntax_highlighting`,
  `static/js/prism.js`, and `static/css/prism.css`. Prism could not coexist
  with the attributes this theme's code blocks are built on — `tab`, `group`,
  `value`, `num`, and `caption` all require Chroma — so any site using tabs or
  numbered examples failed the build the moment it opted in, while every site
  paid 55 KB of published assets whether it enabled Prism or not. Chroma with
  `params.highlight_classes` is the only highlighter.
- **Breaking.** The `{.filetree}` and `{.gallery}` list markers, the
  `filetree`/`filetree-file`/`filetree-folder` and `gallery`/`gallery-image`
  shortcodes, `code-group`/`code-tab`, Docsy's `tabpane`/`tab`, `doc-cards`,
  `nav-cards`, Docsy's `card`/`cardpane`, `doc-carousel`, `imgproc`,
  `readfile`, `example`, `alert`, `pageinfo`, and `details`. (`card` survives
  as the child of `cards`, with a different contract.) Every replacement is
  listed in the migration table in `docs/components.md`.
- **Breaking.** `{{< badge outline= >}}`. There is one badge appearance.
- **Breaking.** `{{< book-figures kind= >}}` in favour of `book-tables`,
  `book-equations`, and `book-examples`.
- **Breaking.** The 0.x compatibility layer and the Docsy leftovers no site
  used. Gone: the 18 `_partials/home/**` adapters, `home-data.html`, and
  `outputformat.html` (call `landing/**` and read `tdOutputFormat` from the
  page store); the `td/code-dark`, `td/color-adjustments-dark`, and
  `td/gcs-search-dark` Sass shims and the never-imported `td/extra/` files;
  the Docsy community page (`layouts/community/`, `docs/community.html`,
  `community_links.html`, `params.links`, front matter `contributingUrl`, the
  `community_*` i18n keys) together with the `.td-box` box variants
  (`td/_boxes.scss`) and the paint-by-number palette classes (`td/_colors.scss`,
  `$td-box-colors`); the dead partials `taxonomy_terms_clouds.html`,
  `code/markdown-escape.html`, and `td/render-heading.html` (the remaining
  `taxonomy_terms_*` partials are `taxonomy-terms-*`); `params.algolia_docsearch`
  (fails the build naming `params.search.algolia`); the `home` data `footer`
  key as a footer source (fails the build naming `data/footer/<lang>.yaml`);
  the implicit `hero → metrics → capabilities → principles → cta` landing order
  when `data/home` has no `sections` (fails the build asking for `sections`);
  and `body_class: td-no-left-sidebar` as a second way to hide the sidebar
  (fails the build naming `ui.sidebar_enabled: false`). Build errors and
  `warnf` messages no longer point at documentation URLs of the old site
  information architecture.

### Added

- Landing section `preview`: a Markdown `source` beside what the theme
  renders from it. The rendered pane is the real renderer (`RenderString`
  through the site's hooks — callouts, `{.steps}`, adjacent-fence tabs, and
  fences all appear as on a docs page and register their runtimes); the
  source pane is Chroma-highlighted Markdown on the terminal surface. Markdown
  output emits the source as a fence; RSS omits Landing sections. Pane labels
  are theme i18n
  (`ui_preview_source`, `ui_preview_rendered`). `hero.align: center` is a
  text-only centred hero (the copy widens, the title balances; combining it
  with `hero.image` fails the build).
- Native Markdown forms for every content primitive, so most components no
  longer need a shortcode: `> [!TYPE]` callouts with optional folding and an
  `{icon=}` attribute; `{.steps}` and `{.cards}` list markers; the
  `{.fields}`, `{.matrix}`, `{.full-width}`, `{caption=}`, `{#id num=}`, and
  `{tab=}` table attributes; ```` ```filetree ````, ```` ```gallery ````,
  ```` ```echarts ````, ```` ```infographic ````, and ```` ```checksums ````
  data fences; adjacent fences with `{tab= group= value=}` for code tabs; and
  the numbered Book forms for figures, tables, equations, and examples. The
  29 remaining shortcodes are the full forms for the cases a Markdown block
  cannot express. `docs/components.md` is the authoring guide.
- One block-attribute policy shared by every render hook
  (`content/attributes.html`): allowlisted keys are consumed, `class` is token
  validated, `data-*` and `aria-*` pass through, and `style`, `on*`, and
  unknown keys fail the build.
- A content migration toolkit, `bin/migrations/oink06.py`, with
  `report` / `migrate` / `check` modes. It is dry-run by default and
  idempotent; `tests/migrations/` covers it.
- `bin/check-namespace.py`: every class the theme generates starts with
  `td-`, every data attribute with `data-td-`, every CSS custom property with
  `--td-`, and every JavaScript global with `Oink`. Third-party markup and the
  documented unprefixed author markers are allowlisted; nothing else is.
- Four-state goldens (HTML, print, Markdown, RSS, `llms.txt`) over 30 surfaces
  of the fixture site, plus output-structure, duplicate-ID, bundle-graph, and
  output-security checks.
- A heading render hook of the theme's own: every heading carries its id and
  a hover-revealed self-link (`.td-heading-self-link`, label
  `ui_heading_self_link`), and heading block attributes follow the shared
  policy. Sites no longer need a `render-heading.html` that calls
  `td/render-heading.html` (that partial is gone). Print and RSS output strip
  the self-link.
- CI builds a small consumer site in Hugo Module mode (the fixture site
  mounts the theme through a classic `themes/` symlink), so module-only path
  resolution such as the `include` shortcode's `os.ReadFile` is covered.

### Changed

- **Breaking.** Configuration keys converge on three rules ahead of the 1.0
  API freeze: a boolean
  switch is the bare feature name (`ui.annotation: true`, not
  `ui.annotation.enable` or `ui.annotation_enabled` — the only `_enabled`
  suffixes left are `ui.navbar_enabled`, `ui.sidebar_enabled`, and
  `ui.sidebar_root_enabled`, whose bare names would collide with sibling
  keys); a single-key map is flattened to a scalar, and the maps that stay
  (`comments`, `ui.feedback`, `ui.page_context_menu`, `ui.dark_mode`,
  `plantuml`, `drawio`, …) also accept a bare boolean; and a front matter key
  is the site key with its `ui.` prefix dropped, without exception. Keys are
  snake_case, positive, and named for what they do; camelCase survives only
  where a value is passed straight to an external runtime
  (`comments.giscus.*`, `mermaid.*`). Every old key or shape fails the build
  with its replacement rather than being silently ignored
  (`_partials/config-legacy.html` for site configuration,
  `_partials/front-matter-legacy.html` for pages), so upgrading is a matter
  of following the build errors one by one:

  | Old | New |
  | --- | --- |
  | `offlineSearch`, `offlineSearchIndex`, `offlineSearchMaxResults`, `offlineSearchOnServe`, `offlineSearchSummaryLength` | `offline_search`, `offline_search_index`, `offline_search_max_results`, `offline_search_on_serve`, `offline_search_summary_length` |
  | `ui.showLightDarkModeMenu: "enable-only (experimental)"` | `ui.dark_mode` (`true`, or `{ enable, show_menu }`) |
  | `ui.scrollSpy.disable` | `ui.scroll_spy` (inverted) |
  | `ui.no_left_sidebar` | `ui.sidebar_enabled` (inverted) |
  | `ui.breadcrumb_disable` | `ui.breadcrumb` (inverted) |
  | `print.disable_toc` | `print.toc` (inverted) |
  | `disable_click2copy_chroma` | `ui.code_copy` (inverted) |
  | `ui.readingtime.enable` | `ui.reading_time` |
  | `ui.ul_show` | `ui.sidebar_expand_levels` |
  | `Taxonomy.taxonomyCloud`, `.taxonomyCloudTitle`, `.taxonomyPageHeader` | `taxonomy.cloud`, `.cloud_title`, `.page_header` |
  | `ui.annotation.enable`, `ui.image_zoom.enable`, `ui.keyboard_nav.enable` | `ui.annotation`, `ui.image_zoom`, `ui.keyboard_nav` (bare booleans) |
  | `ui.typography.preset` | `ui.typography` (`technical` \| `system`) |
  | `ui.pager.types` | `ui.pager_types` |
  | `markmap.enable` | `markmap` |
  | `content_width` (`slim` \| `norm` \| `wide`) | `reading_width` (`slim` \| `normal` \| `wide`) |
  | `ui.docs_root` | `ui.docs_sidebar_root` |
  | front matter `context_menu` | `page_context_menu` |
  | front matter `params.ui.image_zoom.enable` | `image_zoom` |
  | front matter `hide_readingtime: true` | `reading_time: false` |
  | front matter `hide_feedback: true` | `feedback: false` |
  | front matter `exclude_search`, `excludeSearch` | `search_exclude` |
  | front matter `assistant_links` | `page_context_menu: { assistant_links: … }` |
  | front matter `manualLink`, `manualLinkTitle`, `manualLinkTarget`, `manualLinkRelref` | `manual_link`, `manual_link_title`, `manual_link_target`, `manual_link_relref` |
  | front matter `params.ui.<key>` (any) | `<key>` |
  | `github_url` | `github_repo` (the edit, history, and issue links are derived from it) |
  | `rss_sections` | removed; it was never read |

  `ui.code_copy: false` sets the site-wide *default* only: a fence that names
  `copy` explicitly still gets what it asks for (the old key silently overrode
  an explicit author value). Every theme default is now declared in the
  theme's `hugo.yaml` with its value range in a comment (`offline_search`,
  `offline_search_summary_length`, `ui.breadcrumb`, `ui.reading_time`,
  `ui.dark_mode`, `ui.docs_sidebar_root`, `ui.sidebar_icon_policy`,
  `ui.section_index_columns`, `print.toc`, `print.section_break_wordcount`,
  `markmap`, `plantuml.enable`, `drawio.enable`, `github_branch` were
  previously template-only fallbacks), except `ui.quick_links` and
  `ui.taxonomy_icons`, whose defaults are derived and documented as such;
  the template fallbacks for `ui.sidebar_expand_levels` (2) and
  `ui.sidebar_menu_truncate` (2000) now match the declared values. The
  unloaded Docsy `click-to-copy.js` runtime and its styles are gone.
  `bin/check-params.py` enforces the key rules and the legacy-key errors.

  Rule 3 has no exceptions any more. Every `params.ui.*` setting that a page
  may override — the Docsy sidebar family (`sidebar_menu_compact`,
  `sidebar_menu_foldable`, `sidebar_expand_levels`, `sidebar_width_*`,
  `sidebar_item_overflow`, `sidebar_headings`, `sidebar_enabled`),
  `section_index`, `section_index_columns`, `lastmod_commit`, `breadcrumb`,
  `scroll_spy`, `code_copy`, `keyboard_nav`, `book_draft_banner` — is read
  through one helper (`ui-param.html`) that takes the bare key from front
  matter or a cascade (`section_index: cards`), not `params.ui.section_index`.
  Front matter never carries a `ui:` block; one that does fails the build
  naming the bare key. Front matter `page_context_menu` mirrors the site key
  (a boolean, or `{ enable, assistant_links }`), replacing the top-level
  `assistant_links` page key. The last camelCase front matter keys,
  `manualLink`, `manualLinkTitle`, `manualLinkTarget`, and `manualLinkRelref`,
  are `manual_link`, `manual_link_title`, `manual_link_target`, and
  `manual_link_relref`; `bin/migrations/oink06.py migrate --only
  frontmatter` rewrites all of these page keys.
- **Breaking.** One naming namespace. Classes the theme generates are `td-`
  prefixed (`leaf`, `has-child`, `active-path`, `is-open`, `is-active`,
  `is-hidden`, `is-disabled`, `landing-header`, `landing-nav`,
  `landing-container`, `article-meta`, `pageinfo`, `nav-*`, `taxonomy-*`,
  `ul-N`, and the landing subsystem's `oink-*` set are gone); data attributes
  are `data-td-*`; CSS custom properties are `--td-*` (`--oink-*` and
  `--term-*` are gone); the ECharts extension point is
  `window.OinkEchartsFunctions`. The site header and nav are now
  `td-site-header` / `td-site-nav` / `td-site-container` — they style every
  page, not only a landing page, and the old names said otherwise.
  `check-namespace.py` keeps it that way.
- **Breaking.** Callout labels are namespaced i18n keys (`callout_note`,
  `callout_tip`, …). The theme no longer claims bare top-level keys such as
  `note`, `example`, or `quote` that a consuming site is just as likely to
  want. All 32 locales are updated.
- **Breaking.** The `swaggerui` shortcode is `swagger`, matching every other
  multi-word shortcode name.
- Three JavaScript bundles instead of one per flag combination. `js/actions.js`
  (the action registry and its two dependencies) and `js/core.js` (Bootstrap
  and the interactive shell) are byte-identical on every page, so a reader
  crossing pages with different feature sets keeps one cached copy; only a
  small `js/page-<key>.js` varies. ECharts is its own `<script>` rather than a
  megabyte inside an uncacheable bundle, matching how every other large vendor
  runtime already shipped. The per-page bundle name is derived from its members
  instead of a hand-maintained 21-argument `printf`, so adding a runtime can no
  longer collide two different feature sets on one file name. Over the fixture
  site this is 3.2 MB of JavaScript down to 1.8 MB.
- Print output loads 7.9 KB instead of 100 KB: it keeps the action runtime its
  "click to print" control needs and drops Bootstrap, the navbar, the sidebar,
  the palette, and the scroll spy, none of which a print view can use.
- Both sidebar sources — the content tree and an explicit `data/docs_nav.json`
  tree — render through one row partial, `shell/sidebar-node.html`. The two
  walkers keep their own tree traversal; everything a reader can see is now
  written once instead of being kept in sync by a check script.
- Every shortcode validates its parameters through
  `content/shortcode-params.html`, and the contract check fails if a new one
  does not. `asciinema`, `redoc`, `swagger`, `param`, `comment`, and `steps`
  previously accepted any parameter silently.
- Build failures follow one shape: `<component>: <subject> <expectation>;
  got <value> at <position>`, lower case throughout, one preposition for the
  location, and configuration errors naming the full `params.` path. The
  contract check enforces it.
- `llms.txt` reads the configured `params.ui.docs_section` instead of a
  hard-coded `docs`, and lists documentation pages with their descriptions
  rather than only top-level sections.
- Documentation is named for its subject rather than the internal planning
  document it came from: `navigation-contract.md`, `reading-release-contract.md`,
  `landing-contract.md`, `book-contract.md`, `keyboard-nav-contract.zh.md`,
  `docs-shell-contract.zh.md`, and `migration-{navigation,components,docs-shell}.md`.
  The check scripts and JavaScript tests are renamed to match. One-time
  site-specific migration work orders are no longer published with the theme.
- **Breaking.** Open Sans is gone (18 woff2 subsets, 652 KB, published to
  every site for a print-only body face). `--td-print-font-family` keeps its
  role but follows the body role in both presets; `$td-print-font-name` and
  `$td-enable-webfonts` no longer exist. A site that wants a different face
  on paper sets the role in its own stylesheet.
- Shell motion runs on three duration tokens (`--td-motion-duration-fast`
  100ms, `--td-motion-duration` 150ms, `--td-motion-duration-slow` 250ms)
  declared in `shell/_tokens.scss`; every transition and animation of the
  shell, page actions, language/version selectors, taxonomy, skip link, and
  footer toggle draws from them, and `prefers-reduced-motion: reduce` zeroes
  the tokens instead of maintaining a per-selector opt-out list that drifted
  (12 selectors covered 42 rules; four files had no guard at all).
- `bin/migrations/oink06.py` gains a `frontmatter` transform (run first)
  that rewrites the 0.5.0 page-key renames in YAML front matter and cascades —
  `manualLink*`, `context_menu`, `hide_readingtime`, `hide_feedback`,
  `exclude_search`/`excludeSearch`, `content_width`, `assistant_links`,
  `annotation: {enable}`, and any `ui:` block (lifted to bare keys) — with
  findings for anything it will not guess at; TOML/JSON front matter is
  reported, not rewritten. Dry-run over the eleven in-house sites: 628 files,
  0 findings, idempotent.
- The giscus palettes ship as `assets/css/giscus-{light,dark}.css` and are
  published only on pages that render comments; they are also the default
  `comments.giscus.lightTheme` / `darkTheme`, so a site no longer points at
  `/css/giscus-oink-*.css` itself (those files are gone). Set a giscus
  built-in theme name or a stylesheet URL to override.
- The theme no longer uses `.Scratch`: the blog list and the search input
  use variables and the page store, and DocSearch mounts on one
  `#td-docsearch` container instead of two hard-coded ids paired with a
  `mod 2` counter. Configuring more than one search backend fails the build
  instead of warning.
- Unify the shell chrome on Font Awesome. `shell/icon.html` now dispenses one
  FA class pair per semantic name as
  `<i class="td-shell-icon td-shell-icon--<name> fa-solid fa-…">` instead of
  inline lucide SVG, so the sidebar, navbar, TOC, page actions and Command
  Palette share one icon family and one sizing model (`--td-shell-icon-size`
  sets the box; the glyph em derives from it, chevrons a step smaller). Role
  classes are unchanged, so CSS hooks and `dark-mode.js` keep working; the
  page-action menu takes its icons from the action registry, so it and the
  palette always show the same glyph.
- Refresh docs and blog typography: Inter for UI and prose, borderless inline
  code, quiet code cards with a hover-revealed Copy control, Mintlify-style
  field rows, a page-end pager of two text links, and a rule above card
  section indexes.
- `{{< fields >}}` and the `{.fields}` table produce one rendering, and every
  entry gets a `#field-<name>` anchor.

### Fixed

- The action manifest now precedes the synchronous action-registry bundle, and
  browser runtimes read the `data-td-*` names that templates actually emit.
  Page actions, Command Palette rows and search, command-only code copying,
  collapsible code blocks, localized disclosure labels, feedback identity,
  Giscus palettes, Image Zoom labels, and Asciinema timer labels therefore
  work in the rendered DOM rather than only in hand-written unit-test mocks.
- The Quick Start includes the three consuming-site Goldmark prerequisites;
  `bin/check-site-markup.py` verifies their resolved Hugo configuration.
  The content migration checker now fails closed on missing, empty, unreadable,
  or non-UTF-8 targets, and JSON front matter is parsed rather than brace-counted.
- Legacy front-matter errors also run for Markdown, RSS, and aggregate print
  rendering; an empty or scalar `ui` key fails with the bare page-key rule, and
  the removed sidebar body class names the valid `sidebar_enabled` replacement.
- Data-fence and unknown-callout hooks retain accepted `data-*` / `aria-*`
  attributes, chart `full` values are strict booleans, Swagger/ReDoc instances
  have unique IDs without replacing `window.onload`, and configured shell or
  featured images pass through the shared URL policy.
- Print aggregates rendered a page's content once per enclosing section — a
  chapter that is itself a section was rendered by its own print output and
  by its parent's, concurrently, and the two renders raced on the page store
  (render scope, code-block id registry), which produced intermittent
  duplicate `td-code-…` ids in `_print/` output. `print/page-content.html`
  now renders each page's print content exactly once per build through
  `partialCached`, and every print template (section, page, Book, single
  page) reads that.
- Landmarks: `<main>` no longer carries the redundant `role="main"`, and the
  sidebar `<aside>` no longer repeats the inner `<nav>`'s "Section navigation"
  label, so assistive technology lists one navigation landmark instead of two
  with the same name.
- `CLAUDE.md` documented `params.ui.shell_types` as `docs, blog, swagger`; the
  declared default has been `[docs, book, blog, swagger]` since Book shipped.
  `check-params.py` now asserts that every `params.X (default V)` in
  `CLAUDE.md` / `README.md` matches `hugo.yaml`.

- The table render hook runs in the print and RSS outputs, so a table keeps its
  caption, number, and scroll container outside interactive HTML.
- Folded (`[!TYPE]-` / `[!DETAILS]`) callouts get symmetric summary padding:
  the print-only static title rule no longer zeroes the `<summary>` bottom
  padding, and the open state keeps the static callout's title-to-body rhythm.
- The image resolver labels its errors by the caller — a Markdown image says
  `image`, not `shortcode` — so a failure names something the author can find.
- Book `fig` sources resolve through the shared image resolver, and
  configuration image sources are held to the same URL policy as content.
- The navbar renders on the home page; callout titles meet contrast; Gallery
  items are Zoom-eligible on the same terms as other images; the tabs runtime
  keeps its run boundaries, unique peer IDs, and print titles; FileTree honours
  `prefers-reduced-motion`.
- README no longer advertises carousels, which the theme does not have.

## [0.4.2] - 2026-08-16

### Added

- Refine FileTree with validated Font Awesome icon overrides, semantic colors,
  stateful folders, and one author-controlled code-font `#` comment instead of
  dedicated owner/group/mode fields. The terminal-window surface uses strictly
  equal-height single-line rows and a pointer- and keyboard-resizable divider;
  narrow names truncate while long comments remain horizontally scrollable.
- Reduce the shared navbar height to 50px and add opt-in
  `params.ui.navbar_autohide`, with section-cascade and page overrides. On
  mouse-driven devices at 768px and above the hidden bar returns from a
  corner-safe top-edge reveal zone or keyboard focus without reflowing the
  page; touch-only devices and the complete drawer-width tier keep it visible.
- Add the PRD 7 Docs/Blog shell and page-end system: global sidebar-root
  switching, count-sorted taxonomy tag panels, a stable Annotation override,
  compact root-aware Previous/Next cards, and one-click structured feedback
  that can hand detailed reports to the page's Giscus discussion.
- Accept `y` as a global alias for the `l` language switch, and `n` as a
  homepage-only next-section alias for `j`.

### Changed

- Replace the legacy configurable Yes/No response fragments and the unreleased
  endpoint/Worker prototype with structured `docs_feedback` events, optional
  fixed reasons, local per-language state, and a Giscus details link.
- Make Blog Previous/Next links follow the exact rendered sidebar sequence,
  including the Blog root, instead of a separate `PrevInSection` branch.

### Fixed

- Keep explicitly authored leaf-page icons visible in the starter sidebar by
  using the `all` icon-density policy. The sparse `groups` policy remains
  available as an explicit opt-in.
- Keep each Docs/Blog root landing as the first selectable W/S and Q/E entry,
  including sites that provide an explicit `data/docs_nav.json` order. A
  `sidebar_root_for: self` root now links to itself unless the legacy
  `sidebar_root_link_self: false` behavior is explicitly requested.
- Align the collapsed left/right rail restore controls with the breadcrumb and
  page-action row, outside the hidden navbar's corner-safe reveal area.
- Restore the sidebar's bottom utility dock at every rail and drawer width,
  with language/version anchored left and theme/GitHub anchored right. Its
  menus open upward on hover, while the mobile header carries a full search
  field with `/` hint immediately before the close control.
- Remove the empty breadcrumb band from top-level Docs and Blog pages: their
  title now starts at the content top while the page-action split button stays
  fixed on the original context-row coordinate.
- Keep a rendered navbar visible below 768px even when auto-hide or keyboard
  reading mode is active. Its phone utility edge contains only search and the
  relevant menu opener; the other global tools live in the drawer footer.

## [0.4.1] - 2026-08-14

### Added

- Add a Book-specific `content_width` presentation API with `slim`, `norm`,
  and `wide` modes. The default `norm` measure aligns prose, code, tables, and
  figures while remaining independent from the outer `page_width` shell.
- Add a non-heading `example` caption shortcode for labeled code/data samples,
  plus a reusable local-data `contributors` shortcode that renders an
  accessible, responsive GitHub contributor wall with Markdown, print, and RSS
  fallbacks.
- Let Landing Hero data cap its responsive display-title size with a validated
  `title_size` CSS length.
- Make the action-oriented keyboard shortcuts available on every interactive
  page, including the homepage: `l` cycles languages, `t` toggles the theme,
  and `f` / `c` open search or command mode. Add `r` to cycle through Home and
  the unique same-origin top-level routes registered in the navbar; shell-only
  tree, outline, pager, and reading-mode keys remain scoped to shell pages.

### Fixed

- Keep article reading-time metadata off Book chapters, where numbered
  structure and whole-Book output make the per-page estimate misleading.
- Keep Book sidebar numbers in a compact column and left-align the title text
  after it instead of letting both spans divide the row and visually center
  chapter labels.
- Align `j` / `k` heading jumps with native right-rail TOC navigation by using
  the computed root `scroll-padding-top` and target scroll margin. Navbar
  heights authored in `rem` are no longer misread as pixel values that leave
  headings hidden beneath the sticky header.
- Make the rendered sidebar tree the authoritative `q` / `e` order whenever it
  is available. Blog navigation now crosses a column boundary through the next
  column landing page before its first post, independent of date pager order;
  tree edges no longer fall through to another navigation family.
- Namespace automatic enhanced-code IDs with their enclosing alert and tab
  identities when Hugo resets fence ordinals in nested Markdown fragments.
  Copy, collapse, viewport, and line-anchor targets now remain unambiguous
  across repeated alerts and text tabs; authored public IDs stay unchanged.

## [0.4.0] - 2026-08-14

### Added

- Ship all five PRD 5 Scenario Components tracks in one consolidated release;
  the original 0.4/0.5/0.6 milestones remain design history rather than public
  tags.
- Add the Reading & Release track: a sidebar-tree-order sequential pager
  for docs and generic book pages (with blog time order preserved), matching
  same-origin `rel=prev/next` head links, a server-side Goldmark passthrough hook
  for local KaTeX/MathML, and a strict parameter-free `eq` display-math escape
  hatch for sites that cannot yet enable passthrough.
- Add local-first GitHub release facts, cards, lists, and checksum asset tables
  with one conditional copy runtime. Add a validated
  `data/download/<key>.yaml` model and `download` shortcode for rolling and
  pinned channels, including explicit pending-release behavior.
- Generalize the data-driven homepage renderer into a reusable `layout: landing`
  shell for regular pages, with inline and language-aware local data sources,
  the existing section family, and new pricing, comparison, command, steps,
  timeline, code, case-study, download, and bar-chart sections.
- Add a conditional `landing.js` progressive-enhancement runtime for reveal,
  count-up, copy, theme-image, and compact-menu behavior. Keep server-rendered
  content complete without JavaScript and make CSS-only marquees pausable,
  reduced-motion safe, forced-colors legible, and duplicate-track inert.
- Add the Book capability package on the existing docs shell: `book_*` chapter
  metadata, draft labels and optional notices, active-page sidebar headings,
  stable `fig`/`tbl`/numbered-`eq` targets, current-language `xref`, Book-wide
  figure lists and tables of contents, and opt-in whole-Book print HTML with
  document-local cross-chapter links and collision-free heading IDs.
- Add a dry-run-first, idempotent Book migration tool with reproducible TPME,
  DDIA v1/v2, and pg-internal recipes. JSON reports preserve conversion counts,
  skipped ambiguities, and a diff digest; focused checks cover dry-run, write,
  zero-change second runs, rendered target numbers, alternatives, duplicate IDs,
  and missing fragments.
- Freeze all three PRD 5 human contracts and their machine companion, bilingual
  migration guidance, root/subpath fixtures, 32-locale labels, and dual-Hugo
  checks for the complete HTML/print/Markdown/RSS behavior.

- Single-key keyboard navigation (PRD 6), on by default on docs, blog, and
  swagger shells and configurable via `params.ui.keyboard_nav.enable` (site,
  section cascade, or page front matter; a non-boolean value fails the
  build). `w`/`s` move the sidebar focus in one step from the current page's
  item (inside the tree `↑`/`↓` continue); `a`/`d` (and `←`/`→`, RTL-aware)
  collapse and expand groups through the existing chevrons, acting on the
  current page's item straight away; `Enter`, `Space`, or `g` opens the
  focused page; `Escape` returns to the content. The keyboard focus is a
  row-level tint one step stronger than the active pill, not an outline box.
  `j`/`k` jump to the next or previous section of the page outline with a
  fast, fixed 100ms ease-out glide (rapid repeats advance the queued outline
  cursor; heading-less pages fall back to the same short animation, and
  reduced motion gets instant steps); `q`/`e` go to the previous or next page
  following the sidebar tree order, `rel=prev/next` head links, or the blog
  pager. `h` toggles a chrome-free reading mode that hides both rails and
  the footer (remembered per session across page flips); `l` cycles through
  the available languages; `t` flips light and dark; `f` and `c` open the
  Command Palette in search and command mode. All bindings yield to inputs,
  IME composition, held modifiers, and open dialogs, and the `?` key stays
  reserved for a future shortcut help overlay.
- A collapse arrow at the right edge of the fat footer's copyright line
  hides or restores the link grid above it. The choice persists in
  localStorage, defaults to expanded, and localizes its labels through the
  new `ui_footer_collapse` / `ui_footer_expand` keys.
- Render the site navbar on every layout, including docs, blog, swagger, and
  taxonomy pages. The new `navbar_enabled` switch (default `true`) can turn it
  off globally via `params.ui.navbar_enabled`, per section via a front-matter
  cascade, or per page; disabling it restores the previous chrome (mobile
  subnav, sidebar brand and search rows, TOC-rail utility buttons, sidebar
  footer utilities). The navbar has exactly two states: full, and a compact
  state below `lg` that keeps every item visible as a right-aligned icon —
  there is no separate mobile menu, and the `navbar_accordion_single_open`
  parameter is retired. Menu parents are plain links that open their panel on
  hover or keyboard focus (no disclosure caret); the version selector, the
  language selector, and the theme control (with a System/Light/Dark picker)
  are Font Awesome icon triggers sharing one popover style; search is a
  magnifier icon opening the Command Palette. On shell pages below `md` an
  extra icon opens the sidebar drawer.
- Introduce `footer_style` (default `fat`) with the same site, cascade, and
  page override chain: `fat` renders the four-column footer grid above the
  copyright line on every layout, `slim` keeps only the line, and `none`
  removes the footer; an unknown value fails the build. Fat-footer data now
  lives in `data/footer/<lang>.yaml` (or single-language `data/footer.yaml`),
  with the legacy `data/home/<lang>.yaml` `footer` key still honored — note
  that sites using the legacy key now get the fat footer site-wide, where it
  was previously homepage-only. A fat footer without data degrades to slim.

### Changed

- Consolidate the legacy `home/` partial family behind thin adapters to the
  canonical Landing registry; keep existing homepage data and deliberate local
  partial escape hatches compatible while deprecating Docsy block shortcodes
  for new Landing work.
- Reuse the download facts in Landing pages, add local navbar/footer facts for
  GitHub stars and an alternate site, and support one-to-four-column navbar mega
  menus without runtime fact retrieval or a second data model.
- Extend the parameter-free `eq` escape hatch without breaking it: no parameters
  remains unnumbered and registers no target, while an explicit quoted `num`
  selects the numbered Book equation form; identity and caption fields are
  rejected unless that number is present.
- Preserve Docsy's `params.copyright` string/map contract and Hugo's top-level
  `copyright` fallback for the left side of the bottom bar. Replace OINK's
  ICP-specific `params.footer_icp` and `params.footer_icp_url` fields with one
  inline-Markdown `params.footer_center_info` string. It defaults to
  `Powered by Oink`; an explicit empty string hides the center region. The
  former ICP fields are no longer read.
- Make `docs`, `book`, and `blog` sequential reading types by default; allow a
  site type list or boolean `pager: false` page override. Explicit
  `data/docs_nav.json`, link-only pages, and sidebar dividers now share one
  flattened navigation projection with the pager.
- Extend the content-primitives contract with Release Assets, full-width
  contained tables, semantic numbered figures/tables/equations, cross
  references, Book indexes, strict parameter/URL/ID/i18n validation, print
  containment, repeated-render behavior, and plain non-HTML fallbacks.

- **`/` now opens the Command Palette in full search mode** (it previously
  opened the command-only mode); the new `\` shortcut opens command-only
  mode, and the `>` prefix keeps working inside the palette. Palette command
  listings now mirror the navbar control order — version, language, theme,
  then GitHub — with configured site commands after the built-ins, and the
  empty command-only listing keeps this order instead of sorting
  alphabetically.
- Move the page actions from the collapsible TOC-rail group to a Fumadocs-style
  split button in the breadcrumb row: an icon-only primary copies the page's
  Markdown (flipping to a green check), and the caret disclosure lists ten
  actions — reading items (copy, assistants, view markdown, view history)
  above a separator, acting items (edit, create child page, create docs or
  project issue, print entire section) below, plus configured custom links.
  `create_child_page`, `create_project_issue`, and `print_section` are now
  first-class registry actions surfaced in the Command Palette too; the
  page-level `print` action is retired in favor of Cmd/Ctrl+P. On the blog
  root and its first-level sections the primary becomes the RSS link. Pages
  without a Markdown output render a labeled dropdown-only button. Top-level
  section pages keep their one-crumb breadcrumb so the row stays anchored.
- The TOC collapse toggle is a three-line glyph inline with the group title
  (now labeled "Content"), aligned with the taxonomy group heads, which carry
  configurable icons (`params.ui.taxonomy_icons`, with folder/tags defaults);
  the whole header row highlights as one item, and in the sidebar drawer the
  group keeps a static three-line icon so it reads like the taxonomy heads.
- Scope the sidebar root switcher to the current top-level section: the
  dropdown appears only when a descendant section opts in with
  `sidebar_root_for: self`, listing the section itself (the default) plus each
  opted-in descendant. Sibling top-level sections belong to the navbar, and a
  section without switchable descendants renders a plain, unboxed link to its
  landing page — flush with the tree's top-level rows — instead of a
  single-entry dropdown. Taxonomy term pages adopt their members' shared top
  section for both the sidebar tree and the root link, so following a docs tag
  keeps the docs navigation instead of falling back to the site-wide tree. Blog leaf pages no longer show an RSS
  icon — feeds belong to the blog root and its sections. Fix the blank seam
  between the sidebar's lower edge and the footer while scrolling.

- Pin the navbar to the viewport edges on shell pages: the brand logo sits in
  the top-left corner above the sidebar (matching its 16px content inset) and
  the utility controls sit in the top-right above the TOC rail, instead of
  drifting with the centered 1280px landing container. The landing page and
  other non-shell layouts keep the centered container. In the control row the
  search icon moves before the version selector, separating the site's own
  menu entries from the fixed controls and keeping version and language
  adjacent.
- Blog sections in the generic sidebar tree now start expanded, so with the
  default `sidebar_menu_foldable: true` their collapse chevrons appear and
  every section is open until the reader folds it; an explicit
  `sidebar_expanded: false` in a section's front matter starts it collapsed
  (an `isset` check keeps that explicit false from being swallowed).
- Redesign the Fields component as a Mintlify-style stacked list: each entry
  puts the field name on its own header row followed by inline `type`,
  `required`, and `default` pills, with the description below and hairline
  dividers between entries, replacing the boxed name/value columns. The
  `required` and `default` metadata labels are now untranslated API vocabulary
  in every locale and output format (the `ui_field_default` i18n key is
  removed; `ui_field_required` remains for the action registry), and the
  Markdown fallback writes the literal `required` / `default:` words. An
  absent default still emits nothing while an explicit `""` stays visible.
- Upgrade the vendored Font Awesome Free assets from 6.7.2 to 7.3.1, use its
  official OpenAI and Claude icons for the assistant actions, and follow the
  upstream WOFF2-only web-font distribution instead of retaining legacy TTFs.
- Refresh the remaining outdated browser runtimes: DocSearch 5.0.1, Mermaid
  11.16.1, KaTeX 0.18.4, Highlight.js 11.12.0, Swagger UI 5.32.13,
  Asciinema Player 3.17.0, ECharts 6.1.0, AntV Infographic 0.2.19, Pako
  3.0.1, External SVG Loader 1.7.1, and the existing custom Prism
  language/plugin bundle on Prism 1.30.0. The SVG Loader artifact continues to
  embed the exact idb-keyval 6.2.0 code shipped by that upstream bundle.
- Publish the pre-minified Asciinema and AntV Infographic runtimes separately
  with fingerprinting and SRI so Hugo does not transform their runtime shims a
  second time during a production build.

### Fixed

- Supply an environment-aware default `robots.txt`, deterministic multilingual
  multi-output 404 document, functional `{.full-width}` table rendering,
  card-style section indexes, configurable last-commit subject/hash/omission,
  first-class non-linking `sidebar_divider` rows, and a search-keyword extension
  hook that avoids copying the search metadata partial.
- Preserve the sticky mobile subnav offset for deep anchors, contain wide
  tables and long KaTeX displays inside the article canvas, and keep print
  tables free of interactive wrappers.

- Render the shared OpenAI and Claude icon descriptors in both the page-action
  rail and Command Palette instead of keeping custom inline SVGs on only one
  surface.
- Replace the deprecated `.Page.IsNode` call in the blog shell with
  `not .IsPage`, keeping builds free of Hugo 0.163+ deprecation notices.

## [0.3.0] - 2026-08-12

### Breaking changes

- **Remove jQuery.** The theme no longer loads jQuery on any page. It was
  previously fetched render-blocking in `<head>` for every request, and the
  third-party inventory listed it as part of the UI foundation, so a consuming
  site's own scripts may have relied on the global `$`. Sites that do must now
  bundle jQuery themselves through project JavaScript. No theme feature
  requires it.
- **Remove `static/js/tabpane-persist.js`.** `assets/js/code-tabs.js` took over
  the legacy persistence contract, keeping the `td-tp-persist` storage key and
  data attribute, so authored tab content is unaffected. Sites that referenced
  the published file path directly must drop that reference.
- **Apply body and heading typography roles directly to content.** Sites that
  previously restyled raw `body` or heading selectors should move to the
  corresponding `--td-*-font-family` role or the established Sass variable.

### Added

- Add one-level Hugo Menu dropdowns on desktop and matching mobile accordions,
  preserving independent parent navigation, keyboard operation, active paths,
  external-link safety, and flat-menu compatibility.
- Add `all`, `groups`, and `none` sidebar icon-density policies. The absent
  compatibility default remains `all`; the starter example opts into
  `groups`.
- Add local-search keywords, positive boost multipliers, canonical exclusion,
  root/section/type grouping metadata, deterministic breadcrumbs and icons,
  language-separated size budgets, and identical boost behavior in Lunr and
  CJK substring ranking.
- Upgrade the existing local-search dialog to a Command Palette with empty,
  text, and `>` command modes, plus quick links, grouped page results,
  context-aware actions, localized safe site commands, choice actions, and a
  shared page-action registry.
- Add `/` as a command-first Palette shortcut outside editable controls. It
  opens with the `>` prefix, preserves the existing Cmd/Ctrl-K entry point,
  and returns focus to the pre-shortcut element when closed.
- Complete the shared page-action set with Open in ChatGPT, Open in Claude, and
  View edit history. Assistant prompts resolve the current browser URL at
  activation time, including its deployed host, query string, and fragment;
  repository history uses the same source path as Edit this page. The outbound
  assistant actions are disabled by default and require
  `params.ui.page_context_menu.assistant_links: true`.
- Add a bilingual PRD 4 migration reference and machine-checked root/subpath
  starter fixtures.
- Run the browser runtime tests in CI. `tests/js/` covers the shell, Command
  Palette, search engine, action registry, and surface coordination; until now
  no workflow executed it, so the only automated check on that code was that
  Hugo could bundle it.
- Add validated `badge`, `kbd`, `fields`, and `filetree` content primitives
  with semantic HTML, responsive presentation, and dedicated print and Markdown
  fallbacks. A standalone public `icon` shortcode remains deferred; components
  may use a private, allowlisted icon registry for their own decoration.
- Add opt-in native-dialog Image Zoom plus the shared `gallery` primitive,
  with page-level overrides, lazy media metadata, keyboard and focus handling,
  and page-store-driven runtime loading.
- Add validated `technical` and `system` typography presets plus public
  `--td-*-font-family` roles for UI, body, headings, code, display text,
  metadata, and print output. Existing Docsy and Bootstrap Sass font variables
  seed the new roles, and the system preset does not request OINK brand fonts.
- Add a typography-token boundary check and representative docs, blog, and
  print fixtures to the minimal example site.
- Add enhanced fenced code surfaces with filenames, language labels, copy,
  wrapping, long-block collapse, and deterministic transcript-command copying;
  add `code-group` for synchronized, deep-linkable alternatives while retaining
  legacy `tabpane` persistence.

### Changed

- Rename the reader-facing Copy Markdown and View Markdown actions to Copy text
  and View source. Their stable action IDs and Markdown-output requirements do
  not change.
- Route landing, shell, navigation, footer, content-card, search, print, and
  Asciinema font choices through semantic typography roles while preserving the
  default technical appearance.
- Give code stacks explicit Sarasa and Noto CJK monospace fallbacks instead of
  relying on the browser's generic `monospace` fallback.
- Keep off-site navigation out of `llms.txt`. Menu entries whose host differs
  from the site's own are navigation chrome rather than content, and listing
  them diluted an index meant for agents. Page-backed and same-host entries are
  unchanged.

### Fixed

- Link the `llms.txt` a site actually publishes. The Markdown output advertised
  the index unconditionally, so a site enabling the `markdown` output format
  without `LLMS` emitted a dangling link on every Markdown page. Each language
  now links its own index instead of pointing every translation at the default
  language's file.
- Localize the archived-version banner and the giscus `noscript` block, which
  were hardcoded English on every site. This also closes an unclosed `<p>` the
  banner emitted whenever `url_latest_version` was unset.
- Strip single-quoted and bare `data-zoom-src` attributes from print and
  Markdown output; only double-quoted values were removed before.
- Percent-encode the query that `search.js` places in the search URL. A query
  containing `&` was previously truncated at that character.
- Wait for the Asciinema terminal font before fitting terminal output, avoiding
  incorrect geometry when the custom font finishes loading after the player.
- Resolve product roots by content type when docs and blog share a type, and
  keep configured internal command URLs under the active deployment subpath.

### Performance

- Read the recorded `tdOutputFormat` page-store value instead of re-deriving the
  active output format, and cache the shell configuration and search dialog per
  language. On a 576-page build this cut `shell/config.html` from 151.9ms to
  22.1ms, `chrome-enabled.html` from 141.9ms to 49.6ms, and removed 3930 calls
  to `outputformat.html`, which is retained as a deprecated shim for consumer
  sites. Generated output is byte-identical.
- Case-fold search fields once when the engine is created rather than on every
  keystroke. A CJK query previously re-allocated a lowercase copy of the whole
  corpus per character typed; on an 800-document corpus this is 3.44ms to
  0.34ms per keystroke.
- Drop jQuery and the superseded `offline-search.js` runtime, which the Command
  Palette replaced. On the measured project-site snapshot this removed about
  88 KB from a typical documentation page's combined CSS and JavaScript; exact
  totals vary as later candidate assets change.

### Removed

- Remove `assets/js/offline-search.js`. The Command Palette replaced it and the
  runtime-isolation checks already asserted that it must not be bundled.

## [0.2.1] - 2026-08-10

### Fixed

- Normalize configurable docs and blog section paths with the documented
  `strings.Trim STRING CUTSET` argument order instead of resolving both roots
  to the site home.
- Keep docs and blog shell selection type-based, so a site can place content
  outside the configured root path while assigning `type: docs` or
  `type: blog` through front matter cascades.

## [0.2.0] - 2026-08-10

### Breaking changes

- **Rename `default_featured_image` to `default_featured`.** There is no
  compatibility alias. Update site parameters, page front matter, and section
  cascades. The implicit theme placeholder was also removed: entries without a
  page image or explicit default now render as text-only cards.
- **Require explicit Algolia credentials.** Sites that enable
  `params.search.algolia` must provide `appId`, `apiKey`, and `indexName`. OINK
  no longer falls back to Docsy's public example index and the build fails with
  a configuration error when any value is missing.
- **Remove legacy `base.js` navbar and Bootstrap widget hooks.** The obsolete
  `.js-navbar-scroll`, navbar-overflow, tooltip, and popover initializers are no
  longer run by the theme. Consumer layouts that still use those Docsy-era
  hooks must initialize the behavior in project JavaScript.
- **Change the English TOC label from `Content` to `On this page`.** The i18n
  key is unchanged, but sites with text snapshots or label-dependent tests may
  need to update their expected copy.

### Added

- Responsive landing-page media, linked component boards, and wordmark support
  across the landing navigation, docs shell, mobile subnav, and footer.
- The Markdown-first `steps` shortcode and polished, theme-aware Asciinema
  terminal frames.
- Theme-aware giscus styling and expanded documentation for hero and featured
  image configuration.
- Configurable shell content types and docs/blog section paths through
  `params.ui.shell_types`, `params.ui.docs_section`, and
  `params.ui.blog_section`.
- Complete 89-key i18n schemas for every bundled locale, including a generic
  `zh` catalog; untranslated OINK-only labels use explicit English fallbacks.
- Font Awesome Regular face support alongside the existing Solid and Brands
  faces.
- Theme CI for the minimum and current supported Hugo versions, translation-key
  parity checks, and contribution templates.

### Changed

- Refined blog imagery and summaries, section indexes, taxonomy rail groups, RSS
  navigation, page actions, link styling, and version-menu alignment.
- Trusted ECharts callback blocks no longer emit redundant warnings.
- Taxonomy “All” links now derive a common content section when possible and
  otherwise fall back to the taxonomy index instead of hard-coding `/blog/`.
- Public source comments for the OINK shell now describe behavior in English;
  shortcode templates include concise purpose and parameter headers.
- README quick-start configuration now distinguishes theme-provided features
  from site-enabled output formats and search/theme policy.
- The remaining td-site-header, mobile-menu, and language-menu behavior in
  `base.js` now uses the native DOM directly.
- Document the Google search dark-mode stylesheet as an explicit consumer
  opt-in.

### Removed

- Removed unreachable legacy navbar/Bootstrap widget code from `base.js` and
  unused Font Awesome v4 compatibility fonts.

### Fixed

- Added the ARIA presentation role required by tabpane list wrappers, removing
  `aria-required-children`, `aria-required-parent`, and `listitem` violations.
- Preserve OINK light and dark brand tokens when the stock Bootstrap RTL
  stylesheet is loaded after the main theme stylesheet.
- Guard color-theme storage access and always clear prepaint animation locks
  when browsers or sandbox policy deny `localStorage`.
- Replaced decorative nested `main` and `aside` elements on the landing page
  with neutral containers.
- Replaced the print view's inline `onclick` handler with the shared,
  CSP-compatible print action.
- Guard sidebar td-active-path lookup for consumer sites that do not provide the
  optional navigation data map.

## [0.1.0] - 2026-08-10

- First reviewed OINK release after the Docsy fork, requiring Hugo Extended
  0.160.1 or newer.
- Added class-based light/dark syntax highlighting, unified page actions,
  responsive shell rails, improved footer/hero/blog layouts, and accessibility
  repairs.

[0.5.0]: https://github.com/pgsty/oink/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/pgsty/oink/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/pgsty/oink/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/pgsty/oink/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/pgsty/oink/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/pgsty/oink/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/pgsty/oink/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pgsty/oink/releases/tag/v0.1.0
