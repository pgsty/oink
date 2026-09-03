#!/usr/bin/env python3
"""Check the complete, native OINK locale catalogs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "i18n"
KEY = re.compile(r"^([A-Za-z0-9_]+):")
BRACED_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
GO_TEMPLATE_PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}")
PRINTF_PLACEHOLDER = re.compile(r"(?<!%)%(?:[0-9]+\$)?[A-Za-z]")
BIDI_CONTROL = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
# Locale filenames in google/docsy@64f51c5bde2abd2e8a001cb31b32656f5800ca56.
DOCSY_LOCALES = {
    "ar", "az", "bg", "bn", "de", "en", "es", "et", "fa", "fi", "fr",
    "he", "hi", "hu", "it", "ja", "ko", "nl", "no", "oc", "pl",
    "pt-br", "ro", "ru", "sr-cyrl", "sr-latn", "sv", "tr", "uk",
    "zh-cn", "zh-tw",
}
OINK_LOCALES = DOCSY_LOCALES | {"zh"}
CALLOUT_KEYS = tuple(
    f"callout_{name}"
    for name in (
        "caution", "important", "note", "tip", "warning", "success",
        "danger", "question", "example", "quote", "details",
    )
)
FALLBACK_MARKERS = (
    "Replace these values with reviewed translations when available.",
    "Explicit English fallbacks for untranslated OINK UI strings.",
)
UNIVERSAL_IDENTICAL = {"ui_preview_source", "ui_list_separator"}
REVIEWED_IDENTICAL = {
    "de": {"callout_details", "ui_theme_auto", "post_meta_in"},
    "es": {"post_translated_original", "post_reading_minutes", "feedback_negative"},
    "et": {"post_reading_minutes"},
    "fi": {"post_reading_minutes"},
    "fr": {
        "callout_important", "callout_note", "callout_danger", "callout_question",
        "ui_palette_actions", "ui_palette_pages", "ui_modules_title",
        "ui_module_title", "ui_page_actions", "ui_release_source",
        "post_upstream_notice", "post_translated_original", "post_reading_minutes",
        "book_figure",
    },
    "it": {
        "ui_home", "ui_tag_title", "ui_share_email", "ui_assets_file",
        "post_meta_in", "post_reading_minutes", "feedback_negative",
    },
    "nl": {
        "callout_tip", "callout_details", "ui_home", "ui_tags_title",
        "ui_tag_title", "ui_modules_title", "ui_module_title",
        "ui_open_in_chatgpt", "ui_open_in_claude", "ui_tabs_label",
        "post_meta_in", "post_reading_minutes",
    },
    "no": {"ui_theme_auto", "post_reading_minutes"},
    "oc": {
        "callout_important", "callout_question", "post_translated_original",
        "post_reading_minutes", "contributors_count",
    },
    "pl": {"ui_tag_title", "ui_theme_auto", "post_reading_minutes"},
    "pt-br": {"post_translated_original", "post_reading_minutes"},
    "ro": {
        "callout_important", "ui_share_email", "post_translated_original",
        "post_reading_minutes",
    },
    "sr-latn": {"post_translated_original", "post_reading_minutes"},
    "sv": {"ui_theme_auto", "post_reading_minutes"},
}
SERBIAN_CYRILLIC = "АБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШабвгдђежзијклљмнњопрстћуфхцчџш"
SERBIAN_LATIN = (
    "A", "B", "V", "G", "D", "Đ", "E", "Ž", "Z", "I", "J", "K", "L", "Lj",
    "M", "N", "Nj", "O", "P", "R", "S", "T", "Ć", "U", "F", "H", "C", "Č",
    "Dž", "Š", "a", "b", "v", "g", "d", "đ", "e", "ž", "z", "i", "j", "k", "l",
    "lj", "m", "n", "nj", "o", "p", "r", "s", "t", "ć", "u", "f", "h", "c", "č",
    "dž", "š",
)
SERBIAN_TRANSLITERATION = str.maketrans(
    {char: replacement for char, replacement in zip(SERBIAN_CYRILLIC, SERBIAN_LATIN)}
)


class TranslationSpanParser(HTMLParser):
    """Collect the rendered text of the runtime check's translation spans."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}
        self._key: str | None = None
        self._parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "span" and self._key is None:
            key = dict(attrs).get("data-key")
            if key is not None:
                self._key = key
                self._parts = []

    def handle_data(self, data: str) -> None:
        if self._key is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._key is not None:
            self.values[self._key] = "".join(self._parts)
            self._key = None
            self._parts = []


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


