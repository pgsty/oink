---
title: 卡片、文件树、画廊
linkTitle: 卡片 / 文件树 / 画廊
description: 由行尾标记选中的、以列表为基础的原生形态。
outputs: [HTML, markdown]
weight: 30
---

## 卡片——链接列表 `{.cards}`

- [安装](/zh/docs/) — 五分钟从零部署。
- [配置](/zh/fixtures/content-primitives/) — 调整运行时参数。
- [运维](/zh/fixtures/code-blocks/) — 上线之后的日常与升级。
- [参考](/zh/fixtures/typography/)
{.cards}

松散形态（描述单独成段）：

- [安装](/zh/docs/)

  五分钟从零部署。

- [配置](/zh/fixtures/content-primitives/)

  调整运行时参数，*描述里可以写 Markdown*。
{.cards}

## 任务列表

- [x] 渲染静态状态
- [ ] 在运行时给禁用的复选框加标签

## 文件树——`filetree` 围栏

```filetree {title="仓库结构"}
- content/                                # 站点内容
  - _index.md                             # 站点首页
  - docs/                                 # 产品指南       {open=false}
    - [getting-started.md](/zh/docs/)     # 带链接的条目
    - configuration.md
  - logs/
- hugo.yaml                               # root:root 0644
- README.md
- LICENSE                                 # {icon="fa-solid fa-scale-balanced" tone=warning}
```

四空格缩进，没有标题也没有注释（单列）：

```filetree
src
    main.go
    internal
        server.go
    build {type=dir}
```

粘贴来的 `tree` 输出：

```filetree
.
├── bin
│   └── pig
├── etc
│   └── pig.yml
└── README.md

2 directories, 3 files
```

## 画廊——`gallery` 围栏

```gallery
![总览页](shot-a.png)
![详情页](shot-b.png) # 请求详情
```
