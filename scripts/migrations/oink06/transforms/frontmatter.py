"""frontmatter: the 1.0 front matter key renames (YAML front matter only).

Rewrites, inside the ``---`` delimited block only (the body is never touched):

1. ``manualLink*``           -> ``manual_link``/``manual_link_title``/``manual_link_target``/``manual_link_relref``
2. ``context_menu``         -> ``page_context_menu``
3. ``hide_readingtime: X``  -> ``reading_time: not X``
4. ``hide_feedback: true``  -> ``feedback: false`` (``false`` just goes away)
5. ``exclude_search`` / ``excludeSearch`` -> ``search_exclude`` (merged, OR of true)
6. ``content_width: norm``  -> ``reading_width: normal`` (``slim``/``wide`` keep their value)
7. a page ``ui:`` map (top level or under ``params:``) is lifted to the top
   level — a page override is the site key without its ``ui.`` prefix — with
   ``image_zoom``/``keyboard_nav``/``annotation``/``typography`` maps collapsed
   to their scalar and ``ui.pager`` dropped (site-only)
8. ``annotation: {enable: X}`` -> ``annotation: X``
9. ``assistant_links: X``   -> merged into the ``page_context_menu`` map
10. the same rules inside ``cascade:`` (map or list of maps), where the ``ui.*``
    children land under the cascade item's ``params:`` map (Hugo >= 0.123)

TOML (``+++``) and JSON front matter are never rewritten; a file whose
non-YAML front matter mentions a legacy key gets one finding instead.

The YAML walk is deliberately small and conservative: indentation-aware key
lines, opaque blocks, and a finding for anything it will not touch (anchors,
block scalars, flow shapes it cannot parse, keys that already exist).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from ..base import Result, Transformation
from ..scanner import Document

INDENT = "  "

KEY_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)[ \t]*:(?P<rest>[ \t].*|)$")
DASH_RE = re.compile(r"^(?P<indent>[ \t]*)-(?P<gap>[ \t]*)(?P<rest>.*)$")
UNSAFE_YAML_RE = re.compile(r":[ \t]*[&*]|^[ \t]*<<[ \t]*:|^[ \t]*[&*]")
BLOCK_SCALAR_RE = re.compile(r":[ \t]*[|>][-+0-9]*[ \t]*(#.*)?$")

MANUAL_LINKS = {
    "manuallink": "manual_link",
    "manuallinktitle": "manual_link_title",
    "manuallinktarget": "manual_link_target",
    "manuallinkrelref": "manual_link_relref",
}
SEARCH_KEYS = ("exclude_search", "excludesearch", "search_exclude")
WIDTHS = {"norm": "normal", "normal": "normal", "slim": "slim", "wide": "wide"}
ENABLE_KEYS = {"image_zoom", "keyboard_nav", "annotation"}
LEGACY_KEYS = (
    "context_menu",
    "hide_readingtime",
    "hide_feedback",
    "exclude_search",
    "excludesearch",
    "content_width",
    "assistant_links",
)
NON_YAML_MARKERS = tuple(sorted(set(LEGACY_KEYS) | set(MANUAL_LINKS)))
NON_YAML_UI_RE = re.compile(r"^[ \t]*\[[^\]]*\bui\]|\bui[ \t]*=[ \t]*\{|\"ui\"[ \t]*:", re.M | re.I)


# --------------------------------------------------------------------- helpers
def indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def split_comment(rest: str) -> tuple[str, str]:
    """Split ``value  # comment`` honouring quotes (the gap stays with the comment)."""

    quote = None
    for index, char in enumerate(rest):
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
            continue
        if char == "#" and (index == 0 or rest[index - 1] in " \t"):
            start = index
            while start > 0 and rest[start - 1] in " \t":
                start -= 1
            return rest[:start], rest[start:]
    return rest, ""


def split_top(text: str, sep: str) -> list[str] | None:
    """Split on ``sep`` at brace/bracket depth 0, outside quotes."""

    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quote = None
    for char in text:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
            current.append(char)
            continue
        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth < 0:
                return None
        if char == sep and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if depth or quote:
        return None
    parts.append("".join(current))
    return parts


