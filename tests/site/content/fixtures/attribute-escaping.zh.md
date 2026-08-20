---
title: 属性转义
linkTitle: 属性转义
description: 试图闭合自身属性的 data-* 取值，覆盖每个会发射它们的渲染钩子。
outputs: [HTML, markdown]
weight: 95
---

下面每个取值都带一个双引号加一个事件处理器。共享发射点
（`content/attrs.html`）必须转义这个引号，否则解析器会在那里结束属性，
把后面的内容读成真正的属性 —— 曾经就是这样让一个 `onclick` 绕过了刚刚
拒绝了 `on*` 的策略。

`check-output-security.py` 会让任何出现在输出里的内联事件处理器构建失败，
这一页就是让那条检查真正起作用的东西：示例站和其余 fixture 里没有任何
内容会发射带引号的 generic 属性取值。

每个块同时带一个 class，这样回归就无法躲在"属性块根本没被解析"背后。

## 标题
{#biao-ti}

### 带有恶意 data 取值的标题
{#attr-escape-heading .attr-escape data-probe="q\" onmouseover=alert(1) data-z=\"q"}

## 提示块
{#ti-shi-kuai}

> [!NOTE]
> 提示块外层承载这个取值。
{.attr-escape data-probe="q\" onmouseover=alert(2) data-z=\"q"}

## 表格
{#biao-ge}

| 列 | 值 |
| --- | --- |
| 第一 | 1 |
{.attr-escape data-probe="q\" onmouseover=alert(3) data-z=\"q"}

## 图片
{#tu-pian}

![蓝金独立预览](/media/content-primitives-global.png)
{.attr-escape data-probe="q\" onmouseover=alert(4) data-z=\"q"}
