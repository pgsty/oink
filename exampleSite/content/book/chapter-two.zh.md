---
title: 发布流程
description: 把经过评审的变更变成可追溯的发布。
book_kind: chapter
book_number: 2
book_status: draft
weight: 20
outputs: [HTML, print, markdown]
---

第一章通过 {{< xref page="chapter-one" fig="1-1" anchor="fig-overview" />}} 建立了基线，本章沿着同一项变更继续走完发布流程。

## 明确区分交付状态 {#delivery-states}

本地修改、提交、推送与生产部署是彼此独立的状态。把它们分别记录，发布过程才容易审计。

{{< fig num="2-1" id="fig-release" src="/images/releasenote.webp" alt="OINK 发布说明页面" caption="发布说明把已交付制品与验证证据连接起来。" width="600" height="300" />}}

{{< tbl num="2-1" id="tbl-release" caption="各交付阶段需要的证据。" >}}
| 阶段 | 证据 | 负责人 |
| --- | --- | --- |
| 构建 | 可复现的制品 | 维护者 |
| 发布 | 远端校验和 | 发布工程师 |
| 部署 | 实际运行版本 | 运维人员 |
{{< /tbl >}}

{{< eq num="2.1" id="eq-readiness" caption="一个简单的发布就绪度评分。" >}}
R = \frac{B + T + D}{3}
{{< /eq >}}

{{< eg num="2-1" id="eg-manifest" caption="记录一份不可变的发布清单。" >}}
```yaml
version: 0.5.0
artifact: oink-0.5.0.tar.gz
sha256: verified
status: staged
```
{{< /eg >}}

{{< xref eg="2-1" anchor="eg-manifest" />}} 中的清单与 {{< xref tbl="2-1" anchor="tbl-release" />}} 中的阶段代表不同证据，不应被压成一个状态。

## 交接 {#handoff}

第三章会把 {{< xref eq="2.1" anchor="eq-readiness" />}} 作为运行复盘的输入。
