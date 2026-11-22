#!/usr/bin/env python3
"""Convert a site's retired SCSS hooks into the plain-CSS project stylesheet.

    bin/migrations/sass_hooks.py --site ~/pgsty/site-a            # report only
    bin/migrations/sass_hooks.py --site ~/pgsty/site-a --write    # write assets/css/project.css

OINK ships compiled CSS and a site build no longer runs Sass, so
assets/scss/_variables_project.scss, _variables_project_after_bs.scss and
_styles_project.scss are ignored. This tool compiles the theme once without
and once with those hooks, then writes the difference as plain CSS:

- theme rules whose values changed with the site's Sass variables, and
- the site's own rules, with their comments.

It verifies that the theme bundle followed by the new file gives every
selector the declarations of the old compiled stylesheet, and lists what
plain CSS cannot express. Dry-run is the default. ``--write`` creates
assets/css/project.css and leaves the SCSS files for review; delete them once
the result is accepted. It is run once per site and needs LibSass, which only
Hugo Extended up to 0.169 contains: where the default ``hugo`` is newer, keep
that release on PATH as ``hugo-0.169.0`` or name it with ``--hugo``. Stdlib only.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
HOOKS = ("_variables_project", "_variables_project_after_bs", "_styles_project")
VARIABLE_HOOKS = HOOKS[:2]
# Where td/_main.scss imported each hook before the hooks were retired.
ANCHORS = (
    ("@import 'variables_forward';\n", "@import '../variables_project';\n"),
    ("@import 'support/bootstrap_vers_test';\n", "@import '../variables_project_after_bs';\n"),
)
GROUP_RULES = {"@media", "@supports", "@container", "@layer", "@starting-style", "@scope",
               "@document", "@-moz-document"}
BUILD_TIMEOUT = 120
# Hugo executables to try for LibSass, in order, when --hugo is not given.
LIBSASS_HUGO = ("hugo", "hugo-0.169.0")

LAYOUT = """{{- $options := dict "transpiler" site.Params.transpiler "outputStyle" "expanded" -}}
{{- (resources.Get "scss/oink-legacy.scss" | css.Sass $options).Publish -}}
"""


# --- CSS model ---------------------------------------------------------------

@dataclass
class Node:
    kind: str                 # rule | group | opaque | comment
    prelude: str              # normalized selector list, at-rule prelude or text
    text: str                 # source text, verbatim
    selectors: tuple[str, ...] = ()
    decls: list[tuple[str, str]] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str]:
        if self.kind == "rule":
            return ("rule", ", ".join(self.selectors))
        if self.kind == "group":
            return ("group", self.prelude)
        return (self.kind, squash(self.text))


ATTRIBUTE_QUOTES = re.compile(r"\[([^\]'\"]+=)'([^'\"\]]*)'\]")


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_comments(text: str) -> str:
    out, index, quote = [], 0, ""
    while index < len(text):
        char = text[index]
        if quote:
            out.append(char)
            if char == "\\" and index + 1 < len(text):
                out.append(text[index + 1])
                index += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
            out.append(char)
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 1
        else:
            out.append(char)
        index += 1
    return "".join(out)


def split_top(text: str, separator: str) -> list[str]:
    """Split on a separator outside strings, parentheses and brackets."""

    parts, depth, quote, start, index = [], 0, "", 0, 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char in "([":
            depth += 1
        elif char in ")]":
            depth = max(0, depth - 1)
        elif char == separator and depth == 0:
            parts.append(text[start:index])
            start = index + 1
        index += 1
    parts.append(text[start:])
    return parts


def scan_block(text: str, index: int) -> tuple[int, str]:
    """From ``index``, return (position, terminator) of the next ``{``, ``;`` or ``}``."""

    depth, quote = 0, ""
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and char in "{;}":
            return index, char
        index += 1
    return len(text), ""


def has_block(body: str) -> bool:
    """Whether a rule body nests another block, as native CSS nesting does."""

    index = 0
    while index < len(body):
        index, terminator = scan_block(body, index)
        if terminator == "{":
            return True
        index += 1
    return False


def matching_brace(text: str, opening: int) -> int:
    depth, quote, index = 0, "", opening
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return len(text) - 1


def parse(css: str) -> list[Node]:
    """Parse a stylesheet into rules, conditional groups, opaque at-rules and comments."""

    nodes, index = [], 0
    while index < len(css):
        if css[index].isspace():
            index += 1
            continue
        if css.startswith("/*", index):
            end = css.find("*/", index + 2)
            end = len(css) if end < 0 else end + 2
            nodes.append(Node("comment", "", css[index:end]))
            index = end
            continue
        stop, terminator = scan_block(css, index)
        if terminator == "}" or not terminator:
            index = stop + 1
            continue
        prelude = squash(strip_comments(css[index:stop]))
        if terminator == ";":
            if prelude:
                nodes.append(Node("opaque", prelude, css[index:stop + 1]))
            index = stop + 1
            continue
        end = matching_brace(css, stop)
        text, body = css[index:end + 1], css[stop + 1:end]
        name = prelude.split("(")[0].split(" ")[0].lower()
        if name in GROUP_RULES:
            nodes.append(Node("group", prelude, text, children=parse(body)))
        elif prelude.startswith("@") or has_block(body):
            nodes.append(Node("opaque", prelude, text))
        else:
            selectors = tuple(ATTRIBUTE_QUOTES.sub(r'[\1"\2"]', squash(part))
                              for part in split_top(prelude, ","))
            decls = []
            for part in split_top(strip_comments(body), ";"):
                if ":" in part:
                    prop, value = part.split(":", 1)
                    decls.append((squash(prop), squash(value)))
            nodes.append(Node("rule", prelude, text, selectors, decls))
        index = end + 1
    return nodes


# --- Difference --------------------------------------------------------------

@dataclass
class Report:
    changed_rules: int = 0
    changed_decls: int = 0
    site_rules: int = 0
    dead: int = 0
    scoped: int = 0
    removed: list[str] = field(default_factory=list)
    extended: list[str] = field(default_factory=list)
    order: list[str] = field(default_factory=list)


@dataclass
class Override:
    """Declarations of one theme rule that the site's Sass changed or extended."""

    source: Node
    context: tuple[str, ...]
    selectors: tuple[str, ...]
    decls: list[tuple[str, str]]


