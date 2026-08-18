---
title: Images
linkTitle: Images
description: Plain Markdown image syntax plus one attribute line gives you captions, sizing, zoom, links, numbering and Hugo image processing.
weight: 20
search_keywords: [Image, Figure, caption, zoom, image processing, imgproc, width, height, numbering]
image_zoom: true
---

There is one way to write an image: Markdown's `![alt](src "title")`. An image
that stands alone as a paragraph can be followed by a `{…}` attribute line,
which turns it into a captioned figure, a zoom candidate, a numbered figure, or
a derivative processed by Hugo. The theme has no image shortcode.

## Shortest form {#minimal}

```markdown {title="Source"}
![The OINK documentation shell: sidebar, article and table of contents](oink-shell.webp)
```

![The OINK documentation shell: sidebar, article and table of contents](oink-shell.webp)

This image lives in the same directory as the page (a page bundle). The theme
reads its intrinsic dimensions and writes `width`/`height`, so nothing shifts
while the page loads; every image is lazy-loaded. Alternative text serves
screen readers and search engines and should always be written. An empty alt
marks a decorative image, and zoom skips it.

## Where images come from {#sources}

Sources resolve in this order and are all written the same way:

| Placement | In the source | Good for |
| --- | --- | --- |
| Next to the page (bundle: `index.md` + image) | `![…](oink-shell.webp)` | Screenshots only this page uses; they travel with the page and are shared by translations |
| Global resource `assets/images/…` | `![…](images/logo/oink.webp)` | Images several pages share, especially ones that need processing |
| Static directory `static/images/…` | `![…](/images/oink.webp)` | Large images and downloads that need no processing; supply `width`/`height` since the theme cannot measure them |
| Remote URL | `![…](https://example.com/a.png)` | Rare: nothing is downloaded at build time and nothing can be processed |

A relative path is looked up as a page resource first, then as a global
resource; if neither matches it is emitted as a static path unchanged. The
theme does not verify that static paths and remote URLs exist. Only an image
that asks for processing (`command=`) fails the build when its resource is
missing.

## Inline versus block {#inline-vs-block}

An image inside a line of text is inline: it renders as a bare `<img>` and
takes no attributes. An image that stands alone as a paragraph is a block image
and can carry an attribute line.

```markdown {title="Source"}
This little one ![shell thumbnail](oink-mini.webp) sits inside a sentence — an inline image.

![shell thumbnail](oink-mini.webp)
{width="100" height="64"}
```

This little one ![shell thumbnail](oink-mini.webp) sits inside a sentence — an inline image.

![shell thumbnail](oink-mini.webp)
{width="100" height="64"}

An inline image renders at its own size (50×32 here). An SVG without intrinsic
dimensions stretches to the container width when inlined, so use SVGs as block
images and give them `width`/`height`.

