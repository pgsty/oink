# PRD 5 · 场景组件体系（Scenario Components）— 设计沉淀

状态：**已评审** —— 开放问题已于 2026-08-13 裁决（见 §8 逐条决议）；
任务分解与执行提示词见本地 `plan/` 目录（gitignored 工作区，不入库）。
各 track 验收后按惯例冻结为 contract。

日期：2026-08-13

范围：OINK 0.4.x – 0.6.x 三个里程碑的功能规划与公共 API 设计

前置阅读：`docs/content-primitives.md`、`docs/prd4-navigation-command-palette-contract.md`、`CLAUDE.md`

本文是"下一波演化"的总设计。与 PRD 4 contract 不同，本文允许讨论与取舍；
每个 track 验收后，公共决策按惯例冻结进对应 contract 文档
（内容原语进 `content-primitives.md`，页面装配另立 `prd5-*-contract.md`），
并配套 `scripts/check-*.py` 机器检查。

---

## 0. TL;DR

OINK 服务四类场景：**文档站、博客站、落地展示站、书籍站**（调研中识别出
第五类：**连载归档**，如 zj 的 402 期访谈站）。全部 12 个自有站点已运行在
OINK 0.2.1–0.3.0 之上（唯一例外 pigsty.cc 仍在 Docsy 0.15，是迁移对象）。
各站点 `layouts/` 里的覆盖文件，就是主题缺什么的直接证据。

本轮规划五条 track，按三个里程碑交付：

| Track | 对应需求 | 里程碑 | 一句话 |
| --- | --- | --- | --- |
| 5.1 顺序阅读 Pager | 想法 3 | 0.4 | 把现有 blog-only 的原始 pager 升级为侧栏树序的卡片式上一页/下一页，docs/book 可用 |
| 5.2 Release 与资产 | 想法 1 | 0.4 | `release` front matter → 发布卡片；`{{< release-assets >}}` 把 sha256sum 文本渲染为可下载资产表 |
| 5.3 下载页模板 | 想法 4 | 0.4/0.5 | data 驱动的多渠道下载页：版本号一处定义，RPM/DEB/Docker/二进制渠道可配置 |
| 5.4 Landing 泛化 | 想法 5 | 0.5 | 把已有的 12 种 home section 数据驱动系统泛化到任意页面，补 pricing/timeline/compare/marquee |
| 5.5 Book 能力包 | 想法 2 | 0.6 | `book` 类型 + 图/表/公式编号锚点与交叉引用 + 图表目录 + 整书视图；**数学 passthrough 补洞提前到 0.4（唯一 P0 正确性缺陷）** |

核心架构决策：**不建任何平行体系**。五条 track 全部落在既有机制的延长线上
（landing section 注册表、Page Store flag 装配、content-primitives 契约、
输出矩阵、32 locale i18n），并遵守既有的 local-first 红线 —— 主题只渲染
本地数据，任何网络获取（GitHub API、头像、star 数）都属于站点侧脚本/CI 的职责。

---

## 1. 背景：四类场景与站点矩阵

### 1.1 场景模型

| 场景 | 形态特征 | 关键诉求 |
| --- | --- | --- |
| 文档站 docs | 侧栏树 + TOC + 搜索/命令面板 | 已是主线能力（PRD 1–4）；缺顺序阅读、发布/下载页 |
| 博客站 blog | 时间序列表 + taxonomy | 基本完备；pager 已有但样式原始 |
| 落地展示站 landing | 首页/价格页/下载页等营销页 | 数据驱动拼装，不写 HTML；滚动展示组件 |
| 书籍站 book | 章节树 + 顺序阅读 + 图表公式编号 | 全新场景包；五本书已在主题上土法运行 |
| 连载归档 archive | 大量同构线性条目（调研新识别，zj 402 期访谈） | 与 book 共享 pager，不共享图表/数学/书籍装配；另需分组侧栏与归档索引 |

书籍本身也不是一种场景而是一族：纯叙事本（aiempire）、图文书
（tpme/ddia）、技术手册（pg-internal/pg36g）需求几乎不重叠，能力按需
拾取，不做大一统开关。

### 1.2 站点矩阵

| 站点 | 场景 | 版本 | 定制规模（调研实测） |
| --- | --- | --- | --- |
| oink.pgsty.com | docs+blog | 0.3.0 | 最少；仅 Docsy 上游遗留（4 个旧 shortcode + 2 段 SCSS） |
| sow.pgsty.com | docs+blog | 0.3.0 | 自造 `download` type（117 行 layout）+ hero SCSS 覆盖 + lastmod fork + robots |
| silo.pgsty.com | docs+blog | 0.2.1 | 14 个 layout 文件；下载页 682 行 + 落地页 629 行独立 HTML；~3400 行 CSS + 168 行 JS |
| pig.pgsty.com | docs+blog | 0.3.0 | 10 个 layout；落地页 470 行；sidebar-tree 161 行 fork；1658 行拷来的死 CSS |
| exp.pgsty.com | docs+blog | 0.3.0 | 404/robots/9 行缺陷绕行 SCSS；`docs_nav.json`；43 处无效 `{.full-width}` |
| pigsty.cc | docs+blog+landing | **Docsy 0.15** | 首页 2147 行 + 价格页 711 行硬编码；silo 壳层 2571 行（OINK 前身）；9 个自建 shortcode |
| pgsty.com | 纯 landing | 0.3.0 | 5 个绕壳模板 1666 行 + 3316 行 CSS + 547 行 JS + 7 个 portal partial |
| ddia | book（图文书） | 0.3.0 | 自建 figure shortcode（131 处调用）+ llms 模板；简繁×两版四语言变体；pandoc EPUB 链路 |
| pg-internal | book（技术手册） | 0.3.0 | 仅 2 个文件：自建 passthrough hook + 8 行 KaTeX 溢出 CSS；en 版 84 页因构建配置缺失从未上线 |
| aiempire | book（纯叙事） | 0.3.0 | layouts 为空！51 行排版 SCSS；站外 583 行 WeasyPrint 整书 PDF 管线 |
| tpme | book（图文书） | 0.3.0 | 死 figure.html + Hextra i18n/CSS 化石；62 张手编插图；1062 处跨语言链接泄漏 |
| pg36g | book（技术手册） | 0.3.0 | 死 figure.html；站外 4552 行数据模型 + 1428 行 Ruby 工具链；公式线上损坏 |
| zj | **连载归档**（非书） | 0.3.0 | 8 个文件 15.8KB，含 68 行 search-metadata fork；402 期线性内容零 prev/next |

---

## 2. 主题存量盘点：五个想法各自站在什么地基上

先纠正一个认知前提：五个想法里有两个半已经有地基，规划必须"续建"而非"新建"。

