---
title: 表格
linkTitle: 表格
description: 表格家族——参数表、矩阵、标题、编号、标签页与通栏。
outputs: [HTML, markdown]
weight: 40
---

## 默认表格

| 列 A | 列 B | 列 C |
| --- | --- | ---: |
| a1 | b1 | 1 |
| a2 | b2 | 22 |

## 参数表 `{.fields}`

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | 开启本地索引与命令面板 |
| `offline_search_max_results` | integer | `10` | 结果上限，*支持行内 Markdown* 与 [链接](/zh/docs/) |
| `offline_search_summary_length` | integer | | 摘要长度（空的中间列被省略） |
{.fields caption="搜索参数"}

两列（术语表）：

| 函数 | 说明 |
| --- | --- |
| `now()` | 当前时间戳 |
| `random()` | 一个随机数 |
{.fields}

语义列（`meta=`）渲染出与 shortcode 形态相同的芯片：

| 参数 | 类型 | 必填 | 默认值 | 备注 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `baseURL` | string | 是 | | 部署地址 | 必须带上子路径 |
| `offline_search` | boolean | | `false` | | 构建本地索引 |
{.fields meta="type required default -" caption="语义列"}

## 矩阵 `{.matrix}`

| OS / PG | PG18 | PG17 | PG16 | PG15 | PG14 |
| --- | :---: | :---: | :---: | :---: | :---: |
| EL 9 | ✅ | ✅ | ✅ | ✅ | ✅ |
| EL 8 | ✅ | ✅ | ✅ | ✅ | ❌ |
| Debian 12 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ubuntu 24.04 | ✅ | ✅ | ✅ | ❌ | ❌ |
{.matrix}

## 表格标题 `{caption="…"}`

| 条目 | 取值 |
| --- | --- |
| 版本 | 1.7.0 |
| 许可证 | Apache-2.0 |
{caption="发布事实"}

## 书籍编号表 `{#id num= caption=}`

| 隔离级别 | 脏读 | 更新丢失 |
| --- | --- | --- |
| 读已提交 | 否 | 是 |
| 可串行化 | 否 | 否 |
{#tab_iso num="9-1" caption="各隔离级别允许的异象"}

参见 {{< xref tbl="9-1" anchor="tab_iso" />}}。

## 相邻表格加 `{tab=}`

| 参数 | 取值 |
| --- | --- |
| max_connections | 100 |
{tab="PG 17" group="pgver" value="pg17"}

| 参数 | 取值 |
| --- | --- |
| max_connections | 200 |
{tab="PG 16" value="pg16"}

## 通栏 `{.full-width}`

| A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- |
| a | b | c | d | e | f |
{.full-width}
