---
title: 题图横幅
description: 用一个可处理的页面资源固定 banner 模式的渲染结果。
date: 2026-08-09
weight: 30
outputs: [HTML, print]
featured_image: banner
resources:
  - src: featured.png
    params:
      byline: OINK 固件署名
build:
  list: never
---

横幅取自随页打包的 `featured.png`，它优先于本文从栏目 cascade 继承来的
`images`。这篇文章不进博客列表，既有的回归面因此保持逐字节不变。
