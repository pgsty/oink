---
title: A wash featured image
description: Pins the wash mode against the static image the section cascade carries.
date: 2026-08-08
weight: 40
outputs: [HTML, print]
featured_image: wash
# A page override beats the section cascade; with no dark value in sight,
# the emitted dark palette derives from this teal.
theme_color: '#0f766e'
build:
  list: never
---

The wash is resolved from the section cascade's `images` value, a static path
Hugo cannot process, so it reaches the header at its original URL.
