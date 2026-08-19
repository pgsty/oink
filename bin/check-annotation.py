#!/usr/bin/env python3
"""Enforce the page-annotation contract.

The annotation's upstream attribution exists to discharge a licence
obligation, so its failure mode matters more than its appearance: a page that
silently omits an attribution looks exactly like a page that never needed one.
Every rule below therefore fails the build rather than degrading.

1. `upstream_link` is the per-page fact and is read from front matter only. A
   cascade counts (that is how a vendored tree is marked), site params do not.
2. Any other `upstream_*` key in front matter without `upstream_link` is an
   error naming `upstream_link`. Because the constants are normally cascaded
   over a whole tree, this makes a page that forgot its source URL fail.
3. `upstream_link: ""` opts one page out of an inherited cascade.
4. With `upstream_link` set, `upstream_name`, `upstream_copyright`,
   `upstream_license`, and `upstream_notice` must all resolve -- from front
   matter, site params, or the `data/upstreams` entry named by
   `upstream_source`, most specific first.
5. `upstream_license` is an SPDX identifier resolved through `data/licenses`;
   an unknown one is an error, not an unlinked string.
6. `upstream_modified` is a boolean. It does not add a line: it changes the
   attribution's verb to "adapted" -- the licence asks for an indication that
   the material was changed, not a second sentence -- and appends a link to
   the page's commit history when the repository is known.
7. `translation_notice` is the authoritative language code (or false) and
   renders only when the page is in another language, that translation exists,
   and the page has authored text of its own. It is the annotation's one
   inferred line, so it carries the guard: a generated taxonomy or term page,
   or a section index that is only a title and a child list, has nothing to be
   a translation of. Being a page key it cascades, so a partly
   translated site scopes the claim instead of declaring it site-wide.

Each case builds a one-page site against the checkout and asserts either the
error fragment or the rendered markup.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]

UPSTREAMS = """\
minio-docs:
  name: minio/docs
  copyright: "© 2020–2026 MinIO, Inc."
  license: CC-BY-4.0
  notice: /about/attribution/
  modified: true
