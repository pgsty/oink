---
title: Social posts
description: Regression fixtures for the offline social post card, its platforms, a quoted post, and degraded forms.
outputs: [HTML, print, markdown]
weight: 62
---

## Full card {#full}

{{< social author="Ada Lovelace" handle="@ada" avatar="media/content-primitives-global.png"
           date="2026-02-15" url="https://x.com/ada/status/1890000000000000000" >}}
The post text, in ordinary **Markdown**, with a [link](https://example.org/)
and `inline code`.

![The image attached to the post](media/content-primitives-global.png)
{{< /social >}}

## Other platforms {#platforms}

{{< social author="Grace Hopper" handle="@grace@mastodon.social" platform="mastodon" date="2026-03-01 08:30" >}}
No avatar: the card draws the first letter.
{{< /social >}}

{{< social handle="@oink.bsky.social" platform="bluesky" url="https://bsky.app/profile/oink.bsky.social/post/3kxyz" >}}
Only a handle, no author name.
{{< /social >}}

## Quoted post {#quote}

{{< social author="OINK" handle="@pgsty" date="2026-11-23" url="https://x.com/pgsty/status/1" >}}
OINK v1.6.0 is out.

{{< social author="Hugo" handle="@GoHugoIO" date="2026-11-13" url="https://x.com/GoHugoIO/status/2" >}}
Hugo v0.170.0 removes the extended edition.
{{< /social >}}
{{< /social >}}
