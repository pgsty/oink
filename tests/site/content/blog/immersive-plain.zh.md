---
title: 无图的沉浸式页面
description: 固定没有题图可渲染时配方的骨架。
date: 2026-08-11
weight: 60
outputs: [HTML, print]
featured_image: hero
toc_style: flow
toc_taxonomies: false
sidebar_enabled: false
breadcrumb: false
images: []
build:
  list: never
---

空的图片列表关掉了博客 cascade 携带的图,于是 hero 模式解析后什么也不渲染:
没有背景,开头不下移,导航栏回到普通的吸顶形态。其余键各自成立——无侧栏、
无面包屑、无云、随文大纲——因为配方是正交的开关,不是一个总闸。

## 只剩正文 {#alone-with-the-text}

大纲栏是正文旁唯一的骨架。
