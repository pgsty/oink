#!/usr/bin/env python3
"""Generate the theme's configuration JSON Schemas.

The schemas under ``schema/`` are GENERATED artifacts, never edited by hand.
Their authorities are:

1. ``hugo.yaml`` -- the theme's declared defaults, with each key's comment
   block becoming its description; and
2. ``check-params.py``'s read-point scan -- the keys the templates actually
   consume, which is what keeps the schema honest about keys that carry no
   declared default; and
3. its explicit 1.x compatibility no-op list, whose keys remain accepted but
   deliberately have no template read point.

``--check`` regenerates in memory and fails when the committed files drift,
which is what keeps this a projection of the existing authorities rather than
a second configuration authority. CI runs it beside the checkers.

The ``hugo.yaml`` reader is deliberately a small parser for the shape that
file actually uses inside ``params:`` -- nested maps, scalars, and inline
lists, two-space indents. Anything it does not understand is a hard error, so
outgrowing it breaks the drift check loudly instead of mis-generating.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"
GENERATOR = "bin/generate-config-schema.py"

KEY_LINE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*?))?\s*$")

# Keys the read-point scan reports that are NOT part of the page authoring
# surface: three removed keys read only by their migration-warning resolvers,
# and one navbar menu-entry parameter the page-context regex cannot tell
# apart from front matter. Excluding them keeps editor completion from
# advertising keys that only ever warn; ``build`` asserts each entry is still
# observed so this list cannot outlive the resolvers that justify it.
FRONT_SCHEMA_EXCLUDES = {
    "release": "replaced by release_url; read only by the release/meta.html migration warning",
    "upstream_attribution": "renamed to the upstream_link companions; read only by the annotation-items.html migration warning",
    "downstream_modified": "renamed to upstream_modified; read only by the annotation-items.html migration warning",
    "columns": "navbar menu-entry parameter (navbar-item.html), not page front matter",
}


def strip_inline_comment(text: str) -> str:
    """Drop a trailing ``# comment`` that sits outside quotes.

    YAML starts an inline comment only at a ``#`` preceded by whitespace,
    which is also what keeps quoted values (``'#abc'``) and bare URL
    fragments (``.../page#anchor``) intact."""
    if text.lstrip().startswith("#"):
        raise SystemExit(f"generate-config-schema: a key with only a comment for a value is ambiguous: {text!r}")
    quote = ""
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char == "#" and index > 0 and text[index - 1] in " \t":
            return text[:index].rstrip()
    return text


def load_check_params():
    spec = importlib.util.spec_from_file_location("oink_check_params", ROOT / "bin/check-params.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load bin/check-params.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def split_items(inner: str) -> list[str]:
    """Split an inline list on its separating commas only.

    A plain ``inner.split(",")`` would cut ``['a, b', c]`` in half, and the
    drift gate could not catch it because it compares this parser against
    itself -- so the split tracks quote state, and an unterminated quote is a
    hard error rather than a silent misreading."""
    items: list[str] = []
    current = ""
    quote = ""
    for char in inner:
        if quote:
            current += char
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
            current += char
        elif char == ",":
            items.append(current)
            current = ""
        else:
            current += char
    if quote:
        raise SystemExit(f"generate-config-schema: unterminated quote in inline list: {inner!r}")
    items.append(current)
    return items


def parse_scalar(raw: str):
    """Parse the scalar subset hugo.yaml uses: booleans, numbers, quoted and
    bare strings, and inline lists of the same."""
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part) for part in split_items(inner)]
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        return text[1:-1]
    if text in ("true", "false"):
        return text == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def parse_params(lines: list[str]) -> dict:
    """Parse hugo.yaml's params: section into (value, description) trees."""
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "params:")
    tree: dict = {}
    stack: list[tuple[int, dict]] = []  # (key indent, container) per open level
    pending: tuple[int, dict] | None = None  # a just-opened map awaiting children
    comments: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            comments = []
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break  # end of the params table
        if stripped.startswith("#"):
            comments.append(stripped.lstrip("#").strip())
            continue
        match = KEY_LINE.match(line)
        if not match:
            raise SystemExit(f"generate-config-schema: unsupported hugo.yaml construct: {line.rstrip()!r}")
        if not stack:
            stack.append((indent, tree))
        elif pending is not None and indent > pending[0]:
            stack.append((indent, pending[1]))
        pending = None
        while stack and indent < stack[-1][0]:
            stack.pop()
        if not stack or indent != stack[-1][0]:
            raise SystemExit(f"generate-config-schema: unexpected indent: {line.rstrip()!r}")
        key, value = match.group(2), match.group(3)
        node = {"description": " ".join(comments)} if comments else {}
        comments = []
        stack[-1][1][key] = node
        if value is not None:
            value = strip_inline_comment(value).strip()
        if value is None or value == "":
            node["children"] = {}
            pending = (indent, node["children"])
        else:
            node["value"] = parse_scalar(value)
    return tree


