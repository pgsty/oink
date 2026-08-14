# OINK PRD 5 场景组件迁移参考

版本归属：OINK 0.4.0（阅读与发布）与 OINK 0.5.0（Landing）

本文覆盖 0.4「阅读与发布」与 0.5「Landing」源码契约。源码状态、已验收
checkout、不可变签名标签、消费站固定版本与线上部署是彼此独立的证据。
规范性决策见[阅读/发布契约](prd5-reading-release-contract.md)与
[Landing 契约](prd5-landing-contract.md)，机器可读副本为
`tests/fixtures/prd5/contract.json`。

兼容下限：Hugo Extended 0.160.1。

## 发布闸门 {#release-gates}

以下状态分别记录：

1. 主题 checkout 中的源码完成；
2. 两个支持的 Hugo 版本与聚焦契约均通过；
3. 对应的 OINK 0.4.0 或 0.5.0 不可变签名标签可解析；
4. 消费站在 `go.mod` 中固定该精确标签；
5. 线上输出通过 URL、语言和浏览器冒烟检查。

生产环境不以 `@latest` 作为版本策略，也不能用本地构建推断线上已交付。

## 顺序阅读导航 {#reading-navigation}

Pager 默认为 `docs`、`book`、`blog` 开启。站点可以替换类型列表，页面也可
单独退出：

```yaml
params:
  ui:
    pager:
      types: [docs, book, blog]
---
pager: false
```

docs 与普通 book 页面遵循侧栏同一棵树的前序顺序；blog 保持时间顺序。
存在 `data/docs_nav.json` 时，其可见页面树是权威顺序；link-only 页面与
`sidebar_divider` 分组仍可见，但不成为阅读目标。

直接位于站点根部的手册可让侧栏与 Pager 共享同一棵树：

```yaml
params:
  ui:
    sidebar_root_enabled: true
    docs_root: home
```

`docs_root` 只接受 `section` 或 `home`。HTML 输出 Pager 卡片与同源
`rel=prev` / `rel=next`；print、Markdown、RSS 均剥离这些导航。

## 数学公式 {#mathematics}

分隔符数学需要消费站开启 Goldmark，因为 Hugo 不会合并主题的 `markup`
配置：

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

OINK 提供 render hook 与本地 KaTeX CSS；仅写 `math: true` 没有语义。若站点
暂时无法启用 passthrough，可用严格的 display-only 逃生舱：

```go-html-template
{{< eq >}}E = mc^2{{< /eq >}}
```

0.4 形态不接受参数，也不创建编号、图注、锚点或 Book target。HTML 与 print
得到本地 KaTeX/MathML；Markdown 与 RSS 保留纯 `$$` TeX 块。

## 发布页面 {#release-pages}

发布事实属于页面 front matter：

```yaml
release:
  version: 1.7.0
  repo: pgsty/pig
  product: PIG
  tag: v1.7.0
  prev: v1.6.0
  checksums: SHA256SUMS
```

使用 `{{< release-card >}}` 本地生成仓库、归档、校验和与版本比较链接，不发
网络请求。已提交的校验和数据用
`{{< release-assets src="release/SHA256SUMS" >}}` 渲染。资产表只在交互 HTML
加载 `asset-list.js`；print、Markdown 与 RSS 显示完整 hash，不保留控件。

发布 section 可声明 `layout: releases`，按日期和 SemVer 排序而非 page weight；
产品分组与过滤均为显式 opt-in。

## 下载数据 {#download-data}

提交一份 `data/download/<key>.yaml` 事实记录：

```yaml
version: 1.7.0
published: true
channels:
  - id: source
    kind: rolling
    title: Source repository
    url: https://github.com/pgsty/pig
  - id: binary
    kind: pinned
    title: Versioned archive
    url: https://github.com/pgsty/pig/releases/download/${tag}/pig-${version}.tar.gz
```