FUNCTIONAL = re.compile(r":([a-z-]+)\(([^()]*)\)")
PSEUDO_ELEMENT = re.compile(r"::[\w-]+|:(?:before|after|first-line|first-letter)\b")


def specificity(selector: str) -> tuple[int, int, int]:
    text = re.sub(r"\[[^\]]*\]", "[a]", selector)
    ids = classes = types = 0
    while match := FUNCTIONAL.search(text):
        name, arguments = match.groups()
        if name in ("is", "not", "has", "matches", "-webkit-any", "-moz-any"):
            best = max((specificity(part) for part in split_top(arguments, ",")), default=(0, 0, 0))
            ids, classes, types = ids + best[0], classes + best[1], types + best[2]
        elif name != "where":
            classes += 1
        text = text[:match.start()] + text[match.end():]
    types += len(PSEUDO_ELEMENT.findall(text))
    text = PSEUDO_ELEMENT.sub("", text)
    ids += len(re.findall(r"#[\w-]+", text))
    classes += len(re.findall(r"\.[\w-]+|\[a\]|:[\w-]+", text))
    text = re.sub(r"#[\w-]+|\.[\w-]+|\[a\]|:[\w-]+", "", text)
    types += len(re.findall(r"(?:^|[\s>+~])[a-zA-Z][\w-]*", text))
    return ids, classes, types


def subject(selector: str) -> str:
    """Return the compound that names the styled element."""

    flat = re.sub(r"\([^()]*\)", lambda match: "(" + "_" * (len(match.group()) - 2) + ")",
                  re.sub(r"\[[^\]]*\]", lambda match: "[" + "_" * (len(match.group()) - 2) + "]",
                         selector))
    cut = max(flat.rfind(char) for char in " >+~") + 1
    return selector[cut:]


