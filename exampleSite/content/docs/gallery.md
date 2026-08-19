---
title: Galleries
linkTitle: Galleries
description: A `gallery` fence arranges related screenshots in a responsive grid, each with an optional description or link, reusing the page's image zoom dialog.
icon: fa-solid fa-images
weight: 170
search_keywords: [Gallery, screenshot grid, fence, image zoom, link, class]
image_zoom: true
---

A gallery arranges related images in a responsive grid, one image per line
inside the fence. It suits several views of one thing: a few screenshots, a few
states, a few colour schemes. A single image is an
[image](/docs/image/), and images with no order or comparison between
them do not belong in one gallery.

## Shortest form {#minimal}

One image per line, written as Markdown's `![alt](src)`.

````markdown {title="Source"}
```gallery
![OINK's default documentation shell](/images/oink.webp)
![The classic Docsy layout upstream](/images/docsy.webp)
```
````

```gallery
![OINK's default documentation shell](/images/oink.webp)
![The classic Docsy layout upstream](/images/docsy.webp)
```

Alternative text is mandatory: it is the item's title, the only text a screen
reader gets, and what decides whether the image can zoom. There is no column
parameter — the grid adapts to the container and drops columns on a narrow
screen.

## Descriptions {#description}

Start a description with ` # ` after the image and it appears underneath.
Descriptions are plain text, so Markdown inside them shows literally; for a
literal hash write `\#`.

````markdown {title="Source"}
```gallery
![The three-column layout of an OINK page](/images/oink.webp) # The default shell: sidebar, article, table of contents
![The classic Docsy documentation layout](/images/docsy.webp) # Docsy upstream — the content model is the same lineage
![A release notes page](/images/releasenote.webp) # Release pages are generated from facts in data/download, offline
```
````

```gallery
![The three-column layout of an OINK page](/images/oink.webp) # The default shell: sidebar, article, table of contents
![The classic Docsy documentation layout](/images/docsy.webp) # Docsy upstream — the content model is the same lineage
![A release notes page](/images/releasenote.webp) # Release pages are generated from facts in data/download, offline
```

Descriptions need not be the same length: the grid aligns to the tallest item
and a wrapped description does not disturb its neighbours. The image is parsed
first, so a `#` inside the alt text or the path needs no escaping.

## A link per item {#link}

`{link=…}` at the end of a line turns that item into a link. Site paths,
relative paths and `http(s):` all work.

````markdown {title="Source"}
```gallery
![OINK's default documentation shell](/images/oink.webp) # Opens the Images component page {link=/docs/image/}
![A release notes page](/images/releasenote.webp) # Opens "Releases and downloads" {link=https://oink.pgsty.com/docs/write/releases/}
```
````

```gallery
![OINK's default documentation shell](/images/oink.webp) # Opens the Images component page {link=/docs/image/}
![A release notes page](/images/releasenote.webp) # Opens "Releases and downloads" {link=https://oink.pgsty.com/docs/write/releases/}
```

A linked item does not zoom, because clicking already means something else. Both
kinds can share one gallery: linked items open a page, the rest open the full
image.

## Where images come from {#sources}

Sources resolve exactly as for a plain image: page resource (a file next to the
page in its bundle) → global resource in `assets/` → static path `/images/…` →
remote URL. This example site keeps its shared demo images together in
`static/images/` because they do not need build-time processing.

````markdown {title="Source"}
```gallery
![OINK documentation overview](/images/oink.webp) # From static/images/…, published as is
![OINK release notes](/images/releasenote.webp) # Shared from the same simple directory
```
````

```gallery
![OINK documentation overview](/images/oink.webp) # From static/images/…, published as is
![OINK release notes](/images/releasenote.webp) # Shared from the same simple directory
```

A missing page or global resource fails the build; static paths and remote URLs
are not checked.

## Decorative images and zoom {#zoom}

Empty alternative text marks a decorative image: no title, skipped by screen
readers, and never a zoom candidate.

Image zoom is a site-level switch and is off by default. This page turns it on
in its front matter, so every image above that has alt text and no link opens
full size (<kbd>Esc</kbd> closes it and focus returns where it was).