def parse_flow_map(text: str) -> dict[str, str] | None:
    """``{a: 1, b: {c: d}}`` -> ordered dict of raw value text (None when unsure)."""

    text = text.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    inner = text[1:-1].strip()
    if not inner:
        return {}
    parts = split_top(inner, ",")
    if parts is None:
        return None
    out: dict[str, str] = {}
    for part in parts:
        part = part.strip()
        if not part:
            continue
        pieces = split_top(part, ":")
        if pieces is None or len(pieces) < 2:
            return None
        key = pieces[0].strip().strip("\"'")
        value = ":".join(pieces[1:]).strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", key) or key in out:
            return None
        out[key] = value
    return out


def boolean(value: str) -> str | None:
    lowered = value.strip().lower()
    if lowered in ("true", "yes", "on"):
        return "true"
    if lowered in ("false", "no", "off"):
        return "false"
    return None


def block_end(lines: list[str], start: int, width: int) -> int:
    """Last line index of the block owned by the key line at ``start``."""

    last = start
    index = start + 1
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        current = len(indent_of(line))
        if current > width or (current == width and re.match(r"-([ \t]|$)", line.lstrip())):
            last = index
            index += 1
            continue
        break
    return last


@dataclass(eq=False)
class Raw:
    """A line at a map level that is not a key line (blank, comment, unknown)."""

    lines: list[str]

    def lines_out(self) -> list[str]:
        return list(self.lines)


@dataclass(eq=False)
class Item:
    """One ``key: value`` mapping entry plus the block it owns."""

    key: str
    indent: str
    line: str
    rest: str
    value: str
    comment: str
    block: list[str]
    abs_line: int
    new_key: str | None = None
    new_value: str | None = None
    new_block: list[str] | None = None
    dropped: bool = False

    @property
    def norm(self) -> str:
        return (self.new_key if self.new_key is not None else self.key).strip().lower()

    @property
    def out_value(self) -> str:
        return self.value if self.new_value is None else self.new_value

    @property
    def out_block(self) -> list[str]:
        return self.block if self.new_block is None else self.new_block

    def lines_out(self) -> list[str]:
        if self.dropped:
            return []
        if self.new_key is None and self.new_value is None:
            head = self.line
        else:
            key = self.new_key if self.new_key is not None else self.key
            value = self.out_value
            head = self.indent + key + ":" + ((" " + value) if value else "") + self.comment
        return [head] + list(self.out_block)


def make_item(indent: str, key: str, value: str = "", block: list[str] | None = None, abs_line: int = 0) -> Item:
    rest = (" " + value) if value else ""
    return Item(
        key=key,
        indent=indent,
        line=indent + key + ":" + rest,
        rest=rest,
        value=value,
        comment="",
        block=list(block or []),
        abs_line=abs_line,
    )


@dataclass(eq=False)
class Level:
    """One mapping level: ordered items plus the raw lines between them."""

    nodes: list = field(default_factory=list)
    indent: str = ""
    safe: bool = True

    def items(self) -> list[Item]:
        return [node for node in self.nodes if isinstance(node, Item) and not node.dropped]

    def one(self, name: str) -> Item | None:
        lowered = name.lower()
        for item in self.items():
            if item.norm == lowered:
                return item
        return None

    def render(self) -> list[str]:
        out: list[str] = []
        for node in self.nodes:
            out.extend(node.lines_out())
        return out

    def empty(self) -> bool:
        if self.items():
            return False
        return not any(line.strip() for node in self.nodes if isinstance(node, Raw) for line in node.lines)

    def insert_after(self, anchor: Item | None, nodes: list) -> None:
        if anchor is None or anchor not in self.nodes:
            self.nodes.extend(nodes)
            return
        index = self.nodes.index(anchor)
        self.nodes[index + 1 : index + 1] = nodes

    def replace(self, node, nodes: list) -> None:
        index = self.nodes.index(node)
        self.nodes[index : index + 1] = nodes


def parse_level(lines: list[str], abs_offset: int) -> Level:
    """Split ``lines`` into the mapping entries of one indentation level."""

    level = Level()
    base: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.strip().startswith("#"):
            level.nodes.append(Raw([line]))
            index += 1
            continue
        match = KEY_RE.match(line)
        if match is None or (base is not None and match.group("indent") != base):
            level.nodes.append(Raw([line]))
            level.safe = False
            index += 1
            continue
        if base is None:
            base = match.group("indent")
            level.indent = base
        rest = match.group("rest")
        value, comment = split_comment(rest)
        end = block_end(lines, index, len(match.group("indent")))
        level.nodes.append(
            Item(
                key=match.group("key"),
                indent=match.group("indent"),
                line=line,
                rest=rest,
                value=value.strip(),
                comment=comment,
                block=lines[index + 1 : end + 1],
                abs_line=abs_offset + index,
            )
        )
        index = end + 1
    return level


