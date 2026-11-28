---
title: 帖子
description: 离线帖子卡片、各平台、引用帖与降级形态的回归样例。
outputs: [HTML, print, markdown]
weight: 62
---

## 完整卡片 {#full}

> [!SOCIAL] Ada Lovelace `@ada`
>
> 帖子正文是普通的 **Markdown**，可以带[链接](https://example.org/)
> 和 `行内代码`。
>
> ![帖子附带的图片](media/content-primitives-global.png)
{avatar="media/content-primitives-global.png" date="2026-02-15" url="https://x.com/ada/status/1890000000000000000" platform="x"}

## 其他平台 {#platforms}

> [!SOCIAL] Grace Hopper `@grace@mastodon.social`
>
> 没有头像时，卡片显示首字符。
{platform="mastodon" date="2026-03-01 08:30"}

> [!SOCIAL] `@oink.bsky.social`
>
> 只有账号名，没有作者名。
{platform="bluesky" url="https://bsky.app/profile/oink.bsky.social/post/3kxyz"}

## 引用帖 {#quote}

> [!SOCIAL] OINK `@pgsty`
>
> OINK v1.6.0 已发布。
>
> > [!SOCIAL] Hugo `@GoHugoIO`
> >
> > Hugo v0.170.0 移除了 extended 版本。
> {date="2026-11-13" url="https://x.com/GoHugoIO/status/2"}
{date="2026-11-23" url="https://x.com/pgsty/status/1" platform="x"}
