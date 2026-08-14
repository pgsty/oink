# Changelog

All notable changes to OINK are documented here. The project follows
[Semantic Versioning](https://semver.org/) for published tags.

## [Unreleased]

## [0.6.0] - 2026-08-14

### Added

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
- Freeze the PRD 5 0.6 Book contract and extend the machine contract, bilingual
  migration guide, root/subpath fixtures, 32-locale labels, and dual-Hugo CI
  matrix for the complete HTML/print/Markdown/RSS behavior.

### Changed

- Extend the 0.4 parameter-free `eq` escape hatch without breaking it: no
  parameters remains unnumbered and registers no target, while an explicit
  quoted `num` selects the 0.6 Book equation form; identity and caption fields
  are rejected unless that number is present.
- Extend the content-primitives contract with semantic numbered figures,
  tables, equations, cross references, Book indexes, strict parameter/URL/ID
  validation, print containment, and plain non-HTML fallbacks. PDF/EPUB
  generation and automatic numbering remain site-owned non-goals.

## [0.5.0] - 2026-08-14

### Added

- Generalize the data-driven homepage renderer into a reusable `layout: landing`
  shell for regular pages, with inline and language-aware local data sources,
  the existing section family, and new pricing, comparison, command, steps,
  timeline, code, case-study, download, and bar-chart sections.
- Add a conditional `landing.js` progressive-enhancement runtime for reveal,
  count-up, copy, theme-image, and compact-menu behavior. Keep server-rendered
  content complete without JavaScript and make CSS-only marquees pausable,
  reduced-motion safe, forced-colors legible, and duplicate-track inert.
- Freeze the PRD 5 0.5 Landing human and machine contracts, bilingual migration
  guidance, root/subpath output fixtures, and focused Hugo and browser checks.

### Changed

- Consolidate the legacy `home/` partial family behind thin adapters to the
  canonical Landing registry; keep existing homepage data and deliberate local
  partial escape hatches compatible while deprecating Docsy block shortcodes
  for new Landing work.
- Reuse the 0.4 download facts in Landing pages, add local navbar/footer facts
  for GitHub stars and an alternate site, and support one-to-four-column navbar
  mega menus without introducing runtime fact retrieval or a second data model.

## [0.4.0] - 2026-08-14

### Added

- Add the PRD 5 Reading & Release track: a sidebar-tree-order sequential pager
  for docs and generic book pages (with blog time order preserved), matching
  same-origin `rel=prev/next` head links, a server-side Goldmark passthrough hook
  for local KaTeX/MathML, and a strict parameter-free `eq` display-math escape
  hatch for sites that cannot yet enable passthrough.
- Add local-first GitHub release facts, cards, lists, and checksum asset tables
  with one conditional copy runtime. Add a validated
  `data/download/<key>.yaml` model and `download` shortcode for rolling and
  pinned channels, including explicit pending-release behavior.
- Freeze the PRD 5 0.4 human and machine contracts, bilingual migration guide,
  root/subpath fixtures, and focused validators for the complete
  HTML/print/Markdown/RSS matrix.

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
  contained tables, and the parameter-free equation escape hatch, including
  strict parameter, URL, i18n, repeated-render, and output-format behavior.

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
- The remaining landing-header, mobile-menu, and language-menu behavior in
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
- Guard sidebar active-path lookup for consumer sites that do not provide the
  optional navigation data map.

## [0.1.0] - 2026-08-10

- First reviewed OINK release after the Docsy fork, requiring Hugo Extended
  0.160.1 or newer.
- Added class-based light/dark syntax highlighting, unified page actions,
  responsive shell rails, improved footer/hero/blog layouts, and accessibility
  repairs.

[Unreleased]: https://github.com/pgsty/oink/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/pgsty/oink/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/pgsty/oink/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/pgsty/oink/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/pgsty/oink/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/pgsty/oink/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/pgsty/oink/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pgsty/oink/releases/tag/v0.1.0
