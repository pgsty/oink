---
title: Share bar
description: A section fixture for the page-end share bar and its opt-out.
weight: 60
# How a site is expected to reach for the bar: one cascade over the section
# that wants it, rather than a key repeated on every page. One entry per URL
# shape the catalog knows, so a change to any of them shows up here.
cascade:
  share: [x, facebook, whatsapp, pinterest, claude, email, copy]
---

The section itself is not a page anyone shares, so it renders no bar; its
children inherit the list above.