def split_pseudo(selector: str) -> tuple[str, str, str]:
    """Split a selector into its element part, pseudo-element and any state after it."""

    match = PSEUDO_ELEMENT.search(selector)
    if not match:
        return selector, "", ""
    return selector[:match.start()], match.group(), selector[match.end():]


def scope(selector: str, others: tuple[str, ...]) -> str | None:
    """Limit ``selector`` to elements none of ``others`` match, at unchanged specificity."""

    base, pseudo, state = split_pseudo(selector)
    bases = [split_pseudo(other) for other in others]
    if any(other_pseudo != pseudo or other_state for _, other_pseudo, other_state in bases):
        return None
    return f"{base}:where(:not({', '.join(head for head, _, _ in bases)})){pseudo}{state}"


def may_share_element(left: str, right: str) -> bool:
    """Whether two selectors plausibly style one element at the same time."""

    def facts(selector: str) -> tuple[str, set[str], list[str], dict[str, str]]:
        compound = subject(selector)
        exact = dict(re.findall(r'\[([\w-]+)="([^"]*)"\]', compound))
        bare = re.sub(r"\[[^\]]*\]|\([^()]*\)", "", compound)
        names = set(re.findall(r"[.#][\w-]+", bare))
        tag = re.match(r"[a-zA-Z][\w-]*", bare)
        pseudo = PSEUDO_ELEMENT.findall(bare)
        if not names and (bare.startswith(":root") or (tag and tag.group() == "html")
                          or (not tag and compound.startswith("["))):
            return "html", names, pseudo, exact
        return (tag.group() if tag else ""), names, pseudo, exact

    (left_tag, left_names, left_pseudo, left_exact), \
        (right_tag, right_names, right_pseudo, right_exact) = facts(left), facts(right)
    if left_pseudo != right_pseudo or (left_tag and right_tag and left_tag != right_tag):
        return False
    if any(left_exact[name] != right_exact[name] for name in left_exact.keys() & right_exact.keys()):
        return False
    if left_tag == right_tag == "html":
        return True
    if left_names & right_names:
        return True
    return bool(left_tag) and left_tag == right_tag and not left_names and not right_names


def rule_text(selectors: tuple[str, ...], decls: list[tuple[str, str]]) -> str:
    body = "".join(f"  {prop}: {value};\n" for prop, value in decls)
    return ",\n".join(selectors) + " {\n" + body + "}"


def indent(text: str) -> str:
    return "\n".join("  " + line if line.strip() else line for line in text.splitlines())


def join(parts: list[str]) -> str:
    """Separate rules with a blank line; keep a comment attached to what follows it."""

    out = ""
    for part in parts:
        if out:
            out += "\n" if out.rstrip().endswith("*/") else "\n\n"
        out += part
    return out


def reindent(text: str) -> str:
    """Return a nested node's verbatim text with its group indentation removed."""

    lines = text.splitlines()
    if len(lines) < 2:
        return text
    margin = min(len(line) - len(line.lstrip()) for line in lines[1:] if line.strip())
    return "\n".join([lines[0]] + [line[margin:] for line in lines[1:]])


