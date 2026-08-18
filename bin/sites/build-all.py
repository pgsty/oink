#!/usr/bin/env python3
"""Strict-build the maintained sites in isolated snapshots against this theme.

HEAD is the default; ``--ref`` selects another revision and ``--worktree``
copies the current tree. A scratch ``go.work`` replaces OINK without modifying
the source checkout. ``--keep`` retains builds and ``--baseline`` compares two
retained public trees by output surface.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITES_FILE = Path(__file__).resolve().parent / "sites.txt"

_spec = importlib.util.spec_from_file_location("measure_baseline", ROOT / "bin/measure-baseline.py")
_mb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mb)  # type: ignore[union-attr]
snapshot_site = _mb.snapshot_site
prepare_workspace = _mb.prepare_workspace


def default_sites() -> list[Path]:
    sites = []
    for line in SITES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            sites.append((ROOT.parent / line).resolve())
    return sites


def snapshot_ref(site: Path, dest: Path, ref: str) -> dict:
    """Detached shared clone of `ref` (branch, tag or sha) — falls back to HEAD when absent."""
    dest.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(dest, ignore_errors=True)
    have = subprocess.run(["git", "-C", str(site), "rev-parse", "--verify", "--quiet", ref], capture_output=True, text=True)
    if have.returncode != 0:
        return {**snapshot_site(site, dest), "ref": "HEAD", "ref_missing": ref}
    sha = have.stdout.strip()
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(site), str(dest)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", "--detach", sha], check=True, capture_output=True)
    return {"snapshot": "ref", "revision": sha, "branch": ref, "ref": ref, "dirty_worktree": bool(subprocess.run(["git", "-C", str(site), "status", "--porcelain"], capture_output=True, text=True).stdout.strip())}


def build(snapshot: Path, hugo: str) -> dict:
    env = dict(os.environ)
    prepare_workspace(snapshot, ROOT)
    if (snapshot / "go.work").exists():
        env["HUGO_MODULE_WORKSPACE"] = str(snapshot / "go.work")
    dest = snapshot / "public"
    shutil.rmtree(dest, ignore_errors=True)
    cmd = [
        hugo, "--source", str(snapshot), "--destination", str(dest), "--minify",
        "--printPathWarnings", "--panicOnWarning",
        "--ignoreVendorPaths", "github.com/pgsty/oink",
    ]
    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    wall = time.perf_counter() - start
    output = result.stdout + result.stderr
    errors = [line for line in output.splitlines() if line.startswith(("ERROR", "WARN"))]
    pages = sum(1 for _ in dest.rglob("*.html")) if dest.exists() else 0
    return {"ok": result.returncode == 0, "wall_seconds": round(wall, 2), "pages": pages, "errors": errors[:40], "error_count": len(errors), "public": str(dest)}


def surface(rel: str) -> str:
    if rel.startswith("_print/") or "/_print/" in rel:
        return "print"
    if rel.endswith(".html"):
        return "html"
    if rel.endswith(".md"):
        return "md"
    if rel.endswith(".xml"):
        return "xml"
    if rel.endswith((".txt", ".json")):
        return "text"
    return "other"


def diff_public(before: Path, after: Path) -> dict:
    """Which files changed between two public/ trees, grouped by surface."""
    def listing(root: Path) -> dict[str, bytes]:
        out = {}
        for p in root.rglob("*"):
            if p.is_file():
                out[p.relative_to(root).as_posix()] = p.read_bytes()
        return out
    a = listing(before) if before.exists() else {}
    b = listing(after) if after.exists() else {}
    changed = {"added": [], "removed": [], "modified": []}
    for rel in sorted(set(a) | set(b)):
        if rel not in a:
            changed["added"].append(rel)
        elif rel not in b:
            changed["removed"].append(rel)
        elif a[rel] != b[rel]:
            changed["modified"].append(rel)
    by_surface: dict[str, int] = {}
    for kind in changed.values():
        for rel in kind:
            by_surface[surface(rel)] = by_surface.get(surface(rel), 0) + 1
    return {"counts": {k: len(v) for k, v in changed.items()}, "by_surface": by_surface, "sample": {k: v[:8] for k, v in changed.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sites", nargs="*", type=Path)
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--ref", default="HEAD", help="git ref to build (falls back to HEAD when a site lacks it)")
    parser.add_argument("--worktree", action="append", default=[], help="build this site's working tree instead of a ref (repeatable)")
    parser.add_argument("--keep", type=Path, help="keep snapshots and public/ trees here")
    parser.add_argument("--baseline", type=Path, help="a previous --keep directory to diff against")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--md", type=Path)
    args = parser.parse_args()

    sites = [p.resolve() for p in args.sites] if args.sites else default_sites()
    work = args.keep.resolve() if args.keep else Path(tempfile.mkdtemp(prefix="oink-sites-"))
    work.mkdir(parents=True, exist_ok=True)
    theme_sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    report = {"generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "theme": theme_sha, "hugo": args.hugo, "ref": args.ref, "sites": {}}
    for site in sites:
        name = site.name
        print(f"== {name}", file=sys.stderr, flush=True)
        snap = work / name
        if not site.is_dir():
            report["sites"][name] = {"path": str(site), "ok": False, "errors": ["site directory missing"]}
            continue
        if name in args.worktree or str(site) in args.worktree or not (site / ".git").exists():
            meta = snapshot_site(site, snap, worktree=True)
        elif args.ref == "HEAD":
            meta = snapshot_site(site, snap)
        else:
            meta = snapshot_ref(site, snap, args.ref)
        result = build(snap, args.hugo)
        entry = {"path": str(site), **meta, **result}
        if args.baseline and (args.baseline / name / "public").exists():
            entry["diff_vs_baseline"] = diff_public(args.baseline / name / "public", Path(result["public"]))
        report["sites"][name] = entry
    ok = sum(1 for s in report["sites"].values() if s.get("ok"))
    total = len(report["sites"])
    lines = [f"# Site builds — theme {theme_sha}, ref {args.ref}, {report['generated_at']}", "",
             f"{ok}/{total} strict builds passed", "", "| site | snapshot | revision | strict | s | pages | errors | first error |", "| --- | --- | --- | --- | ---: | ---: | ---: | --- |"]
    for name, s in report["sites"].items():
        first = (s.get("errors") or [""])[0][:110].replace("|", "\\|")
        rev = (s.get("revision") or "")[:8]
        lines.append(f"| {name} | {s.get('snapshot', '')}{' (dirty)' if s.get('dirty_worktree') else ''} | {rev} | {'ok' if s.get('ok') else 'FAIL'} | {s.get('wall_seconds', '')} | {s.get('pages', '')} | {s.get('error_count', '')} | {first} |")
    if args.baseline:
        lines += ["", "## Output diff vs baseline", "", "| site | added | removed | modified | by surface |", "| --- | ---: | ---: | ---: | --- |"]
        for name, s in report["sites"].items():
            d = s.get("diff_vs_baseline")
            if d:
                lines.append(f"| {name} | {d['counts']['added']} | {d['counts']['removed']} | {d['counts']['modified']} | {d['by_surface']} |")
    markdown = "\n".join(lines) + "\n"
    print(markdown)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.md:
        args.md.write_text(markdown, encoding="utf-8")
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
