---
title: 运行与复盘
description: 用可观测的服务目标与可重复的复盘闭合流程。
book_kind: chapter
book_number: 3
weight: 30
outputs: [HTML, print, markdown]
---

> *寄希望于运气，不是一种策略。*
>
> —— Google，《Site Reliability Engineering》（2016）

只有观察过实际运行的系统，发布才算完成。先取得
{{< xref page="chapter-two" eq="2.1" anchor="eq-readiness" />}} 的就绪度，再与运行证据比较。

## 观察结果 {#observe-result}

{{< fig num="3-1" id="fig-operations" src="/images/oink.webp" alt="发布后的 OINK 文档站点" caption="以读者看到的方式检查已经发布的站点。" width="600" height="300" />}}

{{< tbl num="3-1" id="tbl-operations" caption="最终复盘使用的信号。" >}}
| 信号 | 目标 | 复盘频率 |
| --- | --- | --- |
| 可用性 | 99.9% | 每日 |
| 故障切换耗时（RTO） | ≤ 45 秒 | 每次故障 |
| 失效链接 | 0 | 每次构建 |
| 读者反馈 | 全部归类 | 每周 |
{{< /tbl >}}

{{< eq num="3.1" id="eq-budget" caption="扣除实际故障时间后的剩余错误预算。" >}}
E_{remaining} = E_{planned} - E_{observed}
{{< /eq >}}

{{< eg num="3-1" id="eg-review" caption="用一条可复现的查询总结复盘结论。" >}}
```sql
SELECT signal, actual, target
FROM operational_review
WHERE release = '0.5.0';
```
{{< /eg >}}

最终结论应当引用 {{< xref tbl="3-1" anchor="tbl-operations" />}} 与
{{< xref eq="3.1" anchor="eq-budget" />}}，而不是含糊地说这次部署"看起来还行"。

## 给故障切换编预算 {#failover-budget}

{{< xref tbl="3-1" anchor="tbl-operations" />}} 里有一行值得单开一章。恢复时间并不是数据库
直接报出来的某个数，而是若干段彼此独立的等待之和，每一段各由不同的超时参数支配；
要诚实地公布它，唯一的办法就是把这个分解摊开给人看。

<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.rtoPhase = function (params) {
    if (!params || !params.length || params[0].name === '') return '';
    var rows = params
      .filter(function (p) { return p.value !== '-' && p.value != null; })
      .map(function (p) { return p.marker + ' ' + p.seriesName + '：' + p.value + ' 秒'; });
    return '<b>' + params[0].name + '</b><br/>' + rows.join('<br/>');
  };
</script>

```echarts {height="520px" full=true}
tooltip: { trigger: axis, axisPointer: { type: shadow }, formatter: "$fn:rtoPhase" }
legend: { top: 0, itemGap: 12, data: [故障检测, 重启超时, 从库察觉, 抢锁提拔, 健康检查] }
grid: { left: 78, right: 24, bottom: 32, top: 40 }
xAxis:
  type: value
  name: 秒
  nameLocation: end
  max: 160
  axisLine: { show: true }
  axisTick: { show: true }
  splitLine: { show: true, lineStyle: { type: dashed, opacity: 0.5 } }
  minorTick: { show: true, splitNumber: 5 }
  minorSplitLine: { show: true, lineStyle: { type: dotted, opacity: 0.2 } }
yAxis:
  type: category
  axisLine: { show: true }
  axisTick: { show: true }
  splitLine: { show: false }
  axisLabel: { fontSize: 10, fontFamily: monospace }
  data: [wide-max, wide-avg, wide-min, "", safe-max, safe-avg, safe-min, "", norm-max, norm-avg, norm-min, "", fast-max, fast-avg, fast-min]
series:
  - { name: 故障检测, type: bar, stack: rto, barWidth: 20, z: 2, emphasis: { focus: series }, itemStyle: { color: "#b07aa1" }, data: [20, 10, 0, "-", 10, 5, 0, "-", 5, 3, 0, "-", 5, 3, 0] }
  - { name: 重启超时, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#f28e2c" }, data: [95, 95, 0, "-", 45, 45, 0, "-", 25, 25, 0, "-", 15, 15, 0] }
  - { name: 从库察觉, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#edc949" }, data: [20, 10, 0, "-", 10, 5, 0, "-", 5, 3, 0, "-", 5, 3, 0] }
  - { name: 抢锁提拔, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#59a14f" }, data: [2, 1, 0, "-", 2, 1, 0, "-", 2, 1, 0, "-", 2, 1, 0] }
  - { name: 健康检查, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#4e79a7" }, data: [8, 6, 4, "-", 6, 5, 3, "-", 4, 3, 2, "-", 2, 2, 1] }
  - { name: RTO 预算, type: bar, barGap: "-100%", barWidth: 20, z: 0, itemStyle: { color: "rgba(128,128,128,0.14)" }, emphasis: { itemStyle: { color: "rgba(128,128,128,0.2)" } }, data: [150, 150, 150, "-", 90, 90, 90, "-", 45, 45, 45, "-", 30, 30, 30] }
```

