#!/usr/bin/env python3
"""Validate the checked-in third-party inventory and its file hashes."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "VENDOR.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PREMINIFIED_STANDALONE_ASSETS = {
    "third_party/asciinema/asciinema-player.min.js": "asciinemaJS",
    "third_party/infographic/infographic.min.js": "infographicJS",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def repository_file(value: Any, label: str, errors: list[str]) -> Path | None:
    if not nonempty_string(value):
        errors.append(f"{label} must be a nonempty repository-relative path")
        return None

    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{label} escapes the repository: {value}")
        return None

    candidate = ROOT / relative
    if candidate.is_symlink():
        errors.append(f"{label} must not be a symbolic link: {value}")
        return None
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        errors.append(f"{label} escapes the repository: {value}")
        return None

    if not resolved.is_file():
        errors.append(f"{label} does not exist as a file: {value}")
        return None
    return resolved


def repository_directory(value: Any, label: str, errors: list[str]) -> Path | None:
    if not nonempty_string(value):
        errors.append(f"{label} must be a nonempty repository-relative path")
        return None

    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{label} escapes the repository: {value}")
        return None

    candidate = ROOT / relative
    if candidate.is_symlink():
        errors.append(f"{label} must not be a symbolic link: {value}")
        return None
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        errors.append(f"{label} escapes the repository: {value}")
        return None

    if not resolved.is_dir():
        errors.append(f"{label} does not exist as a directory: {value}")
        return None
    return resolved


def tree_digest(root: Path) -> tuple[int, str]:
    """Hash file names, lengths, and bytes for a complete vendored tree."""

    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    for path in files:
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return len(files), digest.hexdigest()


def main() -> int:
    errors: list[str] = []
    try:
        document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Vendor inventory check failed: {error}", file=sys.stderr)
        return 1

    require(isinstance(document, dict), "manifest root must be an object", errors)
    if not isinstance(document, dict):
        document = {}
    require(document.get("schema") == 1, "schema must be 1", errors)
    require(document.get("hash") == "sha256", "hash must be sha256", errors)
    generated = document.get("generated")
    try:
        generated_date = date.fromisoformat(generated) if isinstance(generated, str) else None
    except ValueError:
        generated_date = None
    require(
        generated_date is not None and generated == generated_date.isoformat(),
        "generated must be an ISO 8601 calendar date",
        errors,
    )
    if generated_date is not None:
        require(generated_date <= date.today(), "generated must not be in the future", errors)

    trees = document.get("trees")
    require(
        isinstance(trees, list) and bool(trees),
        "trees must be a nonempty array",
        errors,
    )
    if not isinstance(trees, list):
        trees = []

    tree_paths: set[str] = set()
    checked_tree_files = 0
    for index, tree in enumerate(trees):
        label = f"trees[{index}]"
        if not isinstance(tree, dict):
            errors.append(f"{label} must be an object")
            continue
        path_value = tree.get("path")
        expected_files = tree.get("files")
        expected_digest = tree.get("sha256")
        require(
            nonempty_string(path_value),
            f"{label}.path must be a nonempty string",
            errors,
        )
        if nonempty_string(path_value):
            require(
                path_value not in tree_paths,
                f"duplicate vendored tree path: {path_value}",
                errors,
            )
            tree_paths.add(path_value)
        require(
            isinstance(expected_files, int) and not isinstance(expected_files, bool)
            and expected_files > 0,
            f"{label}.files must be a positive integer",
            errors,
        )
        require(
            isinstance(expected_digest, str)
            and SHA256.fullmatch(expected_digest) is not None,
            f"{label}.sha256 must be 64 lowercase hexadecimal characters",
            errors,
        )
        path = repository_directory(path_value, f"{label}.path", errors)
        if (
            path is None
            or not isinstance(expected_files, int)
            or isinstance(expected_files, bool)
            or not isinstance(expected_digest, str)
            or SHA256.fullmatch(expected_digest) is None
        ):
            continue
        symlinks = sorted(
            candidate.relative_to(ROOT).as_posix()
            for candidate in path.rglob("*")
            if candidate.is_symlink()
        )
        require(
            not symlinks,
            f"{path_value} contains symbolic links: {', '.join(symlinks)}",
            errors,
        )
        if symlinks:
            continue
        actual_files, actual_digest = tree_digest(path)
        checked_tree_files += actual_files
        require(
            actual_files == expected_files,
            f"file-count mismatch for {path_value}: "
            f"manifest {expected_files}, actual {actual_files}",
            errors,
        )
        require(
            actual_digest == expected_digest,
            f"tree SHA-256 mismatch for {path_value}: "
            f"manifest {expected_digest}, actual {actual_digest}",
            errors,
        )

    dependencies = document.get("dependencies")
    require(
        isinstance(dependencies, list) and bool(dependencies),
        "dependencies must be a nonempty array",
        errors,
    )
    if not isinstance(dependencies, list):
        dependencies = []

    names: set[str] = set()
    artifact_hashes: dict[str, str] = {}
    checked_artifacts: set[str] = set()
    checked_licenses: set[str] = set()

    for index, dependency in enumerate(dependencies):
        label = f"dependencies[{index}]"
        if not isinstance(dependency, dict):
            errors.append(f"{label} must be an object")
            continue

        for field in ("name", "version", "source", "license"):
            require(
                nonempty_string(dependency.get(field)),
                f"{label}.{field} must be a nonempty string",
                errors,
            )

        source = dependency.get("source")
        if nonempty_string(source):
            parsed_source = urlsplit(source)
            require(
                parsed_source.scheme == "https" and bool(parsed_source.netloc)
                and parsed_source.username is None and parsed_source.password is None,
                f"{label}.source must be an HTTPS URL without credentials",
                errors,
            )

        name = dependency.get("name")
        if nonempty_string(name):
            require(name not in names, f"duplicate dependency name: {name}", errors)
            names.add(name)

        license_files = dependency.get("licenseFiles")
        require(
            isinstance(license_files, list) and bool(license_files),
            f"{label}.licenseFiles must be a nonempty array",
            errors,
        )
        if isinstance(license_files, list):
            for license_index, value in enumerate(license_files):
                path = repository_file(
                    value,
                    f"{label}.licenseFiles[{license_index}]",
                    errors,
                )
                if path is not None:
                    checked_licenses.add(path.relative_to(ROOT).as_posix())

        artifacts = dependency.get("artifacts")
        require(
            isinstance(artifacts, list) and bool(artifacts),
            f"{label}.artifacts must be a nonempty array",
            errors,
        )
        if not isinstance(artifacts, list):
            continue

        dependency_paths: set[str] = set()
        for artifact_index, artifact in enumerate(artifacts):
            artifact_label = f"{label}.artifacts[{artifact_index}]"
            if not isinstance(artifact, dict):
                errors.append(f"{artifact_label} must be an object")
                continue

            value = artifact.get("path")
            digest = artifact.get("sha256")
            require(
                nonempty_string(value),
                f"{artifact_label}.path must be a nonempty string",
                errors,
            )
            require(
                isinstance(digest, str) and SHA256.fullmatch(digest) is not None,
                f"{artifact_label}.sha256 must be 64 lowercase hexadecimal characters",
                errors,
            )
            if not nonempty_string(value):
                continue

            require(
                value not in dependency_paths,
                f"{label} lists artifact more than once: {value}",
                errors,
            )
            dependency_paths.add(value)

            path = repository_file(value, f"{artifact_label}.path", errors)
            if path is None or not isinstance(digest, str) or not SHA256.fullmatch(digest):
                continue

            prior = artifact_hashes.get(value)
            require(
                prior is None or prior == digest,
                f"shared artifact has conflicting hashes: {value}",
                errors,
            )
            artifact_hashes[value] = digest

            if value in checked_artifacts:
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            require(
                actual == digest,
                f"SHA-256 mismatch for {value}: manifest {digest}, actual {actual}",
                errors,
            )
            checked_artifacts.add(value)

    scripts_template = (ROOT / "layouts/_partials/scripts.html").read_text(
        encoding="utf-8"
    )
    for asset, resource_variable in PREMINIFIED_STANDALONE_ASSETS.items():
        require(
            f'<script src="{{{{ ${resource_variable}.RelPermalink }}}}"'
            in scripts_template,
            f"pre-minified runtime must be published as a standalone script: {asset}",
            errors,
        )
        require(
            f'append (resources.Get "{asset}")' not in scripts_template,
            f"pre-minified runtime must not enter Hugo's minified JS concat: {asset}",
            errors,
        )

    if errors:
        print("Vendor inventory check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Vendor inventory check passed: "
        f"{len(dependencies)} dependencies, {len(checked_artifacts)} artifacts, "
        f"{len(checked_licenses)} license files, {checked_tree_files} tree files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
