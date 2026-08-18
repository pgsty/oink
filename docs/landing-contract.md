# Landing contract

Status: current for OINK 0.5.0

Compatibility floor: Hugo Extended 0.160.1

This document owns the Landing-specific contract. Shared build and component
rules live in [architecture.md](architecture.md) and
[components.md](components.md); upgrade guidance lives in
[migration.md](migration.md).

## 1. Landing shell and data authority

Any regular content page may declare `layout: landing`. The shell renders the
site navbar, a full-width main canvas, and the configured footer without docs
sidebars or table-of-contents rails. The homepage keeps `data/home/<lang>.yaml`
as its compatible authoring path while internally using the same renderer.

A non-home Landing page resolves its source in this order: inline front matter
`sections`, `data/landing/<key>/<lang>.yaml`, an exact language entry in a
single `data/landing/<key>.yaml`, then the English or unsuffixed local record.
The page never fetches remote content or mutable facts. GitHub stars, pricing,
screenshots, and avatars are committed or generated locally before Hugo runs.

`params.ui.landing_search` is a strict boolean and defaults to true. It enables
the existing local Command Palette only when the site has also opted into
`offline_search`. `params.ui.github_stars` and `params.ui.alt_site` are optional
local chrome facts; no runtime retrieves either value.

## 2. Section registry

The canonical registry keeps the existing `hero`, `metrics`, `capabilities`,
`principles`, `cards`, `logo-wall`, `gallery`, `testimonials`, `contributors`,
`faq`, `markdown`, and `cta` sections. OINK 0.5 adds `pricing`,
`pricing-compare`, `command-box`, `steps`, `timeline`, `code-plate`,
`preview`, `case-study`, `download`, and `bar-chart`.

`preview` places a Markdown `source` beside what the theme renders from it.
The rendered pane is `RenderString` through the site's own hooks, so callouts,
step lists, adjacent-fence tabs, and fences appear as they do on a docs page
and register their runtimes on the page store; the source pane is
Chroma-highlighted Markdown on the terminal surface (`data-bs-theme="dark"`)
under a `file` name (default `page.md`). `source` must be a non-empty string.
Markdown output emits the source as a four-backtick `markdown` fence. RSS
follows the Landing-wide contract and omits all sections. The pane labels are
theme i18n (`ui_preview_source`, `ui_preview_rendered`).

`hero.align` is `start` (default) or `center`. `center` is a text-only layout
— the copy block widens and centres, the title balances across lines — and
combining it with `hero.image` fails the build.

Each section entry may be a type string or a map with `type`, `key`, `id`,
`enabled`, inline `data`, or a deliberate local `partial` escape hatch. IDs are
anchor-safe and unique. Unknown types warn rather than silently disappearing.
The `landing/` partial family owns the implementation; removed `home/` partial
names are not a compatibility API.

The `download` section consumes the same validated
`data/download/<key>.yaml` record as the 0.4 shortcode. It does not introduce a
second version, channel, publication-state, or interpolation model.

## 3. Language resolution

Narrative files may be language-specific. Shared fact records resolve fields
in this order: `<field>_<exact language>` with `-` normalized to `_`, then
`<field>_<primary language>`, then unsuffixed `<field>`. camelCase aliases are
not accepted. Section display text is site data, not theme i18n; only
theme-owned controls such as the marquee pause and pricing-state labels use
OINK translation keys.

## 4. Runtime and accessibility

Interactive HTML sets the Page Store flag `hasLanding`; that flag is part of
the shared bundle key and conditionally adds only `landing.js`. The runtime
uses `OinkSurfaceCoordinator` for the compact menu and owns reveal, count-up,
copy, and theme-image enhancement. Its server-rendered content remains complete
when JavaScript is disabled.

Marquee duplication is CSS-only. The duplicate track is `aria-hidden` and
`inert`; a localized checkbox provides a persistent pause without JavaScript.
Reduced motion disables movement and reveal transitions. Forced-colors mode
preserves controls and state distinctions. Theme-image switching listens to
the shared `td-theme-change` event and also observes the document theme.

Navbar mega-menu columns accept integers 1 through 4. The Landing compact menu
uses real links and buttons, traps no focus, closes through the shared surface
coordinator, and never creates a second navigation tree in the DOM for desktop.

## 5. Output matrix

HTML renders the full static section content and progressively enhances it.
Print keeps content, turns motion surfaces into static grids, and removes
controls. Markdown emits headings, prose, lists, tables, and code without
component classes. RSS strips Landing sections. No non-HTML output sets
`hasLanding` or loads a runtime.

Every root-relative asset and internal link honors Hugo's deployment subpath.
Theme-owned image URLs use Hugo resources or subpath-safe local paths; no
normal build downloads a remote image.

## 6. Compatibility and non-goals

The 0.4 component forms removed in 0.5 are handled by the migration toolkit,
not retained as parallel Landing implementations. OINK does not add a
pricing-period toggle, remote facts, browser API fetches, image hotspots, a
visual page builder, or a second component registry. Existing homepage data
and explicit custom section partials remain valid.
