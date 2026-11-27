---
title: 社交帖子
description: 离线社交帖子卡片、各平台、引用帖与降级形态的回归样例。
outputs: [HTML, print, markdown]
weight: 62
---

## 完整卡片 {#full}

{{< social author="Ada Lovelace" handle="@ada" avatar="media/content-primitives-global.png"
           date="2026-02-15" url="https://x.com/ada/status/1890000000000000000" >}}
帖子正文是普通的 **Markdown**，可以带[链接](https://example.org/)
和 `行内代码`。

![帖子附带的图片](media/content-primitives-global.png)
{{< /social >}}

## 其他平台 {#platforms}

{{< social author="Grace Hopper" handle="@grace@mastodon.social" platform="mastodon" date="2026-03-01 08:30" >}}
没有头像时，卡片显示首字符。
{{< /social >}}

{{< social handle="@oink.bsky.social" platform="bluesky" url="https://bsky.app/profile/oink.bsky.social/post/3kxyz" >}}
只有账号名，没有作者名。
{{< /social >}}

## 引用帖 {#quote}

{{< social author="OINK" handle="@pgsty" date="2026-11-23" url="https://x.com/pgsty/status/1" >}}
OINK v1.6.0 已发布。

{{< social author="Hugo" handle="@GoHugoIO" date="2026-11-13" url="https://x.com/GoHugoIO/status/2" >}}
Hugo v0.170.0 移除了 extended 版本。
{{< /social >}}
{{< /social >}}
