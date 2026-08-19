---
title: 公式
linkTitle: 公式
description: 用 KaTeX 写行内与块级数学公式，构建期渲染完毕，读者不下载任何脚本。
icon: fa-solid fa-square-root-variable
weight: 100
search_keywords: [公式, 数学, Math, KaTeX, LaTeX, TeX, passthrough, chem, mhchem, 化学式, 编号公式, eq]
---

公式由 KaTeX 在构建期渲染成 HTML + MathML，页面只额外加载一份本地 KaTeX 样式表，没有 JavaScript，也不请求远程数学服务。行内公式写 `\(…\)`，块级公式写 `$$…$$`、`\[…\]`，另有 `math` 与 `chem` 两种围栏。需要 TikZ 绘图或 KaTeX 不支持的宏包时，改用预渲染的[图片](/zh/docs/image/)。

## 最简例子 {#minimal}

行内公式写在句子中，前后的空格与标点留在分隔符外面。

```markdown {title="源码"}
共享缓冲区命中率是 \(\mathrm{hit} = \frac{H}{H + R}\)，其中 \(H\) 是 `blks_hit`，\(R\) 是 `blks_read`。
```

共享缓冲区命中率是 \(\mathrm{hit} = \frac{H}{H + R}\)，其中 \(H\) 是 `blks_hit`，\(R\) 是 `blks_read`。

## 块级公式 {#display}

独占一段的公式用 `$$` 包起来，居中显示，字号更大。`\[…\]` 是等价写法。

```markdown {title="源码"}
一棵扇出为 \(f\)、共 \(N\) 个键的 B 树，其高度为：

$$
h = \left\lceil \log_{f} N \right\rceil
$$
```

一棵扇出为 \(f\)、共 \(N\) 个键的 B 树，其高度为：

$$
h = \left\lceil \log_{f} N \right\rceil
$$

一行装不下的长公式在正文列内横向滚动，不会把版面撑宽；打印时保持静态。

## 矩阵、分段与对齐 {#environments}

KaTeX 的环境可以用在任何块级公式里。技术写作最常用的是三个：`bmatrix` 写向量与矩阵，`cases` 写分段定义，`aligned` 写跨若干行的推导。三者都在构建期渲染完毕——手机上的读者为此多下载的字节，不比读上面这句话更多。

````markdown {title="源码"}
$$
\begin{bmatrix} a^{l}_{1} \\ \vdots \\ a^{l}_{d_l} \end{bmatrix}
= \sigma\!\left(
\begin{bmatrix}
  w^{l}_{1,1} & \cdots & w^{l}_{1,d_{l-1}} \\
  \vdots      & \ddots & \vdots \\
  w^{l}_{d_l,1} & \cdots & w^{l}_{d_l,d_{l-1}}
\end{bmatrix}
\begin{bmatrix} a^{l-1}_{1} \\ \vdots \\ a^{l-1}_{d_{l-1}} \end{bmatrix}
+
\begin{bmatrix} b^{l}_{1} \\ \vdots \\ b^{l}_{d_l} \end{bmatrix}
\right)
$$
````

$$
\begin{bmatrix} a^{l}_{1} \\ \vdots \\ a^{l}_{d_l} \end{bmatrix}
= \sigma\!\left(
\begin{bmatrix}
  w^{l}_{1,1} & \cdots & w^{l}_{1,d_{l-1}} \\
  \vdots      & \ddots & \vdots \\
  w^{l}_{d_l,1} & \cdots & w^{l}_{d_l,d_{l-1}}
\end{bmatrix}
\begin{bmatrix} a^{l-1}_{1} \\ \vdots \\ a^{l-1}_{d_{l-1}} \end{bmatrix}
+
\begin{bmatrix} b^{l}_{1} \\ \vdots \\ b^{l}_{d_l} \end{bmatrix}
\right)
$$

比正文栏更宽的公式会在自己的视口里横向滚动，而不会把页面撑宽；打印时它是静态的，所以宽矩阵要窄到一张 A4 放得下。

`cases` 用来写"取值取决于落在哪一支"——延迟与超时的论证，本来就是这个形状：