def diff(old: list[Node], new: list[Node], report: Report,
         context: tuple[str, ...] = ()) -> tuple[list, list[str]]:
    """Return (override items, trailing site CSS) that turn ``old`` into ``new``.

    An item is verbatim CSS, an Override, or (group prelude, items).
    """

    matcher = SequenceMatcher(None, [node.key for node in old], [node.key for node in new],
                              autojunk=False)
    opcodes = matcher.get_opcodes()
    path = "".join(f"{part} > " for part in context)
    items: list = []
    tail: list[str] = []

    for position, (tag, a1, a2, b1, b2) in enumerate(opcodes):
        if tag == "equal":
            for before, after in zip(old[a1:a2], new[b1:b2]):
                if before.kind == "group":
                    inner, inner_tail = diff(before.children, after.children, report,
                                             context + (before.prelude,))
                    if inner or inner_tail:
                        items.append((after.prelude, inner + inner_tail))
                elif before.kind == "rule" and before.decls != after.decls:
                    was: dict[str, list[str]] = {}
                    for prop, value in before.decls:
                        was.setdefault(prop, []).append(value)
                    now: dict[str, list[str]] = {}
                    for prop, value in after.decls:
                        now.setdefault(prop, []).append(value)
                    for prop in was:
                        if prop not in now:
                            report.removed.append(f"{path}{before.prelude} {{ {prop} }}")
                    changed = [prop for prop in now if now[prop] != was.get(prop)]
                    items.append(Override(before, context, after.selectors,
                                          [(p, v) for p, v in after.decls if p in changed]))
            continue
        before, after = old[a1:a2], new[b1:b2]
        if tag == "replace" and len(before) == len(after):
            # @extend adds a site selector to a theme rule: emit only the addition.
            paired = []
            for left, right in zip(before, after):
                extra = tuple(s for s in right.selectors if s not in left.selectors)
                if (left.kind == right.kind == "rule" and left.decls == right.decls and extra
                        and set(left.selectors) <= set(right.selectors)):
                    paired.append(Override(left, context, extra, right.decls))
                else:
                    paired = []
                    break
            if paired:
                items.extend(paired)
                for override in paired:
                    report.extended.append(f"{path}{', '.join(override.selectors)} "
                                           f"extends {override.source.prelude}")
                continue
        for node in before:
            if node.kind in ("rule", "group") or node.prelude.startswith(("@font-face", "@keyframes")):
                report.removed.append(f"{path}{node.prelude or squash(node.text)[:80]}")
        trailing = position == len(opcodes) - 1 and not context
        for node in after:
            if node.kind == "opaque" and node.prelude.lower().startswith("@charset"):
                continue
            if node.kind == "comment" and not trailing:
                continue
            (tail if trailing else items).append(reindent(node.text) if context else node.text)
            report.site_rules += node.kind != "comment"
    return items, tail


def render(items: list, theme: list[Node], report: Report) -> list[str]:
    """Write override items as CSS that keeps each declaration's old cascade position.

    An override now loads after the whole theme. Where an unchanged theme
    declaration of equal specificity used to follow it and win, the override
    is dropped (same selector) or scoped away from that selector.
    """

    order: dict[int, int] = {}
    later: dict[str, list[tuple[int, tuple[str, ...], str, bool, Node]]] = {}

    def index(nodes: list[Node], context: tuple[str, ...]) -> None:
        for node in nodes:
            if node.kind == "group":
                index(node.children, context + (node.prelude,))
            elif node.kind == "rule":
                order[id(node)] = len(order)
                for selector in node.selectors:
                    for prop, value in node.decls:
                        later.setdefault(prop, []).append(
                            (order[id(node)], context, selector, value.endswith("!important"), node))

    def overrides(nodes: list) -> list[Override]:
        found = []
        for item in nodes:
            if isinstance(item, Override):
                found.append(item)
            elif isinstance(item, tuple):
                found.extend(overrides(item[1]))
        return found

    index(theme, ())
    changed = {(id(item.source), prop) for item in overrides(items) for prop, _ in item.decls}

    def write(nodes: list) -> list[str]:
        out = []
        for item in nodes:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, tuple):
                inner = write(item[1])
                if inner:
                    out.append(item[0] + " {\n" + indent(join(inner)) + "\n}")
            else:
                out.extend(write_override(item))
        return out

    def write_override(item: Override) -> list[str]:
        position = order[id(item.source)]
        groups: dict[tuple[tuple[str, ...], tuple[tuple[str, str], ...]], list[str]] = {}
        for selector in item.selectors:
            weight = specificity(selector)
            scopes: dict[tuple[str, ...], list[tuple[str, str]]] = {}
            for prop, value in item.decls:
                important = value.endswith("!important")
                followers = [entry for entry in later.get(prop, ())
                             if entry[0] > position and entry[3] == important]
                if any(entry[1] == item.context and entry[2] == selector for entry in followers):
                    report.dead += 1
                    continue
                exclude, elsewhere = [], []
                for _, context, other, _, node in followers:
                    if ((id(node), prop) in changed or other == selector
                            or specificity(other) != weight
                            or not may_share_element(selector, other)):
                        continue
                    (exclude if context == item.context else elsewhere).append((context, other))
                exclude = tuple(dict.fromkeys(other for _, other in exclude))
                if exclude and scope(selector, exclude) is None:
                    elsewhere += [(item.context, other) for other in exclude]
                    exclude = ()
                for context, other in elsewhere:
                    where = "".join(f"{part} > " for part in context)
                    report.order.append(
                        f"{selector} {{ {prop} }} now follows {where}{other}, which used to "
                        "override it at equal specificity")
                scopes.setdefault(exclude, []).append((prop, value))
            for exclude, decls in scopes.items():
                scoped = scope(selector, exclude) if exclude else selector
                report.scoped += bool(exclude) * len(decls)
                groups.setdefault((exclude, tuple(decls)), []).append(scoped)
        out = []
        for (_, decls), selectors in groups.items():
            out.append(rule_text(tuple(selectors), list(decls)))
            report.changed_rules += 1
            report.changed_decls += len(decls) * len(selectors)
        return out

    return write(items)


