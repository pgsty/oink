#!/usr/bin/env python3
"""Validate an OINK-generated EPUB package and every internal reference."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit
from zipfile import BadZipFile, ZIP_STORED, ZipFile


CONTAINER_NS = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}
CHAPTER_RE = re.compile(r"EPUB/text/ch\d+\.xhtml\Z")


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def archive_target(source: str, path: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(path)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("epub", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    try:
        book_manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"EPUB validation failed: cannot read BookManifest: {error}", file=sys.stderr)
        return 1
    expected_pages = book_manifest.get("pages", [])
    expected_targets = {
        target["id"]: target
        for page in expected_pages
        for target in page.get("targets", [])
    }
    expected_page_ids = {page["aggregateId"] for page in expected_pages}

    try:
        archive = ZipFile(args.epub)
    except (FileNotFoundError, BadZipFile) as error:
        print(f"EPUB validation failed: {error}", file=sys.stderr)
        return 1

    chapter_count = 0
    with archive:
        infos = archive.infolist()
        names = set(archive.namelist())
        if not infos or infos[0].filename != "mimetype" or infos[0].compress_type != ZIP_STORED:
            errors.append("mimetype must be the first, uncompressed archive entry")
        if "mimetype" not in names or archive.read("mimetype") != b"application/epub+zip":
            errors.append("mimetype content is not application/epub+zip")

        rootfile = ""
        try:
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            rootfile_node = container.find(".//container:rootfile", CONTAINER_NS)
            rootfile = rootfile_node.attrib.get("full-path", "") if rootfile_node is not None else ""
        except (KeyError, ET.ParseError) as error:
            errors.append(f"invalid META-INF/container.xml: {error}")
        if not rootfile or rootfile not in names:
            errors.append(f"package document is missing: {rootfile or '(unspecified)'}")

        package_manifest: dict[str, str] = {}
        if rootfile in names:
            try:
                package = ET.fromstring(archive.read(rootfile))
                package_dir = posixpath.dirname(rootfile)
                for item in package.findall(".//opf:manifest/opf:item", OPF_NS):
                    identifier = item.attrib.get("id", "")
                    href = item.attrib.get("href", "")
                    target = posixpath.normpath(posixpath.join(package_dir, unquote(href)))
                    if not identifier or identifier in package_manifest:
                        errors.append(f"invalid or duplicate package manifest id: {identifier!r}")
                    else:
                        package_manifest[identifier] = target
                    if target not in names:
                        errors.append(f"package manifest target is missing: {href}")
                for itemref in package.findall(".//opf:spine/opf:itemref", OPF_NS):
                    identifier = itemref.attrib.get("idref", "")
                    if identifier not in package_manifest:
                        errors.append(f"spine idref is not in package manifest: {identifier!r}")
            except ET.ParseError as error:
                errors.append(f"invalid package document {rootfile}: {error}")

        xhtml_names = sorted(name for name in names if name.endswith(".xhtml"))
        roots: dict[str, ET.Element] = {}
        ids: dict[str, set[str]] = {}
        found_ids: Counter[str] = Counter()
        found_targets: dict[str, tuple[str, str]] = {}
        forbidden = {"button", "dialog", "embed", "iframe", "object", "script", "template"}
        for name in xhtml_names:
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError as error:
                errors.append(f"invalid XHTML {name}: {error}")
                continue
            roots[name] = root
            all_ids = [node.attrib["id"] for node in root.iter() if "id" in node.attrib]
            ids[name] = set(all_ids)
            found_ids.update(all_ids)
            for node in root.iter():
                identifier = node.attrib.get("id", "")
                if identifier in expected_targets:
                    found_targets[identifier] = (
                        node.attrib.get("data-td-book-kind", ""),
                        node.attrib.get("data-td-book-num", ""),
                    )
            duplicates = [identifier for identifier, count in Counter(all_ids).items() if count > 1]
            if duplicates:
                errors.append(f"{name}: duplicate ids: {', '.join(duplicates[:5])}")
            bad_tags = sorted({local_name(node.tag) for node in root.iter()} & forbidden)
            if bad_tags:
                errors.append(f"{name}: interactive HTML survived: {', '.join(bad_tags)}")

        for name, root in roots.items():
            for node in root.iter():
                for raw_attr, value in node.attrib.items():
                    if local_name(raw_attr) not in {"href", "src"} or not value:
                        continue
                    parsed = urlsplit(value)
                    if parsed.scheme or parsed.netloc:
                        if parsed.scheme not in {"http", "https", "mailto", "tel", "data"}:
                            errors.append(f"{name}: unsafe external URL {value!r}")
                        continue
                    target = archive_target(name, parsed.path) if parsed.path else name
                    if target not in names:
                        errors.append(f"{name}: missing internal target {value!r}")
                    elif parsed.fragment and target in ids:
                        fragment = unquote(parsed.fragment)
                        if fragment not in ids[target]:
                            errors.append(f"{name}: missing fragment {value!r}")

        chapter_count = sum(bool(CHAPTER_RE.fullmatch(name)) for name in names)
        if chapter_count != len(expected_pages):
            errors.append(f"expected {len(expected_pages)} content chapters, found {chapter_count}")
        missing_targets = sorted(set(expected_targets) - set(found_ids))
        if missing_targets:
            errors.append(f"numbered targets missing from EPUB: {', '.join(missing_targets[:10])}")
        mismatched_targets = [
            identifier
            for identifier, target in expected_targets.items()
            if identifier in found_targets
            and found_targets[identifier] != (str(target.get("kind", "")), str(target.get("num", "")))
        ]
        if mismatched_targets:
            errors.append(
                "numbered target semantics differ from BookManifest: "
                + ", ".join(sorted(mismatched_targets)[:10])
            )
        missing_pages = sorted(expected_page_ids - set(found_ids))
        if missing_pages:
            errors.append(f"Book page anchors missing from EPUB: {', '.join(missing_pages[:10])}")

    summary = (
        f"EPUB chapters={chapter_count} targets={len(expected_targets)} "
        f"xhtml={len(roots)} entries={len(names)}"
    )
    if errors:
        print(f"{summary} errors={len(errors)}", file=sys.stderr)
        for error in errors[:100]:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"{summary} errors=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