| 需求 | 主题现状 | 缺口 |
| --- | --- | --- |
| Release 卡片 | 无 | 全新 |
| sha256 资产表 | 无 | 全新 |
| 图/表/公式锚点与引用 | 无（imgproc/gallery 只管图片呈现） | 全新 |
| 数学公式渲染 | **半成品**：仅 ` ```math ` 围栏可触发（`render-codeblock-math.html` → `transform.ToMath` 服务端 KaTeX）；KaTeX 0.18.4 已 vendored；`hasMath` flag → 条件加载 KaTeX CSS+字体。**主题没有 `render-passthrough.html`**，`$$…$$` 无人接住（silo/pig/oink 站各自手写了这个 hook——是缺口的证据，不是存量） | 主题落地 passthrough hook + 起步配置文档；这是线上正确性缺陷（pg36g 44 个文件公式裸奔），应按 0.4 修复处理 |
| 上一页/下一页 | **已有雏形**：`_partials/pager.html`，仅 blog 使用，基于 `.PrevInSection`（Hugo 章节序，非侧栏树序），Bootstrap 按钮样式，i18n key `ui_pager_prev/next` 已在 32 locale | 树序化、卡片化、docs/book 启用、head rel 链接 |
| Landing 组件 | **已有系统**：`data/home/<lang>.yaml` → `home/section.html` 分发器 → 12 种 section（hero、metrics、capabilities、principles、cards、logo-wall、gallery、testimonials、contributors、faq、markdown、cta），支持类型别名、`key` 多实例、内联 data、`partial:` 自定义逃生舱、`enabled` 开关、`_landing.scss` ~1700 行样式含 reduced-motion 处理 | 仅限首页（`layouts/index.html`）；缺 pricing/timeline/compare/download section；缺 marquee 滚动模式 |
| 下载页模板 | 无（但 tabpane、enhanced code block 复制、Badge 等可复用件齐全） | 全新 |

另有两组存量与本轮相关：

- **卡片家族**：`card/cardpane`（Docsy 遗留）、`doc-card(s)`、`nav-card(s)`、
  `doc-carousel`、`steps`。内容页的卡片拼装已够用，本轮不动。
- **Docsy blocks 遗留**：`blocks/cover|feature|lead|link-down|section`。
  与 landing section 系统职责重叠，本轮标记 deprecated（保留兼容，不再投资）。

### 2.1 相邻在建工程：navbar/footer 集成

本文写作时，另一条工作线已完成 shell navbar/footer 的设计评审（要点：
`navbar_enabled` 参数默认 true、`footer_style: fat|slim|none`、
`data/footer/<lang>.yaml` 三级回退、移动端以 navbar 凝缩形态替代 subnav、
`--td-shell-nav-h` 几何 token）。**Track 5.4（Landing 泛化）依赖它落地**：
独立 landing 页需要 navbar + fat footer 的页面骨架。本文不重复该设计，
只声明依赖顺序。

---

## 3. 调研发现：站点侧证据

本章为五路实地调研的汇总，只保留驱动设计决策的证据。

### 3.1 文档站（sow / exp / oink.pgsty.com）

**下载页已被独立发明了两次，且形态同构。**
sow 自造 `download` type（`shell_types` 扩展 + 117 行自定义 layout），模板
100% 复用主题 landing 的 CSS 类（`oink-landing/oink-hero/oink-card` 等）——
等于站点在证明"下载页就是 landing section 的一种变体"；制品矩阵用模板内
`slice+dict` 硬编码，双语靠内联 `{{ if $zh }}`。exp 则用 258 行纯 Markdown
（nav-cards + 对比表 + code-group/steps）表达完全相同的事实：
OS×arch 归档矩阵、RPM/DEB 安装命令、容器、SHA256 校验、源码构建。
sow 还发明了 `data/releases/sow.yaml`（版本号 + `published` 开关），下载项
在未发布时渲染为禁用态"待发布"——**发布状态门控**是设计时没预料到的真实需求。

**顺序阅读需求确凿，全靠手写。** sow 的 tutorial 是 5 篇 weight 序列、
exp 的 start→download→install 有隐含顺序、oink 站 33 个文件手写
`## Next steps` 链接列表。没有任何 prev/next UI。

**release notes 均为 blog 子 section、每 tag 一页**（sow 4 篇、exp 35 tag
×2 语言），exp 用 permalinks 剥掉 URL 的 `/blog/` 前缀，并用
`manualLink + build.render: link` 的"幽灵页"把 release 挂进 docs 侧栏——
该机制主题已支持但从未写进契约文档。

**宽表格是最高频未满足需求**：三站含表格文件数 80/22/68；exp 使用
`{.full-width}` 达 43 处，而主题没有任何 CSS 实现它（43 次使用，零效果）。

**Section index 三站三种做法**：sow 手写 doc-cards 重述子页、exp 手写表格、
oink 站用主题 `section-index.html` 的朴素 `<h2>+<p>` 列表。自动化的
卡片式 section index（从子页 title/description/icon 生成）能消除这类重复。

**碎片共性**：两站 `layouts/robots.txt` 逐字节相同（主题不提供，生产站点
人人要写）；sow 为改一行文案（GitInfo.Subject → 仅 hash）复制了整个
`page-meta-lastmod.html`；sow 用 30 行 SCSS 覆盖 hero 媒体栅格
（列宽比例/媒体宽度/窄屏断点）——应参数化；exp 存在死 i18n 键
（前 pig 主题遗留）。

**主题缺陷（应修复而非视作定制）**：exp 手写 404 绕开"block-only 404 在
多语言多输出并发构建下可能继承 print base"的不确定性；exp 用 9 行 SCSS 绕开
"<768px 时 scroll-padding-top 被重置为 1.5rem 而移动 subnav 仍 sticky、
深链锚点被遮"的回归。

**负面证据（决定不投入什么）**：三个文档站都没有路线图/timeline、独立 FAQ 页、
贡献者页、logo 墙、插图编号、公式（passthrough 配好但零使用）；主题现成的
contributors/logo-wall/testimonials/gallery 四个 home section 三站全未启用。
落地组件的投入优先级应由 pgsty.com/pigsty.cc 的证据驱动，而非文档站。

### 3.2 下载与发布（silo / pig.pgsty.com）

两站是同一问题的两个极端解：silo 把下载页做成 **682 行绕开 baseof 的独立
HTML**（自带 `<!DOCTYPE>`，配 1718 行 `download.css` + 168 行 JS，连语法
高亮都是手写 `<span class="k">`，主题的 Chroma/code-group/复制按钮一个都
用不上）；pig 把发布注记做成 **51 版 ×2 语言的 markdown**，校验和是裸
```bash 代码块。

**结构性阻塞点（本轮最硬的证据）**：Hugo 不支持在 shortcode 参数里内嵌
shortcode。pig 升级 OINK 0.3 时，原本可插值的 ```text 资产列表改用
`{{< filetree >}}` 后，`{{< param version >}}` 无法传入 `name` 参数，
**被迫退化成写死的 `X.Y.Z` 占位符**（git c6fc6a0），且因 URL 同样无法
插值而放弃了下载链接。→ 新组件的版本/仓库信息**必须从 front matter 或
site params 解析，不得设计成字符串参数**。此条应写入契约。

**发布注记形态（release 卡片的直接依据）**：
- 两站 front matter 均无 `version`/tag URL 字段——版本号被困在
  `title: "pig v1.7.0"` 字符串里；pig 46 页页末手写
  `Release: https://github.com/pgsty/pig/releases/tag/v1.7.0`。
- **多产品发布区不是边缘情况**：silo 一个 `/blog/release/` 混着
  silo/mcli/console/pkg 四条版本线，靠文件名前缀和 tags 区分。
- `weight` 手工序列已经烂掉：pig 一处重复 + 三处间隙插值（135/156/158），
  silo 三页撞 `weight: 10`。→ release 列表必须按 version/date 派生排序。

**校验和现状（release-assets 的直接依据）**：
- pig：**400 行裸 hash**（200 EN + 200 ZH 逐字节重复，双语漂移无任何检查
  能发现）分布在 50 个文件；早期 10 个文件是 **MD5**，与 SHA-256 同样包在
  ```bash 围栏里，**算法切换在页面上完全不可见**。
- silo：发布页不贴校验和（散文式 `## Artifacts` bullet），下载页只放
  `checksums.txt` 链接。→ 组件必须支持"只给链接不给列表"的降级形态。

**下载渠道模型（download 模板的直接依据）**：
- silo 下载页：两产品 × tab 组（Docker 含 4 子 tab、K8s、Linux 包、
  二进制、Ansible、源码），资产按包格式分组（RPM/DEB/APK × x86_64/arm64）
  + 按平台分组（Linux/macOS/Windows × 2 arch），版本变量集中在模板头部
  4 个变量（引用 72 次、printf 27 个 URL），但**日期另外硬编码 5 次**
  （tag `RELEASE.2026-08-06T…` 本身含日期却未派生）。
- pig `install.md`：138 行干净 markdown，`{{< param version >}}` 全站
  14 处 + `{{< code-group >}}` 双 tab（YUM/APT）用得很好——**"渠道分两类"
  是真实文案约束**：GitHub Release（即时、精确版本）vs 包仓库/镜像
  （同步滞后，宜用 latest，pig 特意把镜像安装命令的版本参数去掉并注明
  滞后）。组件不能一律插当前版本号。
- sow 的 `published` 开关（§3.1）补上第三个状态：**版本已定、制品未发布**
  时渲染禁用态。
- 版本字面量在配置层无解可依：pig 的 "575" 在 hugo.yaml 两处 language
  description + params + metrics.yaml 共存 4 份——组件救不了 site
  description，配套一致性检查脚本是唯一出路。

**发布自动化为零**：两站 Makefile/bin/CI 均无任何 release 目标；silo 发一版
要动 7 类文件，pig 发 v1.7.0 实际动了 18 个文件（+276/−71）。

**其他复用证据**：silo/pig 各自手写 `_markup/render-passthrough.html`
（KaTeX→MathML）——连同 oink.pgsty.com 的页面级版本，**三个站点独立发明了
同一个 render hook，主题应直接内置**；`download.css` 在姊妹站间拷贝
（1718 vs 1658 行，pig 那份 99% 是死代码）；robots.txt/favicons 覆盖、
落地页页脚 partial、独立 HTML 落地页（silo 629 行 / pig 470 行）两站
重复——与 3.3 落地页证据合并处理。

### 3.3 落地页（pgsty.com / pigsty.cc）

