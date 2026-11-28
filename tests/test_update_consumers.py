import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "update_consumers", Path(__file__).resolve().parents[1] / "bin/update-consumers.py")
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


class ConsumerUpdates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def site(self, name="site"):
        site = self.root / name
        site.mkdir(parents=True)
        (site / "go.mod").write_text(
            "module example.org/site\n\ngo 1.27.0\n\nrequire github.com/pgsty/oink v1.0.0\n")
        (site / "go.sum").write_text("original checksums\n")
        subprocess.run(["git", "init", "-q", "-b", "main", str(site)], check=True)
        subprocess.run(["git", "-C", str(site), "add", "."], check=True)
        subprocess.run(["git", "-C", str(site), "-c", "user.name=Test",
                        "-c", "user.email=test@example.org", "commit", "-qm", "fixture"], check=True)
        return site

    def test_discovery_excludes_nested_archives_and_hidden_copies(self):
        site = self.site()
        self.site("site/archive/old")
        self.site(".hidden/site")
        self.assertEqual([str(site.resolve())], [x["site"] for x in updater.discover([self.root], [])])

    def test_primary_nested_site_is_found_but_archive_site_is_excluded(self):
        site = self.site("project/site")
        (site / "hugo.yaml").write_text("title: Primary nested site\n")
        archive = self.site("archive/site")
        (archive / "hugo.yaml").write_text("title: Archive\n")
        self.assertEqual([str(site.resolve())], [x["site"] for x in updater.discover([self.root], [])])
        self.assertEqual([str(site.resolve())], [x["site"] for x in updater.discover([], [self.root / "project"])])

    def test_classic_theme_is_reported_for_separate_update(self):
        site = self.root / "classic"
        theme = site / "themes/oink"
        theme.mkdir(parents=True)
        (theme / "go.mod").write_text("module github.com/pgsty/oink\n")
        (site / "hugo.yaml").write_text("theme: oink\n")
        with patch.object(updater, "hugo_config", return_value={"theme": ["oink"]}):
            item = updater.inspect(site, explicit=True)
            self.assertEqual("skipped", item["status"])
            self.assertEqual("classic", item["kind"])
            self.assertIn("separately", item["reason"])
        with patch.object(updater, "hugo_config", return_value={"theme": ["other"]}):
            self.assertIsNone(updater.inspect(site))

    def test_explicit_project_with_go_application_resolves_nested_site(self):
        site = self.site("application/site")
        (site / "hugo.yaml").write_text("title: Application docs\n")
        project = site.parent
        (project / "go.mod").write_text("module example.org/application\n\ngo 1.27.0\n")
        items = updater.discover([], [project, site])
        self.assertEqual([str(site.resolve())], [item["site"] for item in items])
        self.assertEqual("ready", items[0]["status"])
        (project / "go.mod").write_text(
            "module example.org/application\n// github.com/pgsty/oink is used only in site/\n")
        self.assertEqual(str(site.resolve()), updater.discover([], [project])[0]["site"])
        # An actual root consumer takes precedence over its nested site.
        (project / "go.mod").write_text((site / "go.mod").read_text())
        items = updater.discover([], [project])
        self.assertEqual([str(project.resolve())], [item["site"] for item in items])
        self.assertEqual("ready", items[0]["status"])

    def test_explicit_resolution_error_is_reported_without_losing_other_sites(self):
        site = self.site("broken/site")
        (site / "hugo.yaml").write_text("title: Nested docs\n")
        (site.parent / "go.mod").write_bytes(b"\xff")
        good = self.site("good")
        items = updater.discover([], [site.parent, good])
        self.assertEqual(["failed", "ready"], [item["status"] for item in items])
        self.assertIn("cannot resolve explicit site", items[0]["reason"])

    def test_inventory_reports_broken_root_and_module_and_continues(self):
        good = self.site("good")
        broken = self.site("broken")
        (broken / "go.mod").write_text("module example.org/broken\nrequire github.com/pgsty/oink BADVERSION\n")
        missing = self.root / "missing"
        report = self.root / "report"
        result = subprocess.run(
            [sys.executable, str(Path(updater.__file__)), "v1.1.0", "--roots", str(self.root),
             str(missing), "--report-dir", str(report)], text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        items = {item["site"]: item for item in json.loads((report / "report.json").read_text())["sites"]}
        self.assertEqual(items[str(good.resolve())]["status"], "pending")
        self.assertEqual(items[str(broken.resolve())]["status"], "failed")
        self.assertEqual(items[str(missing.resolve())]["status"], "failed")

    def test_explicit_missing_site_is_reported(self):
        missing = self.root / "missing"
        items = updater.discover([], [missing])
        self.assertEqual(items[0]["status"], "failed")
        self.assertIn("explicit site", items[0]["reason"])

    def test_source_only_site_requires_explicit_selection(self):
        site = self.root / "source-only"
        site.mkdir()
        (site / "go.mod").write_text(
            "module example.org/site\n\ngo 1.27.0\n\nrequire github.com/pgsty/oink v1.0.0\n")
        self.assertEqual("skipped", updater.inspect(site)["status"])
        self.assertEqual("ready", updater.inspect(site, explicit=True)["status"])

    def appearance_page(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<html data-td-preset="paper" data-td-site-preset="paper">'
                        + ''.join(f'<input data-td-preset-value="{p}">' for p in
                                  ("paper", "slate", "ink", "terminal", "news", "github")) + '</html>')

    def test_appearance_checks_localized_pages_and_rejects_missing_controls(self):
        self.appearance_page(self.root / "index.html")
        self.appearance_page(self.root / "zh/index.html")
        self.assertIn("zh/index.html", updater.check_appearance(self.root, {"languages": {"en": {}, "zh": {}}}))
        (self.root / "zh/index.html").write_text('<html data-td-preset="paper" data-td-site-preset="paper"></html>')
        with self.assertRaisesRegex(RuntimeError, "zh/index.html"):
            updater.check_appearance(self.root, {"languages": {"zh": {}}})

    def test_appearance_expects_the_four_styles_of_v1_7_0_and_older(self):
        self.appearance_page(self.root / "index.html")
        self.assertIn("index.html", updater.check_appearance(self.root, {}, "v1.8.0"))
        with self.assertRaisesRegex(RuntimeError, "all 4 style controls"):
            updater.check_appearance(self.root, {}, "v1.7.0")
        self.assertEqual(updater.maintained_styles("v1.6.0"), updater.LEGACY_STYLES)
        self.assertEqual(updater.maintained_styles("v1.8.0-rc.1"), updater.MAINTAINED_STYLES)

    def test_appearance_uses_docs_for_disabled_home_and_ignores_redirects(self):
        self.appearance_page(self.root / "docs/index.html")
        (self.root / "index.html").write_text('<html><meta http-equiv="refresh" content="0;url=/docs/"></html>')
        self.assertIn("docs/index.html", updater.check_appearance(self.root, {"disablekinds": ["home"]}))
        with self.assertRaisesRegex(RuntimeError, "no rendered entry pages"):
            updater.check_appearance(self.root, {})

    def test_retained_vendor_uses_the_resolved_graph(self):
        site = self.site()
        (site / "_vendor").mkdir()
        (site / "_vendor/modules.txt").write_text("# github.com/pgsty/oink v0.8.0\n")
        real_run = updater.run

        for graph, status in (("site github.com/pgsty/oink@v1.0.0", "ready"),
                              ("site github.com/pgsty/oink@v0.8.0+vendor", "blocked")):
            def graph_run(path, *args):
                return graph if args[0] == "hugo" else real_run(path, *args)

            with patch.object(updater, "run", graph_run):
                self.assertEqual(status, updater.inspect(site, version="v1.0.0")["status"])
                self.assertEqual(status == "blocked", updater.uses_vendor(site, "hugo"))

    def test_dirty_content_is_preserved_but_dirty_pins_need_explicit_selection(self):
        site = self.site()
        (site / "article.md").write_text("work in progress\n")
        self.assertEqual("ready", updater.inspect(site)["status"])
        (site / "go.sum").write_text("local change\n")
        self.assertEqual("blocked", updater.inspect(site)["status"])
        self.assertEqual("ready", updater.inspect(site, explicit=True)["status"])

    def test_old_branch_and_linked_worktree_are_skipped(self):
        site = self.site()
        linked = self.root / "editorial"
        subprocess.run(["git", "-C", str(site), "worktree", "add", "-qb", "editorial", str(linked)], check=True)
        self.assertEqual("skipped", updater.inspect(linked)["status"])
        subprocess.run(["git", "-C", str(site), "checkout", "-qb", "migration"], check=True)
        self.assertEqual("skipped", updater.inspect(site)["status"])

    def test_replacement_is_never_silently_overridden(self):
        site = self.site()
        with (site / "go.mod").open("a") as stream:
            stream.write("\nreplace github.com/pgsty/oink => ../oink\n")
        self.assertEqual("blocked", updater.inspect(site, explicit=True)["status"])

    def test_completed_uncommitted_upgrade_can_be_checked_again(self):
        site = self.site()
        (site / "go.mod").write_text((site / "go.mod").read_text().replace("v1.0.0", "v1.1.0"))
        (site / "go.sum").write_text(
            "github.com/pgsty/oink v1.1.0 h1:fixture\n"
            "github.com/pgsty/oink v1.1.0/go.mod h1:fixture\n")
        self.assertEqual("ready", updater.inspect(site, version="v1.1.0")["status"])
        self.assertEqual("blocked", updater.inspect(site, version="v1.2.0")["status"])

    def test_failed_update_restores_only_owned_files(self):
        site = self.site()
        before = {n: (site / n).read_bytes() for n in ("go.mod", "go.sum")}
        real_run = updater.run

        def failing_run(path, *args):
            if args[0] == "hugo":
                (site / "go.mod").write_text("partial update\n")
                (site / "go.sum").write_text("partial checksums\n")
                (site / "article.md").write_text("independent edit\n")
                raise RuntimeError("download failed")
            return real_run(path, *args)

        with patch.object(updater, "run", failing_run), self.assertRaises(RuntimeError):
            updater.update(site, "hugo", "v1.1.0", self.root / "backup")
        for name, data in before.items():
            self.assertEqual(data, (site / name).read_bytes())
        self.assertEqual("independent edit\n", (site / "article.md").read_text())

    def test_update_applies_required_go_version_bump_from_probe(self):
        site = self.site()
        (site / "go.mod").write_text(
            "module example.org/site\n\ngo 1.27.0\n\n"
            "require (\n\tgithub.com/pgsty/oink v1.5.1\n\texample.org/other v0.1.0\n)\n")
        (site / "go.sum").write_text(
            "example.org/other v0.1.0 h1:keep\n"
            "github.com/pgsty/oink v1.5.1 h1:old\n"
            "github.com/pgsty/oink v1.5.1/go.mod h1:oldmod\n")
        real_run = updater.run

        def fake_run(path, *args):
            if args[:3] == ("hugo", "mod", "get"):
                real_run(path, "go", "mod", "edit", "-go=1.27.4")
                (path / "go.sum").write_text(
                    "github.com/pgsty/oink v1.6.0 h1:new\n"
                    "github.com/pgsty/oink v1.6.0/go.mod h1:newmod\n")
                return "probe updated"
            if args[:3] == ("hugo", "mod", "graph"):
                return "example.org/site github.com/pgsty/oink@v1.6.0"
            return real_run(path, *args)

        with patch.object(updater, "run", fake_run):
            updater.update(site, "hugo", "v1.6.0", self.root / "backup")
        info = updater.module_info(site)
        self.assertEqual("1.27.4", info["Go"])
        requires = {r["Path"]: r["Version"] for r in info["Require"]}
        self.assertEqual({"github.com/pgsty/oink": "v1.6.0", "example.org/other": "v0.1.0"}, requires)
        sums = (site / "go.sum").read_text()
        self.assertIn("example.org/other v0.1.0 h1:keep", sums)
        self.assertIn("github.com/pgsty/oink v1.6.0 h1:new", sums)
        self.assertNotIn("v1.5.1", sums)

    def test_graph_rejects_stale_vendor_and_replacement(self):
        for graph in ("site github.com/pgsty/oink@v1.0.0",
                      "site github.com/pgsty/oink@v1.1.0 => ../oink",
                      "site github.com/pgsty/oink@v1.0.0+vendor"):
            with patch.object(updater, "run", return_value=graph), self.assertRaises(RuntimeError):
                updater.verify_graph(self.root, "hugo", "v1.1.0")

    def test_release_env_disables_both_workspace_mechanisms(self):
        with patch.dict(os.environ, {"GOWORK": "/tmp/go.work", "HUGO_MODULE_WORKSPACE": "/tmp/go.work",
                                     "HUGO_MODULE_REPLACEMENTS": "github.com/pgsty/oink -> ../oink"}):
            env = updater.release_env()
        self.assertEqual("off", env["GOWORK"])
        self.assertEqual("off", env["HUGO_MODULE_WORKSPACE"])
        self.assertNotIn("HUGO_MODULE_REPLACEMENTS", env)


if __name__ == "__main__":
    unittest.main()
