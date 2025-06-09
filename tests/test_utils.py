from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.utils import get_combinations
from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.models.provider import ProviderConfig
from variantlib.utils import aggregate_feature_priorities
from variantlib.utils import aggregate_namespace_priorities
from variantlib.utils import aggregate_property_priorities

if TYPE_CHECKING:
    from variantlib.models.provider import ProviderConfig
    from variantlib.plugins.loader import BasePluginLoader


@pytest.fixture
def configs(
    mocked_plugin_loader: BasePluginLoader,
) -> list[ProviderConfig]:
    return list(mocked_plugin_loader.get_supported_configs().values())


def test_get_combinations(configs: list[ProviderConfig]) -> None:
    """Test `get_combinations` yields the expected result in the right order."""
    val1a = VariantProperty("test_namespace", "name1", "val1a")
    val1b = VariantProperty("test_namespace", "name1", "val1b")
    val2a = VariantProperty("test_namespace", "name2", "val2a")
    val2b = VariantProperty("test_namespace", "name2", "val2b")
    val2c = VariantProperty("test_namespace", "name2", "val2c")
    val3a = VariantProperty("second_namespace", "name3", "val3a")

    namespace_priorities = [
        "test_namespace",
        "second_namespace",
    ]

    assert list(get_combinations(configs, namespace_priorities)) == [
        VariantDescription([val1a, val2a, val3a]),
        VariantDescription([val1a, val2a]),
        VariantDescription([val1a, val2b, val3a]),
        VariantDescription([val1a, val2b]),
        VariantDescription([val1a, val2c, val3a]),
        VariantDescription([val1a, val2c]),
        VariantDescription([val1a, val3a]),
        VariantDescription([val1a]),
        VariantDescription([val1b, val2a, val3a]),
        VariantDescription([val1b, val2a]),
        VariantDescription([val1b, val2b, val3a]),
        VariantDescription([val1b, val2b]),
        VariantDescription([val1b, val2c, val3a]),
        VariantDescription([val1b, val2c]),
        VariantDescription([val1b, val3a]),
        VariantDescription([val1b]),
        VariantDescription([val2a, val3a]),
        VariantDescription([val2a]),
        VariantDescription([val2b, val3a]),
        VariantDescription([val2b]),
        VariantDescription([val2c, val3a]),
        VariantDescription([val2c]),
        VariantDescription([val3a]),
        VariantDescription(),
    ]


def test_get_combinations_flipped_order(configs: list[ProviderConfig]) -> None:
    """Test `get_combinations` yields the expected result in the right order."""
    val1a = VariantProperty("test_namespace", "name1", "val1a")
    val1b = VariantProperty("test_namespace", "name1", "val1b")
    val2a = VariantProperty("test_namespace", "name2", "val2a")
    val2b = VariantProperty("test_namespace", "name2", "val2b")
    val2c = VariantProperty("test_namespace", "name2", "val2c")
    val3a = VariantProperty("second_namespace", "name3", "val3a")

    namespace_priorities = [
        "second_namespace",
        "test_namespace",
    ]

    assert list(get_combinations(configs, namespace_priorities)) == [
        VariantDescription([val1a, val2a, val3a]),
        VariantDescription([val1a, val2b, val3a]),
        VariantDescription([val1a, val2c, val3a]),
        VariantDescription([val1a, val3a]),
        VariantDescription([val1b, val2a, val3a]),
        VariantDescription([val1b, val2b, val3a]),
        VariantDescription([val1b, val2c, val3a]),
        VariantDescription([val1b, val3a]),
        VariantDescription([val2a, val3a]),
        VariantDescription([val2b, val3a]),
        VariantDescription([val2c, val3a]),
        VariantDescription([val3a]),
        VariantDescription([val1a, val2a]),
        VariantDescription([val1a, val2b]),
        VariantDescription([val1a, val2c]),
        VariantDescription([val1a]),
        VariantDescription([val1b, val2a]),
        VariantDescription([val1b, val2b]),
        VariantDescription([val1b, val2c]),
        VariantDescription([val1b]),
        VariantDescription([val2a]),
        VariantDescription([val2b]),
        VariantDescription([val2c]),
        VariantDescription(),
    ]


def test_get_combinations_one_one_namespace_one(configs: list[ProviderConfig]) -> None:
    """Test `get_combinations` yields the expected result in the right order."""

    namespace_priorities = ["second_namespace"]

    assert list(get_combinations(configs, namespace_priorities)) == [
        VariantDescription(
            [
                VariantProperty("second_namespace", "name3", "val3a"),
            ]
        ),
        VariantDescription(),
    ]


