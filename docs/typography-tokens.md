# Typography tokens

Version: included in OINK 0.3.0

Scope: typography only. Semantic colour, surface, radius, shadow, density, and
appearance presets are not part of this interface yet; see the "Scope" section
below.

OINK exposes font choices as CSS custom properties so a consuming site can
change typography without copying component selectors. Hugo Extended still
performs the only asset build: this interface adds no Node.js, npm, PostCSS,
remote font service, or client-side preset loader.

## Presets

Set one of the two built-in values in `hugo.yaml`:

```yaml
params:
  ui:
    typography: technical # technical | system
```

- `technical` is the default. It sets UI and prose in the bundled Inter face
  (variable weight, Latin/Latin-ext/Cyrillic/Greek/Vietnamese subsets served
  by `unicode-range`; CJK and emoji fall through to the platform stack behind
  it), keeps the Chakra Petch and IBM Plex Mono treatment, and uses only
  locally bundled font files.
- `system` resets the UI, display, metadata, and Bootstrap monospace roles to
  platform stacks; body, heading, and print roles follow the UI role. OINK's
  Inter and brand font files remain static theme assets, but the browser does
  not request them with the stock configuration.

OINK emits the selected value as `data-td-typography` on `<html>`. Unsupported
values fail the Hugo build instead of silently changing the site.

## Public roles

| Token | Intended use | Default source |
| --- | --- | --- |
| `--td-ui-font-family` | Navigation, controls, and general chrome | Inter, then `--bs-body-font-family` (`technical`); `--bs-body-font-family` (`system`) |
| `--td-body-font-family` | Article and blog prose | UI role |
| `--td-heading-font-family` | Content headings | `$headings-font-family`, or body role |
| `--td-code-font-family` | Code and terminal content | `$font-family-code` |
| `--td-display-font-family` | Wordmarks and display titles | Chakra Petch, then UI role |
| `--td-meta-font-family` | Technical labels and metadata | IBM Plex Mono, then code role |
| `--td-print-font-family` | Print-only body copy | The body role (the theme ships no print-only face; a site may point the role elsewhere) |

Components consume these roles or a component alias such as
`--td-asciinema-font-family`; they must not name OINK's bundled text faces
directly. The dependency direction is always Bootstrap base token, then OINK
semantic role, then component alias. OINK roles may be seeded by established
Docsy and Bootstrap Sass variables, but Bootstrap custom properties never
reference OINK custom properties. This keeps the runtime dependency graph
one-way and prevents custom-property cycles.

## Docsy and Bootstrap compatibility

Existing Sass customization remains the first input to the token system. OINK
reuses these established variables instead of introducing parallel Sass knobs:

| Existing variable | OINK interpretation |
| --- | --- |
| `$td-fonts-serif` / `$font-family-sans-serif` / `$font-family-base` | Bootstrap body font, then UI and body roles; a project value replaces the stock stack outright, so Inter is not put in front of it |
| `$headings-font-family` | Heading role when explicitly configured |
| `$td-font-family-monospace` / `$font-family-monospace` | Bootstrap monospace base; an explicit project value also survives `system` |
| `$font-family-code` | Code role and ordinary `code`, `pre`, `kbd`, and `samp` |

Declare legacy Sass overrides in `assets/scss/_variables_project.scss`, as in
Docsy. They are compiled into the role defaults. CSS custom-property overrides
in `_styles_project.scss` run later and therefore remain available for
contextual or runtime-independent theming. The `system` preset replaces only
OINK's stock monospace value; an explicit project Sass or custom-property
override can still cause a bundled face to be used. Project settings
intentionally take precedence over preset defaults.

## Site-owned fonts

Put local `.woff2` files under the consuming site's `static/webfonts/` folder.
Declare the faces and override only the required roles in
`assets/scss/_styles_project.scss`, which Hugo loads after the theme styles:

```scss
@font-face {
  font-family: 'My Sans';
  font-display: swap;
  font-style: normal;
  font-weight: 400 800;
  src: url('../webfonts/my-sans-variable.woff2') format('woff2');
}

:root {
  --td-ui-font-family: 'My Sans', 'Noto Sans SC', sans-serif;
  --td-body-font-family: var(--td-ui-font-family);
  --td-heading-font-family: var(--td-ui-font-family);
  --td-display-font-family: var(--td-heading-font-family);
}
```

For a custom monospace face, include an explicit CJK fallback when the site can
contain Chinese text:

```scss
:root {
  --td-code-font-family:
    'My Mono', 'Sarasa Mono SC', 'Noto Sans Mono CJK SC', monospace;
}
```

Remote URLs and arbitrary CSS are intentionally not accepted through YAML.
Font files and CSS remain local, reviewable inputs to the normal Hugo build.

Roles inherit normally, so a future content-specific treatment does not need a
new global preset or copied component selectors. For example, a consuming site
can give only blog content an editorial face:

```scss
body.td-blog {
  --td-body-font-family: 'My Serif', 'Noto Serif SC', serif;
  --td-heading-font-family: var(--td-body-font-family);
}
```

## Scope

This first token slice covers typography only. Color, surface, radius, density,
and appearance presets should be introduced independently after their existing
Bootstrap and shell-token contracts have matching regression coverage.
