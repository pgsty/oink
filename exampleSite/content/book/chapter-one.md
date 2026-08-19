---
title: Establish the baseline
description: Start a technical book with visible assumptions and measurable evidence.
book_kind: chapter
book_number: 1
weight: 10
outputs: [HTML, print, markdown]
---

> *Documentation is a love letter that you write to your future self.*
>
> — Damian Conway, *Perl Best Practices* (2005)

A useful handbook starts with a shared picture of the system and names the facts
that later chapters will rely on. A baseline is not an introduction. An
introduction says what a book is about; a baseline says what the book will treat
as true from here on. Every later chapter may assume it silently, and any claim
that contradicts it has to say so out loud.[^conway]

## Describe the system {#describe-system}

Describe what a reader can see before describing what they cannot. The shell of
a documentation site is three regions — navigation, content, and local context —
and almost every question about a page turns out to be a question about which
region should have answered it.

{{< fig num="1-1" id="fig-overview" src="/images/oink.webp" alt="OINK documentation site overview" caption="The documentation shell provides navigation, content, and local context." width="600" height="300" />}}

The artifact a release produces is a second, narrower surface: one page per
version, generated from the same content pipeline as the rest of the book.
{{< xref fig="1-2" anchor="fig-artifact" />}} is that page, and chapter two
follows the change that produced it.

![A release note page listing version, date, and published assets](/images/releasenote.webp)
{#fig-artifact num="1-2" caption="A release note is the narrowest surface in the system: one page, one version, no navigation of its own." width="600" height="300"}

> [!TIP] Terminology: surface, evidence, claim
>
> A **surface** is anything a reader can reach: a rendered page, a printed
> sheet, an RSS item, a Markdown file served to a language model. Surfaces are
> counted, not described — a book that says "the site works" has not said which
> of them was checked.
>
> **Evidence** is a value someone can recompute: the exit status of a build, the
> number of broken links, a checksum. A **claim** is a sentence in the prose. This
> book only makes claims that name their evidence, which is why the numbered
> tables carry queries rather than adjectives.

## Agree on the evidence {#agree-evidence}

Two readers disagree about whether a site is finished because they are counting
different things. Write the count down first.

{{< tbl num="1-1" id="tbl-baseline" caption="A compact baseline for the sample system." >}}
| Surface | Question | Expected result |
| --- | --- | --- |
| Navigation | Can readers find all four chapters? | Yes |
| Content | Are numbered objects linkable? | Yes |
| Output | Do HTML, print, and Markdown agree? | Yes |
| Search | Does every chapter carry its own keywords? | Yes |
{{< /tbl >}}

The same four surfaces are produced by different code paths and therefore fail
in different ways. A table that records how each one is verified is worth more
than a paragraph promising that all of them are.

| Output | Emitted by | Verified against | Fails the build on |
| --- | --- | --- | --- |
| HTML | The page layouts | A parsed DOM: no duplicate IDs, one bundle per feature set [^goldens] | An unknown fence attribute |
| Print | `layouts/**/*.print.html` | The same DOM with interactive affordances removed [^print] | An expanded disclosure that stayed closed |
| Markdown | `layouts/all.md` | A byte-comparison against a stored golden [^goldens] | Any HTML that leaked into the text |
| RSS | The feed template | The Markdown rules, minus page-local links | An unresolvable relative link |
{#tbl-outputs num="1-2" caption="What each output state is checked against, and what makes it fail."}

Note that {{< xref tbl="1-2" anchor="tbl-outputs" />}} names a file for every
row. A row without a file is a hope, not a check.

## Show the evidence {#show-evidence}

A numbered example is a listing the prose can point at. Keep it short enough to
read in one screen and real enough to run.

{{< eg num="1-1" id="eg-baseline" caption="Query a small evidence table before publishing." >}}
```sql
SELECT surface, verified
FROM book_evidence
ORDER BY surface;
```
{{< /eg >}}

The inventory that feeds that table is checked into the repository next to the
content, so a reviewer can see the claim and its input in one diff.

```yaml {num="1-2" caption="The inventory a baseline is computed from — four surfaces, one owner each." #eg-inventory}
surfaces:
  - name: navigation
    owner: shell
    checked_by: bin/check-navigation-contract.py
  - name: content
    owner: markup
    checked_by: bin/check-content-primitives.py
  - name: output
    owner: layouts
    checked_by: bin/check-goldens.py
  - name: search
    owner: search
    checked_by: bin/check-search.py
```

## Measure the coverage {#measure-coverage}

Coverage is the one number this book quotes without qualification, because it is
the one number whose inputs are both written down.

{{< eq num="1.1" id="eq-coverage" caption="Coverage as verified surfaces over planned surfaces." >}}
C = \frac{V}{P}
{{< /eq >}}

A single ratio hides how much of it rests on one lucky build. Weight each
surface by how often it is exercised and the number stops flattering the parts
nobody looks at.

$$
C_{w} = \frac{\sum_{i=1}^{n} w_i v_i}{\sum_{i=1}^{n} w_i},
\qquad w_i = \log_{2}\left(1 + r_i\right)
$$
{#eq-weighted num="1.2" caption="Weighted coverage, where r is how many times per week surface i is rebuilt."}

With \(v_i \in \{0, 1\}\) and \(r_i\) the weekly rebuild count,
{{< xref eq="1.2" anchor="eq-weighted" />}} reduces to
{{< xref eq="1.1" anchor="eq-coverage" />}} when every surface is rebuilt equally
often. The gap between the two numbers is the part of the site that is only
checked by accident.

## Keep the chapter readable {#keep-readable}

The prose explains why each object exists; the numbered objects make it easy to
refer to the exact evidence from another chapter or output format. Together,
{{< xref fig="1-1" anchor="fig-overview" />}},
{{< xref tbl="1-1" anchor="tbl-baseline" />}}, and
{{< xref eq="1.1" anchor="eq-coverage" />}} form the baseline. Chapter two turns
that evidence into a release workflow.

## References {#references}

[^conway]: Damian Conway. *Perl Best Practices*. O'Reilly Media, July 2005. ISBN 978-0-596-00173-5.
[^goldens]: [Golden testing](https://ro-che.info/articles/2017-12-04-golden-tests). *ro-che.info*, December 2017.
[^print]: [Designing for print with CSS Paged Media](https://www.w3.org/TR/css-page-3/). W3C Working Draft, *w3.org*, October 2018.
