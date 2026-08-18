#!/usr/bin/env python3
"""Keep OINK text fonts behind defined semantic typography roles."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SCSS_ROOT = ROOT / "assets" / "scss"
TD_ROOT = SCSS_ROOT / "td"
LAYOUT_ROOT = ROOT / "layouts"
FAMILIES = ("Chakra Petch", "IBM Plex Mono")
# Inter is matched only as a quoted family literal: the bare word is ordinary
# English ("interactive", "internal") in comments and selectors.
FAMILY_PATTERN = re.compile(
    "|".join(map(re.escape, FAMILIES)) + r"""|['"]Inter['"]""", re.IGNORECASE
)
REVERSE_PATTERN = re.compile(r"--bs-[\w-]+\s*:\s*var\(--td-")
FAMILY_NAME_ALLOWLIST = {
    TD_ROOT / "_brand.scss",  # Local @font-face declarations.
    TD_ROOT / "_tokens-typography.scss",  # Public role defaults.
    TD_ROOT / "_variables_forward.scss",  # Bootstrap mono compatibility.
    TD_ROOT / "_variables.scss",
}
PUBLIC_ROLES = (
    "ui-font-family",
    "body-font-family",
    "heading-font-family",
    "code-font-family",
    "display-font-family",
    "meta-font-family",
    "print-font-family",
)
FONT_FAMILY_DECLARATION = re.compile(
    r"(?<![-\w])font-family\s*:\s*(?P<value>[^;]+);"
)
SEMANTIC_VALUE = re.compile(
    r"^var\(--td-[\w-]*font-family(?:\s*,[^)]*)?\)(?:\s*!important)?$"
)
LITERAL_DECLARATION_ALLOWLIST = {
    TD_ROOT / "_brand.scss": {"'Chakra Petch'", "'IBM Plex Mono'"},
    TD_ROOT / "_landing.scss": {"Georgia, serif"},  # Decorative quote glyph.
}
SPECIAL_DECLARATION_VALUES = {
    "inherit",
    "$td-font-awesome-font-name",
    "var(--td-term-font-family)",  # Asciinema player component alias.
}


def main() -> int:
    errors: list[str] = []
    sources: dict[Path, str] = {}
    for path in sorted(SCSS_ROOT.rglob("*.scss")):
        source = path.read_text()
        sources[path] = source
        for number, line in enumerate(source.splitlines(), 1):
            if path not in FAMILY_NAME_ALLOWLIST and FAMILY_PATTERN.search(line):
                errors.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")

        for match in REVERSE_PATTERN.finditer(source):
            number = source.count("\n", 0, match.start()) + 1
            errors.append(
                f"{path.relative_to(ROOT)}:{number}: Bootstrap tokens must "
                "not reference OINK semantic tokens"
            )

        for match in FONT_FAMILY_DECLARATION.finditer(source):
            value = " ".join(match.group("value").split())
            allowed_literals = LITERAL_DECLARATION_ALLOWLIST.get(path, set())
            if (
                value in SPECIAL_DECLARATION_VALUES
                or value in allowed_literals
                or SEMANTIC_VALUE.fullmatch(value)
            ):
                continue
            number = source.count("\n", 0, match.start()) + 1
            errors.append(
                f"{path.relative_to(ROOT)}:{number}: font-family must use a "
                f"defined semantic role (found {value})"
            )

    for path in sorted(LAYOUT_ROOT.rglob("*.html")):
        source = path.read_text()
        if FAMILY_PATTERN.search(source):
            errors.append(
                f"{path.relative_to(ROOT)}: bundled text faces belong in "
                "typography role defaults, not layouts"
            )
        if re.search(r"<html(?:\s|>)", source, re.IGNORECASE) and (
            "data-td-typography=" not in source
        ):
            errors.append(
                f"{path.relative_to(ROOT)}: root layout missing "
                "data-td-typography"
            )

    token_path = TD_ROOT / "_tokens-typography.scss"
    token_source = sources[token_path]
    for role in PUBLIC_ROLES:
        token = f"--td-{role}"
        count = len(re.findall(rf"{re.escape(token)}\s*:", token_source))
        if count == 0:
            errors.append(f"{token_path.relative_to(ROOT)}: missing {token}")

    all_source = "\n".join(sources.values())
    definitions = set(re.findall(r"--(td-[\w-]*font-family)\s*:", all_source))
    references = set(re.findall(r"var\(--(td-[\w-]*font-family)", all_source))
    for token in sorted(references - definitions):
        errors.append(f"undefined typography token --{token}")

    legacy_seeds = (
        ("--td-heading-font-family", "$headings-font-family"),
        ("--td-code-font-family", "$font-family-code"),
        ("--td-print-font-family", "var(--td-body-font-family)"),
    )
    for token, variable in legacy_seeds:
        if token not in token_source or variable not in token_source:
            errors.append(
                f"{token_path.relative_to(ROOT)}: {token} must preserve {variable}"
            )

    system_match = re.search(
        r"\[data-td-typography='system'\]\s*\{(?P<body>.*?)\n\}",
        token_source,
        re.DOTALL,
    )
    system_requirements = (
        "--bs-font-monospace:",
        "--td-display-font-family:",
        "--td-meta-font-family:",
        "--td-print-font-family:",
    )
    if not system_match:
        errors.append(f"{token_path.relative_to(ROOT)}: missing system preset")
    else:
        system_source = system_match.group("body")
        if FAMILY_PATTERN.search(system_source):
            errors.append(
                f"{token_path.relative_to(ROOT)}: system preset must not "
                "reference bundled text faces"
            )
        for requirement in system_requirements:
            if requirement not in system_source:
                errors.append(
                    f"{token_path.relative_to(ROOT)}: system preset missing "
                    f"{requirement.removesuffix(':')}"
                )

    if errors:
        print("Typography token check failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print("Typography token check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
