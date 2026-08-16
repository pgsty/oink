#!/usr/bin/env python3
"""Measure the OINK 0.5 T00 baseline: corpus noise, asset weight, bundles, build time.

This is a *measurement* tool, not a gate: it never fails on numbers. It exists so
that the 0.5 / 0.6 gates (`check-asset-budget.py`, the 0.6 noise re-measurement)
have a reproducible T00 reference. Re-run it any time; commit the JSON snapshot it
produces next to the milestone progress record.

Sub-commands
------------
  noise   Corpus noise (four metrics) over one or more site checkouts.
  assets  Isolated build of one or more sites: build time (cold/warm), CSS/JS
          weight per page type (raw + gzip), font-face and third-party presence,
          distinct JS bundle count, optional RTL variant (theme fixture only).
  all     Both, sharing the same snapshots.

Corpus noise — the four metrics (0.5 definition; 0.6 task 00 finalises the method)
----------------------------------------------------------------------------------
Everything is counted over Markdown files under ``content/`` after stripping front
matter. Shortcode *tags* are ``{{< name … >}}``, ``{{% name … %}}``, ``{{< /name >}}``,
``{{% /name %}}``; escaped forms (``{{</* … */>}}``) never count. Hugo expands
shortcodes inside code fences too, so tags inside fences are counted as parsed
tokens (reported separately as ``in_fence`` for the 0.6 method review).

Only *theme-owned* shortcode names (``layouts/_shortcodes/**`` of the theme,
including site overrides of those names) feed the four metrics. Site-local
shortcodes (names that exist only under the site's own ``layouts``) and Hugo
built-ins (``ref`` ``relref`` ``figure`` ``highlight`` ``youtube`` …) are reported
in separate buckets and excluded, as PRD 9 §4.3 requires. Generated corpus is
excluded through ``--exclude`` globs (defaults below) and reported.

1. ``parsed_tokens``   — number of theme shortcode tags (open + close + inline).
                         Normalised as ``parsed_tokens_per_kloc`` = tokens per
                         1,000 body lines.
2. ``wrapper_lines``   — lines whose non-blank content is nothing but *container*
                         tags (an opening tag that is closed later in the file, or a
                         closing tag): pure wrapper markup an author had to write.
                         All-tag lines made of leaf tags (``{{< filetree/file … >}}``)
                         are reported separately as ``leaf_lines``.
3. ``closing_tokens``  — closing tags ``{{< /x >}}`` / ``{{% /x %}}``.
4. ``semantic_fallback`` — component instances (open + inline tags) that render as
                         literal ``{{…}}`` text on GitHub / in plain Markdown, i.e.
                         everything that needs OINK to mean anything. Reported next
                         to ``native_instances`` (GFM callout heads, diagram / data
                         fences, theme block-attribute markers ``{.full-width}`` /
                         ``{.oink-*}``; site-local attribute lines are counted apart
                         as ``attr_lines_other``) and the ratio
                         ``semantic_fallback_ratio`` = fallback / (fallback + native).

Snapshots
---------
Sites are measured from detached ``git clone --shared`` snapshots of HEAD
(revision-locked; a dirty working tree never leaks into the baseline; history is
kept so ``enableGitInfo`` sites build). A directory that is not a git
repository is copied from the working tree and flagged ``snapshot: worktree``.

Builds
------
Each site is built in its snapshot with a scratch ``go.work`` that replaces
``github.com/pgsty/oink`` with the local theme checkout (``--theme``), using
``--minify --printPathWarnings --panicOnWarning`` (the strict build). No network
is needed. The theme fixture (``exampleSite``) is built with ``--themesDir``.

Examples
--------
  python3 scripts/measure-baseline.py all --sites ~/pgsty/pigsty.io ~/pgsty/oink.pgsty.com \
      --json plan/progress/0.5/00-baseline.json --md plan/progress/0.5/00-baseline-tables.md
  python3 scripts/measure-baseline.py noise --sites ~/pgsty/*/ --exclude 'content/ext/**'
  python3 scripts/measure-baseline.py assets --example-site --rtl
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import gzip
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from html import unescape
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"

# ---------------------------------------------------------------------------
# Corpus noise
# ---------------------------------------------------------------------------

# Hugo built-in shortcodes (0.164). Theme overrides of `comment` / `details` /
# `param` make those theme-owned; the rest are Hugo's own vocabulary.
HUGO_BUILTIN_SHORTCODES = {
    "comment", "details", "figure", "gist", "highlight", "instagram", "param",
    "qr", "ref", "relref", "vimeo", "x", "youtube", "twitter", "tweet",
}

# Fence languages whose *content is the component* (diagram / data): native.
NATIVE_FENCE_LANGS = {
    "mermaid", "plantuml", "markmap", "math", "chem", "katex", "tex", "latex",
    "echarts", "infographic", "checksums",
}

# Generated corpus that must not count against the theme (PRD 9 §4.3). Keyed by
# site directory name; globs are relative to the site root.
DEFAULT_EXCLUDES: dict[str, list[str]] = {
    "pigsty.io": ["content/ext/**"],
    "pigsty.cc": ["content/ext/**"],
}

# Theme-owned block-attribute markers (`{.full-width}` today; `{.oink-*}` from 0.6).
THEME_MARKER_RE = re.compile(r"\.(?:full-width|oink-[a-z0-9-]+)\b")

FRONT_MATTER_RE = re.compile(r"\A(---|\+\+\+)\s*\n.*?\n\1\s*\n", re.S)
# One shortcode tag. Group 1: notation, 2: closing slash, 3: name, 4: rest.
SHORTCODE_RE = re.compile(
    r"\{\{([<%])\s*(/?)\s*([A-Za-z0-9_][A-Za-z0-9_./-]*)(.*?)([%>])\}\}",
    re.S,
)
ESCAPED_RE = re.compile(r"\{\{[<%]/\*.*?\*/[%>]\}\}", re.S)
FENCE_RE = re.compile(r"^(?P<indent>[ \t]{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
CALLOUT_RE = re.compile(r"^\s*>\s*\[!([A-Za-z]+)\][+-]?")
ATTR_LINE_RE = re.compile(r"^\{[.#][^}]*\}\s*$")


def strip_front_matter(text: str) -> str:
    match = FRONT_MATTER_RE.match(text)
    return text[match.end():] if match else text


def fence_spans(lines: list[str]) -> tuple[list[bool], list[str]]:
    """Return per-line ``in_fence`` mask and the info strings of opening fences."""
    in_fence = [False] * len(lines)
    infos: list[str] = []
    open_fence: tuple[str, int] | None = None  # (char, length)
    for i, line in enumerate(lines):
        match = FENCE_RE.match(line)
        if open_fence is None:
            if match:
                fence = match.group("fence")
                info = match.group("info").strip()
                # A backtick fence may not contain backticks in its info string.
                if fence[0] == "`" and "`" in info:
                    continue
                open_fence = (fence[0], len(fence))
                infos.append(info)
                in_fence[i] = True
        else:
            in_fence[i] = True
            if match and match.group("fence")[0] == open_fence[0] \
                    and len(match.group("fence")) >= open_fence[1] \
                    and not match.group("info").strip():
                open_fence = None
    return in_fence, infos


def shortcode_names(layout_roots: Iterable[Path]) -> set[str]:
    names: set[str] = set()
    for root in layout_roots:
        for sub in ("_shortcodes", "shortcodes"):
            base = root / sub
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(base)
                    names.add(str(rel.with_suffix("")).replace(os.sep, "/"))
    return names


def new_counter() -> dict:
    return {
        "files": 0,
        "files_with_shortcodes": 0,
        "body_lines": 0,
        "parsed_tokens": 0,
        "parsed_tokens_in_fence": 0,
        "wrapper_lines": 0,
        "leaf_lines": 0,
        "closing_tokens": 0,
        "semantic_fallback": 0,
        "native_instances": 0,
        "native": {"callouts": 0, "data_fences": 0, "attr_lines": 0},
        "attr_lines_other": 0,
        "notation": {"<": 0, "%": 0},
        "by_shortcode": {},
        "site_local": {"tokens": 0, "by_shortcode": {}},
        "hugo_builtin": {"tokens": 0, "by_shortcode": {}},
        "unknown": {"tokens": 0, "by_shortcode": {}},
    }


def add_counter(total: dict, part: dict) -> None:
    for key in ("files", "files_with_shortcodes", "body_lines", "parsed_tokens",
                "parsed_tokens_in_fence", "wrapper_lines", "leaf_lines", "closing_tokens",
                "semantic_fallback", "native_instances", "attr_lines_other"):
        total[key] += part[key]
    for key in total["native"]:
        total["native"][key] += part["native"][key]
    for key in total["notation"]:
        total["notation"][key] += part["notation"][key]
    for bucket in ("by_shortcode",):
        for name, n in part[bucket].items():
            total[bucket][name] = total[bucket].get(name, 0) + n
    for bucket in ("site_local", "hugo_builtin", "unknown"):
        total[bucket]["tokens"] += part[bucket]["tokens"]
        for name, n in part[bucket]["by_shortcode"].items():
            total[bucket]["by_shortcode"][name] = total[bucket]["by_shortcode"].get(name, 0) + n


def finish_counter(counter: dict) -> dict:
    kloc = counter["body_lines"] / 1000 if counter["body_lines"] else 0
    counter["parsed_tokens_per_kloc"] = round(counter["parsed_tokens"] / kloc, 2) if kloc else 0.0
    counter["wrapper_lines_per_kloc"] = round(counter["wrapper_lines"] / kloc, 2) if kloc else 0.0
    counter["closing_tokens_per_kloc"] = round(counter["closing_tokens"] / kloc, 2) if kloc else 0.0
    denom = counter["semantic_fallback"] + counter["native_instances"]
    counter["semantic_fallback_ratio"] = round(counter["semantic_fallback"] / denom, 4) if denom else 0.0
    counter["by_shortcode"] = dict(sorted(counter["by_shortcode"].items(), key=lambda kv: (-kv[1], kv[0])))
    for bucket in ("site_local", "hugo_builtin", "unknown"):
        counter[bucket]["by_shortcode"] = dict(
            sorted(counter[bucket]["by_shortcode"].items(), key=lambda kv: (-kv[1], kv[0]))
        )
    return counter


def measure_file(text: str, theme_names: set[str], local_names: set[str]) -> dict:
    counter = new_counter()
    counter["files"] = 1
    body = strip_front_matter(text)
    lines = body.split("\n")
    counter["body_lines"] = len(lines)
    in_fence, infos = fence_spans(lines)

    for info in infos:
        lang = info.split("{", 1)[0].strip().split()[0].lower() if info.strip() else ""
        if lang in NATIVE_FENCE_LANGS:
            counter["native"]["data_fences"] += 1
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        if CALLOUT_RE.match(line):
            counter["native"]["callouts"] += 1
        elif ATTR_LINE_RE.match(line):
            if THEME_MARKER_RE.search(line):
                counter["native"]["attr_lines"] += 1
            else:
                counter["attr_lines_other"] += 1
    counter["native_instances"] = sum(counter["native"].values())

    # Map char offsets to line numbers for tag-line bookkeeping.
    line_starts = [0]
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)

    def line_of(offset: int) -> int:
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    escaped_spans = [(m.start(), m.end()) for m in ESCAPED_RE.finditer(body)]
    tag_mask = bytearray(len(body))      # 1 = inside a theme shortcode tag
    container_mask = bytearray(len(body))  # 1 = inside a container tag (paired open, or close)
    saw_theme_tag = False
    theme_tags: list[tuple[int, int, bool, str]] = []  # (start, end, closing, name)
    for match in SHORTCODE_RE.finditer(body):
        start, end = match.span()
        if any(s <= start < e for s, e in escaped_spans):
            continue
        notation, closing, name = match.group(1), match.group(2), match.group(3)
        if name in theme_names:
            bucket = "theme"
        elif name in local_names:
            bucket = "site_local"
        elif name in HUGO_BUILTIN_SHORTCODES:
            bucket = "hugo_builtin"
        else:
            bucket = "unknown"
        if bucket != "theme":
            counter[bucket]["tokens"] += 1
            counter[bucket]["by_shortcode"][name] = counter[bucket]["by_shortcode"].get(name, 0) + 1
            continue
        saw_theme_tag = True
        counter["parsed_tokens"] += 1
        counter["notation"][notation] += 1
        if in_fence[line_of(start)]:
            counter["parsed_tokens_in_fence"] += 1
        if closing:
            counter["closing_tokens"] += 1
        else:
            counter["semantic_fallback"] += 1
            counter["by_shortcode"][name] = counter["by_shortcode"].get(name, 0) + 1
        for k in range(start, end):
            tag_mask[k] = 1
        theme_tags.append((start, end, bool(closing), name))
    if saw_theme_tag:
        counter["files_with_shortcodes"] = 1

    # Pair opening tags with their closing tags (Hugo requires proper nesting) to
    # tell container tags from leaf tags.
    stack: list[tuple[int, int, str]] = []
    for start, end, closing, name in theme_tags:
        if not closing:
            stack.append((start, end, name))
            continue
        for depth in range(len(stack) - 1, -1, -1):
            if stack[depth][2] == name:
                o_start, o_end, _ = stack[depth]
                del stack[depth:]
                for k in range(o_start, o_end):
                    container_mask[k] = 1
                break
        for k in range(start, end):
            container_mask[k] = 1

    # Wrapper lines: lines that contain nothing but container tags; leaf lines:
    # nothing but tags, at least one of them a leaf.
    for i, line in enumerate(lines):
        start = line_starts[i]
        end = start + len(line)
        if not any(tag_mask[start:end]):
            continue
        rest = "".join(ch for k, ch in enumerate(line, start) if not tag_mask[k])
        if rest.strip():
            continue
        if all(container_mask[k] for k in range(start, end) if tag_mask[k]):
            counter["wrapper_lines"] += 1
        else:
            counter["leaf_lines"] += 1
    return counter


def iter_markdown(site: Path, excludes: list[str]) -> Iterable[tuple[Path, bool]]:
    content = site / "content"
    if not content.is_dir():
        return
    for path in sorted(content.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".markdown"}:
            continue
        rel = path.relative_to(site).as_posix()
        excluded = any(fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, pattern.rstrip("/**") + "/*")
                       for pattern in excludes)
        yield path, excluded


def measure_site_noise(site: Path, theme_names: set[str], excludes: list[str]) -> dict:
    local_names = shortcode_names([site / "layouts"]) - theme_names
    included = new_counter()
    excluded = new_counter()
    for path, is_excluded in iter_markdown(site, excludes):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        part = measure_file(text, theme_names, local_names)
        add_counter(excluded if is_excluded else included, part)
    return {
        "excludes": excludes,
        "site_local_shortcodes": sorted(local_names),
        "included": finish_counter(included),
        "excluded_generated": finish_counter(excluded),
    }


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def git(site: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(site), *args], capture_output=True, text=True, check=True).stdout.strip()


def is_git_repo(site: Path) -> bool:
    return subprocess.run(["git", "-C", str(site), "rev-parse", "--git-dir"], capture_output=True).returncode == 0


def snapshot_site(site: Path, dest: Path, *, worktree: bool = False) -> dict:
    """Materialise HEAD (or the working tree for non-git dirs / --worktree) into dest."""
    dest.mkdir(parents=True, exist_ok=True)
    if is_git_repo(site) and not worktree:
        head = git(site, "rev-parse", "HEAD")
        branch = subprocess.run(["git", "-C", str(site), "symbolic-ref", "--short", "-q", "HEAD"],
                                capture_output=True, text=True).stdout.strip() or "DETACHED"
        dirty = bool(git(site, "status", "--porcelain"))
        # A shared local clone: reads the source repository only, keeps history so
        # `enableGitInfo` sites still build, and checks out exactly HEAD.
        shutil.rmtree(dest, ignore_errors=True)
        subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(site), str(dest)],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", "--detach", head],
                       check=True, capture_output=True)
        return {"snapshot": "head", "revision": head, "branch": branch, "dirty_worktree": dirty}
    ignore = shutil.ignore_patterns("public", "resources", "node_modules", "tmp", ".idea", ".hugo_build.lock",
                                    ".hugo_cache", ".cache")
    shutil.copytree(site, dest, dirs_exist_ok=True, ignore=ignore, symlinks=True)
    if is_git_repo(site):
        # Keep .git so enableGitInfo works; record the revision the tree is based on.
        return {"snapshot": "worktree", "revision": git(site, "rev-parse", "HEAD"),
                "branch": subprocess.run(["git", "-C", str(site), "symbolic-ref", "--short", "-q", "HEAD"],
                                         capture_output=True, text=True).stdout.strip() or "DETACHED",
                "dirty_worktree": bool(git(site, "status", "--porcelain"))}
    return {"snapshot": "worktree", "revision": None, "branch": None, "dirty_worktree": None}


# ---------------------------------------------------------------------------
# Builds and asset weight
# ---------------------------------------------------------------------------

TOTAL_RE = re.compile(r"Total in (\d+) ms")
LINK_RE = re.compile(r'<link\b[^>]*>', re.I)
SCRIPT_RE = re.compile(r'<script\b[^>]*\bsrc=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))[^>]*>', re.I)
HREF_RE = re.compile(r'\bhref=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
REL_RE = re.compile(r'\brel=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
INLINE_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
INLINE_SCRIPT_RE = re.compile(r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)
BODY_RE = re.compile(r"<body\b([^>]*)>", re.I)
FONT_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+\.(?:woff2|woff|ttf|otf))")
THIRD_PARTY_MARKERS = {
    "bootstrap": "Bootstrap v5",
    "echarts": "echarts",
    "katex": "katex",
    "markmap": "markmap",
    "asciinema": "asciinema",
    "swagger-ui": "SwaggerUI",
    "redoc": "Redoc",
    "infographic": "infographic",
    "lunr": "lunr.Builder",
    "docsearch": "docsearch",
    "pako": "pako",
}


def first(*groups: str | None) -> str:
    for group in groups:
        if group:
            return group
    return ""


ALIAS_RE = re.compile(r'<meta\s+http-equiv=["\']?refresh', re.I)


def classify_page(html: str, rel: str = "") -> str:
    if rel.startswith("_print/") or "/_print/" in rel:
        return "print"
    if ALIAS_RE.search(html) and "<body" not in html.lower():
        return "alias"
    match = BODY_RE.search(html)
    classes = match.group(1) if match else ""
    if "td-shell-chrome" in classes:
        if "td-book" in classes:
            return "book"
        if "td-swagger" in classes:
            return "swagger"
        if "td-blog" in classes:
            return "blog"
        return "docs"
    if "data-td-landing" in html or 'class="td-landing' in html or "td-landing" in html:
        return "landing"
    return "plain"


class AssetCache:
    def __init__(self, public: Path):
        self.public = public
        self.cache: dict[str, dict] = {}

    def resolve(self, url: str) -> Path | None:
        url = unescape(url).split("?", 1)[0].split("#", 1)[0]
        if url.startswith(("http://", "https://", "//")):
            return None
        parts = url.lstrip("/").split("/")
        # A baseURL sub-path is not mirrored under public/; strip leading segments until found.
        for skip in range(0, min(3, len(parts))):
            path = self.public.joinpath(*parts[skip:])
            if path.is_file():
                return path
        return None

    def info(self, url: str) -> dict | None:
        key = unescape(url).split("?", 1)[0]
        if key in self.cache:
            return self.cache[key]
        path = self.resolve(url)
        if path is None:
            self.cache[key] = None
            return None
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        entry = {
            "path": str(path.relative_to(self.public)),
            "bytes": len(data),
            "gzip": len(gzip.compress(data, compresslevel=6)),
            "fonts": sorted({m.group(1).rsplit("/", 1)[-1] for m in FONT_URL_RE.finditer(text)}),
            "third_party": sorted(k for k, marker in THIRD_PARTY_MARKERS.items() if marker in text),
        }
        self.cache[key] = entry
        return entry


def measure_page(public: Path, page: Path, cache: AssetCache) -> dict:
    html = page.read_text(encoding="utf-8", errors="replace")
    rel = page.relative_to(public).as_posix()
    css_urls: list[str] = []
    for tag in LINK_RE.findall(html):
        link_rel = first(*(REL_RE.search(tag).groups() if REL_RE.search(tag) else ())).lower()
        if "stylesheet" not in link_rel:
            continue
        href_match = HREF_RE.search(tag)
        if href_match:
            css_urls.append(first(*href_match.groups()))
    js_urls = [first(*m.groups()) for m in SCRIPT_RE.finditer(html)]
    remote = [u for u in css_urls + js_urls if u.startswith(("http://", "https://", "//"))]
    css = [cache.info(u) for u in css_urls]
    js = [cache.info(u) for u in js_urls]
    css = [c for c in css if c]
    js = [j for j in js if j]
    fonts = sorted({f for c in css for f in c["fonts"]})
    third = sorted({t for a in css + js for t in a["third_party"]})
    bundle = next((j["path"] for j in js if "/main-" in "/" + j["path"] and j["path"].endswith(".js")), None)
    fa_usage = len(re.findall(r'class=["\']?[^"\'>]*\bfa-(?:solid|regular|brands)\b', html))
    return {
        "type": classify_page(html, rel),
        "html_bytes": len(html.encode("utf-8")),
        "css_bytes": sum(c["bytes"] for c in css),
        "css_gzip": sum(c["gzip"] for c in css),
        "js_bytes": sum(j["bytes"] for j in js),
        "js_gzip": sum(j["gzip"] for j in js),
        "inline_style_bytes": sum(len(s.encode()) for s in INLINE_STYLE_RE.findall(html)),
        "inline_script_bytes": sum(len(s.encode()) for s in INLINE_SCRIPT_RE.findall(html)),
        "css_files": len(css),
        "js_files": len(js),
        "fonts_declared": fonts,
        "fa_icon_uses": fa_usage,
        "third_party": third,
        "remote_requests": remote,
        "bundle": bundle,
    }


def summarise_pages(pages: dict[str, dict]) -> dict:
    by_type: dict[str, list[dict]] = {}
    for info in pages.values():
        by_type.setdefault(info["type"], []).append(info)
    summary = {}
    for page_type, infos in sorted(by_type.items()):
        def stat(key: str) -> dict:
            values = [i[key] for i in infos]
            return {"min": min(values), "median": int(statistics.median(values)), "max": max(values)}
        summary[page_type] = {
            "pages": len(infos),
            "css_bytes": stat("css_bytes"),
            "css_gzip": stat("css_gzip"),
            "js_bytes": stat("js_bytes"),
            "js_gzip": stat("js_gzip"),
            "html_bytes": stat("html_bytes"),
            "pages_with_third_party": sum(1 for i in infos if i["third_party"]),
            "pages_with_remote_requests": sum(1 for i in infos if i["remote_requests"]),
            "pages_with_fa_icon_uses": sum(1 for i in infos if i["fa_icon_uses"]),
            "fonts_declared": sorted({f for i in infos for f in i["fonts_declared"]}),
        }
    return summary


def bundle_table(public: Path, pages: dict[str, dict], cache: AssetCache) -> list[dict]:
    usage: dict[str, int] = {}
    for info in pages.values():
        if info["bundle"]:
            usage[info["bundle"]] = usage.get(info["bundle"], 0) + 1
    table = []
    for rel in sorted((public / "js").glob("main-*.js")) if (public / "js").is_dir() else []:
        entry = cache.info("/" + rel.relative_to(public).as_posix())
        if entry:
            table.append({
                "file": entry["path"],
                "bytes": entry["bytes"],
                "gzip": entry["gzip"],
                "third_party": entry["third_party"],
                "pages": usage.get(entry["path"], 0),
            })
    return table


def run_hugo(hugo: str, source: Path, dest: Path, extra: list[str], env: dict[str, str]) -> dict:
    cmd = [hugo, "--source", str(source), "--destination", str(dest), "--minify",
           "--printPathWarnings", "--panicOnWarning", *extra]
    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    wall = time.perf_counter() - start
    match = TOTAL_RE.search(result.stdout + result.stderr)
    return {
        "ok": result.returncode == 0,
        "wall_seconds": round(wall, 3),
        "hugo_total_ms": int(match.group(1)) if match else None,
        "cmd": " ".join(cmd),
        "stderr_tail": (result.stderr or result.stdout)[-2000:] if result.returncode != 0 else "",
    }


def prepare_workspace(snapshot: Path, theme: Path) -> None:
    """Point the site's module import at the local theme with a scratch go.work."""
    if not (snapshot / "go.mod").is_file():
        return
    (snapshot / "go.work").unlink(missing_ok=True)
    subprocess.run(["go", "work", "init", "."], cwd=snapshot, check=True, capture_output=True)
    subprocess.run(["go", "work", "edit", f"-replace=github.com/pgsty/oink={theme}"], cwd=snapshot,
                   check=True, capture_output=True)


