#!/usr/bin/env python3
"""Agent index contracts: the LLMSFULL bundle and the NAVJSON tree.

Both outputs are opt-in through Hugo output configuration. The bundle
concatenates the same semantic Markdown the per-page output publishes, in the
sidebar reading order, one file per enabled top-level section per language.
The navigation JSON serializes the same authority chain the sidebar and pager
read, one file per language at the language root. This checker owns:

- language isolation: each artifact carries only its own language's pages;
- source integrity: every `Source:` pointer and navigation URL resolves to a
  built artifact, bundle pages appear exactly once, the section index leads;
- reading order: bundle pages follow their declared front-matter weights, and
  the navigation JSON's docs subtree flattens to the same sequence the bundle
  publishes -- two template paths, one authority;
- schema: navigation.json validates against schema/nav.v1.schema.json;
- discovery: llms.txt lists the enabled bundle and navigation.json for its
  own language;
- determinism: two builds of the same sources produce identical artifacts;
- the explicit tree: a site with data/docs_nav.json gets its docs subtree in
  the declared order, manual links included as external nodes;
- the negative contract: enabling LLMSFULL on a nested section warns, emits
  nothing, and keeps a build usable with visible warnings.

Artifact sizes are reported as evidence, never enforced: a model-context
ceiling is a consumer's judgement, not a build gate.

  bin/check-agent-indexes.py                # build the fixture and check
  bin/check-agent-indexes.py --hugo PATH    # build with another Hugo binary
  bin/check-agent-indexes.py --public DIR   # reuse a build (skips build cases)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from test_site import ROOT, TEST_SITE, build_fixture_public, fixture_config

BASE_URL = "https://example.org/"
BUILD_TIMEOUT = 120
NAV_SCHEMA = ROOT / "schema/nav.v1.schema.json"

BUNDLES = {
    "docs/llms-full.txt": {"lang": "en", "index": "docs/index.md"},
    "zh/docs/llms-full.txt": {"lang": "zh", "index": "zh/docs/index.md"},
}

NAV_FILES = {
    "navigation.json": "en",
    "zh/navigation.json": "zh",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def bundle_sources(text: str) -> list[str]:
    return re.findall(r"^Source: (\S+)$", text, flags=re.MULTILINE)


def weight_order(language: str) -> list[str]:
    """Expected relative URL order of the docs pages, from front-matter weights.

    An independent oracle: the bundle must present pages in ascending declared
    weight, the same order the sidebar and pager derive from the content tree.
    Only pages with an explicit unique weight participate; the fixture keeps
    them unique on purpose.
    """

    weighted: list[tuple[int, str]] = []
    for path in sorted((TEST_SITE / "content/docs").glob("*.md")):
        if path.name.startswith("_index"):
            continue
        is_zh = path.name.endswith(".zh.md")
        if (language == "zh") != is_zh:
            continue
        front = path.read_text(encoding="utf-8").split("---\n")
        if len(front) < 2:
            continue
        match = re.search(r"^weight:\s*(\d+)\s*$", front[1], flags=re.MULTILINE)
        if not match:
            continue
        slug = path.name.removesuffix(".zh.md").removesuffix(".md")
        prefix = "zh/" if language == "zh" else ""
        weighted.append((int(match.group(1)), f"{prefix}docs/{slug}/index.md"))
    weighted.sort()
    return [url for _, url in weighted]


def check_bundle(public: Path, rel_path: str, spec: dict, errors: list[str]) -> None:
    bundle_path = public / rel_path
    require(bundle_path.exists(), f"{rel_path} was not built", errors)
    if not bundle_path.exists():
        return
    text = bundle_path.read_text(encoding="utf-8")
    sources = bundle_sources(text)
    require(len(sources) >= 2, f"{rel_path} holds fewer than two pages", errors)
    require(len(sources) == len(set(sources)),
            f"{rel_path} repeats a Source pointer", errors)
    separators = text.count("================\n")
    require(separators == 2 * len(sources),
            f"{rel_path} separator count {separators} does not frame "
            f"{len(sources)} Source pointers", errors)

    paths: list[str] = []
    for url in sources:
        require(url.startswith(BASE_URL),
                f"{rel_path} lists an off-site source: {url}", errors)
        if not url.startswith(BASE_URL):
            continue
        rel = url.removeprefix(BASE_URL)
        paths.append(rel)
        require((public / rel).exists(),
                f"{rel_path} points at an unbuilt source: {url}", errors)
        in_zh = rel.startswith("zh/")
        require(in_zh == (spec["lang"] == "zh"),
                f"{rel_path} crosses languages with {url}", errors)

    require(bool(paths) and paths[0] == spec["index"],
            f"{rel_path} does not lead with its section index", errors)

    expected = weight_order(spec["lang"])
    listed = [path for path in paths if path in set(expected)]
    require(listed == expected,
            f"{rel_path} order diverges from front-matter weights:\n"
            f"    bundle:   {listed}\n    expected: {expected}", errors)

    # One renderer, provably: each bundle segment must equal the page's own
    # published .md byte-for-byte (modulo surrounding blank lines). Author
    # markup quoted in source flows through both on purpose; output purity
    # itself is owned by the per-page markdown gates.
    segments = re.split(
        r"^================\nSource: (\S+)\n================\n\n",
        text, flags=re.MULTILINE)
    for url, body in zip(segments[1::2], segments[2::2]):
        rel = url.removeprefix(BASE_URL)
        if not rel.endswith(".md"):
            continue
        page_file = public / rel
        if not page_file.exists():
            continue  # already reported by the source-integrity check
        require(body.strip() == page_file.read_text(encoding="utf-8").strip(),
                f"{rel_path} segment for {rel} diverges from the per-page output",
                errors)

    print(f"  {rel_path}: {len(sources)} pages, {len(text.encode('utf-8'))} bytes")


def check_discovery(public: Path, errors: list[str]) -> None:
    for llms, bundle, nav in (
        ("llms.txt", "docs/llms-full.txt", "navigation.json"),
        ("zh/llms.txt", "zh/docs/llms-full.txt", "zh/navigation.json"),
    ):
        index = public / llms
        require(index.exists(), f"{llms} was not built", errors)
        if not index.exists():
            continue
        text = index.read_text(encoding="utf-8")
        require(f"{BASE_URL}{bundle}" in text,
                f"{llms} does not list the enabled bundle {bundle}", errors)
        require(f"{BASE_URL}{nav}" in text,
                f"{llms} does not list the navigation JSON {nav}", errors)


def validate_against(instance, schema, root_schema, path="$") -> list[str]:
    """Validate against the subset of JSON Schema nav.v1 actually uses.

    Supported keywords: $ref into #/$defs, oneOf, const, enum, type
    (object/array/string), minLength, required, properties,
    additionalProperties: false, items. Anything else in the schema is a
    checker bug, reported loudly rather than silently accepted.
    """

    problems: list[str] = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            return [f"{path}: unsupported $ref {ref}"]
        return validate_against(
            instance, root_schema["$defs"][ref.removeprefix("#/$defs/")],
            root_schema, path)
    if "oneOf" in schema:
        matches = sum(
            1 for branch in schema["oneOf"]
            if not validate_against(instance, branch, root_schema, path))
        if matches != 1:
            problems.append(f"{path}: matches {matches} oneOf branches, not 1")
        return problems
    if "const" in schema and instance != schema["const"]:
        problems.append(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        problems.append(f"{path}: {instance!r} not in {schema['enum']}")
    kinds = {"object": dict, "array": list, "string": str}
    expected = schema.get("type")
    if expected:
        if expected not in kinds:
            return [f"{path}: unsupported schema type {expected}"]
        if not isinstance(instance, kinds[expected]):
            problems.append(f"{path}: expected a {expected}")
            return problems
    if expected == "string" and len(instance) < schema.get("minLength", 0):
        problems.append(f"{path}: shorter than minLength")
    if expected == "object":
        for key in schema.get("required", []):
            if key not in instance:
                problems.append(f"{path}: missing required {key!r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    problems.append(f"{path}: unexpected property {key!r}")
        for key, sub in props.items():
            if key in instance:
                problems += validate_against(
                    instance[key], sub, root_schema, f"{path}.{key}")
    if expected == "array":
        for index, item in enumerate(instance):
            problems += validate_against(
                item, schema.get("items", {}), root_schema, f"{path}[{index}]")
    return problems


def nav_page_nodes(node: dict) -> list[dict]:
    nodes = [node] if node.get("kind") in ("home", "section", "page") else []
    for child in node.get("children", []):
        nodes += nav_page_nodes(child)
    return nodes


def check_navigation(public: Path, errors: list[str]) -> None:
    schema = json.loads(NAV_SCHEMA.read_text(encoding="utf-8"))
    for rel_path, lang in NAV_FILES.items():
        nav_path = public / rel_path
        require(nav_path.exists(), f"{rel_path} was not built", errors)
        if not nav_path.exists():
            continue
        nav = json.loads(nav_path.read_text(encoding="utf-8"))
        for problem in validate_against(nav, schema, schema):
            errors.append(f"{rel_path}: schema violation: {problem}")
        require(nav.get("language") == lang,
                f"{rel_path} declares language {nav.get('language')!r}", errors)
        pages = nav_page_nodes(nav.get("root", {}))
        for node in pages:
            for field in ("url", "markdown"):
                url = node.get(field)
                if not url:
                    continue
                require(url.startswith(BASE_URL),
                        f"{rel_path} node {node.get('id')} has an off-site "
                        f"{field}: {url}", errors)
                if not url.startswith(BASE_URL):
                    continue
                rel = url.removeprefix(BASE_URL)
                in_zh = rel.startswith("zh/")
                require(in_zh == (lang == "zh"),
                        f"{rel_path} crosses languages with {url}", errors)
                target = rel + "index.html" if (not rel or rel.endswith("/")) else rel
                require((public / target).exists(),
                        f"{rel_path} node {node.get('id')} points at an "
                        f"unbuilt {field}: {url}", errors)
            # ids are language-neutral so agents can correlate translations.
            require(not str(node.get("id", "")).startswith("/zh/"),
                    f"{rel_path} id {node.get('id')} carries a language prefix",
                    errors)

        # Two template paths, one authority: the docs subtree must flatten to
        # exactly the page sequence the LLMSFULL bundle publishes.
        bundle_rel = "docs/llms-full.txt" if lang == "en" else "zh/docs/llms-full.txt"
        bundle_path = public / bundle_rel
        docs = [c for c in nav.get("root", {}).get("children", [])
                if c.get("id") == "/docs/"]
        require(len(docs) == 1, f"{rel_path} lacks a single /docs/ node", errors)
        if len(docs) == 1 and bundle_path.exists():
            flattened = [node["markdown"] for node in nav_page_nodes(docs[0])
                         if "markdown" in node]
            sources = bundle_sources(bundle_path.read_text(encoding="utf-8"))
            require(flattened == sources,
                    f"{rel_path} docs subtree diverges from the bundle order:\n"
                    f"    json:   {flattened}\n    bundle: {sources}", errors)

        print(f"  {rel_path}: {len(pages)} page nodes, "
              f"{len(nav_path.read_bytes())} bytes")


def check_determinism(hugo: str, first: Path, errors: list[str]) -> None:
    second, result = build_fixture_public(hugo)
    require(result.returncode == 0,
            "second fixture build failed; determinism unverified", errors)
    if result.returncode != 0:
        return
    for rel_path in list(BUNDLES) + list(NAV_FILES):
        a = (first / rel_path).read_bytes() if (first / rel_path).exists() else b""
        b = (second / rel_path).read_bytes() if (second / rel_path).exists() else b""
        require(a == b, f"{rel_path} differs between two identical builds", errors)


def check_explicit_tree(hugo: str, errors: list[str]) -> None:
    """A declared data/docs_nav.json owns the docs subtree order.

    The temporary site declares the tree in the reverse of the weights, plus a
    manual-link placeholder, and the navigation JSON must follow the declared
    order with the placeholder as an external node. Site-local HTML layouts
    keep the case focused on the navigation output.
    """

    with tempfile.TemporaryDirectory(prefix="oink-agent-indexes-explicit-") as temp:
        site = Path(temp) / "site"

        def write(path: Path, text: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        write(site / "hugo.yaml", f"""baseURL: https://example.org/
