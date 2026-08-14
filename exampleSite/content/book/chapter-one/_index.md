---
title: Numbered evidence
description: The first chapter carries stable IDs and output-aware labels.
book_kind: chapter
book_number: 1
weight: 10
outputs: [HTML, print, markdown]
---

Forward reference: {{< xref fig="1-1" anchor="office_2003" />}}.

Cross-chapter heading: {{< xref page="../chapter-two" anchor="stable-heading" >}}the stable heading{{< /xref >}}.

{{< fig num="1-1" id="office_2003" src="/icons/logo.svg" alt="OINK mark used as a fixture" caption="A stable, manually numbered figure." class="fixture-figure" width="120" height="120" />}}

{{< tbl num="1-1" caption="Output behavior by surface." >}}
| Surface | Label | Anchor |
| --- | --- | --- |
| HTML | Visible | Stable |
| Print | Visible | Stable |
{{< /tbl >}}

{{< eq num="1.1" caption="A direct ToMath escape hatch." >}}X \approx \frac{C}{R+Z}{{< /eq >}}

{{< example num="1-1" id="example-query" caption="A labeled example stays out of the page outline." />}}

```sql
SELECT book_number FROM chapters ORDER BY weight;
```

{{< contributors data="contributors" >}}

## Chapter details {#chapter-details}

This heading participates in the depth-three book table of contents.

## Shared heading {#shared-heading}

This deliberately repeated heading ID is page-local outside the aggregate.