通过 `{{< download "key" >}}` 渲染。rolling 渠道拒绝插值；只有 pinned URL
与命令步骤可以展开 `${version}` 和 `${tag}`。`published: false` 仍保留
rolling 渠道，但 pinned 渠道显示为待发布状态，不输出误导性链接或命令。
RSS 剥离组件；print 与 Markdown 保留安全静态说明。

## Landing 迁移 {#landing-migration}

任意普通内容页都可选择复用全宽壳层。页面身份放在 front matter，section
数据放在本地且区分语言的记录中：

```yaml
---
title: 价格
layout: landing
landing: pricing
---
# data/landing/pricing/zh.yaml
sections:
  - type: pricing
    data:
      title: 静态套餐
      tiers:
        - { name: 社区版, price: 免费, features: [本地优先] }
```

通用路径为 `data/landing/<key>/<lang>.yaml`；front matter 内联 `sections`
优先。精确语言标签依次回退到主语言与无后缀本地值。首页继续兼容
`data/home/<lang>.yaml`，但首页与普通页面都由 `landing/` 注册表渲染。

注册表保留已有首页 section，并新增 `pricing`、`pricing-compare`、
`command-box`、`steps`、`timeline`、`code-plate`、`case-study`、`download`
与 `bar-chart`。Landing download section 与 shortcode 读取同一份
`data/download/<key>.yaml` 事实，不会在运行时获取价格、GitHub stars、图片、
发布信息或其他可变事实。

交互 HTML 设置 `hasLanding`，并按需加载 `landing.js` 增强 reveal、count-up、
复制、主题图片与紧凑菜单；禁用 JavaScript 时服务端内容仍然完整。Marquee
用本地化 CSS checkbox 暂停，复制轨道同时设置 `aria-hidden` 与 `inert`。
reduced motion 关闭移动与 reveal 动画，forced colors 仍保留控件和状态差异。

`params.ui.landing_search` 是严格布尔值，默认 true，但搜索仍要求已有的
`offlineSearch` opt-in。可选本地事实放在 `params.ui.github_stars` 与
`params.ui.alt_site`。Navbar 父菜单可将 `params.columns` 设为 1–4，生成
mega-menu 网格。这些值都在构建期渲染，不由浏览器 API 补写。

HTML 在完整静态 section 上渐进增强；print 保留静态布局，Markdown 输出
朴素结构，RSS 剥离 Landing 正文。根相对链接与资源必须在 `/` 和
`/preview/` 等部署前缀下都正确。旧 `blocks/*` shortcode 保持兼容，但新
Landing 页面不应继续采用。

## 删除共享覆盖 {#shared-overrides}

删除消费站 override 前，必须把真实本地差异与已固定的主题版本逐项比较。
OINK 0.4–0.5 已包含 passthrough hook、生产环境感知的 `robots.txt`、确定性 404、
last-commit 模式、全宽表格、卡片式 section index、侧栏 divider、显式导航树
支持、搜索关键词扩展 hook，以及供首页和普通页面共用的 Landing renderer。
站点政策与内容事实仍留在消费站仓库。

## 验收清单 {#validation-checklist}

- [ ] `python3 scripts/check-prd5-contract.py` 通过。
- [ ] `check-prd5-reading.py`、`check-release-assets.py`、`check-download.py`
      、`check-landing.py` 与 `check-prd5-misc.py` 在 Hugo Extended 0.160.1
      和 0.164.0 通过。
- [ ] `python3 scripts/check-content-primitives-contract.py` 与
      `python3 scripts/check-i18n.py` 通过。
- [ ] `node --test 'tests/js/**/*.test.js'` 通过。
- [ ] 严格 root 与 `/preview/` 构建都保留部署前缀。
- [ ] HTML、print、Markdown 与 RSS 遵守冻结的输出矩阵。
- [ ] Landing 在禁用 JavaScript、reduced motion、forced colors、双主题、
      键盘操作与窄视口下仍可使用。
- [ ] 消费站 pin、CI 结果、签名标签与线上部署分别验收。
