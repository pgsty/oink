---
title: ECharts
linkTitle: ECharts
description: 在 `echarts` 围栏里用 YAML 或 JSON 写图表选项，Hugo 构建期校验，浏览器用本地 ECharts 画出跟随深浅色的统计图。
icon: fa-solid fa-chart-line
weight: 150
search_keywords: [ECharts, 图表, 统计图, 柱状图, 折线图, 饼图, chart, bar, line, pie, height, theme, OinkEchartsFunctions]
---

`echarts` 围栏的正文是一段 YAML 或 JSON 的 ECharts 选项对象，不是代码。适用于需要坐标轴、序列与图例的定量图表；只表达关系与流程时用 [Mermaid](/zh/docs/mermaid/)，只表达顺序与层级时用 [Infographic](/zh/docs/infographic/)。Hugo 在构建期解析选项，解析失败则构建失败；浏览器用随主题分发的 ECharts 绘图，只有用到它的页面加载运行时。

## 最简例子 {#minimal}

一个柱状图只需要三段：`xAxis`、`yAxis`、`series`。下面是本站文档六个栏目各有多少页。

````markdown {title="源码"}
```echarts {height="320px"}
tooltip:
  trigger: axis
xAxis:
  type: category
  data: [简介, 快速上手, 创作内容, 组件, 定制站点, 维护管理]
yAxis:
  type: value
  name: 页数
series:
  - name: 页数
    type: bar
    data: [4, 3, 8, 22, 15, 7]
```
````

```echarts {height="320px"}
tooltip:
  trigger: axis
xAxis:
  type: category
  data: [简介, 快速上手, 创作内容, 组件, 定制站点, 维护管理]
yAxis:
  type: value
  name: 页数
series:
  - name: 页数
    type: bar
    data: [4, 3, 8, 22, 15, 7]
```

两种格式都接受，YAML 不需要引号与逗号，写起来更短。缩进写错、正文解析成数组而不是映射，构建在这一行失败，不会输出一张空白图。

## 多序列折线 {#line}

`series` 是数组，多一项就是多一条线；`legend` 让读者单独隐藏其中一条。下面是 PostgreSQL 各大版本的发布年份，以及按社区五年支持策略推算的终止年份。

````markdown {title="源码"}
```echarts {height="360px"}
tooltip:
  trigger: axis
legend:
  data: [发布年份, 支持终止]
grid:
  left: 56
  right: 24
  top: 48
  bottom: 40
xAxis:
  type: category
  name: 大版本
  data: ["9.6", "10", "11", "12", "13", "14", "15", "16", "17", "18"]
yAxis:
  type: value
  min: 2015
  max: 2031
  name: 年份
series:
  - name: 发布年份
    type: line
    smooth: false
    data: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
  - name: 支持终止
    type: line
    lineStyle:
      type: dashed
    data: [2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
```
````

```echarts {height="360px"}
tooltip:
  trigger: axis
legend:
  data: [发布年份, 支持终止]
grid:
  left: 56
  right: 24
  top: 48
  bottom: 40
xAxis:
  type: category
  name: 大版本
  data: ["9.6", "10", "11", "12", "13", "14", "15", "16", "17", "18"]
yAxis:
  type: value
  min: 2015
  max: 2031
  name: 年份
series:
  - name: 发布年份
    type: line
    smooth: false
    data: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
  - name: 支持终止
    type: line
    lineStyle:
      type: dashed
    data: [2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
```

版本号要加引号：YAML 里不带引号的 `10` 是数字，`9.6` 也是；作为分类轴的标签它们必须是字符串。

## 饼图与环形图 {#pie}

`radius` 给两个值就是环形图。下面是 OINK 的 29 个 shortcode 按用途的构成。

````markdown {title="源码"}
```echarts {height="340px"}
tooltip:
  trigger: item
  formatter: "{b}：{c} 个（{d}%）"
legend:
  bottom: 0
series:
  - type: pie
    radius: [42%, 70%]
    itemStyle:
      borderRadius: 6
      borderWidth: 2
    label:
      formatter: "{b} {c}"
    data:
      - { value: 14, name: 核心组件 }
      - { value: 10, name: Book 编号与索引 }
      - { value: 3, name: 发布与下载 }
      - { value: 2, name: OpenAPI }
```
````

```echarts {height="340px"}
tooltip:
  trigger: item
  formatter: "{b}：{c} 个（{d}%）"
legend:
  bottom: 0
series:
  - type: pie
    radius: [42%, 70%]
    itemStyle:
      borderRadius: 6
      borderWidth: 2
    label:
      formatter: "{b} {c}"
    data:
      - { value: 14, name: 核心组件 }
      - { value: 10, name: Book 编号与索引 }
      - { value: 3, name: 发布与下载 }
      - { value: 2, name: OpenAPI }
```