def measure_build(name: str, snapshot: Path, hugo: str, theme: Path, *, example: bool,
                  config_extra: Path | None = None) -> dict:
    env = dict(os.environ)
    extra: list[str] = []
    if example:
        extra += ["--themesDir", str(theme.parent)]
    else:
        prepare_workspace(snapshot, theme)
        env["HUGO_MODULE_WORKSPACE"] = str(snapshot / "go.work")
    if config_extra:
        extra += ["--config", f"{snapshot / 'hugo.yaml' if (snapshot / 'hugo.yaml').exists() else snapshot / 'hugo.yml'},{config_extra}"]
    dest = snapshot / "public"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.rmtree(snapshot / "resources", ignore_errors=True)
    cold = run_hugo(hugo, snapshot, dest, extra, env)
    warm = run_hugo(hugo, snapshot, dest, extra, env) if cold["ok"] else None
    result: dict = {"name": name, "strict_build_ok": cold["ok"], "cold": cold, "warm": warm}
    if not cold["ok"]:
        # Retry non-strict so the numbers still exist; the strict failure is recorded.
        lenient_cmd = [hugo, "--source", str(snapshot), "--destination", str(dest), "--minify", *extra]
        lenient = subprocess.run(lenient_cmd, capture_output=True, text=True, env=env, check=False)
        result["lenient_build_ok"] = lenient.returncode == 0
        if lenient.returncode != 0:
            result["lenient_stderr_tail"] = (lenient.stderr or lenient.stdout)[-2000:]
            return result
    cache = AssetCache(dest)
    pages: dict[str, dict] = {}
    for page in sorted(dest.rglob("*.html")):
        rel = page.relative_to(dest).as_posix()
        pages[rel] = measure_page(dest, page, cache)
    result["pages_measured"] = len(pages)
    result["by_type"] = summarise_pages(pages)
    result["bundles"] = bundle_table(dest, pages, cache)
    result["bundle_count"] = len(result["bundles"])
    css_files = sorted(dest.glob("scss/main*.css"))
    result["main_css"] = [
        {"file": p.name, "bytes": p.stat().st_size, "gzip": len(gzip.compress(p.read_bytes(), 6))}
        for p in css_files
    ]
    fonts_dir = [p for p in dest.rglob("*.woff2")]
    result["font_files"] = {
        "count": len(fonts_dir),
        "bytes": sum(p.stat().st_size for p in fonts_dir),
        "font_awesome_bytes": sum(p.stat().st_size for p in fonts_dir if p.name.startswith("fa-")),
    }
    rtl_css = sorted(dest.rglob("bootstrap.rtl*.css"))
    result["rtl_css"] = [{"file": p.name, "bytes": p.stat().st_size, "gzip": len(gzip.compress(p.read_bytes(), 6))} for p in rtl_css]
    result["public_bytes"] = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    # Representative pages per type (first by path) for the human table.
    result["samples"] = {}
    for page_type in result["by_type"]:
        sample = next((rel for rel, info in pages.items() if info["type"] == page_type), None)
        if sample:
            result["samples"][page_type] = {"page": sample, **{k: v for k, v in pages[sample].items() if k != "type"}}
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def kb(n: int | None) -> str:
    return "—" if n is None else f"{n / 1024:.1f}"