**规模事实**：pgsty.com 全站仅 10 个 md（正文在 HTML 视图里一个字都不渲染），
却背着 5 个自带完整 `<html>` 骨架、绕开 baseof 的模板（首页 611 行、下云页
615 行、价格页 161 行、关于页 233 行）+ 3316 行手写 CSS + 338 行 JS。
pigsty.cc（Docsy 旧站，1490 md）首页 2147 行、价格页 711 行全部硬编码，
其中约 1600 行是重复的 `<a>` 标签：770 个扩展标签、42 张评论卡、
66 个截图 slide 与 24 个 logo（**为做无缝滚动手工复制两遍**，改一处要改
两处）。两站合计 4000+ 行落地模板、~3800 行 CSS、650 行几乎逐字相同但
已各自漂移的 `landing-v3.js`。而主题现成的 12 种 section **只被消费了
1 次**（pgsty.com 挂了一个 FAQ）。

**站点绕开主题的根因不是"缺概念"，而是三个缺口**：

1. **缺外壳**：主题只有文档壳，没有 landing 版 header/footer。两站各自
   重造顶栏（两级/多列下拉、⌘K 按钮、主题切换、GitHub 星数、移动端汉堡）
   与五列页脚（含 ICP 备案、跨仓库语言切换——pigsty.cc↔pigsty.io 是两个
   repo，不是 Hugo `.Translations`）。这是 pigsty.cc 迁移的头号硬阻塞。
2. **缺运行时**：主题落地页零 JS。两站各带一份同源的
   `data-reveal`（IntersectionObserver 入场）、`data-count`（数字滚动）、
   `data-copy`、明暗双图切换（`data-theme-src-light/dark`）、移动端菜单
   （pgsty.com 已通过 `OinkSurfaceCoordinator.register('mobile-menu',…)`
   与主题面板互斥——此契约必须保留）。
3. **缺形态**：既有 section 差最后一步——`capabilities` 已是 zigzag 特性行
   且支持 `visual.type: code/shell/components`，但**缺最常用的
   `image`**（两站共 10 个 zigzag 行里多数配图）；`metrics` 缺计数动画与
   `source` 溯源角标；`faq` 只有折叠态、缺价格页要的扁平网格；
   `logo-wall/testimonials/gallery` 只有静态网格、缺跑马灯变体。

**两站都在造、主题完全缺失的组件**（按交叉验证强度排序）：

| 组件 | 证据 |
| --- | --- |
| pricing（分档卡+分组对比表） | 两站各一份，schema 高度一致（`featured` 推荐档、`Y/N` 勾叉、`price_row`、分组行）；**同一份定价事实两份副本已经漂移**（PG 16–18 vs 17/18） |
| marquee 跑马灯 | pigsty.cc 四处使用（扩展标签/logo/评论/截图，多行反向滚动、懒加载），是首页视觉主体；"复制一遍做无缝循环"必须由模板 `range` 两遍代劳 |
| command-box（安装命令+复制） | 两站 hero 都有 |
| steps 编号流程卡 | 下云页四步、pigsty.cc 快速开始三步 |
| timeline | pgsty.com about 页 `<ol>` 时间轴 |
| code-plate 装饰代码面板 | 两站 5+ 处**手写 `<span class="k/s/v">` 上色**，又丑又易错 |
| case-study/fieldreport（数字+引语+出处案例块） | 两站都出现同名 class |
| bar-chart（纯 CSS 归一化条形图） | 下云页 ×3，模板算宽度无图表库；顺带修 int/float `gt` 退化成字符串比较的坑 |

**数据模式冲突需要裁决**：pgsty.com 用"单文件 + `xxx`/`xxxZh` 字段后缀"
（`brand.yml` 立了规矩：模板硬编码数字视为 bug；`portal/pricing.yaml`
219 行是范本），主题 home 系统用"每语言一个文件"。事实型数据（价格、数字）
用后缀式可防双语漂移，叙事型数据用分语言文件更顺——新 section 的字段解析
应同时支持两者（`title_zh` → `title` 回退链）。

**不值得抽象**（品牌/业务专属）：六边形字母板、主板热点标注
（pin 坐标手调，用途窄，暂缓）、八旋钮 TCO 计算器、宣言块、实体卡。

**pigsty.cc 迁移阻塞清单**（按序）：landing 外壳 → landing 运行时 →
marquee → pricing → `capabilities.visual.type: image` → 数据下沉
（站点侧工作量最大：770 个 ext-pill 应从 `content/ext/` 的 658 页 range
出来而非再抄 YAML）→ `shell_types` cascade 改造 → i18n 键位核对。

### 3.4 书籍站 I（aiempire / tpme / pg36g）

三本书对"书籍能力"的需求几乎不重叠——**书籍不是一种场景，是一族场景**：
aiempire 纯叙事（0 图 0 表 0 公式）、tpme 引进版图文书（62 张编号插图）、
pg36g 技术手册（281 页标记 `math: true`、44 个文件有公式、22 个文件用
Mermaid 代替插图、章/节/目三级结构 301 页）。

**三站 layouts/ 覆盖接近于零**——唯一的"覆盖"是 tpme 与 pg36g 各有一份
**逐字节相同、从未被调用**的 `figure.html`（还躺着 Hextra 键名的 i18n
死文件、`.hextra-sidebar` 死 CSS）。结论：shell 够用；**书籍特性没人自建
成功，是尝试过然后放弃了**。主题补位后这些化石自然消失。

**P0 正确性缺陷：公式在线上是坏的。** 主题数学入口只有
` ```math ` 围栏（`render-codeblock-math.html` → `transform.ToMath`），
**没有全局 `render-passthrough.html`**；`math: true` 是 Hextra 约定主题不认。
pg36g 未配 passthrough 扩展 → 44 个文件的 `$$…$$` 原样渲染成字面美元符
（构建产物实证）；aiempire/tpme 配了 passthrough delimiters 但没有 hook
接住，只是恰好零公式没暴露。silo/pig/oink 站各自手写了同一个
render-passthrough hook（§3.2）。**六个站点、三种配置状态、零个正确**——
这个 hook 必须由主题内置（passthrough 扩展本身受"Hugo 忽略主题 markup
配置"约束，仍需站点开启，主题负责 hook + 起步配置文档）。

**prev/next：三站全无**，tpme i18n 死文件里的 `previous/next` 键是"想要
顺序阅读但没做成"的化石。且 `.PrevInSection` 方案对 pg36g 的章/节两层
结构不成立（章末走不到下一章首页）——**必须按侧栏树序展平**，并尊重
aiempire 在用的 `data/docs_nav.json` 显式书序。

**图表编号（tpme 实况倒推的硬约束）**：编号"图 2-1"以硬文本同时活在
caption、每处引用、图片文件名（`tpme_0201.png`）三处，人肉同步；caption
是 `###### … {#anchor}` 伪标题（h6 语义污染，未进 ToC 纯靠 endLevel=4
侥幸）；锚点是 O'Reilly 语义 ID（`office_2003`），与显示编号脱钩——
**组件必须允许手工指定 ID、编号按章重置、ID 与编号解耦**。另外中文正文
**1062 处链接指向 `/en/…`**（章节引用为主、图引用其次）：交叉引用组件
默认按当前语言解析，附带修掉这类系统性泄漏。**编号表格三站零实践**，
tbl 降优先级（fig/eq 之后）。

**多级编号锚点是同一问题的更大实例**：pg36g 772 个目锚点靠手写
`## 7.6.1 xxx {#item-7-6-1}` 维护（编号在标题文本与 ID 里两套人肉同步）。

**全书目录与整书视图**：三站各手写 `toc.md`（40 / 32 / **1181** 行）；
pg36g 在 Hugo 外面建了完整书籍模型（4552 行 `data/chapters.yaml` +
1036 行 Ruby scaffolder + 392 行 checker），**只因主题没有模板消费它**。
print 输出割裂：pg36g 因章是 section 白捡 40 个整章单页，aiempire/tpme
因章是顶层 page 一个都没有；**整书单页三站皆无**，aiempire 为此站外重写
583 行 Python + WeasyPrint 的 PDF 管线。

**已被验证够用的**：封面页 = `data/home/*.yaml`（三站都满意，不需要新
组件）；命令面板自定义 commands 三站都在深度使用（"从序言开始阅读"）；
`book_*` front matter 命名空间（`book_kind/number/part/status` 等
1400+ 处）是经 301 页实战检验的现成参考，`book_status: draft`（290 页）
尚无任何 UI 呈现。

### 3.5 书籍站 II（ddia / pg-internal）与连载归档（zj）

**三套互不兼容的插图约定，没有一套是主题给的**：