title: Explicit tree fixture
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
outputs:
  home: [NAVJSON]
  section: [HTML]
  page: [HTML]
""")
        # Type-specific theme layouts outrank a site's _default, so the
        # overrides sit at the docs type to keep the case focused on the
        # navigation output rather than the full docs shell.
        write(site / "layouts/docs/single.html", "ok\n")
        write(site / "layouts/docs/list.html", "ok\n")
        write(site / "content/docs/_index.md", "---\ntitle: Docs\n---\n")
        write(site / "content/docs/a.md", "---\ntitle: A\nweight: 10\n---\n")
        write(site / "content/docs/b.md", "---\ntitle: B\nweight: 20\n---\n")
        write(site / "content/docs/ext.md",
              "---\ntitle: Ext\nweight: 30\nmanual_link: https://example.com/ext\n---\n")
        write(site / "data/docs_nav.json", json.dumps({"sections": [
            {"page": "/docs/b", "url": "/docs/b/"},
            {"page": "/docs/ext", "url": "/docs/ext/"},
            {"page": "/docs/a", "url": "/docs/a/"},
        ]}))
        result = subprocess.run(
            [hugo, "--source", str(site), "--themesDir", str(ROOT.parent),
             "--destination", str(site / "public"), "--logLevel", "warn"],
            capture_output=True, text=True, check=False, timeout=BUILD_TIMEOUT)
        require(result.returncode == 0,
                "explicit-tree fixture build failed:\n"
                + result.stdout + result.stderr, errors)
        if result.returncode != 0:
            return
        nav_path = site / "public/navigation.json"
        require(nav_path.exists(), "explicit-tree navigation.json missing", errors)
        if not nav_path.exists():
            return
        nav = json.loads(nav_path.read_text(encoding="utf-8"))
        docs = [c for c in nav["root"].get("children", [])
                if c.get("id") == "/docs/"]
        require(len(docs) == 1, "explicit-tree /docs/ node missing", errors)
        if len(docs) != 1:
            return
        children = docs[0].get("children", [])
        shape = [(c.get("kind"), c.get("id") or c.get("url")) for c in children]
        expected = [
            ("page", "/docs/b/"),
            ("external", "https://example.com/ext"),
            ("page", "/docs/a/"),
        ]
        require(shape == expected,
                "explicit tree order was not honoured:\n"
                f"    json:     {shape}\n    expected: {expected}", errors)


def check_explicit_boundaries(hugo: str, errors: list[str]) -> None:
    """The explicit tree retains content-tree visibility and link semantics."""
    with tempfile.TemporaryDirectory(prefix="oink-nav-boundaries-") as temp:
        site = Path(temp)
        def write(relative: str, value: str) -> None:
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")
        write("hugo.yaml", f"""baseURL: https://example.org/manual/