def placeholders(block: str) -> tuple[list[str], list[str], list[str]]:
    """Return the runtime placeholders used by a translation block."""

    return (
        sorted(BRACED_PLACEHOLDER.findall(block)),
        sorted(GO_TEMPLATE_PLACEHOLDER.findall(block)),
        sorted(PRINTF_PLACEHOLDER.findall(block)),
    )


def scalar_value(block: str) -> str | None:
    """Read the simple scalar styles used by OINK without a YAML dependency."""

    lines = block.splitlines()
    value = lines[0].partition(":")[2].strip()
    if not value:
        return None
    if value.startswith('"'):
        try:
            parsed, end = json.JSONDecoder().raw_decode(value)
        except (json.JSONDecodeError, TypeError):
            return None
        trailing = value[end:]
        if trailing and not re.fullmatch(r"[ \t]+#.*", trailing):
            return None
        return parsed if isinstance(parsed, str) else None
    if value.startswith("'"):
        quoted = re.fullmatch(r"'((?:[^']|'')*)'(?:[ \t]+#.*)?", value)
        return quoted.group(1).replace("''", "'") if quoted else None
    if value.startswith("#"):
        return None
    value = re.sub(r"[ \t]+#.*$", "", value).rstrip()
    if not value:
        return None
    if value in {">", ">-", "|", "|-"}:
        return " ".join(line.strip() for line in lines[1:] if line[:1].isspace()).strip()
    return value