| | 图注位置 | 锚点 | 交叉引用 |
| --- | --- | --- | --- |
| DDIA 二版 | `<figcaption>`（自建 shortcode） | 手写语义 id（`fig_obama_relational`） | 真链接 301 条，**0 断链** |
| DDIA 一版 | 图下方粗体段落 | 无 | **206 条链接指向 PNG 文件本身** |
| pg-internal | 图上方粗体段落（4 种格式变体） | 无 | **90 处纯文本，0 链接** |

（tpme 是第四套：h6 伪标题 + O'Reilly 语义锚点，§3.4。）

**DDIA（131 处 figure 调用、350 处编号提及、1035 条脚注）**：手工编号
体系"能用但完全冻结"——编号在 caption 与每处引用文字里独立手写，插一张
新图 = 人肉重排整章图号 + 全书引用；组件的价值不是省代码而是**让插图
从不可变变成可编辑**。迁移硬约束：主题 fig 必须兼容其现有参数面
（`src/id/caption/title/class/link/alt/width/height`），xref 必须兼容
既有语义 id 与 `/chN#fig_xxx` 绝对引用形式，否则 131 处迁移成本高到不做。
其编号表格用法暴露一个语义 bug：自闭合 figure + 兄弟节点表格，DOM 上
编号与内容脱节——`{{< tbl >}}` 包裹式设计正是解法。另外：passthrough
配置开着却无 hook 接住（写 `$$` 即静默裸奔，与 zj 同病）；EPUB 导出链
会丢弃全部锚点与无 src 的编号标题，且 pandoc `--webtex` 依赖外部服务
（反 local-first）；一版的 104 张裸图与 206 条伪引用需要一份迁移脚本
配方。**术语表与 289KB 主题索引的每一条都手写 `/chN#anchor` 回指**——
与图表引用同源，xref 若只认 fig/tbl/eq 就覆盖不到 → xref 必须泛化为
"语言正确的锚点引用"，kind 只决定是否加"图 N"前缀。

**pg-internal（366 处图表提及、90 处死引用、51 个公式块）**：与 DDIA
相反，是**从零补能力**——图注 4 种格式变体、3 张漏注、2 张空 alt
（站点自写的检查脚本正则有误而漏检）；交叉引用 100% 死文本。严格
`errorf` 校验在这里价值最大。**数学是六站唯一端到端工作的**：站点自建
passthrough hook（**第四个重复发明**）→ 主题 `transform.ToMath` 服务端
KaTeX，KaTeX CSS 仅在真有公式的 6 页加载——完全符合条件装配模型；其
8 行 `.katex-display` 溢出修补 CSS 应上移主题。**真实瓶颈不在 shell**：
每章一个 100KB 单文件，侧栏无论多好都表达不出章内小节（全书 7361 行
只有 1 个手写锚点，56 条跨章链接都想指向小节）——需要的是 book 类型下
基于 `.Fragments` 的**章内标题侧栏下钻**与稳定锚点策略。en 版 84 页因
`hugo.en.yaml` 未进 Makefile/CI 从未构建（站点侧运维问题，双语书设计
需知悉）。

**zj（402 期访谈归档，非书）**：图表/数学/书籍装配全部零需求，暴露的是
第五类场景"**连载归档**"——严格线性、weight=期号，**prev/next 是它最缺
的一个控件**（当前从第 N 期到 N+1 期只能滚 402 项侧栏）。另有三个独立
发现：为给期号搜索加 15 行逻辑而 fork 了 68 行 `search/metadata.html`
（主题应提供 search 关键词扩展钩子）；402 项扁平侧栏占每页体积 65%
（大型扁平 section 需要按年份分组的侧栏形态）；`offlineSearchIndex:
content` 在 760 万 CJK 字符上产出 25MB 索引（需要运维指引）。

### 3.6 共性矩阵

调研汇总——行为候选组件，列为场景簇，标注需求强度：

| 组件 | 文档站 | 下载/发布 | 落地页 | 书籍 | 归档 |
| --- | --- | --- | --- | --- | --- |
| Pager 顺序阅读 | **强**（33 处手写 Next） | 强 | — | **全缺**（五本） | **最痛**（402 期） |
| Release 原语 | 强（release section ×2 站） | **核心**（51+14 版） | — | — | — |
| 资产校验和表 | 有（SHA256SUMS 链接） | **核心**（400 行裸 hash） | — | — | — |
| Download 模板 | **已被发明两次** | **核心**（682 行独立 HTML） | 入口段 | — | — |
| Landing 外壳+运行时 | — | silo 绕壳自建 | **核心**（4000+ 行代偿） | 封面已够用 | 落地已够用 |
| Marquee 跑马灯 | — | — | **核心**（cc 四处，视觉主体） | — | — |
| Pricing | — | — | **核心**（两站已漂移） | — | — |
| fig/tbl/eq + xref | — | — | — | **核心**（四套私有约定并存） | 零 |
| 数学 passthrough | 配好未用 ×2 | hook 自建 ×2 | — | **P0**（pg36g 损坏；pg-internal 自建） | 死配置 |
| book-toc / 整书视图 | — | — | — | **核心**（1181 行 toc + 583 行 PDF 代偿） | 归档表变体 |
| 杂项（宽表/robots/section-index…） | **强** | 强 | — | 部分 | 部分 |

矩阵之外的负面证据同样重要：文档站不需要 landing 花活（contributors/
logo-wall/testimonials 三个文档站零启用）；书籍站不需要新封面组件
（data/home 三站满意）；归档站不需要书籍组件。**按场景簇交付，不做
全家桶。**

---

## 4. 设计原则

继承既有章程（红线，逐条适用于本轮每个组件）：

- **C1 local-first**：不依赖 CDN、构建期下载、未配置的公共服务。宁可 `errorf`
  也不静默联网。
- **C2 严格失败**：非法参数 `errorf`，带 `.Position`/行号。
- **C3 输出矩阵**：每个组件在 html / print / markdown(llms) / rss 四种输出下
  都有明确定义的降级行为。
- **C4 i18n ×32**：任何用户可见字符串 = 32 个 locale 文件同步加 key。
- **C5 flag 装配**：需要 JS 的组件设自有 Page Store flag，进 `$bundleKey`；
  shortcode 只写 flag 不读别家 flag。
- **C6 a11y 四件套**：forced-colors、prefers-reduced-motion、print、RTL
  （逻辑属性）。
- **C7 保守默认**：会改变站点行为/政策的功能 opt-in；纯导航与内容呈现可以
  默认启用但必须可关。

本轮新增三条：

- **P1 数据边界**：主题是**本地数据的渲染器**。GitHub Release URL → 链接推导
  属于纯字符串运算（合规）；调 GitHub API 拉 release 资产/贡献者/star 数属于
  站点侧脚本或 CI 的职责，主题提供 data schema 与文档化的采集配方，不提供
  采集本身。
- **P2 收敛不并列**：新能力必须落在既有系统的延长线上——landing 新 section
  进既有注册表；pager 升级既有 partial；fig/tbl/eq 进 content-primitives
  契约。禁止出现第二套 landing 体系、第二套卡片体系。
- **P3 Markdown 可拼装**：自有站点的首页/价格页/下载页应当由
  markdown + front matter + data 文件拼装而成；手写 HTML 是逃生舱
  （`partial:` 自定义 section），不是常规路径。
- **P4 事实单源，参数不嵌套**：Hugo 不支持 shortcode 参数内嵌 shortcode
  （pig 的 filetree 版本号回退事故，§3.2）。因此版本号、仓库名、日期等
  "事实"一律从 front matter / site params / data 文件解析，**组件不得把
  它们设计成字符串参数**；同一事实只允许一个权威来源，其余位置全部派生。

---

## 5. Track 设计

### 5.1 顺序阅读 Pager（想法 3 · 里程碑 0.4）

**现状**：`_partials/pager.html` 仅被 `blog/_td-content.html` 调用，
基于 `.PrevInSection`/`.NextInSection`，禁用态渲染灰按钮。三个书籍站、
三个文档站全部为零，33+ 处手写 "Next steps" 是代偿。

**设计**：

1. **阅读序 = 侧栏树序，别无第二真相。** 新增
   `_partials/shell/nav-flatten.html`：输入 section 根，输出与
   `shell/sidebar-tree.html` / `docs-sidebar-tree.html` **完全一致**的
   有序页面数组（含 section index 页；尊重 `data/docs_nav.json` 显式书序；
   跳过 `manualLink`/`build.render: link` 幽灵页、`sidebar_divider` 分隔行
   与隐藏页）。`partialCached` 按 (root, lang) 缓存。这同时解决 pg36g
   跨章翻页（`ch07/07.md` → `ch08/_index.md`）——`.PrevInSection` 做不到。
