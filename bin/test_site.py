"""Shared paths and Hugo config arguments for the private fixture site."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
TEST_SITE = ROOT / "tests/site"


def fixture_config(*extra: Path) -> str:
    """Return the merged example + private-fixture config list."""

    configs = [EXAMPLE / "hugo.yaml", TEST_SITE / "hugo.yaml", *extra]
    return ",".join(str(path) for path in configs)


def fixture_config_args(*extra: Path) -> list[str]:
    return ["--config", fixture_config(*extra)]


def fixture_media_config(*extra: Path) -> str:
    """Return configs that add private media without replacing test content."""

    configs = [EXAMPLE / "hugo.yaml", TEST_SITE / "media.yaml", *extra]
    return ",".join(str(path) for path in configs)


def build_fixture_public(
    hugo: str,
    *extra_args: str,
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    """Build exampleSite with the private behaviour fixtures mounted."""

    destination = Path(tempfile.mkdtemp(prefix="oink-private-fixtures-")) / "public"
    result = subprocess.run(
        [
            hugo,
            "--source",
            str(EXAMPLE),
            "--themesDir",
            str(ROOT.parent),
            "--destination",
            str(destination),
            *fixture_config_args(),
            "--logLevel",
            "warn",
            *extra_args,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return destination, result