> [!NOTE]
> Block images depend on the site setting
> `markup.goldmark.parser.wrapStandAloneImageWithinParagraph: false` (this site
> has it; see [Configuration](https://oink.pgsty.com/docs/customize/config/)).
> Without it Goldmark wraps standalone images in `<p>` and the attribute line
> becomes body text.

## Captions {#caption}

Add `caption="…"` to the attribute line and the image renders as `<figure>` +
`<figcaption>`. The caption is plain text and is not parsed as Markdown.

```markdown {title="Source"}
![Release card: version, publication date and asset buttons](release-note.webp)
{caption="The release card is generated from data/download and the page's release record"}
```

![Release card: version, publication date and asset buttons](release-note.webp)
{caption="The release card is generated from data/download and the page's release record"}

Markdown's `"title"` keeps its own meaning (a hover tooltip); it never becomes
the caption.

## Size {#size}

`width`/`height` are positive integers that override the resource's own
dimensions: give static or remote images a placeholder box so the page does not
jump, or display a large image smaller (the browser scales it — the file does
not change).

```markdown {title="Source"}
![OINK documentation site overview](/images/oink.webp)
{width="300" height="150" caption="A 600×300 screenshot from static/images/ shown at half size"}
```

![OINK documentation site overview](/images/oink.webp)
{width="300" height="150" caption="A 600×300 screenshot from static/images/ shown at half size"}

## Processed images {#processing}

Page resources and global resources can be processed by Hugo at build time.
`command` and `options` must both be given: the command is one of `Fit`,
`Resize`, `Fill`, `Crop`, and the options are Hugo's image-processing string.
The rendered `src` is the derivative; with zoom enabled the dialog opens the
original.

```markdown {title="Source"}
![shell thumbnail](oink-shell.webp)
{command="Fit" options="300x150" caption="Fit 300x150: scaled to fit inside a 300×150 box"}

![the left half of the shell](oink-shell.webp)
{command="Fill" options="300x150 Left" caption="Fill 300x150 Left: fills the box, cropped from the left"}
```

![shell thumbnail](oink-shell.webp)
{command="Fit" options="300x150" caption="Fit 300x150: scaled to fit inside a 300×150 box"}

![the left half of the shell](oink-shell.webp)
{command="Fill" options="300x150 Left" caption="Fill 300x150 Left: fills the box, cropped from the left"}

Static paths, remote URLs and SVGs cannot be processed; writing `command` for
one fails the build. For the option syntax — anchors, quality, format
conversion such as `300x150 webp q80` — see
[Hugo image processing](https://gohugo.io/content-management/image-processing/).

## Linked images {#link}

Two spellings for two situations:

- No caption, the image itself is the link: wrap it in a Markdown link,
  `[![alt](src)](href)`.
- A captioned figure that is clickable as a whole: add `link="…"` to the
  attribute line (it requires `caption` or `num`).

```markdown {title="Source"}
[![Go to the highlights page](oink-shell.webp)](https://oink.pgsty.com/docs/about/features/)

![Release card](release-note.webp)
{caption="Click the image for the release and download page" link="https://oink.pgsty.com/docs/write/releases/"}
```

[![Go to the highlights page](oink-shell.webp)](https://oink.pgsty.com/docs/about/features/)

![Release card](release-note.webp)
{caption="Click the image for the release and download page" link="https://oink.pgsty.com/docs/write/releases/"}

A linked image does not take part in zoom. Writing `link=` without a caption
fails the build, and the error suggests `[![…](…)](…)` instead.

## Numbered figures {#numbered}

Numbered figures are for books and long manuals: add `num` to the attribute
line, optionally `#id`. The number is a string the author writes (`2-1`,
`3.4`) — the theme never counts for you. The caption gains a localized
"Figure 2-1" prefix and `#id` defaults to `fig-<num>`. Reference it from the
prose with an ordinary link, `[Figure 2-1](#fig-2-1)`, or with the `xref`
shortcode; for a book-wide list of figures see
[publishing books](https://oink.pgsty.com/docs/write/book/).

```markdown {title="Source"}
![Release card](release-note.webp)
{#fig-release num="2-1" caption="Release card: version, date and assets"}

See [Figure 2-1](#fig-release).
```

![Release card](release-note.webp)
{#fig-release num="2-1" caption="Release card: version, date and assets"}

See [Figure 2-1](#fig-release).

A numbered figure can also be a processed image (`num` + `command`) and can
carry `link`.

## Zoom {#zoom}

Image zoom is off by default. Once the site enables it, block images, figures
and gallery images that have alt text become clickable buttons that open the
full image in a native `<dialog>` (Esc closes it, focus returns where it was).
This page turns it on in its front matter, so every image above is clickable.

```yaml {title="hugo.yaml"}
params:
  ui:
    image_zoom:
      enable: true
```

```yaml {title="One page's front matter: off for this page only"}
params:
  ui:
    image_zoom:
      enable: false
```

Images that never zoom: inline images, decorative images with an empty alt,
linked images, and images marked `data-no-zoom`. The runtime loads only when
the page really has a candidate; print, Markdown and RSS have no dialog.

```markdown {title="Source: a decorative image does not zoom"}
![](oink-shell.webp)
{width="150" height="75"}
```

![](oink-shell.webp)
{width="150" height="75"}

## Light and dark images {#dark-mode}

The theme has no parameter for swapping images by colour scheme. When you need
two, give each one a `class` and show one of them from site CSS keyed on
`[data-bs-theme="dark"]`:

```markdown {title="Source"}
![Sidebar (light)](oink-shell.webp)
{class="only-light"}

![Sidebar (dark)](oink-shell.webp)
{class="only-dark"}
```

```scss {title="assets/scss/_styles_project.scss"}
[data-bs-theme="dark"] .only-light,
:not([data-bs-theme="dark"]) .only-dark { display: none; }
```

`class` is passed through verbatim by the theme for site CSS to use.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | Inline `<img>`; block `<img class="td-image">`; with a caption or number, `<figure class="td-figure">` + `<figcaption>`; zoom candidates carry `data-td-image-zoom` |
| Print | Same as HTML, zoom affordances removed |
| Markdown | `![alt](src)` and the attribute line, emitted as written |
| RSS | Image `src` becomes absolute; no zoom |

## Parameter reference {#reference}

The attribute line `{…}`, immediately after a block image:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `caption` | plain text | — | Its presence makes a figure; not parsed as Markdown |
| `#id` | identifier | `fig-<num>` when `num` is set | `[A-Za-z][A-Za-z0-9_.:-]*`; the anchor and the Book target ID |
| `num` | string | — | `[0-9A-Za-z.-]+`; registers a Book figure target and prefixes the caption with "Figure N." |
| `width` / `height` | positive integer | the resource's own size | Overrides the size; static and remote images need it to avoid layout shift |
| `command` | enum | — | `Fit` `Resize` `Fill` `Crop`; must appear with `options`; page and global resources only |
| `options` | string | — | Hugo image-processing options such as `600x300`, `300x150 Left`, `800x webp q80` |
| `link` | URL | — | Wraps the figure in a link; requires `caption` or `num`; a linked image does not zoom |
| `class` | class list | — | Passed through for site CSS |
| `data-*` / `aria-*` | string | — | Passed through |
{.fields meta="type default"}

`style`, `on*`, `alt`, `title`, `src` and any other key on the attribute line
fail the build (alt, title and src belong to the Markdown image itself).

## Limits {#limits}

- Captions carry no Markdown: every public string parameter is plain text.
  Put rich explanation in a paragraph under the image.
- `title` is not a caption: the `c` in `![a](b "c")` is a hover tooltip.
- Processing applies to resources only: move an image out of `static/` into a
  page bundle or `assets/` when it needs to be processed.
- Remote images are never downloaded at build time.
- Zoom has no drag, pan, or previous / next; for a set of related images use a
  [gallery](/docs/gallery/).

## Related {#related}

- [Galleries](/docs/gallery/) — a set of images sharing one zoom dialog
- [Publishing books](https://oink.pgsty.com/docs/write/book/) — lists of figures and `xref`
- [Branding](https://oink.pgsty.com/docs/customize/brand/) — where the site logo and favicon live
- [Cards](/docs/cards/) — images on cards