def test_get_combinations_one_one_namespace_two(configs: list[ProviderConfig]) -> None:
    """Test `get_combinations` yields the expected result in the right order."""
    val1a = VariantProperty("test_namespace", "name1", "val1a")
    val1b = VariantProperty("test_namespace", "name1", "val1b")
    val2a = VariantProperty("test_namespace", "name2", "val2a")
    val2b = VariantProperty("test_namespace", "name2", "val2b")
    val2c = VariantProperty("test_namespace", "name2", "val2c")

    namespace_priorities = [
        "test_namespace",
    ]

    assert list(get_combinations(configs, namespace_priorities)) == [
        VariantDescription([val1a, val2a]),
        VariantDescription([val1a, val2b]),
        VariantDescription([val1a, val2c]),
        VariantDescription([val1a]),
        VariantDescription([val1b, val2a]),
        VariantDescription([val1b, val2b]),
        VariantDescription([val1b, val2c]),
        VariantDescription([val1b]),
        VariantDescription([val2a]),
        VariantDescription([val2b]),
        VariantDescription([val2c]),
        VariantDescription(),
    ]


@pytest.mark.parametrize(
    ("lists", "expected"),
    [
        ([None, [1, 2, 3]], [1, 2, 3]),
        ([[], [1, 2, 3]], [1, 2, 3]),
        ([[1], [1, 2, 3]], [1, 2, 3]),
        ([[1, 4], [1, 2, 3]], [1, 4, 2, 3]),
        ([[5], [1, 2, 3]], [5, 1, 2, 3]),
        ([[3], [1, 2, 3]], [3, 1, 2]),
        ([[3], [1, 3], [3, 2, 1]], [3, 1, 2]),
        ([[3], None, [3, 2, 1]], [3, 2, 1]),
        ([None, None, [2, 3, 1]], [2, 3, 1]),
    ],
)
def test_aggregate_namespace_priorities(
    lists: list[list[int] | None], expected: list[int]
) -> None:
    assert aggregate_namespace_priorities(*lists) == expected


@pytest.mark.parametrize(
    ("dicts", "expected"),
    [
        ([None, {1: [1, 2], 2: [2, 3]}], {1: [1, 2], 2: [2, 3]}),
        ([{}, {1: [1, 2], 2: [2, 3]}], {1: [1, 2], 2: [2, 3]}),
        ([{1: [2], 3: [1]}, {1: [1, 2], 2: [2, 3]}], {1: [2, 1], 2: [2, 3], 3: [1]}),
        ([{1: [], 3: [1]}, {1: [1, 2], 2: [3]}], {1: [1, 2], 2: [3], 3: [1]}),
        ([{1: [], 3: [1]}, None, {1: [1, 2], 2: [3]}], {1: [1, 2], 2: [3], 3: [1]}),
        ([{1: [], 3: [1]}, {1: [2]}, {1: [1, 2], 2: [3]}], {1: [2, 1], 2: [3], 3: [1]}),
    ],
)
def test_aggregate_feature_priorities(
    dicts: list[dict[int, list[int]] | None], expected: dict[int, list[int]]
) -> None:
    assert aggregate_feature_priorities(*dicts) == expected


@pytest.mark.parametrize(
    ("dicts", "expected"),
    [
        (
            [None, {1: {2: [3, 4], 3: [4, 5]}, 2: {3: [4], 4: [5, 6]}}],
            {1: {2: [3, 4], 3: [4, 5]}, 2: {3: [4], 4: [5, 6]}},
        ),
        (
            [{}, {1: {2: [3, 4], 3: [4, 5]}, 2: {3: [4], 4: [5, 6]}}],
            {1: {2: [3, 4], 3: [4, 5]}, 2: {3: [4], 4: [5, 6]}},
        ),
        (
            [
                {1: {2: [4], 4: [1]}, 2: {4: [1]}},
                {1: {2: [3, 4], 3: [4, 5]}, 2: {3: [4], 4: [5, 6]}},
            ],
            {1: {2: [4, 3], 3: [4, 5], 4: [1]}, 2: {3: [4], 4: [1, 5, 6]}},
        ),
        (
            [
                {1: {2: [4], 4: [1]}, 2: {4: [1]}},
                None,
                {1: {2: [3, 4], 3: [4, 5]}, 2: {3: [4], 4: [5, 6]}},
            ],
            {1: {2: [4, 3], 3: [4, 5], 4: [1]}, 2: {3: [4], 4: [1, 5, 6]}},
        ),
        (
            [
                {1: {2: [4], 4: [1]}, 2: {4: [1]}},
                {1: {4: [2]}, 2: {3: [1]}},
                {1: {2: [3, 4], 3: [4, 5]}, 2: {3: [4], 4: [5, 6]}},
            ],
            {1: {2: [4, 3], 3: [4, 5], 4: [1, 2]}, 2: {3: [1, 4], 4: [1, 5, 6]}},
        ),
    ],
)
def test_aggregate_property_priorities(
    dicts: list[dict[int, dict[int, list[int]]] | None],
    expected: dict[int, dict[int, list[int]]],
) -> None:
    assert aggregate_property_priorities(*dicts) == expected
