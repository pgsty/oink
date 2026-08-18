"""Read-only inventory over many sites (JSON + Markdown)."""

from __future__ import annotations

from collections import Counter, defaultdict
import datetime as dt
from pathlib import Path

from .cli import process_site, residual_findings
from .transforms import load

MAX_FINDINGS_PER_REASON = 40


def build_report(sites: list[Path], only: list[str] | None) -> dict:
    keys = [cls.key for cls in load(only)]
    report: dict = {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "transformations": keys,
        "sites": {},
    }
    for site in sites:
        outcomes = process_site(site, only)
        totals: Counter = Counter()
        findings = []
        residual = []
        changed = 0
        for outcome in outcomes:
            totals.update(outcome.counts)
            findings.extend(f.__dict__ for f in outcome.findings)
            if outcome.changed:
                changed += 1
            text = outcome.final or outcome.original
            if text and not outcome.error:
                residual.extend(f.__dict__ for f in residual_findings(outcome.rel, text))
            if outcome.error:
                findings.append({"path": outcome.rel, "line": 0, "kind": "error", "reason": outcome.error, "source": ""})
        report["sites"][site.name] = {
            "path": str(site),
            "files": len(outcomes),
            "changed_files": changed,
            "not_idempotent": [o.rel for o in outcomes if not o.idempotent],
            "counts": dict(sorted(totals.items())),
            "findings": findings,
            "residual": residual,
        }
    return report


def _fmt(value: int) -> str:
    return str(value) if value else ""


def render_markdown(report: dict) -> str:
    sites = report["sites"]
    lines: list[str] = []
    lines.append(f"# OINK 0.5 migration inventory — {report['generated_at']}")
    lines.append("")
    lines.append("Read-only dry-run of `bin/migrations/oink06.py` over the listed sites. Counts are conversions the")
    lines.append("scripts would perform; findings are constructs left untouched (with the reason).")
    lines.append("")
    # summary ------------------------------------------------------------------
    columns = [
        ("alert", "alert"), ("details", "details"), ("td-page-notice", "td-page-notice"), ("rawdetails", "raw <details>"),
        ("tabpane", "tabpane"), ("codegroup", "code-group"), ("filetree", "filetree"), ("filetree.list", "{.filetree} list"), ("gallery", "gallery"), ("gallery.list", "{.gallery} list"),
        ("echarts", "echarts"), ("infographic", "infographic"), ("cards", "cards"), ("imgproc", "imgproc"),
        ("readfile", "readfile"), ("fencetitle", "filename="), ("badge.outline_dropped", "badge outline"),
        ("example", "example"), ("xref.kindless", "xref (no kind)"),
        ("frontmatter.manual_link", "manualLink"), ("frontmatter.ui_lift", "ui.* lifted"), ("frontmatter.feedback", "hide_feedback"),
        ("frontmatter.search_exclude", "exclude_search"), ("frontmatter.reading_time", "hide_readingtime"),
    ]
    lines.append("## 1. Conversions per site")
    lines.append("")
    lines.append("| site | files | changed | " + " | ".join(label for _, label in columns) + " | findings | residual |")
    lines.append("| --- | ---: | ---: | " + " | ".join("---:" for _ in columns) + " | ---: | ---: |")
    total: Counter = Counter()
    for name, data in sites.items():
        counts = data["counts"]
        total.update(counts)
        cells = [_fmt(counts.get(key, 0)) for key, _ in columns]
        lines.append(f"| {name} | {data['files']} | {data['changed_files']} | " + " | ".join(cells) + f" | {len(data['findings'])} | {len(data['residual'])} |")
    cells = [_fmt(total.get(key, 0)) for key, _ in columns]
    lines.append("| **total** | | | " + " | ".join(cells) + f" | {sum(len(d['findings']) for d in sites.values())} | {sum(len(d['residual']) for d in sites.values())} |")
    lines.append("")
    # tabpane classification ---------------------------------------------------
    lines.append("## 2. Tabpane classification")
    lines.append("")
    lines.append("| site | code_only → fences | prose_simple → % tabs | headings → % tabs | shortcodes → % tabs | grouped | disabled tabs dropped | selected dropped | indented prose skipped |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for name, data in sites.items():
        c = data["counts"]
        skipped = sum(1 for f in data["findings"] if "indented" in f["reason"] and f["kind"] == "tabs")
        lines.append(
            f"| {name} | {_fmt(c.get('tabpane.code_only', 0))} | {_fmt(c.get('tabpane.prose_simple', 0))} | {_fmt(c.get('tabpane.headings', 0))} | "
            f"{_fmt(c.get('tabpane.shortcodes', 0))} | {_fmt(c.get('tabpane.grouped', 0))} | {_fmt(c.get('tabs.disabled_tab_dropped', 0))} | "
            f"{_fmt(c.get('tabs.selected_dropped', 0))} | {_fmt(skipped)} |"
        )
    lines.append("")
    # dropped parameters -------------------------------------------------------
    lines.append("## 3. Dropped / notable parameters")
    lines.append("")
    dropped_keys = sorted(k for k in total if k.endswith("_dropped") or k in ("cards.desc_param_token", "codegroup.sync_as_group", "codegroup.persist_false", "tabs.right_dropped", "tabs.highlight_dropped"))
    if dropped_keys:
        lines.append("| key | total | sites |")
        lines.append("| --- | ---: | --- |")
        for key in dropped_keys:
            where = ", ".join(f"{n} ({d['counts'][key]})" for n, d in sites.items() if d["counts"].get(key))
            lines.append(f"| `{key}` | {total[key]} | {where} |")
    else:
        lines.append("(none)")
    lines.append("")
    # findings -----------------------------------------------------------------
    lines.append("## 4. Findings (left unchanged; file:line — reason)")
    lines.append("")
    grouped: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for name, data in sites.items():
        for finding in data["findings"]:
            grouped[f"[{finding['kind']}] {finding['reason']}"].append((name, finding))
    if not grouped:
        lines.append("(none)")
    for reason, items in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"### {reason} — {len(items)}")
        lines.append("")
        for name, finding in items[:MAX_FINDINGS_PER_REASON]:
            source = finding.get("source", "").replace("|", "\\|")
            lines.append(f"- `{name}/{finding['path']}:{finding['line']}` {source[:100]}")
        if len(items) > MAX_FINDINGS_PER_REASON:
            lines.append(f"- … {len(items) - MAX_FINDINGS_PER_REASON} more (see JSON)")
        lines.append("")
    # residual -----------------------------------------------------------------
    lines.append("## 5. Residual legacy syntax after the dry-run (what `check` would still flag)")
    lines.append("")
    residual_grouped: Counter = Counter()
    for name, data in sites.items():
        for finding in data["residual"]:
            residual_grouped[(name, finding["kind"], finding["reason"])] += 1
    if not residual_grouped:
        lines.append("(none)")
    else:
        lines.append("| site | kind | reason | count |")
        lines.append("| --- | --- | --- | ---: |")
        for (name, kind, reason), count in sorted(residual_grouped.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| {name} | {kind} | `{reason.replace('|', '\\|')}` | {count} |")
    lines.append("")
    bad = [(n, p) for n, d in sites.items() for p in d["not_idempotent"]]
    if bad:
        lines.append("## NOT idempotent")
        lines.append("")
        for name, path in bad:
            lines.append(f"- {name}/{path}")
        lines.append("")
    return "\n".join(lines) + "\n"
