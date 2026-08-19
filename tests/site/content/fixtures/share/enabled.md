---
title: Shared page
description: Seven inherited targets - one intent link per URL shape, plus the local copy control.
weight: 10
---

The bar above the feedback prompt is the section's inherited list, and each
entry is a different shape of intent URL: `x` carries the URL and the title as
separate parameters, `facebook` takes the URL alone and reads the title off the
page, `whatsapp` gets one merged `Title URL` string, `pinterest` adds the pin's
`media` image when the page has one, `claude` sends a prompt naming the
permalink, `email` is a `mailto:` whose subject precedes its body, and `copy`
is not a link at all but the local `copy_link` action.

`bluesky` and `mastodon` share WhatsApp's merged shape; `linkedin` shares
Facebook's; `reddit`, `hackernews`, `telegram`, `line`, and `weibo` share X's;
`chatgpt` shares Claude's. Discord has no share-intent URL of any shape, so the
bar offers none and `copy` stands in for it.
