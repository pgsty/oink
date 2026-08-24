---
title: 数据围栏
linkTitle: 数据围栏
description: 以代码围栏形式声明的图表、信息图与校验和清单。
outputs: [HTML, markdown]
weight: 50
---

## ECharts

```echarts {height="320px"}
xAxis:
  type: category
  data: [草稿, 评审, 已发布]
yAxis:
  type: value
series:
  - type: bar
    data: [12, 9, 4]
tooltip:
  formatter: "$fn:bytesFormatter"
```

## 校验和（发布包的原生形态）

```checksums {base="https://downloads.example.org/releases/stable" algo="sha256"}
f0b8c9d84dd2b877e0b952130b73e218106fec04c23852271d390213a1ff96f4  pig-1.7.0-1.aarch64.rpm
fbd9b5a696a3cbdcd49ec946664bcdb4a7963919380d3809beb5cefdcfe8bcdf  pig-1.7.0-1.x86_64.rpm
```

## Mermaid

```mermaid
flowchart LR
  围栏 --> 图形 --> 运行时
```
