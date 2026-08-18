---
title: OINK 书籍样例
description: 用于编写书籍的例子
type: book
icon: fa-solid fa-book
weight: 30
book_kind: book
book_number: B
outputs: [HTML, print, markdown]
cascade:
  type: book
---

{{< book-toc depth=3 >}}

这本小书把完整的出版能力压缩在可读范围内：三章、两张共享图片，每章各演示一种带编号内容。

## 图目录

{{< book-figures >}}

## 表目录

{{< book-tables >}}

## 公式目录

{{< book-equations >}}

## 示例目录

{{< book-examples >}}