`{b}` `{c}` `{d}` 是 ECharts 的模板占位符（名称 / 数值 / 百分比），写在字符串里即可，不需要函数。

## 高度与通栏 {#size}

`height` 默认 `400px`，接受 `px rem em vh vw %`；`full=true` 去掉正文的宽度限制，让图铺满内容区。适用于数据点多、标签长的图。

````markdown {title="源码"}
```echarts {height="260px" full=true}
tooltip:
  trigger: axis
grid:
  left: 40
  right: 16
  top: 24
  bottom: 32
xAxis:
  type: category
  data: [i18n, 分类法, 字体令牌, 内容契约, 导航, 运行时, 侧栏图标, 搜索, 动作, 命令面板, 双语文档, 阅读, 发布物, 下载, Landing, Book, 迁移, 键盘, 页尾, 输出, 金样本]
yAxis:
  type: value
  name: 脚本数
series:
  - type: bar
    data: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
```
````

```echarts {height="260px" full=true}
tooltip:
  trigger: axis
grid:
  left: 40
  right: 16
  top: 24
  bottom: 32
xAxis:
  type: category
  data: [i18n, 分类法, 字体令牌, 内容契约, 导航, 运行时, 侧栏图标, 搜索, 动作, 命令面板, 双语文档, 阅读, 发布物, 下载, Landing, Book, 迁移, 键盘, 页尾, 输出, 金样本]
yAxis:
  type: value
  name: 脚本数
series:
  - type: bar
    data: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
```

无效的高度（`360`、`36pt`）会让构建失败，不会退回默认值。

## 深浅色 {#theme}

不写 `theme` 时，图按读者当前的配色模式初始化；切换配色时图原地重绘，不刷新页面。容器尺寸变化时自动 resize。把本页切到深色，上面每张图的底色与文字随之改变。

写定 `theme` 则固定配色，两种模式下都是同一套：

````markdown {title="源码"}
```echarts {height="240px" theme="dark"}
xAxis:
  type: category
  data: [HTML, 打印, Markdown, RSS]
yAxis:
  type: value
series:
  - type: bar
    data: [1, 1, 1, 1]
```
````

```echarts {height="240px" theme="dark"}
xAxis:
  type: category
  data: [HTML, 打印, Markdown, RSS]
yAxis:
  type: value
series:
  - type: bar
    data: [1, 1, 1, 1]
```

运行时内置的只有 `dark`；其它 ECharts 主题要先用 `echarts.registerTheme()` 注册才能在这里引用。没有品牌要求时不写 `theme`，让图跟随站点配色。

## 回调：`$fn:` {#callbacks}

围栏是数据，不能带 JavaScript。某个选项需要函数时（提示框格式化、数据驱动的颜色），在选项里写字符串 `"$fn:名字"`，再把这个名字注册到 `window.OinkEchartsFunctions`：

````markdown {title="源码"}
<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.pageShare = function (params) {
    var p = params[0];
    return p.name + '：' + p.value + ' 页，占全站 ' + Math.round((p.value / 59) * 100) + '%';
  };
</script>

```echarts {height="300px"}
tooltip:
  trigger: axis
  formatter: "$fn:pageShare"
xAxis:
  type: category
  data: [简介, 快速上手, 创作内容, 组件, 定制站点, 维护管理]
yAxis:
  type: value
series:
  - type: bar
    data: [4, 3, 8, 22, 15, 7]
```
````

<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.pageShare = function (params) {
    var p = params[0];
    return p.name + '：' + p.value + ' 页，占全站 ' + Math.round((p.value / 59) * 100) + '%';
  };
</script>

```echarts {height="300px"}
tooltip:
  trigger: axis
  formatter: "$fn:pageShare"
xAxis:
  type: category
  data: [简介, 快速上手, 创作内容, 组件, 定制站点, 维护管理]
yAxis:
  type: value
series:
  - type: bar
    data: [4, 3, 8, 22, 15, 7]
```

鼠标悬停在任意一根柱子上，提示框里是该函数拼出的句子。名字未注册时该选项解析为 `undefined`，图按未设置该项绘制，构建与运行都不报错。脚本与围栏放在同一页的相邻位置，便于一起改动。

这段脚本属于站点代码，按代码审查对待。字符串模板（`{b}` `{c}` `{d}`）能表达的格式不写成函数。

## 承担论证的图表 {#complex}

上面的例子演示的是选项。真实文档里的图表通常还要多做一件事：把某一个序列推到前景，让其余部分退成背景。两种选项写法就能覆盖其中大部分工作。

第一种是带数据驱动配色的排序条形图。`itemStyle.color` 接受函数，于是 `$fn:` 可以给正在论证的那一行返回渐变、给其余行返回平色；`showBackground` 在每根条后面画出轨道，短的那几行也就不至于难以辨认。

