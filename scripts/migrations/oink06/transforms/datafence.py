"""echarts / infographic shortcodes -> same-name declarative fences.

    {{< echarts height="300px" >}}      ```echarts {height="300px"}
    series: [...]                  ->   series: [...]
    {{< /echarts >}}                    ```

An inner ```yaml / ```json wrapper is unwrapped; a nested ```js sub-fence or
a shortcode inside the body is reported and left alone.
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, dedent_lines, ensure_blank_around, quote_attr_value, strip_blank_edges
from ..scanner import FENCE_OPEN_RE, Document, Tag

NAMES = {"echarts", "infographic"}


class DataFenceTransformation(Transformation):
    key = "datafence"
    description = "echarts/infographic shortcodes -> declarative fences"
    residual_patterns = (r"\{\{[<%]\s*/?(?:echarts|infographic)\b",)

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        opens = [tag for tag in doc.iter_tags(NAMES) if not tag.closing]
        if not opens:
            return
        changed = False
        for open_tag in reversed(opens):
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, f"unclosed {open_tag.name}", open_tag.raw)
                continue
            if self._convert(path, doc, result, open_tag, close_tag):
                changed = True
        if changed:
            result.text = doc.render()

    def _convert(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag) -> bool:
        lines = doc.lines
        if not doc.tag_alone(open_tag) or not doc.tag_alone(close_tag):
            self.note(result, path, open_tag.line, self.key, f"{open_tag.name} tags share a line with other content", lines[open_tag.line])
            return False
        if open_tag.positional():
            self.note(result, path, open_tag.line, self.key, f"positional {open_tag.name} parameters", open_tag.raw)
            return False
        indent = lines[open_tag.line][: open_tag.start]
        body = strip_blank_edges(dedent_lines(lines[open_tag.line + 1 : close_tag.line], indent))
        joined = "\n".join(body)
        if "{{<" in joined or "{{%" in joined:
            self.note(result, path, open_tag.line, self.key, f"{open_tag.name} body contains a shortcode", open_tag.raw)
            return False
        script_lines: list[str] = []
        js_blocks = [i for i, line in enumerate(body) if re.match(r"^[ \t]*(`{3,}|~{3,})(?:js|javascript)\s*$", line)]
        if js_blocks:
            if open_tag.name != "echarts" or len(js_blocks) != 1:
                self.note(result, path, open_tag.line, self.key, f"{open_tag.name} body contains {len(js_blocks)} JavaScript sub-fences", open_tag.raw)
                return False
            start = js_blocks[0]
            head = FENCE_OPEN_RE.match(body[start])
            marker = head.group("fence")
            closer = re.compile(r"^[ \t]*" + re.escape(marker[0]) + "{" + str(len(marker)) + ",}[ \t]*$")
            end = next((i for i in range(start + 1, len(body)) if closer.match(body[i])), None)
            if end is None:
                self.note(result, path, open_tag.line, self.key, "unterminated JavaScript sub-fence in echarts body", open_tag.raw)
                return False
            js_code = dedent_lines(body[start + 1 : end], head.group("indent"))
            names: list[str] = []
            for line in js_code:
                for match in re.finditer(r"(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=", line):
                    if match.group(1) not in names:
                        names.append(match.group(1))
                for match in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(", line):
                    if match.group(1) not in names:
                        names.append(match.group(1))
            script_lines = ["<script>", "window.tdEchartsFunctions = window.tdEchartsFunctions || {};", "(function (registry) {"]
            script_lines.extend(js_code)
            script_lines.extend(f'registry["{name}"] = {name};' for name in names)
            script_lines.extend(["})(window.tdEchartsFunctions);", "</script>"])
            body = strip_blank_edges(body[:start] + body[end + 1 :])
            if not body:
                self.note(result, path, open_tag.line, self.key, "echarts body has a JavaScript sub-fence but no options body", open_tag.raw)
                return False
            result.counts["echarts.callbacks_inlined"] += 1
        # unwrap a single ```yaml/```json wrapper
        if body and FENCE_OPEN_RE.match(body[0]):
            head = FENCE_OPEN_RE.match(body[0])
            info = head.group("info").strip()
            marker = head.group("fence")
            closer = re.compile(r"^[ \t]*" + re.escape(marker[0]) + "{" + str(len(marker)) + ",}[ \t]*$")
            if info in ("", "yaml", "yml", "json", "text", "txt") and closer.match(body[-1]) and not any(closer.match(l) for l in body[1:-1]):
                body = strip_blank_edges(dedent_lines(body[1:-1], head.group("indent")))
            else:
                self.note(result, path, open_tag.line, self.key, f"{open_tag.name} body wraps an unexpected fence {info!r}", body[0])
                return False
        if any(FENCE_OPEN_RE.match(line) for line in body):
            self.note(result, path, open_tag.line, self.key, f"{open_tag.name} body contains another fence", open_tag.raw)
            return False
        if not body:
            self.note(result, path, open_tag.line, self.key, f"empty {open_tag.name} body", open_tag.raw)
            return False
        attrs = " ".join(f"{p.name}={quote_attr_value(p.value)}" for p in open_tag.params)
        marker = "```"
        longest = max((len(m.group(0)) for line in body for m in re.finditer(r"`+", line)), default=0)
        if longest >= 3:
            marker = "`" * (longest + 1)
        head = indent + marker + open_tag.name + ((" {" + attrs + "}") if attrs else "")
        out = [head] + [(indent + line) if line.strip() else "" for line in body] + [indent + marker]
        if script_lines:
            out = [(indent + line) if line.strip() else "" for line in script_lines] + [""] + out
        result.counts[open_tag.name] += 1
        self.replace_lines(doc, open_tag.line, close_tag.line, out)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(out) - 1)
        return True