"""

# params fragment shared by the cases that rely on the registry.
REGISTRY_SITE = "github_repo: https://github.com/example/docs\ngithub_branch: main\n"

FULL_PAGE = """\
upstream_link: https://docs.min.io/community/console.html
upstream_name: minio/docs
upstream_copyright: "© 2020–2026 MinIO, Inc."
upstream_license: CC-BY-4.0
upstream_notice: /about/attribution/
upstream_modified: true
"""


class Case:
    """One fixture build: site params, section cascade, page front matter."""

    def __init__(
        self,
        name: str,
        *,
        params: str = "",
        cascade: str = "",
        front: str = "",
        data: bool = False,
        error: str | None = None,
        expect: tuple[str, ...] = (),
        reject: tuple[str, ...] = (),
        languages: bool = False,
        taxonomy: bool = False,
        page_zh: str | None = None,
        target: str = "docs/page",
    ) -> None:
        self.name = name
        self.params = params
        self.cascade = cascade
        self.front = front
        self.data = data
        self.error = error
        self.expect = expect
        self.reject = reject
        self.languages = languages
        self.taxonomy = taxonomy
        self.page_zh = page_zh
        self.target = target


CASES = [
    Case(
        "full-front-matter",
        params=REGISTRY_SITE,
        front=FULL_PAGE,
        expect=(
            'class="td-page-meta__item td-page-meta__upstream"',
            '<a href="https://docs.min.io/community/console.html" target="_blank" rel="noopener">minio/docs</a>',
            '<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>',
            '<a href="/about/attribution/">attribution</a>',
            "https://github.com/example/docs/commits/main/content/docs/page.md",
            "change history",
            "Adapted from",
        ),
    ),
    Case(
        "registry-supplies-constants",
        params=REGISTRY_SITE,
        data=True,
        cascade="  upstream_source: minio-docs\n",
        front="upstream_link: https://docs.min.io/community/console.html\n",
        expect=("minio/docs", "CC BY 4.0", "change history"),
    ),
    Case(
        "front-matter-beats-registry",
        params=REGISTRY_SITE,
        data=True,
        cascade="  upstream_source: minio-docs\n",
        front=(
            "upstream_link: https://docs.min.io/community/console.html\n"
            "upstream_name: minio/docs (console subtree)\n"
            "upstream_modified: false\n"
        ),
        expect=("minio/docs (console subtree)",),
        reject=("change history", "Adapted from"),
    ),
    Case(
        "section-declaring-the-cascade-needs-its-own-link",
        params=REGISTRY_SITE,
        data=True,
        cascade="  upstream_source: minio-docs\n",
        front="upstream_link: https://docs.min.io/community/console.html\n",
        target="docs",
        expect=("td-page-meta__upstream",),
    ),
    Case(
        "cascade-without-link-fails",
        params=REGISTRY_SITE,
        data=True,
        cascade="  upstream_source: minio-docs\n",
        front="",
        error="needs upstream_link",
    ),
    Case(
        "empty-link-opts-out",
        params=REGISTRY_SITE,
        data=True,
        cascade="  upstream_source: minio-docs\n",
        front='upstream_link: ""\n',
        reject=("td-page-meta__upstream",),
    ),
    Case(
        "modified-without-link-fails",
        front="upstream_modified: true\n",
        error="upstream_modified needs upstream_link",
    ),
    Case(
        "incomplete-attribution-fails",
        front="upstream_link: https://docs.min.io/community/console.html\n",
        error="upstream_link needs upstream_name",
    ),
    Case(
        "unknown-license-fails",
        front=FULL_PAGE.replace("CC-BY-4.0", "CC-BY4.0"),
        error='upstream_license "CC-BY4.0" is not in data/licenses',
    ),
    Case(
        "unknown-registry-entry-fails",
        front=(
            "upstream_link: https://docs.min.io/community/console.html\n"
            "upstream_source: not-a-key\n"
        ),
        error='upstream_source "not-a-key" has no entry',
    ),
    Case(
        "non-boolean-modified-fails",
        front=FULL_PAGE.replace("upstream_modified: true", 'upstream_modified: "yes"'),
        error="upstream_modified must be a boolean",
    ),
    Case(
        "site-params-supply-constants",
        params=(
            REGISTRY_SITE
            + "upstream_name: minio/docs\n"
            + 'upstream_copyright: "© 2020–2026 MinIO, Inc."\n'
            + "upstream_license: CC-BY-4.0\n"
            + "upstream_notice: /about/attribution/\n"
        ),
        front="upstream_link: https://docs.min.io/community/console.html\n",
        expect=("minio/docs", "CC BY 4.0"),
    ),
    Case(
        "site-params-alone-do-not-force-a-link",
        params=(
            REGISTRY_SITE
            + "upstream_name: minio/docs\n"
            + "upstream_license: CC-BY-4.0\n"
        ),
        front="",
        reject=("td-page-meta__upstream",),
    ),
    Case(
        "translation-notice",
        params="ui:\n  translation_notice: en\n",
        languages=True,
        front="",
        page_zh="",
        target="zh/docs/page",
        expect=(
            'class="td-page-meta__item td-page-meta__translation"',
            '<a href="/docs/page/">原文</a>',
        ),
    ),
    Case(
        "translation-notice-skips-the-authority",
        params="ui:\n  translation_notice: en\n",
        languages=True,
        front="",
        page_zh="",
        target="docs/page",
        reject=("td-page-meta__translation",),
    ),
    Case(
        "translation-notice-skips-generated-pages",
        params="ui:\n  translation_notice: en\n",
        languages=True,
        taxonomy=True,
        front="",
        page_zh="",
        target="zh/tags/demo",
        reject=("td-page-meta__translation",),
    ),
    Case(
        "translation-notice-skips-empty-pages",
        params="ui:\n  translation_notice: en\n",
        languages=True,
        front="",
        page_zh="",
        target="zh/docs/stub",
        reject=("td-page-meta__translation",),
    ),
    Case(
        "translation-notice-cascades",
        cascade="  translation_notice: en\n",
        languages=True,
        front="",
        page_zh="",
        target="zh/docs/page",
        expect=("td-page-meta__translation",),
    ),
    Case(
        "translation-notice-page-opt-out",
        params="ui:\n  translation_notice: en\n",
        languages=True,
        front="",
        page_zh="translation_notice: false\n",
        target="zh/docs/page",
        reject=("td-page-meta__translation",),
    ),
]


LANGUAGES = """\
defaultContentLanguage: en
defaultContentLanguageInSubdir: false
languages:
  en:
    weight: 1
  zh:
    weight: 2