def json_type(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    return "string"


def to_schema(tree: dict, path: str, kept_maps: set[str]) -> dict:
    properties = {}
    for key, node in tree.items():
        dotted = f"{path}.{key}" if path else key
        entry: dict = {}
        if node.get("description"):
            entry["description"] = node["description"]
        if "children" in node:
            entry.update(to_schema(node["children"], dotted, kept_maps))
            if dotted in kept_maps:
                # A kept map also accepts the bare-boolean shorthand.
                entry = {"type": ["boolean", "object"], **{k: v for k, v in entry.items() if k != "type"}}
        else:
            value = node["value"]
            entry["type"] = json_type(value)
            entry["default"] = value
        properties[key] = entry
    return {"type": "object", "additionalProperties": True, "properties": properties}


def lookup(tree: dict, dotted: str):
    node = None
    children = tree
    for part in dotted.split("."):
        node = children.get(part)
        if node is None:
            return None
        children = node.get("children", {})
    return node


def build(check_params) -> dict[str, str]:
    lines = (ROOT / "hugo.yaml").read_text(encoding="utf-8").splitlines()
    tree = parse_params(lines)
    site_keys, page_keys, _ = check_params.scan_read_points()

    params_schema = to_schema(tree, "", set(check_params.KEPT_MAPS))
    # Keys the templates read without a declared default still belong to the
    # authoring surface; surface them rather than pretending they don't exist.
    # Nested ones (ui.breadcrumb, plantuml.svg) matter as much as top-level
    # ones, so walk the dotted path and open each missing level on the way --
    # dropping them would leave the schema quietly incomplete, which is the
    # same failure as drifting from the authority.
    read_only_note = "Read by the theme's templates; no declared default."
    for key in sorted(k for k in site_keys if lookup(tree, k) is None):
        properties = params_schema["properties"]
        parts = key.split(".")
        for part in parts[:-1]:
            node = properties.setdefault(part, {})
            if "properties" not in node:
                node.setdefault("type", "object")
                node.setdefault("additionalProperties", True)
                node["properties"] = {}
            properties = node["properties"]
        properties.setdefault(parts[-1], {"description": read_only_note})

    for key, reason in FRONT_SCHEMA_EXCLUDES.items():
        if key not in page_keys:
            raise SystemExit(
                f"generate-config-schema: FRONT_SCHEMA_EXCLUDES entry {key!r} is no longer read anywhere; "
                f"drop it ({reason})")

    front_properties = {}
    page_schema_keys = set(page_keys) | check_params.COMPATIBILITY_NOOP_PAGE_KEYS
    for key in sorted(k for k in page_schema_keys if k not in FRONT_SCHEMA_EXCLUDES):
        entry: dict = {}
        site_node = lookup(tree, f"ui.{key}") or lookup(tree, key)
        if site_node is not None:
            if site_node.get("description"):
                entry["description"] = site_node["description"]
            # Deliberately no type: several front matter keys accept a
            # bare-boolean opt-out beside their site type (share: false,
            # theme_color: false), and a wrong squiggle is worse than none.
        if not entry:
            entry["description"] = "Front matter key read by the theme's templates."
        front_properties[key] = entry
    front_schema = {"type": "object", "additionalProperties": True, "properties": front_properties}

    stamp = f"GENERATED by {GENERATOR} from hugo.yaml and check-params.py -- do not edit"
    site_document = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$comment": stamp,
        "title": "OINK site configuration (hugo.yaml)",
        "type": "object",
        "additionalProperties": True,
        "properties": {"params": {**params_schema, "description": "OINK theme parameters."}},
    }
    front_document = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$comment": stamp,
        "title": "OINK page front matter",
        **front_schema,
    }
    return {
        "site-params.schema.json": json.dumps(site_document, indent=2, ensure_ascii=False) + "\n",
        "front-matter.schema.json": json.dumps(front_document, indent=2, ensure_ascii=False) + "\n",
    }


def verify_documents(documents: dict[str, str]) -> None:
    """Regression tripwires for the two parser defects this generator had:
    inline comments bleeding into defaults, and legacy-only read points being
    advertised as front matter. These check the OUTPUT, so they hold even if
    the parser regresses in a new way that reproduces the same symptom."""
    site = json.loads(documents["site-params.schema.json"])
    front = json.loads(documents["front-matter.schema.json"])

    def walk(node, path=""):
        if isinstance(node, dict):
            default = node.get("default")
            if isinstance(default, str) and re.search(r"\s#\s", default):
                raise SystemExit(f"generate-config-schema: default at {path} still carries an inline comment: {default!r}")
            for key, value in node.items():
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(site)
    params = site["properties"]["params"]["properties"]
    pins = (
        (("print", "toc"), bool),
        (("print", "section_break_wordcount"), int),
        (("ui", "blog_index_columns"), int),
        (("ui", "section_index_columns"), int),
    )
    for path, expected in pins:
        node = params
        for part in path[:-1]:
            node = node[part]["properties"]
        default = node[path[-1]].get("default")
        if not isinstance(default, expected) or (expected is int and isinstance(default, bool)):
            raise SystemExit(
                f"generate-config-schema: params.{'.'.join(path)} default should be {expected.__name__}, got {default!r}")

    front_keys = set(front["properties"])
    for key in FRONT_SCHEMA_EXCLUDES:
        if key in front_keys:
            raise SystemExit(f"generate-config-schema: excluded key {key!r} leaked into the front matter schema")
    if "release_url" not in front_keys:
        raise SystemExit("generate-config-schema: release_url disappeared from the front matter schema")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the committed schemas drift from the sources")
    args = parser.parse_args()
    documents = build(load_check_params())
    verify_documents(documents)
    if args.check:
        drift = []
        for name, body in documents.items():
            path = SCHEMA_DIR / name
            if not path.is_file():
                drift.append(f"{path} is missing")
            elif path.read_text(encoding="utf-8") != body:
                drift.append(f"{path} is stale")
        if drift:
            print("Config schema drift (regenerate with python3 " + GENERATOR + "):")
            for item in drift:
                print(f"  {item}")
            return 1
        print(f"Config schemas match their sources ({len(documents)} files)")
        return 0
    SCHEMA_DIR.mkdir(exist_ok=True)
    for name, body in documents.items():
        (SCHEMA_DIR / name).write_text(body, encoding="utf-8")
        print(f"wrote schema/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
