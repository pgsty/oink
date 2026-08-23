---
title: 博客
type: blog
description: 真实的 OINK 发布说明与工程随笔，接线到全部博客特性。
weight: 20
icon: fa-solid fa-blog
# 本栏目索引用卡片网格，两个子栏目保持行式，一个站点里多种形态都看得到。
# 站点配置打开了读者切换（ui.blog_index_toggle），因此每个博客索引都带有
# 循环 list、cards、table 的工具栏按钮。
blog_index: cards
cascade:
  type: blog
  images: [/images/oink.webp]
  # Fumadocs 式栏目标识：博客整体走紫罗兰主题色，docs 保持默认藏青。只写浅色，
  # 发射出的深色调即固定「向白提亮」派生；featured-wash.md 按页覆盖这个颜色。
  theme_color: '#7c3aed'
  # 标题下的信息行总是带日期；这个开关在旁边加上字数与阅读分钟数。
  reading_time: true
  # 纯静态意图链接加一个本地复制按钮。读者不点，就没有任何请求。这里用了十六个可选
  # 目标中的十三个，其余三个（reddit、line、pinterest）见主题 hugo.yaml。
  share: [x, bluesky, mastodon, facebook, linkedin, hackernews, telegram,
          whatsapp, weibo, chatgpt, claude, email, copy]
---

下面两个栏目：发布说明是一条有编号的系列，OINK 随笔的署名来自 `authors` 分类法。

![OINK 标识，放在这里让博客索引带上一张可缩放的正文图片](/images/oink.webp)
