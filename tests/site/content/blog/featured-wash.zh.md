---
title: 题图底纹
description: 用栏目 cascade 携带的静态图片固定 wash 模式的渲染结果。
date: 2026-08-08
weight: 40
outputs: [HTML, print]
featured_image: wash
# 页面覆盖优先于栏目 cascade；周围没有任何深色值，发射的深色调就从这只青色派生。
theme_color: '#0f766e'
build:
  list: never
---

底纹取自栏目 cascade 的 `images`，那是一个 Hugo 无法处理的静态路径，因此它以
原始 URL 进入文章头部。