def render_markdown(report: dict) -> str:
    out: list[str] = []
    out.append(f"# OINK T00 baseline — {report['generated_at']}")
    out.append("")
    theme = report["theme"]
    out.append(f"Theme `{theme['path']}` @ `{theme['commit'][:10]}`{' (dirty)' if theme['dirty'] else ''}; "
               f"Hugo `{report['hugo']['version']}`")
    out.append("")
    if any("noise" in s for s in report["sites"].values()):
        out.append("## Corpus noise (theme shortcodes; generated corpus excluded)")
        out.append("")
        out.append("| site | snapshot | files | body lines | parsed tokens | /kloc | wrapper lines | /kloc | leaf lines | closing | /kloc | fallback | native | fallback ratio | site-local tokens (excluded) |")
        out.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for name, site in report["sites"].items():
            noise = site.get("noise")
            if not noise:
                continue
            c = noise["included"]
            snap = site["snapshot"] + (f" `{site['revision'][:8]}`" if site.get("revision") else "")
            out.append(f"| {name} | {snap} | {c['files']} | {c['body_lines']} | {c['parsed_tokens']} | {c['parsed_tokens_per_kloc']} | "
                       f"{c['wrapper_lines']} | {c['wrapper_lines_per_kloc']} | {c['leaf_lines']} | {c['closing_tokens']} | {c['closing_tokens_per_kloc']} | "
                       f"{c['semantic_fallback']} | {c['native_instances']} | {c['semantic_fallback_ratio']} | {c['site_local']['tokens']} |")
        total = report.get("totals", {}).get("noise")
        if total:
            c = total
            out.append(f"| **total** | | {c['files']} | {c['body_lines']} | {c['parsed_tokens']} | {c['parsed_tokens_per_kloc']} | "
                       f"{c['wrapper_lines']} | {c['wrapper_lines_per_kloc']} | {c['leaf_lines']} | {c['closing_tokens']} | {c['closing_tokens_per_kloc']} | "
                       f"{c['semantic_fallback']} | {c['native_instances']} | {c['semantic_fallback_ratio']} | {c['site_local']['tokens']} |")
        out.append("")
        if total:
            out.append("Top theme shortcodes (instances = open + inline tags, generated corpus excluded):")
            out.append("")
            out.append("| shortcode | instances |")
            out.append("| --- | ---: |")
            for name, n in list(total["by_shortcode"].items())[:40]:
                out.append(f"| `{name}` | {n} |")
            out.append("")
            excluded = report.get("totals", {}).get("noise_excluded_generated")
            if excluded and excluded["files"]:
                out.append(f"Excluded generated corpus: {excluded['files']} files, {excluded['parsed_tokens']} parsed tokens, "
                           f"{excluded['semantic_fallback']} instances (not counted above).")
                out.append("")
    if any("build" in s for s in report["sites"].values()):
        out.append("## Builds (strict: --minify --printPathWarnings --panicOnWarning; isolated snapshot; local theme via go.work)")
        out.append("")
        out.append("| site | strict | cold wall s | cold hugo ms | warm wall s | warm hugo ms | pages | bundles | main.css KB (gz) | fonts (FA) KB | public MB |")
        out.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for name, site in report["sites"].items():
            b = site.get("build")
            if not b:
                continue
            css = b.get("main_css", [{}])
            css0 = css[0] if css else {}
            fonts = b.get("font_files", {})
            out.append(f"| {name} | {'ok' if b['strict_build_ok'] else 'FAIL'} | {b['cold']['wall_seconds']} | {b['cold']['hugo_total_ms']} | "
                       f"{b['warm']['wall_seconds'] if b.get('warm') else '—'} | {b['warm']['hugo_total_ms'] if b.get('warm') else '—'} | "
                       f"{b.get('pages_measured', '—')} | {b.get('bundle_count', '—')} | {kb(css0.get('bytes'))} ({kb(css0.get('gzip'))}) | "
                       f"{kb(fonts.get('bytes'))} ({kb(fonts.get('font_awesome_bytes'))}) | {b.get('public_bytes', 0) / 1048576:.1f} |")
        out.append("")
        out.append("### Per page type (median; KB raw / gz)")
        out.append("")
        out.append("| site | type | pages | CSS | JS | HTML | third-party pages | remote pages | FA icon pages |")
        out.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for name, site in report["sites"].items():
            b = site.get("build")
            if not b or "by_type" not in b:
                continue
            for page_type, s in b["by_type"].items():
                out.append(f"| {name} | {page_type} | {s['pages']} | {kb(s['css_bytes']['median'])} / {kb(s['css_gzip']['median'])} | "
                           f"{kb(s['js_bytes']['median'])} / {kb(s['js_gzip']['median'])} | {kb(s['html_bytes']['median'])} | "
                           f"{s['pages_with_third_party']} | {s['pages_with_remote_requests']} | {s['pages_with_fa_icon_uses']} |")
        out.append("")
        out.append("### JS bundles (main-*.js; combinations of runtime flags)")
        out.append("")
        out.append("| site | bundle | KB (gz) | pages | third-party |")
        out.append("| --- | --- | ---: | ---: | --- |")
        for name, site in report["sites"].items():
            b = site.get("build")
            if not b or "bundles" not in b:
                continue
            for entry in b["bundles"]:
                out.append(f"| {name} | `{entry['file'].split('/')[-1][:48]}…` | {kb(entry['bytes'])} ({kb(entry['gzip'])}) | {entry['pages']} | {', '.join(entry['third_party']) or '—'} |")
        out.append("")
        for name, site in report["sites"].items():
            b = site.get("build")
            if b and b.get("rtl_css"):
                for entry in b["rtl_css"]:
                    out.append(f"RTL stylesheet ({name}): `{entry['file']}` {kb(entry['bytes'])} KB ({kb(entry['gzip'])} gz)")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def theme_facts(theme: Path) -> dict:
    commit = subprocess.run(["git", "-C", str(theme), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(theme), "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    return {"path": str(theme), "commit": commit, "dirty": dirty}


def hugo_facts(hugo: str) -> dict:
    version = subprocess.run([hugo, "version"], capture_output=True, text=True).stdout.strip()
    return {"bin": hugo, "version": version}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["noise", "assets", "all"])
    parser.add_argument("--sites", nargs="*", default=[], help="site checkouts to measure (default: none)")
    parser.add_argument("--example-site", action="store_true", help="also measure the theme's exampleSite fixture")
    parser.add_argument("--theme", default=str(ROOT), help="theme checkout used for builds (default: this repo)")
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--exclude", action="append", default=None,
                        help="glob (relative to a site root) of generated corpus to exclude; repeatable. "
                             "Default: built-in per-site list.")
    parser.add_argument("--rtl", action="store_true", help="also build the exampleSite with languages.en.direction=rtl")
    parser.add_argument("--worktree", action="append", default=[], metavar="SITE",
                        help="measure this site's working tree instead of HEAD (flagged in the report); repeatable")
    parser.add_argument("--keep", help="directory to keep snapshots and builds in (default: temp dir, removed)")
    parser.add_argument("--json", help="write the JSON report here")
    parser.add_argument("--md", help="write the Markdown tables here")
    args = parser.parse_args()

    theme = Path(args.theme).resolve()
    theme_names = shortcode_names([theme / "layouts"])
    if not theme_names:
        print(f"no shortcodes found under {theme}/layouts — wrong --theme?", file=sys.stderr)
        return 2
    do_noise = args.command in ("noise", "all")
    do_assets = args.command in ("assets", "all")

    work_root = Path(args.keep).resolve() if args.keep else Path(tempfile.mkdtemp(prefix="oink-baseline-"))
    work_root.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "theme": theme_facts(theme),
        "hugo": hugo_facts(args.hugo),
        "method": {
            "noise": "theme shortcode tags outside escaped forms; fences counted; site-local / hugo built-in / unknown excluded; "
                     "generated corpus excluded via globs; native = GFM callouts + diagram/data fences + theme block-attribute markers",
            "build": "git clone --shared HEAD snapshot; go.work replace -> local theme; hugo --minify --printPathWarnings --panicOnWarning; "
                     "cold = fresh resources/, warm = second run; gzip level 6",
        },
        "sites": {},
    }
    total_noise = new_counter()
    total_excluded = new_counter()

    targets: list[tuple[str, Path, bool]] = []
    if args.example_site:
        targets.append(("exampleSite", EXAMPLE if theme == ROOT else theme / "exampleSite", True))
    for raw in args.sites:
        path = Path(raw).resolve()
        if not path.is_dir():
            print(f"skip {raw}: not a directory", file=sys.stderr)
            continue
        targets.append((path.name, path, False))

    for name, path, example in targets:
        print(f"== {name}", file=sys.stderr, flush=True)
        entry: dict = {"path": str(path)}
        snapshot = work_root / name
        shutil.rmtree(snapshot, ignore_errors=True)
        if example:
            shutil.copytree(path, snapshot, ignore=shutil.ignore_patterns("public", "resources", "themes"), symlinks=False)
            entry.update({"snapshot": "worktree", "revision": report["theme"]["commit"], "branch": None,
                          "dirty_worktree": report["theme"]["dirty"]})
        else:
            entry.update(snapshot_site(path, snapshot, worktree=name in args.worktree or str(path) in args.worktree))
        if do_noise:
            excludes = args.exclude if args.exclude is not None else DEFAULT_EXCLUDES.get(name, [])
            entry["noise"] = measure_site_noise(snapshot, theme_names, excludes)
            add_counter(total_noise, entry["noise"]["included"])
            add_counter(total_excluded, entry["noise"]["excluded_generated"])
        if do_assets:
            entry["build"] = measure_build(name, snapshot, args.hugo, theme, example=example)
            if example and args.rtl:
                rtl_cfg = work_root / "rtl.yaml"
                rtl_cfg.write_text("languages:\n  en:\n    direction: rtl\n")
                rtl_snapshot = work_root / f"{name}-rtl"
                shutil.rmtree(rtl_snapshot, ignore_errors=True)
                shutil.copytree(path, rtl_snapshot, ignore=shutil.ignore_patterns("public", "resources", "themes"), symlinks=False)
                report["sites"][f"{name}-rtl"] = {
                    "path": str(path), "snapshot": "worktree", "revision": report["theme"]["commit"],
                    "build": measure_build(f"{name}-rtl", rtl_snapshot, args.hugo, theme, example=True,
                                           config_extra=rtl_cfg),
                }
        report["sites"][name] = entry

    if do_noise:
        report["totals"] = {
            "noise": finish_counter(total_noise),
            "noise_excluded_generated": finish_counter(total_excluded),
        }

    markdown = render_markdown(report)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(markdown + "\n")
    print(markdown)
    if not args.keep:
        shutil.rmtree(work_root, ignore_errors=True)
    else:
        print(f"\nsnapshots kept in {work_root}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
