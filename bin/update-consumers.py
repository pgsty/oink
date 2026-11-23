#!/usr/bin/env python3
"""Inventory or update published OINK pins in sibling Hugo repositories."""

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

MODULE = "github.com/pgsty/oink"
CONFIG_NAMES = ("hugo.yaml", "hugo.yml", "hugo.toml", "hugo.json",
                "config.yaml", "config.yml", "config.toml", "config.json")


def release_env():
    env = os.environ.copy()
    env.pop("HUGO_MODULE_REPLACEMENTS", None)
    env.pop("HUGO_PANICONWARNING", None)
    env["GOWORK"] = "off"
    env["HUGO_MODULE_WORKSPACE"] = "off"
    return env


def run(site, *args):
    result = subprocess.run(args, cwd=site, env=release_env(), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{result.stdout}")
    return result.stdout.strip()


def git(site, *args):
    try:
        return run(site, "git", *args)
    except RuntimeError:
        return ""


def module_info(site):
    return json.loads(run(site, "go", "mod", "edit", "-json"))


def pin(info):
    return next((r["Version"] for r in info.get("Require") or []
                 if r["Path"] == MODULE), None)


def has_checksums(site, version):
    sums = site / "go.sum"
    if not version or not sums.exists():
        return False
    versions = {parts[1] for line in sums.read_text().splitlines()
                if len(parts := line.split()) == 3 and parts[0] == MODULE}
    return {version, version + "/go.mod"}.issubset(versions)


def imports_theme(site):
    files = [site / name for name in CONFIG_NAMES]
    if (site / "config").is_dir():
        files.extend(p for p in (site / "config").rglob("*")
                     if p.suffix in (".yaml", ".yml", ".toml", ".json"))
    return any(p.is_file() and MODULE in p.read_text() for p in files)


def hugo_config(site, hugo):
    raw = run(site, hugo, "config", "--format", "json")
    # Hugo can surround its JSON with module-download progress messages.
    return json.JSONDecoder().raw_decode(raw[raw.index("{"):])[0]


def uses_vendor(site, hugo):
    vendor = site / "_vendor/modules.txt"
    if not vendor.exists() or MODULE not in vendor.read_text():
        return False
    # A retained snapshot can be deliberately bypassed by ignoreVendorPaths.
    # Hugo's resolved graph, rather than the directory's presence, owns this.
    graph = run(site, hugo, "mod", "graph")
    return any(line.split()[-1].startswith(MODULE + "@")
               and line.split()[-1].endswith("+vendor")
               for line in graph.splitlines() if line.split())


def inspect(site, explicit=False, refresh_vendor=False, version=None, hugo="hugo"):
    if not (site / "go.mod").is_file():
        classic = site / "themes/oink/go.mod"
        if (classic.is_file() and MODULE in classic.read_text()
                and any((site / name).is_file() for name in CONFIG_NAMES)
                and "oink" in hugo_config(site, hugo).get("theme", [])):
            return {"site": str(site), "before": None, "status": "skipped",
                    "kind": "classic", "reason": "classic themes/oink; update its submodule or reviewed source copy separately"}
        return None
    if MODULE not in (site / "go.mod").read_text() and not imports_theme(site):
        return None
    info = module_info(site)
    if not pin(info) and not imports_theme(site):
        return None
    item = {"site": str(site), "before": pin(info), "status": "ready"}
    reason = None
    if not git(site, "rev-parse", "--show-toplevel") and not explicit:
        reason = "not a Git checkout; review and select with --sites"
    elif not explicit:
        branch = git(site, "branch", "--show-current")
        default = git(site, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        default = default.removeprefix("origin/") if default else "main"
        git_dir = git(site, "rev-parse", "--absolute-git-dir")
        common = git(site, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if git_dir != common:
            reason = "linked worktree; update its primary checkout"
        elif branch != default:
            reason = f"branch {branch or '(detached)'}; default is {default}"
    if reason:
        item.update(status="skipped", reason=reason)
    elif any(r["Old"]["Path"] == MODULE for r in info.get("Replace") or []):
        item.update(status="blocked", reason="go.mod replaces OINK; review manually")
    elif ((site / "_vendor/modules.txt").exists()
          and f"# {MODULE} {version}\n" not in (site / "_vendor/modules.txt").read_text()
          and not refresh_vendor and uses_vendor(site, hugo)):
        item.update(status="blocked", reason="vendored modules require a separate vendor refresh")
    elif (git(site, "status", "--porcelain", "--", "go.mod", "go.sum") and not explicit
          and not (pin(info) == version and has_checksums(site, version))):
        item.update(status="blocked", reason="module files have local changes; review and select with --sites")
    return item


def discover(roots, sites, refresh_vendor=False, version=None, hugo="hugo"):
    # Do not recurse into archives, generated output, caches, or theme fixtures.
    candidates = set()
    items = []
    for root in roots:
        root = root.expanduser().resolve()
        try:
            projects = [p for p in root.iterdir()
                        if p.is_dir() and not p.name.startswith(".")]
            candidates.update(p.resolve() for p in projects)
            # A primary project can put its reader-facing Hugo site here.
            # Do not walk arbitrary nested archives or review snapshots.
            candidates.update((p / "site").resolve() for p in projects
                              if p.name not in ("archive", "archives", "backup", "backups")
                              and not any((p / name).is_file() for name in CONFIG_NAMES)
                              and any((p / "site" / name).is_file() for name in CONFIG_NAMES))
        except OSError as error:
            items.append({"site": str(root), "before": None, "status": "failed",
                          "reason": f"cannot scan root: {error}"})
    explicit = set()
    for selected in sites:
        try:
            site = selected.expanduser().resolve()
            if (not any((site / name).is_file() for name in CONFIG_NAMES)
                    and any((site / "site" / name).is_file() for name in CONFIG_NAMES)
                    and not imports_theme(site)):
                module = site / "go.mod"
                root_consumer = (module.is_file() and MODULE in module.read_text()
                                 and pin(module_info(site)))
                if not root_consumer:
                    site = (site / "site").resolve()
            explicit.add(site)
        except (RuntimeError, OSError, ValueError) as error:
            items.append({"site": str(selected), "before": None, "status": "failed",
                          "reason": f"cannot resolve explicit site: {error}"})
    candidates.update(explicit)
    for site in sorted(candidates):
        try:
            item = inspect(site, site in explicit, refresh_vendor, version, hugo)
            if item is None and site in explicit:
                item = {"site": str(site), "before": None, "status": "failed",
                        "reason": "explicit site is missing or is not an OINK consumer"}
        except (RuntimeError, OSError, ValueError) as error:
            item = {"site": str(site), "before": None, "status": "failed",
                    "reason": f"cannot inspect consumer: {error}"}
        if item:
            items.append(item)
    return items


def verify_graph(site, hugo, version, vendored=False):
    graph = run(site, hugo, "mod", "graph")
    matches = [line for line in graph.splitlines() if MODULE + "@" in line]
    expected = MODULE + "@" + version + ("+vendor" if vendored else "")
    if not matches or any(line.split()[-1] != expected
                          for line in matches):
        raise RuntimeError(f"expected published {MODULE}@{version}; got:\n{graph}")
    return graph


def update(site, hugo, version, backup, refresh_vendor=False):
    names = ("go.mod", "go.sum")
    original = {name: (site / name).read_bytes() if (site / name).exists() else None
                for name in names}
    backup.mkdir(parents=True, exist_ok=True)
    for name, data in original.items():
        if data is not None:
            (backup / name).write_bytes(data)
    before = module_info(site)
    vendor = site / "_vendor"
    vendored = uses_vendor(site, hugo)
    if vendored and refresh_vendor:
        shutil.copytree(vendor, backup / "_vendor")
    try:
        # Resolve in a small Hugo module so `go get` never traverses or updates
        # the unrelated dependencies of a mixed Go application/Hugo site.
        with tempfile.TemporaryDirectory(prefix="oink-release-probe-") as directory:
            probe = Path(directory)
            (probe / "go.mod").write_text(
                f"module example.org/oink-release-probe\n\ngo {before['Go']}\n\nrequire {MODULE} {version}\n")
            (probe / "hugo.yaml").write_text(f"module:\n  imports:\n    - path: {MODULE}\n")
            output = run(probe, hugo, "mod", "get", MODULE + "@" + version)
            verify_graph(probe, hugo, version)
            probe_go = module_info(probe).get("Go")
            sums = [line for line in (probe / "go.sum").read_text().splitlines()
                    if line.startswith(MODULE + " ") and line.split()[1] in (version, version + "/go.mod")]
            if {line.split()[1] for line in sums} != {version, version + "/go.mod"}:
                raise RuntimeError("release probe did not resolve both OINK checksums")
        run(site, "go", "mod", "edit", "-require=" + MODULE + "@" + version)
        if probe_go and probe_go != before.get("Go"):
            run(site, "go", "mod", "edit", "-go=" + probe_go)
            before["Go"] = probe_go
        current_sums = (site / "go.sum").read_text().splitlines() if (site / "go.sum").exists() else []
        retained = [line for line in current_sums if not line.startswith(MODULE + " ")]
        position = next((i for i, line in enumerate(retained)
                         if line.split() and line.split()[0] > MODULE), len(retained))
        (site / "go.sum").write_text("\n".join(retained[:position] + sums + retained[position:]) + "\n")
        after = module_info(site)
        # A theme-only update must not rewrite a mixed Go application's dependencies.
        for info in (before, after):
            info["Require"] = [r for r in info.get("Require") or [] if r["Path"] != MODULE]
        if before != after:
            raise RuntimeError("update changed module settings or dependencies other than OINK")
        if vendored and refresh_vendor:
            output += "\n" + run(site, hugo, "mod", "vendor")
        verify_graph(site, hugo, version, vendored)
        return output
    except Exception:
        for name, data in original.items():
            if data is None:
                (site / name).unlink(missing_ok=True)
            else:
                (site / name).write_bytes(data)
        if vendored and refresh_vendor:
            shutil.rmtree(vendor, ignore_errors=True)
            shutil.copytree(backup / "_vendor", vendor)
        raise


class Appearance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = {}
        self.styles = set()
        self.redirect = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.root = attrs
        if tag == "input" and "data-td-preset-value" in attrs:
            self.styles.add(attrs["data-td-preset-value"])
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.redirect = True


def check_appearance(public, config):
    # Sites may intentionally disable Home. Check their documentation entry
    # instead, and omit Hugo's redirect aliases rather than treating them as UI.
    entry = "docs/index.html" if "home" in config.get("disablekinds", []) else "index.html"
    candidates = [public / entry] + [public / lang / entry for lang in config.get("languages", {})]
    checked = []
    for path in candidates:
        if not path.exists():
            continue
        page = Appearance()
        page.feed(path.read_text())
        if page.redirect:
            continue
        if (page.root.get("data-td-site-preset") != "paper"
                or page.root.get("data-td-preset") != "paper"
                or page.styles != {"paper", "slate", "ink", "terminal"}):
            raise RuntimeError(f"{path.relative_to(public)}: expected Paper default and all four style controls")
        checked.append(str(path.relative_to(public)))
    if not checked:
        raise RuntimeError("appearance check found no rendered entry pages")
    return "Appearance passed: " + ", ".join(checked)


def check(site, hugo, version, appearance=False):
    graph = verify_graph(site, hugo, version, uses_vendor(site, hugo))
    if appearance:
        config = hugo_config(site, hugo)
    with tempfile.TemporaryDirectory(prefix="oink-consumer-build-") as directory:
        public = Path(directory) / "public"
        output = run(site, hugo, "--environment", "production", "--minify",
                     "--printPathWarnings", "--printI18nWarnings",
                     "--destination", str(public),
                     "--noBuildLock")
        if appearance:
            output += "\n" + check_appearance(public, config)
    return graph + "\n" + output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="explicit published tag, e.g. v1.3.2")
    parser.add_argument("--roots", nargs="*", type=Path,
                        default=[Path("~/www"), Path("~/pgsty")],
                        help="scan primary projects and their site/ directories (default: ~/www ~/pgsty)")
    parser.add_argument("--sites", nargs="*", type=Path, default=[],
                        help="include reviewed sites, including dirty modules or directories without Git")
    parser.add_argument("--write", action="store_true", help="update pins; otherwise inventory only")
    parser.add_argument("--check", action="store_true", help="verify the published graph and build every selected site with warnings visible")
    parser.add_argument("--check-appearance", action="store_true",
                        help="with --check, require Paper default and all four styles on rendered entry pages")
    parser.add_argument("--refresh-vendor", action="store_true", help="back up and regenerate reviewed vendored themes")
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--report-dir", type=Path, help="directory for JSON, logs, and original module files")
    args = parser.parse_args()
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", args.version):
        parser.error("select an explicit release tag, not a branch or @latest")
    if args.check_appearance and not args.check:
        parser.error("--check-appearance requires --check")
    items = discover(args.roots, args.sites, args.refresh_vendor, args.version, args.hugo)
    if not items:
        parser.error("no OINK consumers found")
    report = args.report_dir
    if args.write or args.check:
        report = report or Path(tempfile.mkdtemp(prefix="oink-consumers-"))
    if report:
        report = report.expanduser().resolve()
        report.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items):
        site = Path(item["site"])
        if item["status"] == "ready":
            try:
                log = ""
                key = f"{index:02d}-{site.name}"
                vendor = site / "_vendor/modules.txt"
                stale_vendor = (vendor.exists() and MODULE in vendor.read_text()
                                and f"# {MODULE} {args.version}\n" not in vendor.read_text()
                                and uses_vendor(site, args.hugo))
                if item["before"] == args.version and not stale_vendor and has_checksums(site, args.version):
                    item["status"] = "current"
                elif args.write:
                    log = update(site, args.hugo, args.version, report / "before" / key, args.refresh_vendor)
                    item["status"] = "updated"
                else:
                    item["status"] = "pending"
                if args.check and item["status"] != "pending":
                    print(f"BUILD {site}", flush=True)
                    log += "\n" + check(site, args.hugo, args.version, args.check_appearance)
                    item["build"] = "passed"
                if report:
                    path = report / f"{key}.log"
                    path.write_text(log + "\n")
                    item["log"] = str(path)
            except (RuntimeError, OSError) as error:
                item["reason"] = str(error)
                if item["status"] in ("updated", "current"):
                    item["build"] = "failed"
                else:
                    item["status"] = "failed"
                if report:
                    (report / f"{key}.log").write_text(str(error) + "\n")
        print(f"{item['status'].upper():8} {site}: {item['before'] or '(unpinned)'} -> {args.version}"
              + (f" [{item.get('build')}]" if item.get("build") else "")
              + (f" — {item['reason'].splitlines()[0]}" if item.get("reason") else ""), flush=True)
        if report:
            (report / "report.json").write_text(json.dumps(
                {"version": args.version, "sites": items}, ensure_ascii=False, indent=2) + "\n")
    if report:
        print(f"Report: {report / 'report.json'}")
    return int(any(i["status"] in ("blocked", "failed", "pending") or i.get("build") == "failed"
                   for i in items))


if __name__ == "__main__":
    raise SystemExit(main())
