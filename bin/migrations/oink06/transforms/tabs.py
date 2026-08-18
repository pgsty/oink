"""tabpane/tab and code-group/code-tab -> adjacent fences or {{< tabs >}}/{{< tab >}}.

Classification per tabpane (reported):

* ``code_only`` – every tab is exactly one fenced block (or a raw-code tab
  with ``lang``): emitted as adjacent fences carrying
  ``{tab="Header" group="G" value="V"}``.
* ``prose`` – anything else: emitted as the full ``{{< tabs >}}`` form
  (sub-classified as prose_simple / headings / shortcodes for the report).
  Angle-bracket containers are placeholder-substituted by Hugo, so they may
  sit inside list items; the theme dedents tab bodies (``.InnerDeindent``).
"""

from __future__ import annotations

import hashlib
import re

from ..base import Result, Transformation, dedent_lines, ensure_blank_around, quote_attr_value, slugify, strip_blank_edges
from ..scanner import FENCE_OPEN_RE, Document, Tag, quote

MAX_GROUP_LEN = 48
HEADING_RE = re.compile(r"^\s*#{1,6}\s|\{#[A-Za-z]")


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() == "true"


def make_group(values: list[str]) -> str:
    joined = "-".join(values)
    if len(joined) > MAX_GROUP_LEN:
        return "tabs-" + hashlib.sha1(joined.encode("utf-8")).hexdigest()[:8]
    if not re.match(r"[a-z]", joined):
        joined = "g-" + joined
    return joined


def unique_values(headers: list[str]) -> list[str]:
    values: list[str] = []
    for index, header in enumerate(headers):
        value = slugify(header) or f"tab{index + 1}"
        base = value
        suffix = 2
        while value in values:
            value = f"{base}-{suffix}"
            suffix += 1
        values.append(value)
    return values


def split_info(info: str) -> tuple[str, str] | None:
    """Split a fence info string into (language, attribute body without braces).

    Returns None when the info string has a shape the merge cannot handle.
    """

    info = info.strip()
    if not info:
        return "", ""
    if "{" not in info:
        if len(info.split()) > 1:
            return None
        return info, ""
    brace = info.index("{")
    lang = info[:brace].strip()
    rest = info[brace:]
    if not rest.endswith("}") or rest.count("{") != 1:
        return None
    if len(lang.split()) > 1:
        return None
    return lang, rest[1:-1].strip()


def merge_info(lang: str, attrs: str, extra: list[tuple[str, str]]) -> str:
    rendered = " ".join(f'{key}={quote_attr_value(value)}' for key, value in extra)
    body = (attrs + " " + rendered).strip() if attrs else rendered
    language = lang or "text"
    return f"{language} {{{body}}}"


class _Tab:
    def __init__(self, header: str, open_tag: Tag):
        self.header = header
        self.open_tag = open_tag
        self.close_tag: Tag | None = None
        self.body: list[str] = []
        self.selected = False
        self.disabled = False
        self.text: bool | None = None
        self.lang = ""
        self.highlight = ""
        self.right = False


