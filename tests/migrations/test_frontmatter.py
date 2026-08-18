"""Freeze the 1.0 front matter migration: key renames, ui: lifting, cascade,
non-YAML findings, idempotency, and the dry-run-first CLI.

    python3 -m unittest discover -s tests/migrations -t .
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bin" / "migrations"))

from oink06.cli import migrate_text, residual_findings  # noqa: E402
from oink06.transforms import load  # noqa: E402

CLI = ROOT / "bin" / "migrations" / "oink06.py"
ONLY = ["frontmatter"]


class FrontMatterCase(unittest.TestCase):
    maxDiff = None

    def migrate(self, before: str, after: str, findings: int = 0):
        text = textwrap.dedent(before)
        final, counts, found = migrate_text("t.md", text, load(ONLY))
        self.assertEqual(final, textwrap.dedent(after))
        self.assertEqual(len(found), findings, [f.__dict__ for f in found])
        second, _, _ = migrate_text("t.md", final, load(ONLY))
        self.assertEqual(second, final, "second run must not change the text")
        return counts, found

    def unchanged(self, text: str, findings: int = 0):
        return self.migrate(text, text, findings)

    # -- rule 1 ---------------------------------------------------------------
    def test_manual_link_keys(self):
        counts, _ = self.migrate(
            """\
            ---
            title: Section
            manualLink: /docs/
            manualLinkTitle: Read the docs
            manualLinkTarget: _blank
            manuallinkrelref: "/docs/x"
            ---

            Body mentioning manualLink stays as it is.
            """,
            """\
            ---
            title: Section
            manual_link: /docs/
            manual_link_title: Read the docs
            manual_link_target: _blank
            manual_link_relref: "/docs/x"
            ---

            Body mentioning manualLink stays as it is.
            """,
        )
        self.assertEqual(counts["frontmatter.manual_link"], 4)

    def test_manual_link_conflict_is_dropped_with_a_finding(self):
        counts, found = self.migrate(
            """\
            ---
            manual_link: /new/
            manualLink: /old/
            ---
            """,
            """\
            ---
            manual_link: /new/
            ---
            """,
            findings=1,
        )
        self.assertIn("already set", found[0].reason)
        self.assertEqual(counts["frontmatter.dropped"], 1)

    # -- rule 2 ---------------------------------------------------------------
    def test_context_menu_rename_keeps_the_value(self):
        counts, _ = self.migrate(
            """\
            ---
            title: X
            context_menu:
              enable: true
              copy_markdown: false
            ---
            """,
            """\
            ---
            title: X
            page_context_menu:
              enable: true
              copy_markdown: false
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.page_context_menu"], 1)

    # -- rule 3 ---------------------------------------------------------------
    def test_hide_readingtime_inverts(self):
        counts, _ = self.migrate(
            """\
            ---
            hide_readingtime: true
            ---
            """,
            """\
            ---
            reading_time: false
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.reading_time"], 1)
        self.migrate(
            """\
            ---
            hide_readingtime: false   # keep the estimate
            ---
            """,
            """\
            ---
            reading_time: true   # keep the estimate
            ---
            """,
        )

    def test_hide_readingtime_non_boolean_is_reported(self):
        _, found = self.unchanged(
            """\
            ---
            hide_readingtime: maybe
            ---
            """,
            findings=1,
        )
        self.assertIn("not a boolean", found[0].reason)

    # -- rule 4 ---------------------------------------------------------------
    def test_hide_feedback_true_becomes_feedback_false(self):
        counts, _ = self.migrate(
            """\
            ---
            title: X
            hide_feedback: true
            ---
            """,
            """\
            ---
            title: X
            feedback: false
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.feedback"], 1)

    def test_hide_feedback_false_is_deleted(self):
        counts, _ = self.migrate(
            """\
            ---
            title: X
            hide_feedback: false
            ---
            """,
            """\
            ---
            title: X
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.feedback"], 1)

    def test_hide_feedback_with_existing_feedback_is_dropped(self):
        _, found = self.migrate(
            """\
            ---
            feedback: true
            hide_feedback: true
            ---
            """,
            """\
            ---
            feedback: true
            ---
            """,
            findings=1,
        )
        self.assertEqual(found[0].reason, "hide_feedback dropped; feedback already set")

    # -- rule 5 ---------------------------------------------------------------
    def test_exclude_search_rename(self):
        counts, _ = self.migrate(
            """\
            ---
            excludeSearch: true
            ---
            """,
            """\
            ---
            search_exclude: true
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.search_exclude"], 1)

    def test_search_exclusion_keys_merge_with_or(self):
        counts, found = self.migrate(
            """\
            ---
            exclude_search: false
            excludeSearch: true
            ---
            """,
            """\
            ---
            search_exclude: true
            ---
            """,
            findings=1,
        )
        self.assertIn("merged into search_exclude", found[0].reason)
        self.assertEqual(counts["frontmatter.search_exclude"], 1)
        self.assertEqual(counts["frontmatter.dropped"], 1)

    def test_search_exclude_merges_with_an_existing_new_key(self):
        self.migrate(
            """\
            ---
            search_exclude: false
            exclude_search: true
            ---
            """,
            """\
            ---
            search_exclude: true
            ---
            """,
            findings=1,
        )

    # -- rule 6 ---------------------------------------------------------------
    def test_content_width_values(self):
        counts, _ = self.migrate(
            """\
            ---
            content_width: norm
            ---
            """,
            """\
            ---
            reading_width: normal
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.reading_width"], 1)
        self.migrate(
            """\
            ---
            content_width: wide
            ---
            """,
            """\
            ---
            reading_width: wide
            ---
            """,
        )

    def test_content_width_unknown_value_renames_and_reports(self):
        _, found = self.migrate(
            """\
            ---
            content_width: full
            ---
            """,
            """\
            ---
            reading_width: full
            ---
            """,
            findings=1,
        )
        self.assertIn("norm/slim/wide", found[0].reason)

    # -- rule 7 ---------------------------------------------------------------
    def test_params_ui_block_is_lifted_to_the_top_level(self):
        counts, _ = self.migrate(
            """\
            ---
            title: X
            params:
              ui:
                section_index: cards
                image_zoom:
                  enable: true
                keyboard_nav:
                  enable: false
                typography:
                  preset: system
            ---

            Body.
            """,
            """\
            ---
            title: X
            section_index: cards
            image_zoom: true
            keyboard_nav: false
            typography: system
            ---

            Body.
            """,
        )
        self.assertEqual(counts["frontmatter.ui_lift"], 4)
        self.assertEqual(counts["frontmatter.ui_enable"], 3)

    def test_top_level_ui_flow_map_is_lifted(self):
        counts, _ = self.migrate(
            """\
            ---
            title: X
            ui: {section_index: cards, image_zoom: {enable: true}}
            ---
            """,
            """\
            ---
            title: X
            section_index: cards
            image_zoom: true
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.ui_lift"], 2)

    def test_params_keeps_its_other_keys_when_ui_is_lifted(self):
        self.migrate(
            """\
            ---
            title: X
            params:
              author: rh
              ui:
                section_index: list
            weight: 3
            ---
            """,
            """\
            ---
            title: X
            params:
              author: rh
            section_index: list
            weight: 3
            ---
            """,
        )

    def test_nested_ui_children_keep_their_own_blocks(self):
        self.migrate(
            """\
            ---
            ui:
              taxonomy_icons:
                tags: fa-solid fa-tag
                categories: fa-solid fa-folder
            ---
            """,
            """\
            ---
            taxonomy_icons:
              tags: fa-solid fa-tag
              categories: fa-solid fa-folder
            ---
            """,
        )

    def test_ui_pager_is_site_only(self):
        counts, found = self.migrate(
            """\
            ---
            title: X
            ui:
              pager:
                types: prev-next
            ---
            """,
            """\
            ---
            title: X
            ---
            """,
            findings=1,
        )
        self.assertIn("site-only key ui.pager.types", found[0].reason)
        self.assertEqual(counts["frontmatter.dropped"], 1)

    def test_ui_key_conflicting_with_the_top_level_is_reported(self):
        counts, found = self.migrate(
            """\
            ---
            section_index: list
            ui:
              section_index: cards
            ---
            """,
            """\
            ---
            section_index: list
            ---
            """,
            findings=1,
        )
        self.assertIn("conflicts with the existing top-level", found[0].reason)
        self.assertEqual(counts["frontmatter.dropped"], 1)

    def test_ui_key_identical_to_the_top_level_is_dropped_silently(self):
        self.migrate(
            """\
            ---
            section_index: cards
            ui:
              section_index: cards
            ---
            """,
            """\
            ---
            section_index: cards
            ---
            """,
        )

    def test_empty_ui_map_is_removed(self):
        counts, _ = self.migrate(
            """\
            ---
            title: X
            params:
              ui: {}
            ---
            """,
            """\
            ---
            title: X
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.dropped"], 1)

    def test_a_finding_is_reported_once_even_when_earlier_rules_shift_lines(self):
        _, found = self.migrate(
            """\
            ---
            params:
              ui: {}
            hide_feedback: "true"
            ---
            """,
            """\
            ---
            hide_feedback: "true"
            ---
            """,
            findings=1,
        )
        self.assertEqual(found[0].line, 4)  # the line in the source file, not after the rewrite

    def test_ui_block_with_a_block_scalar_is_left_alone(self):
        _, found = self.unchanged(
            """\
            ---
            ui:
              note: |
                a
                b
            ---
            """,
            findings=1,
        )
        self.assertIn("block scalar", found[0].reason)

    def test_ui_block_with_an_anchor_is_left_alone(self):
        _, found = self.unchanged(
            """\
            ---
            ui:
              section_index: &idx cards
            ---
            """,
            findings=1,
        )
        self.assertIn("anchor", found[0].reason)

    # -- rule 8 ---------------------------------------------------------------
    def test_top_level_annotation_map_collapses(self):
        counts, _ = self.migrate(
            """\
            ---
            annotation:
              enable: true
            ---
            """,
            """\
            ---
            annotation: true
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.annotation"], 1)
        self.migrate(
            """\
            ---
            annotation: {enable: false}
            ---
            """,
            """\
            ---
            annotation: false
            ---
            """,
        )

    def test_annotation_map_with_extra_keys_is_reported(self):
        _, found = self.unchanged(
            """\
            ---
            annotation:
              enable: true
              style: margin
            ---
            """,
            findings=1,
        )
        self.assertIn("keys other than enable", found[0].reason)

    def test_annotation_boolean_is_left_alone(self):
        self.unchanged(
            """\
            ---
            annotation: true
            ---
            """
        )

    # -- rule 9 ---------------------------------------------------------------
    def test_assistant_links_without_a_menu(self):
        counts, _ = self.migrate(
            """\
            ---
            title: X
            assistant_links: false
            ---
            """,
            """\
            ---
            title: X
            page_context_menu:
              assistant_links: false
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.assistant_links"], 1)

    def test_assistant_links_with_a_boolean_menu(self):
        self.migrate(
            """\
            ---
            page_context_menu: true
            assistant_links: false
            ---
            """,
            """\
            ---
            page_context_menu:
              enable: true
              assistant_links: false
            ---
            """,
        )

    def test_assistant_links_with_a_map_menu(self):
        self.migrate(
            """\
            ---
            page_context_menu:
              enable: true
              copy_markdown: false
            assistant_links: true
            ---
            """,
            """\
            ---
            page_context_menu:
              enable: true
              copy_markdown: false
              assistant_links: true
            ---
            """,
        )

    def test_context_menu_rename_then_assistant_links_merge(self):
        counts, _ = self.migrate(
            """\
            ---
            context_menu: false
            assistant_links: true
            ---
            """,
            """\
            ---
            page_context_menu:
              enable: false
              assistant_links: true
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.page_context_menu"], 1)
        self.assertEqual(counts["frontmatter.assistant_links"], 1)

    def test_assistant_links_already_inside_the_menu_is_reported(self):
        _, found = self.unchanged(
            """\
            ---
            page_context_menu:
              assistant_links: true
            assistant_links: false
            ---
            """,
            findings=1,
        )
        self.assertIn("already set inside page_context_menu", found[0].reason)

    # -- rule 10 --------------------------------------------------------------
    def test_cascade_map(self):
        self.migrate(
            """\
            ---
            title: Docs
            cascade:
              type: docs
              hide_feedback: true
              params:
                ui:
                  section_index: cards
            ---
            """,
            """\
            ---
            title: Docs
            cascade:
              type: docs
              feedback: false
              params:
                section_index: cards
            ---
            """,
        )

    def test_cascade_list_lifts_ui_into_params(self):
        counts, _ = self.migrate(
            """\
            ---
            cascade:
              - _target:
                  path: /docs/**
                ui:
                  image_zoom:
                    enable: true
              - _target:
                  path: /blog/**
                params:
                  ui:
                    section_index: list
                  hide_readingtime: true
            ---
            """,
            """\
            ---
            cascade:
              - _target:
                  path: /docs/**
                params:
                  image_zoom: true
              - _target:
                  path: /blog/**
                params:
                  section_index: list
                  reading_time: false
            ---
            """,
        )
        self.assertEqual(counts["frontmatter.ui_lift"], 2)
        self.assertEqual(counts["frontmatter.reading_time"], 1)

    def test_cascade_list_with_the_map_starting_on_the_next_line(self):
        self.migrate(
            """\
            ---
            cascade:
              -
                _target:
                  path: /docs/**
                content_width: slim
            ---
            """,
            """\
            ---
            cascade:
              -
                _target:
                  path: /docs/**
                reading_width: slim
            ---
            """,
        )

    def test_cascade_flow_item_is_reported(self):
        _, found = self.unchanged(
            """\
            ---
            cascade:
              - {_target: {path: /docs/**}, hide_feedback: true}
            ---
            """,
            findings=1,
        )
        self.assertIn("flow mapping", found[0].reason)

    # -- non-YAML front matter -------------------------------------------------
    def test_toml_front_matter_is_reported_not_rewritten(self):
        _, found = self.unchanged(
            """\
            +++
            title = "X"
            hide_feedback = true
            +++

            Body.
            """,
            findings=1,
        )
        self.assertEqual(found[0].reason, "TOML/JSON front matter is not migrated automatically")

    def test_toml_front_matter_without_legacy_keys_is_silent(self):
        self.unchanged(
            """\
            +++
            title = "X"
            weight = 3
            +++
            """
        )

    def test_toml_ui_table_is_reported(self):
        _, found = self.unchanged(
            """\
            +++
            title = "X"
            [params.ui]
            section_index = "cards"
            +++
            """,
            findings=1,
        )
        self.assertIn("not migrated automatically", found[0].reason)

    def test_json_front_matter_is_reported(self):
        _, found = self.unchanged(
            """\
            {
              "title": "X",
              "hide_readingtime": true
            }

            Body.
            """,
            findings=1,
        )
        self.assertIn("not migrated automatically", found[0].reason)

    def test_json_front_matter_braces_inside_strings_do_not_end_the_object(self):
        _, found = self.unchanged(
            """\
            {
              "title": "Config } reference",
              "hide_feedback": true
            }

            Body.
            """,
            findings=1,
        )
        self.assertEqual(found[0].reason, "TOML/JSON front matter is not migrated automatically")

    # -- safety ---------------------------------------------------------------
    def test_body_and_unrelated_front_matter_are_untouched(self):
        self.unchanged(
            """\
            ---
            title: X
            weight: 3
            tags:
              - a
              - b
            params:
              author: rh
            resources:
              - src: a.png
                title: A
            ---

            context_menu: not front matter
            hide_feedback: still not front matter

            ```yaml
            ui:
              section_index: cards
            ```
            """
        )

    def test_file_without_front_matter_is_untouched(self):
        self.unchanged("Just a body with hide_feedback: true in it.\n")

    def test_comments_and_blank_lines_survive(self):
        self.migrate(
            """\
            ---
            # leading comment
            title: X

            # about search
            excludeSearch: true
            ---
            """,
            """\
            ---
            # leading comment
            title: X

            # about search
            search_exclude: true
            ---
            """,
        )

    def test_crlf_front_matter(self):
        text = "---\r\nhide_feedback: true\r\n---\r\n\r\nBody\r\n"
        final, _, _ = migrate_text("t.md", text, load(ONLY))
        self.assertEqual(final, "---\r\nfeedback: false\r\n---\r\n\r\nBody\r\n")

    # -- check -----------------------------------------------------------------
    def test_residual_flags_front_matter_only(self):
        residual = residual_findings(
            "t.md",
            textwrap.dedent(
                """\
                ---
                title: X
                manualLink: /a/
                context_menu: true
                hide_readingtime: true
                hide_feedback: true
                exclude_search: true
                content_width: norm
                assistant_links: true
                ui:
                  section_index: cards
                params:
                  ui:
                    section_index: cards
                cascade:
                  - _target:
                      path: /docs/**
                    ui:
                      section_index: cards
                    params:
                      hide_feedback: true
                ---

                Body.
                """
            ),
        )
        reasons = [f.reason for f in residual if f.kind == "frontmatter"]
        for key in ("manualLink", "context_menu", "hide_readingtime", "hide_feedback", "exclude_search", "content_width", "assistant_links"):
            self.assertTrue(any(key in reason for reason in reasons), key)
        self.assertEqual(sum(1 for reason in reasons if "ui: map" in reason), 3)
        self.assertEqual(sum(1 for reason in reasons if "hide_feedback" in reason), 2)  # page + cascade item

    def test_residual_does_not_flag_migrated_front_matter(self):
        residual = residual_findings(
            "t.md",
            textwrap.dedent(
                """\
                ---
                title: X
                manual_link: /a/
                reading_time: false
                feedback: false
                search_exclude: true
                reading_width: normal
                image_zoom: true
                page_context_menu:
                  enable: true
                  assistant_links: false
                cascade:
                  - _target:
                      path: /docs/**
                    params:
                      section_index: cards
                ---

                Body.
                """
            ),
        )
        self.assertEqual([f.__dict__ for f in residual if f.kind == "frontmatter"], [])

    def test_residual_flags_non_yaml_front_matter(self):
        residual = residual_findings("t.md", "+++\ntitle = \"X\"\nhide_feedback = true\n+++\n")
        self.assertEqual([f.reason for f in residual if f.kind == "frontmatter"], ["residual: TOML/JSON front matter is not migrated automatically"])


class FrontMatterCliCase(unittest.TestCase):
    def test_check_and_report_fail_closed_on_missing_or_empty_sites(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            for command in (
                ["check", "--site", str(missing)],
                ["report", "--sites", str(missing)],
            ):
                result = subprocess.run(
                    [sys.executable, str(CLI), *command],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("site directory not found", result.stderr)

            empty = Path(tmp) / "empty"
            (empty / "content").mkdir(parents=True)
            result = subprocess.run(
                [sys.executable, str(CLI), "check", "--site", str(empty)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("no Markdown content files", result.stderr)

    def test_check_fails_on_non_utf8_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            (site / "content").mkdir(parents=True)
            (site / "content" / "bad.md").write_bytes(b"\xff\xfe")
            result = subprocess.run(
                [sys.executable, str(CLI), "check", "--site", str(site)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("not utf-8", result.stderr)

    def test_cli_dry_run_then_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            (site / "content").mkdir(parents=True)
            page = site / "content" / "page.md"
            page.write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: Page
                    manualLink: /x/
                    hide_feedback: true
                    params:
                      ui:
                        section_index: cards
                    ---

                    Body.
                    """
                ),
                encoding="utf-8",
            )
            before = page.read_bytes()
            dry = subprocess.run(
                [sys.executable, str(CLI), "migrate", "--site", str(site), "--only", "frontmatter", "--quiet"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn("frontmatter.manual_link: 1", dry.stdout)
            self.assertEqual(page.read_bytes(), before, "dry-run must not write")
            written = subprocess.run(
                [sys.executable, str(CLI), "migrate", "--site", str(site), "--only", "frontmatter", "--quiet", "--write"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            self.assertEqual(
                page.read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    ---
                    title: Page
                    manual_link: /x/
                    feedback: false
                    section_index: cards
                    ---

                    Body.
                    """
                ),
            )
            check = subprocess.run(
                [sys.executable, str(CLI), "check", "--site", str(site)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout)


if __name__ == "__main__":
    unittest.main()
