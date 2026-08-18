---
title: Establish the baseline
description: Start a technical book with visible assumptions and measurable evidence.
book_kind: chapter
book_number: 1
weight: 10
outputs: [HTML, print, markdown]
---

A useful handbook starts with a shared picture of the system and names the facts
that later chapters will rely on.

## Describe the system {#describe-system}

{{< fig num="1-1" id="fig-overview" src="/images/oink.webp" alt="OINK documentation site overview" caption="The documentation shell provides navigation, content, and local context." width="600" height="300" />}}

{{< tbl num="1-1" id="tbl-baseline" caption="A compact baseline for the sample system." >}}
| Surface | Question | Expected result |
| --- | --- | --- |
| Navigation | Can readers find all three chapters? | Yes |
| Content | Are numbered objects linkable? | Yes |
| Output | Do HTML, print, and Markdown agree? | Yes |
{{< /tbl >}}

{{< eq num="1.1" id="eq-coverage" caption="Coverage as verified surfaces over planned surfaces." >}}
C = \frac{V}{P}
{{< /eq >}}

{{< eg num="1-1" id="eg-baseline" caption="Query a small evidence table before publishing." >}}
```sql
SELECT surface, verified
FROM book_evidence
ORDER BY surface;
```
{{< /eg >}}

Together, {{< xref fig="1-1" anchor="fig-overview" />}},
{{< xref tbl="1-1" anchor="tbl-baseline" />}}, and
{{< xref eq="1.1" anchor="eq-coverage" />}} form the baseline. Chapter two turns
that evidence into a release workflow.

## Keep the chapter readable {#keep-readable}

The prose explains why each object exists; the numbered objects make it easy to
refer to the exact evidence from another chapter or output format.
