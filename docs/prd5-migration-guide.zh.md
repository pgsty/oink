# OINK PRD 5 迁移与配置参考

基础合并发布版本：OINK 0.4.0（阅读与发布、Landing 与 Book）

展示能力更新：OINK 0.4.1（`content_width`、`example`、`contributors` 与
Landing Hero `title_size`）；组件 API v5（OINK 0.5/0.6）：`example` 改为带原生围栏
形态的 `eg` 包裹组件，`book-figures kind=` 改为 `book-tables` / `book-equations` /
`book-examples`，四种编号组件都获得原生形态（见 `docs/prd5-book-contract.md` 版本 2）

原始设计里程碑：OINK 0.4.0（阅读与发布）、OINK 0.5.0（Landing）与
OINK 0.6.0（Book）

本文描述为 v0.4.0 合并发布冻结的源码，以及 v0.4.1 中向后兼容的展示能力
增量。只有当已签名标签可解析、消费站固定到该标签，而且渲染结果通过冒烟
检查后，消费站才能把功能称为“已发布”。规范性决策见
[阅读/发布契约](prd5-reading-release-contract.md)、
[Landing 契约](prd5-landing-contract.md)与
[Book 契约](prd5-book-contract.md)。

## 发布闸门 {#release-gates}

以下证据状态互不等价：

1. 主题 checkout 源码完成；
2. Hugo Extended 0.160.1 与当前矩阵版本验收通过；
3. 发布为不可变、已签名的主题标签；
4. 消费站固定该标签并完成文档化；
5. 已部署，并在真实 URL 上完成检查。

不要把示例复制到仍固定旧版本的站点后，便假设旧主题认识它。生产环境的
`go.mod` 固定具体版本，不以 `@latest` 作为发布策略。

## 阅读与发布接入 {#reading-and-release-adoption}

Pager 默认为 `docs`、`book`、`blog` 开启；站点可以明确列出类型，页面也可
单独退出：

```yaml
params:
  ui:
    pager:
      types: [docs, book, blog]
---
pager: false
```

手册通常位于已配置的 docs section 下。若文档页刻意直接挂在 `/`，而
`/docs/` 只是总览页，应显式声明这套信息架构，而不是 fork 侧栏：

```yaml
params:
  ui:
    sidebar_root_enabled: true
    docs_root: home
```

`docs_root` 只接受默认值 `section` 或 `home`；侧栏可见树与 Pager 顺序共同
使用同一个解析结果。

站点存在 `data/docs_nav.json` 时，这棵显式树同时定义 Pager 顺序。
`manualLink` 幽灵页与 `sidebar_divider` 分组仍显示在导航里，但不会成为阅读
跳转目标。

分隔符数学需要消费站开启 Goldmark；Hugo 不会合并主题里的 `markup` 配置：

```yaml
markup:
  goldmark:
    extensions:
      passthrough:
        enable: true
        delimiters:
          block: [['\[', '\]'], ['$$', '$$']]
          inline: [['\(', '\)']]
```

主题提供 render hook 与本地 KaTeX CSS；仅写 `math: true` 没有语义。至少构建
一页行内与块公式，确认输出是 MathML，而不是裸露的 `$$`。

若站点暂时无法启用 passthrough，可直接使用严格的 display-only 逃生舱，
无需修改站点配置：

```go-html-template
{{< eq >}}E = mc^2{{< /eq >}}
```

这个无参数形态没有编号、锚点、图注或 Book registry 记录。只有在接入 0.6
的编号 Book 组件时，才加入 `num="5.3"`。

发布事实属于页面 front matter：

```yaml
release:
  version: 1.7.0
  repo: pgsty/pig
  tag: v1.7.0
  prev: v1.6.0
  checksums: SHA256SUMS
```

随后使用 `{{< release-card >}}`，并在该页使用
`{{< release-assets src="release/SHA256SUMS" >}}`。下载数据只写一份
`data/download/<key>.yaml`，同时供 `{{< download "key" >}}` 与 landing 的
`download` section 消费。rolling 渠道不得插版本；只有 pinned 渠道可以展开
`${version}` 与 `${tag}`。

删除站点覆盖前逐项检查：

- 只有站点固定的新主题确实包含 hook 后，才删除本地 passthrough hook；
- 删除复制的 `robots.txt`、404、lastmod、section-index、search-metadata 或
  sidebar-tree 前，先核对真实本地差异；
