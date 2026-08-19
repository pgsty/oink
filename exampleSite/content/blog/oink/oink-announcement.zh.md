---
title: OINK 实现预览正式亮相
linkTitle: OINK 实现预览
date: 2026-08-08
aliases: [/blog/2026/oink-announcement/]
lastmod: 2026-08-08
description: >-
  OINK 将直接定制的 Docsy 代码库演化为本地优先、仅依赖 Hugo
  的文档主题，并提供多语言基础设施与可复用内容组件。
featured_image: wash
authors: [oink-maintainers, vonng]
tags: [Oink]
---

今天，我们发布 OINK 实现预览：它从 Docsy 直接演化而来，提供唯一标准产品外壳、仅依赖 Hugo 的消费端构建、本地优先浏览器依赖、通用多语言框架，以及一组从 PGSTY 文档站提炼出的可复用内容组件。

这是实现与文档里程碑，不是已经公开的版本化发行。最终公开品牌、模块与软件包身份、首个版本，以及生产 Cloudflare
Pages 部署，仍是必须显式关闭的发布关卡。

## 为什么需要 OINK？ {#why-oink-exists}

多个成熟文档站分别复制了相同的 Docsy 布局、导航、搜索代码、SCSS、JavaScript 与短代码。一个公共修复必须在多个仓库重复实施；与此同时，每个站点都携带前端工具链与隐含网络依赖，让网络隔离构建变得异常复杂。

OINK 将真正可复用的部分合并到主题中。产品矩阵、门户、价格页和其他业务专用行为仍留在各自站点；共享主题负责文档外壳、浏览器运行时、多语言路由、无障碍行为与内容组件契约。

## 有哪些变化？ {#what-changes}

### 产品本身，而不是一种模式 {#one-product-instead-of-a-mode}

OINK 不是可选皮肤。项目没有 `oink.enabled` 开关、`params.oink.*`
命名空间，也没有“上游版与品牌版”并行的模板树。`theme/` 中的实现就是产品。

这项决策避免维护两套视觉系统与两套测试矩阵。Hugo 原生设置与兼容的 Docsy 参数继续保持原有含义。

### 消费端仅依赖 Hugo 构建 {#hugo-only-consumer-builds}

完整消费站点只需运行：

```sh
hugo --gc --minify
```

Bootstrap、Font
Awesome、字体、搜索、图表、API 文档运行时与 OINK 组件都已随主题提交。Node.js、npm、PostCSS、Autoprefixer 与 CDN 下载不属于消费端要求。

仓库维护者仍会使用 Node 工具运行测试和更新 vendor 资源；这套维护工具链有意置于公开站点构建契约之外。

### 本地优先的浏览器行为 {#local-first-browser-behavior}

默认 starter 会从生成后的站点提供页面外壳、字体、图标、搜索、Mermaid、KaTeX、Markmap、Swagger
UI、Redoc、Asciinema、ECharts 与 Infographic 依赖。可选运行时按页面选取，并且每页最多加载一次。

PlantUML 与 Diagrams.net 不再拥有公共服务默认值。站点必须配置受控端点、使用预渲染结果，或明确选择远程服务。

### 多语言基础设施 {#multilingual-infrastructure}

语言路由来自 Hugo 的语言与翻译对象。配置一种语言时隐藏选择器；配置两种或更多语言时，直接点击按配置顺序切换，短暂悬停或键盘聚焦则打开完整菜单。当前页面缺少译文时，选择器会进入目标语言首页，而不是失效路径。

starter 与本站均以英文为首要语言、简体中文为第二语言。核心文档与博客范围内的每个页面都有并置的
`.zh.md` 译文，且标题采用稳定的显式 ID。

### 可复用组件 {#reusable-components}

OINK 新增主题级 Asciinema、ECharts、Infographic、文档轮播、折叠块、标签页、卡片、导航卡片、文档卡片与参数组件。它们会生成唯一实例 ID，并且只在实际使用时加载本地资源。

ECharts 接受结构化 JSON 或 YAML，也支持通过 `$fn:name`
引用可选的 JavaScript 回调。回调代码只在声明它的页面运行。

## 哪些能力保持不变？ {#what-stays-familiar}

OINK 沿用 Docsy 的内容组织、front
matter、文档与博客 section、菜单、taxonomy、打印输出、仓库链接、常用短代码、图表、API 参考能力与扩展 hook。现有站点可以删除重复公共实现，而不必重写普通 Markdown。

项目也保留 Docsy 的 Apache-2.0 历史与归属信息。vendor 清单记录固定的第三方来源、许可证、产物与校验值。

## 体验 starter {#try-the-starter}

安装 Hugo Extended `0.160.1` 或更高版本，然后在当前检出目录运行：

```sh
hugo --source starter --gc --minify
```

当前验证基线为 Hugo Extended
`0.164.0`。打开生成的英文与中文页面，切换语言、使用本地搜索、改变颜色模式，并访问组件示例。

需要传入网络隔离环境时，维护者可以创建完整归档：

```sh
scripts/package-offline.sh /absolute/path/oink-preview.tar.gz preview
```

归档包含主题、starter、许可证、上游记录、迁移指南、vendor 清单和配套校验值。

## 当前验证范围 {#current-validation}

当前实现的自动化覆盖包括：

- 最低版本与当前版本 Hugo Extended 构建；
- 禁止消费端 Node/npm/PostCSS/Autoprefixer 路径；
- LTR、RTL、子路径、打印、颜色模式与生产资源；
- 完整的一种/两种/三种/四种及以上语言选择器矩阵；
- 本地按页运行时与重复组件实例；
- ECharts 结构化选项与回调集成；
- 离线双语 starter 与离线发行归档；
- vendor 许可证与校验值；
- SILO、PGSTY、SOW 与 Pigsty 的非破坏性迁移演练。

最近一次四站演练成功构建了临时副本，但没有修改或部署这些生产仓库。

## 正式发布前还需要什么？ {#what-remains-before-release}

公开身份与首个版本必须获批，并一致应用到模块、软件包、源码标签、嵌套主题标签、归档与文档。随后还要把目标 Cloudflare
Pages 项目连接到源分支，使用固定 Hugo 版本构建、公开发布，并在托管 URL 上完成验证。

这些关卡关闭之前，请把该预览用于评估与迁移演练，不要把未固定版本的代码当作生产依赖。

## 继续阅读 {#read-next}

- [OINK 概览](/zh/docs/about/)
- [架构](/zh/docs/about/architecture/)
- [本地优先运行](/zh/docs/about/local-first/)
- [内容组件](/zh/docs/components/)
- [配置总览](/zh/docs/customize/config/)
- [迁移指南](/zh/docs/upgrade/from-docsy/)
- [发布流程](/zh/docs/about/)
- [实施日记](/zh/blog/oink/oink-implementation-diary/)