title: Navigation boundaries
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
outputs:
  home: [HTML, NAVJSON]
  section: [HTML]
  page: [HTML]
""")
        write("layouts/index.html", "ok")
        layout = ('{{ .Store.Set "tdOutputFormat" "html" }}'
                  '{{ partial "shell/sidebar.html" . }}'
                  '{{ $p := partial "pager-state.html" . }}'
                  '{{ with $p.prev }}<a data-prev href="{{ .RelPermalink }}"></a>{{ end }}'
                  '{{ with $p.next }}<a data-next href="{{ .RelPermalink }}"></a>{{ end }}')
        write("layouts/docs/list.html", layout)
        write("layouts/docs/single.html", layout)
        write("content/docs/_index.md", "---\ntitle: Docs\noutputs: [HTML, LLMSFULL]\n---\n")
        write("content/docs/a.md", "---\ntitle: A\nweight: 1\n---\nVisible A\n")
        write("content/docs/b.md", "---\ntitle: B\nweight: 2\n---\nVisible B\n")
        write("content/docs/alias.md", "---\ntitle: Alias\nmanual_link_relref: /docs/a\nweight: 3\n---\n")
        write("content/docs/bad-alias.md", "---\ntitle: Bad alias\nmanual_link_relref: /docs/does-not-exist\nweight: 4\n---\n")
        write("content/docs/hidden/_index.md", "---\ntitle: Hidden group\ntoc_hide: true\n---\n")
        write("content/docs/hidden/child.md", "---\ntitle: Hidden child\n---\nHidden body\n")
        declared = [
            {"page": "/docs/hidden", "url": "/docs/hidden/", "children": [
                {"page": "/docs/hidden/child", "url": "/docs/hidden/child/"}]},
            {"page": "/docs/b", "url": "/docs/b/"},
            {"page": "/docs/alias", "url": "/docs/alias/"},
            {"page": "/docs/bad-alias", "url": "/docs/bad-alias/"},
            {"page": "/docs/a", "url": "/docs/a/"},
        ]
        for name, sections in (("declared", declared), ("empty", [])):
            write("data/docs_nav.json", json.dumps({"sections": sections}))
            destination = site / name
            command = [hugo, "--source", str(site), "--themesDir", str(ROOT.parent),
                       "--destination", str(destination), "--logLevel", "warn"]
            result = subprocess.run(command,
                                    capture_output=True, text=True, check=False, timeout=BUILD_TIMEOUT)
            require(result.returncode == 0, f"{name} navigation build failed: {result.stdout}{result.stderr}", errors)
            if result.returncode != 0:
                continue
            html = (destination / "docs/index.html").read_text()
            nav = json.loads((destination / "navigation.json").read_text())
            children = nav["root"]["children"][0]["children"]
            bundle = (destination / "docs/llms-full.txt").read_text()
            order = ["b", "a"] if sections else ["a", "b"]
            require("Hidden group" not in html and "Hidden child" not in html,
                    f"{name}: sidebar included a toc_hide subtree", errors)
            require("hidden" not in json.dumps(children), f"{name}: NAVJSON included a toc_hide subtree", errors)
            require(bundle_sources(bundle) == ["https://example.org/manual/docs/"] +
                    [f"https://example.org/manual/docs/{page}/" for page in order],
                    f"{name}: LLMSFULL visibility or reading order differs", errors)
            alias = next((node for node in children if node["title"] == "Alias"), {})
            require(alias == {"title": "Alias", "kind": "link", "url": "/manual/docs/a/"},
                    f"{name}: internal alias lost its target: {alias}", errors)
            bad = next((node for node in children if node["title"] == "Bad alias"), {})
            require(bad.get("url") == "/manual/docs/bad-alias/", "invalid alias lost its safe permalink", errors)
            require("does not resolve to a page" in result.stdout + result.stderr, "invalid alias emitted no warning", errors)
            first = (destination / f"docs/{order[0]}/index.html").read_text()
            require(f'<a data-next href="/manual/docs/{order[1]}/">' in first,
                    f"{name}: pager differs from visible reading order", errors)
            if not sections:
                require("falling back to the section tree" in result.stdout + result.stderr,
                        "empty explicit navigation did not warn", errors)


def check_navigation_path_keys(hugo: str, errors: list[str]) -> None:
    """Identity and declared section order survive language/deployment prefixes."""
    for base_path in ("/", "/manual/"):
        for language_subdir in (False, True):
            case = f"{base_path} language_subdir={language_subdir}"
            with tempfile.TemporaryDirectory(prefix="oink-nav-path-keys-") as temp:
                site = Path(temp)

                def write(relative: str, value: str) -> None:
                    path = site / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(value, encoding="utf-8")

                write("hugo.yaml", f"""baseURL: https://example.org{base_path}