- 纯分组占位页改用 `sidebar_divider: true` 与 `build.render: never`，但保持
  list 可见，才能维持排序；
- 使用 `{.full-width}` 前先开启 Goldmark block attributes。

## Landing 迁移 {#landing-migration}

把独立页面壳改成内容与本地数据：

```yaml
---
title: Pricing
layout: landing
landing: pricing
---
```

叙事数据放在 `data/landing/pricing/<lang>.yaml`；共享事实可以使用
`title_zh_cn`、`title_zh`、`title` 这条回退链。一次性页面也可在 front
matter 内联 `sections`。首页继续使用 `data/home/`，内部已走同一分发器。

Hero 数据可通过 `title_size` 设置 `rem`、`em` 或 `px` 长度。它会限制大屏
展示标题的最大字号，同时保留 OINK 在较窄屏幕上的响应式断点：

```yaml
hero:
  title: 一个有意写得很长的 Landing 标题
  title_size: 4.45rem
```

站点模板按以下顺序映射到 section registry：

1. 迁移 navbar/footer 外壳，删除页面级重复 chrome；
2. 把 pricing、`pricing-compare`、command、steps、timeline、code plate、
   case study、download、bar chart 改成数据；
3. 用 `hasLanding` 取代复制的 reveal/count/copy/双图/menu JavaScript；
4. 手工复制两遍的跑马灯改为一份 item 数组；
5. 在禁用 JavaScript 与 reduced motion 下检查静态内容。

section 不得发 API 请求。GitHub star、价格、头像、截图等事实由站点 CI 更新，
在 Hugo 构建前变成本地数据；浏览器不得抓取可变事实。

旧 Docsy blocks shortcode 保持兼容但已弃用。新内容迁移到 landing data，
不要再把页面翻译成另一层自定义 HTML partial。

## Book 起步配置与稳定锚点 {#book-starter-and-stable-anchors}

Book 根声明类型并向后代 cascade；需要 print/Markdown 的站点还要显式请求输出：

```yaml
---
title: Systems Handbook
type: book
book_kind: book
book_number: B
outputs: [HTML, print, markdown]
cascade:
  type: book
---
```

站点配置：

```yaml
outputs:
  # 若书根就是站点根，改为配置 home。
  section: [HTML, print]
params:
  # slim | norm | wide；Book 默认为 norm。
  content_width: norm
  ui:
    shell_types: [docs, book, blog, swagger]
    # 右栏已有页内目录时保持 false。
    sidebar_headings: false
    book_draft_banner: true
```

`content_width` 只控制 Book 正文内层宽度：`slim` 是紧凑的文字栏，`norm`
让正文与普通图片、代码块对齐，`wide` 则铺满文章画布。它与控制外层框架的
`page_width` 相互独立，也可在页面 front matter 中单独覆盖。

章节添加 `book_number`、`book_kind`，草稿可写 `book_status: draft`。替换跨页
链接前，先为标题补显式稳定锚点：

```markdown
## Synchronous replication {#sec_replication_sync}

See {{< xref page="../replication" anchor="sec_replication_sync" >}}synchronous replication{{< /xref >}}.
```

公开术语表、索引与引用不能依赖自动生成的标题 ID。每轮编号引用改写后运行
`python3 scripts/check-book.py`。
整书 print 会按源页面为 Markdown 标题 ID 加命名空间，因此不同页面的同名
标题可以安全聚合。Book ToC、`xref` 与图表目录链接会转为文档内片段；普通
Markdown 跨页 URL 刻意仍是站点 URL，必须在整书内工作的引用应迁移为
`xref`。

## 插图迁移配方 {#figure-migration-recipes}

DDIA v2 可机械迁移，因为 `fig` 接受已有的
`src/id/caption/title/class/link/alt/width/height` 参数面。把已有图注编号补成
带引号的 `num`，并优先明确填写有意义的 `alt`：

```markdown
{{< fig num="2-1" id="office_2003" src="/fig/tpme_0201.png"
    caption="The cluttered Word 2003 interface" alt="Word 2003 interface with stacked toolbars" />}}
```

需要可见题注、但不应进入 Hugo 标题目录的代码或数据样例，应使用 `eg`
（编号示例包裹组件，或单围栏原生形态）而不是伪 h4/h6 标题：

````markdown
{{< eg num="2-1" id="example-query" caption="查询当前快照" >}}
```sql
SELECT * FROM snapshot;
```
{{< /eg >}}