````markdown {title="源码"}
$$
T_{\text{detect}} =
\begin{cases}
0, & \text{崩溃恰好落在探测之前} \\[2pt]
\tfrac{1}{2}\,t_{\text{loop}}, & \text{到达时刻服从均匀分布} \\[2pt]
t_{\text{loop}}, & \text{崩溃恰好落在探测之后}
\end{cases}
$$
````

$$
T_{\text{detect}} =
\begin{cases}
0, & \text{崩溃恰好落在探测之前} \\[2pt]
\tfrac{1}{2}\,t_{\text{loop}}, & \text{到达时刻服从均匀分布} \\[2pt]
t_{\text{loop}}, & \text{崩溃恰好落在探测之后}
\end{cases}
$$

`aligned` 让推导始终对齐在它讨论的那个关系上：`&` 标出要对齐的列，`\\[4pt]` 给相邻两步之间留出呼吸的空间。

````markdown {title="源码"}
$$
\begin{aligned}
\delta^{l}_{j}
&= \frac{\partial C}{\partial z^{l}_{j}}
 = \sum_{k=1}^{d_{l+1}} \frac{\partial C}{\partial z^{l+1}_{k}} \frac{\partial z^{l+1}_{k}}{\partial z^{l}_{j}} \\[4pt]
&= \sigma'\bigl(z^{l}_{j}\bigr) \sum_{k=1}^{d_{l+1}} \delta^{l+1}_{k}\, w^{l+1}_{kj}
 = \sigma'\bigl(z^{l}_{j}\bigr) \Bigl[ \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \Bigr]_{j}
\end{aligned}
$$
````

$$
\begin{aligned}
\delta^{l}_{j}
&= \frac{\partial C}{\partial z^{l}_{j}}
 = \sum_{k=1}^{d_{l+1}} \frac{\partial C}{\partial z^{l+1}_{k}} \frac{\partial z^{l+1}_{k}}{\partial z^{l}_{j}} \\[4pt]
&= \sigma'\bigl(z^{l}_{j}\bigr) \sum_{k=1}^{d_{l+1}} \delta^{l+1}_{k}\, w^{l+1}_{kj}
 = \sigma'\bigl(z^{l}_{j}\bigr) \Bigl[ \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \Bigr]_{j}
\end{aligned}
$$

要用 `aligned` 而不是 `align`：外层的 `$$` 已经把 KaTeX 置于块级模式，而带星号与不带星号的 `align` 是给那些自己给公式编号的文档用的。

## 正文与表格里的公式 {#inline}

