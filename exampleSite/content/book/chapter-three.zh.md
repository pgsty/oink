---
title: 运行与复盘
description: 用可观测的服务目标与可重复的复盘闭合流程。
book_kind: chapter
book_number: 3
weight: 30
outputs: [HTML, print, markdown]
---

只有观察过实际运行的系统，发布才算完成。先取得
{{< xref page="chapter-two" eq="2.1" anchor="eq-readiness" />}} 的就绪度，再与运行证据比较。

## 观察结果 {#observe-result}

{{< fig num="3-1" id="fig-operations" src="/images/oink.webp" alt="发布后的 OINK 文档站点" caption="以读者看到的方式检查已经发布的站点。" width="600" height="300" />}}

{{< tbl num="3-1" id="tbl-operations" caption="最终复盘使用的信号。" >}}
| 信号 | 目标 | 复盘频率 |
| --- | --- | --- |
| 可用性 | 99.9% | 每日 |
| 失效链接 | 0 | 每次构建 |
| 读者反馈 | 全部归类 | 每周 |
{{< /tbl >}}

{{< eq num="3.1" id="eq-budget" caption="扣除实际故障时间后的剩余错误预算。" >}}
E_{remaining} = E_{planned} - E_{observed}
{{< /eq >}}

{{< eg num="3-1" id="eg-review" caption="用一条可复现的查询汇总复盘。" >}}
```sql
SELECT signal, actual, target
FROM operational_review
WHERE release = '0.5.0';
```
{{< /eg >}}

最终判断应引用 {{< xref tbl="3-1" anchor="tbl-operations" />}} 与
{{< xref eq="3.1" anchor="eq-budget" />}}，而不是笼统声称部署“看起来没问题”。

## 闭合流程 {#close-loop}

把复盘结果写回 {{< xref page="chapter-one" eg="1-1" anchor="eg-baseline" />}} 的基线，让下一次发布从最新证据出发。