````markdown {title="源码"}
<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.starCount = function (p) {
    return Number(p.value).toLocaleString('zh-CN');
  };
  window.OinkEchartsFunctions.starColour = function (p) {
    if (p.name !== 'pgsty/pigsty') return '#7aa6c2';
    return new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0, color: '#d94841' },
      { offset: 1, color: '#f97316' }
    ]);
  };
</script>

```echarts {height="360px" full=true}
grid: { left: 260, right: 88, top: 8, bottom: 28 }
xAxis: { type: value, max: 6000, splitLine: { lineStyle: { type: dashed, opacity: 0.45 } } }
yAxis:
  type: category
  inverse: true
  axisLabel: { align: right, fontFamily: monospace, fontSize: 11 }
  data: [pgsty/pigsty, polardb/PolarDB-for-PostgreSQL, tensorchord/pgvecto.rs, Tencent/TBase, apache/cloudberry, IvorySQL/IvorySQL]
series:
  - type: bar
    barWidth: 18
    showBackground: true
    backgroundStyle: { color: "rgba(148, 163, 184, 0.16)" }
    itemStyle: { color: "$fn:starColour", borderRadius: [0, 5, 5, 0] }
    label: { show: true, position: right, formatter: "$fn:starCount", fontWeight: 600 }
    data: [5521, 3191, 2181, 1439, 1315, 1051]
```
````

<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.starCount = function (p) {
    return Number(p.value).toLocaleString('zh-CN');
  };
  window.OinkEchartsFunctions.starColour = function (p) {
    if (p.name !== 'pgsty/pigsty') return '#7aa6c2';
    return new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0, color: '#d94841' },
      { offset: 1, color: '#f97316' }
    ]);
  };
</script>

```echarts {height="360px" full=true}
grid: { left: 260, right: 88, top: 8, bottom: 28 }
xAxis: { type: value, max: 6000, splitLine: { lineStyle: { type: dashed, opacity: 0.45 } } }
yAxis:
  type: category
  inverse: true
  axisLabel: { align: right, fontFamily: monospace, fontSize: 11 }
  data: [pgsty/pigsty, polardb/PolarDB-for-PostgreSQL, tensorchord/pgvecto.rs, Tencent/TBase, apache/cloudberry, IvorySQL/IvorySQL]
series:
  - type: bar
    barWidth: 18
    showBackground: true
    backgroundStyle: { color: "rgba(148, 163, 184, 0.16)" }
    itemStyle: { color: "$fn:starColour", borderRadius: [0, 5, 5, 0] }
    label: { show: true, position: right, formatter: "$fn:starCount", fontWeight: 600 }
    data: [5521, 3191, 2181, 1439, 1315, 1051]
```

回调里可以直接用全局的 `echarts`，因为运行时早已在页面上——函数是图表在库加载之后调用的。注意那个 `full=true`：轴标签占掉 260 像素的图表，正文栏是放不下的。

第二种写法是"分解 vs. 预算"。用 `stack:` 把各部分堆起来，再用 `barGap: "-100%"` 和更低的 `z` 把预算画成压在第一根条上的第二根条，于是它读起来像轨道而不像数据。类目轴里的空字符串会在组与组之间留出空档，序列里的 `"-"` 则跳过那一行。

````markdown {title="源码"}
```echarts {height="300px"}
tooltip: { trigger: axis, axisPointer: { type: shadow }, formatter: "$fn:phaseSeconds" }
legend: { top: 0, data: [故障检测, 重启超时, 切换完成] }
grid: { left: 72, right: 24, top: 40, bottom: 28 }
xAxis:
  type: value
  name: 秒
  max: 100
  minorTick: { show: true, splitNumber: 5 }
  minorSplitLine: { show: true, lineStyle: { type: dotted, opacity: 0.2 } }
yAxis:
  type: category
  axisLabel: { fontFamily: monospace, fontSize: 10 }
  data: [safe-max, safe-avg, "", fast-max, fast-avg]
series:
  - { name: 故障检测, type: bar, stack: rto, barWidth: 18, z: 2, itemStyle: { color: "#b07aa1" }, data: [10, 5, "-", 5, 3] }
  - { name: 重启超时, type: bar, stack: rto, z: 2, itemStyle: { color: "#f28e2c" }, data: [45, 45, "-", 15, 15] }
  - { name: 切换完成, type: bar, stack: rto, z: 2, itemStyle: { color: "#4e79a7" }, data: [18, 11, "-", 9, 6] }
  - { name: RTO 预算, type: bar, barGap: "-100%", barWidth: 18, z: 0, itemStyle: { color: "rgba(128,128,128,0.14)" }, data: [90, 90, "-", 30, 30] }
```
````

