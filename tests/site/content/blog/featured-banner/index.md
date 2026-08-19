---
title: A banner featured image
description: Pins the banner mode against a bundled, processable page resource.
date: 2026-08-09
weight: 30
outputs: [HTML, print]
featured_image: banner
resources:
  - src: featured.png
    params:
      byline: OINK fixture byline
build:
  list: never
---

The banner is resolved from the bundled `featured.png`, which outranks the
`images` value this post inherits from the section cascade. The article stays
out of the blog list so the surfaces that were already pinned keep their bytes.
