#!/usr/bin/env python3
"""Dry-run-first migrations for the PRD 5 Book primitives.

The profiles intentionally recognize only the legacy forms observed in TPME,
DDIA, and pg-internal. Unknown or ambiguous forms are reported and left
untouched. Files are changed only with ``--write``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Iterable


NUMBER = r"[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*"
ID = r"[A-Za-z][A-Za-z0-9_.:-]*"
IMAGE_RE = re.compile(
    r'^\s*!\[(?P<alt>[^\]]*)\]\((?P<src>[^\s)]+)(?:\s+["\'][^"\']*["\'])?\)\s*$'
)
TPME_CAPTION_RE = re.compile(
    rf"^######\s+(?P<label>图|表|Figure|Table)\s+(?P<num>{NUMBER})[.:：。]\s*"
    rf"(?P<caption>.*?)\s+\{{#(?P<anchor>{ID})\}}\s*$"
)
SHORTCODE_PARAM_RE = re.compile(
    r"(?P<name>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?P<value>\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*')"
)
DDIA_FIGURE_RE = re.compile(r"^\s*\{\{<\s*figure(?P<body>.*?)>\}\}\s*$")
DDIA_FIGURE_CLOSE_RE = re.compile(r"^\s*\{\{<\s*/figure\s*>\}\}\s*$")
NUMBERED_LABEL_RE = re.compile(
    rf"^(?P<label>图|表|Figure|Table)\s*(?P<num>{NUMBER})\s*[.:：。]?\s*(?P<caption>.*)$"
)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[(?P<label>[^\]\n]+)\]\((?P<href>/[^)\s]+)\)")
PROTECTED_INLINE_RE = re.compile(r"`[^`\n]*`|!?\[[^\]\n]*\]\([^)]*\)|\{\{<.*?>\}\}")
PLAIN_CAPTION_FORBIDDEN_RE = re.compile(r"[`*\[\]]")
DDIA_EXAMPLE_RE = re.compile(rf"^(?:示例|Example)\s+(?P<num>{NUMBER})[.:：。]\s*(?P<caption>.+)$")


PROFILE_DEFAULTS = {
    "tpme": ("content/zh",),
    "ddia-v2": ("content/zh",),
    "ddia-v1": ("content/v1",),
    "pg-internal": ("content",),
}


@dataclass(frozen=True)
class Target:
    kind: str
    num: str
    anchor: str
    path: str
    page: str
    src: str = ""


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    reason: str
    source: str


@dataclass
class MigrationResult:
    sources: dict[Path, str]
    counts: Counter[str]
    findings: list[Finding]


def shortcode_quote(value: str) -> str:
    """Return a Hugo-compatible quoted string with deterministic escaping."""

    return json.dumps(value, ensure_ascii=False)


def shortcode(name: str, params: Iterable[tuple[str, str]], *, close: bool = True) -> str:
    rendered = " ".join(f"{key}={shortcode_quote(value)}" for key, value in params if value != "")
    prefix = "{{< " + name + ((" " + rendered) if rendered else "")
    return prefix + (" />}}" if close else " >}}")


def keep_final_newline(original: str, lines: list[str]) -> str:
    result = "\n".join(lines)
    if original.endswith("\n"):
        result += "\n"
    return result


def next_nonblank(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def previous_nonblank(lines: list[str], start: int) -> int | None:
    for index in range(start, -1, -1):
        if lines[index].strip():
            return index
    return None


def plain_caption(caption: str) -> str | None:
    """Lower the safe inline emphasis observed in legacy captions to text."""

    value = caption.strip()
    value = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", value)
    value = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", value)
    value = re.sub(r"`([^`\n]+)`", r"\1", value)
    value = re.sub(r"(?<!\\)\$([^$\n]+)\$", r"\1", value)
    value = re.sub(r"(?<!!)\[([^\]\n]+)\]\([^)\n]+\)", r"\1", value)
    return value if PLAIN_CAPTION_FORBIDDEN_RE.search(value) is None else None


def label_kind(label: str) -> str:
    return "fig" if label in {"图", "Figure"} else "tbl"


def language_scope(path: Path) -> str:
    parts = path.parts
    return parts[1] if len(parts) > 1 and parts[0] == "content" else "default"


def scoped_anchor(path: Path, anchor: str) -> str:
    return f"{language_scope(path)}:{anchor}"


def parse_numbered_label(value: str) -> tuple[str, str, str] | None:
    match = NUMBERED_LABEL_RE.fullmatch(value.strip())
    if not match:
        return None
    return label_kind(match.group("label")), match.group("num"), match.group("caption").strip()


def page_for_path(profile: str, relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    if profile == "tpme" and len(parts) >= 3 and parts[:2] == ["content", "zh"]:
        parts = parts[2:]
    elif profile == "tpme" and len(parts) >= 3 and parts[:2] == ["content", "en"]:
        parts = parts[2:]
    elif profile == "ddia-v2" and len(parts) >= 3 and parts[:2] == ["content", "zh"]:
        parts = parts[2:]
    elif profile == "ddia-v1" and len(parts) >= 3 and parts[:2] == ["content", "v1"]:
        parts = parts[2:]
    elif profile == "pg-internal" and parts and parts[0] == "content":
        parts = parts[1:]
    if parts and parts[-1] == "_index":
        parts = parts[:-1]
    return "/" + "/".join(parts) if parts else "/"


def parse_shortcode_params(body: str) -> dict[str, str] | None:
    params: dict[str, str] = {}
    spans: list[tuple[int, int]] = []
    for match in SHORTCODE_PARAM_RE.finditer(body):
        name = match.group("name")
        if name in params:
            return None
        raw = match.group("value")
        if raw.startswith('"'):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                return None
        else:
            value = raw[1:-1].replace("\\'", "'").replace("\\\\", "\\")
        params[name] = value
        spans.append(match.span())
    residue = list(body)
    for start, end in spans:
        residue[start:end] = " " * (end - start)
    if "".join(residue).strip():
        return None
    return params


def is_fence(line: str) -> bool:
    return bool(re.match(r"^\s*(```|~~~)", line))


def protected_replace(line: str, transform: Callable[[str], str]) -> str:
    """Apply a replacement outside inline code, links, images, and shortcodes."""

    output: list[str] = []
    cursor = 0
    for match in PROTECTED_INLINE_RE.finditer(line):
        output.append(transform(line[cursor : match.start()]))
        output.append(match.group(0))
        cursor = match.end()
    output.append(transform(line[cursor:]))
    return "".join(output)


def relative_sources(root: Path, paths: Iterable[str]) -> dict[Path, str]:
    sources: dict[Path, str] = {}
    for value in paths:
        target = (root / value).resolve()
        if root.resolve() not in (target, *target.parents):
            raise ValueError(f"path escapes root: {value}")
        candidates = [target] if target.is_file() else sorted(target.rglob("*.md"))
        for path in candidates:
            if path.is_file():
                sources[path.relative_to(root)] = path.read_text(encoding="utf-8")
    return sources


def tpme_inventory(sources: dict[Path, str]) -> tuple[dict[str, Target], list[Finding]]:
    targets: dict[str, Target] = {}
    findings: list[Finding] = []
    for path, source in sources.items():
        lines = source.splitlines()
        for index, line in enumerate(lines):
            match = TPME_CAPTION_RE.match(line)
            if not match:
                continue
            kind = label_kind(match.group("label"))
            caption = plain_caption(match.group("caption"))
            anchor = match.group("anchor")
            if caption is None:
                findings.append(Finding(str(path), index + 1, "caption contains Markdown and needs manual plain-text review", line))
                continue
            convertible = False
            src = ""
            if kind == "fig":
                prior = previous_nonblank(lines, index - 1)
                if prior is not None:
                    image = IMAGE_RE.match(lines[prior])
                    if image and index - prior <= 2:
                        convertible = True
                        src = image.group("src")
            else:
                following = next_nonblank(lines, index + 1)
                convertible = following is not None and lines[following].lstrip().startswith("|")
            if not convertible:
                findings.append(Finding(str(path), index + 1, f"{kind} caption has no unique adjacent body", line))
                continue
            target = Target(kind, match.group("num"), anchor, str(path), page_for_path("tpme", path), src)
            key = scoped_anchor(path, anchor)
            if key in targets:
                findings.append(Finding(str(path), index + 1, f"duplicate target anchor {anchor}", line))
                targets.pop(key, None)
            else:
                targets[key] = target
    return targets, findings


def tpme_reference(line: str, path: Path, targets: dict[str, Target], counts: Counter[str]) -> str:
    if not str(path).startswith("content/zh/"):
        return line

    def replace(match: re.Match[str]) -> str:
        href = match.group("href")
        parsed = re.fullmatch(r"/en(?P<page>/[^#?]+)#(?P<anchor>[A-Za-z][A-Za-z0-9_.:-]*)", href)
        if not parsed:
            return match.group(0)
        page = parsed.group("page").rstrip("/") or "/"
        anchor = parsed.group("anchor")
        label = match.group("label")
        target = targets.get(f"zh:{anchor}")
        params: list[tuple[str, str]] = []
        if target is not None:
            numbered = parse_numbered_label(label)
            if numbered and numbered[:2] == (target.kind, target.num):
                params.append((target.kind, target.num))
            else:
                target = None
        params.extend((("page", page), ("anchor", anchor)))
        counts["references_numbered" if target else "references_generic"] += 1
        return shortcode("xref", params, close=False) + label + "{{< /xref >}}"

    return MARKDOWN_LINK_RE.sub(replace, line)


def migrate_tpme(sources: dict[Path, str]) -> MigrationResult:
    targets, findings = tpme_inventory(sources)
    counts: Counter[str] = Counter()
    output: dict[Path, str] = {}
    for path, source in sources.items():
        lines = source.splitlines()
        rewritten: list[str] = []
        index = 0
        in_code = False
        while index < len(lines):
            line = lines[index]
            if is_fence(line):
                in_code = not in_code
                rewritten.append(line)
                index += 1
                continue
            if not in_code:
                image = IMAGE_RE.match(line)
                following = next_nonblank(lines, index + 1) if image else None
                caption = TPME_CAPTION_RE.match(lines[following]) if following is not None else None
                if image and caption and following - index <= 2 and label_kind(caption.group("label")) == "fig":
                    target = targets.get(scoped_anchor(path, caption.group("anchor")))
                    if target is not None:
                        caption_text = plain_caption(caption.group("caption"))
                        assert caption_text is not None
                        params = [
                            ("num", target.num),
                            ("id", target.anchor),
                            ("src", image.group("src")),
                            ("caption", caption_text),
                        ]
                        if image.group("alt").strip():
                            params.append(("alt", image.group("alt").strip()))
                        rewritten.append(shortcode("fig", params))
                        counts["figures"] += 1
                        index = following + 1
                        continue
                cap = TPME_CAPTION_RE.match(line)
                following = next_nonblank(lines, index + 1) if cap else None
                if cap and label_kind(cap.group("label")) == "tbl" and following is not None and lines[following].lstrip().startswith("|"):
                    target = targets.get(scoped_anchor(path, cap.group("anchor")))
                    if target is not None:
                        caption_text = plain_caption(cap.group("caption"))
                        assert caption_text is not None
                        end = following
                        while end < len(lines) and lines[end].strip() and lines[end].lstrip().startswith("|"):
                            end += 1
                        rewritten.append(shortcode("tbl", (("num", target.num), ("id", target.anchor), ("caption", caption_text)), close=False))
                        rewritten.extend(lines[following:end])
                        rewritten.append("{{< /tbl >}}")
                        counts["tables"] += 1
                        index = end
                        continue
                line = tpme_reference(line, path, targets, counts)
            rewritten.append(line)
            index += 1
        output[path] = keep_final_newline(source, rewritten)
    return MigrationResult(output, counts, findings)


def ddia_v2_candidate(path: Path, index: int, line: str) -> tuple[Target, dict[str, str]] | Finding | None:
    match = DDIA_FIGURE_RE.match(line)
    if not match:
        return None
    params = parse_shortcode_params(match.group("body"))
    if params is None:
        return Finding(str(path), index + 1, "figure parameters are not a supported named-string form", line)
    unknown = set(params) - {"src", "id", "caption", "title", "class", "link", "alt", "width", "height"}
    if unknown:
        return Finding(str(path), index + 1, f"unsupported figure parameters: {', '.join(sorted(unknown))}", line)
    values = [params.get("caption", ""), params.get("title", "")]
    values = [value for value in values if value]
    if len(values) != 1:
        return Finding(str(path), index + 1, "figure needs exactly one numbered caption or title", line)
    parsed = parse_numbered_label(values[0])
    if parsed is None:
        return Finding(str(path), index + 1, "caption/title has no recognized figure or table number", line)
    kind, num, caption = parsed
    caption = plain_caption(caption)
    if caption is None:
        return Finding(str(path), index + 1, "caption contains Markdown and needs manual plain-text review", line)
    anchor = params.get("id", f"{kind}-{num}")
    if not re.fullmatch(ID, anchor):
        return Finding(str(path), index + 1, "target id is outside the Book ID grammar", line)
    if kind == "fig" and not params.get("src"):
        return Finding(str(path), index + 1, "numbered figure has no src", line)
    if kind == "tbl" and params.get("src"):
        return Finding(str(path), index + 1, "numbered table unexpectedly has src", line)
    target = Target(kind, num, anchor, str(path), page_for_path("ddia-v2", path), params.get("src", ""))
    return target, params


def ddia_v2_inventory(sources: dict[Path, str]) -> tuple[dict[str, Target], dict[tuple[Path, int], dict[str, str]], list[Finding]]:
    targets: dict[str, Target] = {}
    params_by_line: dict[tuple[Path, int], dict[str, str]] = {}
    findings: list[Finding] = []
    for path, source in sources.items():
        for index, line in enumerate(source.splitlines()):
            candidate = ddia_v2_candidate(path, index, line)
            if candidate is None:
                continue
            if isinstance(candidate, Finding):
                findings.append(candidate)
                continue
            target, params = candidate
            if target.anchor in targets:
                findings.append(Finding(str(path), index + 1, f"duplicate target anchor {target.anchor}", line))
                targets.pop(target.anchor, None)
                continue
            targets[target.anchor] = target
            params_by_line[(path, index)] = params
    return targets, params_by_line, findings


def ddia_v2_examples(sources: dict[Path, str]) -> tuple[dict[tuple[Path, int], tuple[str, str]], list[Finding]]:
    examples: dict[tuple[Path, int], tuple[str, str]] = {}
    findings: list[Finding] = []
    for path, source in sources.items():
        for index, line in enumerate(source.splitlines()):
            match = DDIA_FIGURE_RE.match(line)
            if not match:
                continue
            params = parse_shortcode_params(match.group("body"))
            if params is None or params.get("src") or not params.get("id") or not params.get("title"):
                continue
            if set(params) - {"id", "title", "class"}:
                continue
            if not DDIA_EXAMPLE_RE.match(params["title"]):
                continue
            if not re.fullmatch(ID, params["id"]):
                findings.append(Finding(str(path), index + 1, "example id is outside the Book ID grammar", line))
                continue
            css_class = params.get("class", "")
            if css_class and css_class not in {"w-full my-4", "my-4 w-full"}:
                findings.append(Finding(str(path), index + 1, "example carries a non-legacy class that needs review", line))
                continue
            examples[(path, index)] = (params["id"], params["title"])
    return examples, findings


def ddia_v2_generic_targets(
    sources: dict[Path, str],
    examples: dict[tuple[Path, int], tuple[str, str]],
) -> dict[str, str]:
    """Return known non-numbered legacy targets as anchor -> public page."""

    targets = {anchor: page_for_path("ddia-v2", path) for (path, _index), (anchor, _title) in examples.items()}
    explicit = re.compile(rf'<a\s+id=["\'](?P<anchor>{ID})["\']\s*></a>')
    for path, source in sources.items():
        page = page_for_path("ddia-v2", path)
        for match in explicit.finditer(source):
            anchor = match.group("anchor")
            if anchor.startswith("fig_"):
                targets[anchor] = page
    return targets


def ddia_v2_reference(
    line: str,
    targets: dict[str, Target],
    generic_targets: dict[str, str],
    counts: Counter[str],
) -> str:
    def replace(match: re.Match[str]) -> str:
        parsed = re.fullmatch(r"(?P<page>/[^#?]+)#(?P<anchor>[A-Za-z][A-Za-z0-9_.:-]*)", match.group("href"))
        if not parsed:
            return match.group(0)
        page = parsed.group("page").rstrip("/") or "/"
        anchor = parsed.group("anchor")
        target = targets.get(anchor)
        if target is not None and target.page == page:
            numbered = parse_numbered_label(match.group("label"))
            if numbered is not None and numbered[:2] == (target.kind, target.num):
                counts["references_numbered"] += 1
                params = ((target.kind, target.num), ("page", page), ("anchor", target.anchor))
                return shortcode("xref", params, close=False) + match.group("label") + "{{< /xref >}}"
        if generic_targets.get(anchor) == page:
            counts["references_generic"] += 1
            params = (("page", page), ("anchor", anchor))
            return shortcode("xref", params, close=False) + match.group("label") + "{{< /xref >}}"
        return match.group(0)

    return MARKDOWN_LINK_RE.sub(replace, line)


def migrate_ddia_v2(sources: dict[Path, str]) -> MigrationResult:
    targets, params_by_line, findings = ddia_v2_inventory(sources)
    examples_by_line, example_findings = ddia_v2_examples(sources)
    generic_targets = ddia_v2_generic_targets(sources, examples_by_line)
    findings.extend(example_findings)
    example_lines = set(examples_by_line)
    findings = [
        finding
        for finding in findings
        if not (
            finding.reason == "caption/title has no recognized figure or table number"
            and (Path(finding.path), finding.line - 1) in example_lines
        )
    ]
    counts: Counter[str] = Counter()
    output: dict[Path, str] = {}
    for path, source in sources.items():
        lines = source.splitlines()
        rewritten: list[str] = []
        in_code = False
        index = 0
        while index < len(lines):
            line = lines[index]
            if is_fence(line):
                in_code = not in_code
                rewritten.append(line)
                index += 1
                continue
            if not in_code and (path, index) in examples_by_line:
                anchor, title = examples_by_line[(path, index)]
                title = ddia_v2_reference(title, targets, generic_targets, counts)
                indent = line[: len(line) - len(line.lstrip())]
                rewritten.append(f"{indent}#### {title} {{#{anchor}}}")
                counts["examples"] += 1
                index += 1
                continue
            if not in_code and (path, index) in params_by_line:
                params = params_by_line[(path, index)]
                value = params.get("caption") or params.get("title") or ""
                parsed = parse_numbered_label(value)
                assert parsed is not None
                kind, num, caption = parsed
                caption_links = sum(1 for _ in MARKDOWN_LINK_RE.finditer(caption))
                if caption_links:
                    counts["caption_links_flattened"] += caption_links
                caption = plain_caption(caption)
                assert caption is not None
                anchor = params.get("id", f"{kind}-{num}")
                rendered: list[tuple[str, str]] = [("num", num), ("id", anchor)]
                if kind == "fig":
                    rendered.append(("src", params["src"]))
                rendered.append(("caption", caption))
                for name in ("alt", "link", "width", "height"):
                    if params.get(name):
                        rendered.append((name, params[name]))
                css_class = params.get("class", "")
                if css_class and css_class not in {"w-full my-4", "my-4 w-full"}:
                    rendered.append(("class", css_class))
                if kind == "fig":
                    rewritten.append(shortcode("fig", rendered))
                    counts["figures"] += 1
                    index += 1
                    continue
                table_start = next_nonblank(lines, index + 1)
                if table_start is None or not lines[table_start].lstrip().startswith("|"):
                    findings.append(Finding(str(path), index + 1, "numbered table has no adjacent Markdown table", line))
                    rewritten.append(line)
                    index += 1
                    continue
                table_end = table_start
                while table_end < len(lines) and lines[table_end].strip() and lines[table_end].lstrip().startswith("|"):
                    table_end += 1
                rewritten.append(shortcode("tbl", rendered, close=False))
                rewritten.extend(lines[index + 1 : table_end])
                rewritten.append("{{< /tbl >}}")
                counts["tables"] += 1
                index = table_end
                continue
            if not in_code:
                line = ddia_v2_reference(line, targets, generic_targets, counts)
            rewritten.append(line)
            index += 1
        output[path] = keep_final_newline(source, rewritten)
    return MigrationResult(output, counts, findings)


def formatted_caption(line: str, *, labels: set[str]) -> tuple[str, str, str] | None:
    value = line.strip()
    if value.startswith("**") and value.endswith("**") and len(value) > 4:
        value = value[2:-2].strip()
    elif value.startswith("*") and value.endswith("*") and len(value) > 2:
        value = value[1:-1].strip()
    else:
        return None
    parsed = parse_numbered_label(value)
    if parsed is None:
        return None
    kind, num, caption = parsed
    expected = {"fig" if label in {"图", "Figure"} else "tbl" for label in labels}
    return parsed if kind in expected else None


def paired_image_targets(
    profile: str,
    sources: dict[Path, str],
    caption_parser: Callable[[str], tuple[str, str, str] | None],
    anchor_for: Callable[[str, str], str],
) -> tuple[dict[tuple[Path, int], Target], dict[str, list[Target]], list[Finding]]:
    by_line: dict[tuple[Path, int], Target] = {}
    by_src: dict[str, list[Target]] = defaultdict(list)
    findings: list[Finding] = []
    for path, source in sources.items():
        lines = source.splitlines()
        paired_images: set[int] = set()
        for index, line in enumerate(lines):
            parsed = caption_parser(line)
            if parsed is None or parsed[0] != "fig":
                continue
            candidates: list[int] = []
            before = previous_nonblank(lines, index - 1)
            after = next_nonblank(lines, index + 1)
            for candidate in (before, after):
                if candidate is not None and abs(candidate - index) <= 2 and IMAGE_RE.match(lines[candidate]):
                    candidates.append(candidate)
            candidates = sorted(set(candidates))
            if len(candidates) != 1:
                findings.append(Finding(str(path), index + 1, "caption has no unique adjacent image", line))
                continue
            image_index = candidates[0]
            if image_index in paired_images:
                findings.append(Finding(str(path), index + 1, "image is paired with more than one caption", line))
                continue
            image = IMAGE_RE.match(lines[image_index])
            assert image is not None
            kind, num, caption = parsed
            caption = plain_caption(caption)
            if caption is None:
                findings.append(Finding(str(path), index + 1, "caption contains Markdown and needs manual plain-text review", line))
                continue
            anchor = anchor_for(image.group("src"), num)
            target = Target(kind, num, anchor, str(path), page_for_path(profile, path), image.group("src"))
            by_line[(path, image_index)] = target
            by_line[(path, index)] = target
            by_src[target.src].append(target)
            paired_images.add(image_index)
        for index, line in enumerate(lines):
            if IMAGE_RE.match(line) and index not in paired_images:
                findings.append(Finding(str(path), index + 1, "image has no unique numbered caption", line))
    return by_line, by_src, findings


def ddia_v1_caption(line: str) -> tuple[str, str, str] | None:
    return formatted_caption(line, labels={"图", "Figure"})


def migrate_ddia_v1(sources: dict[Path, str]) -> MigrationResult:
    by_line, by_src, findings = paired_image_targets(
        "ddia-v1",
        sources,
        ddia_v1_caption,
        lambda src, _num: "fig_" + re.sub(r"[^A-Za-z0-9_.:-]", "_", Path(src).stem),
    )
    counts: Counter[str] = Counter()
    output: dict[Path, str] = {}
    for path, source in sources.items():
        lines = source.splitlines()
        rewritten: list[str] = []
        consumed: set[int] = set()
        in_code = False
        for index, line in enumerate(lines):
            if index in consumed:
                continue
            if is_fence(line):
                in_code = not in_code
                rewritten.append(line)
                continue
            if not in_code and (path, index) in by_line:
                target = by_line[(path, index)]
                partner = [key[1] for key, value in by_line.items() if key[0] == path and value == target and key[1] != index]
                if partner:
                    other = partner[0]
                    start, end = sorted((index, other))
                    if index == start:
                        image_line = lines[index] if IMAGE_RE.match(lines[index]) else lines[other]
                        caption_line = lines[other] if image_line == lines[index] else lines[index]
                        image = IMAGE_RE.match(image_line)
                        caption = ddia_v1_caption(caption_line)
                        assert image is not None and caption is not None
                        params = [("num", target.num), ("id", target.anchor), ("src", target.src), ("caption", caption[2])]
                        if image.group("alt").strip():
                            params.append(("alt", image.group("alt").strip()))
                        rewritten.append(shortcode("fig", params))
                        counts["figures"] += 1
                        consumed.update(range(start + 1, end + 1))
                        continue
            if not in_code:
                def replace(match: re.Match[str]) -> str:
                    targets = by_src.get(match.group("href"), [])
                    if len(targets) != 1:
                        return match.group(0)
                    target = targets[0]
                    parsed = parse_numbered_label(match.group("label"))
                    if parsed is None or parsed[:2] != ("fig", target.num):
                        return match.group(0)
                    counts["references_numbered"] += 1
                    params = (("fig", target.num), ("page", target.page), ("anchor", target.anchor))
                    return shortcode("xref", params, close=False) + match.group("label") + "{{< /xref >}}"

                line = MARKDOWN_LINK_RE.sub(replace, line)
            rewritten.append(line)
        output[path] = keep_final_newline(source, rewritten)
    return MigrationResult(output, counts, findings)


def pg_caption(line: str) -> tuple[str, str, str] | None:
    return formatted_caption(line, labels={"图", "Figure", "表", "Table"})


def pg_anchor(src: str, num: str) -> str:
    del src
    return f"fig-{num}"


def pg_table_targets(sources: dict[Path, str]) -> dict[tuple[str, str], list[Target]]:
    targets: dict[tuple[str, str], list[Target]] = defaultdict(list)
    for path, source in sources.items():
        lines = source.splitlines()
        for index, line in enumerate(lines):
            caption = pg_caption(line)
            if caption is None or caption[0] != "tbl":
                continue
            following = next_nonblank(lines, index + 1)
            if following is None or not lines[following].lstrip().startswith("|"):
                continue
            kind, num, _text = caption
            targets[(kind, num)].append(
                Target(kind, num, f"tbl-{num}", str(path), page_for_path("pg-internal", path))
            )
    return targets


def migrate_pg_internal(sources: dict[Path, str]) -> MigrationResult:
    by_line, _by_src, findings = paired_image_targets("pg-internal", sources, pg_caption, pg_anchor)
    targets_by_num: dict[tuple[str, str], list[Target]] = defaultdict(list)
    for target in set(by_line.values()):
        targets_by_num[(target.kind, target.num)].append(target)
    for key, targets in pg_table_targets(sources).items():
        targets_by_num[key].extend(targets)
    counts: Counter[str] = Counter()
    output: dict[Path, str] = {}
    for path, source in sources.items():
        lines = source.splitlines()
        rewritten: list[str] = []
        consumed: set[int] = set()
        in_code = False
        index = 0
        while index < len(lines):
            if index in consumed:
                index += 1
                continue
            line = lines[index]
            if is_fence(line):
                in_code = not in_code
                rewritten.append(line)
                index += 1
                continue
            if not in_code and (path, index) in by_line:
                target = by_line[(path, index)]
                partner = [key[1] for key, value in by_line.items() if key[0] == path and value == target and key[1] != index]
                if partner:
                    other = partner[0]
                    start, end = sorted((index, other))
                    if index == start:
                        image_line = lines[index] if IMAGE_RE.match(lines[index]) else lines[other]
                        caption_line = lines[other] if image_line == lines[index] else lines[index]
                        image = IMAGE_RE.match(image_line)
                        caption = pg_caption(caption_line)
                        assert image is not None and caption is not None
                        params = [("num", target.num), ("src", target.src), ("caption", caption[2])]
                        if image.group("alt").strip():
                            params.append(("alt", image.group("alt").strip()))
                        rewritten.append(shortcode("fig", params))
                        counts["figures"] += 1
                        consumed.update(range(start + 1, end + 1))
                        index += 1
                        continue
            caption = pg_caption(line) if not in_code else None
            following = next_nonblank(lines, index + 1) if caption and caption[0] == "tbl" else None
            if not in_code and caption and caption[0] == "tbl" and following is not None and lines[following].lstrip().startswith("|"):
                kind, num, text = caption
                end = following
                while end < len(lines) and lines[end].strip() and lines[end].lstrip().startswith("|"):
                    end += 1
                rewritten.append(shortcode("tbl", (("num", num), ("caption", text)), close=False))
                rewritten.extend(lines[following:end])
                rewritten.append("{{< /tbl >}}")
                counts["tables"] += 1
                index = end
                continue
            if not in_code and not line.lstrip().startswith(("#", "!", "{{<")) and pg_caption(line) is None:
                mention = re.compile(rf"(?P<label>图|表|Figure|Table)\s*(?P<num>{NUMBER})")

                def transform(segment: str) -> str:
                    def replace(match: re.Match[str]) -> str:
                        kind = label_kind(match.group("label"))
                        candidates = targets_by_num.get((kind, match.group("num")), [])
                        if len(candidates) != 1:
                            return match.group(0)
                        target = candidates[0]
                        params: list[tuple[str, str]] = [(kind, target.num)]
                        if target.page != page_for_path("pg-internal", path):
                            params.append(("page", target.page))
                        params.append(("anchor", target.anchor))
                        counts["references_numbered"] += 1
                        return shortcode("xref", params, close=False) + match.group(0) + "{{< /xref >}}"

                    return mention.sub(replace, segment)

                line = protected_replace(line, transform)
            rewritten.append(line)
            index += 1
        output[path] = keep_final_newline(source, rewritten)
    return MigrationResult(output, counts, findings)


MIGRATORS: dict[str, Callable[[dict[Path, str]], MigrationResult]] = {
    "tpme": migrate_tpme,
    "ddia-v2": migrate_ddia_v2,
    "ddia-v1": migrate_ddia_v1,
    "pg-internal": migrate_pg_internal,
}


def git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def diff_for(path: Path, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def run(profile: str, root: Path, paths: list[str], *, write: bool, show_diff: bool, report_path: Path | None) -> int:
    try:
        sources = relative_sources(root, paths)
    except (OSError, ValueError) as exc:
        print(f"migration input error: {exc}", file=sys.stderr)
        return 2
    if not sources:
        print("migration input error: no Markdown files found", file=sys.stderr)
        return 2
    result = MIGRATORS[profile](sources)
    changed = {path: source for path, source in result.sources.items() if source != sources[path]}
    diffs = {path: diff_for(path, sources[path], source) for path, source in changed.items()}
    second = MIGRATORS[profile](result.sources)
    idempotent = second.sources == result.sources
    digest = hashlib.sha256("".join(diffs[path] for path in sorted(diffs)).encode()).hexdigest()
    report = {
        "schema": 1,
        "profile": profile,
        "source_revision": git_revision(root),
        "paths": paths,
        "files_scanned": len(sources),
        "files_changed": len(changed),
        "counts": dict(sorted(result.counts.items())),
        "skipped": [asdict(finding) for finding in result.findings],
        "idempotent": idempotent,
        "diff_sha256": digest,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if show_diff:
        for path in sorted(diffs):
            sys.stdout.write(diffs[path])
    if write:
        for path, source in changed.items():
            (root / path).write_text(source, encoding="utf-8")
    action = "wrote" if write else "would change"
    print(
        f"{profile}: scanned {len(sources)} files, {action} {len(changed)}, "
        f"counts={dict(sorted(result.counts.items()))}, skipped={len(result.findings)}, "
        f"idempotent={idempotent}",
        file=sys.stderr,
    )
    return 0 if idempotent else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=sorted(MIGRATORS))
    parser.add_argument("--root", type=Path, required=True, help="consumer repository root")
    parser.add_argument("--path", action="append", dest="paths", help="file or directory relative to root; repeatable")
    parser.add_argument("--write", action="store_true", help="apply the reviewed migration (default is dry-run)")
    parser.add_argument("--no-diff", action="store_true", help="suppress unified diff while retaining summary/report")
    parser.add_argument("--report", type=Path, help="write the machine-readable JSON report")
    args = parser.parse_args(argv)
    paths = args.paths or list(PROFILE_DEFAULTS[args.profile])
    return run(args.profile, args.root.resolve(), paths, write=args.write, show_diff=not args.no_diff, report_path=args.report)


if __name__ == "__main__":
    raise SystemExit(main())
