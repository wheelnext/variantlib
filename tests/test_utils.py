from __future__ import annotations

import pytest

from tests.test_plugins import mocked_plugin_loader  # noqa: F401
from tests.utils import get_combinations
from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.loader import PluginLoader
from variantlib.utils import aggregate_user_and_default_lists


@pytest.fixture
def configs(mocked_plugin_loader: type[PluginLoader]):  # noqa: F811
    return list(PluginLoader.get_supported_configs().values())


def test_get_combinations(configs):
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
    ]


def test_get_combinations_flipped_order(configs):
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
    ]


def test_get_combinations_one_one_namespace_one(configs):
    """Test `get_combinations` yields the expected result in the right order."""

    namespace_priorities = ["second_namespace"]

    assert list(get_combinations(configs, namespace_priorities)) == [
        VariantDescription([VariantProperty("second_namespace", "name3", "val3a")]),
    ]


def test_get_combinations_one_one_namespace_two(configs):
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
    ]


@pytest.mark.parametrize(
    ("user_list", "default_list", "expected"),
    [
        (None, [1, 2, 3], [1, 2, 3]),
        ([], [1, 2, 3], [1, 2, 3]),
        ([1], [1, 2, 3], [1, 2, 3]),
        ([1, 4], [1, 2, 3], [1, 4, 2, 3]),
        ([5], [1, 2, 3], [5, 1, 2, 3]),
        ([3], [1, 2, 3], [3, 1, 2]),
    ],
)
def test_aggregate_user_and_default_lists(
    user_list: list | None, default_list: list, expected: list
):
    assert aggregate_user_and_default_lists(user_list, default_list) == expected
