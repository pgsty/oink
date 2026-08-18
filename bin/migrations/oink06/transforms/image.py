"""imgproc and the retired `image` shortcode -> the block-image attribute line.

    {{< imgproc src="a.png" command="Fit" options="640x320" alt="A" >}}
    A **caption**.
    {{< /imgproc >}}

becomes

    ![A](a.png)
    {command="Fit" options="640x320" caption="A caption."}

The attribute-line caption is plain text, so a body carrying inline Markdown or
a double quote is reported and left alone rather than silently flattened.
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, dedent_lines, strip_blank_edges
from ..scanner import Document, Tag, quote


class ImageTransformation(Transformation):
    key = "image"
    description = "imgproc / image shortcode -> ![alt](src) + {command= options= caption=} attribute line"
    residual_patterns = (
        r"\{\{[<%]\s*/?imgproc\b",
        r"\{\{[<%]\s*/?image\b",
    )

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        opens = [tag for tag in doc.iter_tags({"imgproc", "image"}) if not tag.closing]
        if not opens:
            return
        changed = False
        for open_tag in reversed(opens):
            close_tag = None if open_tag.self_closing else doc.find_close(open_tag)
            if close_tag is None and not open_tag.self_closing:
                self.note(result, path, open_tag.line, self.key, f"unclosed {open_tag.name}", open_tag.raw)
                continue
            if self._convert(path, doc, result, open_tag, close_tag):
                changed = True
        if changed:
            result.text = doc.render()

    def _convert(self, path: str, doc: Document, result: Result, open_tag: Tag, close_tag: Tag | None) -> bool:
        lines = doc.lines
        params: list[tuple[str, str]] = []
        if open_tag.is_named():
            unknown = [p.name for p in open_tag.params if p.name not in {"src", "command", "options", "alt", "decorative"}]
            if unknown:
                self.note(result, path, open_tag.line, self.key, f"unsupported {open_tag.name} parameters {unknown}", open_tag.raw)
                return False
            src, command, options = (open_tag.get(k) for k in ("src", "command", "options"))
            if not (src and command and options):
                self.note(result, path, open_tag.line, self.key, f"{open_tag.name} requires src, command and options", open_tag.raw)
                return False
            params = [("src", src), ("command", command), ("options", options)]
            if open_tag.has("alt"):
                params.append(("alt", open_tag.get("alt") or ""))
            elif open_tag.get("decorative", "").strip().lower() == "true":
                params.append(("decorative", "true"))
            else:
                self.note(result, path, open_tag.line, self.key, f"{open_tag.name} without alt/decorative — the attribute line requires meaningful alt or an empty one", open_tag.raw)
                return False
        else:
            positional = open_tag.positional()
            if len(positional) != 3:
                self.note(result, path, open_tag.line, self.key, "positional imgproc needs exactly src command options", open_tag.raw)
                return False
            self.note(result, path, open_tag.line, self.key, "positional imgproc has no alt — add alt=/decorative=true by hand", open_tag.raw)
            return False
        line = lines[open_tag.line]
        prefix = line[: open_tag.start]
        if prefix.strip():
            self.note(result, path, open_tag.line, self.key, f"{open_tag.name} tag is not the first thing on its line", line)
            return False
        indent = prefix
        # caption body
        if close_tag is None:
            body: list[str] = []
            end_line = open_tag.line
            trailing = line[open_tag.end :]
        else:
            end_line = close_tag.line
            trailing = lines[close_tag.line][close_tag.end :]
            if open_tag.line == close_tag.line:
                between = line[open_tag.end : close_tag.start]
                body = [between.strip()] if between.strip() else []
            else:
                body = []
                rest = line[open_tag.end :]
                if rest.strip():
                    body.append(rest.strip())
                body.extend(lines[open_tag.line + 1 : close_tag.line])
                head = lines[close_tag.line][: close_tag.start]
                if head.strip():
                    body.append(head.strip())
        if trailing.strip():
            self.note(result, path, end_line, self.key, f"text after the {open_tag.name} closing tag", lines[end_line])
            return False
        body = strip_blank_edges(dedent_lines(body, indent))
        head = "{{< image " + " ".join(f"{k}={v if v in ('true', 'false') else quote(v)}" for k, v in params) + " >}}"
        values = dict(params)
        caption = " ".join(line.strip() for line in body if line.strip())
        if caption:
            if '"' in caption:
                self.note(result, path, open_tag.line, self.key, "caption contains a double quote — rewrite it by hand", caption[:80])
                return False
            if re.search(r"(\*[^*]+\*|_[^_]+_|`[^`]+`|\[[^\]]*\]\(|<[a-zA-Z/])", caption):
                self.note(result, path, open_tag.line, self.key, "caption is Markdown but the attribute line takes plain text — rewrite it by hand", caption[:80])
                return False
        alt = values.get("alt", "")
        attrs = [f'command="{values["command"]}"', f'options="{values["options"]}"']
        if caption:
            attrs.append(f'caption="{caption}"')
        out = [
            f"{indent}![{alt}]({values['src']})",
            indent + "{" + " ".join(attrs) + "}",
        ]
        result.counts[open_tag.name] += 1
        self.replace_lines(doc, open_tag.line, end_line, out)
        return True