title: Navigation path keys
theme: {ROOT.name}
defaultContentLanguage: en
defaultContentLanguageInSubdir: {str(language_subdir).lower()}
languages:
  en: {{weight: 1}}
  zh: {{weight: 2}}
disableKinds: [RSS, sitemap, taxonomy, term]
outputs:
  home: [HTML, NAVJSON]
  section: [HTML]
  page: [HTML]
""")
                write("layouts/index.html", "ok")
                write("layouts/docs/list.html", '{{ partial "section-index.html" . }}')
                write("layouts/docs/single.html", "ok")
                for suffix in ("", ".zh"):
                    write(f"content/docs/_index{suffix}.md", "---\ntitle: Docs\n---\n")
                    for weight, name in enumerate(("alpha", "beta"), 1):
                        write(f"content/docs/{name}{suffix}.md",
                              f"---\ntitle: {name}\nweight: {weight}\n---\n")
                write("data/docs_nav.json", json.dumps({
                    "sections": [{"page": "/docs", "children": [
                        {"page": "/docs/beta"}, {"page": "/docs/alpha"}]}],
                    "children_by_url": {"/docs/": ["/docs/beta", "/docs/alpha"]},
                }))
                result = subprocess.run(
                    [hugo, "--source", str(site), "--themesDir", str(ROOT.parent),
                     "--destination", str(site / "public"), "--logLevel", "warn"],
                    capture_output=True, text=True, check=False, timeout=BUILD_TIMEOUT)
                require(result.returncode == 0, f"{case}: navigation build failed: {result.stdout}{result.stderr}", errors)
                if result.returncode != 0:
                    continue
                for lang in ("en", "zh"):
                    language_path = f"{lang}/" if language_subdir or lang != "en" else ""
                    output = site / "public" / language_path
                    nav = json.loads((output / "navigation.json").read_text())
                    nodes = nav_page_nodes(nav["root"])
                    expected_ids = ["/", "/docs/", "/docs/beta/", "/docs/alpha/"]
                    require([node["id"] for node in nodes] == expected_ids,
                            f"{case}/{lang}: navigation IDs retain a language or deployment prefix: {[node['id'] for node in nodes]}", errors)
                    for node, expected_id in zip(nodes, expected_ids):
                        expected = f"https://example.org{base_path}{language_path}{expected_id.lstrip('/')}"
                        require(node["url"] == expected, f"{case}/{lang}: published URL changed: {node['url']}", errors)
                    html = (output / "docs/index.html").read_text()
                    links = re.findall(r'<a\b[^>]*href="([^"]+)"', html)
                    require(links == [f"{base_path}{language_path}docs/{name}/" for name in ("beta", "alpha")],
                            f"{case}/{lang}: section index ignored declared order: {links}", errors)


def check_nested_section(hugo: str, errors: list[str]) -> None:
    """Enabling LLMSFULL below the top level warns and blocks publication."""

    with tempfile.TemporaryDirectory(prefix="oink-agent-indexes-nested-") as temp:
        temp_path = Path(temp)
        override = temp_path / "override.yaml"
        override.write_text(
            "outputs:\n  section: [HTML, print, RSS, markdown, LLMSFULL]\n",
            encoding="utf-8",
        )
        command = [
            hugo,
            "--source", str(TEST_SITE),
            "--themesDir", str(ROOT.parent),
            "--destination", str(temp_path / "public"),
            "--config", fixture_config(override),
            "--logLevel", "warn",
        ]
        result = subprocess.run(command, capture_output=True, text=True,
                                check=False, timeout=BUILD_TIMEOUT)
        output = result.stdout + result.stderr
        expected = "LLMSFULL output requires a top-level section"
        require(expected in output,
                f"nested-section LLMSFULL did not report {expected!r}", errors)
        require(result.returncode == 0,
                "nested-section LLMSFULL stopped a plain build instead of warning",
                errors)
        nested = temp_path / "public/fixtures/guides/llms-full.txt"
        require((not nested.exists()) or nested.read_text(encoding="utf-8") == "",
                "nested-section LLMSFULL emitted content instead of nothing", errors)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    if args.public:
        public = args.public
    else:
        public, result = build_fixture_public(
            args.hugo, "--printPathWarnings")
        if result.returncode != 0:
            print(result.stdout + result.stderr, file=sys.stderr)
            raise SystemExit("regression fixture build failed")

    for rel_path, spec in BUNDLES.items():
        check_bundle(public, rel_path, spec, errors)
    check_navigation(public, errors)
    check_discovery(public, errors)
    if args.public is None:
        check_determinism(args.hugo, public, errors)
        check_explicit_tree(args.hugo, errors)
        check_explicit_boundaries(args.hugo, errors)
        check_navigation_path_keys(args.hugo, errors)
        check_nested_section(args.hugo, errors)
    else:
        print("  (reused build: determinism, explicit-tree, and "
              "nested-section cases skipped)")

    if errors:
        print("Agent index checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Agent index checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
