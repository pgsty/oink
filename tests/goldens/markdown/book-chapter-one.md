# Numbered evidence
> The first chapter carries stable IDs and output-aware labels.
---
LLMS index: [llms.txt](/llms.txt)
---
Forward reference: [Figure 1-1](#office_2003).
Cross-chapter heading: [the stable heading](/book/chapter-two/#stable-heading).
**Figure 1-1.** A stable\, manually numbered figure\.
![OINK mark used as a fixture](/icons/logo.svg)
**Figure 1-2.** A page\-resource bitmap\: the shared resolver supplies intrinsic dimensions and the resource alt\.
![A resolved page\-resource bitmap](/book/chapter-one/diagram.png)
**Figure 1-3.** A page\-resource SVG\: it resolves without error and claims no intrinsic size\.
![A page\-resource SVG\: it resolves without error and claims no intrinsic size\.](/book/chapter-one/vector.svg)
**Table 1-1.** Output behavior by surface\.
| Surface | Label | Anchor |
| --- | --- | --- |
| HTML | Visible | Stable |
| Print | Visible | Stable |
**Equation 1.1.** A direct ToMath escape hatch\.
$$
X \approx \frac{C}{R+Z}
$$
**Example 1-1.** A labeled example stays out of the page outline\.
```sql
SELECT book_number FROM chapters ORDER BY weight;
```
```sql {num="1-2" caption="A native numbered example: one fence plus attributes." #example-native}
SELECT title FROM chapters WHERE book_number = '1';
```
See [Example 1-1](#example-query) and [Example 1-2](#example-native).
- [\@pgsty](https://github.com/pgsty) — Theme fixture
- [\@gohugoio](https://github.com/gohugoio) — Static site generator
- [\@getbootstrap](https://github.com/getbootstrap) — Interface foundation
## Chapter details {#chapter-details}
This heading participates in the depth-three book table of contents.
## Shared heading {#shared-heading}
This deliberately repeated heading ID is page-local outside the aggregate.
