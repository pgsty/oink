"""doc-cards/doc-card and nav-cards/nav-card -> {{< cards >}}{{< card >}} or {.cards}.

Bootstrap ``card`` / ``cardpane`` (header/title/subtitle/footer + raw HTML)
have no v5 equivalent and are only reported.
"""

from __future__ import annotations

import re

from ..base import Result, Transformation, dedent_lines, ensure_blank_around, strip_blank_edges
from ..scanner import Document, Tag, quote, render_tag

CONTAINERS = {"doc-cards", "nav-cards", "doc-carousel"}
CHILDREN = {"doc-card", "nav-card"}
CARD_PARAMS = {"title", "link", "image", "alt", "icon", "desc", "accent", "badge"}
FA_ICON_RE = re.compile(r"^fa-(?:solid|regular|brands) fa-[a-z0-9-]+$")


class _Card:
    def __init__(self, tag: Tag):
        self.tag = tag
        self.title = (tag.get("title") or "").strip()
        self.link = (tag.get("link") or "").strip()
        self.image = (tag.get("image") or "").strip()
        self.alt = (tag.get("alt") or "").strip()
        self.icon = (tag.get("icon") or "").strip()
        self.desc = (tag.get("desc") or "").strip()
        self.accent = (tag.get("accent") or "").strip()
        self.badge = (tag.get("badge") or "").strip()
        self.body: list[str] = []


