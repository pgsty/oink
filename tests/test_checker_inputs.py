#!/usr/bin/env python3
"""Self-tests for fresh and explicitly reused checker input modes."""

from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

import test_site  # noqa: E402


class CheckerFixtureInputTests(unittest.TestCase):
    def test_shared_hugo_runner_sets_a_finite_timeout(self) -> None:
        completed = subprocess.CompletedProcess(["hugo", "version"], 0)
        with mock.patch.object(
            test_site.subprocess, "run", return_value=completed
        ) as run:
            result = test_site.run_hugo_process(
                ["hugo", "version"], capture_output=True, text=True
            )

        self.assertIs(result, completed)
        run.assert_called_once_with(
            ["hugo", "version"],
            timeout=test_site.HUGO_BUILD_TIMEOUT,
            capture_output=True,
            text=True,
        )

    def test_default_builds_a_fresh_strict_fixture(self) -> None:
        built = object()
        with mock.patch.object(
            test_site,
            "build_fixture_public",
            return_value=(Path("/tmp/fresh-public"), built),
        ) as build:
            public, result = test_site.checker_fixture_public(None, "custom-hugo")

        self.assertEqual(public, Path("/tmp/fresh-public"))
        self.assertIs(result, built)
        build.assert_called_once_with(
            "custom-hugo", "--printPathWarnings", "--panicOnWarning"
        )

    def test_explicit_public_is_reused_without_a_build(self) -> None:
        supplied = Path("/tmp/existing-public")
        with mock.patch.object(test_site, "build_fixture_public") as build:
            public, result = test_site.checker_fixture_public(supplied, "unused")

        self.assertEqual(public, supplied)
        self.assertIsNone(result)
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