每一组是一套超时档位，组后面那条灰色的条是这套档位承诺的预算。`fast` 档能把最坏情况压进
30 秒，靠的是五段等待全都很短——没有哪一个参数能单独买到这个结果。

| 阶段 | 最好 | 最坏 | 平均 | 由谁决定 |
| --- | :---: | :---: | :---: | --- |
| 故障检测 | `0` | `loop` | `loop/2` | `loop_wait`——崩溃可能恰好落在一次探测之后 [^patroni] |
| 重启超时 | `0` | `start` | `start` | `primary_start_timeout`；最好情况是自愈，于是不发生切换 |
| 从库察觉 | `0` | `loop` | `loop/2` | 从库一侧的 `loop_wait` |
| 抢锁提拔 | `0` | `2` | `1` | 一次 DCS 往返再加一次 `promote` |
| 健康检查 | `(rise-1) × fastinter` | `(rise-1) × fastinter + inter` | `(rise-1) × fastinter + inter/2` | HAProxy 的 `rise`、`inter`、`fastinter` [^haproxy] |
{#tbl-failure-model .full-width num="3-2" caption="恢复路径上每一段等待各自的来源，只有最后一行不在数据库里。"}

{{< xref tbl="3-2" anchor="tbl-failure-model" />}} 的每一行都是分段的：最好情况是崩溃恰好落在
探测之前，最坏情况是恰好落在探测之后。

$$
T_{\text{detect}} =
\begin{cases}
0, & \text{崩溃恰好落在探测之前} \\[2pt]
\tfrac{1}{2}\,t_{\text{loop}}, & \text{到达时刻服从均匀分布} \\[2pt]
t_{\text{loop}}, & \text{崩溃恰好落在探测之后}
\end{cases}
$$
{#eq-detect num="3.2" caption="检测延迟：一个以崩溃到达时刻为自变量的分段函数。"}

把各段相加，就得到复盘要公布的那个数，同时也让人看清：平均值并不是运维口中那些平均值
之和。

$$
\mathrm{RTO}_{\max} = t_{\text{loop}} + t_{\text{start}} + t_{\text{loop}} + t_{\text{promote}} + \bigl[(\mathit{rise}-1)\,t_{\text{fast}} + t_{\text{inter}}\bigr]
$$
{#eq-rto num="3.3" caption="最坏情况恢复时间等于五段独立等待之和。"}

图中的四套档位，其实是同样五个参数的四组取值，而且它们属于配置，不属于代码：

```yaml {num="3-2" caption="norm 档：30 秒的租约，以及一个能在租约内放下两次的重启窗口。" #eg-profile}
patroni:
  ttl: 30                     # Leader 租约
  loop_wait: 5                # HA 循环间隔
  retry_timeout: 10           # DCS 操作重试预算
  primary_start_timeout: 25   # 切换之前，等待崩溃主库恢复的时间
haproxy:
  inter: 3s                   # 状态稳定时的健康检查间隔
  fastinter: 1s               # 怀疑状态正在切换时的间隔
  rise: 3                     # 连续成功多少次才把流量放回来
```

把 {{< xref eq="3.3" anchor="eq-rto" />}} 与 {{< xref eg="3-2" anchor="eg-profile" />}} 对着读：
`25 + 5 + 5 + 2 + (2 × 1 + 3) = 42` 秒，落在
{{< xref tbl="3-1" anchor="tbl-operations" />}} 的 45 秒目标之内，只富余三秒。
只富余三秒的目标，迟早会被打破。

## 闭合循环 {#close-loop}

把复盘结论反馈回
{{< xref page="chapter-one" eg="1-1" anchor="eg-baseline" />}} 的基线，
让下一次发布从最新证据开始。第四章处理本书迄今刻意回避的一类材料：论证由数学、
而不是由表格承担的章节。

## 参考文献 {#references}

[^patroni]: [Patroni documentation: replication and failover parameters](https://patroni.readthedocs.io/en/latest/replication_modes.html). *patroni.readthedocs.io*, 2026 年查阅.
[^haproxy]: [HAProxy Configuration Manual: `inter`, `fastinter`, `rise`, `fall`](https://docs.haproxy.org/3.0/configuration.html#5.2-inter). *docs.haproxy.org*, 2026 年查阅.