2. **卡片式 UI**：左 prev 右 next 两张卡（RTL 用逻辑属性自动镜像），
   卡内为方向词（复用现有 `ui_pager_prev/next` key）+ 页面标题 +
   可选父 section 名。**单边缺失时只渲染存在的一侧**，废除禁用灰按钮。
   不绑定全局左右方向键（与浏览器/输入法冲突）。
3. **位置与 head**：`_td-content.html` 中 feedback 之后、comments 之前；
   同时在 head 输出 `<link rel="prev/next">`。
4. **配置**：
   ```yaml
   params:
     ui:
       pager:
         types: [docs, book, blog]   # 默认；blog 保持时间序，docs/book 走树序
```
   页面级 `pager: false` 单关。默认开启的理由：pager 是导航而非站点政策
   （C7 的"保守默认"针对的是行为/外联类特性）；0.4 release note 明示，
   不愿意的站点一行关闭。
5. **排序来源按类型分流**：docs/book → nav-flatten 树序；blog → 保留现有
   时间序（仅升级样式与单边渲染）。
6. **输出矩阵**：仅 html 输出渲染；print/markdown/rss 全部剥离。

**验收**：oink.pgsty.com（docs 树序）、pg36g（跨章）、aiempire
（docs_nav.json 显式序）、zj（402 期线性归档——本组件最痛的消费者）、
ddia/tpme/pg-internal（扁平书，树序退化为 weight 序，自然正确）。
侧栏顺序与 pager 顺序的一致性由检查脚本断言。

### 5.2 GitHub Release 与资产（想法 1 · 里程碑 0.4）

一切纯字符串推导，零网络（P1）。数据源自 front matter（P4）。

**5.2.1 `release` front matter 与发布卡片**

```yaml
# content/blog/release/pig-1.7.0.md
release:
  product: pig          # 多产品发布区必填（silo: silo/mcli/console/pkg）
  version: 1.7.0
  repo: pgsty/pig
  tag: v1.7.0           # 缺省 v{version}
  date: 2026-08-12      # 缺省取页面 date
  prev: 1.6.2           # 可选：生成 compare 链接
  checksums: checksums.txt   # 可选：GitHub 资产里的校验和文件名
# 或速记形态：release: https://github.com/pgsty/pig/releases/tag/v1.7.0
```

- URL 速记解析出 repo/tag；无法解析 → `errorf`（v1 仅认 GitHub 域名，
  forge 参数化留作开放问题）。
- `{{< release-card >}}`（或 release 布局自动渲染）：tag 名、日期、按钮组
  （GitHub Release 页 / 源码 tar.gz·zip / checksums / Compare / 仓库）。
  全部由 repo+tag 派生（`releases/download/<tag>/…`、
  `archive/refs/tags/<tag>.tar.gz`、`compare/v<prev>...<tag>`）。
  silo 的"只给链接不给列表"降级形态由此卡片承担。
- **release 列表布局**：section index 提供 `layout: releases`——按
  `release.date` + semver 排序、按 `product` 分组过滤。**`weight` 退出
  发布场景**（两站的 weight 序列均已腐坏：撞号 + 间隙插值）。
- 站点首页 metrics 的 releases 计数可从带 `release.product` 的页面数派生
  （消灭 silo 手数 `releases: 9`）。

**5.2.2 `{{< release-assets >}}` 资产表**

包住 `sha256sum` 原始输出（pig 现有 50 个文件、400 行裸 hash 的直接替代）：

```markdown
{{< release-assets >}}
e3a339fefdd2203825d15438b52f18e729547eb88dae014212a46006a9bd47d1  pig-1.7.0-1.aarch64.rpm
34ce29d75ef9f669f3bf832cc812ae082abda7320ee2b2336ea61e701b9b67f8  pig-1.7.0-1.x86_64.rpm
{{< /release-assets >}}
```

- **行文法**：`<hex>␠␠<name>` 与 `<hex>␠*<name>`（binary 标志）；空行与
  `#` 注释跳过；其余任何行 → `errorf` 带行号（C2）。
- **算法自动识别并强制标注**：按 hex 长度（32=MD5 / 40=SHA-1 / 64=SHA-256
  / 128=SHA-512）打徽章，`algo=` 可显式覆盖、不符 `errorf`。直接消灭
  pig 早期 10 个文件 MD5 与 SHA-256 在同样围栏里不可分辨的问题。
- **下载链接**：默认从页面 `release` front matter 的 repo+tag 派生
  `releases/download/<tag>/<name>`；无 release 上下文时接受 `base=` 参数
  （纯前缀，非版本事实，不违反 P4）。文件名转义 + path segment URL 编码。
- **呈现**：文件类型图标（.rpm/.deb/.apk/.tar.gz/.zip/.exe/.msi/.dmg）、
  OS/arch 徽章（amd64|x86_64、arm64|aarch64、loongarch64、riscv64 →
  复用 Badge 视觉）、校验和截断显示 + 单行复制 + 整块复制、可选
  `group=auto` 按包格式/平台分组。
- **双语去重**：`src=` 可指向页面 bundle 资源或全局 asset 路径
  （`resources.Get`），EN/ZH 两页引用同一份文本，消灭 pig 200+200 行
  逐字节重复与漂移风险；inner 与 `src` 互斥，双给 `errorf`。
- **运行时**：复制按钮 → 新 flag `hasAssetList`，独立 runtime 文件，
  进 `$bundleKey`（C5）。
- **输出矩阵**：markdown/llms → 管道表格含完整 hash；print → 静态表格
  无按钮；rss → 同 markdown。契约条目进 `content-primitives.md`。

### 5.3 下载页模板（想法 4 · 数据层 0.4，落地形态 0.5）

**数据先行**：`data/download/<key>.yaml`，一份数据双消费
（文档页 shortcode + landing section）。

```yaml
# data/download/pig.yaml —— 事实型数据用字段后缀双语（§3.3 裁决）
version: 1.7.0            # 省略则回退 site.Params.version；两者皆无 → errorf
repo: pgsty/pig
published: true           # sow 语义：false → 渠道渲染禁用态"待发布"
channels:
  - id: script
    kind: rolling         # rolling：仓库/镜像/latest —— 禁止插值精确版本
    title: Script
    title_zh: 一键安装
    icon: fa-solid fa-bolt
    note_zh: 镜像同步可能滞后于 GitHub Release。
    steps:
      - code: curl -fsSL https://repo.pigsty.io/pig | bash
        lang: bash
  - id: apt
    kind: rolling
    title: Debian / Ubuntu
    steps: [...]
  - id: assets
    kind: pinned          # pinned：GitHub 资产 —— 精确版本，URL 由 repo+tag 派生
    title: Release Assets
    checksums: |          # 或 checksums_src: 引用资源文件
      e3a339…  pig-1.7.0-1.aarch64.rpm
```

- **渠道两类是硬约束**（pig 实证）：`rolling`（包仓库/镜像/docker latest，
  不插版本，可带滞后提示）与 `pinned`（GitHub 资产，`${version}` 白名单
  插值，未知变量 `errorf`）。
- `steps[].code` 走 enhanced code block 管线（Chroma 高亮 + 复制按钮，
  设 `hasCodeRuntime`），替掉 silo 手写 `<span class="k">` 上色。
- 资产表复用 5.2.2 渲染器。
- **消费形态一**（0.4）：`{{< download "pig" >}}` 在普通文档页展开为
  纵向分段 + 顶部渠道锚点 chip（无 JS）；pig 的 `install.md` 即目标用户。
- **消费形态二**（0.5）：landing section `download`（同一数据，tab 化
  呈现），供 silo 式独立下载页/首页使用——依赖 5.4 的 landing 外壳。
- 验收：silo 下载页 682 行模板 + 1718 行 CSS + 168 行 JS 归零重建；
  pig `install.md` 的 filetree 占位符恢复为带真实链接的资产表。

---

### 5.4 Landing 泛化与组件补全（想法 5 · 里程碑 0.5）

调研结论（§3.3）：差距不在缺概念而在**缺外壳、缺运行时、缺形态**。
本 track 四个子项，优先级即此顺序。

**5.4.1 landing 外壳（迁移硬阻塞，依赖 navbar/footer 在建工程）**

- 任意页面可声明 `layout: landing`：navbar + fat footer、无侧栏、
  全宽画布；`data` 源由 front matter 指定：
  ```yaml
  # content/price.md
  layout: landing
  landing: pricing        # → data/landing/pricing/<lang>.yaml（或单文件）
  ```
  front matter 内联 `sections:` 亦可（分发器已支持内联 data）。
  首页维持 `data/home/` 兼容路径不变。
