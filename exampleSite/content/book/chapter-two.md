---
title: Release workflow
description: Turn a reviewed change into a traceable release.
book_kind: chapter
book_number: 2
book_status: draft
weight: 20
outputs: [HTML, print, markdown]
---

Chapter one established the baseline in {{< xref page="chapter-one" fig="1-1" anchor="fig-overview" />}}. This chapter follows the same change through release.

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
{{< /tbl >}}

{{< eq num="2.1" id="eq-readiness" caption="A simple release-readiness score." >}}
R = \frac{B + T + D}{3}
{{< /eq >}}

{{< eg num="2-1" id="eg-manifest" caption="Record one immutable release manifest." >}}
```yaml
version: 0.5.0
artifact: oink-0.5.0.tar.gz
sha256: verified
status: staged
```
{{< /eg >}}

The manifest in {{< xref eg="2-1" anchor="eg-manifest" />}} and the stages in
{{< xref tbl="2-1" anchor="tbl-release" />}} describe different evidence and
should not be collapsed into one status.

## Handoff {#handoff}

Chapter three uses {{< xref eq="2.1" anchor="eq-readiness" />}} as the input to
an operational review.