# --- Equivalence -------------------------------------------------------------

SCOPE = re.compile(r":where\(:not\((?:[^()]|\([^()]*\))*\)\)(?=$|::?[\w-]+)")


def cascade(nodes: list[Node], context: tuple[str, ...] = (),
            into: dict | None = None, order: list[int] | None = None) -> dict:
    """Map (context, selector, property) to its winning value by source order."""

    into = {} if into is None else into
    order = [0] if order is None else order
    for node in nodes:
        if node.kind == "group":
            cascade(node.children, context + (node.prelude,), into, order)
        elif node.kind == "rule":
            for selector in node.selectors:
                selector = SCOPE.sub("", selector)
                for prop, value in node.decls:
                    order[0] += 1
                    key = (context, selector, prop)
                    rank = (value.endswith("!important"), order[0])
                    if key not in into or rank >= into[key][0]:
                        into[key] = (rank, value)
        elif node.kind == "opaque" and not node.prelude.lower().startswith("@charset"):
            name = node.prelude if not node.prelude.startswith("@font-face") else squash(node.text)
            into[(context, name, "")] = ((False, 0), squash(strip_comments(node.text)))
    return into


def equivalent(theme: list[Node], project: list[Node], compiled: list[Node]) -> list[str]:
    """List every (selector, property) where theme + project differs from the old stylesheet."""

    ours = {key: value for key, (_, value) in cascade(theme + project).items()}
    theirs = {key: value for key, (_, value) in cascade(compiled).items()}
    problems = []
    for key, value in theirs.items():
        if ours.get(key) != value:
            context, selector, prop = key
            problems.append(f"{' > '.join(context + (selector,))} {{ {prop}: {value} }}"
                            f" but the new stylesheet gives {ours.get(key, 'nothing')}")
    return problems


OVERRIDES_NOTE = """/* Theme rules whose values came from the site's Sass variables. Where a rule
   ends in :where(:not(...)), a later theme rule of equal specificity already
   overrode the value for those selectors; the suffix keeps it that way. */"""


def convert(theme_css: str, compiled_css: str) -> tuple[str, Report, list[str]]:
    """Return (project CSS, report, equivalence problems) for one compiled stylesheet."""

    theme, compiled, report = parse(theme_css), parse(compiled_css), Report()
    items, tail = diff(theme, compiled, report)
    overrides = render(items, theme, report)
    sections = []
    if overrides:
        sections.append(OVERRIDES_NOTE + "\n\n" + join(overrides))
    if tail:
        sections.append(join(tail))
    project = "\n\n".join(sections) + "\n" if sections else ""
    if not project.isascii():
        project = '@charset "UTF-8";\n' + project
    return project, report, equivalent(theme, parse(project), compiled)


# --- Sass --------------------------------------------------------------------

