---
title: 提示块
linkTitle: 提示块
description: 由块引用渲染钩子渲染的 GitHub / Obsidian 风格提示块。
outputs: [HTML, markdown]
weight: 10
---

## 标准类型

> [!NOTE]
> 前五种类型在 GitHub 上原生渲染。这一个是 note。

> [!TIP] 带标题的提示
> 标题是行内 Markdown：`代码`、*强调*、[链接](/zh/docs/)。

> [!IMPORTANT]
> 重要信息。

> [!WARNING]
> 警告：这个操作是破坏性的。

> [!CAUTION]
> 小心：可能丢数据。

> [!SUCCESS]
> 一切正常。

> [!DANGER]
> 危险区域。

> [!QUESTION]
> 接下来会发生什么？

> [!EXAMPLE]
> 一个带围栏的示例提示块：
>
> ```bash
> echo "hello"
> ```

> [!QUOTE]
> Talk is cheap. Show me the code.

## 折叠

> [!NOTE]- 默认收起
> 点标题展开。原生 `<details>`，没有 JavaScript 也能用。

> [!TIP]+ 默认展开
> `+` 让它初始就是展开的。

> [!DETAILS] 中性折叠块
> 默认收起，因为 `details` 是没有语义色的折叠类型。
>
> - 列表
> - 在这里可用

> [!DETAILS]+ 带图标的展开折叠块
> 正文。
{icon="fa-solid fa-rocket"}

## 嵌套内容

> [!WARNING] 嵌套内容
> 1. 一个有序列表
> 2. 放在提示块里
>
> | A | B |
> | --- | --- |
> | 1 | 2 |
>
> > [!NOTE]
> > 嵌套的提示块。

## 未知类型

> [!FOO]- 未知类型仍然可见
> 渲染成普通块引用，标记原样保留。
