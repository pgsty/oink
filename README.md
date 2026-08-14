<h1 align="center">
  <a href="https://oink.pgsty.com/">
    <img src="https://raw.githubusercontent.com/pgsty/oink/main/images/logo.svg" alt="OINK" width="420">
  </a>
</h1>

<p align="center">
  <strong>Open. Indexed. Navigable. Knowledge.</strong><br>
  A local-first Hugo theme for engineering documentation.
</p>

<p align="center">
  <a href="https://oink.pgsty.com/"><img alt="Website" src="https://img.shields.io/badge/website-oink.pgsty.com-17385c?style=flat-square"></a>
  <a href="https://github.com/pgsty/oink/tags"><img alt="Version" src="https://img.shields.io/github/v/tag/pgsty/oink?sort=semver&amp;label=version&amp;style=flat-square"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/pgsty/oink?label=license&amp;style=flat-square"></a>
</p>

OINK gives engineering teams a complete documentation system without making
consumer sites maintain a frontend toolchain. The theme bundles its assets and
feature runtimes locally; Hugo Extended turns Markdown into a deployable static
site with no Node.js, npm, PostCSS, or CDN dependency.

## Why OINK

- **Local-first delivery.** One Hugo build produces an auditable, portable site
  whose core assets work without third-party networks.
- **Documentation at scale.** Responsive docs and blog shells, navigation,
  full-text search, table of contents, dark mode, RSS, SEO, and print views are
  built in.
- **Multilingual by design.** Language-aware routing, translated-page fallback,
  RTL support, and alternate-language metadata support serious international
  documentation.
- **Engineering-native content.** Diagrams, formulae, API references, terminal
  recordings, charts, cards, tabs, and carousels load only when a page needs
  them.
- **Proven foundation.** OINK evolves Docsy's mature content model with a
  focused interface and site-owned extension points.

## Quick start

Requires Git, Go, and **Hugo Extended 0.160.1 or newer**.

```sh
hugo mod init github.com/example/docs
hugo mod get github.com/pgsty/oink@latest
```

Add OINK to `hugo.yaml`. Hugo leaves output selection to the consuming site, so
enable the formats and interactive features you want explicitly:

```yaml
module:
  imports:
    - path: github.com/pgsty/oink

outputs:
  home: [HTML, RSS, markdown, LLMS]
  page: [HTML, markdown]
  section: [HTML, RSS, print, markdown]

params:
  # Book content measure: slim | norm | wide (default: norm).
  content_width: norm
  copyright:
    authors: '[Example Documentation](https://example.org/)'
    from_year: 2026
  # footer_center_info defaults to Powered by Oink and accepts inline Markdown.
  offlineSearch: true
  ui:
    showLightDarkModeMenu: true
    image_zoom:
      enable: true
```

`markdown` enables Copy text and View source, `LLMS` emits `llms.txt`, and
`print` enables section print views. Offline search, assistant handoff links,
the theme menu, and native image previews are opt-in; the theme supplies their
implementation but does not silently enable site policy. A page can override
Image Zoom with the same nested `params.ui.image_zoom.enable` front matter key.
Book pages can likewise override `content_width`; this controls the inner
reading measure while `page_width` continues to control the surrounding shell.

Then preview the site:

```sh
hugo server
```

### Delimiter-style mathematics

OINK renders fenced `math` code blocks out of the box. To author inline
`\( ... \)` or block `\[ ... \]` / `$$ ... $$` formulae, the consuming site
must also enable Hugo's Goldmark passthrough extension:

```yaml
markup:
  goldmark:
    extensions:
      passthrough:
        enable: true
        delimiters:
          block: [['\[', '\]'], ['$$', '$$']]
          inline: [['\(', '\)']]
```

