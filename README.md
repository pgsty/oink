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
  recordings, charts, file trees, galleries, cards, and tabs load only when a
  page needs them.
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

# Hugo does not merge a theme module's Goldmark configuration into the site.
# These three settings are required by OINK's native component forms.
markup:
  goldmark:
    renderer:
      unsafe: true # `%` container shortcodes emit HTML that Goldmark must keep
    parser:
      wrapStandAloneImageWithinParagraph: false # block images carry attributes
      attribute:
        block: true # {.steps}, {.fields}, captions, numbered Book targets

params:
  # Book reading measure: slim | normal | wide (default: normal).
  reading_width: normal
  copyright:
    authors: '[Example Documentation](https://example.org/)'
    from_year: 2026
  # footer_center_info defaults to Powered by Oink and accepts inline Markdown.
  offline_search: true
  # `hugo server` builds the search index too (default); set false to skip it.
  offline_search_on_serve: true
  ui:
    dark_mode:
      show_menu: true
    # Hide the 50px navbar until a mouse reaches the top edge; touch stays visible.
    navbar_autohide: false
    # Optional one-click docs feedback; records structured gtag events only.
    feedback:
      enable: false
      reasons: true
    image_zoom: true
```

Before migrating content, verify the consuming site's resolved configuration:

```sh
python3 path/to/oink/bin/check-site-markup.py --site .
```

`markdown` enables Copy text and View source, `LLMS` emits `llms.txt`, and
`print` enables section print views. A top-level section that lists `LLMSFULL`
in its own front matter `outputs` additionally publishes `llms-full.txt` — the
whole section's semantic Markdown in reading order, one file per language,
linked from `llms.txt` for agents that want the full text in one fetch. Offline search, assistant handoff links,
the theme menu, and native image previews are opt-in; the theme supplies their
implementation but does not silently enable site policy. A page can override
Image Zoom with the front matter key `image_zoom` — every `params.ui.*` switch
that a page may override uses the site key without its `ui.` prefix. Book pages
can likewise override `reading_width`; this controls the inner reading measure
while `page_width` continues to control the surrounding shell.
Set `params.ui.navbar_autohide: true` to tuck the navbar above the viewport on
mouse-driven devices at the `md` breakpoint (768px) and above and reveal it
from the center of the top edge. The two 64px corners stay inactive for
collapsed-rail controls, while touch pointers and every drawer-width viewport
keep the sticky navbar visible. The home page is exempt: a landing page shows
its navbar even when the site-wide setting is on (its own front matter can
still set `navbar_autohide: true`). A section cascade or page can override the
policy with the top-level `navbar_autohide` front-matter key. This differs from
`navbar_enabled: false`, which omits the navbar completely.

`params.ui.feedback.enable: true` adds a “Yes / No” prompt. A click
immediately emits a `docs_feedback` event through an existing `gtag` function;
an optional reason emits a refining event with `refinement: true`. OINK does
not send free text and needs no endpoint. When Giscus comments are active, the
result also links readers to the comments section for a detailed report. Use a
Docs/Book/Swagger section cascade to enable it only where it is useful.
When upgrading an older feedback configuration, remove `yes`, `no`,
`max_value`, `endpoint`, and `max_length`; the one-click model does not use a
Worker or a submission endpoint.

Then preview the site. When `offline_search` is enabled, `hugo server` builds
the local index by default so preview matches production. Large sites can skip
that work for an edit loop with the parameter override below (the `x` is Hugo's
alternate key delimiter because the key contains underscores):

```sh
hugo server
HUGOxPARAMSxOFFLINE_SEARCH_ON_SERVE=false hugo server
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
    typography: system
```

Both presets are compiled by Hugo into the same static stylesheet. They add no
JavaScript, package-manager step, remote font service, or runtime stylesheet.
Sites can locally host their own faces and override the documented
`--td-*-font-family` roles in `assets/scss/_styles_project.scss`; see the
[architecture contract](https://oink.pgsty.com/docs/design/architecture/#trust-css-and-accessibility).

## Documentation and fixtures

- [oink.pgsty.com](https://oink.pgsty.com/) —
  [source](https://github.com/pgsty/oink.pgsty.com) — the bilingual
  documentation, tutorial, case-study, feature-showcase, and regression site.
- [`tests/site/`](tests/site/) — the self-contained internal fixture used by
  theme checkers and output goldens. It is test input, not public documentation.

## Documentation

[Get started](https://oink.pgsty.com/docs/start/) ·
[Components](https://oink.pgsty.com/docs/components/) ·
[Cases](https://oink.pgsty.com/case/) ·
[Book](https://oink.pgsty.com/book/) ·
[Administration](https://oink.pgsty.com/docs/admin/)

Theme maintainer Design:
[index](https://oink.pgsty.com/docs/design/) ·
[architecture](https://oink.pgsty.com/docs/design/architecture/) ·
[components](https://oink.pgsty.com/docs/design/components/) ·
[shell, navigation, and actions](https://oink.pgsty.com/docs/design/shell/) ·
[Landing](https://oink.pgsty.com/docs/design/landing/) ·
[Migration boundaries](https://oink.pgsty.com/docs/design/migration/) ·
[proposals](https://oink.pgsty.com/docs/design/proposals/).

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