"""


def site_config(case: Case) -> str:
    indented = "\n".join(f"  {line}" if line else line for line in case.params.splitlines())
    return (
        "baseURL: https://example.org/\n"
        "title: Downstream Docs\n"
        f"theme: {ROOT.name}\n"
        "disableKinds: [RSS, sitemap, taxonomy, term]\n"
        + (LANGUAGES if case.languages else "")
        + ("params:\n" + indented + "\n" if case.params.strip() else "")
    )


def build(hugo: str, case: Case) -> tuple[str, str]:
    """Return (build output on failure, rendered target page)."""
    with tempfile.TemporaryDirectory(prefix=f"oink-annotation-{case.name}-") as temp:
        source = Path(temp)
        (source / "content/docs").mkdir(parents=True)
        (source / "hugo.yaml").write_text(site_config(case), encoding="utf-8")
        if case.data:
            (source / "data").mkdir()
            (source / "data/upstreams.yaml").write_text(UPSTREAMS, encoding="utf-8")
        # Only an upstream cascade obliges the section page to name its own source.
        section_link = "upstream_link: https://docs.min.io/community/\n" if "upstream" in case.cascade else ""
        (source / "content/docs/_index.md").write_text(
            "---\ntitle: Docs\n"
            + section_link
            + (f"cascade:\n{case.cascade}" if case.cascade else "")
            + "---\n\nSection.\n",
            encoding="utf-8",
        )
        tags = "tags: [demo]\n" if case.taxonomy else ""
        (source / "content/docs/page.md").write_text(
            f"---\ntitle: Page\n{tags}{case.front}---\n\nBody.\n", encoding="utf-8"
        )
        if case.languages:
            (source / "content/docs/_index.zh.md").write_text(
                "---\ntitle: 文档\n"
                + section_link
                + (f"cascade:\n{case.cascade}" if case.cascade else "")
                + "---\n\n段落。\n",
                encoding="utf-8",
            )
            (source / "content/docs/page.zh.md").write_text(
                f"---\ntitle: 页面\n{tags}{case.page_zh or ''}---\n\n正文。\n", encoding="utf-8"
            )
            # A translated pair that carries no body of its own.
            (source / "content/docs/stub.md").write_text("---\ntitle: Stub\n---\n", encoding="utf-8")
            (source / "content/docs/stub.zh.md").write_text("---\ntitle: 空页\n---\n", encoding="utf-8")
        result = subprocess.run(
            [
                hugo,
                "--source", str(source),
                "--themesDir", str(ROOT.parent),
                "--destination", str(source / "public"),
                "--logLevel", "warn",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return (result.stdout + result.stderr) or "build failed without output", ""
        rendered = source / "public" / case.target / "index.html"
        if not rendered.exists():
            return "", f"MISSING {case.target}"
        return "", rendered.read_text(encoding="utf-8")


def annotation(html: str) -> str:
    match = re.search(r'<section class="td-page-annotation".*?</section>', html, re.S)
    return match.group(0) if match else ""


def check_source() -> list[str]:
    """The resolver must stay the single place the lines are decided."""
    errors: list[str] = []
    items = (ROOT / "layouts/_partials/annotation-items.html").read_text(encoding="utf-8")
    render = (ROOT / "layouts/_partials/page-meta-lastmod.html").read_text(encoding="utf-8")
    wrapper = (ROOT / "layouts/_partials/page-annotation.html").read_text(encoding="utf-8")
    if 'partial "annotation-items.html"' not in render:
        errors.append("page-meta-lastmod.html no longer renders the resolved items")
    if 'partial "annotation-items.html"' not in wrapper:
        errors.append("page-annotation.html no longer gates on the resolved items")
    if "upstream_link" not in items:
        errors.append("annotation-items.html no longer reads upstream_link")
    licences = (ROOT / "data/licenses.yaml").read_text(encoding="utf-8")
    for spdx in ("CC-BY-4.0", "GPL-2.0-only", "PostgreSQL", "Apache-2.0", "MIT"):
        if f"\n{spdx}:" not in licences:
            errors.append(f"data/licenses.yaml lost {spdx}")
    mounts = (ROOT / "hugo.yaml").read_text(encoding="utf-8")
    if "source: data" not in mounts:
        errors.append("hugo.yaml stopped mounting data/, so the licence table would not reach a site")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors = check_source()

    def run(case: Case) -> tuple[Case, tuple[str, str]]:
        return case, build(args.hugo, case)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for case, (failure, html) in pool.map(run, CASES):
            if case.error is not None:
                if not failure:
                    errors.append(f"{case.name}: built without an error")
                elif case.error not in failure:
                    errors.append(f"{case.name}: error did not say {case.error!r}: {failure[-400:]}")
                continue
            if failure:
                errors.append(f"{case.name}: expected a clean build: {failure[-400:]}")
                continue
            block = annotation(html)
            for fragment in case.expect:
                if fragment not in block:
                    errors.append(f"{case.name}: annotation missing {fragment!r}: {block or '(no annotation)'}")
            for fragment in case.reject:
                if fragment in block:
                    errors.append(f"{case.name}: annotation should not contain {fragment!r}")

    if errors:
        print("Annotation contract check failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"Annotation contract check passed ({len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
