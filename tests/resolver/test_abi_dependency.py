from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from variantlib.constants import VARIANT_ABI_DEPENDENCY_NAMESPACE
from variantlib.models.variant import VariantProperty
from variantlib.resolver.lib import inject_abi_dependency

if TYPE_CHECKING:
    import pytest
    import pytest_mock


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