```sql {num="2-2" caption="同一示例的单围栏写法" #example-native}
SELECT * FROM snapshot;
```
````

`eg` 目标用 `{{< xref eg="2-1" >}}` 引用、由 `{{< book-examples >}}` 汇总；
`scripts/migrations/oink06.py migrate --only eg` 改写已删除的叶子形态 `example`。

内容页贡献者墙可在 `data/contributors.yaml` 中维护 GitHub 用户名 `items`
列表，并用 `{{< contributors data="contributors" >}}` 渲染。`name`、`role`、
`url` 与 `avatar` 均为可选本地字段，不需要浏览器调用运行时 API。省略头像时
使用本地首字母占位；确需头像时，生产站点应优先填写已提交的根相对路径。

DDIA v1 的一次性站点脚本应当：

1. 盘点每张裸图及其后续图注段落；
2. 从现有文本提出编号，但不修改文件路径；
3. 把伪装成“引用”的图片链接改为 `xref`；
4. 图注缺失或含糊时停止，不猜测；
5. 提交前运行 Book 检查器并对比渲染前后的锚点数量。

pg-internal 先盘点四种图注与 90 处纯文本引用，只包裹清晰匹配的图表并改写
无歧义的 `Figure N`/`Table N`；三张漏注与两张空 alt 必须交给人工处理。
tpme 则把每个 h6 伪标题与图片合成一个 `fig`，保留 O'Reilly 语义 ID，再把
`/en/...#anchor` 改为当前语言的 `xref page=... anchor=...`。

这些是脚本设计位置，不是主题命令：命名与歧义属于站点事实。务必在分支上
执行，保留机器可读的前后清单，并人工审阅所有跳过项。

OINK 现已提供一个默认 dry-run 的可执行工具，并附三份基于真实语料的配方：

- [TPME](prd5-migrate-tpme.md)：迁移 h6 伪图注、编号表格，以及简中正文全部
  `/en/` fragment 泄漏；
- [DDIA](prd5-migrate-ddia.md)：区分 v2 的图、表与示例，并配对 v1 裸图；
- [pg-internal](prd5-migrate-pg-internal.md)：迁移相邻图注/图片、表格，以及不
  依赖目标先后次序的正文编号引用。

每份配方均记录干净 checkout 的清点数字、精确命令、跳过边界、临时克隆严格
构建证据，以及必须为零改动的第二次运行。共享工具是
`scripts/migrations/prd5_book_migrate.py`；其安全契约由双 Hugo 矩阵中的
`scripts/check-prd5-migrations.py` 覆盖。

## Part 层级与整书输出 {#part-hierarchy-and-whole-book-output}

自然层级使用目录；需要保持 URL 时复用已有 `data/docs_nav.json` 来安排 part 与
chapter。不要仅为模板再造一份平行 `chapters.yaml` 模型。
`{{< book-toc depth=3 >}}` 消费同一棵树与 Hugo fragment；
`{{< book-figures >}}`、`{{< book-tables >}}`、`{{< book-equations >}}` 与
`{{< book-examples >}}` 各自汇总一种稳定编号目标。

Book 根的 print URL 是整书 HTML，锚点保留，跨章链接会变成文档内链接。
PDF/EPUB 分页仍由站点负责；已经能用本地 KaTeX/MathML 渲染公式时，不要恢复
依赖网络的 `pandoc --webtex`。

## 验收清单 {#validation-checklist}

- [ ] `python3 scripts/check-prd5-contract.py` 通过。
- [ ] `check-prd5-reading.py`、`check-release-assets.py`、
      `check-download.py`、`check-landing.py`、`check-book.py`、
      `check-prd5-misc.py` 在两个 Hugo 版本上通过。
- [ ] `python3 scripts/check-content-primitives-contract.py` 与
      `python3 scripts/check-i18n.py` 通过。
- [ ] `node --test 'tests/js/**/*.test.js'` 通过。
- [ ] root 与 `/preview/` 构建中的内部 URL 都保留部署前缀。
- [ ] HTML、print、Markdown、RSS 符合输出矩阵。
- [ ] Landing 在无 JavaScript、reduced motion、forced colors 下可用。
- [ ] Book xref、目标编号、图片 alt 与整书 ID 验收通过。
- [ ] 英中两份文档与稳定锚点覆盖一致。
- [ ] 消费站 CI、线上冒烟与公开发布状态和本地主题验收分开记录。
