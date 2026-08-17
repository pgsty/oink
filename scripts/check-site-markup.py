#!/usr/bin/env python3
"""Validate the resolved Goldmark settings required by OINK native forms.

Hugo does not merge a theme module's ``markup`` configuration into a consuming
site. This command asks Hugo for the site's fully merged configuration instead
of guessing across YAML/TOML files and environment overlays.

    python3 scripts/check-site-markup.py --site /path/to/site
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def nested(config: dict, *keys: str):
    value = config
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    site = args.site.resolve()
    if not site.is_dir():
        print(f"site directory not found: {site}", file=sys.stderr)
        return 2

    result = subprocess.run(
        [
            args.hugo,
            "config",
            "--source",
            str(site),
            "--printZero",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout + result.stderr, file=sys.stderr, end="")
        return 2
    try:
        config = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"could not parse `hugo config` JSON: {exc}", file=sys.stderr)
        return 2

    required = (
        (
            ("markup", "goldmark", "renderer", "unsafe"),
            True,
            "markup.goldmark.renderer.unsafe: true",
        ),
        (
            ("markup", "goldmark", "parser", "attribute", "block"),
            True,
            "markup.goldmark.parser.attribute.block: true",
        ),
        (
            ("markup", "goldmark", "parser", "wrapstandaloneimagewithinparagraph"),
            False,
            "markup.goldmark.parser.wrapStandAloneImageWithinParagraph: false",
        ),
    )
    missing = [label for keys, expected, label in required if nested(config, *keys) is not expected]
    if missing:
        print(f"OINK Goldmark preflight failed for {site}:")
        for label in missing:
            print(f"  required: {label}")
        return 1

    print(f"OINK Goldmark preflight passed: {site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
