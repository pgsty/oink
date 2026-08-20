---
title: 在博客壳上沉浸式阅读
linkTitle: 沉浸式阅读
date: 2026-08-19
description: >-
  四个 front matter 键把一个博客页面变成以阅读为先的版式:题图化作 hero
  开场,骨架只剩大纲栏,而每个博客组件都在折叠线以下的老位置上。
authors: [vonng]
featured_image: hero
toc_style: flow
toc_taxonomies: false
sidebar_enabled: false
tags: [Oink]
---

本页由普通的博客壳渲染——背后没有任何特殊 type。它的 front matter 设了四个
键,一个 section 也可以在 cascade 里把同样四行写一次:

```yaml
featured_image: hero      # 题图成为全幅开场
toc_style: flow           # 更宽的大纲,随开场一起下移
toc_taxonomies: false     # 右栏只留大纲
sidebar_enabled: false
```

## 题图 {#the-hero}

携带题图的页面以它开篇。`hero` 把图片变成视口顶部的全幅背景,在正文开始之前
被遮罩淡出,标题块下移为它让出空间——而且因为是壳自己绘制的,section 索引页
也会在列表上方获得同样的开场。这张图与页面卡片、社交预览用的是同一张,三处
只解析一次。偏好带边框图片的页面继续用 `featured_image: banner`;没有图的
页面就正常开头。

## 大纲栏 {#the-rail}

`toc_style: flow` 把钉在视口边的大纲换成一条更宽的、随文流的:它从文章起点
——hero 之下——开始,滚动后才钉住。它与 hero 有意保持独立,这样无论各页有没
有图,同一 section 的栏样式都一致。`toc_taxonomies: false` 去掉分类法云;
一条无事可做的栏干脆什么也不渲染。

## 保留的部分 {#what-stays-on}

折叠线以下的一切都是你熟悉的博客文章:信息行、标签徽章、作者与档案、
系列条、描述导语,以及带分享栏、页面注记、顺序翻页器和评论的页尾。博客壳
默认不渲染面包屑——`breadcrumb: true` 可以把它请回来;导航栏在 hero 之上
渲染为透明覆盖,随图片一起滚出视口。上面每个键都是普通的 `ui.` 参数,任何
一页随时可以单独翻回去。
