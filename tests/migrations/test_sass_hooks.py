"""Freeze the SCSS-hook converter: parsing, the difference it writes, the
cascade-order scoping, and the equivalence check. No Sass compiler is needed.

    python3 -m unittest discover -s tests/migrations -t .
"""

from __future__ import annotations

from pathlib import Path
import sys
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bin" / "migrations"))

import sass_hooks  # noqa: E402


def css(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


THEME = css("""
    :root, [data-bs-theme='light'] {
      --bs-primary: #0d6efd;
      --bs-link-color: #0d6efd;
    }

    .btn-primary {
      --bs-btn-bg: #0d6efd;
    }

    @media (min-width: 768px) {
      .lead {
        font-size: 1.25rem;
      }
    }

    [data-td-preset='paper'] {
      --bs-link-color: #1d588c;
    }

    @keyframes spin {
      to { rotate: 360deg; }
    }
""")


class ParseTest(unittest.TestCase):
    def test_rules_groups_and_opaque_at_rules(self):
        nodes = sass_hooks.parse(THEME)
        self.assertEqual([node.kind for node in nodes], ["rule", "rule", "group", "rule", "opaque"])
        self.assertEqual(nodes[0].selectors, (":root", '[data-bs-theme="light"]'))
        self.assertEqual(nodes[0].decls[0], ("--bs-primary", "#0d6efd"))
        self.assertEqual(nodes[2].children[0].selectors, (".lead",))

    def test_separators_inside_strings_and_functions_do_not_split(self):
        node = sass_hooks.parse('a::after { content: "a;b{c}"; background: url(x.png?a=1;b=2); }')[0]
        self.assertEqual(node.decls, [("content", '"a;b{c}"'), ("background", "url(x.png?a=1;b=2)")])

    def test_specificity(self):
        self.assertEqual(sass_hooks.specificity(":root"), (0, 1, 0))
        self.assertEqual(sass_hooks.specificity("[data-td-preset='paper']"), (0, 1, 0))
        self.assertEqual(sass_hooks.specificity("#a .b:hover > p::before"), (1, 2, 2))
        self.assertEqual(sass_hooks.specificity("a:where(.x):not(.y, #z)"), (1, 0, 1))


class ConvertTest(unittest.TestCase):
    def convert(self, compiled: str):
        project, report, problems = sass_hooks.convert(THEME, compiled)
        self.assertEqual(problems, [])
        return project, report

    def test_unchanged_theme_yields_nothing(self):
        project, report = self.convert(THEME)
        self.assertEqual(project, "")
        self.assertEqual(report.changed_rules + report.site_rules, 0)

    def test_site_rules_are_kept_verbatim_with_their_comments(self):
        tail = css("""
            /* Site navigation. */
            .site-nav {
              gap: 1rem;
            }

            @media print {
              .site-nav {
                display: none;
              }
            }
        """)
        project, report = self.convert(THEME + "\n" + tail)
        self.assertEqual(project, tail)
        self.assertEqual(report.site_rules, 2)

    def test_variable_change_becomes_an_override_of_only_the_changed_declarations(self):
        compiled = THEME.replace("--bs-btn-bg: #0d6efd", "--bs-btn-bg: #2f6793") \
                        .replace("font-size: 1.25rem", "font-size: 1.5rem")
        project, report = self.convert(compiled)
        self.assertIn(".btn-primary {\n  --bs-btn-bg: #2f6793;\n}", project)
        self.assertIn("@media (min-width: 768px) {\n  .lead {\n    font-size: 1.5rem;\n  }\n}", project)
        self.assertNotIn("--bs-primary", project)
        self.assertEqual(report.changed_decls, 2)

    def test_override_stays_behind_a_later_theme_rule_of_equal_specificity(self):
        compiled = THEME.replace("--bs-primary: #0d6efd;\n  --bs-link-color: #0d6efd",
                                 "--bs-primary: #2f6793;\n  --bs-link-color: #2f6793")
        project, report = self.convert(compiled)
        # --bs-primary has no later competitor; the paper palette keeps the link colour.
        self.assertIn(':root,\n[data-bs-theme="light"] {\n  --bs-primary: #2f6793;\n}', project)
        self.assertIn(':root:where(:not([data-td-preset="paper"])),\n'
                      '[data-bs-theme="light"]:where(:not([data-td-preset="paper"])) {\n'
                      "  --bs-link-color: #2f6793;\n}", project)
        self.assertEqual(report.scoped, 2)

    def test_value_overridden_by_the_same_selector_later_is_dropped(self):
        theme = THEME + ":root {\n  --bs-link-color: #123456;\n}\n"
        compiled = theme.replace("--bs-link-color: #0d6efd", "--bs-link-color: #2f6793")
        project, report, problems = sass_hooks.convert(theme, compiled)
        self.assertEqual(problems, [])
        self.assertEqual(report.dead, 1)
        self.assertFalse([line for line in project.splitlines() if line.startswith(":root")])
        # A nested colour-mode island is not :root, so the value still applies there.
        self.assertIn('[data-bs-theme="light"]:where(:not([data-td-preset="paper"], :root)) {\n'
                      "  --bs-link-color: #2f6793;\n}", project)

    def test_theme_output_that_disappears_is_reported(self):
        compiled = THEME.replace("  --bs-link-color: #0d6efd;\n", "")
        _, report = self.convert(compiled)
        self.assertEqual(len(report.removed), 1)
        self.assertIn("--bs-link-color", report.removed[0])

    def test_changed_keyframes_are_replaced_whole(self):
        compiled = THEME.replace("rotate: 360deg", "rotate: 180deg")
        project, _ = self.convert(compiled)
        self.assertIn("@keyframes spin {\n  to { rotate: 180deg; }\n}", project)

    def test_equivalence_reports_a_lost_declaration(self):
        compiled = THEME + ".site-nav {\n  gap: 1rem;\n}\n"
        problems = sass_hooks.equivalent(sass_hooks.parse(THEME), [], sass_hooks.parse(compiled))
        self.assertEqual(len(problems), 1)
        self.assertIn(".site-nav { gap: 1rem }", problems[0])


class ScopeTest(unittest.TestCase):
    def test_scope_keeps_pseudo_elements_last(self):
        self.assertEqual(
            sass_hooks.scope(".range::-moz-range-thumb:active", (".range:disabled::-moz-range-thumb",)),
            ".range:where(:not(.range:disabled))::-moz-range-thumb:active")
        self.assertIsNone(sass_hooks.scope(".a::before", (".b::after",)))

    def test_only_plausible_companions_share_an_element(self):
        share = sass_hooks.may_share_element
        self.assertTrue(share(":root", '[data-td-preset="paper"]'))
        self.assertTrue(share(".form-control:focus", ".form-control.is-valid"))
        self.assertFalse(share('[data-bs-theme="light"]', '[data-bs-theme="dark"]'))
        self.assertFalse(share(".btn-primary", ".btn-secondary"))
        self.assertFalse(share(".a::before", ".a::after"))


class LoudCommentTest(unittest.TestCase):
    def test_line_comments_become_block_comments(self):
        scss = css("""
            // First line,
            // second line.
            .a { color: red; } // trailing
            .b { background: url(//cdn.example/x.png); content: "// not a comment"; }
            // ==========
        """)
        self.assertEqual(sass_hooks.loud_comments(scss), css("""
            /* First line,
               second line. */
            .a { color: red; } /* trailing */
            .b { background: url(//cdn.example/x.png); content: "// not a comment"; }
        """) + "\n")


if __name__ == "__main__":
    unittest.main()
