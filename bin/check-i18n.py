#!/usr/bin/env python3
"""Check translation key parity, or append explicit English fallbacks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "i18n"
KEY = re.compile(r"^([A-Za-z0-9_]+):")
BRACED_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
PRINTF_PLACEHOLDER = re.compile(r"(?<!%)%(?:[0-9]+\$)?[A-Za-z]")


def translation_blocks(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = KEY.match(line)
        if match:
            starts.append((index, match.group(1)))

    order = [key for _, key in starts]
    blocks: dict[str, str] = {}
    for offset, (start, key) in enumerate(starts):
        end = starts[offset + 1][0] if offset + 1 < len(starts) else len(lines)
        blocks[key] = "".join(lines[start:end])
    return order, blocks


def placeholders(block: str) -> tuple[list[str], list[str]]:
    """Return the runtime placeholders used by a translation block."""

    return (
        sorted(BRACED_PLACEHOLDER.findall(block)),
        sorted(PRINTF_PLACEHOLDER.findall(block)),
    )


def sync_fallbacks() -> None:
    generic_chinese = I18N / "zh.yaml"
    if not generic_chinese.exists():
        generic_chinese.write_text(
            "# Generic Chinese defaults to Simplified Chinese; use zh-tw for Traditional Chinese.\n"
            + (I18N / "zh-cn.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    english_order, english = translation_blocks(I18N / "en.yaml")
    for path in sorted(I18N.glob("*.yaml")):
        if path.name in {"en.yaml", "zh.yaml"}:
            continue
        _, translated = translation_blocks(path)
        missing = [key for key in english_order if key not in translated]
        if not missing:
            continue
        with path.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n# Explicit English fallbacks for untranslated OINK UI strings.\n"
                "# Replace these values with reviewed translations when available.\n"
            )
            for key in missing:
                stream.write(english[key])


def check() -> int:
    english_order, english_blocks = translation_blocks(I18N / "en.yaml")
    english = set(english_order)
    failed = False
    for path in sorted(I18N.glob("*.yaml")):
        order, blocks = translation_blocks(path)
        keys = set(order)
        missing = sorted(english - keys)
        extra = sorted(keys - english)
        duplicates = sorted({key for key in order if order.count(key) > 1})
        if missing or extra or duplicates:
            failed = True
            print(path.relative_to(ROOT))
            if missing:
                print(f"  missing: {', '.join(missing)}")
            if extra:
                print(f"  extra: {', '.join(extra)}")
            if duplicates:
                print(f"  duplicate: {', '.join(duplicates)}")
        for key in sorted(english & keys):
            expected = placeholders(english_blocks[key])
            actual = placeholders(blocks[key])
            if actual != expected:
                failed = True
                print(path.relative_to(ROOT))
                print(
                    f"  placeholder mismatch for {key}: "
                    f"expected {expected}, found {actual}"
                )
    if failed:
        return 1
    print(f"i18n key parity OK: {len(list(I18N.glob('*.yaml')))} locales, {len(english)} keys")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sync",
        action="store_true",
        help="append missing English fallback blocks before checking",
    )
    args = parser.parse_args()
    if args.sync:
        sync_fallbacks()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
