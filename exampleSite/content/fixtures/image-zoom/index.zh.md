---
title: 图片缩放
description: 选择性开启的原生图片预览回归样例。
outputs: [HTML, markdown]
weight: 32
---

## 独立成段的 Markdown 图片

![蓝金配色的独立预览图](/media/content-primitives-static.svg)

## 带长图注的处理型图片

![绿紫配色的处理型预览图](media/content-primitives-global.png)
{command="Resize" options="56x" caption="这段刻意写长的图注用来验证：共享的预览在窄屏上仍然可读，保留可访问的图片名称，并且换行时不会引入页面级的横向溢出。"}

## 有图注但替代文字为空的处理型图片

![](legacy-empty.png)
{command="Fit" options="48x32" caption="装饰性的处理型图片不参与缩放，图注仍然提供可见的上下文。"}

## 带链接的图片被排除

[![带链接的图片仍然是链接](/media/content-primitives-static.svg)](/zh/docs/)
