# Changelog

All notable changes to OINK are documented here. The project follows
[Semantic Versioning](https://semver.org/) for published tags.

## [Unreleased]

### Changed

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

- Render the shared OpenAI and Claude icon descriptors in both the page-action
  rail and Command Palette instead of keeping custom inline SVGs on only one
  surface.

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

[Unreleased]: https://github.com/pgsty/oink/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/pgsty/oink/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/pgsty/oink/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/pgsty/oink/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pgsty/oink/releases/tag/v0.1.0
