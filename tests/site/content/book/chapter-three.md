---
title: Operate and review
description: Close the loop with observable service goals and a repeatable review.
book_kind: chapter
book_number: 3
weight: 30
outputs: [HTML, print, markdown]
---

> *Hope is not a strategy.*
>
> — Site Reliability Engineering, Google (2016)

A release is complete only after the running system is observed. Start with the
readiness measure in {{< xref page="chapter-two" eq="2.1" anchor="eq-readiness" />}}
and compare it with operational evidence.

## Observe the result {#observe-result}

{{< fig num="3-1" id="fig-operations" src="/images/oink.webp" alt="OINK documentation site after publication" caption="The published site is checked as a reader sees it." width="600" height="300" />}}

{{< tbl num="3-1" id="tbl-operations" caption="Signals used in the final review." >}}
| Signal | Target | Review cadence |
| --- | --- | --- |
| Availability | 99.9% | Daily |
| Failover time (RTO) | ≤ 45 s | Per incident |
| Broken links | 0 | Every build |
| Reader feedback | Triaged | Weekly |
{{< /tbl >}}

{{< eq num="3.1" id="eq-budget" caption="Remaining error budget after observed downtime." >}}
E_{remaining} = E_{planned} - E_{observed}
{{< /eq >}}

{{< eg num="3-1" id="eg-review" caption="Summarize the review with one reproducible query." >}}
```sql
SELECT signal, actual, target
FROM operational_review
WHERE release = '0.5.0';
```
{{< /eg >}}

The final decision should cite {{< xref tbl="3-1" anchor="tbl-operations" />}}
and {{< xref eq="3.1" anchor="eq-budget" />}} rather than relying on a vague
statement that the deployment “looks good.”

## Budget the failover {#failover-budget}

One row of {{< xref tbl="3-1" anchor="tbl-operations" />}} deserves a chapter of
its own. Recovery time is not a single number the database reports; it is a sum
of independent waits, each governed by a different timeout, and the only honest
way to publish it is to show the decomposition.

<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.rtoPhase = function (params) {
    if (!params || !params.length || params[0].name === '') return '';
    var rows = params
      .filter(function (p) { return p.value !== '-' && p.value != null; })
      .map(function (p) { return p.marker + ' ' + p.seriesName + ': ' + p.value + ' s'; });
    return '<b>' + params[0].name + '</b><br/>' + rows.join('<br/>');
  };
</script>

```echarts {height="520px" full=true}
tooltip: { trigger: axis, axisPointer: { type: shadow }, formatter: "$fn:rtoPhase" }
legend: { top: 0, itemGap: 12, data: [Detect, Restart timeout, Replica notices, Leader race, Health check] }
grid: { left: 78, right: 24, bottom: 32, top: 40 }
xAxis:
  type: value
  name: seconds
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
  - { name: Detect, type: bar, stack: rto, barWidth: 20, z: 2, emphasis: { focus: series }, itemStyle: { color: "#b07aa1" }, data: [20, 10, 0, "-", 10, 5, 0, "-", 5, 3, 0, "-", 5, 3, 0] }
  - { name: Restart timeout, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#f28e2c" }, data: [95, 95, 0, "-", 45, 45, 0, "-", 25, 25, 0, "-", 15, 15, 0] }
  - { name: Replica notices, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#edc949" }, data: [20, 10, 0, "-", 10, 5, 0, "-", 5, 3, 0, "-", 5, 3, 0] }
  - { name: Leader race, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#59a14f" }, data: [2, 1, 0, "-", 2, 1, 0, "-", 2, 1, 0, "-", 2, 1, 0] }
  - { name: Health check, type: bar, stack: rto, z: 2, emphasis: { focus: series }, itemStyle: { color: "#4e79a7" }, data: [8, 6, 4, "-", 6, 5, 3, "-", 4, 3, 2, "-", 2, 2, 1] }
  - { name: Budget, type: bar, barGap: "-100%", barWidth: 20, z: 0, itemStyle: { color: "rgba(128,128,128,0.14)" }, emphasis: { itemStyle: { color: "rgba(128,128,128,0.2)" } }, data: [150, 150, 150, "-", 90, 90, 90, "-", 45, 45, 45, "-", 30, 30, 30] }
```