class CardsTransformation(Transformation):
    key = "cards"
    description = "doc-card(s)/nav-card(s) -> {{< cards >}}{{< card >}} or {.cards}; card/cardpane reported"
    residual_patterns = (
        r"\{\{[<%]\s*/?(?:doc-cards?|nav-cards?|doc-carousel|cardpane)\b",
        r"\{\{%\s*/?cards?\b",  # withdrawn % form of the new containers
    )

    def residual_findings(self, doc: Document):  # used by `check`
        for tag in bootstrap_cards(doc):
            yield tag.line, "Bootstrap card (header/subtitle/footer/code) — rewrite by hand", tag.raw

    def _apply(self, path: str, doc: Document, result: Result) -> None:
        for tag in bootstrap_cards(doc):
            self.note(result, path, tag.line, self.key, "Bootstrap card/cardpane has no v5 form (header/subtitle/footer/raw HTML) — rewrite by hand", tag.raw)
        opens = [tag for tag in doc.iter_tags(CONTAINERS) if not tag.closing]
        spans = []
        for open_tag in opens:
            close_tag = doc.find_close(open_tag)
            if close_tag is not None:
                spans.append(((open_tag.line, open_tag.start), (close_tag.line, close_tag.start)))
        for tag in doc.iter_tags(CHILDREN):
            if tag.closing:
                continue
            if not any(a < (tag.line, tag.start) < b for a, b in spans):
                self.note(result, path, tag.line, self.key, f"{tag.name} outside doc-cards/nav-cards/doc-carousel — wrap by hand", tag.raw)
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
        unknown = [p.name for p in open_tag.params if p.name != "cols"]
        if unknown:
            self.note(result, path, open_tag.line, self.key, f"unsupported {open_tag.name} parameters {unknown}", open_tag.raw)
            return False
        indent = lines[open_tag.line][: open_tag.start]
        children = [t for t in doc.iter_tags(CHILDREN) if (open_tag.line, open_tag.start) < (t.line, t.start) < (close_tag.line, close_tag.start)]
        cards: list[_Card] = []
        covered: set[int] = set()
        index = 0
        while index < len(children):
            tag = children[index]
            if tag.closing:
                self.note(result, path, tag.line, self.key, "stray closing card tag", tag.raw)
                return False
            if not doc.tag_alone(tag):
                self.note(result, path, tag.line, self.key, "card tag shares a line with other content", lines[tag.line])
                return False
            unknown = [p.name for p in tag.params if p.name not in CARD_PARAMS]
            if unknown or tag.positional():
                self.note(result, path, tag.line, self.key, f"unsupported {tag.name} parameters {unknown or tag.positional()}", tag.raw)
                return False
            card = _Card(tag)
            if not card.title:
                self.note(result, path, tag.line, self.key, f"{tag.name} without title", tag.raw)
                return False
            if card.icon and not FA_ICON_RE.match(card.icon):
                self.note(result, path, tag.line, self.key, f"{tag.name} icon {card.icon!r} is not one FA class pair", tag.raw)
                return False
            if card.image and not card.alt:
                self.note(result, path, tag.line, self.key, f"{tag.name} image without alt (image_alt is required)", tag.raw)
                return False
            covered.add(tag.line)
            if not tag.self_closing:
                close = doc.find_close(tag)
                if close is None or (close.line, close.start) > (close_tag.line, close_tag.start):
                    self.note(result, path, tag.line, self.key, f"unclosed {tag.name}", tag.raw)
                    return False
                if not doc.tag_alone(close):
                    self.note(result, path, close.line, self.key, "closing card tag shares a line with other content", lines[close.line])
                    return False
                card.body = strip_blank_edges(dedent_lines(lines[tag.line + 1 : close.line], lines[tag.line][: tag.start]))
                covered.update(range(tag.line, close.line + 1))
                index += 1
                while index < len(children) and children[index].line <= close.line:
                    index += 1
            else:
                index += 1
            cards.append(card)
        for line in range(open_tag.line + 1, close_tag.line):
            if lines[line].strip() and line not in covered:
                self.note(result, path, line, self.key, "content between cards", lines[line])
                return False
        if not cards:
            self.note(result, path, open_tag.line, self.key, f"{open_tag.name} without cards", open_tag.raw)
            return False
        # description = desc + inner Markdown
        for card in cards:
            if card.desc and re.search(r"\{[a-z][a-z0-9_]*\}", card.desc):
                result.counts["cards.desc_param_token"] += 1
        simple = all(
            card.link and not card.icon and not card.image and not card.badge and _single_line(card)
            for card in cards
        )
        if any(card.accent for card in cards):
            result.counts["cards.accent_dropped"] += sum(1 for c in cards if c.accent)
        out: list[str] = []
        if simple:
            for card in cards:
                text = card.desc or (card.body[0] if card.body else "")
                entry = f"{indent}- [{card.title}]({card.link})"
                if text:
                    entry += f" — {text}"
                out.append(entry)
            out.append(indent + "{.cards}")
            result.counts["cards.list"] += 1
        else:
            out.append(indent + "{{< cards >}}")
            for card in cards:
                params = [("title", card.title)]
                if card.link:
                    params.append(("link", card.link))
                if card.icon:
                    params.append(("icon", card.icon))
                if card.badge:
                    params.append(("badge", card.badge))
                if card.image:
                    params.append(("image", card.image))
                    params.append(("image_alt", card.alt))
                out.append(indent + "{{< card " + " ".join(f"{k}={quote(v)}" for k, v in params) + " >}}")
                body: list[str] = []
                if card.desc:
                    body.append(card.desc)
                if card.body:
                    if body:
                        body.append("")
                    body.extend(card.body)
                out.extend((indent + line) if line.strip() else "" for line in body)
                out.append(indent + "{{< /card >}}")
            out.append(indent + "{{< /cards >}}")
            result.counts["cards.rich"] += 1
        if open_tag.has("cols"):
            result.counts["cards.cols_dropped"] += 1
        if open_tag.name == "doc-carousel":
            result.counts["cards.carousel_flattened"] += 1
        result.counts["cards"] += 1
        result.counts["cards.items"] += len(cards)
        self.replace_lines(doc, open_tag.line, close_tag.line, out)
        ensure_blank_around(doc, open_tag.line, open_tag.line + len(out) - 1)
        return True


BOOTSTRAP_CARD_PARAMS = {"header", "subtitle", "footer", "code", "lang", "highlight"}


def bootstrap_cards(doc: Document):
    """Yield legacy Bootstrap `card` / `cardpane` open tags (not the new %card)."""

    panes = []
    for tag in doc.iter_tags({"cardpane"}):
        if not tag.closing:
            close = doc.find_close(tag)
            panes.append((tag, close))
            yield tag
    for tag in doc.iter_tags({"card"}):
        if tag.closing:
            continue
        legacy = any(p.name in BOOTSTRAP_CARD_PARAMS for p in tag.params) or bool(tag.positional())
        if not legacy:
            for open_tag, close_tag in panes:
                if close_tag is not None and open_tag.line < tag.line < close_tag.line:
                    legacy = True
                    break
        if legacy:
            yield tag


def _single_line(card: _Card) -> bool:
    if card.desc and card.body:
        return False
    if card.body:
        return len(card.body) == 1 and not re.match(r"^\s*([-*+]|\d+[.)])\s|^\s*#|^\s*[`>|]|\{\{", card.body[0])
    return "\n" not in card.desc
