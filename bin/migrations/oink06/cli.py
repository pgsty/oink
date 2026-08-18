"""Command line: report / migrate / check."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import difflib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from .base import Finding, Result
from .scanner import Document
from .transforms import load

CONTENT_SUFFIXES = (".md", ".markdown")
SKIP_DIRS = {"node_modules", "public", "resources", ".git", "tmp", ".cache"}
EXTRA_RESIDUAL = (
    r"\{\{[<%]\s*_param\b",
    r"\{\{[<%]\s*iframe\b",
    r"\{\{[<%]\s*conditional-text\b",
    r"\{\{[<%]\s*blocks/",
    r"\{\{[<%]\s*(?:td/site-build-info/)?netlify\b",
)


def content_dir(site: Path) -> str:
    """Hugo ``contentDir`` from hugo.yaml / hugo.toml (default ``content``)."""

    for name in ("hugo.yaml", "hugo.yml", "config.yaml", "config.yml"):
        cfg = site / name
        if cfg.is_file():
            match = re.search(r"^contentDir:\s*['\"]?([^'\"#\n]+)", cfg.read_text(encoding="utf-8", errors="ignore"), re.M)
            if match:
                return match.group(1).strip()
    for name in ("hugo.toml", "config.toml"):
        cfg = site / name
        if cfg.is_file():
            match = re.search(r"^contentDir\s*=\s*['\"]([^'\"]+)", cfg.read_text(encoding="utf-8", errors="ignore"), re.M)
            if match:
                return match.group(1).strip()
    return "content"


def content_files(site: Path, paths: list[str] | None = None) -> list[Path]:
    roots = [site / p for p in paths] if paths else [site / content_dir(site)]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
            continue
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                if name.endswith(CONTENT_SUFFIXES):
                    files.append(Path(dirpath) / name)
    return sorted(files)


def validate_scan_targets(site: Path, paths: list[str] | None = None) -> list[str]:
    """Return fail-closed target errors before a report/check/migration run."""

    if not site.is_dir():
        return [f"site directory not found: {site}"]
    roots = [site / p for p in paths] if paths else [site / content_dir(site)]
    errors: list[str] = []
    for root in roots:
        resolved = root.resolve()
        try:
            resolved.relative_to(site)
        except ValueError:
            errors.append(f"scan target is outside the site: {root}")
            continue
        if not resolved.exists():
            errors.append(f"scan target not found: {root}")
    if not errors and not content_files(site, paths):
        errors.append(f"no Markdown content files found under {', '.join(str(root) for root in roots)}")
    return errors


def read_text(path: Path) -> str | None:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class FileOutcome:
    def __init__(self, path: Path, rel: str):
        self.path = path
        self.rel = rel
        self.original = ""
        self.final = ""
        self.counts: Counter = Counter()
        self.findings: list[Finding] = []
        self.changed = False
        self.idempotent = True
        self.error = ""


def migrate_text(rel: str, text: str, classes: list[type]) -> tuple[str, Counter, list[Finding]]:
    counts: Counter = Counter()
    findings: list[Finding] = []
    current = text
    for cls in classes:
        result: Result = cls().run(rel, current)
        current = result.text
        counts.update(result.counts)
        findings.extend(result.findings)
    return current, counts, findings


def process_site(site: Path, only: list[str] | None, paths: list[str] | None = None) -> list[FileOutcome]:
    classes = load(only)
    outcomes: list[FileOutcome] = []
    for path in content_files(site, paths):
        rel = str(path.relative_to(site))
        outcome = FileOutcome(path, rel)
        try:
            text = read_text(path)
        except OSError as exc:
            outcome.error = f"{type(exc).__name__}: {exc}"
            outcomes.append(outcome)
            continue
        if text is None:
            outcome.error = "not utf-8"
            outcomes.append(outcome)
            continue
        outcome.original = text
        try:
            final, counts, findings = migrate_text(rel, text, classes)
        except Exception as exc:  # defensive: one bad file must not stop the run
            outcome.error = f"{type(exc).__name__}: {exc}"
            outcomes.append(outcome)
            continue
        outcome.final = final
        outcome.counts = counts
        outcome.findings = findings
        outcome.changed = final != text
        if outcome.changed:
            second, _, _ = migrate_text(rel, final, classes)
            outcome.idempotent = second == final
        outcomes.append(outcome)
    return outcomes


def residual_findings(rel: str, text: str) -> list[Finding]:
    """Legacy syntax still present in ``text`` (outside fences)."""

    doc = Document.parse(text)
    findings: list[Finding] = []
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for cls in load():
        for pattern in cls.residual_patterns:
            patterns.append((cls.key, re.compile(pattern)))
    for pattern in EXTRA_RESIDUAL:
        patterns.append(("removed", re.compile(pattern)))
    for index in range(doc.front_matter_end, len(doc.lines)):
        if doc.in_fence[index]:
            continue
        line = doc.lines[index]
        for key, pattern in patterns:
            if pattern.search(line):
                findings.append(Finding(rel, index + 1, key, f"residual: {pattern.pattern}", line.strip()[:160]))
    for cls in load():
        hook = getattr(cls, "residual_findings", None)
        if hook is None:
            continue
        for line, reason, source in hook(cls(), doc):
            findings.append(Finding(rel, line + 1, cls.key, f"residual: {reason}", source[:160]))
    return findings


# --------------------------------------------------------------------- output
def outcome_json(outcomes: list[FileOutcome], *, include_residual: bool) -> dict:
    files = []
    totals: Counter = Counter()
    for outcome in outcomes:
        entry = {
            "path": outcome.rel,
            "changed": outcome.changed,
            "idempotent": outcome.idempotent,
            "counts": dict(sorted(outcome.counts.items())),
            "findings": [finding.__dict__ for finding in outcome.findings],
        }
        if outcome.error:
            entry["error"] = outcome.error
        if include_residual and outcome.final:
            entry["residual"] = [f.__dict__ for f in residual_findings(outcome.rel, outcome.final)]
        totals.update(outcome.counts)
        files.append(entry)
    return {
        "files": files,
        "totals": dict(sorted(totals.items())),
        "changed_files": sum(1 for o in outcomes if o.changed),
        "findings": sum(len(o.findings) for o in outcomes),
        "not_idempotent": [o.rel for o in outcomes if not o.idempotent],
        "errors": {o.rel: o.error for o in outcomes if o.error},
    }


def print_diff(outcome: FileOutcome, limit: int) -> None:
    diff = list(
        difflib.unified_diff(
            outcome.original.splitlines(),
            outcome.final.splitlines(),
            fromfile=f"a/{outcome.rel}",
            tofile=f"b/{outcome.rel}",
            lineterm="",
            n=1,
        )
    )
    for line in diff[:limit]:
        print(line)
    if len(diff) > limit:
        print(f"... ({len(diff) - limit} more diff lines)")


# ------------------------------------------------------------------- commands
def cmd_migrate(args: argparse.Namespace) -> int:
    site = args.site.resolve()
    target_errors = validate_scan_targets(site, args.paths)
    if target_errors:
        for error in target_errors:
            print(error, file=sys.stderr)
        return 2
    only = args.only.split(",") if args.only else None
    outcomes = process_site(site, only, args.paths)
    changed = [o for o in outcomes if o.changed]
    totals: Counter = Counter()
    for outcome in outcomes:
        totals.update(outcome.counts)
    print(f"# oink06 migrate {'--write' if args.write else '(dry-run)'} {site}")
    print(f"files scanned: {len(outcomes)}  changed: {len(changed)}  findings: {sum(len(o.findings) for o in outcomes)}")
    for key, value in sorted(totals.items()):
        print(f"  {key}: {value}")
    if not args.quiet:
        for outcome in changed:
            print(f"\n## {outcome.rel}  ({'+'.join(f'{k}={v}' for k, v in sorted(outcome.counts.items()) if not k.startswith('xref'))})")
            print_diff(outcome, args.diff_lines)
    findings = [f for o in outcomes for f in o.findings]
    if findings:
        print("\n## findings (left unchanged)")
        for finding in findings:
            print(f"{finding.path}:{finding.line}: [{finding.kind}] {finding.reason} — {finding.source}")
    bad = [o.rel for o in outcomes if not o.idempotent]
    if bad:
        print("\n## NOT IDEMPOTENT (second run changes the text again):")
        for rel in bad:
            print(f"  {rel}")
    errors = {o.rel: o.error for o in outcomes if o.error}
    for rel, error in errors.items():
        print(f"ERROR {rel}: {error}")
    if args.json:
        args.json.write_text(json.dumps(outcome_json(outcomes, include_residual=False), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and (bad or errors):
        print("\nwrote 0 file(s): resolve errors and non-idempotent transforms first")
    elif args.write:
        written = 0
        for outcome in changed:
            if not outcome.idempotent:
                print(f"skip (not idempotent): {outcome.rel}")
                continue
            atomic_write(outcome.path, outcome.final)
            written += 1
        print(f"\nwrote {written} file(s)")
    else:
        print("\n(dry-run: pass --write to rewrite files)")
    return 1 if (bad or errors) else 0


def cmd_check(args: argparse.Namespace) -> int:
    site = args.site.resolve()
    target_errors = validate_scan_targets(site, args.paths)
    if target_errors:
        for error in target_errors:
            print(error, file=sys.stderr)
        return 2
    findings: list[Finding] = []
    errors: list[str] = []
    for path in content_files(site, args.paths):
        try:
            text = read_text(path)
        except OSError as exc:
            errors.append(f"{path.relative_to(site)}: {type(exc).__name__}: {exc}")
            continue
        if text is None:
            errors.append(f"{path.relative_to(site)}: not utf-8")
            continue
        try:
            findings.extend(residual_findings(str(path.relative_to(site)), text))
        except Exception as exc:
            errors.append(f"{path.relative_to(site)}: {type(exc).__name__}: {exc}")
    for finding in findings:
        print(f"{finding.path}:{finding.line}: [{finding.kind}] {finding.reason} — {finding.source}")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    print(f"{len(findings)} residual legacy construct(s) in {site}")
    return 2 if errors else (1 if findings else 0)


def cmd_report(args: argparse.Namespace) -> int:
    from .report import build_report, render_markdown

    sites = [p.resolve() for p in args.sites]
    target_errors = [error for site in sites for error in validate_scan_targets(site)]
    if target_errors:
        for error in target_errors:
            print(error, file=sys.stderr)
        return 2
    only = args.only.split(",") if args.only else None
    report = build_report(sites, only)
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    if args.notes and args.notes.is_file():
        markdown += "\n" + args.notes.read_text(encoding="utf-8")
    if args.md:
        args.md.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    has_errors = any(
        finding.get("kind") == "error"
        for site in report["sites"].values()
        for finding in site["findings"]
    )
    return 1 if has_errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oink06", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    migrate = sub.add_parser("migrate", help="rewrite one site (dry-run unless --write)")
    migrate.add_argument("--site", type=Path, required=True)
    migrate.add_argument("--only", help="comma-separated transformation keys")
    migrate.add_argument("--paths", nargs="*", help="files/dirs relative to the site (default: content)")
    migrate.add_argument("--write", action="store_true")
    migrate.add_argument("--json", type=Path)
    migrate.add_argument("--quiet", action="store_true", help="suppress diffs")
    migrate.add_argument("--diff-lines", type=int, default=40)
    migrate.set_defaults(func=cmd_migrate)

    check = sub.add_parser("check", help="scan for residual legacy syntax (exit 1 if any)")
    check.add_argument("--site", type=Path, required=True)
    check.add_argument("--paths", nargs="*")
    check.set_defaults(func=cmd_check)

    report = sub.add_parser("report", help="read-only inventory over many sites")
    report.add_argument("--sites", nargs="+", type=Path, required=True)
    report.add_argument("--only")
    report.add_argument("--json", type=Path)
    report.add_argument("--md", type=Path)
    report.add_argument("--notes", type=Path, help="Markdown appended verbatim to the report (open questions, site notes)")
    report.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
