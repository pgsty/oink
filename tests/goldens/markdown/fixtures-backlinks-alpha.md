# Alpha
LLMS index: [llms.txt](/llms.txt)
---
Alpha links its siblings every way authors actually write links: a relative
link to [Beta](beta), an absolute link to [Gamma](/fixtures/backlinks/gamma/),
a fragment-carrying repeat of [Beta again](beta#part), a self link to
[Alpha](/fixtures/backlinks/alpha/), an external link to
[nowhere](https://example.com/nothing), a same-page anchor to
[the heading](#part), and a shortcode reference to
[Quiet](/fixtures/backlinks/quiet/).
Links inside code never become edges:
```markdown
[Delta](delta)
```
Nor does inline code such as `[Delta](delta)`.
## A heading {#part}
The fragment above resolves here.
---
Backlinks:
- [Beta](/fixtures/backlinks/beta/)
