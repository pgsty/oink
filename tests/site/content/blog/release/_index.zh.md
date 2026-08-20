---
title: 版本发布
description: OINK 的全部发布说明，从新到旧，每一篇都属于同一条系列。
type: blog
# 紧凑表格是本小节自己的默认形态;因为改用普通博客索引,工具栏的
# 三形态循环(list、cards、table)在这里生效。专用的 `layout: releases`
# 项目名+标签索引仍是主题特性,由独立 fixture 钉住。
blog_index: table
# 整节按沉浸式呈现:小节题图作 hero 开场,无侧栏,右栏是去掉分类法云的
# 随文目录;博客壳本来就不渲染面包屑。索引页自己带一份键(cascade 不
# 作用于声明它的页面),再把同一配方传给下面的每篇发布说明。
images: [/images/releasenote.webp]
featured_image: hero
sidebar_enabled: false
toc_taxonomies: false
cascade:
  images: [/images/releasenote.webp]
  featured_image: hero
  toc_style: flow
  toc_taxonomies: false
  sidebar_enabled: false
---

0.1.0 到 0.6.0 的真实发布说明,以一张紧凑表格整节呈现——用工具栏按钮可
循环切换为行式或卡片。每一篇都属于
[OINK 版本发布](/zh/series/oink-releases/) 系列。
