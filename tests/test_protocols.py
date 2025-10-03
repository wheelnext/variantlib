from __future__ import annotations

import pytest
from variantlib.models.provider import VariantFeatureConfig
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType

from tests import mocked_plugin_as_module
from tests.mocked_plugins import MockedPluginA
from tests.mocked_plugins import MockedPluginC
from tests.mocked_plugins import MyVariantFeatureConfig


class VariantFeatureConfigTypeSubclass(VariantFeatureConfigType):
    name = "a"
    values = ["b"]
    multi_value = False

    def __init__(self, *args):
        pass


@pytest.mark.parametrize(
    "cls",
    [VariantFeatureConfig, MyVariantFeatureConfig, VariantFeatureConfigTypeSubclass],
)
def test_variant_feature_config_type(cls: type) -> None:
    # TODO: why do we need to instantiate it? VariantFeatureConfig fails otherwise.
    assert isinstance(
        cls(name="x", values=["y"], multi_value=False), VariantFeatureConfigType
    )


@pytest.mark.parametrize("missing", ["name", "values", "multi_value"])
def test_variant_feature_config_type_abstract(missing: str) -> None:
    class PartialVariantFeatureConfigTypeSubclass(VariantFeatureConfigType):
        if missing != "name":
            name = "a"
        if missing != "values":
            values = ["b"]
        if missing != "multi_value":
            multi_value = False

    with pytest.raises(TypeError):
        PartialVariantFeatureConfigTypeSubclass()


@pytest.mark.parametrize("cls", [MockedPluginA, MockedPluginC, mocked_plugin_as_module])
def test_plugin_type(cls: type) -> None:
    assert isinstance(cls, PluginType)


@pytest.mark.parametrize(
    "missing", ["namespace", "get_all_configs", "get_supported_configs"]
)
def test_plugin_type_abstract(missing: str) -> None:
    class PartialPluginTypeSubclass(PluginType):
        if missing != "namespace":
            namespace = "ns"

        if missing != "get_all_configs":

            @staticmethod
            def get_all_configs() -> list[VariantFeatureConfigType]:
                return []

        if missing != "get_supported_configs":

            @staticmethod
            def get_supported_configs() -> list[VariantFeatureConfigType]:
                return []

    with pytest.raises(TypeError):
        PartialPluginTypeSubclass()