def loud_comments(scss: str) -> str:
    """Turn ``//`` comments into ``/* */`` so the compiler keeps them."""

    out, index, quote, url = [], 0, "", False
    while index < len(scss):
        char = scss[index]
        if quote:
            out.append(char)
            if char == "\\" and index + 1 < len(scss):
                out.append(scss[index + 1])
                index += 1
            elif char == quote:
                quote = ""
        elif url:
            out.append(char)
            url = char != ")"
        elif char in "\"'":
            quote = char
            out.append(char)
        elif scss.startswith("url(", index):
            out.append("url(")
            index += 3
            url = True
        elif scss.startswith("/*", index):
            end = scss.find("*/", index + 2)
            end = len(scss) if end < 0 else end + 2
            out.append(scss[index:end])
            index = end - 1
        elif scss.startswith("//", index):
            # Consecutive whole-line comments become one block comment.
            line_start = "".join(out).rfind("\n") + 1
            margin = "".join(out)[line_start:]
            whole_line = not margin.strip()
            notes = []
            while True:
                end = scss.find("\n", index)
                end = len(scss) if end < 0 else end
                notes.append(scss[index + 2:end].rstrip().removeprefix(" ").replace("*/", "* /"))
                following = scss[end + 1:end + 1 + len(margin) + 2] if whole_line else ""
                if not (whole_line and following == margin + "//"):
                    break
                index = end + 1 + len(margin)
            if any(note.strip("/-=*#~ ") for note in notes):
                out.append("/* " + ("\n" + margin + "   ").join(notes) + " */")
            index = end - 1
        else:
            out.append(char)
        index += 1
    return "".join(out)


def find_compiler(requested: str | None, transpiler: str) -> str:
    """Return the Hugo executable that will run the Sass compiler."""

    names = (requested,) if requested else (LIBSASS_HUGO if transpiler == "libsass" else ("hugo",))
    found = [path for path in map(shutil.which, names) if path]
    if not found:
        raise SystemExit(f"Hugo executable not found: {', '.join(names)}")
    for path in found:
        version = subprocess.run([path, "version"], text=True, capture_output=True).stdout
        if transpiler != "libsass" or "+extended" in version:
            return path
    raise SystemExit(
        f"No LibSass in {', '.join(found)}: Hugo 0.170 removed it. Keep Hugo Extended 0.169.0 "
        "on PATH as hugo-0.169.0, or pass --hugo <path to it>.")


def legacy_entry() -> str:
    """Rebuild the retired composition: td/_main.scss with its three hook imports."""

    source = (ROOT / "assets/scss/td/_main.scss").read_text(encoding="utf-8")
    for anchor, hook in ANCHORS:
        if anchor not in source:
            raise SystemExit(f"assets/scss/td/_main.scss no longer has {anchor.strip()}; "
                             "use the OINK release that retired the SCSS hooks")
        source = source.replace(anchor, anchor + hook)
    return source + "\n@import '../styles_project';\n"


def compile_legacy(hugo: str, transpiler: str, scss: Path | None, loud: bool = False) -> str:
    """Compile the theme as it was composed with hooks; ``scss`` is the site's assets/scss."""

    with tempfile.TemporaryDirectory(prefix="oink-sass-hooks-") as directory:
        site = Path(directory)
        # One tree holds the entry, empty hooks and then the site's own SCSS,
        # which overwrites them. Hugo lets the later of two mounts win, so the
        # tree overrides the theme's assets as a site's files do.
        tree = site / "tree/scss"
        (tree / "td").mkdir(parents=True)
        for name in HOOKS:
            (tree / f"{name}.scss").write_text("", encoding="utf-8")
        for path in sorted(scss.rglob("*.scss")) if scss else ():
            target = tree / path.relative_to(scss)
            target.parent.mkdir(parents=True, exist_ok=True)
            text = path.read_text(encoding="utf-8")
            target.write_text(loud_comments(text) if loud and path.stem not in VARIABLE_HOOKS
                              else text, encoding="utf-8")
        (tree / "td/_oink_legacy_main.scss").write_text(legacy_entry(), encoding="utf-8")
        (tree / "oink-legacy.scss").write_text("@import 'td/oink_legacy_main';\n", encoding="utf-8")
        mounts = [ROOT / "assets", site / "tree"]
        (site / "layouts").mkdir()
        (site / "layouts/home.html").write_text(LAYOUT, encoding="utf-8")
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\n"
            "disableKinds: [page, section, taxonomy, term, rss, sitemap, robotstxt, 404]\n"
            "module:\n  mounts:\n"
            + "".join(f"    - source: {mount}\n      target: assets\n" for mount in mounts)
            + f"params:\n  transpiler: {transpiler}\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(GOWORK="off", HUGO_MODULE_WORKSPACE="off",
                   HUGO_RESOURCEDIR=str(site / "resources"))
        env.pop("HUGO_MODULE_REPLACEMENTS", None)
        command = [hugo, "--source", str(site), "--destination", str(site / "public"),
                   "--cacheDir", str(site / "cache"), "--ignoreCache", "--noBuildLock",
                   "--logLevel", "warn"]
        result = subprocess.run(command, env=env, text=True, capture_output=True,
                                timeout=BUILD_TIMEOUT)
        output = result.stdout + result.stderr
        if result.returncode or any(line.startswith("ERROR") for line in output.splitlines()):
            raise RuntimeError(output)
        return (site / "public/scss/oink-legacy.css").read_text(encoding="utf-8")