- landing header 在 navbar 基础上补齐两站实证需求：**多列 mega menu**
  （仍是 PRD 4 的"仅一层子级可交互"契约，多列只是显示形态，不引入第三级）、
  GitHub 星数徽标（数据来自 params/data，站点 CI 刷新——P1，绝不客户端拉取）、
  跨仓库语言切换（pigsty.cc↔pigsty.io 型，footer/nav 外链配置）、
  ICP 备案行（footer data 字段）。
- 命令面板/搜索在 landing 壳可用（pgsty.com 已实证复用 `shell/search-dialog`
  + action manifest 的组合，收编为 landing 壳内置选项）。

**5.4.2 landing 运行时（`hasLanding` flag）**

收编两站同源漂移的 `landing-v3.js`（338/313 行）为主题条件运行时：
`data-reveal`（IntersectionObserver 入场）、`data-count`（数字滚动）、
`data-copy`、明暗双图切换（`data-theme-src-light/dark`）、移动端菜单
（**必须经 `OinkSurfaceCoordinator.register` 与既有面板互斥**——保留
pgsty.com 已建立的契约）。全部 data-attribute 驱动、
`prefers-reduced-motion` 降级、进 `$bundleKey`、tests/js 补覆盖。

**5.4.3 既有 section 补形态（回收率最高的改动）**

| section | 补什么 | 证据 |
| --- | --- | --- |
| capabilities | `visual.type: image`（及 `card`）；媒体栅格参数化（列比/宽度/断点，收编 sow 的 30 行 SCSS 覆盖） | 两站 10 个 zigzag 行多数配图 |
| metrics | `animate: true` 计数动画；`source` 溯源角标；`compact-number`（2189→2.2k）helper 收编 | 两站 stats-grid + silo/pgsty 各一份 compact-number |
| faq | `style: flat \| accordion` | 价格页扁平网格形态 |
| logo-wall / testimonials / gallery | `layout: grid \| marquee`（方向/速度/多行/懒加载） | pigsty.cc 四处跑马灯是首页视觉主体 |
| cta | 多按钮 + 描述覆盖 | contact-band 参数 |

**marquee 机制**：模板把条目 `range` 两遍（副本 `aria-hidden`），CSS
keyframes 无缝滚动、hover/focus 暂停、`prefers-reduced-motion` → 静态
网格、forced-colors 安全。**纯 CSS，无 JS，不进 bundleKey**。直接消灭
pigsty.cc "33 张截图手工复制两遍"的维护地狱。

**5.4.4 新 section（按交叉验证强度排序）**

1. `pricing`：分档卡（`featured` 推荐徽标）+ 分组对比表（`Y`/`N` 勾叉
   + `price_row` + 组行），schema 以 pgsty.com `portal/pricing.yaml`
   （219 行实战范本）为基准。验收：两站共用一份定价事实，消灭已发生的
   双站漂移（PG 16–18 vs 17/18）。
2. `command-box`：安装命令 + 复制（hero 伴生条目）。
3. `steps`：编号流程卡（landing 形态；内容页已有 `{{% steps %}}`，
   视觉对齐但独立实现）。
4. `timeline`：`<ol>` 时间轴（年份标记 + 正文 + 可选图标/链接）。
5. `code-plate`：装饰代码面板，吃 `lines:` 数组或 fenced 文本走 Chroma——
   终结两站 5+ 处手写 `<span class="k/s/v">` 上色。
6. `case-study`（fieldreport）：数字组 + 大引语 + 出处。
7. `download`：5.3 数据的 landing 形态。
8. `bar-chart`：归一化水平条形图（吃 `{label, value, group}`，模板算
   宽度，无图表库；顺带修 int/float `gt` 字符串比较坑）。
9. `image-hotspots`：**暂缓**（用途窄、坐标手调，等第二个消费者）。

**5.4.5 双语字段解析**

新 section 的字段解析统一走 helper：`<key>_<lang>` → `<key>_<语言主标签>`
→ `<key>`（如 `title_zh_cn` → `title_zh` → `title`）。事实型数据
（pricing/brand 数字）推荐单文件 + 后缀，杜绝双语漂移；叙事型数据沿用
分语言文件。pgsty.com 现有 camelCase 后缀（`titleZh`）做一次机械迁移。

**5.4.6 Docsy blocks 处置**

`blocks/cover|feature|lead|link-down|section` 标记 deprecated：保留兼容
（Docsy heritage 原则）、文档指向 landing sections、不再投资。

### 5.5 Book 能力包（想法 2 · 里程碑 0.6；数学修复提前至 0.4）

书籍不是一种场景而是一族（§3.4）：纯叙事本（aiempire）只要 pager 与
排版；图文书（tpme、ddia）要图表编号与交叉引用；技术手册（pg36g、
pg-internal）要公式、多级编号与书籍目录。能力按需拾取，不做大一统开关。

**5.5.1 数学渲染补洞（0.4，正确性修复）**

- 主题落地 `layouts/_markup/render-passthrough.html`（转发既有
  `scripts/math.html`，`transform.ToMath` 服务端 KaTeX，零 JS）。
  silo/pig/oink 站/pg-internal 的**四份重复站点实现**是现成参考，
  落地后全部删除。pg-internal 已实证该链路端到端工作且完美契合条件
  装配模型（KaTeX CSS 只在真有公式的页面加载）。
- passthrough 扩展受"Hugo 忽略主题 markup 配置"约束，仍需站点开启：
  提供起步配置片段 + 书籍指南；`math: true`（Hextra 遗俗，pg36g 281 页）
  不赋语义，文档明示。**特别警示"配置开着、hook 缺位"的静默陷阱**
  （ddia/zj 现状：写 `$$` 即裸奔，比 errorf 更糟）。
- pg-internal 的 8 行 `.katex-display` 溢出修补 CSS 一并上移主题
  （修的是主题元素在主题布局里的溢出，不该由站点承担）。
- `{{< eq >}}`（见 5.5.2）兼作未启用 passthrough 站点的逃生舱：inner
  直接过 `transform.ToMath`。
- 验收：pg36g 44 个文件的公式**内容零改动**恢复渲染（站点仅加一段
  markup 配置）；四个站点删除自建 hook。

**5.5.2 图/表/公式编号锚点与交叉引用（内容原语）**

来自 tpme/ddia 实况的硬约束：编号手工指定且按章语义（"图 2-1"）、锚点
ID 可手工指定（O'Reilly/AsciiDoc 语义 ID 是既有资产）、**ID 与显示编号
解耦**、引用先于目标出现（shortcode 渲染顺序决定了**引用渲染不得依赖
同页注册表**）。**DDIA 迁移兼容面**：fig 参数须覆盖其自建 shortcode 的
全集（`src/id/caption/title/class/link/alt/width/height`），既有
`/chN#fig_xxx` 绝对链接必须继续可达——131 处调用才能机械迁移。
（自动编号是真实诉求但另有代价，见开放问题 12：v1 手动编号 + 一致性
检查，把"插图不可编辑"的问题先转化为"改错必被检查抓住"。）

锚点族（collector 同款风格，inner 经 RenderString）：

```markdown
{{< fig num="2-1" id="office_2003" caption="2003 版 Word 的凌乱截图" >}}
![](/fig/tpme_0201.png)
{{< /fig >}}

{{< tbl num="9-1" caption="各隔离级别允许的异象" >}}
| 异象 | RC | RR | SER |
|------|----|----|-----|
{{< /tbl >}}

{{< eq num="5.3" >}}X \approx \frac{C}{R+Z}{{< /eq >}}
```

- 渲染为语义 HTML：`<figure id="…"><figcaption>
  <span class="td-fig-label">图 2-1</span> caption</figcaption></figure>`；
  label 前缀走 i18n（图/表/公式 · Figure/Table/Equation）。消灭 tpme 的
  `###### … {#anchor}` h6 伪标题污染。
- **显式 `id` 原样使用、不加前缀**（DDIA 301 条既有 `#fig_xxx` 链接与
  tpme 的 O'Reilly 锚点必须原样可达）；缺省时派生 `fig-<num>`。
  `num` 必填、纯文本 `[0-9A-Za-z.-]+`；同页 id 重复 → `errorf`
  （Store 注册表）。`eq` 编号按书排惯例右侧呈现。
- 引用：`{{< xref fig="2-1" >}}` → `<a href="#fig-2-1">图 2-1</a>`；
  `anchor="office_2003"` 覆盖目标锚点；`page="ch2"` 跨页走 relref——
  **天然按当前语言解析**，顺带修掉 tpme 中文正文 1062 处 `/en/` 泄漏
  这一类系统性缺陷；inner 可覆盖显示文本。渲染不读注册表（次序无关），
  存在性校验交给配套检查脚本。
