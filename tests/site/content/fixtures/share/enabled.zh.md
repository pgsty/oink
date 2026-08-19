---
title: 开启分享的页面
description: 继承来的七个目标：每种 URL 形态各一个，外加本地复制按钮。
weight: 10
---

反馈区上方那一条就是栏目继承下来的清单，每一项代表一种 intent URL 形态：`x` 用两个
参数分别带 URL 和标题，`facebook` 只带 URL、标题由对方抓页面得到，`whatsapp` 收到
的是拼成一串的 `标题 URL`，`pinterest` 在页面有代表图时额外带上 `media`，`claude`
发过去的是一句点明永久链接的提示语，`email` 是先带标题的 `mailto:`，而 `copy` 根本
不是链接，是本地的 `copy_link` 动作。

`bluesky`、`mastodon` 与 WhatsApp 同形，`linkedin` 与 Facebook 同形，`reddit`、
`hackernews`、`telegram`、`line`、`weibo` 与 X 同形，`chatgpt` 与 Claude 同形。
Discord 没有任何形态的分享 URL，所以分享条里没有它，用 `copy` 代替。