Each group is one timeout profile; the grey bar behind it is the budget that
profile promises. The `fast` profile keeps its worst case inside 30 seconds only
because every one of its five waits is short — no single parameter buys the
result.

| Phase | Best | Worst | Mean | Governed by |
| --- | :---: | :---: | :---: | --- |
| Detect | `0` | `loop` | `loop/2` | `loop_wait` — the crash may land just after a probe [^patroni] |
| Restart timeout | `0` | `start` | `start` | `primary_start_timeout`; best case is self-healing, so no failover |
| Replica notices | `0` | `loop` | `loop/2` | `loop_wait` on the replica side |
| Leader race | `0` | `2` | `1` | One DCS round trip plus `promote` |
| Health check | `(rise-1) × fastinter` | `(rise-1) × fastinter + inter` | `(rise-1) × fastinter + inter/2` | HAProxy `rise`, `inter`, `fastinter` [^haproxy] |
{#tbl-failure-model .full-width num="3-2" caption="Where each wait in the recovery path comes from. Only the last row is outside the database."}

Every row in {{< xref tbl="3-2" anchor="tbl-failure-model" />}} is piecewise: the
best case is the crash arriving just before a probe, the worst is it arriving
just after.

$$
T_{\text{detect}} =
\begin{cases}
0, & \text{crash lands immediately before a probe} \\[2pt]
\tfrac{1}{2}\,t_{\text{loop}}, & \text{uniformly distributed arrival} \\[2pt]
t_{\text{loop}}, & \text{crash lands immediately after a probe}
\end{cases}
$$
{#eq-detect num="3.2" caption="Detection latency as a piecewise function of when the crash arrives."}

Summing the phases gives the number the review publishes, and makes visible that
the mean is not the sum of the means an operator usually quotes:

$$
\mathrm{RTO}_{\max} = t_{\text{loop}} + t_{\text{start}} + t_{\text{loop}} + t_{\text{promote}} + \bigl[(\mathit{rise}-1)\,t_{\text{fast}} + t_{\text{inter}}\bigr]
$$
{#eq-rto num="3.3" caption="Worst-case recovery time as the sum of five independent waits."}

The profiles in the chart are four settings of the same five parameters, and
they are configuration, not code:

```yaml {num="3-2" caption="The norm profile: a 30-second lease, and a restart window that fits inside it twice." #eg-profile}
patroni:
  ttl: 30                     # leader lease
  loop_wait: 5                # HA loop interval
  retry_timeout: 10           # DCS operation retry budget
  primary_start_timeout: 25   # wait for a crashed primary before failing over
haproxy:
  inter: 3s                   # health-check interval when the state is stable
  fastinter: 1s               # interval while a transition is suspected
  rise: 3                     # consecutive successes before traffic returns
```

Read {{< xref eq="3.3" anchor="eq-rto" />}} against
{{< xref eg="3-2" anchor="eg-profile" />}}: `25 + 5 + 5 + 2 + (2 × 1 + 3) = 42`
seconds, inside the 45-second target of
{{< xref tbl="3-1" anchor="tbl-operations" />}} with three seconds to spare. A
target met by three seconds is a target that will be missed.

## Close the loop {#close-loop}

Feed the review back into the baseline from
{{< xref page="chapter-one" eg="1-1" anchor="eg-baseline" />}} so the next
release starts with current evidence. Chapter four sets out the one class of
material this book has so far avoided: a chapter whose argument is carried by
mathematics rather than by tables.

## References {#references}

[^patroni]: [Patroni documentation: replication and failover parameters](https://patroni.readthedocs.io/en/latest/replication_modes.html). *patroni.readthedocs.io*, retrieved 2026.
[^haproxy]: [HAProxy Configuration Manual: `inter`, `fastinter`, `rise`, `fall`](https://docs.haproxy.org/3.0/configuration.html#5.2-inter). *docs.haproxy.org*, retrieved 2026.
