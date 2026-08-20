---
title: Immersive reading on the blog shell
linkTitle: Immersive reading
date: 2026-08-19
description: >-
  Four front-matter keys turn a blog page into a reading-first layout: a hero
  drawn from the featured image, no chrome but the outline rail, and every
  blog component in its usual place below the fold.
authors: [vonng]
featured_image: hero
toc_style: flow
toc_taxonomies: false
sidebar_enabled: false
tags: [Oink]
---

This page is rendered by the ordinary blog shell — there is no special type
behind it. Its front matter sets four keys, and a section can set the same
four once, in a cascade:

```yaml
featured_image: hero      # the image becomes a full-bleed opening
toc_style: flow           # a wider outline that moves down with it
toc_taxonomies: false     # the rail carries the outline alone
sidebar_enabled: false
```

## The hero

A page that carries a featured image opens with it. `hero` makes the image a
full-bleed backdrop across the top of the viewport, masked to nothing before
the body text starts, with the title block moved down to give it room — and
because the shell itself paints it, a section index gets the same opening
above its list. The image is the one the page's card and social preview use,
resolved once for all three. A page that prefers the framed figure keeps
`featured_image: banner`; a page with no image simply opens normally.

## The rail

`toc_style: flow` swaps the viewport-pinned outline for a wider one that sits
in the content flow: it starts where the article starts — below the hero —
and pins only once you scroll. It is deliberately independent of the hero, so
a section keeps one rail whether or not each page carries an image.
`toc_taxonomies: false` removes the taxonomy clouds; a rail with nothing left
to show renders nothing at all.

## What stays on

Everything below the fold is the blog article you already know: the info
line, the tag badges, the authors and their profiles, the series strip, the
description lead, and the page end with its share bar, annotation, sequential
pager, and discussion. The blog shell renders no breadcrumb by default --
`breadcrumb: true` brings one back -- and the navbar renders over a hero as a
transparent overlay that scrolls away with the image. Every key above is an
ordinary `ui.` parameter, so each can be flipped back per page at any time.
