"""Docsy `_param` placeholders and Bootstrap `card header=` highlight boxes (oink.pgsty.com blog).

    {{% _param FAS rocket primary %}}      -> <i class="fa-solid fa-rocket text-primary px-1"></i>
    {{% _param FAS_LG robot info %}}       -> <i class="fa-solid fa-robot text-info fa-lg"></i>
    {{% _param FA regular file info %}}    -> <i class="fa-regular fa-file text-info px-1"></i>
    {{% _param BADGE BREAKING warning %}}  -> {{< badge text="BREAKING" tone="warning" >}}
    {{% _param BREAKING %}} / NEW / CLEANUP -> fixed icons; {{% _param hugoMinVersion %}} -> {{< param hugoMinVersion >}}
    {{% card header="Highlights" %}}…{{% /card %}} -> > [!NOTE] Highlights + quoted body
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, dedent_lines, ensure_blank_around, strip_blank_edges, strip_prefix
from ..scanner import Document, Tag, quote

BADGE_TONES = {"warning": "warning", "info": "info", "success": "success", "danger": "danger", "primary": "info", "secondary": "neutral"}
FIXED = {
    "BREAKING": '<i class="fa-solid fa-triangle-exclamation fa-lg text-warning px-1"></i>',
    "NEW": '<i class="fa-regular fa-square-check fa-lg text-success px-1"></i>',
    "CLEANUP": '<i class="fa-regular fa-wand-magic-sparkles fa-lg text-info px-1"></i>',
    "hugoMinVersion": "{{< param hugoMinVersion >}}",
}
ICON_RE = re.compile(r"^[a-z0-9-]+$")
TONE_RE = re.compile(r"^[a-z-]*$")


def _classes(*parts: str) -> str:
    return " ".join(part for part in parts if part)


class ParamPlaceholdersTransformation(Transformation):
    key = "param_placeholders"
    description = "_param placeholders -> FA icons / badge / param; card header= highlight box -> callout"
    residual_patterns = ()  # `_param` itself is in the removed-shortcode residual list

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        changed = self._apply_params(path, doc, result)
        if changed:
            doc.rescan()
        if self._apply_highlight_cards(path, doc, result):
            changed = True
        if changed:
            result.text = doc.render()

    # -- _param ---------------------------------------------------------------
    def _apply_params(self, path: str, doc: Document, result: Result) -> bool:
        tags = [tag for tag in doc.iter_tags({"_param"}) if not tag.closing]
        changed = False
        for tag in reversed(tags):
            replacement = self._render(tag)
            if replacement is None:
                self.note(result, path, tag.line, self.key, "_param form has no mapping — rewrite by hand", tag.raw)
                continue
            line = doc.lines[tag.line]
            doc.lines[tag.line] = line[: tag.start] + replacement + line[tag.end :]
            result.counts["_param"] += 1
            result.counts[f"_param.{tag.positional()[0] if tag.positional() else '?'}"] += 1
            changed = True
        return changed

    @staticmethod
    def _render(tag: Tag) -> str | None:
        args = tag.positional()
        if not args or tag.is_named():
            return None
        kind = args[0]
        if kind in FIXED and len(args) == 1:
            return FIXED[kind]
        if kind in ("FAS", "FAS_LG") and len(args) == 3:
            icon, tone = args[1], args[2]
            if not ICON_RE.match(icon) or not TONE_RE.match(tone):
                return None
            tone_class = f"text-{tone}" if tone else ""
            if kind == "FAS":
                return f'<i class="{_classes("fa-solid", "fa-" + icon, tone_class, "px-1")}"></i>'
            return f'<i class="{_classes("fa-solid", "fa-" + icon, tone_class, "fa-lg")}"></i>'
        if kind == "FA" and len(args) == 4:
            style, icon, tone = args[1], args[2], args[3]
            if style not in ("solid", "regular", "brands") or not ICON_RE.match(icon) or not TONE_RE.match(tone):
                return None
            tone_class = f"text-{tone}" if tone else ""
            return f'<i class="{_classes("fa-" + style, "fa-" + icon, tone_class, "px-1")}"></i>'
        if kind == "BADGE" and len(args) == 3:
            text, tone = args[1], args[2]
            if not text:
                return None
            return "{{< badge text=" + quote(text) + " tone=" + quote(BADGE_TONES.get(tone, "neutral")) + " >}}"
        return None

    # -- card header= "Highlights" box ------------------------------------------
    def _apply_highlight_cards(self, path: str, doc: Document, result: Result) -> bool:
        panes = []
        for tag in doc.iter_tags({"cardpane"}):
            if not tag.closing:
                close = doc.find_close(tag)
                if close is not None:
                    panes.append(((tag.line, tag.start), (close.line, close.start)))
        opens = []
        for tag in doc.iter_tags({"card"}):
            if tag.closing or tag.positional():
                continue
            names = {p.name for p in tag.params}
            if names != {"header"}:
                continue
            if any(a < (tag.line, tag.start) < b for a, b in panes):
                continue
            opens.append(tag)
        changed = False
        lines = doc.lines
        for open_tag in reversed(opens):
            close_tag = doc.find_close(open_tag)
            if close_tag is None:
                self.note(result, path, open_tag.line, self.key, "unclosed card", open_tag.raw)
                continue
            if lines[open_tag.line][: open_tag.start].strip() or lines[open_tag.line][open_tag.end :].strip() or lines[close_tag.line][close_tag.end :].strip():
                self.note(result, path, open_tag.line, self.key, "card header= box shares a line with other content", lines[open_tag.line])
                continue
            indent = lines[open_tag.line][: open_tag.start]
            header = (open_tag.get("header") or "").strip()
            body = lines[open_tag.line + 1 : close_tag.line]
            tail = lines[close_tag.line][: close_tag.start]
            if tail.strip():
                body.append(tail)
            body = strip_blank_edges([strip_prefix(line, indent) for line in body])
            quoted = [("> " + line) if line.strip() else ">" for line in body]
            new_lines = [indent + "> [!NOTE]" + ((" " + header) if header else "")] + [indent + line for line in quoted]
            self.replace_lines(doc, open_tag.line, close_tag.line, new_lines)
            ensure_blank_around(doc, open_tag.line, open_tag.line + len(new_lines) - 1)
            result.counts["card.header_box"] += 1
            changed = True
        return changed
