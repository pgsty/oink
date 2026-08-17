#!/usr/bin/env python3
"""Build and verify local-search metadata, ranking, and budgets."""

from __future__ import annotations

import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCRIPT = ROOT / "scripts" / "check-navigation-contract.py"
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "navigation" / "contract.json"
NEW_FIELDS = {"root", "section", "type", "keywords", "boost", "breadcrumb", "icon"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_contract_module() -> Any:
    spec = importlib.util.spec_from_file_location("navigation_contract", CONTRACT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the navigation fixture helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def index_path(output: Path, lang: str) -> Path:
    candidates = sorted(output.glob(f"offline-search-index.{lang}*.json"))
    require(
        len(candidates) == 1,
        f"expected one {lang} index, found {[path.name for path in candidates]}",
    )
    return candidates[0]


def by_suffix(documents: list[dict[str, Any]], suffix: str) -> dict[str, Any]:
    matches = [doc for doc in documents if doc.get("ref", "").endswith(suffix)]
    require(len(matches) == 1, f"expected one index entry ending in {suffix}")
    return matches[0]


def compact_payload(documents: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        documents, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def validate_language(
    documents: list[dict[str, Any]],
    lang: str,
    deployment_prefix: str,
    required_fields: set[str],
) -> None:
    require(documents, f"{lang} index is empty")
    other = "zh" if lang == "en" else "en"
    for doc in documents:
        ref = doc.get("ref", "")
        require(ref.startswith(deployment_prefix + lang + "/"), f"unsafe {lang} ref: {ref}")
        require(f"/{other}/" not in ref, f"{lang} index contains {other} ref: {ref}")
        require(required_fields <= set(doc), f"{ref} is missing index fields")
        require(isinstance(doc["keywords"], list), f"{ref} keywords are not an array")
        require(isinstance(doc["breadcrumb"], list), f"{ref} breadcrumb is not an array")
        require(
            isinstance(doc["boost"], (int, float)) and doc["boost"] > 0,
            f"{ref} has an invalid emitted boost",
        )

    for suffix in ("/docs/excluded-canonical/", "/docs/guides/nav-active/"):
        require(
            not any(doc["ref"].endswith(suffix) for doc in documents),
            f"{lang} index retained search_exclude fixture {suffix}",
        )

    tutorial = by_suffix(documents, "/docs/guides/tutorial/")
    advanced = by_suffix(documents, "/docs/guides/advanced/")
    reference = by_suffix(documents, "/docs/reference/")
    post = by_suffix(documents, "/blog/post/")

    expected = {
        "en": {
            "tutorial_title": "First Tutorial",
            "tutorial_keywords": ["postgresql", "pgboost"],
            "advanced_keywords": ["pgboost"],
            "reference_keywords": ["postgres"],
            "tutorial_breadcrumb": ["Docs", "Guides", "First Tutorial"],
            "reference_breadcrumb": ["Docs", "Reference"],
            "blog_breadcrumb": ["Blog", "Release Post"],
        },
        "zh": {
            "tutorial_title": "第一个教程",
            "tutorial_keywords": ["数据库别名", "增强词"],
            "advanced_keywords": ["增强词"],
            "reference_keywords": ["数据库别名"],
            "tutorial_breadcrumb": ["文档", "指南", "第一个教程"],
            "reference_breadcrumb": ["文档", "参考"],
            "blog_breadcrumb": ["博客", "发布文章"],
        },
    }[lang]

    require(tutorial["title"] == expected["tutorial_title"], f"{lang} tutorial changed")
    require(tutorial["keywords"] == expected["tutorial_keywords"], f"{lang} keyword array changed")
    require(advanced["keywords"] == expected["advanced_keywords"], f"{lang} advanced keywords changed")
    require(reference["keywords"] == expected["reference_keywords"], f"{lang} scalar keyword was not normalized")
    require(tutorial["boost"] == 1.5, f"{lang} cascade boost was not inherited")
    require(advanced["boost"] == 3, f"{lang} explicit boost did not override cascade")
    require(reference["boost"] == 1, f"{lang} invalid boost did not fall back")
    require(tutorial["breadcrumb"] == expected["tutorial_breadcrumb"], f"{lang} tutorial breadcrumb changed")
    require(reference["breadcrumb"] == expected["reference_breadcrumb"], f"{lang} reference breadcrumb changed")
    require(post["breadcrumb"] == expected["blog_breadcrumb"], f"{lang} blog breadcrumb changed")
    require(
        (tutorial["root"], tutorial["section"], tutorial["type"])
        == ("docs", "guides", "docs"),
        f"{lang} docs root/section/type fallback changed",
    )
    require(
        (post["root"], post["section"], post["type"])
        == ("blog", "blog", "blog"),
        f"{lang} blog root/section/type fallback changed",
    )
    require(tutorial["icon"] == "fa-solid fa-rocket", f"{lang} page icon fallback changed")


def main() -> int:
    reports: list[str] = []
    built_indexes: dict[str, dict[str, Path]] = {}
    try:
        helper = load_contract_module()
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        required_fields = set(contract["search"]["index_fields"])
        budget = contract["search"]["size_budget"]
        with tempfile.TemporaryDirectory(prefix="oink-search-") as temp:
            workspace = Path(temp)
            for deployment, subpath, prefix in (
                ("root", False, "/"),
                ("subpath", True, "/preview/"),
            ):
                built_indexes[deployment] = {}
                site = workspace / f"site-{deployment}"
                output = workspace / f"public-{deployment}"
                helper.copy_fixture_site(site, "flat", True, subpath=subpath)
                log = helper.run_hugo(site, output, workspace / "cache")
                warnings = [line for line in log.splitlines() if "WARN" in line]
                require(
                    warnings and all("invalid search_boost" in line for line in warnings),
                    f"{deployment} build did not emit only invalid-boost warnings",
                )

                for lang in helper.LANGUAGES:
                    path = index_path(output, lang)
                    built_indexes[deployment][lang] = path
                    payload = path.read_bytes()
                    documents = json.loads(payload)
                    require(isinstance(documents, list), f"{lang} index is not an array")
                    validate_language(documents, lang, prefix, required_fields)
                    raw_size = len(payload)
                    gzip_size = len(gzip.compress(payload, mtime=0))
                    require(raw_size <= budget["uncompressed_bytes"], f"{lang} raw index exceeds budget")
                    require(gzip_size <= budget["gzip_bytes"], f"{lang} gzip index exceeds budget")

                    baseline = [
                        {key: value for key, value in doc.items() if key not in NEW_FIELDS}
                        for doc in documents
                    ]
                    baseline_payload = compact_payload(baseline)
                    baseline_gzip = len(gzip.compress(baseline_payload, mtime=0))
                    full_payload = compact_payload(documents)
                    full_gzip = len(gzip.compress(full_payload, mtime=0))
                    reports.append(
                        f"{deployment}/{lang}: {raw_size} B raw "
                        f"(+{len(full_payload) - len(baseline_payload)} metadata), "
                        f"{gzip_size} B gzip (+{full_gzip - baseline_gzip})"
                    )

            for deployment, indexes in built_indexes.items():
                behavior = subprocess.run(
                    [
                        "node",
                        str(ROOT / "tests" / "js" / "search-engine.test.js"),
                        str(indexes["en"]),
                        str(indexes["zh"]),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                    text=True,
                )
                require(
                    behavior.returncode == 0,
                    f"{deployment} search ranking behavior test failed:\n"
                    + (behavior.stdout + behavior.stderr).strip(),
                )
        palette = (ROOT / "assets" / "js" / "command-palette.js").read_text(encoding="utf-8")
        require(
            "searchApi.group(results)" in palette
            and "td-shell-search__group-label" in palette,
            "Palette does not render normalized result groups",
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"search check failed: {exc}", file=sys.stderr)
        return 1

    print("search metadata and ranking checks passed")
    for report in reports:
        print(f"  {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
