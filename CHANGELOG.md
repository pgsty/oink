# Changelog

All notable changes to OINK are documented here. The project follows
[Semantic Versioning](https://semver.org/) for published tags.

## [Unreleased]

### Added

- Opt-in static backlinks (knowledge-graph proposal, stage G1): with
  `params.ui.backlinks: true` — or the prefix-free front matter key
  `backlinks`, which a section can cascade — every page lists the pages
  that link to it, between the page annotation and the pager. The
  per-language reverse index derives at build time from ordinary Markdown
  links and `ref`/`relref` in raw source: fenced and inline code are
  stripped first, duplicate references merge into one edge, self links,
  external links, and same-page anchors never count, fragments drop for
  page identity, and languages stay isolated. No runtime, no new syntax;
  the block renders only when pages actually link in, sorted by stable
  page path. The per-page Markdown output carries the same list through
  the same partial; RSS omits it. Unresolvable destinations are dropped
  silently — a documented gap, not a link checker. An invalid value warns,
  falls back to off, and fails `--panicOnWarning`.
  `bin/check-backlinks.py` owns the contract.
- Opt-in `NAVJSON` output format: a machine-readable navigation tree
  (`navigation.json`), one file per language at the language root, enabled
  through the site's `outputs.home`. The tree serializes the same authority
  chain the sidebar and pager read — the explicit `data/docs_nav.json` tree
  for docs/book sections when it exists, the weighted content tree
  everywhere else — with child selection shared through the new
  `shell/nav-children.html` partial the flattened reading chain also
  consumes. Array order is the contract; `weight` is never serialized.
  Manual-link placeholders appear as `external`/`link` nodes the way the
  sidebar shows them; dividers and never-rendered pages are omitted with
  their children kept. The format owns `schema/nav.v1.schema.json` (a
  hand-authored, versioned contract artifact outside the generated
  configuration schemas' drift gate), and `llms.txt` lists the file for its
  own language. `bin/check-agent-indexes.py` validates schema compliance,
  URL resolution, language isolation, determinism, the explicit-tree order
  (manual links included), and that the docs subtree flattens to exactly the
  LLMSFULL bundle's page sequence — two template paths, one authority.
- Opt-in `LLMSFULL` output format: a per-top-level-section full-text bundle
  (`llms-full.txt`) for agents, concatenating the same semantic Markdown as
  the per-page output in sidebar reading order, one file per language. A
  section enables it in its `_index` front matter `outputs`; the theme never
  adds it to a site's output set. Enabling it below the top level warns and
  emits nothing, so ordinary preview keeps working while `--panicOnWarning`
  blocks publication. `llms.txt` lists the enabled bundles for its own
  language. `bin/check-agent-indexes.py` owns the contract: language
  isolation, source integrity, weight order, per-page equivalence,
  determinism, discovery, and the nested-section negative case. The per-page
  Markdown body moved into the shared `content/markdown-document.md` partial
  (byte-identical output, proven by the unchanged markdown goldens) so the
  two outputs cannot drift apart.

### Fixed

- A `data/docs_nav.json` node without a `children` key crashed the build
  with a reflection error from inside the sidebar walker. Authored data
  degrades instead of erroring: a childless node now renders as the leaf it
  is.

## [0.7.1] - 2026-08-26

### Security

- Swagger UI no longer contacts the online validator. The vendored bundle
  defaults `validatorUrl` to `https://validator.swagger.io/validator` and
  only skips it for localhost spec URLs, so every deployed `swagger` page
  quietly sent its spec URL to a third party -- against the theme's
  zero-implicit-network promise. The initializer now pins
  `validatorUrl: null`, and it moved out of the shortcode's inline
  `<script>` into the stable `js/chunks/swagger-init.js` chunk
  (one initializer per page, any number of containers).
- The two configured URL surfaces that bypassed the shared URL policy now go
  through it: `params.ui.page_context_menu.links` entries and
  `params.url_latest_version` used to reach `href` via `safeURL` unchecked,
  so a `javascript:` URL in site configuration rendered as a clickable
  script. Both now warn and drop an unsafe link; custom links also skip
  entries without a string, non-blank name or a string URL, a non-array
  `links` value warns and is ignored, and the menu separator only renders
  when a valid link survives. The archived-version banner additionally
  HTML-escapes the URL at its `safeHTML` sink -- the shared policy clears the
  scheme and host, but a quote in an otherwise valid URL would still break
  out of the attribute without escaping.
- Landing hero `media.ratio` and `media.max_width` were interpolated into a
  `safeCSS` style attribute unvalidated, so front matter `sections` -- an
  author-level input -- could inject arbitrary CSS with zero warnings.
  `ratio` now accepts exactly two `<number>(fr|px|rem|em|%)` tracks (the
  documented `'1fr 240px'` shape), `max_width` a plain CSS length; anything
  else warns and is ignored.

### Fixed

- Invalid configuration values warn and fall back instead of stopping an
  ordinary build or silently emitting broken output, per the diagnostics
  contract. `blog_index_size`, `sidebar_expand_levels`,
  `sidebar_menu_truncate`, and `offline_search_summary_length` crashed
  `hugo server` on a non-numeric value; `sidebar_width_min/max` accepted
  CSS-injection text (emitted as `ZgotmplZpx`) and negatives with zero
  warnings; `blog_index_columns`/`section_index_columns` fed fractions into
  CSS `repeat()`; `sidebar_item_overflow`, `sidebar_menu_foldable`,
  `print.toc`, `sidebar_cache_limit`, `print.section_break_wordcount`,
  `offline_search_max_results`, and `blog_index_size: 0` changed behavior
  silently. All of them now resolve through the shared validator (a new
  `int` kind checks the whole-number lexical form and casts through float so
  the value is read as base-10 -- Hugo's string-to-int cast is base-0, which
  would read `010` as octal 8 and overflow-error on very long input), a min
  above its max falls back to the 220/480 pair, and every
  case is in the check-params invalid matrix (warn on normal builds, fail
  under `--panicOnWarning`).
- Asciinema, ReDoc, and Swagger respect the output contract. Their
  shortcodes rendered the full interactive component into every output:
  page Markdown/LLMS carried `td-*` markup and JSON config, RSS the same,
  print rendered dead containers -- and a page-level print output loaded the
  full player runtime. All three now read the output format like the other
  sixteen gated shortcodes: Markdown and RSS get a plain link line, print a
  static labelled link, and only interactive HTML registers the runtime
  flags (scripts.html additionally gates the three runtime loads on the
  interactive output, since a Page Store can carry values across a page's
  output renders). The asciinema numeric parameters (`speed`, `startAt`,
  `cols`, `rows`, `idleTimeLimit`, marker times) validate lexically and
  warn instead of failing the build on author input, and the cast/spec URLs
  of all three now pass the shared URL policy. Covered by a new
  `fixtures/media-embeds` fixture with HTML/print/Markdown/RSS goldens and a
  four-state component check with runtime absence assertions.
- The landing capabilities `rules` bars now render at their authored widths:
  the template emitted `--w` per bar but the stylesheet hardcoded the
  fallback rhythm and never read it. Widths validate as CSS lengths (bad
  entries warn and keep the default), `rules` must be an array, and the
  capabilities `columns` and marquee `rows` counts validate as whole numbers
  instead of crashing the build on a bad string.
- The generated configuration schemas match what Hugo actually parses. The
  hugo.yaml reader kept trailing inline comments inside scalar values, so
  eleven defaults shipped as comment-contaminated strings (`print.toc` was
  the string `"true # section print views..."` instead of boolean `true`),
  and four comment blocks attached to the wrong key. The parser now strips
  unquoted trailing comments, the misattached blocks are separated, and the
  front matter schema no longer advertises keys read only by migration
  warnings (`release`, `upstream_attribution`, `downstream_modified`) or the
  navbar menu-entry `columns`; regeneration self-checks these invariants so
  the drift gate cannot re-approve the bug it compares against.

### Changed

- The shared-scenarios checker survives a wedged Hugo instead of spending a
  run on it. Hugo can deadlock under `--panicOnWarning`: the panic is raised
  while the warning logger still holds its mutex, the lock is never released,
  and the next goroutine to reach the logger blocks forever
  (gohugoio/hugo#9380, fixed in 0.92.0 and seen again on 0.164.0 and
  0.165.0). It is a scheduling race, reproduced once in 240 local runs at
  `GOMAXPROCS=2` and never at higher parallelism, which is why it read as
  noise: it passed on the same commit forty minutes earlier and again on a
  rerun. The per-build ceiling drops from ten minutes to two -- still roughly
  twenty times the slowest build on a cold CI cache -- and a build that wedges
  is retried once, loudly, naming the command. A build that wedges twice still
  fails the run, because a timeout that reproduces is a result rather than
  noise, and a timeout is not a return code, so retrying one cannot weaken
  what the case asserts. The ten-minute ceiling did not cause any of this; it
  revealed it, because a six-hour hang reads as a stuck runner while a bounded
  one reads as a bug.

## [0.7.0] - 2026-08-25

### Added

- A Mermaid diagram can be opened at its own size. Mermaid never overflows a
  narrow column, it *shrinks* to fit it, so `overflow-x` never offered a way
  back: on a 390px phone the sequence diagram in the theme's own
  documentation rendered at 35% of its natural width, with 14px labels
  arriving as five. Hovering a diagram -- or reaching it with the keyboard --
  now reveals a control in its corner that renders the diagram a second time
  into a dialog at full size, panned by dragging, zoomed with the wheel, a
  two-finger pinch, or `+`/`-`, and reset with `0`. A diagram that would have
  to shrink below half size to fit opens at 1:1 at its starting corner
  instead of as a thumbnail, because a fitted view of an unreadable diagram
  is the problem, not the fix; zooming back out always reaches the whole
  diagram, however large it is. Nothing is downloaded for it, there is no
  switch to set, and the viewer is its own dialog rather than a second mode
  bolted onto Image Zoom's.
- A theme color. `params.ui.theme_color` takes a `#rgb`/`#rrggbb` hex and
  tints the shell's accent *grounds*: the selected sidebar row and the greyed
  ground its neighbours take under the pointer, hover washes, the outline pill
  and its travelling rail and dot, tag and chip hovers, a content card's
  hovered edge, a share button's hover fill, text selection, focus rings, and
  each root's mark in the sidebar switcher. Ink that belongs to the shell
  rather than to the prose follows it as well -- the outline anchors the
  viewport is standing over, and a Book chapter's headings under the pointer
  or keyboard focus. It deliberately leaves the reading surface alone -- prose
  links, external URLs and inline code keep the brand palette in every section
  -- so a colored section is a quiet signal of place rather than a recolor of
  the text.
  Front matter `theme_color` overrides the site value per page, and a section
  root writes it into its `cascade` to give a whole section its own identity,
  the way a site keeps a navy Docs beside a violet Blog. The optional
  `theme_color_dark` carries the dark palette; when omitted the dark accent
  derives by lightening the light color toward white in 4% steps until it
  reads AA body text on the theme's dark canvas, so a derived palette is
  never unreadable. Hovers derive by the same lightening move.
  The implementation is one head-emitted `style` element declaring three
  custom properties -- `--td-accent`, `--td-accent-rgb`, `--td-accent-hover`
  -- which every accent ground already resolves through. With neither key set
  the head carries no style element at all; an invalid value warns and keeps
  the default palette; a `theme_color_dark` with no `theme_color` to pair with
  warns and is ignored, so a page is colored in both modes or in neither; and
  the emitted block is formatted from parsed integer channels only, so no
  author text can reach the style element. The theme also
  reads the chosen colors against its own canvases: a palette below AA body
  text (4.5:1) still ships, but warns with a suppressible id, so the
  publishing gate catches an unreadable accent while a deliberate palette
  stays one config line away.
- `params.ui.fonts` reaches the theme's seven typography roles from
  configuration. A site that wants a different face no longer needs to mount
  SCSS or add a stylesheet: `ui` is the main face, and because
  `--td-body-font-family` and `--td-heading-font-family` resolve through it,
  one line moves chrome, prose and headings together. The other keys --
  `body`, `heading`, `code`, `display`, `meta`, `print` -- narrow from there.
  The key names faces and never loads them: a family must be one the reader
  already has or one the site declared in an `@font-face` of its own, so a
  normal build still downloads nothing and every list should end in a generic
  family. Values are gated to plain font family syntax -- quoted names, bare
  identifiers, a leading hyphen, and names spelled in any script -- and the
  emitted `:root` block is rebuilt from the matched parts. A boolean, an
  unknown role, or an unsafe value warns and is dropped on its own, leaving
  the rest of the map in force; a site that sets nothing gets no style element
  at all. The block renders after the stylesheet, which is what lets an
  authored face outrank the `params.ui.typography` preset at equal
  specificity.
- An opt-in `BookManifest` output records the existing Book sequence, stable
  page/heading/numbered-object targets, per-page HTML and Markdown, and xrefs
  without guessing publication metadata or changing default builds. The theme
  repository now ships generic `book-epub.py` and `book-pdf.py` publication
  steps plus EPUB/PDF artifact checkers. EPUB packaging consumes the same
  whole-Book Print semantics through pinned Pandoc and EPUBCheck gates; PDF
  rendering uses an explicit Chrome/Chromium binary, a temporary loopback
  server with a script-blocking Content Security Policy, offline-by-default
  resource validation, A4 output and CSS page numbers. Missing, out-of-tree,
  and remote resources fail unless an explicit opt-in applies; that opt-in
  permits only passive HTTP(S) media, never local-file schemes or remote
  scripts. Existing artifacts are never replaced implicitly.

- One media-result contract behind every resolved image. The content
  resolver, the representative (featured) resolver, and Landing media now
  answer "where is it, how big is it, can Hugo process it" in one shared
  shape (`_funcs/media-result.html`) instead of three private ones. Landing
  items gain from it directly: an `image:` or image `icon:` that names a page
  bundle or global asset resolves to that resource and ships its intrinsic
  `width`/`height` -- an explicit authored pair still wins verbatim, and only
  as a pair, while static files and remote URLs never pretend to carry
  metadata they did not provide. The full `fig` source form is now pinned as
  a numbered container whose parameters deliberately exclude processing;
  a processed numbered image is a native block image with `num`.
- Generated configuration schemas. `bin/generate-config-schema.py` projects
  `schema/site-params.schema.json` and `schema/front-matter.schema.json` from
  the two existing authorities -- `hugo.yaml`'s defaults with their comment
  documentation, and `check-params.py`'s template read-point scan -- for
  editor completion and hover help. The schemas are generated artifacts,
  never a second configuration authority: CI regenerates them and fails on
  drift, and the front-matter schema deliberately carries no type constraints
  because several keys accept a bare-boolean opt-out beside their site type.

### Changed

- A `mermaid` fence renders through a figure, not through the code block's
  `<pre>`. It keeps its source in a `<script type="application/json">` beside
  an empty stage -- the shape `echarts` and `infographic` already use -- and a
  runtime owns when the diagram is drawn. That is what makes the three
  entries around this one possible: the source is still readable after
  Mermaid has run. The diagram is now centred, and the code frame it never
  earned is gone: Mermaid emits `width="100%"` with a `max-width` at the
  diagram's own size, so anything narrower than the column used to sit
  against the start edge with up to 300px of empty bordered box beside it.
  There is deliberately no alignment attribute; a diagram is a figure, and no
  reader wanted one flush right. Markdown, RSS and Print carry the source
  block that `echarts` and `infographic` already emit there -- Print had been
  carrying a `<pre class="mermaid">` no runtime ever reached, set to
  `font-size: 0`, so a printed diagram was a blank gap. A page whose Mermaid
  asset fails to arrive falls back to the same source block rather than to an
  empty figure.
- Switching colour scheme re-renders the diagrams instead of reloading the
  page. The old runtime reloaded on every theme change on any page holding a
  diagram, citing a Mermaid limitation from the 8.x era; Mermaid 11
  re-initializes cleanly, and the stage holds its height across the swap so
  the page does not collapse under the reader.
- Book numbers and captions read in the prose face. The sidebar chapter number
  and the in-prose `Figure`/`Table`/`Equation`/`Example` labels were set in the
  bundled `IBM Plex Mono`, which ships a Latin subset only: a Chinese label
  split across two faces mid-sentence, the digits in Plex and the character in
  whatever monospace fallback the reader had. They now inherit the surrounding
  face and keep their weight, with `tabular-nums` holding the sidebar column
  aligned. A Book no longer carries typography of its own; it reads as Docs
  does, and a site that wants technical labels back sets them from its own
  stylesheet.
- First-party browser behavior now publishes as stable capability chunks under
  `js/chunks/`; page flags select script tags instead of creating one
  concatenated bundle for every feature combination. Execution order and the
  fixed action/core layers remain unchanged, while cache identities grow with
  capabilities rather than with `2^N` page combinations.
- Font Awesome's compiled distribution is a separately fingerprinted
  `scss/fontawesome.css` resource, loaded before the consumer-specific main
  stylesheet. An ordinary theme or site CSS edit no longer invalidates the
  vendor bytes. Fingerprinted URLs make immutable caching safe when the
  deployment host supplies an appropriate cache policy; the theme does not
  claim control over host response headers.
- Visual checker ownership follows the rendered surface: geometry, computed
  color, sizing and spacing assertions live in the documentation site's
  Playwright suites, while source checkers keep forbidden-input and
  non-observable topology contracts. This removes brittle CSS-value grep from
  the theme gate without weakening browser coverage.
- Whole-Book Print propagates child mathematics to the aggregate KaTeX asset
  gate. Print code children inherit paper-edge wrapping, Bootstrap column
  resets are scoped to direct `.row` children instead of matching KaTeX
  `col-align-*`, and numbered equations use the full paper width with their
  caption below. Chrome 131+ also receives centered CSS page numbers. These
  fixes came from rendered EPUB/PDF publication review and leave screen layout
  unchanged.
- Google Analytics is limited to interactive HTML output; Print and machine
  outputs no longer request analytics during rendering or packaging.
- Inline code is crimson ink, not a grey pill. Following Blowfish, prose
  `code` reads in a semibold monospace crimson on a hairline wash -- an order
  of magnitude lighter than the old tint, enough that a run of adjacent tokens
  in one table cell stays countable without turning the paragraph into a field
  of lozenges. Crimson rather than a blue, so a page dense in identifiers
  reads as code and prose instead of code and links. Bold code
  (`` **`code`** ``) deepens within the same crimson: staying inside one hue
  keeps it emphasis rather than a second category. `--bs-code-color` joins the
  same family, so Landing narrative fields agree with prose. None of it
  follows a theme color -- code ink is a reading convention.
- The sidebar root switcher draws each root's mark in that section's own
  theme color. It is the one place a reader compares the sections against
  each other, so it is the one place the colors appear side by side; the
  labels stay body text, and the navbar keeps a single resting tone and picks
  up the current section's accent only on hover.
- The selected sidebar row reads as the theme color instead of as grey. At
  10% even a saturated violet renders as a warm neutral, so the accent ground
  moved to 14% in light and 16% in dark. Where accent ink sits on a wash of
  the same accent -- a hovered solid badge, the outline pill -- the readable
  pairing is tighter than the page canvas suggests, which is what the shipped
  palettes are tuned against.
- Taxonomy chips are quiet at rest and light up on the pointer. The solid
  slug fill became a pale neutral ground with muted ink, and hover glides the
  whole chip into the section's accent instead of the fixed copper it used
  before.
- The series strip is one disclosure the width of the bar. The whole row
  toggles rather than the part counter alone, the text caret became the
  theme's own chevron parked at the end of the row and rotating on open, the
  member list starts at the bar's leading edge instead of hanging off the
  counter, and each member is a full-width target with its ordinal drawn by
  the link, so a row is clicked rather than a word. The term link stays a
  sibling of the disclosure -- a focusable descendant of a summary is a nested
  interactive control -- and is laid over a ghost copy of its own text that
  reserves the width inside the summary.

- Link hover leaves the muted navy for a vivid azure. The resting color is
  unchanged; the hover target moves from a half-step within the navy to
  `#1d6fc4`, the Tailwind move where saturation does as much of the work as
  lightness, held at the brightest step that still reads AA body text on the
  sky canvas (4.62:1) and the white surfaces (5.09:1). The 150ms glide on the
  shared colors curve, and the dark palette, are unchanged.
- The navbar's dropdown panels breathe in and out instead of popping. A 100ms
  fade with a 4px settle rides the shared hover curve in both directions; the
  runtime still toggles only `hidden`, with `transition: display
  allow-discrete` holding the exit and an `@starting-style` block feeding the
  entry. Browsers without discrete display transitions keep today's instant
  toggle, and reduced motion zeroes the duration tokens.
- The series strip is a panel now, not a stack of links. It is translucent over
  a blur rather than an opaque card, because a `hero` article paints its
  featured image behind exactly this band and a solid ground punched a hole
  through the picture; on a plain article the tint resolves to the page's own
  ground, so one treatment serves both. The bar carries the series' taxonomy
  icon beside its name and its part counter as a soft pill in tabular figures,
  with a hairline ruling it off from the reading order below -- on one surface,
  not a second ground stacked inside the first. Each ordinal sits at the end of
  a fixed square track, so the titles hold a straight edge where a two-digit
  part used to shove every row after the ninth to the right, and a member title
  now carries its own weight on its own element instead of inheriting the prose
  rule that thickens links in running text -- thirty-five parts read as a
  reading order rather than thirty-five shouted links. The members themselves
  became cells on one adaptive grid: `auto-fit` tracks at a readable minimum
  measure, so the same markup is one column on a phone and several on a wide
  desk with no template threshold for a particular series length, and cell
  order stays DOM order, which keeps tab order and visual order identical.
  Hover and the reader's own place borrow the two grounds sidebar navigation
  already uses for those states, so a series panel and the tree beside it agree
  about what "under the pointer" and "you are here" look like; the current
  member adds a filled ordinal and a heavier title, so the cue is never colour
  alone. A cell's margin reset is scoped through the list, because the prose
  rule that spaces `ol` items carries two classes and a type and had been
  adding 4px of rhythm to every cell that the component never asked for.
- Print expands a closed disclosure again in browsers that hide one through
  `::details-content`. Forcing `display` on the children left the subtree out
  of layout, so a collapsed series strip, file tree or callout printed as its
  summary alone.
- The sidebar agrees with itself about what being somewhere looks like. The
  row naming the section you are in was the one row that lifted to the link
  colour when selected, because nothing outranked the selected-ink rule --
  every other top-level row keeps body text and lets the selected ground say
  it. It now does the same: a place, not a link to one. The ink travels as a
  token the row sets and the link reads, so the two rules that used to express
  that intent no longer have to win a specificity contest to agree.
  Everything that answers "which section" is drawn in that section's own
  colour rather than the brand's: the mark on that row, the mark in the
  switcher's closed trigger, the tick beside the root you are in, the rail
  down an open branch, and a selected row's ink wherever it does lift. A site
  with no theme color sees the brand accent throughout, as before -- except
  the root row, which stops turning blue when you are standing on it.

### Fixed

- The Book publication job renders its PDF. It never had: `chrome-headless-shell`
  needs unprivileged user namespaces for its zygote sandbox, and Ubuntu 24.04
  -- what `ubuntu-latest` now resolves to -- restricts them through AppArmor,
  so the job aborted with "No usable sandbox" on the first run it ever had on
  a runner; EPUB packaging and epubcheck had already passed above it. CI now
  relaxes that one sysctl before rendering, which leaves Chrome's own sandbox
  on. `bin/book-pdf.py` is untouched: `--no-sandbox` would have weakened the
  render for every consumer to work around a single runner image.
- A Mermaid diagram inside a tab that is not the open one renders at its
  proper size. Docsy's `startOnLoad` ran after the tab runtime had set
  `panel.hidden`, and inside `display: none` every text measurement returns
  zero, so Mermaid wrote `max-width: 16px` into the SVG and -- having marked
  it processed -- never recomputed it; revealing the tab did not recover it.
  The theme's own Mermaid page shipped one such squashed diagram. Diagrams
  are now drawn before anything hides them, and a stage that has no box when
  its turn comes waits for one through a `ResizeObserver`, the same recovery
  ECharts already relies on here. `visibility: hidden` and
  `content-visibility: hidden` were never affected, which is why a folded
  callout was always fine.
- An image `src` that resolves to a non-image resource degrades instead of
  detonating. The resolver warned "dropping the image" and then read fields
  off the resource it had just dropped, stopping the build -- the one path
  the media fixtures never walked. It now drops to the same empty `src` the
  URL policy uses, and every invalid-media fixture newly asserts the
  ordinary build stays alive, which is what had let the crash hide behind a
  passing warning check.
- `theme_color: false` opts a page out of an inherited section color -- the
  theme's bare-boolean idiom, inherited dark half included, silent because it
  is deliberate. Every other non-hex value now warns: a numeric `0` used to
  vanish into the resolver's `default` on the way to the warning, violating
  the "non-hex warns" contract, and `true` warned only by the accident of its
  spelling. Negative fixtures pin all three shapes.
- The featured-banner heading takes its full measure back on phones. The
  page-title band reserved 5rem of clearance for the floating actions button,
  but a banner page parks that button on the artwork -- the heading below it
  was holding a 390px Chinese title to ~278px and wrapping one orphaned
  character per line. A banner heading now drops the reservation; a browser
  test measures both languages at 360 and 390px.
- CI hardening: the theme-unit matrix gains Hugo 0.165.0 (verified locally:
  strict fixture build plus every Hugo-consuming checker), `v*` tags now run
  the full suite so a release carries its own green, every job has a timeout,
  and the shared-scenarios checker bounds each Hugo subprocess -- a wedged
  build once idled a CI job for six hours before cancellation ever spoke.
- Housekeeping: dead selectors left behind by retired markup are gone
  (`.td-shell-toc__title`, the sidebar-footer language-selector wrapper, the
  retired image shortcode's `.td-figure__image`, two `.td-navbar` scopes from
  the Docsy era), SCSS entry-point comments point at the pages that exist
  today instead of a retired information architecture, and an unreachable
  test expression lost its dead branch.
- The outline's lit range reads in the section's accent, not just its cursor.
  `docs-shell.js` marks every heading the viewport stands over; those entries
  now take the same theme-color ink the rail's lit line and travelling dot
  already carry, and the cursor entry alone keeps the pill ground, so the ink
  and the line tell one story instead of two.
- The cursor pill is the same height on every outline row. The first and last
  entries trim the padding that would push the list off the body's edges, and
  the pill -- drawn inside the link box -- silently shrank with them; each
  trimmed side now compensates by the 5px the box no longer carries.

## [0.6.1] - 2026-08-22

### Changed

- The home page's navbar takes the soft boundary a hero page already had. A
  landing opens on artwork over a ruled grid, and the shell's bottom rule cut
  a hard line straight across that composition -- the one surface where the
  bar has no article column to separate itself from. `.td-home .td-site-header`
  now drops the rule and the scrolled shadow and resolves into a short wash
  below the bar instead, keeping the translucent background and backdrop blur.
  Every other surface is untouched.

### Fixed

- A pinned navbar occupies the band the shell reserved for it. Fixed rails
  clear `--td-shell-nav-h` (the 50px navbar height), and the auto-hide band
  reserves exactly that, but a pinned `.td-site-header` measured 51px: its
  bottom rule sat below the band rather than inside it. Every surface that
  pins the bar therefore started its article column one pixel under the fixed
  outline rail, so the breadcrumb row and the outline heading beside it never
  quite lined up. The header now takes `height: $td-navbar-min-height` under
  border-box sizing, with the container and nav row inheriting it, so the rule
  is drawn inside the reserved band and the two rows share a baseline again.
- A stored blog index form no longer blanks a section that publishes one form.
  `prepaint.html` writes the reader's `td-blog-index` choice onto the root
  element of every shell page, and the `html[data-td-blog-index=…]` rules
  applied to any `.td-blog-posts` they found -- so a reader who cycled to
  cards or table anywhere, then opened a section whose `blog_index_toggle` is
  off, had the one form that section emitted hidden in favour of markup that
  was never rendered: the index kept its title and description and listed
  nothing. The index now declares what it published (`data-td-blog-forms="all"`,
  emitted only under the toggle) and the reader-choice rules are scoped to it,
  so a single-form section always shows its form and a stored choice still
  governs every index that carries all three.
- The blog table's date column keeps its gap. `.td-blog-table td` sets the
  cells' padding, and an element-and-class selector outranks the bare
  `.td-blog-table__date` that declared the 1rem separating a date from the
  title beside it -- so the declaration never landed, and any locale whose
  dates run longer than the ISO default (`February 14, 2026`, `2026年01月02日`)
  rendered them butted straight against the title. Both the date's trailing
  gap and the tag column's leading one now sit on the base rule, at the
  specificity that wins.

## [0.6.0] - 2026-08-20

### Added

- The immersive blog presentation. A Blowfish-style reading page -- a
  full-bleed hero opening, no chrome but the outline, every blog component in
  its usual place below the fold -- is not a new shell or type but four
  orthogonal front-matter keys on the ordinary blog shell, written per page
  or once per section in a cascade. `featured_image` gains the `hero` mode:
  the blog baseof paints the page's resolved image as the shell's own
  decorative backdrop, masked out before the text starts, with the opening
  moved down to give it the top of the viewport -- and because the shell
  paints it, a section index opens its list under the same hero as its pages,
  which is what turns the release section into a hero-headed archive. A
  navbar over a hero renders as an overlay in normal flow, on a fading
  contrast scrim, that scrolls away with the image and reserves no height.
  Two new parameters carry the rail: `ui.toc_style: flow` swaps the
  viewport-pinned outline for a wider in-flow one that starts with the
  article and pins only on scroll -- deliberately independent of the
  hero, so a section keeps one rail whether or not each page carries an
  image -- and `ui.toc_taxonomies: false` removes the right-rail term clouds,
  with a rail left holding nothing rendering nothing at all. The flow rail's
  resting place aligns with the article's info line, or its description where
  a page has no info line, measured by docs-shell.js because a title wraps to
  an unknown number of lines; without JavaScript it starts where the article
  starts. The remaining key already existed (`sidebar_enabled`), and the blog
  shell renders no breadcrumb of its own -- see below -- so the recipe needs
  no key for it. Every switch degrades rather than errors, and nothing about
  the page's type, pager sequence, feeds, or lists changes.

- The blog article head, recomposed. Under the title: one info line -- the
  date, the localized author-and-section phrase, the word count and the
  minutes when `reading_time` is on, and, when front matter `upstream_link`
  names the material the page is derived from (the same per-page fact the
  annotation attributes), a localized *Read More* link to the original, gated
  by the shared URL policy. Then the page's
  terms as a bare badge row -- the taxonomy's name moves to the group's
  `aria-label` instead of a visible `Tags:` prefix -- then the byline: no
  label, just each author's portrait beside their name and the profile's
  one-line bio, the whole pair linking to the profile. Then the series strip,
  and the description leads the body below them. Three strings join the 32
  locales for the line (`post_word_count`, `post_reading_minutes`,
  `post_read_original`) and three leave it unused (`post_byline_by`,
  `post_posts_in`, `ui_series_next`); the reading-time chip's class gains its
  missing `td-` prefix (`td-reading-time`). List rows, cards, and term
  archives share one metadata line -- date, one localized author-and-section
  phrase, word count and minutes, and, on rows, the post's tags as trailing
  badges on the same line -- so `post_meta_by_in` and `post_meta_in` drop
  their embedded date; a card reduces the line to the date and the author,
  its own tags row carrying the rest. And because an article reads
  as a standalone piece rather than a place in a tree, the blog shell now
  renders no breadcrumb by default; `breadcrumb: true` on a page or cascade
  turns it back on.

- The featured image on the article itself. The theme resolved one image per
  page and rendered it in list rows and social cards, but never on the post,
  so authors wrote the hero by hand: across the eleven consuming sites, 559
  articles open with a literal `[![featured](...)](...)` above their first
  paragraph, duplicating the `images` value the front matter already carries.
  `params.ui.featured_image` renders it instead -- `banner` frames it above the
  title in a fixed 16:9 figure so a run of articles keeps one rhythm, `wash`
  lays it behind the article header at a tenth of its opacity, masked to
  nothing before the text starts, so a post takes a colour from its subject
  without spending any contrast on it. It draws from
  `featured-image-resolve.html` like every other consumer, so the image at the
  top of an article and the image its card carries cannot disagree, and it adds
  no runtime, no Page Store flag, and no bundle member. The default is `none`
  and blog articles are the only pages that call it, so a site that renders
  nothing today renders exactly the same bytes. Front matter `featured_image`
  turns one page or, in a cascade, one section on or off; an article with no
  image renders nothing in either mode, because a section can carry the switch
  for posts that do not all carry art.
- Multiple authors, with profiles and bylines, from one taxonomy declaration.
  `taxonomies: {author: authors}` is the entire switch -- the theme adds no
  parameter. An author's profile is the term page: `title` is the display
  name, `description` the one-line introduction, the body the long one, and
  the avatar whatever `featured-image-resolve.html` selects for that page, so
  `images:` and a bundled portrait follow the same rules an article's featured
  image follows and a bilingual profile is an `_index.zh.md` beside it. There
  is deliberately no `data/authors` second authority to disagree with the
  page. An article head renders portraits and linked names in the order the
  page listed them -- `GetTerms` preserves the front matter sequence, so
  `authors:` is both the set and the order -- a list row renders the names,
  and the blog feed declares `xmlns:dc` and emits one `<dc:creator>` per
  author per item beside the untouched site-level `managingEditor`. Names are
  separated by CSS gap rather than punctuation, because a connector word is a
  per-locale decision and there are 32 of them. A term a post names but no one
  gave a profile page still bylines: link title, initial, archive link. The
  0.4 `author:` string remains Markdown-capable where `authors` is absent;
  neither form warns about the other, and both share the article-info date.
  Because the byline is now the author surface, the generic taxonomy chip row
  skips the reserved plurals `authors` and `series` unless a site names them
  in `params.taxonomy.page_header`.
- A page-end share bar, behind `params.ui.share`. The page end had no way to
  hand an article on: a reader who finished a post could rate it, see where it
  came from, page to the next one, and comment, but the one thing a reader
  actually does with a good post -- send it to someone -- had no affordance at
  all, so every site grew its own. `params.ui.share` takes a list drawn from
  sixteen targets -- `x`, `bluesky`, `mastodon`, `facebook`, `linkedin`,
  `reddit`, `hackernews`, `telegram`, `whatsapp`, `line`, `pinterest`, `weibo`,
  `chatgpt`, `claude`, `email`, and `copy` -- and is empty by default; a section
  cascade scopes the bar to the tree that wants it, a page's own list replaces
  the inherited one, and `share: false` opts one page out. An unknown target
  warns and is dropped. Only a regular page renders the bar -- a list, a term,
  and the home page have no single thing being shared -- and print, Markdown,
  and RSS carry none of it.

  Each entry is the endpoint that platform itself documents, and they disagree
  about how a permalink and a title reach a compose box, so the catalog names
  the shape rather than repeating the argument order: the URL alone, the URL
  and the title as separate parameters, the title before the URL, one merged
  `Title URL` string for a plain-text compose box, Pinterest's pin (whose
  `media` image comes from `featured-image-resolve.html`, so a pin and the
  page's own social card cannot disagree), and an assistant prompt naming the
  permalink. `chatgpt` and `claude` are that build-time permalink and nothing
  more -- not the `open_chatgpt` / `open_claude` actions the runtime rewrites
  to the live browser URL, which is why those stay behind
  `page_context_menu.assistant_links` and these two do not. Discord is absent
  on purpose: it publishes no share-intent URL at all, so `copy` stands in for
  it rather than the theme guessing at a private scheme.

  The bar itself is one centred row of rounded-square tiles, each on a quiet
  tint of its own that floods with the theme colour under the pointer: no
  heading over it, and no rule of its own, because whatever follows it at the
  page end already draws the hairline that closes the article. The name it does not show lives on the
  group's `aria-label`, so it is still announced as Share.

  What the bar does *not* do is the reason it can exist here at all. There is
  no share count, no platform SDK, no iframe, and no third-party script or
  stylesheet, which is what those three normally arrive as: one request per
  page to a company the reader never chose, on every page, whether or not
  anyone shares anything. Every target is a plain `<a href>` intent link
  carrying only the page's own permalink and title, with no campaign
  parameters attached, plus one local copy button. Nothing is fetched when the
  site builds or when the page loads; the only request a share can cause is
  the navigation the reader starts by clicking. A build with every target
  enabled passes `bin/check-output-security.py` with no `--third-party`
  allowance, and `bin/check-shell.py` now proves that on each run.
- `copy_link`, a built-in action that copies the page's canonical URL. The
  share bar renders it, and because it is a registry action rather than a
  widget the Command Palette carries it on every page of every site -- the
  half of the share bar that turns out to be useful even where no bar is
  configured.
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
  carries no `upstream_link` warns and emits no attribution;
  `upstream_link: ""` is the deliberate opt-out. An incomplete attribution or
  unknown SPDX identifier likewise warns and emits no legal notice, while a
  non-boolean `upstream_modified` warns and falls back to unmodified. Strict
  builds reject each warning with `--panicOnWarning`.
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
- Three forms for the blog index, and a reader-side cycle between them.
  `params.ui.blog_index: cards` renders a blog section's list page as a grid
  of the shared content cards -- `params.ui.blog_index_columns` wide, two
  between the md and xxl breakpoints, one below md -- instead of the row
  list, which stays the default; `blog_index: table` renders the whole
  section as one compact table, a row per post with the date, the linked
  title, and the post's tags right-aligned as term-page badges, horizontal
  rules only, no pagination -- the form for a section whose point is scanning
  many entries at once. A card opens with a 16:9 crop of the lead image
  through Hugo's `.Fill`, then the date and author -- then the post's tags as badges,
  each linking to its term page, then a three-line summary. The list and
  cards forms are one flat run, newest first, sharing pagination
  (`blog_index_size`) and `manual_link` external semantics; the metadata
  line's dates make year headings redundant, so there are none. Front matter
  `blog_index` on the blog root, or its cascade, overrides the site value per
  section, and `params.ui.blog_index_toggle` puts every form in the document
  with one toolbar control, left of the feed button, that cycles list, cards,
  table: all three share the current paginator slice, the published form still
  decides the first paint, a stored choice wins after it, and hidden forms load
  no images. A table published without the toggle remains a complete archive.
  Term and taxonomy pages keep the row list.
- Article series. Declaring the taxonomy -- `taxonomies: {series: series}` --
  is the whole switch: no theme parameter, no metadata file, no cover model.
  The term page `content/series/<name>/_index.md` is the introduction, and a
  `_index.zh.md` beside it makes the pair bilingual. An article names
  `series: [<name>]` and may add `series_weight` to place itself, and gets a
  strip above its body: one closed `<details>` line naming the series and its
  position -- part M of N -- that expands to the whole reading order, one
  member per line, and prints expanded. No JavaScript, no bundle member. Reading
  order is the theme's own, because a term page cannot supply it: an unweighted
  term arrives newest first, a mixed one puts unweighted members before weight
  1, and the taxonomy weight reaches neither `Page.Weight` nor `GroupByParam`.
  `series-pages.html` resolves it once -- weighted members ascending, the rest
  by ascending date, `Path` breaking a tie -- and the strip and the term page
  both read it, so they can never disagree about which article is part 2. A
  series term page therefore changes from reverse-date to reading order, which
  is the feature. A member of several series shows one strip, for the first
  term it names, and its scalar
  `series_weight` applies to every membership; a series of one shows none.
  `series` and `authors` both stay
  out of the default taxonomy chips row, since each has a surface of its own.
  A series is a reading path through articles that stand alone: numbering,
  cross-references, and aggregate output remain Book's.

### Changed

- Chrome links glide into the link color. Navbar entries, dropdown rows,
  utility and dock triggers, and the footer's text links now share one hover
  vocabulary: text and glyph fade to the link color while the soft ground
  fades in beneath them, on the 150ms Tailwind colors curve
  (`--td-shell-ease-color`) instead of a hard background swap. Every other
  anchor sitewide — article links, sidebar and TOC entries, cards, badges,
  pagers — inherits the same colors transition from the base layer, so any
  hover that changes color, background, or border glides instead of
  snapping. Reduced motion zeroes the shared duration tokens, so the fades
  collapse to instant changes there.
- A lazy image inside the zoom trigger reserves its box before it loads.
  The trigger's `fit-content` width and its image's `inline-size: 100%`
  chased each other in a circle that resolved to zero, so below-the-fold
  figures collapsed and then jumped as their images arrived; the image now
  keeps its own attribute-driven size under a `max-inline-size` clamp.
- The auto-hidden navbar keeps its slot. With `navbar_autohide` the bar no
  longer collapses into a floating overlay that reclaims its height: the
  sticky band stays in the layout in both states, so the article title and
  table of contents sit exactly where a visible navbar would put them, and
  revealing simply fades the bar in over its own band instead of covering
  content. Hero pages keep their overlay bar and ignore the policy. The
  content start line moves down a touch (`--td-shell-content-top` 2.5rem to
  2.75rem, hero offset `clamp(150px, 32vh, 360px)`), and the hero navbar is
  now solid through its control row with the wash fading in over a band
  below the bar, so the featured color never touches the search box.
- **Breaking.** Dropdown panels are one column of icon-and-title rows. The
  0.5 mega panel is retired together with its `columns` menu parameter --
  setting `columns` now emits a targeted warning and the panel keeps its
  single moderate-width column -- and menu `description` values are
  configuration data that no dropdown or drawer renders. The Home/Landing
  drawer rows adopt the docs drawer's quiet vocabulary (14px rows, soft
  hover pill, primary-dim active state), and the footline's four dock
  triggers share one 14px glyph size.
- The compact navbar keeps its tree centered and gains a phone drawer entry.
  Between lg and md the icon links sit true-centered between the brand and
  the full utility cluster -- search, version, language, theme, GitHub --
  with no menu button. Below md those utilities leave for the footline dock
  as before, and Home and explicit Landing pages -- the navbar-only
  surfaces -- add one drawer entry beside search that opens the full
  labelled menu tree. Other widths and surfaces render no drawer entry.
- Taxonomy chips wear their taxonomy. A term badge -- the article's page-end
  row, the blog meta line, cards, the table's tag column -- is now a solid
  brand chip with the label knocked out of the fill, led by a glyph that says
  which classification it names: `folder` for a category, `tag` for a tag,
  `cube` for a module, `user-pen` for an author, `book` for a series,
  `shapes` for anything else. The whole classification wears the plural of
  the same glyph -- `folder-open`, `tags`, `cubes`, `users`,
  `book-bookmark` -- on the right-rail cloud head, and only there: cloud
  chips and the term-archive filter chips stay text plus count, since a glyph
  repeated beside an announced taxonomy is noise. One partial
  (`taxonomy-icon.html`) owns the vocabulary; `ui.taxonomy_icons` still
  overrides per plural, now with either one string for both surfaces or a
  `taxonomy`/`term` map, and an unusable icon warns and keeps the built-in.
- The index metadata unit is a sentence plus a badge line. List rows and
  cards put every taxonomy's terms -- taxonomies in alphabetical order, each
  badge wearing its term glyph -- on one wrapping line under the meta
  sentence, instead of a tags-only run inside it. Cards leave out `authors`,
  already named in the sentence, and their sentence now carries the word
  count and minutes under the same `reading_time` switch that governs
  everywhere else.
- The global utilities live in the bottom bar. Version, language, theme,
  and the keyboard cheat sheet move from the sidebar footer to a persistent
  icon dock at the end of the footline, opening upward on every rendered
  footer style; the sidebar keeps only navigation. The GitHub link stays in
  the navbar and the fat footer rather than repeating in the dock, and the
  footline version trigger is icon-only while its menu keeps the full
  configured labels.
- Release facts are one URL. The 0.5 `release` map -- product, version, repo,
  tag, date, prev, checksums -- declared seven things a GitHub release URL
  already carries or the page already knows, so front matter is now
  `release_url: https://github.com/<owner>/<repo>/releases/tag/<tag>` and
  nothing else: owner, project, and tag come out of the URL, the date is the
  page's own. The card keeps the four links the URL alone can name -- the
  release, both source archives, and the repository -- and drops the declared
  checksum and comparison links; checksum tables under a note are unchanged.
  The releases index sheds its product filter and grouping
  (`release_products`, `release_group_by_product`) and simply lists every
  page of the section, two lines per entry: the parsed `project tag` -- or
  the page's own title when there is nothing to parse -- with the date
  beside it, and the description under it. The removed map and both removed
  index keys warn naming their replacement.
- Page-end order is now Share, Feedback, Annotation, Pager, Comments. Share
  leads because it is the only block that points outward, and because a reader
  who has decided to pass a page on has decided it before being asked how the
  page went. Sites that enable neither share nor feedback see no change.
- `upstream_attribution` is now `upstream_link` and needs the companion keys
  above; `downstream_modified` is now `upstream_modified`. Both old names warn
  and name their replacement, so strict builds fail without taking down an
  ordinary preview.
- `time_format_blog` and `time_format_default` now default to ISO `2006-01-02`.
  Sites that prefer localized prose dates can retain explicit format strings.
- The theme mounts `data/`, which it did not before, so the licence table
  reaches consuming sites. A site's own `data/licenses.yaml` merges over it.
- The outline's cursor pill is fainter. It shared `--td-shell-primary-dim`
  with the sidebar's current-page marker, but the outline already says where
  the reader is twice -- accent colour and the lit rail -- so the pill only
  needs a breath of tint: `--td-shell-toc-pill-bg`, at roughly half the
  shared value's opacity in both themes.

### Fixed

- The language switch no longer leaves the site. Its links were absolute
  `baseURL` permalinks, so a build viewed anywhere other than its configured
  host -- `public/` behind a local static server, a deploy preview, a LAN
  address -- sent the reader to the configured domain instead of the
  translation, while every other internal link stayed put. Language targets
  are now relative whenever all languages share one scheme, host, and base
  path, and absolute only for a site that gives a language its own `baseURL`.
  `hreflang` alternates keep the absolute form they require.
- Mounted content outside Hugo's working directory no longer leaks an absolute
  build-machine path into GitHub Edit, History, or Create Child links. A site
  may map such a source explicitly with `path_base_for_github_subdir`; without
  that mapping the three source-derived actions stay unavailable while issue
  actions continue to work.
- Invalid or incomplete upstream attribution now warns and emits no legal
  notice at all. Its source, notice, and licence URLs share the theme URL
  policy; unsupported schemes are refused, and a non-boolean
  `upstream_modified` really falls back to unmodified.
- Blog index toggles now render the table from the current paginator slice
  instead of repeating the complete archive on every generated page.
- Incomplete Algolia configuration emits no container, stylesheet, or script.
  Draw.io loads only on pages with PNG/SVG candidates, and language-neutral
  feature bundles are shared across translations.
- Page actions, pager state, language targets, and section-index children no
  longer repeat site-wide work for each consumer or scan the whole site when a
  page-local collection is authoritative.
- The outline dot no longer detaches from the accent line under fast
  scrolling. The dot was tuned to arrive before the range on purpose -- 150ms
  with a hard ease-out against the clip's 250ms ease-in-out -- so the accent
  would read as dragged behind it, but a fast scroll retargets both every
  frame and the "lead" became a visible gap between the dot and the line it
  is supposed to cap. No pair of separate transitions can close that gap:
  retargeting two curves every frame lets them drift, and mid-drift the dot
  sits pinned to nothing. The dot now has no motion schedule of its own. The
  accent is lit by the path's dash pattern, the dash's start and length are
  registered custom properties animated on the overlay, and the dot's offset
  along the same path is *computed* from those in-flight values -- start plus
  none or all of the lit length -- so the line positions the dot and it caps
  the lit line at every frame of every animation. The only thing the script
  chooses is the end: a 0/1 selector with a fast transition of its own, so a
  change of reading direction is one quick flick of the dot along the lit
  line to its other end. The script registers the three properties with
  `CSS.registerProperty` -- an `@property` rule would not survive the CSS
  minifier -- and an engine without registered properties snaps the rail
  into place, still glued. The line's own chase is retuned for the same
  reason the dot was: it moved at 250ms ease-in-out, and a fast scroll
  retargets that transition on every heading it passes, which restarts an
  ease-in-out into the slow opening of its curve each time -- the lit line
  fell whole entries behind the links the list had already coloured. It now
  moves at the base duration with a hard ease-out, which makes its progress
  up front, so every retarget advances the line at once and it stays under
  the entries being highlighted however fast the page scrolls.
- Field anchors a reader can actually derive. Every Fields entry already
  carried an id and a self-link, but the slug came from `anchorize`, Goldmark's
  rule for prose headings, which *deletes* punctuation rather than converting
  it. Field names are identifiers, and the ones worth linking to are the
  punctuated ones: `params.ui.typography` anchored as
  `#field-paramsuitypography`, `pg.exporter.port` as `#field-pgexporterport`,
  `data-*` as `#field-data-`. The anchor existed and no one could guess it, so
  in practice a parameter could not be linked from outside the page without
  first reading the generated HTML. The slug now lowercases the name and
  collapses each run of punctuation into a single hyphen, trimming what is left
  at the ends: `#field-params-ui-typography`, `#field-pg-exporter-port`,
  `#field-data`. `_` stays a word character, because configuration keys carry
  meaning in it, and Unicode letters survive, so `搜索模式` still anchors as
  itself. Names made only of word characters -- `offline_search`, `page_width`,
  `enable` -- are byte-identical to before; the anchors that change are the ones
  that were unusable. Duplicate names keep their positional `-2`, `-3` suffixes,
  and print and RSS still emit no entry anchors at all.
- Give each field description its own render scope. The scope prefixes every id
  a nested render hook generates inside a shortcode body, so it has to be unique
  per body -- and `fields` derived it from the field name, which is not: `a.b`
  and `ab` collapse to one scope, so two `field` bodies containing a code block
  emitted the same `td-code-…-fence-0` id. The scope is now the entry anchor,
  which the anchor registry has already made unique, so the one allocation
  answers both questions. Generated ids inside field descriptions change shape
  accordingly (`…-fields0---dry-run-fence-0` becomes `…-field-dry-run-fence-0`);
  they are generated, not authored, and nothing links to them.
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
  body. Both now warn and remain literal, naming the native form; strict builds
  reject the warning. A table, image, or fence carrying `{num=… caption=…}`
  keeps its content in the page document,
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
- Move public documentation, examples, tutorials, and case studies to
  `oink.pgsty.com`. Keep the checker suite's self-contained `tests/site/` as the
  only in-repository fixture, with its content, media, layout overrides, and
  output goldens isolated from the public documentation site.

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
  listed in the public
  [component contract](https://oink.pgsty.com/docs/design/components/).
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
  cannot express. The public
  [component contract](https://oink.pgsty.com/docs/design/components/) is the
  authoring guide.
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
- Print aggregates render each page once through `partialCached`. Nested
  `RenderString` calls no longer put a temporary ID scope in the shared Page
  Store: automatic code IDs are namespaced after rendering, explicit IDs stay
  unchanged, and final documents still reject duplicates. Concurrent Book and
  section print outputs therefore cannot leak scopes into one another.
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

[Unreleased]: https://github.com/pgsty/oink/compare/v0.7.1...HEAD
[0.7.1]: https://github.com/pgsty/oink/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/pgsty/oink/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/pgsty/oink/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/pgsty/oink/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/pgsty/oink/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/pgsty/oink/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/pgsty/oink/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/pgsty/oink/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/pgsty/oink/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/pgsty/oink/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/pgsty/oink/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pgsty/oink/releases/tag/v0.1.0