<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.phaseSeconds = function (params) {
    if (!params || !params.length || params[0].name === '') return '';
    var rows = params
      .filter(function (p) { return p.value !== '-' && p.value != null; })
      .map(function (p) { return p.marker + ' ' + p.seriesName + '：' + p.value + ' 秒'; });
    return '<b>' + params[0].name + '</b><br/>' + rows.join('<br/>');
  };
</script>

```echarts {height="300px"}
tooltip: { trigger: axis, axisPointer: { type: shadow }, formatter: "$fn:phaseSeconds" }
legend: { top: 0, data: [故障检测, 重启超时, 切换完成] }
grid: { left: 72, right: 24, top: 40, bottom: 28 }
xAxis:
  type: value
  name: 秒
  max: 100
  minorTick: { show: true, splitNumber: 5 }
  minorSplitLine: { show: true, lineStyle: { type: dotted, opacity: 0.2 } }
yAxis:
  type: category
  axisLabel: { fontFamily: monospace, fontSize: 10 }
  data: [safe-max, safe-avg, "", fast-max, fast-avg]
series:
  - { name: 故障检测, type: bar, stack: rto, barWidth: 18, z: 2, itemStyle: { color: "#b07aa1" }, data: [10, 5, "-", 5, 3] }
  - { name: 重启超时, type: bar, stack: rto, z: 2, itemStyle: { color: "#f28e2c" }, data: [45, 45, "-", 15, 15] }
  - { name: 切换完成, type: bar, stack: rto, z: 2, itemStyle: { color: "#4e79a7" }, data: [18, 11, "-", 9, 6] }
  - { name: RTO 预算, type: bar, barGap: "-100%", barWidth: 18, z: 0, itemStyle: { color: "rgba(128,128,128,0.14)" }, data: [90, 90, "-", 30, 30] }
```

提示框的格式化函数会丢掉值为 `-` 的条目，否则空档那一行也会弹出一个没有内容的提示框。这张图的完整版本——四套档位、五个阶段——在[书籍样例第三章](/zh/book/chapter-three/#failover-budget)，那里它与解释它的表格和公式排在一起。

## 数据位置 {#data}
围栏正文是字面量。Hugo 不在其中展开 shortcode、front matter 变量或 `data/` 目录里的文件，数字写在围栏里。代价是数据不能共享，收益是图表源码与数据一起进入 Git，diff 能看出改动了哪个数值。

数据经常变动（版本矩阵、发布物清单）时不做成图：改用[表格](/zh/docs/table/)，或[发布与下载页](https://oink.pgsty.com/zh/docs/write/releases/)中由 `data/` 驱动的组件。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-echarts">` 里一个画布容器加一段 `application/json` 选项，本地 ECharts 画图 |
| 打印 | 不画图，输出 `<pre class="td-echarts-source">` 包着的围栏源码 |
| Markdown | 原样保留 `echarts` 围栏与选项源码 |
| RSS | 与打印相同，只有源码 |

图上的结论要在正文里写一遍：打印与 RSS 输出里没有图。

## 参数参考 {#reference}

围栏属性行（```` ```echarts {…} ````）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `height` | CSS 长度 | `400px` | 只接受非负数字加 `px` `rem` `em` `vh` `vw` `%`；其它写法构建失败 |
| `theme` | string | 未设置 | 固定使用某个 ECharts 主题，从此不再跟随站点配色；内置只有 `dark` |
| `full` | bool | `false` | `true` 去掉正文宽度限制，图铺满内容区 |
| `class` | 空格分隔的 class | — | 透传给容器，交给站点 CSS |
{.fields meta="type default"}

`style`、`on*` 与其它未知属性都会让构建失败。围栏正文必须能解析成一个 YAML/JSON 映射，解析失败或解析成数组同样失败。选项键本身是 ECharts 的，以[官方选项手册](https://echarts.apache.org/zh/option.html)为准。

没有站点级参数：ECharts 不需要在 `hugo.yaml` 里开关，用到时才加载。

## 限制与常见问题 {#limits}

- 围栏里不能写 JavaScript：需要函数时通过 `$fn:` 桥接，未注册的名字解析为 `undefined`，没有报错。
- 围栏不读外部数据：`data/` 目录、front matter 与 shortcode 都引用不到，数字写在围栏里。
- 打印与 RSS 里只有源码，结论要写进正文。
- YAML 的类型转换：分类轴上的 `10`、`9.6`、`on`、`yes` 会被解析成数字或布尔值，需要引号。
- 颜色不是唯一的区分手段：多序列图同时区分线型或标记形状，两种配色模式下都要检查图例对比度。

## 相关 {#related}

- [Infographic](/zh/docs/infographic/) — 表达结构与顺序的信息图，不是统计图
- [表格](/zh/docs/table/) — 数据少、需要精确读数时用表格
- [Mermaid](/zh/docs/mermaid/) — 关系图与流程图
- [代码块](/zh/docs/code/) — 围栏属性行的通用规则
