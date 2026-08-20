---
title: 表格
linkTitle: 表格
description: 普通 GFM 表格加一行属性，就得到标题、兼容矩阵、参数表、编号表或标签页；宽表格自己横向滚动，不撑宽页面。
icon: fa-solid fa-table
weight: 50
search_keywords: [表格, Table, matrix, 矩阵, full-width, 全宽, caption, 表格标题, 编号表, 横向滚动, GFM]
---

表格是普通的 GFM 管道表格。主题的表格渲染钩子把每张表包进一块可横向滚动的区域，表格下面那一行 `{…}` 属性决定它是哪一种表：带标题的表、兼容矩阵、参数表、编号表或标签页。合并单元格、排序与筛选不在能力范围内，需要它们的场景请改换呈现方式。

## 最简例子 {#minimal}

不写属性行就是一张普通表。对齐方式照旧来自分隔行，表头单元格是 `th scope="col"`。

```markdown {title="源码"}
| 组件 | 端口 | 用途 |
| --- | :---: | --- |
| PostgreSQL | 5432 | 数据库 |
| Pgbouncer | 6432 | 连接池 |
| Patroni | 8008 | 高可用编排 |
```

| 组件 | 端口 | 用途 |
| --- | :---: | --- |
| PostgreSQL | 5432 | 数据库 |
| Pgbouncer | 6432 | 连接池 |
| Patroni | 8008 | 高可用编排 |

## 宽表格自己滚动 {#scroll}

列太多的表不会把页面撑宽，它在自己的区域里横向滚动。这块区域可以用键盘聚焦：Tab 停入后方向键滚动，无障碍名称是本地化的「可横向滚动的表格」。

```markdown {title="源码"}
| 集群 | 角色 | 版本 | 状态 | 延迟 | 连接数 | 大小 | 备份 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pg-meta | primary | 18.1 | running | — | 42 | 12 GB | 2026-08-17 |
| pg-test | replica | 18.1 | streaming | 12 ms | 8 | 12 GB | 2026-08-17 |
```

| 集群 | 角色 | 版本 | 状态 | 延迟 | 连接数 | 大小 | 备份 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pg-meta | primary | 18.1 | running | — | 42 | 12 GB | 2026-08-17 |
| pg-test | replica | 18.1 | streaming | 12 ms | 8 | 12 GB | 2026-08-17 |

## 表格标题 {#caption}

`{caption="…"}` 加一个可见的 `<caption>`，纯文本，不给表编号。

```markdown {title="源码"}
| 条目 | 取值 |
| --- | --- |
| 主题版本 | v0.5.0 |
| Hugo 下限 | 0.160.1 Extended |
| 许可证 | Apache-2.0 |
{caption="本站当前使用的主题事实"}
```

| 条目 | 取值 |
| --- | --- |
| 主题版本 | v0.5.0 |
| Hugo 下限 | 0.160.1 Extended |
| 许可证 | Apache-2.0 |
{caption="本站当前使用的主题事实"}

## 兼容矩阵 {#matrix}

`{.matrix}` 用于「行 × 列 = 支持与否」的对照表：第一列成为行表头（`th scope="row"`），滚动时表头行与第一列吸附不动，其余单元格居中，分隔行另有对齐时以分隔行为准。✅ 与 ❌ 是作者写的字符，主题不解析它们。

```markdown {title="源码"}
| OS / PG | PG18 | PG17 | PG16 | PG15 | PG14 |
| --- | :---: | :---: | :---: | :---: | :---: |
| EL 9 | ✅ | ✅ | ✅ | ✅ | ✅ |
| EL 8 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Debian 13 | ✅ | ✅ | ✅ | ❌ | ❌ |
| Ubuntu 24.04 | ✅ | ✅ | ✅ | ✅ | ❌ |
{.matrix}
```

| OS / PG | PG18 | PG17 | PG16 | PG15 | PG14 |
| --- | :---: | :---: | :---: | :---: | :---: |
| EL 9 | ✅ | ✅ | ✅ | ✅ | ✅ |
| EL 8 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Debian 13 | ✅ | ✅ | ✅ | ❌ | ❌ |
| Ubuntu 24.04 | ✅ | ✅ | ✅ | ✅ | ❌ |
{.matrix}

## 用整个画布 {#full-width}

`{.full-width}` 让表格越出正文栏宽，占满文章可用的宽度。适合列多但每列都短的表。

```markdown {title="源码"}
| 语言 | 代码 | 侧栏 | 搜索 | 目录 | 打印 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 简体中文 | `zh` | ✅ | ✅ | ✅ | ✅ | 已审校 |
| English | `en` | ✅ | ✅ | ✅ | ✅ | 已审校 |
{.full-width}
```

| 语言 | 代码 | 侧栏 | 搜索 | 目录 | 打印 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 简体中文 | `zh` | ✅ | ✅ | ✅ | ✅ | 已审校 |
| English | `en` | ✅ | ✅ | ✅ | ✅ | 已审校 |
{.full-width}

## 参数表 {#fields}

`{.fields}` 把表格变成定义列表：第一列是名称，最后一列是说明，中间列是元数据。它是记录配置项、命令参数、API 字段的形态，写法见[参数表](/zh/docs/fields/)。