def check_hugo_runtime(
    keys: list[str], catalogs: dict[str, dict[str, str]]
) -> list[str]:
    """Render every key once in all supported locales."""

    hugo = shutil.which("hugo")
    if not hugo:
        return ["Hugo executable not found for the all-locale runtime check"]
    with tempfile.TemporaryDirectory(prefix="oink-i18n-") as directory:
        site = Path(directory)
        (site / "content").mkdir()
        (site / "layouts").mkdir()
        (site / "content/_index.md").write_text(
            "---\ntitle: i18n runtime fixture\n---\n",
            encoding="utf-8",
        )
        language_lines: list[str] = []
        for weight, locale in enumerate(["en", *sorted(OINK_LOCALES - {"en"})], 1):
            # Hugo 0.160.x cannot resolve a bare `locale: zh` while the regional
            # Chinese catalogs are present. A concrete locale is also what the
            # public OINK examples use for their generic `zh` language key.
            runtime_locale = "zh-CN" if locale == "zh" else locale
            language_lines.extend(
                [
                    f"  {locale}:\n",
                    f"    locale: {runtime_locale}\n",
                    f"    label: {locale}\n",
                    f"    weight: {weight}\n",
                ]
            )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.test/\n"
            "title: OINK i18n runtime fixture\n"
            "theme: oink\n"
            "defaultContentLanguage: en\n"
            "defaultContentLanguageInSubdir: false\n"
            "disableKinds: [taxonomy, term, RSS, sitemap, robotsTXT, '404']\n"
            "languages:\n"
            + "".join(language_lines),
            encoding="utf-8",
        )
        context = (
            'dict "Count" 2 "Minutes" 3 "Part" 1 "Total" 2 '
            '"Authors" "Author" "Section" "Section" "Version" "1.0" '
            '"Link" "latest" "work" "Work" "copyright" "Copyright" '
            '"license" "License" "notice" "Notice" "history" "History" '
            '"original" "Original"'
        )
        quoted_keys = " ".join(json.dumps(key) for key in keys)
        (site / "layouts/home.html").write_text(
            "<!doctype html><html lang=\"{{ .Site.Language.Lang }}\"><body>\n"
            f"{{{{ $ctx := {context} }}}}\n"
            f"{{{{ range $key := slice {quoted_keys} }}}}"
            "<span data-key=\"{{ $key }}\">{{ T $key $ctx }}</span>"
            "{{ end }}\n"
            "</body></html>\n",
            encoding="utf-8",
        )
        public = site / "public"
        try:
            result = subprocess.run(
                [
                    hugo,
                    "--source",
                    str(site),
                    "--themesDir",
                    str(ROOT.parent),
                    "--destination",
                    str(public),
                    "--printI18nWarnings",
                    "--panicOnWarning",
                ],
                text=True,
                capture_output=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return ["all-locale Hugo render exceeded 120 seconds"]
        if result.returncode:
            return [
                "all-locale Hugo render failed:\n"
                + (result.stdout + result.stderr)[-4000:]
            ]
        outputs = {
            locale: public
            / ("index.html" if locale == "en" else f"{locale}/index.html")
            for locale in OINK_LOCALES
        }
        missing_outputs = sorted(
            locale for locale, path in outputs.items() if not path.is_file()
        )
        if missing_outputs:
            return [f"all-locale Hugo render missed: {', '.join(missing_outputs)}"]
        wrong_values: list[str] = []
        for locale, path in outputs.items():
            parser = TranslationSpanParser()
            parser.feed(path.read_text(encoding="utf-8"))
            for key, expected in catalogs[locale].items():
                if any(placeholders(expected)):
                    continue
                if parser.values.get(key) != expected:
                    wrong_values.append(f"{locale}.{key}")
        if wrong_values:
            shown = ", ".join(sorted(wrong_values)[:20])
            suffix = " …" if len(wrong_values) > 20 else ""
            return [
                "all-locale Hugo render selected wrong catalog values: "
                + shown
                + suffix
            ]
    return []


def check() -> int:
    english_order, english_blocks = translation_blocks(I18N / "en.yaml")
    english = set(english_order)
    english_values = {key: scalar_value(block) for key, block in english_blocks.items()}
    failed = False
    paths = sorted(I18N.glob("*.yaml"))
    locales = {path.stem for path in paths}
    missing_locales = sorted(OINK_LOCALES - locales)
    extra_locales = sorted(locales - OINK_LOCALES)
    if missing_locales or extra_locales:
        failed = True
        print("i18n locale set")
        if missing_locales:
            print(f"  missing: {', '.join(missing_locales)}")
        if extra_locales:
            print(f"  extra: {', '.join(extra_locales)}")
    catalog_values: dict[str, dict[str, str]] = {}
    for path in paths:
        source = path.read_text(encoding="utf-8")
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
        markers = [marker for marker in FALLBACK_MARKERS if marker in source]
        if markers:
            failed = True
            print(path.relative_to(ROOT))
            print(f"  placeholder fallback markers: {', '.join(markers)}")
        values: dict[str, str] = {}
        for key, block in blocks.items():
            value = scalar_value(block)
            if value is None:
                failed = True
                print(path.relative_to(ROOT))
                print(f"  non-scalar or unsupported value for {key}")
                continue
            values[key] = value
            if BIDI_CONTROL.search(value):
                failed = True
                print(path.relative_to(ROOT))
                print(f"  hidden bidi control in {key}")
        catalog_values[path.stem] = values
        callout_labels: dict[str, list[str]] = {}
        for key in CALLOUT_KEYS:
            if key in values:
                callout_labels.setdefault(values[key], []).append(key)
        callout_collisions = [
            keys for keys in callout_labels.values() if len(keys) > 1
        ]
        if callout_collisions:
            failed = True
            print(path.relative_to(ROOT))
            for collision in callout_collisions:
                print(f"  duplicate callout labels: {', '.join(collision)}")
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
        if path.stem != "en":
            identical = {
                key for key, value in values.items()
                if key in english_values and value == english_values[key]
            }
            allowed = UNIVERSAL_IDENTICAL | REVIEWED_IDENTICAL.get(path.stem, set())
            unexpected = sorted(identical - allowed)
            if unexpected:
                failed = True
                print(path.relative_to(ROOT))
                print(f"  unreviewed English-identical values: {', '.join(unexpected)}")
    if catalog_values.get("zh") != catalog_values.get("zh-cn"):
        failed = True
        print("i18n/zh.yaml")
        print("  generic zh must match the Simplified Chinese zh-cn catalog")
    if "sr-cyrl" in catalog_values and "sr-latn" in catalog_values:
        mismatched = sorted(
            key for key, value in catalog_values["sr-cyrl"].items()
            if value.translate(SERBIAN_TRANSLITERATION)
            != catalog_values["sr-latn"].get(key)
        )
        if mismatched:
            failed = True
            print("i18n/sr-latn.yaml")
            print(f"  differs from standard sr-cyrl transliteration: {', '.join(mismatched)}")
    if not failed:
        runtime_errors = check_hugo_runtime(english_order, catalog_values)
        if runtime_errors:
            failed = True
            for error in runtime_errors:
                print(error)
    if failed:
        return 1
    print(
        f"i18n native catalogs OK: {len(paths)} locales, "
        f"{len(english)} keys, placeholders, reviewed cognates, and Hugo runtime"
    )
    return 0


def main() -> int:
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
