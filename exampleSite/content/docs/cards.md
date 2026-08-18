---
title: Cards
linkTitle: Cards
description: A link list plus `{.cards}` lays out a grid of navigation cards; switch to the shortcode when you need icons, badges or images.
weight: 80
search_keywords: [Cards, card, link card, navigation card, section index, icon, badge]
---

Cards are a set of parallel links: each card is a linked title plus a sentence,
and the grid adapts to the container width. They suit section landing pages,
"what to read next", and a handful of parallel entry points. They do not suit
running prose (use paragraphs) or a wall of images (use a
[gallery](/docs/gallery/)).

## Shortest form {#minimal}

A link list with `{.cards}` is a card grid. The link is the title; whatever
follows ` — ` is the description.

```markdown {title="Source"}
- [Get started](https://oink.pgsty.com/docs/start/) — Clone this documentation site, delete what you do not need, replace the site details with your own.
- [Authoring](https://oink.pgsty.com/docs/write/) — How pages are organized and which front matter keys exist.
- [Customization](https://oink.pgsty.com/docs/customize/) — Navigation, search, branding, languages.
{.cards}
```

- [Get started](https://oink.pgsty.com/docs/start/) — Clone this documentation site, delete what you do not need, replace the site details with your own.
- [Authoring](https://oink.pgsty.com/docs/write/) — How pages are organized and which front matter keys exist.
- [Customization](https://oink.pgsty.com/docs/customize/) — Navigation, search, branding, languages.
{.cards}

The whole card is the click target, not just the title text. There is no
`columns` parameter: the column count follows the container width and collapses
to one on a narrow screen.

## Title-only cards {#title-only}

The description is optional. One link per line, `{.cards}` at the end.

```markdown {title="Source"}
- [Callouts](/docs/callout/)
- [Tabs](/docs/tabs/)
- [Steps](/docs/steps/)
- [Fields](/docs/fields/)
{.cards}
```

- [Callouts](/docs/callout/)
- [Tabs](/docs/tabs/)
- [Steps](/docs/steps/)
- [Fields](/docs/fields/)
{.cards}

## Loose lists and longer descriptions {#loose}

When a sentence is not enough, switch to a loose list: the link is its own
paragraph, the description another, with a blank line between items. The title
takes its own line and the description sits under it. `{.cards}` still has to
touch the last paragraph — **no blank line** in between.

```markdown {title="Source"}
- [Front matter](https://oink.pgsty.com/docs/write/frontmatter/)

  Every page parameter is defined here exactly once: type, default, accepted
  values, and the page that explains it.

- [Configuration](https://oink.pgsty.com/docs/customize/config/)

  Site parameters grouped by feature, each row linking back to the guide that
  explains it.
{.cards}
```

- [Front matter](https://oink.pgsty.com/docs/write/frontmatter/)

  Every page parameter is defined here exactly once: type, default, accepted
  values, and the page that explains it.

- [Configuration](https://oink.pgsty.com/docs/customize/config/)

  Site parameters grouped by feature, each row linking back to the guide that
  explains it.
{.cards}

## Icons and badges {#icon-badge}

A link list has no icons, badges, images or multi-paragraph descriptions; those
need the `cards` / `card` shortcode. `icon` is exactly one Font Awesome class
pair and `badge` is plain text.

```markdown {title="Source"}
{{</* cards */>}}
{{</* card title="Get started" link="https://oink.pgsty.com/docs/start/" icon="fa-solid fa-rocket" badge="start here" */>}}
Fork the documentation site itself and get a local preview in ten minutes.
{{</* /card */>}}
{{</* card title="Release and download pages" link="https://oink.pgsty.com/docs/write/releases/" icon="fa-solid fa-box-open" badge="v0.5" */>}}
A `release` fact record, an asset table and checksums — all generated locally.
{{</* /card */>}}
{{</* card title="Keyboard navigation" link="https://oink.pgsty.com/docs/customize/keyboard/" icon="fa-solid fa-keyboard" */>}}
Site-wide shortcuts and focus order.
{{</* /card */>}}
{{</* /cards */>}}
```

{{< cards >}}
{{< card title="Get started" link="https://oink.pgsty.com/docs/start/" icon="fa-solid fa-rocket" badge="start here" >}}
Fork the documentation site itself and get a local preview in ten minutes.
{{< /card >}}
{{< card title="Release and download pages" link="https://oink.pgsty.com/docs/write/releases/" icon="fa-solid fa-box-open" badge="v0.5" >}}
A `release` fact record, an asset table and checksums — all generated locally.
{{< /card >}}
{{< card title="Keyboard navigation" link="https://oink.pgsty.com/docs/customize/keyboard/" icon="fa-solid fa-keyboard" >}}
Site-wide shortcuts and focus order.
{{< /card >}}
{{< /cards >}}

An icon that is not a `fa-solid fa-xxx` style class pair fails the build rather
than being dropped silently.

## Markdown bodies {#markdown-body}

A `card` body renders as page-level Markdown: inline code, emphasis, links,
lists. Parameters such as `title` and `badge` are plain text and are not parsed
as Markdown.

```markdown {title="Source"}
{{</* cards */>}}
{{</* card title="Hugo Module" icon="fa-brands fa-golang" */>}}
`hugo mod get github.com/pgsty/oink`. The recommended way; upgrading is one
version line.
{{</* /card */>}}
{{</* card title="Git submodule" icon="fa-solid fa-code-branch" */>}}
No Go installation needed:

- `git submodule add`
- the theme lands in `themes/oink`
{{</* /card */>}}
{{</* /cards */>}}
```

{{< cards >}}
{{< card title="Hugo Module" icon="fa-brands fa-golang" >}}
`hugo mod get github.com/pgsty/oink`. The recommended way; upgrading is one
version line.
{{< /card >}}
{{< card title="Git submodule" icon="fa-solid fa-code-branch" >}}
No Go installation needed:

- `git submodule add`
- the theme lands in `themes/oink`
{{< /card >}}
{{< /cards >}}

A card without `link` renders as a bold title and produces no link.

## Cards with images {#image}

`image` resolves in the same order as `![alt](src)`: page resource → global
resource in `assets/` → static path `/images/…` → remote URL. Local resources
carry their intrinsic size so nothing shifts while loading.

`image` must be paired with a source of alternative text: `image_alt="…"` for an
informative image, or `decorative=true` for a purely decorative one. Writing
both, or neither, fails the build.

```markdown {title="Source"}
{{</* cards */>}}
{{</* card title="The OINK shell" link="https://oink.pgsty.com/docs/about/features/" image="/images/oink.webp" image_alt="An OINK documentation page: sidebar, article and table of contents" */>}}
Sidebar, article, table of contents — each can be turned off on its own.
{{</* /card */>}}
{{</* card title="Release notes" link="https://oink.pgsty.com/docs/write/releases/" image="/images/releasenote.webp" decorative=true */>}}
A decorative cover: `decorative=true` emits an empty alt and screen readers skip it.
{{</* /card */>}}
{{</* /cards */>}}
```

{{< cards >}}
{{< card title="The OINK shell" link="https://oink.pgsty.com/docs/about/features/" image="/images/oink.webp" image_alt="An OINK documentation page: sidebar, article and table of contents" >}}
Sidebar, article, table of contents — each can be turned off on its own.
{{< /card >}}
{{< card title="Release notes" link="https://oink.pgsty.com/docs/write/releases/" image="/images/releasenote.webp" decorative=true >}}
A decorative cover: `decorative=true` emits an empty alt and screen readers skip it.
{{< /card >}}
{{< /cards >}}

Card images do not take part in [image zoom](/docs/image/#zoom) — the
whole card is already a link.

## Automatic cards on section pages {#section-index}

A section landing page (`_index.md`) needs no hand-written card list: the theme
reads each child page's `title`, `description` and `icon` and generates the
cards. This site turns it on globally in `hugo.yaml`:

```yaml {title="hugo.yaml"}
params:
  ui:
    section_index: cards # list | cards
```

One section can override it in its own front matter, or push the choice down a
whole subtree with `cascade`:

```yaml {title="content/docs/customize/_index.md"}
params:
  ui:
    section_index: list
```

Automatic and hand-written cards share the `td-content-card` styling; only the
data source differs. Do not hand-write a list of child pages on a section page —
it drifts out of step with the sidebar. Hand-write cards only when the set is
not this section's children (external links mixed in, cross-section
recommendations). The keys are defined in
[Configuration](https://oink.pgsty.com/docs/customize/config/).

## Which form to use {#forms}

| What you want | Which form |
| --- | --- |
| A grid of links with one-sentence descriptions | `{.cards}` link list |
| Icons, badges, images | `cards` / `card` shortcode |
| Lists, code or several paragraphs in the description | `cards` / `card` shortcode |
| A card with no link | `cards` / `card` shortcode |
| This section's child pages | nothing at all — `section_index: cards` |

A link list is still a link list on GitHub; a shortcode is not. Use the native
form whenever it is enough.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | Native form: `<ul class="cards">`. Shortcode form: `<div class="td-content-cards">` with one `<article class="td-content-card">` each. Both are pure CSS grids and load no script |
| Print | The native form stacks; the shortcode form collapses to two columns; in both, a card avoids breaking across pages |
| Markdown | The native form keeps the link list; the shortcode form emits `- [Title](link) (badge) — description` |
| RSS | The same markup as HTML — a readable list of links without site CSS |

## Parameter reference {#reference}

The native form:

| Element | Type | Default | Description |
| --- | --- | --- | --- |
| `{.cards}` | list attribute line | — | On the line **after** an unordered list; unordered lists only |
| First link in an item | Markdown link | — | The card title and the whole card's click target |
| Everything else | Markdown | — | The description: after ` — ` in a tight list, its own paragraph in a loose one |
{.fields meta="type default"}

`card` parameters (`cards` itself takes none):

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `title` | plain text | — | Required, non-empty. The card title |
| `link` | URL | — | Site path, relative path, `http(s):`, `mailto:`; external links get `rel="noopener"` |
| `icon` | Font Awesome class pair | — | For example `fa-solid fa-rocket`; a malformed value fails the build |
| `badge` | plain text | — | A small label beside the title |
| `image` | image source | — | Page resource / global resource / static path / remote URL |
| `image_alt` | plain text | — | With `image`, exactly one of this and `decorative` |
| `decorative` | boolean | `false` | `true` marks a decorative image and emits an empty alt |
| Body | Markdown | — | The card description |
{.fields meta="type default"}

There is no `cols`, `columns`, `accent`, `desc` or `color` parameter, and any
unknown parameter fails the build.

## Limits {#limits}

- `{.cards}` recognizes unordered lists only: on an ordered list it does
  nothing.
- `{.cards}` must touch the list: a blank line in between, or indenting it into
  a list item, drops the marker silently — the build succeeds and the list stays
  a list. Check that line first when the output is not a card grid.
- A `card` lives only inside `cards`: alone, or inside another shortcode, it
  fails the build and the error names the location.
- The column count is not configurable: the grid adapts to the container. Only
  automatic section cards take a count, through
  `params.ui.section_index_columns`.
- Cards are not for long text: when a description runs past two lines, use a
  paragraph or a [callout](/docs/callout/).

## Related {#related}

- [Fields](/docs/fields/) — also has a native form and a shortcode form
- [Galleries](/docs/gallery/) — a grid of images
- [Badges](/docs/badge/) — inline status labels
- [Organizing content](https://oink.pgsty.com/docs/write/organize/) — sections, weights and landing pages
- [Configuration](https://oink.pgsty.com/docs/customize/config/) — `section_index` and friends