Hugo does not merge a theme module's `markup` configuration into the consumer,
so OINK cannot enable this on a site's behalf. A passthrough configuration with
no matching render hook silently leaves delimiter text such as `$$` in the
page; OINK supplies that hook and renders KaTeX locally at build time. The
legacy Hextra front matter key `math: true` has no meaning in OINK and is not a
substitute for the Goldmark configuration above.

For an isolated display formula on a site that cannot enable passthrough yet,
use `{{< eq >}}E = mc^2{{< /eq >}}`. This parameter-free escape hatch is
unnumbered; the Book form adds an explicit `num`.

For production, pin a release tag in `go.mod`. See the
[getting-started guide](https://oink.pgsty.com/docs/tutorial/) for site
structure, configuration, and deployment.

The shell defaults to content whose Hugo type is `docs`, `book`, `blog`, or `swagger`.
Sites with a different docs path can set `params.ui.docs_section` (for example,
`guide`) and use a front matter cascade with `type: docs`; additional types can
be added through `params.ui.shell_types`.

## Typography presets

OINK keeps font choices behind semantic CSS custom properties. The default
`technical` preset preserves the OINK display and monospace faces. A site that
wants the platform font stack, with no OINK brand-font requests, can select:

```yaml
params:
  ui:
    typography:
      preset: system
```

Both presets are compiled by Hugo into the same static stylesheet. They add no
JavaScript, package-manager step, remote font service, or runtime stylesheet.
Sites can locally host their own faces and override the documented
`--td-*-font-family` roles in `assets/scss/_styles_project.scss`; see the
[typography token reference](docs/typography-tokens.md).

## Example sites

- [oink.pgsty.com](https://oink.pgsty.com/) —
  [source](https://github.com/pgsty/oink.pgsty.com) — the bilingual
  documentation, feature showcase, and regression site.
- [`exampleSite/`](exampleSite/) — a minimal composable landing page that runs
  directly from this checkout with `cd exampleSite && hugo server`.

## Documentation

[Configuration](https://oink.pgsty.com/docs/content/configuration/) ·
[Components](https://oink.pgsty.com/docs/content/components/) ·
[Examples](https://oink.pgsty.com/docs/about/examples/) ·
[Deployment](https://oink.pgsty.com/docs/deploy/) ·
[Contributing](https://oink.pgsty.com/docs/about/contributing/)

Theme implementation contracts:
[Content primitives](docs/content-primitives.md) ·
[Enhanced code blocks](docs/enhanced-code-blocks.md) ·
[Typography tokens](docs/typography-tokens.md) ·
[PRD 4 contract](docs/prd4-navigation-command-palette-contract.md) ·
[PRD 5 reading/release](docs/prd5-reading-release-contract.md) ·
[PRD 5 landing](docs/prd5-landing-contract.md) ·
[PRD 5 Book](docs/prd5-book-contract.md)

Navigation and Command Palette migration reference, included in 0.3.0:
[English](docs/prd4-migration-guide.md) ·
[简体中文](docs/prd4-migration-guide.zh.md).

Scenario Components migration reference (all tracks included in 0.4.0; the
original 0.4.0–0.6.0 design milestones remain documented as history):
[English](docs/prd5-migration-guide.md) ·
[简体中文](docs/prd5-migration-guide.zh.md).

Book content rewrite recipes:
[TPME](docs/prd5-migrate-tpme.md) ·
[DDIA](docs/prd5-migrate-ddia.md) ·
[pg-internal](docs/prd5-migrate-pg-internal.md).

## Localization status

English, Simplified Chinese (`zh-cn` and generic `zh`), and Traditional Chinese
(`zh-tw`) have complete reviewed OINK interface text. Every other bundled locale
has the same key schema and keeps its inherited Docsy translations; new
OINK-only labels currently use explicit English fallback text pending community
translation.

## License

OINK is licensed under the [Apache License 2.0](LICENSE) and derived from
[Docsy](https://github.com/google/docsy). See [NOTICE](NOTICE) for upstream
attribution and [VENDOR.json](VENDOR.json) for bundled third-party components.
