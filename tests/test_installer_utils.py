# SPDX-License-Identifier: MIT

"""
This file is imported from https://github.com/pypa/build/blob/35d86b8/tests/test_projectbuilder.py
Some modifications have been made to make the code standalone.

If possible, this code should stay as close to the original as possible.
"""

from __future__ import annotations

import sys
import textwrap

import pytest

from variantlib.installer_utils import check_dependency

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
    from importlib.metadata import Distribution
    from importlib.metadata import PackageNotFoundError
else:
    import importlib_metadata
    from importlib_metadata import Distribution
    from importlib_metadata import PackageNotFoundError


class MockDistribution(Distribution):
    def locate_file(self, path):  # pragma: no cover
        return ""

    @classmethod
    def from_name(cls, name):
        if name == "extras_dep":
            return ExtraMockDistribution()
        if name == "requireless_dep":
            return RequirelessMockDistribution()
        if name == "recursive_dep":
            return RecursiveMockDistribution()
        if name == "prerelease_dep":
            return PrereleaseMockDistribution()
        if name == "circular_dep":
            return CircularMockDistribution()
        if name == "nested_circular_dep":
            return NestedCircularMockDistribution()
        raise PackageNotFoundError


class ExtraMockDistribution(MockDistribution):
    def read_text(self, filename) -> str | None:
        if filename == "METADATA":
            return textwrap.dedent(
                """
                Metadata-Version: 2.2
                Name: extras_dep
                Version: 1.0.0
                Provides-Extra: extra-without-associated-deps
                Provides-Extra: extra-with_unmet-deps
                Requires-Dist: unmet_dep; extra == 'extra-with-unmet-deps'
                Provides-Extra: extra-with-met-deps
                Requires-Dist: extras_dep; extra == 'extra-with-met-deps'
                Provides-Extra: recursive-extra-with-unmet-deps
                Requires-Dist: recursive_dep; extra == 'recursive-extra-with-unmet-deps'
                """
            ).strip()

        return None


class RequirelessMockDistribution(MockDistribution):
    def read_text(self, filename) -> str | None:
        if filename == "METADATA":
            return textwrap.dedent(
                """
                Metadata-Version: 2.2
                Name: requireless_dep
                Version: 1.0.0
                """
            ).strip()

        return None


class RecursiveMockDistribution(MockDistribution):
    def read_text(self, filename) -> str | None:
        if filename == "METADATA":
            return textwrap.dedent(
                """
                Metadata-Version: 2.2
                Name: recursive_dep
                Version: 1.0.0
                Requires-Dist: recursive_unmet_dep
                """
            ).strip()

        return None


class PrereleaseMockDistribution(MockDistribution):
    def read_text(self, filename) -> str | None:
        if filename == "METADATA":
            return textwrap.dedent(
                """
                Metadata-Version: 2.2
                Name: prerelease_dep
                Version: 1.0.1a0
                """
            ).strip()

        return None


class CircularMockDistribution(MockDistribution):
    def read_text(self, filename) -> str | None:
        if filename == "METADATA":
            return textwrap.dedent(
                """
                Metadata-Version: 2.2
                Name: circular_dep
                Version: 1.0.0
                Requires-Dist: nested_circular_dep
                """
            ).strip()

        return None


class NestedCircularMockDistribution(MockDistribution):
    def read_text(self, filename) -> str | None:
        if filename == "METADATA":
            return textwrap.dedent(
                """
                Metadata-Version: 2.2
                Name: nested_circular_dep
                Version: 1.0.0
                Requires-Dist: circular_dep
                """
            ).strip()

        return None


@pytest.mark.parametrize(
    ("requirement_string", "expected"),
    [
        ("extras_dep", None),
        ("missing_dep", ("missing_dep",)),
        ("requireless_dep", None),
        ("extras_dep[undefined_extra]", None),
        # would the wheel builder filter this out?
        ("extras_dep[extra-without-associated-deps]", None),
        (
            "extras_dep[extra-with-unmet-deps]",
            (
                "extras_dep[extra-with-unmet-deps]",
                'unmet_dep; extra == "extra-with-unmet-deps"',
            ),
        ),
        (
            "extras_dep[recursive-extra-with-unmet-deps]",
            (
                "extras_dep[recursive-extra-with-unmet-deps]",
                'recursive_dep; extra == "recursive-extra-with-unmet-deps"',
                "recursive_unmet_dep",
            ),
        ),
        ("extras_dep[extra-with-met-deps]", None),
        ('missing_dep; python_version>"10"', None),
        ('missing_dep; python_version<="1"', None),
        ('missing_dep; python_version>="1"', ('missing_dep; python_version >= "1"',)),
        ("extras_dep == 1.0.0", None),
        ("extras_dep == 2.0.0", ("extras_dep==2.0.0",)),
        ("extras_dep[extra-without-associated-deps] == 1.0.0", None),
        (
            "extras_dep[extra-without-associated-deps] == 2.0.0",
            ("extras_dep[extra-without-associated-deps]==2.0.0",),
        ),
        ("prerelease_dep >= 1.0.0", None),
        ("circular_dep", None),
    ],
)
def test_check_dependency(monkeypatch, requirement_string, expected):
    monkeypatch.setattr(importlib_metadata, "Distribution", MockDistribution)
    assert next(check_dependency(requirement_string), None) == expected
