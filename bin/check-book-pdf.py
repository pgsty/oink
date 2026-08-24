#!/usr/bin/env python3
"""Validate an OINK whole-Book PDF with Poppler and BookManifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata


def normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--pdfinfo", default="pdfinfo")
    parser.add_argument("--pdftotext", default="pdftotext")
    args = parser.parse_args()

    errors: list[str] = []
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        pages = manifest.get("pages", [])
        if manifest.get("schemaVersion") != 1 or not isinstance(pages, list) or not pages:
            errors.append("BookManifest schemaVersion/pages are invalid")
    except (OSError, json.JSONDecodeError) as error:
        print(f"PDF validation failed: cannot read BookManifest: {error}", file=sys.stderr)
        return 1

    try:
        prefix = args.pdf.read_bytes()[:5]
    except OSError as error:
        print(f"PDF validation failed: {error}", file=sys.stderr)
        return 1
    if prefix != b"%PDF-":
        errors.append("file does not start with a PDF header")

    pdfinfo = shutil.which(args.pdfinfo)
    pdftotext = shutil.which(args.pdftotext)
    if pdfinfo is None:
        errors.append(f"pdfinfo executable was not found: {args.pdfinfo}")
    if pdftotext is None:
        errors.append(f"pdftotext executable was not found: {args.pdftotext}")

    page_count = 0
    info = ""
    if pdfinfo:
        result = subprocess.run(
            [pdfinfo, str(args.pdf)], capture_output=True, text=True, check=False
        )
        info = result.stdout
        if result.returncode != 0:
            errors.append(f"pdfinfo failed: {result.stdout}{result.stderr}".strip())
        else:
            match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.MULTILINE)
            page_count = int(match.group(1)) if match else 0
            if page_count < len(pages):
                errors.append(
                    f"expected at least {len(pages)} PDF pages for the Book sequence, found {page_count}"
                )
            size = re.search(
                r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts", info, re.MULTILINE
            )
            if size is None:
                errors.append("pdfinfo did not report a page size")
            else:
                width, height = map(float, size.groups())
                if abs(width - 595.28) > 2 or abs(height - 841.89) > 2:
                    errors.append(f"PDF page size is not A4 portrait: {width:g} x {height:g} pts")
            encrypted = re.search(r"^Encrypted:\s+(\S+)", info, re.MULTILINE)
            if encrypted and encrypted.group(1).lower() != "no":
                errors.append("PDF unexpectedly requires encryption")
            tagged = re.search(r"^Tagged:\s+(\S+)", info, re.MULTILINE)
            if tagged is None or tagged.group(1).lower() != "yes":
                errors.append("PDF is not tagged for accessible reading order")

    found_titles = 0
    extracted_pages: list[str] = []
    if pdftotext:
        result = subprocess.run(
            [pdftotext, "-layout", str(args.pdf), "-"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(
                "pdftotext failed: "
                + (result.stdout + result.stderr).decode("utf-8", errors="replace").strip()
            )
        else:
            extracted = result.stdout.decode("utf-8", errors="replace")
            extracted_pages = extracted.split("\f")
            if extracted_pages and not extracted_pages[-1].strip():
                extracted_pages.pop()
            text = normalized_text(extracted)
            missing_titles = [
                str(page.get("title", ""))
                for page in pages
                if page.get("title") and normalized_text(str(page["title"])) not in text
            ]
            found_titles = len(pages) - len(missing_titles)
            if missing_titles:
                errors.append(
                    "Book page titles missing from PDF text: "
                    + ", ".join(missing_titles[:10])
                )
            if len(extracted_pages) != page_count:
                errors.append(
                    f"pdftotext found {len(extracted_pages)} pages but pdfinfo found {page_count}"
                )
            elif page_count:
                for page_number in sorted({1, (page_count + 1) // 2, page_count}):
                    lines = [
                        normalized_text(line)
                        for line in extracted_pages[page_number - 1].splitlines()
                        if normalized_text(line)
                    ]
                    if not lines or lines[-1] != str(page_number):
                        errors.append(
                            f"PDF page {page_number} has no bottom page-number margin"
                        )

    summary = (
        f"PDF pages={page_count} book-pages={len(pages)} "
        f"titles={found_titles}/{len(pages)} bytes={args.pdf.stat().st_size}"
    )
    if errors:
        print(f"{summary} errors={len(errors)}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"{summary} errors=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
