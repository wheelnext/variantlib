from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from variantlib.constants import VARIANT_ABI_DEPENDENCY_NAMESPACE
from variantlib.models.variant import VariantProperty
from variantlib.resolver.lib import inject_abi_dependency

if TYPE_CHECKING:
    import pytest_mock
    from variantlib.protocols import VariantNamespace


@dataclass
class MockedDistribution:
    name: str
    version: str


def test_inject_abi_dependency(
    monkeypatch: pytest.MonkeyPatch, mocker: pytest_mock.MockerFixture
) -> None:
    monkeypatch.delenv("VARIANT_ABI_DEPENDENCY", raising=False)

    namespace_priorities = ["foo"]
    supported_vprops = [
        VariantProperty("foo", "bar", "baz"),
    ]

    mocker.patch("importlib.metadata.distributions").return_value = [
        MockedDistribution("a", "4"),
        MockedDistribution("b", "4.3b1"),
        MockedDistribution("c", "7.2.3.post4"),
        MockedDistribution("d", "1.2.3.4"),
    ]
    inject_abi_dependency(supported_vprops, namespace_priorities)

    assert namespace_priorities == ["foo", VARIANT_ABI_DEPENDENCY_NAMESPACE]
    assert supported_vprops == [
        VariantProperty("foo", "bar", "baz"),
        VariantProperty("abi_dependency", "a", "4"),
        VariantProperty("abi_dependency", "a", "4.0"),
        VariantProperty("abi_dependency", "a", "4.0.0"),
        VariantProperty("abi_dependency", "b", "4"),
        VariantProperty("abi_dependency", "b", "4.3"),
        VariantProperty("abi_dependency", "b", "4.3.0"),
        VariantProperty("abi_dependency", "c", "7"),
        VariantProperty("abi_dependency", "c", "7.2"),
        VariantProperty("abi_dependency", "c", "7.2.3"),
        VariantProperty("abi_dependency", "d", "1"),
        VariantProperty("abi_dependency", "d", "1.2"),
        VariantProperty("abi_dependency", "d", "1.2.3"),
    ]


@pytest.mark.parametrize(
    "env_value",
    [
        "",
        "c==7.8.9b1",
        "d==4.9.4,c==7.8.9",
        "a==1.2.79",
        "a==1.2.79,d==4.9.4",
        # invalid components should be ignored (with a warning)
        "no-version",
        "a==1.2.79,no-version",
        "z>=1.2.3",
    ],
)
def test_inject_abi_dependency_envvar(
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest_mock.MockerFixture,
    env_value: str,
) -> None:
    monkeypatch.setenv("VARIANT_ABI_DEPENDENCY", env_value)

    namespace_priorities: list[VariantNamespace] = []
    supported_vprops: list[VariantProperty] = []

    mocker.patch("importlib.metadata.distributions").return_value = [
        MockedDistribution("a", "1.2.3"),
        MockedDistribution("b", "4.7.9"),
    ]
    inject_abi_dependency(supported_vprops, namespace_priorities)

    expected = {
        VariantProperty("abi_dependency", "b", "4"),
        VariantProperty("abi_dependency", "b", "4.7"),
        VariantProperty("abi_dependency", "b", "4.7.9"),
    }
    if "a" not in env_value:
        expected |= {
            VariantProperty("abi_dependency", "a", "1"),
            VariantProperty("abi_dependency", "a", "1.2"),
            VariantProperty("abi_dependency", "a", "1.2.3"),
        }
    else:
        expected |= {
            VariantProperty("abi_dependency", "a", "1"),
            VariantProperty("abi_dependency", "a", "1.2"),
            VariantProperty("abi_dependency", "a", "1.2.79"),
        }
    if "c" in env_value:
        expected |= {
            VariantProperty("abi_dependency", "c", "7"),
            VariantProperty("abi_dependency", "c", "7.8"),
            VariantProperty("abi_dependency", "c", "7.8.9"),
        }
    if "d" in env_value:
        expected |= {
            VariantProperty("abi_dependency", "d", "4"),
            VariantProperty("abi_dependency", "d", "4.9"),
            VariantProperty("abi_dependency", "d", "4.9.4"),
        }

    assert namespace_priorities == [VARIANT_ABI_DEPENDENCY_NAMESPACE]
    assert set(supported_vprops) == expected
