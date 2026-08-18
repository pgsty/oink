---
title: 带编号的证据
description: 第一章带有稳定的 ID 与随输出形态变化的标签。
book_kind: chapter
book_number: 1
weight: 10
outputs: [HTML, print, markdown]
resources:
  - src: diagram.png
    params:
      alt: 一张解析成功的页面资源位图
---

前向引用：{{< xref fig="1-1" anchor="office_2003" />}}。

跨章节标题引用：{{< xref page="../chapter-two" anchor="stable-heading" >}}那个稳定的标题{{< /xref >}}。

{{< fig num="1-1" id="office_2003" src="/icons/logo.svg" alt="用作样例的 OINK 标识" caption="一张稳定的、手工编号的图。" class="fixture-figure" width="120" height="120" />}}

{{< fig num="1-2" id="resolved_bitmap" src="diagram.png" caption="页面资源位图：共享解析器提供固有尺寸与资源上的替代文字。" />}}

{{< fig num="1-3" id="resolved_vector" src="vector.svg" caption="页面资源 SVG：解析不报错，也不声明固有尺寸。" />}}

{{< tbl num="1-1" caption="各输出形态下的行为。" >}}
| 输出 | 标签 | 锚点 |
| --- | --- | --- |
| HTML | 可见 | 稳定 |
| 打印 | 可见 | 稳定 |
{{< /tbl >}}

{{< eq num="1.1" caption="直接调用 ToMath 的逃生口。" >}}X \approx \frac{C}{R+Z}{{< /eq >}}

{{< eg num="1-1" id="example-query" caption="带标签的示例不会进入页面大纲。" >}}
```sql
SELECT book_number FROM chapters ORDER BY weight;
```
{{< /eg >}}

```sql {num="1-2" caption="原生编号示例：一个围栏加一行属性。" #example-native}
SELECT title FROM chapters WHERE book_number = '1';
```

参见 {{< xref eg="1-1" anchor="example-query" />}} 与 {{< xref eg="1-2" anchor="example-native" />}}。

{{< contributors data="contributors" >}}

## 本章细节 {#chapter-details}

这个标题会进入深度为三的书籍目录。

## 共用标题 {#shared-heading}

这个刻意重复的标题 ID 在整书之外只在本页生效。