# ---------------------------------------------------------------- the transform
class FrontMatterTransformation(Transformation):
    key = "frontmatter"
    description = "1.0 front matter keys: manual_link*, page_context_menu, reading_time, feedback, search_exclude, reading_width, ui.* lifted to the top level"
    residual_patterns = (
        r"^[ \t]*[Mm]anual[Ll]ink(?:[Tt]itle|[Tt]arget|[Rr]elref)?[ \t]*:",
        r"^[ \t]*context_menu[ \t]*:",
        r"^[ \t]*hide_readingtime[ \t]*:",
        r"^[ \t]*hide_feedback[ \t]*:",
        r"^[ \t]*(?:exclude_search|excludeSearch)[ \t]*:",
        r"^[ \t]*content_width[ \t]*:",
        r"^[ \t]*ui:[ \t]*$",
    )

    def __init__(self) -> None:
        # Findings survive the base class' fixed-point loop: a rule that *removes*
        # a key would otherwise lose its finding on the next (stable) pass.
        self._sticky: list[tuple[str, int, str, str]] = []

    def _report(self, result: Result, path: str, line: int, reason: str, source: str = "") -> None:
        source = source[:200]
        for known in self._sticky:  # line numbers shift between passes; keep the first
            if (known[0], known[2], known[3]) == (path, reason, source):
                return
        self._sticky.append((path, line, reason, source))
        self.note(result, path, line, self.key, reason, source)

    # -- check -----------------------------------------------------------------
    def residual_findings(self, doc: Document):
        """Legacy front matter keys `check` should still flag (front matter only)."""

        end = doc.front_matter_end
        if end <= 0:
            return
        first = doc.lines[0].strip()
        if first != "---":
            for line, reason in self._non_yaml_finding(doc, end):
                yield line, reason, doc.lines[line]
            return
        stack: list[tuple[int, str]] = []
        for index in range(1, end - 1):
            line = doc.lines[index]
            match = KEY_RE.match(line)
            width = len(indent_of(line))
            if match is None:
                dash = DASH_RE.match(line)
                if dash is None or not dash.group("rest").strip():
                    continue
                width = len(dash.group("indent")) + 1 + len(dash.group("gap"))
                match = KEY_RE.match(" " * width + dash.group("rest"))
                if match is None:
                    continue
            while stack and stack[-1][0] >= width:
                stack.pop()
            parent = stack[-1][1] if stack else ""
            key = match.group("key")
            norm = key.lower()
            if parent in ("", "params", "cascade"):
                if norm in MANUAL_LINKS:
                    yield index, f"legacy front matter key {key} (use {MANUAL_LINKS[norm]})", line.strip()
                elif norm in LEGACY_KEYS:
                    yield index, f"legacy front matter key {key}", line.strip()
                elif norm == "ui":
                    yield index, "front matter ui: map (page overrides are top-level keys)", line.strip()
            stack.append((width, norm))

    def _non_yaml_finding(self, doc: Document, end: int) -> list[tuple[int, str]]:
        text = "\n".join(doc.lines[:end])
        lowered = text.lower()
        if any(marker in lowered for marker in NON_YAML_MARKERS) or NON_YAML_UI_RE.search(text):
            return [(0, "TOML/JSON front matter is not migrated automatically")]
        return []

    # -- migrate ---------------------------------------------------------------
    def _apply(self, path: str, doc: Document, result: Result) -> None:
        for sticky_path, line, reason, source in self._sticky:
            self.note(result, sticky_path, line, self.key, reason, source)
        end = doc.front_matter_end
        if end <= 0:
            return
        if doc.lines[0].strip() != "---":
            for line, reason in self._non_yaml_finding(doc, end):
                self._report(result, path, line, reason, doc.lines[line])
            return
        body = doc.lines[1 : end - 1]
        level = parse_level(body, 1)
        self._page(path, result, level)
        new_body = level.render()
        if new_body != body:
            doc.lines[1 : end - 1] = new_body
            doc.rescan()
            result.text = doc.render()

    def _page(self, path: str, result: Result, level: Level) -> None:
        ui = level.one("ui")
        if ui is not None:
            self._lift(path, result, ui, level, anchor=ui)
        params = level.one("params")
        if params is not None:
            self._page_params(path, result, params, level)
        cascade = level.one("cascade")
        if cascade is not None:
            self._cascade(path, result, cascade)
        self._simple(path, result, level)

    def _page_params(self, path: str, result: Result, params: Item, level: Level) -> None:
        """A page ``params:`` map: its ``ui:`` children lift to the top level."""

        sub, flow = self._sub_level(path, result, params)
        if sub is None:
            return
        before = sub.render()
        sub_ui = sub.one("ui")
        if sub_ui is not None:
            self._lift(path, result, sub_ui, level, anchor=params)
        self._simple(path, result, sub)
        self._write_back(params, sub, before, flow)

    def _write_back(self, item: Item, sub: Level, before: list[str], flow: bool) -> None:
        after = sub.render()
        if after == before:
            if flow:
                item.new_value = None
                item.new_block = None
            return
        if sub.empty():
            item.dropped = True
            return
        item.new_block = after

    def _sub_level(self, path: str, result: Result, item: Item) -> tuple[Level | None, bool]:
        """Parse ``item``'s map value; flow maps are expanded to block form."""

        if item.block:
            if item.value:
                self._report(result, path, item.abs_line, f"{item.key}: has both an inline value and a block", item.line.strip())
                return None, False
            level = parse_level(item.block, item.abs_line + 1)
            if not level.safe:
                self._report(result, path, item.abs_line, f"{item.key}: block is not a plain mapping — migrate it by hand", item.line.strip())
                return None, False
            return level, False
        if item.value.startswith("{"):
            mapping = parse_flow_map(item.value)
            if mapping is None:
                self._report(result, path, item.abs_line, f"{item.key}: flow mapping could not be parsed — migrate it by hand", item.line.strip())
                return None, False
            lines = [item.indent + INDENT + key + ": " + value for key, value in mapping.items()]
            item.new_value = ""
            return parse_level(lines, item.abs_line), True
        return None, False

    # -- rule 7 / 10: lifting a ui: map ----------------------------------------
    def _lift(self, path: str, result: Result, ui: Item, target: Level, anchor: Item | None) -> bool:
        source_lines = ui.block if ui.block else []
        for line in source_lines:
            if UNSAFE_YAML_RE.search(line) or BLOCK_SCALAR_RE.search(line):
                self._report(result, path, ui.abs_line, "ui: block uses YAML this migration will not lift (anchor or block scalar)", line.strip())
                return False
        if not ui.block and not ui.value:
            ui.dropped = True  # an empty ui: map
            result.counts["frontmatter.dropped"] += 1
            return True
        sub, _flow = self._sub_level(path, result, ui)
        if sub is None:
            return False
        indent = target.indent
        lines: list[str] = []
        for node in sub.nodes:
            for line in node.lines_out():
                if not line.strip():
                    lines.append("")
                    continue
                if not line.startswith(sub.indent):
                    self._report(result, path, ui.abs_line, "ui: children are not indented consistently — lift them by hand", line.strip())
                    return False
                lines.append(indent + line[len(sub.indent) :])
        lifted = parse_level(lines, ui.abs_line)
        if not lifted.safe:
            self._report(result, path, ui.abs_line, "ui: block is not a plain mapping — lift it by hand", ui.line.strip())
            return False
        if not lifted.items():  # an empty ui: map just goes away
            result.counts["frontmatter.dropped"] += 1
        keep: list = []
        for node in lifted.nodes:
            if isinstance(node, Raw):
                keep.append(node)
                continue
            if not self._adjust_lifted(path, result, node):
                continue
            existing = target.one(node.norm)
            if existing is not None:
                same = [line.strip() for line in existing.lines_out()] == [line.strip() for line in node.lines_out()]
                if not same:
                    self._report(result, path, node.abs_line, f"ui.{node.key} conflicts with the existing top-level {existing.key} — kept the existing value",
                        node.lines_out()[0].strip(),
                    )
                result.counts["frontmatter.dropped"] += 1
                continue
            keep.append(node)
            result.counts["frontmatter.ui_lift"] += 1
        ui.dropped = True
        target.insert_after(anchor, keep)
        return True

    def _adjust_lifted(self, path: str, result: Result, item: Item) -> bool:
        norm = item.norm
        if norm == "pager":
            self._report(result, path, item.abs_line, "site-only key ui.pager.types in front matter — set it in the site config", item.lines_out()[0].strip())
            result.counts["frontmatter.dropped"] += 1
            return False
        if norm in ENABLE_KEYS:
            self._collapse(path, result, item, "enable", "frontmatter.ui_enable")
        elif norm == "typography":
            self._collapse(path, result, item, "preset", "frontmatter.ui_enable")
        return True

    def _map_of(self, item: Item) -> dict[str, str] | None:
        """The item's value as a flat one-level mapping, or None."""

        if item.out_block and not item.out_value:
            level = parse_level(item.out_block, item.abs_line + 1)
            if not level.safe:
                return None
            mapping: dict[str, str] = {}
            for node in level.nodes:
                if isinstance(node, Raw):
                    if any(line.strip() for line in node.lines):
                        return None
                    continue
                if node.block or not node.value:
                    return None
                mapping[node.norm] = node.value
            return mapping
        if item.out_value.startswith("{"):
            mapping = parse_flow_map(item.out_value)
            if mapping is None:
                return None
            return {key.lower(): value for key, value in mapping.items()}
        return None

    def _collapse(self, path: str, result: Result, item: Item, child: str, count_key: str) -> bool:
        mapping = self._map_of(item)
        if mapping is None:
            return False
        if set(mapping) != {child} or not mapping[child].strip():
            self._report(result, path, item.abs_line, f"{item.key}: is a map with keys other than {child} — set the page override by hand", item.lines_out()[0].strip())
            return False
        item.new_value = mapping[child]
        item.new_block = []
        result.counts[count_key] += 1
        return True

    # -- rule 10: cascade ------------------------------------------------------
    def _cascade(self, path: str, result: Result, item: Item) -> None:
        if not item.block:
            if item.value:
                self._report(result, path, item.abs_line, "cascade: is not a block mapping/list — migrate it by hand", item.line.strip())
            return
        block = item.block
        first = next((line for line in block if line.strip()), "")
        if re.match(r"-([ \t]|$)", first.lstrip()):
            new_block = self._cascade_list(path, result, block, item.abs_line + 1)
        else:
            level = parse_level(block, item.abs_line + 1)
            if not level.safe:
                self._report(result, path, item.abs_line, "cascade: block is not a plain mapping — migrate it by hand", item.line.strip())
                return
            self._cascade_item(path, result, level)
            new_block = level.render()
        if new_block != block:
            item.new_block = new_block

    def _cascade_list(self, path: str, result: Result, block: list[str], abs_offset: int) -> list[str]:
        dash_indent = None
        for line in block:
            if line.strip():
                dash_indent = len(indent_of(line))
                break
        out: list[str] = []
        chunk: list[str] = []
        chunk_start = 0
        head: list[str] = []
        started = False
        for index, line in enumerate(block):
            is_dash = bool(line.strip()) and len(indent_of(line)) == dash_indent and re.match(r"-([ \t]|$)", line.lstrip())
            if is_dash:
                if started:
                    out.extend(self._cascade_chunk(path, result, chunk, abs_offset + chunk_start))
                else:
                    out.extend(head)
                    started = True
                chunk = [line]
                chunk_start = index
                continue
            if started:
                chunk.append(line)
            else:
                head.append(line)
        if started:
            out.extend(self._cascade_chunk(path, result, chunk, abs_offset + chunk_start))
        else:
            out.extend(head)
        return out

    def _cascade_chunk(self, path: str, result: Result, chunk: list[str], abs_offset: int) -> list[str]:
        match = DASH_RE.match(chunk[0])
        if match is None:  # pragma: no cover - chunks always start with a dash
            return chunk
        inline = match.group("rest")
        if inline.strip().startswith("{"):
            self._report(result, path, abs_offset, "cascade list item is a flow mapping — migrate it by hand", chunk[0].strip())
            return chunk
        if not inline.strip():
            level = parse_level(chunk[1:], abs_offset + 1)
            if not level.safe:
                self._report(result, path, abs_offset, "cascade list item is not a plain mapping — migrate it by hand", chunk[0].strip())
                return chunk
            self._cascade_item(path, result, level)
            return [chunk[0]] + level.render()
        dash_col = len(match.group("indent"))
        width = dash_col + 1 + len(match.group("gap"))
        converted = [" " * width + inline] + chunk[1:]
        level = parse_level(converted, abs_offset)
        if not level.safe:
            self._report(result, path, abs_offset, "cascade list item is not a plain mapping — migrate it by hand", chunk[0].strip())
            return chunk
        self._cascade_item(path, result, level)
        rendered = level.render()
        first = next((index for index, line in enumerate(rendered) if line.strip()), None)
        if first is None or len(indent_of(rendered[first])) <= dash_col:
            self._report(result, path, abs_offset, "cascade list item became empty — migrate it by hand", chunk[0].strip())
            return chunk
        line = rendered[first]
        rendered[first] = line[:dash_col] + "-" + line[dash_col + 1 :]
        return rendered

    def _cascade_item(self, path: str, result: Result, level: Level) -> None:
        """One cascade map: ``ui.*`` children land under the item's ``params:``."""

        params = level.one("params")
        sub: Level | None = None
        flow = False
        before: list[str] = []
        created = False
        if params is not None:
            sub, flow = self._sub_level(path, result, params)
            if sub is not None:
                before = sub.render()
        ui = level.one("ui")
        if ui is not None:
            if params is not None and sub is None:
                self._report(result, path, ui.abs_line, "cascade params: could not be parsed — lift ui: by hand", ui.line.strip())
            elif sub is None:
                fresh = Level(nodes=[], indent=level.indent + INDENT)
                if self._lift(path, result, ui, fresh, anchor=None):
                    params = make_item(level.indent, "params", abs_line=ui.abs_line)
                    level.replace(ui, [params])
                    sub = fresh
                    before = []
                    created = True
            else:
                self._lift(path, result, ui, sub, anchor=None)
        if sub is not None and params is not None:
            sub_ui = sub.one("ui")
            if sub_ui is not None:
                self._lift(path, result, sub_ui, sub, anchor=sub_ui)
            self._simple(path, result, sub)
            if created:
                if sub.empty():
                    params.dropped = True
                else:
                    params.new_block = sub.render()
            else:
                self._write_back(params, sub, before, flow)
        self._simple(path, result, level)

    # -- rules 1-6, 8, 9 -------------------------------------------------------
    def _simple(self, path: str, result: Result, level: Level) -> None:
        self._rule_manual_link(path, result, level)
        self._rule_context_menu(path, result, level)
        self._rule_reading_time(path, result, level)
        self._rule_feedback(path, result, level)
        self._rule_search_exclude(path, result, level)
        self._rule_reading_width(path, result, level)
        self._rule_annotation(path, result, level)
        self._rule_assistant_links(path, result, level)

    def _drop(self, path: str, result: Result, item: Item, reason: str) -> None:
        item.dropped = True
        result.counts["frontmatter.dropped"] += 1
        self._report(result, path, item.abs_line, reason, item.line.strip())

    def _rule_manual_link(self, path: str, result: Result, level: Level) -> None:
        for item in level.items():
            target = MANUAL_LINKS.get(item.norm)
            if not target:
                continue
            if level.one(target) is not None:
                self._drop(path, result, item, f"{item.key} dropped; {target} is already set")
                continue
            item.new_key = target
            result.counts["frontmatter.manual_link"] += 1

    def _rule_context_menu(self, path: str, result: Result, level: Level) -> None:
        for item in level.items():
            if item.norm != "context_menu":
                continue
            if level.one("page_context_menu") is not None:
                self._drop(path, result, item, "context_menu dropped; page_context_menu is already set")
                continue
            item.new_key = "page_context_menu"
            result.counts["frontmatter.page_context_menu"] += 1

    def _rule_reading_time(self, path: str, result: Result, level: Level) -> None:
        for item in level.items():
            if item.norm != "hide_readingtime":
                continue
            if level.one("reading_time") is not None:
                self._drop(path, result, item, "hide_readingtime dropped; reading_time is already set")
                continue
            flag = boolean(item.value) if not item.block else None
            if flag is None:
                self._report(result, path, item.abs_line, "hide_readingtime is not a boolean — set reading_time by hand", item.line.strip())
                continue
            item.new_key = "reading_time"
            item.new_value = "false" if flag == "true" else "true"
            result.counts["frontmatter.reading_time"] += 1

    def _rule_feedback(self, path: str, result: Result, level: Level) -> None:
        for item in level.items():
            if item.norm != "hide_feedback":
                continue
            if level.one("feedback") is not None:
                self._drop(path, result, item, "hide_feedback dropped; feedback already set")
                continue
            flag = boolean(item.value) if not item.block else None
            if flag is None:
                self._report(result, path, item.abs_line, "hide_feedback is not a boolean — set feedback by hand", item.line.strip())
                continue
            if flag == "false":
                item.dropped = True
            else:
                item.new_key = "feedback"
                item.new_value = "false"
            result.counts["frontmatter.feedback"] += 1

    def _rule_search_exclude(self, path: str, result: Result, level: Level) -> None:
        group = [item for item in level.items() if item.norm in SEARCH_KEYS]
        if not group or (len(group) == 1 and group[0].norm == "search_exclude"):
            return
        keep = group[0]
        value = None
        if len(group) > 1:
            values = [boolean(item.value) if not item.block else None for item in group]
            if any(flag is None for flag in values):
                self._report(result, path, keep.abs_line, "search exclusion values are not all booleans — set search_exclude by hand", keep.line.strip())
            else:
                value = "true" if "true" in values else "false"
        for item in group[1:]:
            item.dropped = True
            result.counts["frontmatter.dropped"] += 1
            self._report(result, path, item.abs_line, f"{item.key} merged into search_exclude", item.line.strip())
        if keep.norm != "search_exclude":
            keep.new_key = "search_exclude"
        if value is not None and value != boolean(keep.value):
            keep.new_value = value
        result.counts["frontmatter.search_exclude"] += 1

    def _rule_reading_width(self, path: str, result: Result, level: Level) -> None:
        for item in level.items():
            if item.norm != "content_width":
                continue
            if level.one("reading_width") is not None:
                self._drop(path, result, item, "content_width dropped; reading_width is already set")
                continue
            item.new_key = "reading_width"
            width = WIDTHS.get(item.value.strip().strip("\"'").lower())
            if width is None:
                self._report(result, path, item.abs_line, "content_width value is not norm/slim/wide — check reading_width by hand", item.line.strip())
            elif width != item.value.strip():
                item.new_value = width
            result.counts["frontmatter.reading_width"] += 1

    def _rule_annotation(self, path: str, result: Result, level: Level) -> None:
        for item in level.items():
            if item.norm != "annotation":
                continue
            if self._map_of(item) is None:
                continue
            self._collapse(path, result, item, "enable", "frontmatter.annotation")

    def _rule_assistant_links(self, path: str, result: Result, level: Level) -> None:
        item = level.one("assistant_links")
        if item is None:
            return
        if item.block or not item.value:
            self._report(result, path, item.abs_line, "assistant_links is not a scalar — merge it into page_context_menu by hand", item.line.strip())
            return
        value = item.value
        menu = level.one("page_context_menu")
        if menu is None:
            replacement = make_item(
                level.indent,
                "page_context_menu",
                block=[level.indent + INDENT + "assistant_links: " + value],
                abs_line=item.abs_line,
            )
            level.replace(item, [replacement])
            result.counts["frontmatter.assistant_links"] += 1
            return
        flag = boolean(menu.out_value) if not menu.out_block else None
        if flag is not None:
            menu.new_value = ""
            menu.new_block = [
                menu.indent + INDENT + "enable: " + flag,
                menu.indent + INDENT + "assistant_links: " + value,
            ]
            item.dropped = True
            result.counts["frontmatter.assistant_links"] += 1
            return
        mapping = self._map_of(menu)
        if mapping is None:
            self._report(result, path, menu.abs_line, "page_context_menu is neither a boolean nor a plain map — merge assistant_links by hand", menu.line.strip())
            return
        if "assistant_links" in mapping:
            self._report(result, path, item.abs_line, "assistant_links is already set inside page_context_menu", item.line.strip())
            return
        if menu.out_block:
            block = list(menu.out_block)
            child_indent = next((indent_of(line) for line in block if line.strip()), menu.indent + INDENT)
            last = max((index for index, line in enumerate(block) if line.strip()), default=-1)
            block.insert(last + 1, child_indent + "assistant_links: " + value)
            menu.new_block = block
        else:
            menu.new_value = ""
            menu.new_block = [menu.indent + INDENT + key + ": " + text for key, text in mapping.items()]
            menu.new_block.append(menu.indent + INDENT + "assistant_links: " + value)
        item.dropped = True
        result.counts["frontmatter.assistant_links"] += 1
