---
title: Operate and review
description: Close the loop with observable service goals and a repeatable review.
book_kind: chapter
book_number: 3
weight: 30
outputs: [HTML, print, markdown]
---

A release is complete only after the running system is observed. Start with the
readiness measure in {{< xref page="chapter-two" eq="2.1" anchor="eq-readiness" />}}
and compare it with operational evidence.

## Observe the result {#observe-result}

{{< fig num="3-1" id="fig-operations" src="/images/oink.webp" alt="OINK documentation site after publication" caption="The published site is checked as a reader sees it." width="600" height="300" />}}

{{< tbl num="3-1" id="tbl-operations" caption="Signals used in the final review." >}}
| Signal | Target | Review cadence |
| --- | --- | --- |
| Availability | 99.9% | Daily |
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

## Close the loop {#close-loop}

Feed the review back into the baseline from
{{< xref page="chapter-one" eg="1-1" anchor="eg-baseline" />}} so the next
release starts with current evidence.