```yaml {title="this page's front matter"}
params:
  ui:
    image_zoom:
      enable: true
```

````markdown {title="Source: one decorative image, one ordinary one"}
```gallery
![](/images/docsy.webp) # Decorative, never zooms
![The Pigsty release notes page](/images/releasenote.webp) # Has alt text, so it opens
```
````

```gallery
![](/images/docsy.webp) # Decorative, never zooms
![The Pigsty release notes page](/images/releasenote.webp) # Has alt text, so it opens
```

A gallery has no zoom runtime of its own; it reuses the one dialog the page
shares. With no zoomable image on the page, that runtime is never loaded. The
details are in [Images · Zoom](/docs/image/#zoom).

## Classes and tabs {#class-and-tabs}

`class` can go on the whole fence (after the language) or on one item (at the
end of its line). The theme does not interpret it and passes it through for site
CSS. A fence carrying `tab=` (with `group=` / `value=`) becomes one panel of a
[tab set](/docs/tabs/).

````markdown {title="Source"}
```gallery {tab="OINK" group="shell" value="oink"}
![OINK's default documentation shell](/images/oink.webp) # Sidebar, article, table of contents
```
```gallery {tab="Docsy" value="docsy"}
![The classic Docsy layout upstream](/images/docsy.webp) # The same content-model lineage
```
````

```gallery {tab="OINK" group="shell" value="oink"}
![OINK's default documentation shell](/images/oink.webp) # Sidebar, article, table of contents
```
```gallery {tab="Docsy" value="docsy"}
![The classic Docsy layout upstream](/images/docsy.webp) # The same content-model lineage
```

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | `<ul class="td-gallery">` with one `<li>` per item; eligible images carry `data-td-image-zoom`; everything is lazy-loaded |
| Print | The same images stacked, without zoom markers |
| Markdown | The `gallery` fence, emitted as written |
| RSS | The same static stack as print |

Galleries load no JavaScript of their own.

## Parameter reference {#reference}

The line syntax `![alt](src) [# description] [{key=value …}]`:

| Element | Required | Description |
| --- | --- | --- |
| `![alt](src)` | yes | Must start the line. `alt` is the item's title; empty means decorative |
| `src` | yes | Page resource / global resource / static path / remote URL |
| `# description` | no | Plain text under the image; `\#` is a literal hash; must not be empty |
| `{link=…}` | no | Makes the item a link, and therefore not zoomable |
| `{class=…}` | no | Adds a site CSS class to that item |
{.fields}

Fence attributes:

| Attribute | Type | Default | Description |
| --- | --- | --- | --- |
| `tab` | plain text | — | Makes this gallery one panel of a tab set |
| `group` / `value` | string | — | Tab group and sync value; must appear with `tab` |
| `class` | class list | — | Passed through for site CSS |
{.fields meta="type default"}

There is no `columns`, `caption` or `title` attribute. A line that does not
start with an image, trailing text outside a `#`, an empty description, an
unknown attribute and a malformed `{…}` all fail the build with the line number
inside the fence.

## Limits {#limits}

- The fence is the only form: there is no `{.gallery}` list marker and no
  shortcode. The cost is that the source does not render as images on GitHub;
  the benefit is that four-state output and zoom eligibility are guaranteed by
  the theme.
- Columns cannot be set and images are not cropped to one aspect ratio: the grid
  follows the viewport and images keep their own proportions.
- No slideshow, no carousel, no previous / next: the zoom dialog shows one image
  at a time.
- Remote images are not downloaded: there is no network request at build time,
  so a remote image's size is unknown until the browser loads it and the layout
  may shift.
- Descriptions are not Markdown: put rich text in a paragraph under the gallery.

## Related {#related}

- [Images](/docs/image/) — single images, captions, numbering, the zoom switch
- [Cards](/docs/cards/) — a grid of links with images
- [Tabs](/docs/tabs/) — one gallery per platform or theme
- [File trees](/docs/filetree/) — the same line syntax family
