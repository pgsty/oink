---
title: 媒体嵌入
description: asciinema、redoc、swagger 输出形态的回归夹具——交互 HTML、静态 print、纯净 Markdown/RSS。
outputs: [HTML, print, markdown]
weight: 32
---

## 终端录像

{{< asciinema file="images/install.cast" title="安装演示" speed="2" >}}

## ReDoc 阅读器

{{< redoc "openapi/sample.yaml" >}}

## Swagger 浏览器

{{< swagger src="/openapi/sample.yaml" >}}
