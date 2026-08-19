---
title: Release workflow
description: Turn a reviewed change into a traceable release.
book_kind: chapter
book_number: 2
book_status: draft
weight: 20
outputs: [HTML, print, markdown]
---

> *If it isn't tagged, it didn't ship.*
>
> — Release engineering folklore

Chapter one established the baseline in {{< xref page="chapter-one" fig="1-1" anchor="fig-overview" />}}. This chapter follows the same change through release, and insists on one property throughout: at every point, somebody can name the exact bytes under discussion.

## Make delivery states explicit {#delivery-states}

Local edits, commits, remote delivery, and production rollout are separate states.
Keeping them visible makes a release easier to audit.

{{< fig num="2-1" id="fig-release" src="/images/releasenote.webp" alt="OINK release notes page" caption="A release note connects the shipped artifact to its verification evidence." width="600" height="300" />}}

{{< tbl num="2-1" id="tbl-release" caption="Evidence required at each delivery stage." >}}
| Stage | Evidence | Owner |
| --- | --- | --- |
| Build | Reproducible artifact | Maintainer |
| Publish | Remote checksum | Release engineer |
| Deploy | Running version | Operator |
| Document | A version the reader can pin | Author |
{{< /tbl >}}

The five states below are not synonyms, and a release announcement that conflates
them is the most common way a project loses a reader's trust. A green local build
is none of them.

| State | Reached when | Reversible | Evidence |
| --- | --- | --- | --- |
| Source complete | The change is committed on the release branch | Yes | A commit hash |
| Validated | Every check in the suite passes on that commit [^ci] | Yes | A CI run URL |
| Published | An immutable signed tag resolves through the proxy [^immutable] | **No** | `GOPROXY` returning the version |
| Documented | The consuming site pins the published version | Yes | A diff in `go.mod` |
| Deployed | The pinned version is what readers are served | Yes | A response header |
{#tbl-states num="2-2" caption="Release states, in order. Only one of them cannot be undone."}

The one irreversible row in {{< xref tbl="2-2" anchor="tbl-states" />}} is why
publication happens last and why a mistake becomes a new patch version rather
than a moved tag.

## Write the manifest first {#manifest}

Write down what you intend to ship before shipping it. The manifest is the thing
a later reviewer diffs against reality.

{{< eg num="2-1" id="eg-manifest" caption="Record one immutable release manifest." >}}
```yaml
version: 0.5.0
artifact: oink-0.5.0.tar.gz
sha256: verified
status: staged
```
{{< /eg >}}

Checksums belong beside the artifact, in the format the verifying tool already
reads. Anything that has to be reformatted by hand before it can be checked will
eventually not be checked.

```text {num="2-2" caption="A checksum file in the format sha256sum -c consumes without edits." #eg-checksums}
9d3f0c1c7bd2f9b0a8b9a0f2c7c1c26f1e2ab0d1c4c6ba0d1e0a9f8c7b6a5d4e  oink-0.5.0.tar.gz
1a2b3c4d5e6f708192a3b4c5d6e7f80912a3b4c5d6e7f8091a2b3c4d5e6f70819  oink-0.5.0.zip
```

The tag is the only step that cannot be taken back, so it is the only step this
book shows as a transcript rather than as a file.

```console {num="2-3" caption="Publishing: annotate, sign, push, then verify through the proxy the reader will use." #eg-tag}
$ git tag -s v0.5.0 -m 'oink v0.5.0'
$ git push origin v0.5.0
To github.com:pgsty/oink.git
 * [new tag]         v0.5.0 -> v0.5.0
$ GOPROXY=https://proxy.golang.org go list -m github.com/pgsty/oink@v0.5.0
github.com/pgsty/oink v0.5.0
```

> [!DETAILS] The verification output in full
> ```text
> gpg: Signature made Mon Aug 18 21:04:11 2026 CST
> gpg:                using RSA key 6F2A1C3E7B9D0A45
> gpg: Good signature from "OINK Release <release@example.org>" [ultimate]
> go: downloading github.com/pgsty/oink v0.5.0
> go: verifying github.com/pgsty/oink@v0.5.0: checksum matches
> ```

## Score the readiness {#readiness}

{{< eq num="2.1" id="eq-readiness" caption="A simple release-readiness score." >}}
R = \frac{B + T + D}{3}
{{< /eq >}}

A tag is published once but fetched from many mirrors, and a reader hits
whichever one is nearest. If a mirror carries the version with probability \(p\)
and the client may fall back across \(n\) of them, the version is resolvable with
probability:

$$
P_{\text{resolve}}(n) = 1 - (1 - p)^{n}
$$
{#eq-propagation num="2.2" caption="Probability that at least one of n independent mirrors can already serve the tag."}

The exponent is why "it works for me" is not evidence of publication:
{{< xref eq="2.2" anchor="eq-propagation" />}} is close to 1 for the author, who
has the origin, long before it is close to 1 for a reader who does not.

## Handoff {#handoff}

The manifest in {{< xref eg="2-1" anchor="eg-manifest" />}} and the stages in
{{< xref tbl="2-1" anchor="tbl-release" />}} describe different evidence and
should not be collapsed into one status. Chapter three uses
{{< xref eq="2.1" anchor="eq-readiness" />}} as the input to an operational
review, and re-reads
{{< xref page="chapter-one" tbl="1-2" anchor="tbl-outputs" >}}the output matrix from chapter one{{< /xref >}}
to decide which surfaces that review has to cover.

## References {#references}

[^ci]: [Continuous Delivery: Reliable Software Releases through Build, Test, and Deployment Automation](https://www.oreilly.com/library/view/continuous-delivery-reliable/9780321670250/). Jez Humble and David Farley, Addison-Wesley, 2010.
[^immutable]: [Go Modules Reference: Version queries and the checksum database](https://go.dev/ref/mod#checksum-database). *go.dev*, retrieved 2026.
