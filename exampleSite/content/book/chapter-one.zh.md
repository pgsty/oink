---
title: 建立基线
description: 用明确的假设与可度量的证据开始一本技术书籍。
book_kind: chapter
book_number: 1
weight: 10
outputs: [HTML, print, markdown]
---

一本实用手册首先要让读者对系统形成共同认识，并说清楚后续章节依赖哪些事实。

## 描述系统 {#describe-system}

{{< fig num="1-1" id="fig-overview" src="/images/oink.webp" alt="OINK 文档站点总览" caption="文档外壳同时提供导航、正文与局部上下文。" width="600" height="300" />}}

{{< tbl num="1-1" id="tbl-baseline" caption="样例系统的简洁基线。" >}}
| 界面 | 问题 | 预期结果 |
| --- | --- | --- |
| 导航 | 读者能找到全部三章吗？ | 能 |
| 内容 | 带编号对象可以被引用吗？ | 可以 |
| 输出 | HTML、打印与 Markdown 一致吗？ | 一致 |
{{< /tbl >}}

{{< eq num="1.1" id="eq-coverage" caption="覆盖率等于已验证界面数除以计划界面数。" >}}
C = \frac{V}{P}
{{< /eq >}}

{{< eg num="1-1" id="eg-baseline" caption="发布前查询一张小型证据表。" >}}
```sql
SELECT surface, verified
FROM book_evidence
ORDER BY surface;
```
{{< /eg >}}

{{< xref fig="1-1" anchor="fig-overview" />}},
{{< xref tbl="1-1" anchor="tbl-baseline" />}} 与
{{< xref eq="1.1" anchor="eq-coverage" />}} 共同构成基线。第二章将这些证据带入发布流程。

## 保持章节可读 {#keep-readable}

正文说明每个对象为何存在，编号对象则让其他章节或输出格式能够准确引用同一份证据。
