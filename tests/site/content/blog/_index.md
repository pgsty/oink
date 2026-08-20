---
title: Blog
type: blog
description: Real OINK release notes and engineering posts, wired to every blog feature.
weight: 20
icon: fa-solid fa-blog
# The index of this section is a card grid; the two child sections keep the row
# form, so one site shows both. The site config turns the reader toggle on
# (ui.blog_index_toggle), so every blog index also carries the toolbar control
# that cycles list, cards, and table.
blog_index: cards
cascade:
  type: blog
  images: [/images/oink.webp]
  # The article info line under each title carries the date always; this
  # switch adds the word count and the minutes beside it.
  reading_time: true
  # Static intent links plus one local copy button. Nothing is requested until
  # a reader activates one. Thirteen of the sixteen available targets; the other
  # three (reddit, line, pinterest) are named in the theme's hugo.yaml.
  share: [x, bluesky, mastodon, facebook, linkedin, hackernews, telegram,
          whatsapp, weibo, chatgpt, claude, email, copy]
---

Two sections below: the release notes are a numbered series, and the OINK posts
carry bylines resolved from the `authors` taxonomy.

![The OINK mark, shown here so the blog index carries a zoomable content image](/images/oink.webp)