class TabsTransformation(Transformation):
    key = "tabs"
    description = "tabpane/tab + code-group/code-tab -> adjacent fences {tab=} or {{< tabs >}}"
    residual_patterns = (
        r"\{\{[<%]\s*/?tabpane\b",
        r"\{\{<\s*/?code-(?:group|tab)\b",
        r"\{\{%\s*/?tabs?\b",  # % delimiter is the withdrawn v5 form; tabs/tab are angle-bracket containers
    )

    def residual_findings(self, doc: Document):  # used by `check`
        for tag in doc.iter_tags({"tab"}):
            if not tag.closing and tag.delim == "<" and not tag.has("label"):
                yield tag.line, "legacy tab (no label=)", tag.raw

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        if self._apply_tabpanes(path, doc, result):
            result.text = doc.render()
            return
        if self._apply_code_groups(path, doc, result):
            result.text = doc.render()

    # ------------------------------------------------------------------ tabpane
    def _apply_tabpanes(self, path: str, doc: Document, result: Result) -> bool:
        opens = [tag for tag in doc.iter_tags({"tabpane"}) if not tag.closing]
        if not opens:
            return False
        blocks = []
        for open_tag in opens:
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed tabpane", open_tag.raw)
                continue
            blocks.append((open_tag, close_tag))
        innermost = [
            (o, c)
            for o, c in blocks
            if not any((o2.line, o2.start) > (o.line, o.start) and (c2.line, c2.start) < (c.line, c.start) for o2, c2 in blocks if o2 is not o)
        ]
        changed = False
        for open_tag, close_tag in sorted(innermost, key=lambda pair: pair[0].line, reverse=True):
            if self._convert_tabpane(path, doc, result, open_tag, close_tag):
                changed = True
        return changed

    def _parse_tabs(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> list[_Tab] | None:
        lines = doc.lines
        tabs: list[_Tab] = []
        current: _Tab | None = None
        # tags strictly inside the pane, in order
        inner_tags = [t for t in doc.iter_tags({"tab"}) if (open_tag.line, open_tag.start) < (t.line, t.start) < (close_tag.line, close_tag.start)]
        index = 0
        while index < len(inner_tags):
            tag = inner_tags[index]
            if tag.closing:
                self.note(result, path, tag.line, self.key, "stray closing tab", tag.raw)
                return None
            header = tag.get("header")
            if header is None:
                positional = tag.positional()
                header = positional[0] if positional else f"Tab {len(tabs) + 1}"
            tab = _Tab(header.strip(), tag)
            tab.selected = _bool(tag.get("selected"))
            tab.disabled = _bool(tag.get("disabled"))
            tab.right = _bool(tag.get("right"))
            if tag.has("text"):
                tab.text = _bool(tag.get("text"))
            tab.lang = (tag.get("lang") or "").strip()
            tab.highlight = (tag.get("highlight") or "").strip()
            unknown = [p.name for p in tag.params if p.name not in {"header", "selected", "disabled", "right", "text", "lang", "highlight"} and p.name is not None]
            if unknown:
                self.note(result, path, tag.line, self.key, f"unsupported tab parameters {unknown}", tag.raw)
                return None
            if tag.self_closing:
                tabs.append(tab)
                index += 1
                following = inner_tags[index] if index < len(inner_tags) else close_tag
                trailing = lines[tag.line][tag.end : following.start] if following.line == tag.line else lines[tag.line][tag.end :]
                if trailing.strip():
                    self.note(result, path, tag.line, self.key, "text after self-closing tab tag", lines[tag.line])
                    return None
                continue
            close = doc.find_close(tag)
            if close is None or (close.line, close.start) > (close_tag.line, close_tag.start):
                self.note(result, path, tag.line, self.key, "unclosed tab", tag.raw)
                return None
            tab.close_tag = close
            open_line = lines[tag.line]
            body: list[str] = []
            if tag.line == close.line:
                between = open_line[tag.end : close.start]
                if between.strip():
                    body.append(between)
            else:
                rest = open_line[tag.end :]
                if rest.strip():
                    body.append(rest.strip())
                body.extend(lines[tag.line + 1 : close.line])
                head = lines[close.line][: close.start]
                if head.strip():
                    body.append(head)
            tab.body = body
            tabs.append(tab)
            # skip inner tags that belong to this tab body (none should be `tab`)
            index += 1
            while index < len(inner_tags) and (inner_tags[index].line, inner_tags[index].start) <= (close.line, close.start):
                index += 1
            # only whitespace may follow the closing tag (up to the next tab tag on the same line)
            following = inner_tags[index] if index < len(inner_tags) else close_tag
            trailing = lines[close.line][close.end : following.start] if following.line == close.line else lines[close.line][close.end :]
            if trailing.strip():
                self.note(result, path, close.line, self.key, "text after closing tab tag", lines[close.line])
                return None
        # content between tabs (outside tab bodies) must be blank; tags may share lines
        boundaries = [(open_tag.line, open_tag.end)]
        for tab in tabs:
            boundaries.append((tab.open_tag.line, tab.open_tag.start))
            end_tag = tab.close_tag or tab.open_tag
            boundaries.append((end_tag.line, end_tag.end))
        boundaries.append((close_tag.line, close_tag.start))
        for (l1, c1), (l2, c2) in zip(boundaries[0::2], boundaries[1::2]):
            gap = lines[l1][c1:c2] if l1 == l2 else lines[l1][c1:] + "".join(lines[l1 + 1 : l2]) + lines[l2][:c2]
            if gap.strip():
                self.note(result, path, l1, self.key, "content outside tab bodies inside tabpane", gap.strip()[:80])
                return None
        if lines[open_tag.line][: open_tag.start].strip():
            self.note(result, path, open_tag.line, self.key, "tabpane tag shares its line with other content", lines[open_tag.line])
            return None
        if lines[close_tag.line][close_tag.end :].strip():
            self.note(result, path, close_tag.line, self.key, "closing tabpane tag shares its line with other content", lines[close_tag.line])
            return None
        if not tabs:
            self.note(result, path, open_tag.line, self.key, "tabpane without tabs", open_tag.raw)
            return None
        return tabs

    def _convert_tabpane(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> bool:
        lines = doc.lines
        pane_text = _bool(open_tag.get("text"))
        persist = (open_tag.get("persist") or "").strip().lower()
        persist_lang = open_tag.get("persistLang")
        lang_equals_header = _bool(open_tag.get("langEqualsHeader"))
        pane_lang = (open_tag.get("lang") or "").strip()
        unknown = [p.name for p in open_tag.params if p.name not in {"text", "persist", "persistLang", "langEqualsHeader", "lang", "highlight", "right"} and p.name is not None]
        if unknown or open_tag.positional():
            self.note(result, path, open_tag.line, self.key, f"unsupported tabpane parameters {unknown or open_tag.positional()}", open_tag.raw)
            return False
        tabs = self._parse_tabs(path, doc, result, open_tag, close_tag)
        if tabs is None:
            return False
        indent = lines[open_tag.line][: open_tag.start]
        sync = not (persist == "disabled" or (persist_lang is not None and persist_lang.strip().lower() == "false"))
        active = [tab for tab in tabs if not tab.disabled]
        dropped = len(tabs) - len(active)
        if dropped:
            result.counts["tabs.disabled_tab_dropped"] += dropped
        if not active:
            self.note(result, path, open_tag.line, self.key, "tabpane has only disabled tabs", open_tag.raw)
            return False
        for tab in active:
            if '"' in tab.header:
                self.note(result, path, tab.open_tag.line, self.key, "tab header contains a double quote", tab.open_tag.raw)
                return False
            if tab.right:
                result.counts["tabs.right_dropped"] += 1
            if tab.highlight:
                result.counts["tabs.highlight_dropped"] += 1
        headers = [tab.header for tab in active]
        values = unique_values(headers) if sync else [""] * len(active)
        group = make_group(values) if sync else ""

        # ---- classify --------------------------------------------------------
        fences: list[tuple[str, str, list[str]]] = []  # (lang, attrs, body_lines_without_fence_lines)
        code_only = True
        for tab in active:
            text_mode = tab.text if tab.text is not None else pane_text
            body = strip_blank_edges(tab.body)
            if not text_mode:
                lang = tab.lang or (tab.header if lang_equals_header else "") or pane_lang
                tab_indent = lines[tab.open_tag.line][: tab.open_tag.start]
                code = dedent_lines(body, tab_indent) if all((not l.strip()) or l.startswith(tab_indent) for l in body) else body
                # a raw-code tab whose body is itself a fence is treated as text
                if code and FENCE_OPEN_RE.match(code[0]) and len(code) >= 2:
                    text_mode = True
                    body = code
                else:
                    fences.append((lang, "", code))
                    continue
            if text_mode:
                if not body:
                    code_only = False
                    break
                first = FENCE_OPEN_RE.match(body[0])
                if not first:
                    code_only = False
                    break
                marker = first.group("fence")
                closer = re.compile(r"^(?:[ \t]*>)*[ \t]*" + re.escape(marker[0]) + "{" + str(len(marker)) + ",}[ \t]*$")
                if not closer.match(body[-1]) or len(body) < 2:
                    code_only = False
                    break
                # exactly one fence: no other closing marker inside
                if any(closer.match(line) for line in body[1:-1]):
                    code_only = False
                    break
                info = split_info(first.group("info"))
                if info is None:
                    self.note(result, path, tab.open_tag.line, self.key, f"cannot merge tab attributes into fence info {first.group('info')!r}", body[0])
                    return False
                fence_indent = first.group("indent")
                inner = dedent_lines(body[1:-1], fence_indent)
                fences.append((info[0], info[1], inner))
        selected = [i for i, tab in enumerate(active) if tab.selected]
        if len(selected) > 1:
            self.note(result, path, open_tag.line, self.key, "more than one selected tab", open_tag.raw)
            return False

        new_lines: list[str] = []
        if code_only:
            for index, (lang, attrs, code) in enumerate(fences):
                extra = [("tab", headers[index])]
                if sync:
                    if index == 0:
                        extra.append(("group", group))
                    extra.append(("value", values[index]))
                fence_marker = "```"
                longest = max((len(m.group(0)) for line in code for m in re.finditer(r"`+", line)), default=0)
                if longest >= 3:
                    fence_marker = "`" * (longest + 1)
                new_lines.append(indent + fence_marker + merge_info(lang, attrs, extra))
                new_lines.extend((indent + line) if line.strip() else "" for line in code)
                new_lines.append(indent + fence_marker)
                if index != len(fences) - 1:
                    new_lines.append("")
            if selected:
                result.counts["tabs.selected_dropped"] += 1
            result.counts["tabpane.code_only"] += 1
        else:
            params = []
            if sync:
                params.append(("group", group))
                if selected:
                    params.append(("default", values[selected[0]]))
            elif selected:
                result.counts["tabs.selected_dropped"] += 1
            open_line = "{{< tabs" + ("".join(f" {k}={quote(v)}" for k, v in params)) + " >}}"
            new_lines.append(indent + open_line)
            kind = "prose_simple"
            if indent:
                result.counts["tabpane.indented_prose"] += 1
            for index, tab in enumerate(active):
                tab_params = [("label", tab.header)]
                if sync:
                    tab_params.append(("value", values[index]))
                new_lines.append(indent + "{{< tab" + "".join(f" {k}={quote(v)}" for k, v in tab_params) + " >}}")
                tab_indent = lines[tab.open_tag.line][: tab.open_tag.start]
                text_mode = tab.text if tab.text is not None else pane_text
                body = strip_blank_edges(tab.body)
                if not text_mode:
                    lang = tab.lang or (tab.header if lang_equals_header else "") or pane_lang
                    code = dedent_lines(body, tab_indent)
                    body = ["```" + (lang or "text")] + code + ["```"]
                else:
                    body = dedent_lines(body, tab_indent)
                joined = "\n".join(body)
                if "{{" in joined:
                    kind = "shortcodes"
                elif kind != "shortcodes" and any(HEADING_RE.search(line) for line in body):
                    kind = "headings"
                new_lines.extend((indent + line) if line.strip() else "" for line in body)
                new_lines.append(indent + "{{< /tab >}}")
            new_lines.append(indent + "{{< /tabs >}}")
            result.counts[f"tabpane.{kind}"] += 1
        result.counts["tabpane"] += 1
        if sync:
            result.counts["tabpane.grouped"] += 1
        self.replace_lines(doc, open_tag.line, close_tag.line, new_lines)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(new_lines) - 1)
        return True

    # --------------------------------------------------------------- code-group
    def _apply_code_groups(self, path: str, doc: Document, result: Result) -> bool:
        opens = [tag for tag in doc.iter_tags({"code-group"}) if not tag.closing]
        if not opens:
            return False
        changed = False
        for open_tag in reversed(opens):
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed code-group", open_tag.raw)
                continue
            if self._convert_code_group(path, doc, result, open_tag, close_tag):
                changed = True
        return changed

    def _convert_code_group(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> bool:
        lines = doc.lines
        indent = lines[open_tag.line][: open_tag.start]
        group_id = (open_tag.get("id") or "").strip()
        if not group_id:
            self.note(result, path, open_tag.line, self.key, "code-group without id", open_tag.raw)
            return False
        persist = _bool(open_tag.get("persist"), True)
        sync = (open_tag.get("sync") or "").strip()
        if sync:
            group_id = sync  # Docsy sync key = shared group; hash/persist follow the shared key
            result.counts["codegroup.sync_as_group"] += 1
        if open_tag.has("label"):
            result.counts["codegroup.label_dropped"] += 1
        defaults = [(k, open_tag.get(k)) for k in ("copy", "wrap", "collapse") if open_tag.has(k)]
        children = [t for t in doc.iter_tags({"code-tab"}) if not t.closing and (open_tag.line, open_tag.start) < (t.line, t.start) < (close_tag.line, close_tag.start)]
        if not children:
            self.note(result, path, open_tag.line, self.key, "code-group without code-tab children", open_tag.raw)
            return False
        blocks: list[list[str]] = []
        selected_seen = False
        for index, child in enumerate(children):
            close = doc.find_close(child)
            if close is None or (close.line, close.start) > (close_tag.line, close_tag.start):
                self.note(result, path, child.line, self.key, "unclosed code-tab", child.raw)
                return False
            title = (child.get("title") or "").strip()
            value = (child.get("value") or "").strip()
            lang = (child.get("lang") or "text").strip()
            if not title or not value:
                self.note(result, path, child.line, self.key, "code-tab without title/value", child.raw)
                return False
            if _bool(child.get("selected")):
                selected_seen = True
            body = lines[child.line + 1 : close.line]
            child_indent = lines[child.line][: child.start]
            code = dedent_lines(strip_blank_edges(body), child_indent)
            extra: list[tuple[str, str]] = [("tab", title)]
            if persist:
                if index == 0:
                    extra.append(("group", group_id))
                extra.append(("value", value))
            attrs = dict(defaults)
            for key in ("copy", "wrap", "collapse", "lineNos", "lineNoStart", "hl_lines", "tabWidth", "anchorLineNos", "style"):
                if child.has(key):
                    attrs[key] = child.get(key)
            extra.extend((k, v) for k, v in attrs.items() if v is not None)
            fence_marker = "```"
            longest = max((len(m.group(0)) for line in code for m in re.finditer(r"`+", line)), default=0)
            if longest >= 3:
                fence_marker = "`" * (longest + 1)
            block = [indent + fence_marker + merge_info(lang, "", extra)]
            block.extend((indent + line) if line.strip() else "" for line in code)
            block.append(indent + fence_marker)
            blocks.append(block)
        if selected_seen:
            result.counts["tabs.selected_dropped"] += 1
        if not persist:
            result.counts["codegroup.persist_false"] += 1
        new_lines: list[str] = []
        for index, block in enumerate(blocks):
            new_lines.extend(block)
            if index != len(blocks) - 1:
                new_lines.append("")
        result.counts["codegroup"] += 1
        self.replace_lines(doc, open_tag.line, close_tag.line, new_lines)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(new_lines) - 1)
        return True
