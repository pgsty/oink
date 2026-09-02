"""Shared paths and Hugo config arguments for the regression fixture site."""

from __future__ import annotations

import atexit
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_SITE = ROOT / "tests/site"


def fixture_config(*extra: Path) -> str:
    """Return the fixture config followed by any test-specific overrides."""

    configs = [TEST_SITE / "hugo.yaml", *extra]
    return ",".join(str(path) for path in configs)


def fixture_config_args(*extra: Path) -> list[str]:
    return ["--config", fixture_config(*extra)]


def fixture_media_config(*extra: Path) -> str:
    """Return configs that keep fixture media while replacing test content."""

    configs = [TEST_SITE / "hugo.yaml", TEST_SITE / "media.yaml", *extra]
    return ",".join(str(path) for path in configs)


def build_fixture_public(
    hugo: str,
    *extra_args: str,
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    """Build the self-contained regression fixture."""

    # The caller reads from this directory for the rest of its run, so the
    # cleanup is deferred to interpreter exit rather than scoped with a
    # context manager. Without it every local check run left a complete site
    # build behind: hundreds of directories and gigabytes over a few weeks.
    temp = Path(tempfile.mkdtemp(prefix="oink-private-fixtures-"))
    atexit.register(shutil.rmtree, temp, ignore_errors=True)
    destination = temp / "public"
    result = subprocess.run(
        [
            hugo,
            "--source",
            str(TEST_SITE),
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


def checker_fixture_public(
    public: Path | None,
    hugo: str,
) -> tuple[Path, subprocess.CompletedProcess[str] | None]:
    """Reuse an explicit build, otherwise create a fresh strict fixture."""

    if public is not None:
        return public, None
    return build_fixture_public(hugo, "--printPathWarnings", "--panicOnWarning")
