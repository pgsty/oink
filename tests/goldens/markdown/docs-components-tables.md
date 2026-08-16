# Tables
> Table family — fields, matrix, caption, numbered, tabs, full-width.
---
LLMS index: [llms.txt](/llms.txt)
---
## Default table
| Column A | Column B | Column C |
| --- | --- | ---: |
| a1 | b1 | 1 |
| a2 | b2 | 22 |
## Reference table `{.fields}`
| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offlineSearch` | boolean | `false` | 开启本地索引与命令面板 |
| `offlineSearchMaxResults` | integer | `10` | 结果上限，*支持行内 Markdown* 与 [链接](/docs/) |
| `offlineSearchSummaryLength` | integer | | 摘要长度（空的中间列被省略） |
{.fields caption="搜索参数"}
Two columns (glossary):
| Function | Description |
| --- | --- |
| `now()` | Current timestamp |
| `random()` | A random number |
{.fields}
## Matrix `{.matrix}`
| OS / PG | PG18 | PG17 | PG16 | PG15 | PG14 |
| --- | :---: | :---: | :---: | :---: | :---: |
| EL 9 | ✅ | ✅ | ✅ | ✅ | ✅ |
| EL 8 | ✅ | ✅ | ✅ | ✅ | ❌ |
| Debian 12 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ubuntu 24.04 | ✅ | ✅ | ✅ | ❌ | ❌ |
{.matrix}
## Caption `{caption="…"}`
| Item | Value |
| --- | --- |
| Version | 1.7.0 |
| License | Apache-2.0 |
{caption="Release facts"}
## Numbered Book table `{#id num= caption=}`
| Isolation | Dirty read | Lost update |
| --- | --- | --- |
| Read committed | no | yes |
| Serializable | no | no |
{#tab_iso num="9-1" caption="Anomalies allowed by isolation level"}
See [Table 9-1](#tab_iso).
## Adjacent tables with `{tab=}`
| Parameter | Value |
| --- | --- |
| max_connections | 100 |
{tab="PG 17" group="pgver" value="pg17"}
| Parameter | Value |
| --- | --- |
| max_connections | 200 |
{tab="PG 16" value="pg16"}
## Full width `{.full-width}`
| A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- |
| a | b | c | d | e | f |
{.full-width}
