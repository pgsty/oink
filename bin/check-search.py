#!/usr/bin/env python3
"""Build and verify local-search metadata, ranking, and budgets."""

from __future__ import annotations

import gzip
from html.parser import HTMLParser
from urllib.parse import unquote
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from test_site import theme_warnings


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCRIPT = ROOT / "bin" / "check-navigation-contract.py"
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


class Headings(HTMLParser):
    """Collect the anchors local search may open: headings and search entries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.entries: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        value = attributes.get("id")
        if not value:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.ids.append(value)
        elif (attributes.get("data-td-search-entry") or "").strip():
            self.ids.append(value)
            self.entries[value] = " ".join(attributes["data-td-search-entry"].split())


def validate_sections(documents: list[dict[str, Any]], output: Path, prefix: str) -> None:
    for doc in documents:
        sections = doc.get("sections", [])
        if not sections:
            continue
        relative = unquote(doc["ref"][len(prefix):])
        parser = Headings()
        parser.feed((output / relative / "index.html").read_text())
        offsets = []
        for section in sections:
            require(section["id"] in parser.ids, f"invented heading anchor: {doc['ref']}#{section['id']}")
            entry = parser.entries.get(section["id"])
            require(entry is None or entry == section["title"],
                    f"search entry title changed: {doc['ref']}#{section['id']}")
            if "start" in section:
                offsets.append(section["start"])
                body = doc["body"].encode()[section["start"]:].decode()
                # A heading opens its own text; an entry may be named differently.
                require(entry is not None or body.startswith(section["title"]),
                        f"invalid UTF-8 section offset: {doc['ref']}")
        require(offsets == sorted(offsets), f"section offsets out of document order: {doc['ref']}")


def write_section_probe(site: Path) -> None:
    shortcode = site / "layouts" / "_shortcodes" / "search-headings.html"
    shortcode.parent.mkdir(parents=True, exist_ok=True)
    shortcode.write_text(
        '<h3 id="real-id" data-id="not-an-anchor" aria-label="a > b id=\'fake\'">Real  heading</h3>\n'
        "<h3 id='single-quote'>Single quote</h3>\n"
        '<script>const hidden = "<h3 id=\'phantom\'>Hidden</h3>";</script>\n'
        # Any element may name itself a search entry; it needs an id and a title.
        '<p id="custom-entry" data-td-search-entry="Custom &amp;  entry">probe_custom_text follows.</p>\n'
        '<dt data-td-search-entry=WorkMem id=work-mem>Working memory.</dt>\n'
        '<h2 id=storage>存储 <span id=storage-alias data-td-search-entry=StorageAlias>engine</span></h2>\n'
        '<h3 data-td-search-entry="Alias" id=runtime><span id=runtime-alias '
        'data-td-search-entry=\'Run &amp; time\'>Post</span>greSQL</h3>\n'
        '<h4 id=inline>pg<span data-td-search-entry=Catalog id=catalog>_catalog</span></h4>\n'
        '<p data-td-search-entry="No anchor">Not addressable.</p>\n'
        '<p id="untitled" data-td-search-entry="">No title.</p>\n'
        '<script>const decoy = "<p id=\'phantom-entry\' data-td-search-entry=\'Hidden\'></p>";</script>\n',
        encoding="utf-8")
    for suffix, title in (("", "Search probe"), (".zh", "搜索探针")):
        (site / "content" / "docs" / f"search-probe{suffix}.md").write_text(
            f'---\ntitle: "{title}"\noutputs: [HTML, Print, Markdown]\n---\n\n简介 😀 before headings.\n\n'
            '# 顶层标题\n\nPostgreSQL 物理备份。\n\n'
            '## Repeat\n\nshared_buffers controls cache.\n\n'
            '## Repeat\n\npg_basebackup -D /pg/data --checkpoint=fast\n\n'
            '### A & B `technical-name` {#stable-id}\n\n连接池 超时。\n\n'
            '###### 深层标题\n\nLast section.\n\n'
            '### Special & heading {id="特殊&id"}\n\n--special-option\n\n'
            '## 重复标题\n\nFirst Chinese section.\n\n'
            '## 重复标题\n\nSecond Chinese section.\n\n'
            '{{< search-headings >}}\n\n'
            '```filetree {title="Search output probe"}\n- docs/\n  - search.md # Local search\n```\n\n'
            '{{< fields >}}\n'
            '{{< field name="work_mem" type="integer" id="guc-work-mem" >}}\nBase memory for one sort.\n{{< /field >}}\n'
            '{{< field name="maintenance_work_mem" type="integer" >}}\nMemory for maintenance.\n{{< /field >}}\n'
            '{{< field name="clash" id="guc-work-mem" >}}\nAn id another field already uses.\n{{< /field >}}\n'
            '{{< /fields >}}\n', encoding="utf-8")


def write_large_page(site: Path) -> None:
    """Add one English page that pushes the index past the single-file budget."""
    paragraph = "Filler sentence for the split-index probe. " * 12
    filler = (paragraph + "\n\n") * 150
    parts = "".join(f"## Part {number}\n\n{filler}" for number in range(30))
    (site / "content" / "docs" / "search-large.md").write_text(
        '---\ntitle: "Large page"\n---\n\nIntroduction.\n\n' + parts
        + "## Last part\n\nneedle_in_last_part closes the page.\n",
        encoding="utf-8")


def validate_split(helper: Any, workspace: Path, budget: dict[str, int]) -> str:
    """A large index publishes page text separately; a small one stays whole."""
    site = workspace / "site-split"
    output = workspace / "public-split"
    helper.copy_fixture_site(site, "flat", True, subpath=True)
    write_section_probe(site)
    write_large_page(site)
    helper.run_hugo(site, output, workspace / "cache-split")
    require(not list(output.glob("offline-search-source*")),
            "the unsplit index source was published")

    index_file = index_path(output, "en")
    documents = json.loads(index_file.read_text(encoding="utf-8"))
    require(all("body" not in doc for doc in documents), "split index kept page text")
    payload = index_file.read_bytes()
    require(len(payload) <= budget["uncompressed_bytes"]
            and len(gzip.compress(payload, mtime=0)) <= budget["gzip_bytes"],
            "split navigation index exceeds the budget")
    body_files = sorted(output.glob("offline-search-body.en*.json"))
    require(len(body_files) == 1, f"expected one en body file, found {body_files}")
    entries = json.loads(body_files[0].read_text(encoding="utf-8"))
    require(isinstance(entries, list) and entries
            and all(set(entry) == {"ref", "body"} for entry in entries),
            "page-text file is not a list of ref/body entries")
    bodies = {entry["ref"]: entry["body"] for entry in entries}
    require(len(bodies) == len(entries) and set(bodies) <= {doc["ref"] for doc in documents},
            "page-text entries do not match index documents")
    merged = [dict(doc, body=bodies[doc["ref"]]) if doc["ref"] in bodies else doc
              for doc in documents]
    validate_sections(merged, output, "/preview/")
    large = by_suffix(merged, "/docs/search-large/")
    last = large["sections"][-1]
    require(last["title"] == "Last part"
            and "needle_in_last_part" in large["body"].encode()[last["start"]:].decode(),
            "section offsets no longer address the separated page text")

    html = (output / "en" / "docs" / "guides" / "tutorial" / "index.html").read_text(encoding="utf-8")
    require(f'data-td-index-src="/preview/{index_file.name}"' in html
            and f'data-td-body-src="/preview/{body_files[0].name}"' in html
            and f'data-td-body-bytes="{body_files[0].stat().st_size}"' in html
            and "data-td-t-body-load=" in html and "data-td-t-body-loading=" in html,
            "dialog does not announce the separated page text and its size")

    # The other language stays within the budget and therefore in one file.
    require(not list(output.glob("offline-search-body.zh*.json")), "a small index was split")
    chinese = json.loads(index_path(output, "zh").read_text(encoding="utf-8"))
    require(any("body" in doc for doc in chinese), "an unsplit index lost its page text")
    html = (output / "zh" / "docs" / "guides" / "tutorial" / "index.html").read_text(encoding="utf-8")
    require("data-td-body-src" not in html and "data-td-t-body-load" not in html,
            "an unsplit index announced separate page text")

    behavior = subprocess.run(
        ["node", str(ROOT / "tests" / "js" / "search-engine.test.js"),
         str(index_file), str(index_path(output, "zh"))],
        cwd=ROOT, capture_output=True, check=False, text=True)
    require(behavior.returncode == 0,
            "ranking on a split index failed:\n" + (behavior.stdout + behavior.stderr).strip())
    return (f"split/en: {len(payload)} B index + {body_files[0].stat().st_size} B page text")


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
                write_section_probe(site)
                log = helper.run_hugo(site, output, workspace / "cache")
                warnings = theme_warnings(log)
                expected_warnings = ("invalid search_boost", "data-td-search-entry element needs an id",
                                     'id "guc-work-mem" is already used')
                require(
                    all(any(text in line for line in warnings) for text in expected_warnings)
                    and all(any(text in line for text in expected_warnings) for line in warnings),
                    f"{deployment} build did not emit only the expected warnings: {warnings}",
                )

                for lang in helper.LANGUAGES:
                    path = index_path(output, lang)
                    built_indexes[deployment][lang] = path
                    payload = path.read_bytes()
                    documents = json.loads(payload)
                    require(isinstance(documents, list), f"{lang} index is not an array")
                    validate_language(documents, lang, prefix, required_fields)
                    validate_sections(documents, output, prefix)
                    require(not list(output.glob("offline-search-body.*")),
                            f"{deployment} index within the budget was split")
                    home_rel = "" if lang == "en" else f"{lang}/"
                    home_html = (output / home_rel / "index.html").read_text()
                    require('data-td-search-scope-row' not in home_html,
                            f"{lang} home page rendered a self-referential section scope radio")
                    for suffix in ("/docs/guides/tutorial/", "/blog/post/"):
                        doc = by_suffix(documents, suffix)
                        html = (output / doc["ref"][len(prefix):] / "index.html").read_text()
                        scopes = re.findall(r'<input\b[^>]*name="td-search-scope"[^>]*>', html)
                        require(len(scopes) == 2 and 'role="radiogroup"' in html
                                and 'aria-labelledby="td-search-scope-label"' in html
                                and 'value=""' in scopes[0] and 'checked' in scopes[0]
                                and f'value="{doc["root"]}"' in scopes[1],
                                f"{doc['ref']} inherited another root's cached search dialog")
                    probe = by_suffix(documents, "/docs/search-probe/")
                    probe_html = (output / probe["ref"][len(prefix):] / "index.html").read_text()
                    require('class="td-filetree' in probe_html and 'class="td-filetree-source"' not in probe_html,
                            "search traversal rendered RSS source inside an HTML page")
                    ids = [section["id"] for section in probe["sections"]]
                    require(ids == ["顶层标题", "repeat", "repeat-1", "stable-id", "深层标题", "特殊&id", "重复标题", "重复标题-1", "real-id", "single-quote",
                                    "custom-entry", "work-mem", "storage", "storage-alias", "runtime", "runtime-alias",
                                    "inline", "catalog", "guc-work-mem", "field-maintenance_work_mem", "field-clash"],
                            f"{lang} duplicate/Unicode/explicit/deep headings or search entries changed: {ids}")
                    titles = {section["id"]: section["title"] for section in probe["sections"]}
                    require(titles["custom-entry"] == "Custom & entry" and titles["guc-work-mem"] == "work_mem"
                            and titles["field-maintenance_work_mem"] == "maintenance_work_mem",
                            f"{lang} search entry titles changed: {titles}")
                    require("work_mem" not in probe["headings"] and "Custom" not in probe["headings"],
                            f"{lang} headings field lists search entries")
                    require(titles["work-mem"] == "WorkMem" and titles["storage-alias"] == "StorageAlias"
                            and titles["runtime-alias"] == "Run & time"
                            and titles["storage"] == "存储 engine" and titles["runtime"] == "PostgreSQL"
                            and titles["inline"] == "pg_catalog"
                            and "存储 engine PostgreSQL pg_catalog" in probe["headings"]
                            and "StorageAlias" not in probe["headings"],
                            f"{lang} lost an unquoted entry or nested heading title")
                    starts = {section["id"]: section["start"] for section in probe["sections"]}
                    body = probe["body"].encode()
                    require(body[starts["storage"]:starts["storage-alias"]].decode() == "存储 "
                            and starts["runtime"] == starts["runtime-alias"]
                            and body[starts["inline"]:starts["catalog"]] == b"pg"
                            and body[starts["catalog"]:].startswith(b"_catalog"),
                            f"{lang} nested entry offsets do not address the rendered text")
                    custom = probe["body"].encode()[next(s["start"] for s in probe["sections"] if s["id"] == "custom-entry"):].decode()
                    require(custom.startswith("probe_custom_text"), f"{lang} entry offset does not open its text")
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

            reports.append(validate_split(helper, workspace, budget))

            # Scope reductions must retain only the promised searchable fields.
            for scope in ("title", "heading", "summary"):
                site = workspace / f"scope-{scope}"
                output = workspace / f"public-{scope}"
                helper.copy_fixture_site(site, "flat", True, subpath=True)
                write_section_probe(site)
                config_path = site / "hugo.yaml"
                config_path.write_text(config_path.read_text().replace(
                    "params:\n", f"params:\n  offline_search_index: {scope}\n", 1))
                helper.run_hugo(site, output, workspace / f"cache-{scope}")
                for lang in helper.LANGUAGES:
                    documents = json.loads(index_path(output, lang).read_text())
                    validate_sections(documents, output, "/preview/")
                    probe = by_suffix(documents, "/docs/search-probe/")
                    require("body" not in probe, f"{scope} leaked full text")
                    require(bool(probe.get("sections")) == (scope != "title"), f"{scope} section scope")
                    require(all("start" not in section for section in probe.get("sections", [])),
                            f"{scope} emitted offsets without bodies")

            invalid_site = workspace / "site-algolia-invalid"
            invalid_output = workspace / "public-algolia-invalid"
            helper.copy_fixture_site(invalid_site, "flat", False, subpath=False)
            config = (invalid_site / "hugo.yaml").read_text(encoding="utf-8")
            config = config.replace(
                "params:\n",
                "params:\n  search:\n    algolia:\n      appId: incomplete\n",
                1,
            )
            (invalid_site / "hugo.yaml").write_text(config, encoding="utf-8")
            log = helper.run_hugo(
                invalid_site, invalid_output, workspace / "cache-algolia-invalid"
            )
            require(
                "params.search.algolia requires explicit appId, apiKey, and indexName" in log,
                "incomplete Algolia configuration did not warn",
            )
            rendered = "\n".join(
                path.read_text(encoding="utf-8")
                for path in invalid_output.rglob("*.html")
            )
            require(
                "td-docsearch" not in rendered
                and not (invalid_output / "third_party/docsearch").exists(),
                "incomplete Algolia configuration still emitted DocSearch markup or assets",
            )
            valid_site = workspace / "site-algolia-valid"
            valid_output = workspace / "public-algolia-valid"
            helper.copy_fixture_site(valid_site, "flat", False, subpath=False)
            config_path = valid_site / "hugo.yaml"
            config_path.write_text(config_path.read_text().replace("params:\n",
                "params:\n  search:\n    algolia:\n      appId: TESTAPP\n      apiKey: public-search-key\n      indexName: docs-index\n", 1))
            helper.run_hugo(valid_site, valid_output, workspace / "cache-algolia-valid")
            rendered = "\n".join(path.read_text() for path in valid_output.rglob("*.html"))
            require(re.search(r'indices:\s*\["docs-index"\]', rendered) is not None,
                    "DocSearch 5 did not receive the configured index through indices")
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