```markdown {title="源码"}
| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | 构建本地搜索索引 |
| `page_width` | string | `normal` | 正文栏宽度 |
{.fields meta="type default"}
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | 构建本地搜索索引 |
| `page_width` | string | `normal` | 正文栏宽度 |
{.fields meta="type default"}

## 编号表 {#numbered}

写书或长手册时给表编号：`num` 加可选的 `#id` 与 `caption`。表格会被包进一个带本地化「表 N.」标签的 `<figure>`，并注册成 Book 目标，可以被 `xref` 引用、进入全书表格目录。编号由作者书写，主题不自动计数；`id` 缺省是 `tbl-<num>`。

```markdown {title="源码"}
| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
| --- | --- | --- | --- |
| 读已提交 | 否 | 是 | 是 |
| 可重复读 | 否 | 否 | 是 |
| 可串行化 | 否 | 否 | 否 |
{#tbl-iso num="9-1" caption="PostgreSQL 各隔离级别允许的异象"}

参见 {{</* xref tbl="9-1" anchor="tbl-iso" */>}}。
```

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
| --- | --- | --- | --- |
| 读已提交 | 否 | 是 | 是 |
| 可重复读 | 否 | 否 | 是 |
| 可串行化 | 否 | 否 | 否 |
{#tbl-iso num="9-1" caption="PostgreSQL 各隔离级别允许的异象"}

参见 {{< xref tbl="9-1" anchor="tbl-iso" />}}。

## 表格做成标签页 {#tabs}

连着的表格加 `{tab="…"}` 就组成一组标签页，规则与相邻围栏一致：第一张表上的 `group` 启用 hash、同步与持久化，此后每张表都要 `value`。完整规则见[标签页](/zh/docs/tabs/)。

```markdown {title="源码"}
| 目录 | 内容 |
| --- | --- |
| `content/` | 页面 |
| `data/` | 首页与发布数据 |
{tab="内容" group="repo-layout" value="content"}

| 目录 | 内容 |
| --- | --- |
| `assets/` | SCSS 与图片资源 |
| `static/` | 原样拷贝的文件 |
{tab="资源" value="assets"}
```

| 目录 | 内容 |
| --- | --- |
| `content/` | 页面 |
| `data/` | 首页与发布数据 |
{tab="内容" group="repo-layout" value="content"}

| 目录 | 内容 |
| --- | --- |
| `assets/` | SCSS 与图片资源 |
| `static/` | 原样拷贝的文件 |
{tab="资源" value="assets"}

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-table-scroll">` 可聚焦滚动区 + `<table>`；矩阵与全宽是这个包装器上的修饰 class |
| 打印 | 完整表格按页宽排版；包装器仍在，但标成 `td-table-scroll--static`，不再是可聚焦视口 |
| Markdown | 原样输出源码表格与属性行 |
| RSS | 完整静态表格 |

表格不加载任何脚本。

## 参数参考 {#reference}

表格下一行的属性行：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `.full-width` | 标记 | 无 | 越出正文栏宽，占满文章画布 |
| `.matrix` | 标记 | 无 | 第一列作行表头，表头与首列吸附，其余单元格居中 |
| `.fields` | 标记 | 无 | 渲染成定义列表，见[参数表](/zh/docs/fields/) |
| `caption` | 纯文本 | 无 | 可见表格标题；在 `.fields` 上是列表的标签 |
| `meta` | 角色列表 | 无 | 命名 `.fields` 中间列的语义，取值 `type` `required` `default` `-`；必须与 `.fields` 同用 |
| `#id` | 标识符 | 有 `num` 时为 `tbl-<num>` | `[A-Za-z][A-Za-z0-9_.:-]*`；写在 `<table>`（编号表则写在 `<figure>`）上 |
| `num` | 字符串 | 无 | `[0-9A-Za-z.-]+`；注册为 Book 表目标，标题前加「表 N.」 |
| `tab` / `group` / `value` | 见[标签页](/zh/docs/tabs/) | 无 | 相邻表格组成标签页 |
| `class` | class 列表 | 无 | 站点 CSS 用，原样留在 `<table>` 上 |
| `data-*` / `aria-*` | 字符串 | 无 | 透传 |
{.fields meta="type default"}

`style`、`on*` 与任何其它键都会让构建失败。

## 限制与常见问题 {#limits}

- 互斥规则：`.fields` 不能和 `.matrix`、`.full-width` 或 `num` 一起用；`num` 与 `tab` 互斥；`group`/`value` 需要 `tab`；`meta` 需要 `.fields`。
- 属性行必须紧贴表格：中间空一行，它就变成正文里一段可见的花括号。Markdown 格式化工具常移动这一行，把它包进 `<!-- prettier-ignore-start -->` / `<!-- prettier-ignore-end -->`。
- 没有合并单元格、没有排序、没有筛选：GFM 管道表格能表达的就是全部。需要合并表头的复杂表请拆成两张表或改成一张矩阵。
- 单元格里放不下块内容：多段说明、列表、围栏要用 `fields`/`field` shortcode。
- `.matrix` 的居中由 CSS 实现：分隔行里写了对齐就以分隔行为准。

## 相关 {#related}

- [参数表](/zh/docs/fields/) — `{.fields}` 的完整写法
- [标签页](/zh/docs/tabs/) — 相邻表格组成标签页
- [书籍出版](https://oink.pgsty.com/zh/docs/write/book/) — 编号表、交叉引用与表格目录
- [代码块](/zh/docs/code/) — 属性写在信息行而不是下一行
