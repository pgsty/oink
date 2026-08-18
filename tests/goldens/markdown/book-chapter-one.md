# Establish the baseline
> Start a technical book with visible assumptions and measurable evidence.
---
LLMS index: [llms.txt](/llms.txt)
---
A useful handbook starts with a shared picture of the system and names the facts
that later chapters will rely on.
## Describe the system {#describe-system}
**Figure 1-1.** The documentation shell provides navigation\, content\, and local context\.
![OINK documentation site overview](/images/oink.webp)
**Table 1-1.** A compact baseline for the sample system\.
| Surface | Question | Expected result |
| --- | --- | --- |
| Navigation | Can readers find all three chapters? | Yes |
| Content | Are numbered objects linkable? | Yes |
| Output | Do HTML, print, and Markdown agree? | Yes |
**Equation 1.1.** Coverage as verified surfaces over planned surfaces\.
$$
C = \frac{V}{P}
$$
**Example 1-1.** Query a small evidence table before publishing\.
```sql
SELECT surface, verified
FROM book_evidence
ORDER BY surface;
```
Together, [Figure 1-1](#fig-overview),
[Table 1-1](#tbl-baseline), and
[Equation 1.1](#eq-coverage) form the baseline. Chapter two turns
that evidence into a release workflow.
## Keep the chapter readable {#keep-readable}
The prose explains why each object exists; the numbered objects make it easy to
refer to the exact evidence from another chapter or output format.