- **xref 泛化为"语言正确的锚点引用"**：kind（fig/tbl/eq）只决定是否
  加"图 N"标签前缀；无 kind 形态
  `{{< xref page="ch6" anchor="sec_replication_sync_async" >}}文本{{< /xref >}}`
  覆盖章节小节引用、术语表与索引的回指（ddia 的 glossary + 289KB
  indexes 每条都在手写这类链接；pg-internal 56 条跨章链接只能落到章首
  ——同一问题族，一个机制解决）。
- **配套检查**：`check-book.py` 校验 xref 编号与目标 fig 编号一致、
  目标锚点存在、id 唯一——把 DDIA"插一张图人肉重排全书"的风险转化为
  构建期报错。
- **迁移配方**（站点侧文档，随 0.6 发布）：ddia v1 的 104 张裸图 +
  206 条"链接指向 PNG"伪引用、pg-internal 的 90 处死文本引用与 4 种
  图注变体、tpme 的 h6 伪标题——三份一次性改写脚本的设计位置。
- 注册表用途：章节图表目录 partial + 书级 `{{< book-figures >}}`
  （封面页遍历子页触发 `.Content` 后聚合 Store——render.html 先例）。
- 输出矩阵：print 保留编号与锚点；markdown 输出退化为
  `**图 2-1.** caption` + 原始内容；rss 同 markdown。
- `tbl` 与 `fig`/`eq` 同批实现（机制同一），但文档标注"实践证据弱"
  （三站零编号表格），不做重点宣传。

**5.5.3 `book` 类型与书籍装配**

- `book` 加入 `shell_types` 可选值（starter cascade 示例），本质是 docs
  壳 + 书籍默认值：pager 默认开、章节树侧栏、breadcrumbs。封面页**不需要
  新组件**——三站已用 `data/home/*.yaml` 且满意（§3.4）。
- **front matter 命名空间采认 pg36g 实战方案**：`book_kind`（chapter/
  section/appendix/…）、`book_number`、`book_part`、`book_status`。
  主题消费其中两个：`book_number` 参与侧栏/目录编号显示，
  `book_status: draft` → 侧栏标记 + 页头横幅（opt-in），目录可过滤。
- `{{< book-toc depth=1..3 >}}`：按 nav-flatten 树序（5.1 复用）渲染
  章→节多级目录，`depth=3` 时用 `.Fragments` 下钻页内标题（覆盖 pg36g
  772 个"目"级锚点）。验收：pg36g 删除 1181 行手写 toc.md，
  4552 行 `chapters.yaml` 中间模型与 Ruby 校验器大幅退役。
- **整书/整章单页**：print 聚合从"仅 section"扩展到 book 根
  （nav-flatten 序遍历 RegularPagesRecursive），消除"pg36g 白捡 40 个
  整章单页、aiempire/tpme 零个"的结构性不一致；书根 `_print` 即整书
  单页。aiempire 的 WeasyPrint 管线可砍掉 Markdown 解析与内链重写一半，
  ddia 的 EPUB 预处理脚本可退役其锚点/编号丢失的正则（markdown 输出
  自带编号），PDF/EPUB 排版仍归站点（P1：主题止步于 print HTML；
  ddia 现用的 pandoc `--webtex` 依赖外部服务，属站点侧应弃项）。
- **章内标题侧栏下钻**（`sidebar_headings` opt-in）：pg-internal 的
  真实瓶颈——每章一个 100KB 单文件，侧栏表达不出章内小节。book 类型下
  基于 `.Fragments` 把当前页 h2（可配深度）挂入侧栏树。配套：稳定锚点
  策略指引（`{#anchor}` 的普及是 xref-to-heading 的前置，pg-internal
  7361 行只有 1 个手写锚点）。
- **part/chapter 从属表达**：ddia 的 part 与 chapter 在树上同级——
  文档化 `data/docs_nav.json` 显式分层方案（aiempire 已实践），不强制
  改目录结构。

**5.5.4 连载归档（archive）支援 —— 已搁置（§8 决议 13）**

zj 识别出的第五类场景，与 book 共享 pager（0.4 直接覆盖其核心痛点）。
以下三个小件**进 backlog 不排期**，记录以备将来：

- **分组侧栏**：大型扁平 section 按年份/前缀分组折叠
  （`params.ui.sidebar_group_by`），替代 402 项占页面体积 65% 的
  扁平列表。
- **归档索引表**：section 列表布局的表格形态（期号/日期/标题多列），
  zj 的 `interview-archive.html` 收编为通用布局。
- **超大离线索引运维指引**：`offlineSearchIndex: content` 在 760 万
  CJK 字符上产出 25MB 索引且 lunr 不分词——文档化边界与替代
  （标题+关键词模式、DocSearch）。

### 5.6 杂项共性上收（0.4 顺风车）

调研发现的低成本高回收项：

1. **`layouts/robots.txt`**：主题提供默认模板（sow/exp 逐字节相同的那份）。
2. **宽表格**：正式实现 `{.full-width}`（exp 43 处在用、零效果）+ 表格
   横向滚动策略，写进 content-primitives 契约。
3. **Section index 卡片化**：`section-index.html` 支持
   `params.ui.section_index: cards | list`，从子页 `title/description/
   icon` 生成 doc-cards 视觉——消灭 sow 5 处手写重述与 exp 手写表格。
4. **`page-meta-lastmod` 展示参数**：`subject | hash | none`（sow 为改
   一行文案复制了整个 partial）。
5. **`sidebar_divider` 上收**：pig 复制 161 行 sidebar-tree 只为加分隔行
   ——作为正式 front matter 参数收编。
6. **契约文档补录既有暗机制**：`data/docs_nav.json`、`manualLink` +
   `build.render: link` 幽灵页——两站已在生产使用、三站靠口口相传。
7. **search 关键词扩展钩子**：zj 为 15 行期号别名逻辑 fork 了 68 行
   `search/metadata.html`（升级必然静默腐烂）。暴露一个空默认的
   `search/keywords-extra.html` 钩子即可让该 fork 消失。
8. **主题缺陷修复**：404 模板多语言多输出构建的 base 继承不确定性；
   <768px `scroll-padding-top` 重置与 sticky subnav 冲突的锚点遮挡回归。
9. **站点清障清单**（不动主题，随迁移文档发布）：Hextra/DDIA 化石
   （死 i18n/死 CSS/死 shortcode/错误 CLAUDE.md）。图片 alt/图注一致性
   校验并入 0.6 的 `check-book.py`，不单独立项（配置层版本字面量自查
   已按 §8 决议 11 裁掉）。

---

## 6. 横切约束与工程配套

### 6.1 输出矩阵行为表

每个新组件在四种输出下的行为，实现与契约必须同款：

| 组件 | html | print | markdown / llms | rss |
| --- | --- | --- | --- | --- |
| pager | 卡片 + head rel | 剥离 | 剥离 | 剥离 |
| release-card | 卡片按钮组 | 静态链接列表 | 链接列表 | 链接列表 |
| release-assets | 表格 + 复制 + 徽章 | 静态表格（无按钮） | 管道表全量 hash | 同 markdown |
| download | 分段/tab + 复制 | 静态分段（展开全部） | 各渠道命令原文 | 剥离 |
| landing sections | 完整交互 | 静态化（marquee→网格、动画关） | 标题+文本降级 | 剥离 |
| fig/tbl/eq | figure+figcaption | 同 html（保留编号锚点） | `**图 2-1.** caption` + 原始内容 | 同 markdown |
| xref | 站内链接 | 同 html | `图 2-1`（相对链接） | 同 markdown |
| book-toc | 多级目录 | 同 html | 嵌套列表 | 剥离 |

`static-image-output.html` 的属性剥离正则若需扩展（fig 包装的图片），
按既有"attribute-precise"纪律修改。

### 6.2 i18n 新增 key（×32 locale）

预计 ~20 个：资产表（`ui_assets_*`：file/checksum/copy/copied/download）、
发布卡（`ui_release_*`：view/source/compare/released/checksums）、
下载（`ui_download_unpublished` 等）、书籍（`book_figure/table/equation`、
`book_lof/lot`、`book_draft`）、可达性（`ui_marquee_pause`、pricing 勾叉
aria）。流程照旧：en + zh 系人工评审，其余 `check-i18n.py --sync` 英语
兜底。**landing section 的展示文案不进 i18n**——那是站点数据（P3），
i18n 只管主题 chrome 字符串。

### 6.3 运行时 flag 与 bundleKey

