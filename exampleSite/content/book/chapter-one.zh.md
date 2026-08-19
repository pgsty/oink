---
title: 建立基线
description: 用明确的假设与可度量的证据开始一本技术书籍。
book_kind: chapter
book_number: 1
weight: 10
outputs: [HTML, print, markdown]
---

> *文档是你写给未来自己的情书。*
>
> —— Damian Conway，《Perl Best Practices》（2005）

一本实用手册首先要让读者对系统形成共同认识，并说清楚后续章节依赖哪些事实。
基线不是引言：引言交代这本书讲什么，基线交代这本书从此把什么当作真的。后面每一章都可以
默认引用它，任何与之冲突的说法都必须明说。[^conway]

## 描述系统 {#describe-system}

先描述读者看得见的部分，再描述看不见的部分。文档站点的外壳只有三个区域——导航、正文、
局部上下文——关于某一页的绝大多数疑问，最后都会归结为"这件事本该由哪个区域回答"。

{{< fig num="1-1" id="fig-overview" src="/images/oink.webp" alt="OINK 文档站点总览" caption="文档外壳同时提供导航、正文与局部上下文。" width="600" height="300" />}}

发布产出的制品是第二个、也更窄的界面：一个版本一页，与全书共用同一条内容流水线。
{{< xref fig="1-2" anchor="fig-artifact" />}} 就是这样一页，第二章会跟踪产生它的那次变更。

![列出版本、日期与已发布制品的发布说明页面](/images/releasenote.webp)
{#fig-artifact num="1-2" caption="发布说明是系统中最窄的界面：一页、一个版本，本身没有导航。" width="600" height="300"}

> [!TIP] 术语：界面、证据、断言
>
> **界面**指读者能够抵达的任何东西：一张渲染出来的页面、一张打印稿、一条 RSS 条目、
> 一份交给语言模型的 Markdown。界面是用来数的，不是用来形容的——一本书说"站点没问题"，
> 等于没有说清楚究竟检查了其中哪几个。
>
> **证据**是别人可以重新算一遍的值：构建的退出码、失效链接的条数、一个校验和。
> **断言**则是正文里的一句话。本书只做能指明证据的断言，所以那些带编号的表格里放的是
> 查询，而不是形容词。

## 就证据达成一致 {#agree-evidence}

两个读者之所以会在"站点算不算做完"上争执，是因为他们数的根本不是同一批东西。
所以先把要数什么写下来。

{{< tbl num="1-1" id="tbl-baseline" caption="样例系统的简洁基线。" >}}
| 界面 | 问题 | 预期结果 |
| --- | --- | --- |
| 导航 | 读者能找到全部四章吗？ | 能 |
| 内容 | 带编号对象可以被引用吗？ | 可以 |
| 输出 | HTML、打印与 Markdown 一致吗？ | 一致 |
| 搜索 | 每一章都带有自己的关键词吗？ | 都带 |
{{< /tbl >}}

这四个界面由不同的代码路径生成，因而失败的方式也各不相同。与其用一段话保证"它们都没问题"，
不如用一张表记下每一个到底是怎么验证的。

| 输出 | 由谁生成 | 对照什么验证 | 什么情况下构建失败 |
| --- | --- | --- | --- |
| HTML | 页面布局 | 解析后的 DOM：无重复 ID，每套特性一个包 [^goldens] | 出现未知的围栏属性 |
| 打印 | `layouts/**/*.print.html` | 同一份 DOM，去掉交互性构件 [^print] | 该展开的折叠块仍然折叠 |
| Markdown | `layouts/all.md` | 与保存的 golden 逐字节比对 [^goldens] | 有 HTML 漏进纯文本 |
| RSS | 订阅源模板 | 与 Markdown 同一套规则，另去掉页内链接 | 出现无法解析的相对链接 |
{#tbl-outputs num="1-2" caption="每种输出状态各自对照什么验证、又因什么而失败。"}

注意 {{< xref tbl="1-2" anchor="tbl-outputs" />}} 的每一行都指名了一个文件。
没有文件的那一行只是愿望，不是检查。

## 亮出证据 {#show-evidence}

带编号的示例，是正文可以直接指着说话的清单。短到一屏能读完，真到可以照着跑。

{{< eg num="1-1" id="eg-baseline" caption="发布之前，先查一张小小的证据表。" >}}
```sql
SELECT surface, verified
FROM book_evidence
ORDER BY surface;
```
{{< /eg >}}

生成这张表的清单就放在内容旁边一起进版本库，于是评审者在一个 diff 里既能看见断言，
也能看见它的输入。

```yaml {num="1-2" caption="基线的计算输入——四个界面，各有唯一负责人。" #eg-inventory}
surfaces:
  - name: navigation
    owner: shell
    checked_by: bin/check-navigation-contract.py
  - name: content
    owner: markup
    checked_by: bin/check-content-primitives.py
  - name: output
    owner: layouts
    checked_by: bin/check-goldens.py
  - name: search
    owner: search
    checked_by: bin/check-search.py
```

## 度量覆盖率 {#measure-coverage}

覆盖率是本书唯一不加限定就引用的数字，因为它是唯一一个输入也被完整写下来的数字。

{{< eq num="1.1" id="eq-coverage" caption="覆盖率等于已验证界面数除以计划界面数。" >}}
C = \frac{V}{P}
{{< /eq >}}

单一比值会掩盖它有多少成分只是靠某一次走运的构建撑着。按照被执行的频率给每个界面加权，
这个数字就不会再替没人看的部分说好话。

$$
C_{w} = \frac{\sum_{i=1}^{n} w_i v_i}{\sum_{i=1}^{n} w_i},
\qquad w_i = \log_{2}\left(1 + r_i\right)
$$
{#eq-weighted num="1.2" caption="加权覆盖率，其中 r 表示界面 i 每周被重建的次数。"}

取 \(v_i \in \{0, 1\}\)、\(r_i\) 为每周重建次数，当所有界面重建得一样频繁时，
{{< xref eq="1.2" anchor="eq-weighted" />}} 就退化为
{{< xref eq="1.1" anchor="eq-coverage" />}}。两个数字之间的差额，正是站点中只被顺带
检查到的那一部分。

## 让章节可读 {#keep-readable}

正文解释每个对象为什么存在；带编号的对象则让另一章、另一种输出格式都能精确引用同一份证据。
{{< xref fig="1-1" anchor="fig-overview" />}}、
{{< xref tbl="1-1" anchor="tbl-baseline" />}} 与
{{< xref eq="1.1" anchor="eq-coverage" />}} 共同构成基线，第二章把这些证据接入发布流程。

## 参考文献 {#references}

[^conway]: Damian Conway. *Perl Best Practices*. O'Reilly Media, 2005 年 7 月. ISBN 978-0-596-00173-5.
[^goldens]: [Golden testing](https://ro-che.info/articles/2017-12-04-golden-tests). *ro-che.info*, 2017 年 12 月.
[^print]: [Designing for print with CSS Paged Media](https://www.w3.org/TR/css-page-3/). W3C 工作草案, *w3.org*, 2018 年 10 月.
