"""Freeze the OINK 0.6 migration toolkit: before/after fixtures per transformation,
idempotency, fence safety, indentation, and the dry-run-first CLI.

    python3 -m unittest discover -s tests/migrations -t .
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "migrations"))

from oink06.cli import migrate_text, residual_findings  # noqa: E402
from oink06.transforms import load  # noqa: E402

CLI = ROOT / "scripts" / "migrations" / "oink06.py"


def run(text: str, only: list[str] | None = None):
    final, counts, findings = migrate_text("t.md", textwrap.dedent(text), load(only))
    return final, counts, findings


class TransformationCase(unittest.TestCase):
    maxDiff = None

    def assertMigrates(self, before: str, after: str, only: list[str] | None = None, findings: int = 0):
        final, counts, found = run(before, only)
        self.assertEqual(final, textwrap.dedent(after))
        self.assertEqual(len(found), findings, [f.__dict__ for f in found])
        # idempotent
        second, _, _ = migrate_text("t.md", final, load(only))
        self.assertEqual(second, final, "second run must not change the text")
        return counts, found

    # -- callout ---------------------------------------------------------------
    def test_alert_to_callout(self):
        counts, _ = self.assertMigrates(
            """\
            Intro.
            {{% alert title="Note" color="info" %}}
            Body **bold**.

            second para
            {{% /alert %}}
            Next paragraph.
            """,
            """\
            Intro.

            > [!NOTE] Note
            > Body **bold**.
            >
            > second para

            Next paragraph.
            """,
            ["callout"],
        )
        self.assertEqual(counts["alert"], 1)
        self.assertEqual(counts["alert.color.info"], 1)

    def test_alert_default_color_and_one_liner(self):
        self.assertMigrates(
            """\
            {{% alert title="Enterprise" %}}{{% /alert %}}

            {{% alert color="danger" %}}danger text{{% /alert %}}
            """,
            """\
            > [!IMPORTANT] Enterprise

            > [!CAUTION]
            > danger text
            """,
            ["callout"],
        )

    def test_nested_alert_and_details(self):
        self.assertMigrates(
            """\
            {{% alert color="warning" %}}
            outer
            {{% alert color="success" %}}
            inner
            {{% /alert %}}
            {{% /alert %}}

            {{% details title="Output" closed=false %}}

            ```console {filename="x"}
            $ ls
            ```

            {{% /details %}}

            {{% td-page-notice %}}
            info
            {{% /td-page-notice %}}
            """,
            """\
            > [!WARNING]
            > outer
            >
            > > [!TIP]
            > > inner

            > [!DETAILS]+ Output
            > ```console {title="x"}
            > $ ls
            > ```

            > [!NOTE]
            > info
            """,
        )

    def test_alert_inside_list_item_keeps_indentation(self):
        self.assertMigrates(
            """\
            - item
               {{% alert color="info" %}}
               nested list alert

               second para
               {{% /alert %}}
            - item2
            """,
            """\
            - item
               > [!NOTE]
               > nested list alert
               >
               > second para
            - item2
            """,
            ["callout"],
        )

    def test_alert_inside_blockquote(self):
        self.assertMigrates(
            """\
            > Definition.
            >
            > {{% alert color="info" %}}
            > **Exclusive**
            >
            > body
            > {{% /alert %}}
            > More text.
            """,
            """\
            > Definition.
            >
            > > [!NOTE]
            > > **Exclusive**
            > >
            > > body
            >
            > More text.
            """,
            ["callout"],
        )

    def test_raw_details(self):
        counts, _ = self.assertMigrates(
            """\
            <details>
            <summary><code>oink</code> scorecard</summary>

            | a | b |
            |---|---|
            | <kbd>x</kbd> | y |

            </details>

            <details open>
            <summary>Open one</summary>

            text

            </details>

            <details>
            <summary>Nested block</summary>
            <div>html</div>
            </details>
            """,
            """\
            > [!DETAILS]- `oink` scorecard
            > | a | b |
            > |---|---|
            > | <kbd>x</kbd> | y |

            > [!DETAILS]+ Open one
            > text

            <details>
            <summary>Nested block</summary>
            <div>html</div>
            </details>
            """,
            ["callout"],
            findings=1,
        )
        self.assertEqual(counts["rawdetails"], 2)

    def test_corpus_forms_one_line_details_filetree_tabs_carousel(self):
        counts, found = self.assertMigrates(
            """\
            <details><summary>Pigsty Home Dashboard</summary>

            [![pigsty.jpg](/img/dashboard/pigsty.jpg)](https://demo.pigsty.cc/d/pigsty/)

            </details>

            <details><br>

            **New**

            * item
            </details>

            {{< filetree >}} {{< filetree/folder name="content" open=true >}}
              {{< filetree/folder name="pkg" >}}{{< /filetree/folder >}}
              {{< filetree/file name="a.md" >}}
            {{< /filetree/folder >}}
            {{< /filetree >}}

            {{< tabpane text=true persist=header >}}
            {{% tab header="hugo.yaml" %}}
            ```yaml
            a: 1
            ```
            {{% /tab %}} {{% tab header="hugo.toml" %}}
            ```toml
            a = 1
            ```
            {{% /tab %}}
            {{< /tabpane >}}

            {{< doc-carousel >}}
            {{< doc-card title="A" image="/a.svg" alt="A img" >}}
            Text A.
            {{< /doc-card >}}
            {{< /doc-carousel >}}
            """,
            """\
            > [!DETAILS]- Pigsty Home Dashboard
            > [![pigsty.jpg](/img/dashboard/pigsty.jpg)](https://demo.pigsty.cc/d/pigsty/)

            > [!DETAILS]-
            > **New**
            >
            > * item

            ```filetree
            - content/
              - pkg/   {open=false}
              - a.md
            ```

            ```yaml {tab="hugo.yaml" group="hugoyaml-hugotoml" value="hugoyaml"}
            a: 1
            ```

            ```toml {tab="hugo.toml" value="hugotoml"}
            a = 1
            ```

            {{< cards >}}
            {{< card title="A" image="/a.svg" image_alt="A img" >}}
            Text A.
            {{< /card >}}
            {{< /cards >}}
            """,
        )
        self.assertEqual(counts["rawdetails"], 2)
        self.assertEqual(counts["cards.carousel_flattened"], 1)

    # -- fence safety ----------------------------------------------------------
    def test_legacy_syntax_inside_fences_is_untouched(self):
        source = """\
            Doc.

            ```markdown
            {{% alert color="info" %}}
            inside a fence
            {{% /alert %}}
            {{< tabpane >}}
            {{< filetree >}}
            <details><summary>x</summary></details>
            ```

            ~~~go-html-template
            {{< readfile "x" >}}
            ~~~

            > ```text
            > {{< echarts >}}
            > ```
            """
        final, counts, findings = run(source)
        self.assertEqual(final, textwrap.dedent(source))
        self.assertEqual(sum(counts.values()), 0)
        self.assertEqual(findings, [])
        self.assertEqual(residual_findings("t.md", final), [])

    # -- tabs ------------------------------------------------------------------
    def test_code_only_tabpane_to_adjacent_fences(self):
        counts, _ = self.assertMigrates(
            """\
            Intro.

            {{< tabpane text=true persist=header >}}
            {{% tab header="Homebrew" %}}
            ```bash
            brew install pigsty
            ```
            {{% /tab %}}
            {{% tab header="APT" %}}
            ```bash {filename="x.sh"}
            sudo apt install pigsty
            ```
            {{% /tab %}}
            {{< /tabpane >}}
            After.
            """,
            """\
            Intro.

            ```bash {tab="Homebrew" group="homebrew-apt" value="homebrew"}
            brew install pigsty
            ```

            ```bash {title="x.sh" tab="APT" value="apt"}
            sudo apt install pigsty
            ```

            After.
            """,
        )
        self.assertEqual(counts["tabpane.code_only"], 1)
        self.assertEqual(counts["tabpane.grouped"], 1)

    def test_raw_code_tabs_and_disabled_label_tab(self):
        counts, _ = self.assertMigrates(
            """\
            {{< tabpane persist="disabled" >}}
            {{< tab header="Config file:" disabled=true />}}
            {{< tab header="hugo.toml" lang="toml" >}}
            [outputs]
            section = [ "HTML" ]
            {{< /tab >}}
            {{< tab header="hugo.yaml" lang="yaml" >}}
            outputs:
              section: [HTML]
            {{< /tab >}}
            {{< /tabpane >}}
            """,
            """\
            ```toml {tab="hugo.toml"}
            [outputs]
            section = [ "HTML" ]
            ```

            ```yaml {tab="hugo.yaml"}
            outputs:
              section: [HTML]
            ```
            """,
            ["tabs"],
        )
        self.assertEqual(counts["tabs.disabled_tab_dropped"], 1)
        self.assertNotIn("tabpane.grouped", counts)

    def test_prose_tabpane_to_full_form(self):
        counts, _ = self.assertMigrates(
            """\
            {{< tabpane text=true persist=header >}}
            {{% tab header="环境变量" selected=true %}}
            ###### `MINIO_X` {#envvar.MINIO_X}

            Body para.
            {{% /tab %}}
            {{% tab header="配置项" %}}
            {{% alert color="info" %}}
            note
            {{% /alert %}}
            {{% /tab %}}
            {{< /tabpane >}}
            """,
            """\
            {{< tabs group="tab1-tab2" default="tab1" >}}
            {{< tab label="环境变量" value="tab1" >}}
            ###### `MINIO_X` {#envvar.MINIO_X}

            Body para.
            {{< /tab >}}
            {{< tab label="配置项" value="tab2" >}}
            > [!NOTE]
            > note
            {{< /tab >}}
            {{< /tabs >}}
            """,
        )
        self.assertEqual(counts["tabpane.headings"], 1)
        self.assertEqual(counts["alert"], 1)

    def test_indented_tabpanes(self):
        # code_only inside a list item is re-indented; prose inside a list item becomes an indented {{< tabs >}}
        counts, found = self.assertMigrates(
            """\
            1. Step

                {{< tabpane >}}
            {{< tab header="hugo.toml" lang="toml" >}}
            [deployment]
            {{< /tab >}}
            {{< tab header="hugo.yaml" lang="yaml" >}}
            deployment: x
            {{< /tab >}}
                {{< /tabpane >}}

            2. Step two

               {{< tabpane text=true persist=header >}}
               {{% tab header="A" %}}
               prose

               more
               {{% /tab %}}
               {{% tab header="B" %}}
               other
               {{% /tab %}}
               {{< /tabpane >}}
            """,
            """\
            1. Step

                ```toml {tab="hugo.toml" group="hugotoml-hugoyaml" value="hugotoml"}
                [deployment]
                ```

                ```yaml {tab="hugo.yaml" value="hugoyaml"}
                deployment: x
                ```

            2. Step two

               {{< tabs group="a-b" >}}
               {{< tab label="A" value="a" >}}
               prose

               more
               {{< /tab >}}
               {{< tab label="B" value="b" >}}
               other
               {{< /tab >}}
               {{< /tabs >}}
            """,
            ["tabs"],
        )
        self.assertEqual(counts["tabpane.indented_prose"], 1)

    def test_nested_tabpanes_innermost_first(self):
        final, counts, findings = run(
            """\
            {{< tabpane text=true persist=header >}}
            {{% tab header="Outer" %}}
            Intro

            {{< tabpane text=true persist=header >}}
            {{% tab header="In1" %}}
            ```bash
            echo 1
            ```
            {{% /tab %}}
            {{% tab header="In2" %}}
            ```bash
            echo 2
            ```
            {{% /tab %}}
            {{< /tabpane >}}
            {{% /tab %}}
            {{% tab header="Other" %}}
            text
            {{% /tab %}}
            {{< /tabpane >}}
            """,
            ["tabs"],
        )
        self.assertEqual(findings, [])
        self.assertEqual(counts["tabpane"], 2)
        self.assertIn('```bash {tab="In1" group="in1-in2" value="in1"}', final)
        self.assertIn('{{< tabs group="outer-other" >}}', final)

    def test_code_group_to_fences(self):
        self.assertMigrates(
            """\
            {{< code-group id="install" sync="mirror" persist=true copy="all" >}}
              {{< code-tab title="npm" value="npm" lang="bash" selected=true >}}
            npm i
              {{< /code-tab >}}
              {{< code-tab title="pnpm" value="pnpm" lang="bash" collapse=3 >}}
            pnpm i
              {{< /code-tab >}}
            {{< /code-group >}}
            """,
            """\
            ```bash {tab="npm" group="mirror" value="npm" copy="all"}
            npm i
            ```

            ```bash {tab="pnpm" value="pnpm" copy="all" collapse=3}
            pnpm i
            ```
            """,
            ["tabs"],
        )

    # -- filetree / gallery ------------------------------------------------------
    def test_filetree_to_fence(self):
        counts, _ = self.assertMigrates(
            """\
            {{< filetree label="Files" >}}
              {{< filetree/folder name="content" open=true comment="0755" >}}
                {{< filetree/file name="_index.md" icon="fa-solid fa-file" color="primary" comment="landing" >}}
                {{< filetree/folder name="docs" >}}
                  {{< filetree/file name="a.md" link="/docs/a/" >}}
                {{< /filetree/folder >}}
              {{< /filetree/folder >}}
              {{< filetree/file name="hugo.yaml" >}}
            {{< /filetree >}}
            """,
            """\
            ```filetree {title="Files"}
            - content/      # 0755
              - _index.md   # landing   {icon="fa-solid fa-file" tone=info}
              - docs/   {open=false}
                - [a.md](/docs/a/)
            - hugo.yaml
            ```
            """,
            ["filetree"],
        )
        self.assertEqual(counts["filetree.title"], 1)
        self.assertEqual(counts["filetree.nodes"], 5)
        self.assertEqual(counts["filetree.open"], 1)
        self.assertEqual(counts["filetree.icon"], 1)
        self.assertEqual(counts["filetree.tone"], 1)
        self.assertEqual(counts["filetree.tone_mapped"], 1)
        self.assertEqual(counts["filetree.link"], 1)
        self.assertEqual(counts["filetree.comment"], 2)

    def test_filetree_list_to_fence(self):
        counts, _ = self.assertMigrates(
            """\
            Intro.

            - content/ — 0755 root:root · Site content
              - _index.md — *landing*
              - docs/
                - [`a.md`](/docs/a/) — 0644
              - logs/
            - hugo.yaml — **root:root 0644**
            - `README.md`
            - \\*.yml
            {.filetree}
            After.
            """,
            """\
            Intro.

            ```filetree
            - content/               # 0755 root:root · Site content
              - _index.md            # landing
              - docs/
                - [a.md](/docs/a/)   # 0644
              - logs/
            - hugo.yaml              # root:root 0644
            - README.md
            - *.yml
            ```

            After.
            """,
            ["filetree"],
        )
        self.assertEqual(counts["filetree.list"], 1)
        self.assertEqual(counts["filetree.nodes"], 8)

    def test_filetree_list_inside_list_item_and_odd_dedent(self):
        _, found = self.assertMigrates(
            """\
            - a/
                - deep
              - odd
            {.filetree}
            """,
            """\
            - a/
                - deep
              - odd
            {.filetree}
            """,
            ["filetree"],
            findings=1,
        )
        self.assertIn("unknown level", found[0].reason)

    def test_gallery_to_fence(self):
        self.assertMigrates(
            """\
            {{< gallery columns=3 label="x" >}}
              {{< gallery/image src="a.webp" alt="A" caption="cap a" >}}
              {{< gallery/image src="/b.png" alt="B" >}}
            {{< /gallery >}}
            """,
            """\
            ```gallery
            ![A](a.webp) # cap a
            ![B](/b.png)
            ```
            """,
            ["gallery"],
        )

    def test_gallery_list_marker_to_fence(self):
        """The interim {.gallery} list becomes the fence; ` — ` becomes `#`."""
        self.assertMigrates(
            """\
            - ![A](a.webp) — cap a
            - ![B](/b.png)
            - ![C](c.png) — issue #42
            {.gallery}
            """,
            """\
            ```gallery
            ![A](a.webp) # cap a
            ![B](/b.png)
            ![C](c.png) # issue \\#42
            ```
            """,
            ["gallery"],
        )

    def test_gallery_list_without_alt_is_reported(self):
        source = """\
            - ![](a.webp) — no alt
            {.gallery}
            """
        final, _, findings = run(source, ["gallery"])
        self.assertEqual(final, textwrap.dedent(source))
        self.assertEqual(len(findings), 1)

    def test_gallery_without_alt_is_reported(self):
        source = """\
            {{< gallery >}}
              {{< gallery/image src="a.webp" alt="" >}}
            {{< /gallery >}}
            """
        final, _, findings = run(source, ["gallery"])
        self.assertEqual(final, textwrap.dedent(source))
        self.assertEqual(len(findings), 1)

    # -- data fences -----------------------------------------------------------
    def test_echarts_and_infographic_fences(self):
        self.assertMigrates(
            """\
            {{< echarts height="300px" >}}
            ```yaml
            series: [{type: bar}]
            ```
            {{< /echarts >}}

            {{< infographic >}}
            infographic list
            data
              title X
            {{< /infographic >}}
            """,
            """\
            ```echarts {height="300px"}
            series: [{type: bar}]
            ```

            ```infographic
            infographic list
            data
              title X
            ```
            """,
            ["datafence"],
        )

    def test_echarts_with_js_subfence_inlines_callbacks(self):
        counts, _ = self.assertMigrates(
            """\
            {{< echarts height="820px" >}}
            ```js
            var fnum = function(n) { return n; };
            function tip(p) { return p; }
            ```
            ```yaml
            tooltip:
              formatter: $fn:tip
            ```
            {{< /echarts >}}
            """,
            """\
            <script>
            window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
            (function (registry) {
            var fnum = function(n) { return n; };
            function tip(p) { return p; }
            registry["fnum"] = fnum;
            registry["tip"] = tip;
            })(window.OinkEchartsFunctions);
            </script>

            ```echarts {height="820px"}
            tooltip:
              formatter: $fn:tip
            ```
            """,
            ["datafence"],
        )
        self.assertEqual(counts["echarts.callbacks_inlined"], 1)

    def test_echarts_js_without_options_or_two_js_fences_is_reported(self):
        source = """\
            {{< echarts height="300px" >}}
            ```js
            function f() {}
            ```
            {{< /echarts >}}

            {{< echarts height="300px" >}}
            ```js
            var a = 1;
            ```
            ```js
            var b = 2;
            ```
            series: []
            {{< /echarts >}}
            """
        final, _, findings = run(source, ["datafence"])
        self.assertEqual(final, textwrap.dedent(source))
        self.assertEqual(len(findings), 2)

    def test_param_placeholders_and_highlight_card(self):
        counts, found = self.assertMigrates(
            """\
            {{% card header="Highlights" %}}

            - {{% _param FAS_LG robot info %}} <span>**Agent**</span>
            - {{% _param FAS_LG diagram-project success %}} x

            {{% /card %}}

            Text {{% _param BREAKING %}} {{% _param NEW %}} {{% _param CLEANUP %}} {{% _param FAS globe "" %}}
            {{%_param BADGE EXPERIMENTAL info %}} {{% _param BADGE X secondary %}} {{% _param hugoMinVersion %}}
            {{% _param FA regular file info %}} {{% _param FAS rocket primary %}} {{% _param WEIRD %}}

            {{< cardpane >}}
            {{< card header="[**Pigsty**](https://github.com/pgsty/pigsty)" >}}
            body
            {{< /card >}}
            {{< /cardpane >}}
            """,
            """\
            > [!NOTE] Highlights
            > - <i class="fa-solid fa-robot text-info fa-lg"></i> <span>**Agent**</span>
            > - <i class="fa-solid fa-diagram-project text-success fa-lg"></i> x

            Text <i class="fa-solid fa-triangle-exclamation fa-lg text-warning px-1"></i> <i class="fa-regular fa-square-check fa-lg text-success px-1"></i> <i class="fa-regular fa-wand-magic-sparkles fa-lg text-info px-1"></i> <i class="fa-solid fa-globe px-1"></i>
            {{< badge text="EXPERIMENTAL" tone="info" >}} {{< badge text="X" tone="neutral" >}} {{< param hugoMinVersion >}}
            <i class="fa-regular fa-file text-info px-1"></i> <i class="fa-solid fa-rocket text-primary px-1"></i> {{% _param WEIRD %}}

            {{< cardpane >}}
            {{< card header="[**Pigsty**](https://github.com/pgsty/pigsty)" >}}
            body
            {{< /card >}}
            {{< /cardpane >}}
            """,
            ["param_placeholders", "cards"],
            findings=3,  # WEIRD + cardpane + its card
        )
        self.assertEqual(counts["_param"], 11)
        self.assertEqual(counts["card.header_box"], 1)

    # -- cards -----------------------------------------------------------------
    def test_cards_list_and_rich_forms(self):
        counts, found = self.assertMigrates(
            """\
            {{< doc-cards cols="2" >}}
            {{< doc-card title="Get Started" link="/docs/start/" >}}
            Install SOW.
            {{< /doc-card >}}
            {{< doc-card title="Design" link="/docs/design/" >}}
            Ownership.
            {{< /doc-card >}}
            {{< /doc-cards >}}

            {{< nav-cards cols="4" >}}
            {{< nav-card title="Linux" link="#repo" icon="fa-solid fa-box-archive" badge="Recommended" desc="APT/YUM lifecycle." />}}
            {{< nav-card title="Release" link="#rel" icon="fa-solid fa-file-zipper" desc="RPM, DEB." accent="primary" />}}
            {{< /nav-cards >}}

            {{< cardpane >}}
            {{< card header="**OSS**" title="Free" >}}
            <p>hi</p>
            {{< /card >}}
            {{< /cardpane >}}
            """,
            """\
            - [Get Started](/docs/start/) — Install SOW.
            - [Design](/docs/design/) — Ownership.
            {.cards}

            {{< cards >}}
            {{< card title="Linux" link="#repo" icon="fa-solid fa-box-archive" badge="Recommended" >}}
            APT/YUM lifecycle.
            {{< /card >}}
            {{< card title="Release" link="#rel" icon="fa-solid fa-file-zipper" >}}
            RPM, DEB.
            {{< /card >}}
            {{< /cards >}}

            {{< cardpane >}}
            {{< card header="**OSS**" title="Free" >}}
            <p>hi</p>
            {{< /card >}}
            {{< /cardpane >}}
            """,
            ["cards"],
            findings=2,
        )
        self.assertEqual(counts["cards.list"], 1)
        self.assertEqual(counts["cards.rich"], 1)
        self.assertEqual(counts["cards.accent_dropped"], 1)

    # -- image / include / fence title / badge -----------------------------------
    def test_imgproc_readfile_filename_badge(self):
        counts, found = self.assertMigrates(
            """\
            {{< imgproc src="images/x.webp" command="Fit" options="640x320" alt="Preview" >}}
            Caption **md**.
            {{< /imgproc >}}

            {{% imgproc ddia Fit "768x512" %}}{{% /imgproc %}}

            {{< readfile file="/docs/conf/x.yml" code="true" lang="yaml" >}}
            {{< readfile "score.txt" >}}

            ```yaml {filename="hugo.yaml"}
            a: 1
            ```

            {{< badge text="Deprecated" tone="danger" outline=false >}}
            """,
            """\
            {{< imgproc src="images/x.webp" command="Fit" options="640x320" alt="Preview" >}}
            Caption **md**.
            {{< /imgproc >}}

            {{% imgproc ddia Fit "768x512" %}}{{% /imgproc %}}

            {{< include file="/docs/conf/x.yml" code=true lang="yaml" >}}
            {{< include file="score.txt" >}}

            ```yaml {title="hugo.yaml"}
            a: 1
            ```

            {{< badge text="Deprecated" tone="danger" >}}
            """,
            findings=2,
        )
        self.assertEqual(counts["readfile"], 2)
        self.assertEqual(counts["fencetitle"], 1)
        self.assertEqual(counts["badge.outline_dropped"], 1)
        reasons = " | ".join(f.reason for f in found)
        # A Markdown caption cannot survive as a plain-text attribute value, so
        # the block is reported and left for a human instead of being flattened.
        self.assertIn("caption is Markdown", reasons)
        self.assertIn("positional imgproc", reasons)

    def test_image_shortcode_to_attribute_line(self):
        """A plain-text caption converts cleanly to the block-image attribute line."""
        counts, _ = self.assertMigrates(
            """\
            {{< image src="a.png" command="Fit" options="640x320" alt="A" >}}
            A plain caption.
            {{< /image >}}

            {{< imgproc src="b.png" command="Crop" options="24x24" decorative=true >}}{{< /imgproc >}}
            """,
            """\
            ![A](a.png)
            {command="Fit" options="640x320" caption="A plain caption."}

            ![](b.png)
            {command="Crop" options="24x24"}
            """,
            ["image"],
        )
        self.assertEqual(counts["image"], 1)
        self.assertEqual(counts["imgproc"], 1)

    # -- book: example -> eg, book-figures kind ------------------------------------
    def test_example_to_eg_and_book_figures(self):
        counts, found = self.assertMigrates(
            """\
            {{< example num="4-1" id="fig_x" caption="Analytics query" />}}

            ```sql
            SELECT 1;
            ```

            {{< example caption="unnumbered" />}}

            Some text.

            {{< book-figures kind="tbl" >}}
            {{< book-figures >}}
            """,
            """\
            {{< eg num="4-1" id="fig_x" caption="Analytics query" >}}
            ```sql
            SELECT 1;
            ```
            {{< /eg >}}

            {{< example caption="unnumbered" />}}

            Some text.

            {{< book-tables >}}
            {{< book-figures >}}
            """,
            ["eg"],
            findings=1,
        )
        self.assertEqual(counts["example"], 1)
        self.assertEqual(counts["book-figures.kind.tbl"], 1)

    def test_report_only_counts(self):
        final, counts, findings = run(
            """\
            {{% _param FAS_LG robot info %}}
            {{< xref page="/ch9" anchor="x" >}}第 9 章{{< /xref >}}
            {{< xref fig="2-1" >}}
            """,
            ["reportonly"],
        )
        self.assertEqual(counts["xref.kindless"], 1)
        self.assertEqual(counts["xref.kind"], 1)
        self.assertEqual(len(findings), 0)  # _param is handled by param_placeholders now

    def test_residual_check_flags_legacy_and_not_new_syntax(self):
        residual = residual_findings(
            "t.md",
            textwrap.dedent(
                """\
                {{< tabpane >}}
                {{< tab header="x" >}}
                {{< /tab >}}
                {{< /tabpane >}}
                {{< tabs >}}
                {{< tab label="ok" >}}
                {{< /tab >}}
                {{< /tabs >}}
                {{< card title="new" link="/x/" >}}
                {{< /card >}}
                {{< card header="legacy" >}}
                {{< /card >}}
                {{% tabs %}}{{% tab label="wrong-delim" %}}{{% /tab %}}{{% /tabs %}}
                {{% cards %}}{{% card title="wrong" %}}{{% /card %}}{{% /cards %}}
                {{% image src="x" alt="y" %}}{{% /image %}}
                {{% fields %}}{{% field name="n" %}}{{% /field %}}{{% /fields %}}
                ```yaml {filename="x"}
                ```
                {{< badge text="a" outline=true >}}
                - a/
                  - b
                {.filetree}
                """
            ),
        )
        reasons = [f.reason for f in residual]
        sources = [f.source for f in residual]
        self.assertTrue(any("tabpane" in r for r in reasons))
        self.assertTrue(any("legacy tab" in r for r in reasons))
        self.assertTrue(any("Bootstrap card" in r for r in reasons))
        self.assertTrue(any("filename" in r for r in reasons))
        self.assertTrue(any("outline" in r for r in reasons))
        self.assertTrue(any("filetree" in r for r in reasons))
        # withdrawn % forms of the new containers are flagged
        for wrong in ('{{% tabs %}}', '{{% cards %}}', '{{% image', '{{% fields %}}'):
            self.assertTrue(any(wrong in src for src in sources), wrong)
        # the new angle-bracket syntax is not flagged
        self.assertFalse(any('label="ok"' in src for src in sources))
        self.assertFalse(any('title="new"' in src for src in sources))

    def test_fields_delimiter_rewrite(self):
        counts, _ = self.assertMigrates(
            """\
            {{% fields label="Config" %}}
              {{% field name="offline_search" type="boolean" required=true %}}
              Enables search.
              {{% /field %}}
            {{% /fields %}}
            """,
            """\
            {{< fields label="Config" >}}
              {{< field name="offline_search" type="boolean" required=true >}}
              Enables search.
              {{< /field >}}
            {{< /fields >}}
            """,
            ["fieldsdelim"],
        )
        self.assertEqual(counts["fieldsdelim.fields"], 2)
        self.assertEqual(counts["fieldsdelim.field"], 2)


class CliCase(unittest.TestCase):
    def test_dry_run_does_not_write_and_write_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            shutil.copytree(ROOT / "exampleSite" / "content", site / "content")
            (site / "content" / "migrate-me.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Migrate me
                    ---

                    {{% alert color="info" title="Hi" %}}
                    body
                    {{% /alert %}}
                    """
                ),
                encoding="utf-8",
            )
            before = {p.relative_to(site): p.read_bytes() for p in site.rglob("*.md")}
            dry = subprocess.run([sys.executable, str(CLI), "migrate", "--site", str(site), "--quiet", "--json", str(Path(tmp) / "dry.json")], capture_output=True, text=True)
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn("dry-run", dry.stdout)
            after_dry = {p.relative_to(site): p.read_bytes() for p in site.rglob("*.md")}
            self.assertEqual(before, after_dry, "dry-run must not modify files")
            written = subprocess.run([sys.executable, str(CLI), "migrate", "--site", str(site), "--quiet", "--write"], capture_output=True, text=True)
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            text = (site / "content" / "migrate-me.md").read_text(encoding="utf-8")
            self.assertIn("> [!NOTE] Hi", text)
            self.assertNotIn("{{% alert", text)
            snapshot = {p.relative_to(site): p.read_bytes() for p in site.rglob("*.md")}
            again = subprocess.run([sys.executable, str(CLI), "migrate", "--site", str(site), "--quiet", "--write"], capture_output=True, text=True)
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertIn("changed: 0", again.stdout)
            self.assertEqual(snapshot, {p.relative_to(site): p.read_bytes() for p in site.rglob("*.md")})
            check = subprocess.run([sys.executable, str(CLI), "check", "--site", str(site), "--paths", "content/migrate-me.md"], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stdout)

    def test_report_runs_on_examplesite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "r.json"
            out_md = Path(tmp) / "r.md"
            result = subprocess.run([sys.executable, str(CLI), "report", "--sites", str(ROOT / "exampleSite"), "--json", str(out_json), "--md", str(out_md)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(out_json.exists() and out_md.exists())
            self.assertIn("## 1. Conversions per site", out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
