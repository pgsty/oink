#!/usr/bin/env python3
"""Self-tests for fresh and explicitly reused checker input modes."""

from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

import test_site  # noqa: E402


class CheckerFixtureInputTests(unittest.TestCase):
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