行内公式保持所在段落的行高，于是定义可以留在需要它的那句话里：第 \(l\) 层的误差是 \(\delta^{l} \equiv \partial C / \partial z^{l}\)，形状为 \(d_l \times 1\)，把它往前推一层的递推式是 \(\delta^{l} = (W^{l+1})^{\mathsf{T}} \delta^{l+1} \odot \sigma'(z^{l})\)。

表格单元格用同样的定界符，一张公式速查表就是这么写出来的——一行一个方程，不用图片：

```markdown {title="源码"}
| 方程 | 需要什么 | 编号 |
| --- | --- | :---: |
| \(\delta^{L} = \nabla_a C \odot \sigma'(z^{L})\) | 网络输出与标注 | BP1 |
```

| 方程 | 需要什么 | 编号 |
| --- | --- | :---: |
| \(\delta^{L} = \nabla_a C \odot \sigma'(z^{L})\) | 网络输出 \(a^{L}\) 与标注 \(y\) | BP1 |
| \(\delta^{l} = \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \odot \sigma'(z^{l})\) | 后一层的权值与误差 | BP2 |
| \(\nabla_{W^{l}} C = \delta^{l} \bigl(a^{l-1}\bigr)^{\mathsf{T}}\) | 本层误差与前一层输出 | BP3 |
| \(\nabla_{b^{l}} C = \delta^{l}\) | 只需要本层误差 | BP4 |

公式里出现竖线（`\mid`、`\vert`、`|`）会把单元格截断，所以在表格里要写 `\mid` 或 `\vert`，不要直接写那个字符。

## `math` 围栏 {#math-fence}

`math` 围栏是块级公式的另一种写法，不依赖站点的 passthrough 配置。源码在 GitHub 上是一个普通代码块。

````markdown {title="源码"}
```math
N_{\text{conn}} = \lambda \cdot \bar{t}_{\text{resp}}
```
````

```math
N_{\text{conn}} = \lambda \cdot \bar{t}_{\text{resp}}
```

上式是 Little 定律在连接池上的形式：稳态下需要的并发连接数等于到达速率乘以平均响应时间。连接池大小通常远小于客户端数量。

## 化学式与单位 {#chem}

`chem` 围栏使用 KaTeX 的 mhchem 扩展，正文写 `\ce{…}`。同一个扩展也能排物理单位。

````markdown {title="源码"}
```chem
\ce{CO2 + H2O <=> H2CO3 <=> H+ + HCO3^-}
```
````

```chem
\ce{CO2 + H2O <=> H2CO3 <=> H+ + HCO3^-}
```

语法见 [mhchem 手册](https://mhchem.github.io/MathJax-mhchem/)。

## 编号公式 {#numbered}

块级公式下面跟一行属性即成为编号公式。`num` 是作者书写的字符串（`3-1`、`5.3`），主题不自动计数；`#id` 不写时默认为 `eq-<num>`。编号显示在公式右侧，前缀「公式」按站点语言本地化。

```markdown {title="源码"}
$$
\text{WAL}_{\text{day}} \approx \text{TPS} \times \bar{s}_{\text{record}} \times 86400
$$
{#eq-wal num="3-1" caption="每日 WAL 产量的估算"}

见[公式 3-1](#eq-wal)：乘上保留天数就是归档盘容量的下限。
```

$$
\text{WAL}_{\text{day}} \approx \text{TPS} \times \bar{s}_{\text{record}} \times 86400
$$
{#eq-wal num="3-1" caption="每日 WAL 产量的估算"}

见[公式 3-1](#eq-wal)：乘上保留天数就是归档盘容量的下限。

`caption`（纯文本）可以省略。`#id` 与 `caption` 必须与 `num` 同时出现，不存在「半编号」的公式。同一页里重复的 ID、或同一编号指向两个 ID，都会构建失败。

## 交叉引用 {#xref}

正文可以用普通链接引用编号公式，上一节即是这种写法。跨页引用、或需要自动带上「公式 N」标签时用 `xref`：

```markdown {title="源码"}
容量规划从 {{</* xref eq="3-1" anchor="eq-wal" /*/>}} 开始。
```

容量规划从 {{< xref eq="3-1" anchor="eq-wal" />}} 开始。

`xref` 可以写在目标之前，前向引用合法。整本书的公式目录、`book-equations` 索引见[书籍出版](https://oink.pgsty.com/zh/docs/write/book/)。

## `eq` shortcode {#eq-shortcode}

`eq` 供无法开启 passthrough 的站点使用，正文交给同一个 KaTeX 渲染器。不带参数时是一个不注册编号的块级公式；带 `num` 时与上一节的属性行形态等价。

```markdown {title="源码"}
{{</* eq */>}}\sigma_{\text{idx}} = \frac{\text{rows}_{\text{matched}}}{\text{rows}_{\text{total}}}{{</* /eq */>}}

{{</* eq num="3-2" caption="顺序扫描与索引扫描的代价平衡点" */>}}
c_{\text{seq}} \cdot P = c_{\text{rand}} \cdot \sigma \cdot T
{{</* /eq */>}}
```

{{< eq >}}\sigma_{\text{idx}} = \frac{\text{rows}_{\text{matched}}}{\text{rows}_{\text{total}}}{{< /eq >}}

{{< eq num="3-2" caption="顺序扫描与索引扫描的代价平衡点" >}}
c_{\text{seq}} \cdot P = c_{\text{rand}} \cdot \sigma \cdot T
{{< /eq >}}

本站已开启 passthrough，日常写作用 `$$`。`eq` 用于迁移来的书稿与不能修改 `hugo.yaml` 的场合。

## 站点前置配置 {#config}

`math` 与 `chem` 围栏无需配置。`$$`、`\[…\]`、`\(…\)` 这些分隔符依赖 Goldmark 的 passthrough 扩展。Hugo 不合并主题的 `markup` 配置，这段必须写在站点自己的配置文件里。本站使用下面这份：

```yaml {title="hugo.yaml"}
markup:
  goldmark:
    parser:
      attribute:
        block: true # 编号公式的属性行需要它
    extensions:
      passthrough:
        enable: true
        delimiters:
          block: [['\[', '\]'], ['$$', '$$']]
          inline: [['\(', '\)']]
```

各键的完整定义见[配置总览](https://oink.pgsty.com/zh/docs/customize/config/)。分隔符不能与站点正文冲突：单个 `$` 没有配进去，避免「$5」这样的价格被当成公式。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | 构建期渲染好的 KaTeX HTML + MathML；本页额外加载一份本地 `katex.min.css`，没有公式的页面不加载 |
| 打印 | 同 HTML，静态，长公式不滚动 |
| Markdown | 原样输出源码：`$$` 块（连同下面的属性行）、`math` / `chem` 围栏、`\(…\)`；`eq` shortcode 输出 `**公式 3-2.** 说明` + 一个 `$$` 块 |
| RSS | 与 Markdown 相同的静态文本 |

任何形态都不加载 JavaScript。

## 参数参考 {#reference}

四种写法：

| 写法 | 位置 | 说明 |
| --- | --- | --- |
| `\(…\)` | 行内 | 由站点 passthrough 配置决定；不能带属性 |
| `$$…$$` / `\[…\]` | 块级 | 同上；可以跟一行属性变成编号公式 |
| ```` ```math ```` | 块级围栏 | 不依赖 passthrough 配置；不接受属性 |
| ```` ```chem ```` | 块级围栏 | 同上，正文写 `\ce{…}` |
{.fields}

块级公式的属性行 `{…}`：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `num` | 字符串 | — | `[0-9A-Za-z.-]+`；注册为编号公式，右侧显示「公式 N」 |
| `#id` | 标识符 | `eq-<num>` | `[A-Za-z][A-Za-z0-9_.:-]*`；锚点与交叉引用目标 |
| `caption` | 纯文本 | — | 编号后面的说明；需要 `num` |
{.fields meta="type default"}

`eq` shortcode 的参数：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `num` | 字符串 | — | 同上；不写就是一个不编号的普通块级公式 |
| `id` | 标识符 | `eq-<num>` | 需要 `num` |
| `caption` | 纯文本 | — | 需要 `num` |
| `class` | class 列表 | — | 需要 `num`；透传给站点 CSS |
| 正文 | TeX | — | 必填，非空 |
{.fields meta="type default"}

TeX 写错（未知命令、括号不配对）会构建失败，报错里带 KaTeX 的信息与源码位置。

## 限制与常见问题 {#limits}

- 分隔符由站点配置决定：`$$`、`\[…\]`、`\(…\)` 是否渲染只取决于站点 `markup.goldmark` 的 passthrough 扩展。front matter 里写 `math: true` 主题不读，缺少配置时 `$$` 仍然原样显示；改用 `math` 围栏或 `eq` 可以绕开。
- 只有 `$$` 块和 `eq` 能编号：`math` 围栏不接受属性行，需要编号就换写法。
- 编号是手写的：主题不自动计数，也不重排；调整章节顺序要自己改 `num`。
- 行内公式不能带属性：属性行只对块级公式有效。
- `caption` 是纯文本：里面的 Markdown 不解析。

## 相关 {#related}

- [代码块](/zh/docs/code/) — 围栏参数与代码编号
- [图片](/zh/docs/image/) — 图的编号用同一套 `{#id num=}`
- [书籍出版](https://oink.pgsty.com/zh/docs/write/book/) — 公式目录与跨页交叉引用
- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/) — `markup.goldmark` 相关键
