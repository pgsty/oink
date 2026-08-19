---
title: OINK 书籍样例
description: 用于编写书籍的例子
type: book
icon: fa-solid fa-book
weight: 30
book_kind: book
outputs: [HTML, print, markdown]
cascade:
  type: book
---

{{< book-toc depth=3 >}}

四章，每一章都是一类书籍排版的完整样例：用表格承担论证的证据章、用清单承担论证的发布章、
用图表承担论证的运行章，以及用数学承担论证的公式章。下面每一个带编号的图、表、公式与示例，
都可以被任意一章引用，并且在打印与 Markdown 输出中同样成立。

## 图目录

{{< book-figures >}}

## 表目录

{{< book-tables >}}

## 公式目录

{{< book-equations >}}

## 示例目录

{{< book-examples >}}