# --- Command -----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--site", required=True, type=Path, help="site root containing assets/scss/")
    parser.add_argument("--write", action="store_true", help="write assets/css/project.css")
    parser.add_argument("--hugo", help="Hugo that runs the compiler; default: hugo, then "
                                       "hugo-0.169.0, whichever has LibSass")
    parser.add_argument("--transpiler", choices=("libsass", "dartsass"), default="libsass")
    args = parser.parse_args()
    hugo = find_compiler(args.hugo, args.transpiler)
    site = args.site.expanduser().resolve()
    scss = site / "assets/scss"
    hooks = [name for name in HOOKS if (scss / f"{name}.scss").is_file()]
    if not hooks:
        print(f"{site}: no retired SCSS hook under assets/scss/; nothing to convert")
        return 0
    target = site / "assets/css/project.css"
    if target.exists():
        raise SystemExit(f"{target} already exists; merge by hand or move it aside first")

    try:
        theme = compile_legacy(hugo, args.transpiler, None)
        compiled = compile_legacy(hugo, args.transpiler, scss)
    except RuntimeError as error:
        raise SystemExit(f"Sass build failed:\n{error}")
    project, report, problems = convert(theme, compiled)
    comments = "kept"
    try:
        loud, loud_report, loud_problems = convert(
            theme, compile_legacy(hugo, args.transpiler, scss, loud=True))
        # Trust the commented variant only when it matches the original build.
        if not equivalent(parse(theme), parse(loud), parse(compiled)) and not loud_problems:
            project, report = loud, loud_report
        else:
            comments = "dropped: // comments changed the compiled result"
    except RuntimeError:
        comments = "dropped: the sources did not compile with // comments made loud"

    print(f"{site}")
    print(f"  hooks: {', '.join(name + '.scss' for name in hooks)}")
    print(f"  theme rules changed by Sass variables: {report.changed_rules} "
          f"({report.changed_decls} declarations)")
    print(f"  site rules and at-rules: {report.site_rules}")
    print(f"  // comments: {comments}")
    if report.dead:
        print(f"  skipped {report.dead} changed declarations that a later theme rule overrides")
    if report.scoped:
        print(f"  scoped {report.scoped} declarations away from later theme rules of equal "
              "specificity, such as the visual presets")
    for item in report.extended:
        print(f"  REVIEW @extend now follows the theme stylesheet: {item}")
    for item in report.order:
        print(f"  REVIEW cascade order: {item}")
    for item in report.removed:
        print(f"  REVIEW theme output absent with the site's variables; CSS cannot remove it: {item}")
    for item in problems:
        print(f"  REVIEW not equivalent: {item}")
    print(f"  project.css: {len(project.encode('utf-8'))} bytes, {project.count(chr(10))} lines")
    if args.write and project:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(project, encoding="utf-8")
        print(f"  wrote {target.relative_to(site)}; review it, then delete "
              + ", ".join(f"assets/scss/{name}.scss" for name in hooks))
    elif not args.write:
        print("  dry run; pass --write to create assets/css/project.css")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