| 新 flag | 运行时 | 说明 |
| --- | --- | --- |
| `hasAssetList` | 校验和复制 | 独立小文件；不复用 hasCodeRuntime（C5：不读别家 flag） |
| `hasLanding` | reveal/count/copy/双图/移动菜单 | layout 设置（层内先于 scripts.html，时序合法） |

两者均须加入 `$bundleKey` 列表（否则不同特性组合的页面会撞同名 bundle）。
**零 JS 组件**（pager、fig/xref、book-toc、marquee、pricing、timeline、
code-plate、bar-chart）不设 flag——这是刻意的设计约束，不是遗漏。
download 复用 `hasCodeRuntime`/`hasTabpane` 的方式是**由 download 渲染器
自己 Set**（shortcode 设 flag 供装配读取，合法方向）。

### 6.4 检查脚本与测试布局

主题仓库（源级 + 输出级，进 CI 序列）：

- `check-prd5-reading.py`：pager 树序 == 侧栏序、单边渲染、rel 链接、
  非 html 输出剥离；render-passthrough 存在性与 `$$` 渲染实测。
- `check-release-assets.py`：行文法/算法识别/URL 编码/输出矩阵/errorf 路径。
- `check-download.py`：schema 校验、rolling 不插版本、pinned 插值、
  `published: false` 禁用态。
- `check-landing.py`（0.5）：section registry、marquee reduced-motion、
  print 静态化、双语字段回退链。
- `check-book.py`（0.6）：fig/xref id 唯一性、i18n label、book-toc 层级、
  print 聚合。
- exampleSite 补对应 fixture 页（保持"最小夹具"性质，一特性一页）。
- `tests/js/`：asset-copy 与 landing 运行时的 node --test 覆盖
  （这是浏览器代码唯一的自动检查，C 系惯例）。

站点仓库（oink.pgsty.com）：md-output goldens 补 fig/assets/download 的
markdown 退化样张；Playwright 补 pager 导航、资产复制、marquee 暂停、
palette-in-landing 四条 spec。

### 6.5 契约文档归属

- **content-primitives.md 增补**：release-assets、fig/tbl/eq、xref、
  full-width 表格（machine-checked 结构同步更新
  `check-content-primitives-contract.py`）。
- **新 contract**（沿 PRD 4 格式：决策冻结 + 机器可读伴生 + 迁移指南
  EN/ZH）：`prd5-reading-release-contract.md`（0.4）、
  `prd5-landing-contract.md`（0.5）、`prd5-book-contract.md`（0.6）。
- 每条 track 的契约**与行为同 commit 落地**（既有纪律），本设计稿在
  对应内容冻结后降级为历史记录。

---

## 7. 里程碑与释出规划

排序原则：正确性缺陷最先；小体量高确定性先于大体量；每个里程碑必须有
**真实站点作为验收载体**（绿色本地构建不算完成——按 README 的
release states 走完 validated → published → documented → deployed）。

### 0.4.0 「阅读与发布」（Reading & Release）

| 项 | 内容 | 验收站点 |
| --- | --- | --- |
| 数学补洞 | render-passthrough hook + 起步配置文档 + `{{< eq >}}` 逃生舱 + katex 溢出 CSS 上移 | pg36g（44 文件零改动恢复）、silo/pig/oink 站/pg-internal（删除四份自建 hook） |
| Pager | nav-flatten 树序 + 卡片 UI + rel 链接 + 配置 | oink.pgsty.com、pg36g（跨章）、aiempire（docs_nav 序） |
| Release 原语 | `release` front matter + release-card + releases 列表布局 | pig（51 版）、silo（多产品线） |
| 资产表 | `{{< release-assets >}}` + `hasAssetList` 运行时 | pig（400 行裸 hash 替换、MD5 标注） |
| Download 数据层 | `data/download/<key>.yaml` + `{{< download >}}` 文档页形态 | pig `install.md`（filetree 占位符恢复为真链接） |
| 杂项批 | robots.txt、full-width、section-index 卡片化、lastmod 参数、sidebar_divider、docs_nav/manualLink 契约补录、404 与 scroll-padding 修复 | sow/exp（删覆盖文件）、pig（删 sidebar-tree fork） |

新契约：content-primitives.md 增补（assets/eq）；`prd5-reading-release-contract.md`。

### 0.5.0 「Landing 泛化」

前置依赖：navbar/footer 集成工程（§2.1）落地。

| 项 | 内容 | 验收站点 |
| --- | --- | --- |
| landing 外壳 | `layout: landing` + mega menu + 星数徽标 + 跨仓语言切换 + ICP + 面板复用 | pgsty.com（5 个绕壳模板归零） |
| landing 运行时 | `hasLanding`：reveal/count/copy/双图/移动菜单（SurfaceCoordinator） | pgsty.com、pigsty.cc（各删 ~330 行 JS） |
| 形态补全 | capabilities image、metrics animate+source、faq flat、marquee 变体、cta 增强 | pigsty.cc 首页迁移（2147 行 → 数据驱动） |
| 新 section | pricing → command-box → steps → timeline → code-plate → case-study → download(landing) → bar-chart | pgsty.com/pigsty.cc 共用 pricing 数据；silo 下载页重建 |

新契约：`prd5-landing-contract.md`（section registry、数据双语解析、
marquee 可达性、运行时 flag）。

### 0.6.0 「Book 能力包」

| 项 | 内容 | 验收站点 |
| --- | --- | --- |
| 编号原语 | fig/tbl/eq 锚点 + xref 交叉引用（含无 kind 泛化）+ 图表目录 + 三份迁移脚本配方 + 一致性检查 | tpme（62 图去手编 + 1062 处跨语言泄漏修复）、ddia（131 处兼容迁移，参数全集对齐）、pg-internal（90 处死引用复活） |
| 书籍装配 | `book` 类型 + `book_*` 采认 + draft 状态 UI + `{{< book-toc >}}` + 章内标题侧栏下钻 | pg36g（删 1181 行 toc + 退役 Ruby 模型）、pg-internal（100KB 单文件章可导航） |
| 整书视图 | print 聚合扩展至 book 根（整书单页），消除扁平书零 print 的不一致 | aiempire（PDF 管线减半）、ddia（EPUB 预处理退役）、tpme |

新契约：content-primitives.md 增补（fig/tbl/xref）；`prd5-book-contract.md`。

**为什么这个顺序**：0.4 全部落在既有机制上（风险最低、含唯一 P0），
且立刻解除 pig/pg36g 的现役疼痛；0.5 有外部依赖（navbar/footer）且
体量最大，但它决定"自有站点用纯 Markdown 拼装"的最终目标能否达成；
0.6 的编号原语是全新契约面，放最后可吸收前两轮的实现经验——若 ddia
迁移压力上升，0.6 可与 0.5 对调，二者无依赖关系（0.6 仅依赖 0.4 的
nav-flatten 与数学修复）。

---

## 8. 开放问题决议（2026-08-13 裁决）

1. **Pager 默认开关** → **默认开启**（docs/book/blog，页面级
   `pager: false` 可关）。
2. **fig caption 是否允许 Markdown** → **锁定为纯文本**（与既有契约
   一致：只有 Fields 描述吃 Markdown）。
3. **非 GitHub forge** → **不做**。release/assets 仅认 github.com，
   不预留 `host` 参数，等真实需求再议。
4. **pricing 月/年切换** → **不做**。pricing 做简单版：纯前端静态样式，
   无 JS、无状态切换。
5. **贡献者组件** → **站点自填数据**。主题只提供框架：把条目列成一排
   （头像/名字/URL 前往链接），不做任何抓取，不投资镜像配方。
6. **阅读进度条** → **不做**。
7. **多级编号标题**（render-heading 编号派生锚点） → **不做**。
8. **partial 融合方向** → **确认**：目标是把站点侧覆盖的 partial
   尽可能融合进框架（含 `home/` → `landing/` 内部整并，随 0.5 执行）。
9. **image-hotspots** → 维持暂缓（未另行裁决，按原建议）。
10. **整书 PDF / 书籍 PDF 配方文档** → **不做**。主题止步于 print HTML。
11. **配置层版本字面量一致性自查脚本配方** → **暂不做**。
12. **图表自动编号（post-render 回填方案）** → **不做**，太复杂。
    维持 v1 手动编号 + 检查脚本兜底，不再规划 v2。
13. **连载归档独立 shell type** → **不做**，连带 §5.5.4 的归档支援
    三小件（分组侧栏/归档索引表/大索引指引）一并搁置进 backlog；
    zj 的核心痛点由 0.4 的 pager 直接覆盖。
14. **术语表/索引组件** → **不做**。xref 无 kind 泛化已覆盖回指链接
    的维护问题。

以上决议已同步进各 track 规格与里程碑表；被裁掉的条目不进入 `plan/`
任务分解。
