# PRD 5 landing contract

Version assignment: OINK 0.5.0 (source contract; not a publication claim)

Contract version: 1

Status: frozen for implementation

Compatibility floor: Hugo Extended 0.160.1

This document freezes the Landing track of PRD 5. Its machine-readable
companion is `tests/fixtures/prd5/contract.json`; `scripts/check-prd5-contract.py`
keeps the two aligned. Configuration and migration guidance are available in
[English](prd5-migration-guide.md) and
[Simplified Chinese](prd5-migration-guide.zh.md).

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
`offlineSearch`. `params.ui.github_stars` and `params.ui.alt_site` are optional
local chrome facts; no runtime retrieves either value.

## 2. Section registry

The canonical registry keeps the existing `hero`, `metrics`, `capabilities`,
`principles`, `cards`, `logo-wall`, `gallery`, `testimonials`, `contributors`,
`faq`, `markdown`, and `cta` sections. OINK 0.5 adds `pricing`,
`pricing-compare`, `command-box`, `steps`, `timeline`, `code-plate`,
`case-study`, `download`, and `bar-chart`.

Each section entry may be a type string or a map with `type`, `key`, `id`,
`enabled`, inline `data`, or a deliberate local `partial` escape hatch. IDs are
anchor-safe and unique. Unknown types warn rather than silently disappearing.
The legacy `home/` partial names remain thin compatibility adapters; the
`landing/` family owns the implementation.

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
the shared `oink-theme-change` event and also observes the document theme.

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

The inherited Docsy block shortcodes remain render-compatible but are
deprecated for new Landing work. OINK does not add a pricing-period toggle,
remote facts, browser API fetches, image hotspots, a visual page builder, or a
second component registry. Existing homepage data and compatible custom
partials remain valid while sites migrate incrementally.
